"""
Broker Router — REST API for broker connections (INDstocks + Zerodha).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ZERODHA KITE CONNECT — WHAT TO ENTER ON developers.kite.trade
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Redirect URL (required):
    Local dev  → http://localhost:8000/api/broker/zerodha/callback
    Production → https://your-backend.com/api/broker/zerodha/callback

  Postback URL (optional — for order/trade event webhooks):
    Local dev  → http://localhost:8000/api/broker/zerodha/postback
    Production → https://your-backend.com/api/broker/zerodha/postback
    (Leave blank if you don't need order event notifications)

The user_id is passed as a `state` query param in the login URL
and echoed back by us in the callback to identify which user logged in.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Endpoints:
  GET  /api/broker/list                          → All available brokers
  GET  /api/broker/{user_id}/status              → Which brokers are connected
  GET  /api/broker/zerodha/login-url?user_id=..  → Build Zerodha OAuth URL with state
  GET  /api/broker/indstocks/login-url           → INDstocks token-gen page URL
  POST /api/broker/{user_id}/indstocks/connect   → Connect via token (INDstocks)
  GET  /api/broker/zerodha/callback              → Fixed OAuth callback (Zerodha registers this)
  POST /api/broker/zerodha/postback              → Zerodha order/trade event webhook
  POST /api/broker/{user_id}/{broker_id}/sync    → Pull holdings from broker → MongoDB
  DELETE /api/broker/{user_id}/{broker_id}       → Disconnect broker
"""
import logging
import os
import secrets
import time
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from integrations.broker_registry import get_broker, list_brokers
from memory.mongodb import db as memory
from utils.csv_import import parse_csv_content

logger = logging.getLogger("boardroom-ai")
router = APIRouter()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL  = os.getenv("BACKEND_URL",  "http://localhost:8000")

# ── In-memory state store for OAuth CSRF protection ─────────────────────────
# Maps state_token → { user_id, created_at }
# In production: use Redis or MongoDB with a short TTL
_oauth_state_store: dict[str, dict] = {}
STATE_TTL_SECONDS = 300  # 5 minutes


# ── Request / Response models ────────────────────────────────────────────────

class TokenConnectRequest(BaseModel):
    token: str   # Bearer token pasted by user (for INDstocks)


# ── Helper ───────────────────────────────────────────────────────────────────

def _create_state(user_id: str) -> str:
    """Generate a short-lived CSRF state token tied to a user_id."""
    state = secrets.token_urlsafe(16)
    _oauth_state_store[state] = {"user_id": user_id, "created_at": time.time()}
    return state


def _consume_state(state: str) -> Optional[str]:
    """Validate and consume a state token. Returns user_id or None if invalid/expired."""
    entry = _oauth_state_store.pop(state, None)
    if not entry:
        return None
    if time.time() - entry["created_at"] > STATE_TTL_SECONDS:
        return None
    return entry["user_id"]


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/list")
async def list_available_brokers():
    """Return all supported brokers with metadata."""
    return {"brokers": list_brokers()}


@router.get("/{user_id}/status")
async def get_broker_status(user_id: str):
    """Show which brokers this user has connected and token freshness."""
    connections = await memory.get_broker_connections(user_id)
    result = {}
    for broker_id, token_data in connections.items():
        try:
            expired = get_broker(broker_id).is_token_expired(token_data)
        except Exception:
            expired = True
        result[broker_id] = {
            "connected":    True,
            "user_name":    token_data.get("user_name", ""),
            "connected_at": token_data.get("generated_at", 0),
            "is_expired":   expired,
        }
    return {"user_id": user_id, "connections": result}


@router.get("/zerodha/login-url")
async def get_zerodha_login_url(user_id: str = Query(..., description="FinBoard user ID")):
    """
    Build the Zerodha OAuth login URL with a state token.

    State token encodes the user_id so the callback knows who is connecting.
    This is the URL you open in the browser / redirect to.

    The REDIRECT URL registered on developers.kite.trade must be:
        http://localhost:8000/api/broker/zerodha/callback
    """
    try:
        broker = get_broker("zerodha")
        state  = _create_state(user_id)
        # Zerodha doesn't natively support ?state= but we pass it as a custom param
        # Our callback reads it back from the query string
        base_url = broker.get_login_url()
        login_url = f"{base_url}&state={state}"
        return {
            "login_url":    login_url,
            "redirect_url": f"{BACKEND_URL}/api/broker/zerodha/callback",
            "state":        state,
            "expires_in":   STATE_TTL_SECONDS,
            "note":         "Register the redirect_url on developers.kite.trade",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/indstocks/login-url")
async def get_indstocks_login_url():
    """Return the INDstocks token-generation page URL (manual token flow)."""
    broker = get_broker("indstocks")
    return {
        "login_url": broker.get_login_url(),
        "auth_type": "token",
        "instructions": [
            "1. Log in to your INDstocks account first (e.g. at indstocks.com)",
            "2. Open the login_url in your browser",
            "3. Click 'Generate Token' or 'Get Started'",
            "4. Copy the token and paste it in FinBoard",
        ],
    }


@router.get("/{broker_id}/login-url")
async def get_broker_login_url(broker_id: str, user_id: str = Query(default="")):
    """
    Universal login-URL endpoint for all brokers.
    The frontend calls this with ?user_id= for OAuth brokers.
    Dispatches to broker-specific logic.

    For OAuth brokers: returns a login_url with a state token embedding user_id.
    For token brokers: returns the token-generation page URL.
    """
    try:
        broker = get_broker(broker_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if broker.AUTH_TYPE == "token":
        return {
            "broker_id":  broker_id,
            "login_url":  broker.get_login_url(),
            "auth_type":  "token",
        }
    else:
        # OAuth: need user_id to create state token
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required for OAuth brokers")
        state    = _create_state(user_id)
        base_url = broker.get_login_url(
            redirect_uri=f"{BACKEND_URL}/api/broker/{broker_id}/callback"
        )
        return {
            "broker_id":    broker_id,
            "login_url":    f"{base_url}&state={state}",
            "redirect_url": f"{BACKEND_URL}/api/broker/{broker_id}/callback",
            "auth_type":    "oauth",
            "state":        state,
            "expires_in":   STATE_TTL_SECONDS,
        }


# ── INDstocks Token Connect ──────────────────────────────────────────────────

@router.post("/{user_id}/indstocks/connect")
async def connect_indstocks(user_id: str, req: TokenConnectRequest):
    """
    Connect INDstocks: validate the user-pasted Bearer token and store it.
    Immediately syncs holdings after a successful connection.
    """
    try:
        broker     = get_broker("indstocks")
        token_data = await broker.exchange_token(req.token)
        await memory.save_broker_connection(user_id, "indstocks", token_data)
        return {
            "status":    "connected",
            "broker":    "indstocks",
            "user_name": token_data.get("user_name", ""),
            "message":   "INDstocks connected! Click 'Sync Holdings' to import your portfolio.",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[broker] INDstocks connect error for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")


@router.post("/{user_id}/{broker_id}/connect")
async def connect_token_broker(user_id: str, broker_id: str, req: TokenConnectRequest):
    """
    Generic token-connect for any token-auth broker.
    Works for INDstocks and any future token-based brokers added to the registry.
    """
    try:
        broker = get_broker(broker_id)
        if broker.AUTH_TYPE != "token":
            raise HTTPException(
                status_code=400,
                detail=f"{broker.BROKER_NAME} uses OAuth — use the login URL flow instead.",
            )
        token_data = await broker.exchange_token(req.token)
        await memory.save_broker_connection(user_id, broker_id, token_data)
        return {
            "status":    "connected",
            "broker":    broker_id,
            "user_name": token_data.get("user_name", ""),
            "message":   f"{broker.BROKER_NAME} connected successfully.",
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[broker] Token connect error {broker_id}/{user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")


# ── Upstox OAuth Callback ─────────────────────────────────────────────────────
# Register on Upstox developer portal: http://localhost:8000/api/broker/upstox/callback

@router.get("/upstox/login-url")
async def get_upstox_login_url(user_id: str = Query(...)):
    """Build the Upstox OAuth login URL with state token."""
    try:
        broker   = get_broker("upstox")
        state    = _create_state(user_id)
        base_url = broker.get_login_url(
            f"{BACKEND_URL}/api/broker/upstox/callback"
        )
        return {
            "login_url":    f"{base_url}&state={state}",
            "redirect_url": f"{BACKEND_URL}/api/broker/upstox/callback",
            "note":         "Free API — register redirect_url at account.upstox.com/developer/apps",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/upstox/callback")
async def upstox_oauth_callback(
    code:  str = Query(default="", description="Authorization code from Upstox"),
    state: str = Query(default="", description="Our CSRF state token"),
    error: str = Query(default="", description="Error from Upstox if login failed"),
):
    """Upstox OAuth callback — exchanges code for access_token and syncs holdings."""
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/portfolio?broker=upstox&error={error}")

    user_id = _consume_state(state) if state else None
    if not user_id:
        return HTMLResponse(content=_state_error_page().replace("Zerodha", "Upstox"), status_code=400)

    try:
        broker     = get_broker("upstox")
        token_data = await broker.exchange_token(
            code,
            redirect_uri=f"{BACKEND_URL}/api/broker/upstox/callback",
        )
        await memory.save_broker_connection(user_id, "upstox", token_data)

        holdings      = await broker.fetch_holdings(token_data)
        holdings_list = [h.to_dict() for h in holdings]
        await memory.upsert_user_profile(user_id, {"portfolio.holdings": holdings_list})

        return RedirectResponse(
            f"{FRONTEND_URL}/portfolio?broker=upstox&status=connected&holdings={len(holdings_list)}"
        )
    except Exception as e:
        logger.error(f"[upstox] Callback error for {user_id}: {e}")
        return RedirectResponse(f"{FRONTEND_URL}/portfolio?broker=upstox&error={str(e)[:100]}")


# ── CSV Import (Free — no API key needed) ─────────────────────────────────────

@router.post("/{user_id}/import/csv")
async def import_csv_holdings(user_id: str, file: UploadFile = File(...)):
    """
    Import portfolio holdings from a broker-exported CSV or XLSX file.
    Supports: Zerodha Console, Groww, and generic CSV formats.
    
    How to export from Zerodha Console (FREE):
    1. Go to console.zerodha.com
    2. Portfolio → Holdings
    3. Click the XLSX button (top right)
    4. Save as CSV (File → Save As → CSV in Excel/Sheets)
    5. Upload here
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Accept CSV and XLSX (XLSX must be converted to CSV first)
    allowed = (".csv", ".txt")
    if not any(file.filename.lower().endswith(ext) for ext in allowed):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file. For XLSX: open in Excel/Sheets → File → Save As → CSV."
        )

    try:
        content  = await file.read()
        csv_text = content.decode("utf-8-sig")   # utf-8-sig handles Excel BOM
    except UnicodeDecodeError:
        try:
            csv_text = content.decode("latin-1")
        except Exception:
            raise HTTPException(status_code=400, detail="Could not decode file. Please save as UTF-8 CSV.")

    result = parse_csv_content(csv_text)

    if result.errors:
        raise HTTPException(status_code=422, detail=" | ".join(result.errors))

    if not result.holdings:
        raise HTTPException(
            status_code=422,
            detail=f"No valid holdings found. Detected format: {result.broker_detected}. "
                   f"Make sure Symbol, Quantity, and Avg Cost columns are present."
        )

    # Save to MongoDB (merges with existing — same symbol gets updated)
    existing_profile = await memory.get_user_profile(user_id)
    existing = existing_profile.get("portfolio", {}).get("holdings", [])

    # Merge: imported holdings overwrite existing by symbol
    existing_map = {h["symbol"]: h for h in existing}
    for h in result.holdings:
        existing_map[h["symbol"]] = h
    merged = list(existing_map.values())

    await memory.upsert_user_profile(user_id, {
        "portfolio.holdings":      merged,
        "portfolio.last_imported": time.time(),
        "portfolio.import_source": result.broker_detected,
    })

    return {
        "status":          "imported",
        "broker_detected": result.broker_detected,
        "imported_count":  len(result.holdings),
        "total_holdings":  len(merged),
        "skipped":         result.skipped,
        "message":         f"Imported {len(result.holdings)} holdings from {result.broker_detected} CSV",
    }

# This is the FIXED URL you register on developers.kite.trade:
#   http://localhost:8000/api/broker/zerodha/callback

@router.get("/zerodha/callback")
async def zerodha_oauth_callback(
    request_token: str  = Query(default="",        description="Token from Zerodha after login"),
    action:        str  = Query(default="login",   description="Action type from Zerodha"),
    status:        str  = Query(default="success", description="Login status from Zerodha"),
    state:         str  = Query(default="",        description="Our CSRF state token"),
    type:          str  = Query(default="",        description="Zerodha error type if failed"),
):
    """
    Zerodha OAuth callback — FIXED URL registered on developers.kite.trade.

    What Zerodha sends back:
      On success: ?request_token=xxx&action=login&status=success&state=yyy
      On failure: ?status=error&type=UserException&message=...

    We use the 'state' parameter to recover which user_id initiated the login.
    """
    # ── Failed login from Zerodha side ──────────────────────────────────────
    if status != "success" or not request_token:
        logger.warning(f"[zerodha] Login failed — status={status} type={type}")
        return RedirectResponse(
            f"{FRONTEND_URL}/portfolio?broker=zerodha&error=login_failed&type={type}"
        )

    # ── Recover user_id from state token ────────────────────────────────────
    user_id = _consume_state(state) if state else None
    if not user_id:
        logger.error(f"[zerodha] Invalid/expired state token: '{state}'")
        # Show a helpful HTML error instead of crashing
        return HTMLResponse(
            content=_state_error_page(),
            status_code=400,
        )

    # ── Exchange request_token for access_token ──────────────────────────────
    try:
        broker     = get_broker("zerodha")
        token_data = await broker.exchange_token(request_token)
        await memory.save_broker_connection(user_id, "zerodha", token_data)

        # Auto-sync holdings
        holdings      = await broker.fetch_holdings(token_data)
        holdings_list = [h.to_dict() for h in holdings]
        await memory.upsert_user_profile(user_id, {"portfolio.holdings": holdings_list})

        logger.info(f"[zerodha] Connected {token_data.get('user_name')} — {len(holdings_list)} holdings synced")
        return RedirectResponse(
            f"{FRONTEND_URL}/portfolio?broker=zerodha&status=connected&holdings={len(holdings_list)}"
        )
    except Exception as e:
        logger.error(f"[zerodha] Callback error for user {user_id}: {e}")
        return RedirectResponse(
            f"{FRONTEND_URL}/portfolio?broker=zerodha&error={str(e)[:100]}"
        )


# ── Zerodha Postback (Order / Trade events) ───────────────────────────────────
# Optional — register http://localhost:8000/api/broker/zerodha/postback
# on developers.kite.trade if you want real-time order fill notifications.

@router.post("/zerodha/postback")
async def zerodha_postback(request: Request):
    """
    Zerodha Postback URL handler.

    Zerodha POSTs to this URL when:
    - An order is placed, modified, or cancelled
    - A trade is executed (order fill)

    We log the event and could trigger a board meeting alert in future.
    Register on developers.kite.trade as:
        http://localhost:8000/api/broker/zerodha/postback
    """
    try:
        body = await request.json()
        order_id     = body.get("order_id", "")
        status       = body.get("status", "")
        tradingsymbol = body.get("tradingsymbol", "")
        logger.info(f"[zerodha/postback] Order {order_id} | {tradingsymbol} | status={status}")
        # Future: broadcast to WebSocket, trigger board meeting alert
    except Exception as e:
        logger.warning(f"[zerodha/postback] Parse error: {e}")

    return {"status": "ok"}   # Always return 200 to Zerodha


# ── Sync & Disconnect ─────────────────────────────────────────────────────────

@router.post("/{user_id}/{broker_id}/sync")
async def sync_broker_holdings(user_id: str, broker_id: str):
    """Pull latest holdings from broker → enrich with yfinance → save to MongoDB."""
    connections = await memory.get_broker_connections(user_id)
    token_data  = connections.get(broker_id)

    if not token_data:
        raise HTTPException(
            status_code=400,
            detail=f"No {broker_id} connection found. Please connect first.",
        )

    try:
        broker = get_broker(broker_id)

        if broker.is_token_expired(token_data):
            raise HTTPException(
                status_code=401,
                detail=f"{broker.BROKER_NAME} token expired. Please reconnect.",
                headers={"X-Token-Expired": "true"},
            )

        logger.info(f"[broker] Syncing {broker_id} holdings for {user_id}")
        holdings = await broker.fetch_holdings(token_data)
        funds    = await broker.fetch_funds(token_data)

        holdings_list = [h.to_dict() for h in holdings]
        await memory.upsert_user_profile(user_id, {
            "portfolio.holdings":      holdings_list,
            "portfolio.broker_synced": broker_id,
            "portfolio.last_synced":   time.time(),
        })

        from utils.market_data import compute_portfolio_summary
        summary_data = await compute_portfolio_summary(holdings_list)
        await memory.save_portfolio_snapshot(user_id, {
            "broker": broker_id,
            "holdings_count": len(holdings_list),
            **summary_data.get("summary", {}),
        })

        return {
            "status":         "synced",
            "broker":         broker_id,
            "holdings_count": len(holdings_list),
            "total_value":    summary_data.get("summary", {}).get("total_value", 0),
            "available_cash": funds.get("available_cash", 0),
            "synced_at":      time.time(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[broker] Sync error {broker_id}/{user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.delete("/{user_id}/{broker_id}")
async def disconnect_broker(user_id: str, broker_id: str):
    """Remove stored broker credentials for this user."""
    try:
        get_broker(broker_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await memory.remove_broker_connection(user_id, broker_id)
    return {"status": "disconnected", "broker": broker_id}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _state_error_page() -> str:
    """Minimal HTML error page shown when Zerodha state token is missing/expired."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
      <title>Zerodha Login Error — Boardroom AI</title>
      <style>
        body { font-family: monospace; background: #030712; color: #9ca3af;
               display: flex; align-items: center; justify-content: center; min-height: 100vh; }
        .box { border: 1px solid #374151; border-radius: 12px; padding: 32px; max-width: 480px; }
        h2 { color: #f59e0b; margin-top: 0; }
        a { color: #f59e0b; }
        code { background: #111827; padding: 2px 6px; border-radius: 4px; }
      </style>
    </head>
    <body>
      <div class="box">
        <h2>⚠ Login State Expired</h2>
        <p>The Zerodha login session expired (state token is older than 5 minutes) or was invalid.</p>
        <p>This usually happens when:</p>
        <ul>
          <li>You took too long to complete the Zerodha login</li>
          <li>The login URL was opened from a different browser session</li>
        </ul>
        <p>
          <a href="http://localhost:3000/portfolio">← Go back to Portfolio</a>
          and click <strong>Login with Zerodha</strong> again.
        </p>
      </div>
    </body>
    </html>
    """
