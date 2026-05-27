// components/BrokerConnect.tsx
// Dynamic, registry-driven broker connection UI.
// Auto-renders a card for every broker returned by /api/broker/list.
// Adding a new broker to the backend registry automatically adds a card here.
//
// Auth flows supported:
//   "token"  → User pastes API token (INDstocks)
//   "oauth"  → OAuth redirect (Zerodha Kite Connect, Upstox)
//
// Plus a universal CSV import fallback (free, no API key needed).

import { useCallback, useEffect, useState } from "react";
import CSVImport from "./CSVImport";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const USER_ID = "user_yash_001";

// ─── Types ────────────────────────────────────────────────────────────────────

interface BrokerMeta {
  broker_id:   string;
  broker_name: string;
  broker_logo: string;
  auth_type:   "token" | "oauth";
}

interface BrokerConnectionStatus {
  connected:    boolean;
  user_name:    string;
  connected_at: number;
  is_expired:   boolean;
}

type StatusMap = Record<string, BrokerConnectionStatus>;

// ─── Static broker UI config (logos, colors, fees, instructions) ─────────────

interface BrokerUIConfig {
  color:        string;   // Tailwind border/text color stem
  badge?:       string;   // e.g. "Free" | "₹2000 one-time"
  badgeColor?:  string;
  tokenHelp?:   { label: string; url: string; steps: string[] };
  oauthNote?:   string;
}

const BROKER_UI: Record<string, BrokerUIConfig> = {
  indstocks: {
    color:      "blue",
    badge:      "Free",
    badgeColor: "text-green-400 border-green-800 bg-green-950/20",
    tokenHelp: {
      label: "indstocks.com/app/api-trading",
      url:   "https://indstocks.com/app/api-trading",
      steps: [
        "Open indstocks.com/app/api-trading",
        "Log in to your INDstocks account",
        'Click "Generate Token"',
        "Copy and paste the token below",
      ],
    },
  },
  zerodha: {
    color:      "orange",
    badge:      "Free (Personal)",
    badgeColor: "text-green-400 border-green-800 bg-green-950/20",
    oauthNote:  "Create a 'Personal' app at developers.kite.trade for free portfolio sync.",
  },
  upstox: {
    color:      "purple",
    badge:      "Free API",
    badgeColor: "text-green-400 border-green-800 bg-green-950/20",
    oauthNote:  "Free developer API. Create an app at account.upstox.com/developer/apps.",
  },
};

// ─── Helper: fetch with JSON ──────────────────────────────────────────────────

async function apiFetch(url: string, options?: RequestInit) {
  const res  = await fetch(url, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`);
  return data;
}

// ─── Token Auth Card (INDstocks-style) ───────────────────────────────────────

function TokenBrokerCard({
  meta, status, uiConfig, onRefresh,
}: {
  meta:     BrokerMeta;
  status?:  BrokerConnectionStatus;
  uiConfig: BrokerUIConfig;
  onRefresh: () => void;
}) {
  const [token, setToken]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [syncing, setSyncing]     = useState(false);
  const [error, setError]         = useState("");
  const [success, setSuccess]     = useState("");
  const [showInput, setShowInput] = useState(false);
  const c = uiConfig.color;

  const isConnected = status?.connected && !status?.is_expired;
  const isExpired   = status?.connected && status?.is_expired;

  async function handleConnect() {
    if (!token.trim()) { setError("Please paste your API token."); return; }
    setLoading(true); setError(""); setSuccess("");
    try {
      const data = await apiFetch(
        `${API_URL}/api/broker/${USER_ID}/${meta.broker_id}/connect`,
        { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: token.trim() }) },
      );
      setSuccess(`✓ Connected as ${data.user_name}`);
      setToken(""); setShowInput(false);
      onRefresh();
      // Auto-sync
      await handleSync(true);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }

  async function handleSync(silent = false) {
    setSyncing(true);
    if (!silent) { setError(""); setSuccess(""); }
    try {
      const data = await apiFetch(
        `${API_URL}/api/broker/${USER_ID}/${meta.broker_id}/sync`,
        { method: "POST" },
      );
      if (!silent) setSuccess(`✓ Synced ${data.holdings_count} holdings`);
      onRefresh();
    } catch (e: any) {
      if (e.message.includes("expired")) {
        setError("Token expired — paste a new token below.");
        setShowInput(true);
      } else { setError(e.message); }
    }
    setSyncing(false);
  }

  async function handleDisconnect() {
    await apiFetch(`${API_URL}/api/broker/${USER_ID}/${meta.broker_id}`, { method: "DELETE" });
    onRefresh();
  }

  return (
    <BrokerCardShell
      meta={meta} uiConfig={uiConfig} status={status}
      isConnected={isConnected} isExpired={isExpired}
    >
      {/* Connected info */}
      {isConnected && !showInput && (
        <p className="text-xs text-gray-400 mb-3">
          Logged in as <span className="text-gray-200 font-medium">{status?.user_name}</span>{" "}
          ·{" "}
          <button onClick={() => setShowInput(true)} className={`text-${c}-400 hover:underline`}>
            Refresh token
          </button>
        </p>
      )}

      {/* Expired warning */}
      {isExpired && !showInput && (
        <p className="text-xs text-orange-400 mb-3">
          Token expired.{" "}
          <button onClick={() => setShowInput(true)} className="underline">
            Paste a new token
          </button>
        </p>
      )}

      {/* Token Input */}
      {(showInput || !isConnected) && uiConfig.tokenHelp && (
        <div className="mb-3 space-y-2">
          <ol className="space-y-1">
            {uiConfig.tokenHelp.steps.map((s, i) => (
              <li key={i} className="text-xs text-gray-500 flex gap-1.5">
                <span className={`text-${c}-600 shrink-0`}>{i + 1}.</span>{s}
              </li>
            ))}
          </ol>
          <a href={uiConfig.tokenHelp.url} target="_blank" rel="noopener noreferrer"
            className={`text-xs text-${c}-400 hover:underline block`}>
            ↗ {uiConfig.tokenHelp.label}
          </a>
          <input
            type="text" value={token} onChange={(e) => setToken(e.target.value)}
            placeholder={`Paste your ${meta.broker_name} API token…`}
            className={`w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs
                       text-gray-200 placeholder-gray-600 font-mono
                       focus:outline-none focus:border-${c}-600`}
          />
        </div>
      )}

      {error   && <p className="text-xs text-red-400 mb-2">{error}</p>}
      {success && <p className="text-xs text-green-400 mb-2">{success}</p>}

      {/* Action buttons */}
      <div className="flex gap-2">
        {(showInput || !isConnected) && (
          <button onClick={handleConnect} disabled={loading}
            className={`flex-1 py-2 bg-${c}-600 hover:bg-${c}-500 disabled:opacity-50
                       text-white text-xs font-medium rounded-lg transition-colors`}>
            {loading ? "Connecting…" : `Connect ${meta.broker_name}`}
          </button>
        )}
        {isConnected && !showInput && (
          <>
            <button onClick={() => handleSync()} disabled={syncing}
              className={`flex-1 py-2 bg-${c}-600/20 hover:bg-${c}-600/30 border border-${c}-700
                         text-${c}-400 text-xs font-medium rounded-lg transition-colors`}>
              {syncing ? "Syncing…" : "↻ Sync Holdings"}
            </button>
            <button onClick={handleDisconnect}
              className="px-3 py-2 border border-gray-700 text-gray-500 hover:text-red-400
                         hover:border-red-800 text-xs rounded-lg transition-colors">
              Disconnect
            </button>
          </>
        )}
      </div>
    </BrokerCardShell>
  );
}

// ─── OAuth Card (Zerodha / Upstox) ───────────────────────────────────────────

function OAuthBrokerCard({
  meta, status, uiConfig, onRefresh,
}: {
  meta:     BrokerMeta;
  status?:  BrokerConnectionStatus;
  uiConfig: BrokerUIConfig;
  onRefresh: () => void;
}) {
  const [loginUrl, setLoginUrl] = useState("");
  const [syncing, setSyncing]   = useState(false);
  const [error, setError]       = useState("");
  const [success, setSuccess]   = useState("");
  const c = uiConfig.color;

  const isConnected = status?.connected && !status?.is_expired;
  const isExpired   = status?.connected && status?.is_expired;

  useEffect(() => {
    apiFetch(`${API_URL}/api/broker/${meta.broker_id}/login-url?user_id=${USER_ID}`)
      .then((d) => setLoginUrl(d.login_url ?? ""))
      .catch(() => setLoginUrl(""));
  }, [meta.broker_id]);

  async function handleSync() {
    setSyncing(true); setError(""); setSuccess("");
    try {
      const data = await apiFetch(
        `${API_URL}/api/broker/${USER_ID}/${meta.broker_id}/sync`,
        { method: "POST" },
      );
      setSuccess(`✓ Synced ${data.holdings_count} holdings`);
      onRefresh();
    } catch (e: any) { setError(e.message); }
    setSyncing(false);
  }

  async function handleDisconnect() {
    await apiFetch(`${API_URL}/api/broker/${USER_ID}/${meta.broker_id}`, { method: "DELETE" });
    onRefresh();
  }

  return (
    <BrokerCardShell
      meta={meta} uiConfig={uiConfig} status={status}
      isConnected={isConnected} isExpired={isExpired}
    >
      {/* Note / instructions */}
      <p className="text-xs text-gray-500 leading-relaxed mb-3">
        {isConnected
          ? <>Logged in as <span className="text-gray-200">{status?.user_name}</span> · Session expires daily at midnight IST</>
          : isExpired
          ? <span className="text-orange-400">Session expired. Please re-login below.</span>
          : uiConfig.oauthNote}
      </p>

      {error   && <p className="text-xs text-red-400 mb-2">{error}</p>}
      {success && <p className="text-xs text-green-400 mb-2">{success}</p>}

      <div className="flex gap-2">
        {(!isConnected || isExpired) && (
          <a href={loginUrl || "#"}
            onClick={(e) => !loginUrl && e.preventDefault()}
            className={`flex-1 py-2 text-center rounded-lg text-xs font-medium transition-colors
              ${loginUrl
                ? `bg-${c}-600 hover:bg-${c}-500 text-white`
                : "bg-gray-800 text-gray-500 cursor-not-allowed"}`}>
            {loginUrl ? `🔑 Login with ${meta.broker_name}` : "Set API keys in .env first"}
          </a>
        )}
        {isConnected && (
          <>
            <button onClick={handleSync} disabled={syncing}
              className={`flex-1 py-2 bg-${c}-600/20 hover:bg-${c}-600/30 border border-${c}-700
                         text-${c}-400 text-xs font-medium rounded-lg transition-colors`}>
              {syncing ? "Syncing…" : "↻ Sync Holdings"}
            </button>
            <a href={loginUrl || "#"}
              className={`px-3 py-2 border border-${c}-800 text-${c}-500 text-xs
                         rounded-lg transition-colors text-center hover:text-${c}-300`}>
              Re-login
            </a>
            <button onClick={handleDisconnect}
              className="px-3 py-2 border border-gray-700 text-gray-500 hover:text-red-400
                         hover:border-red-800 text-xs rounded-lg transition-colors">
              ✕
            </button>
          </>
        )}
      </div>
    </BrokerCardShell>
  );
}

// ─── Shared card shell ────────────────────────────────────────────────────────

function BrokerCardShell({
  meta, uiConfig, status, isConnected, isExpired, children,
}: {
  meta:        BrokerMeta;
  uiConfig:    BrokerUIConfig;
  status?:     BrokerConnectionStatus;
  isConnected: boolean;
  isExpired:   boolean;
  children:    React.ReactNode;
}) {
  const c = uiConfig.color;
  const borderClass = isConnected
    ? `border-${c}-700 bg-${c}-950/20`
    : isExpired
    ? "border-orange-800 bg-orange-950/10"
    : "border-gray-700 bg-gray-900/40";

  return (
    <div className={`border rounded-2xl p-5 transition-all ${borderClass}`}>
      {/* Header row */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl bg-${c}-700 flex items-center justify-center
                          text-lg font-bold text-white shrink-0`}>
            {meta.broker_logo}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-200">{meta.broker_name}</h3>
            <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
              <span className="text-xs text-gray-600 capitalize">{meta.auth_type} auth</span>
              {uiConfig.badge && (
                <span className={`text-xs px-1.5 py-0.5 border rounded ${uiConfig.badgeColor}`}>
                  {uiConfig.badge}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Status pill */}
        <div className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded-full border shrink-0 ${
          isConnected
            ? "text-green-400 border-green-800 bg-green-950/20"
            : isExpired
            ? "text-orange-400 border-orange-800 bg-orange-950/20"
            : "text-gray-500 border-gray-700"
        }`}>
          <div className={`w-1.5 h-1.5 rounded-full ${
            isConnected ? "bg-green-400 animate-pulse" : isExpired ? "bg-orange-400" : "bg-gray-600"
          }`} />
          {isConnected ? "Connected" : isExpired ? "Expired" : "Not connected"}
        </div>
      </div>

      {children}
    </div>
  );
}

// ─── Main BrokerConnect Component ─────────────────────────────────────────────

interface BrokerConnectProps {
  onHoldingsSynced: () => void;
}

export default function BrokerConnect({ onHoldingsSynced }: BrokerConnectProps) {
  const [brokers,  setBrokers]  = useState<BrokerMeta[]>([]);
  const [statuses, setStatuses] = useState<StatusMap>({});
  const [loading,  setLoading]  = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      const [bData, sData] = await Promise.all([
        apiFetch(`${API_URL}/api/broker/list`),
        apiFetch(`${API_URL}/api/broker/${USER_ID}/status`),
      ]);
      setBrokers(bData.brokers ?? []);
      setStatuses(sData.connections ?? {});
    } catch {
      setBrokers([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  function handleRefresh() {
    fetchAll();
    onHoldingsSynced();
  }

  const connectedCount = Object.values(statuses).filter(
    (s) => s.connected && !s.is_expired
  ).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <div key={i} className="w-2 h-2 bg-amber-500 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 150}ms` }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-gray-300">Connect Your Broker</h2>
          <p className="text-xs text-gray-600 mt-0.5">
            Auto-sync your demat holdings for real-time AI analysis · Read-only · No trading
          </p>
        </div>
        {connectedCount > 0 && (
          <span className="text-xs px-2.5 py-1 bg-green-950/30 border border-green-800
                           text-green-400 rounded-full">
            {connectedCount} broker{connectedCount > 1 ? "s" : ""} connected
          </span>
        )}
      </div>

      {/* Dynamic broker cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {brokers.map((broker) => {
          const uiConfig = BROKER_UI[broker.broker_id] ?? {
            color:      "amber",
            badge:      "",
            oauthNote:  "Connect your broker account to sync holdings.",
          };

          return broker.auth_type === "token" ? (
            <TokenBrokerCard
              key={broker.broker_id}
              meta={broker}
              status={statuses[broker.broker_id]}
              uiConfig={uiConfig}
              onRefresh={handleRefresh}
            />
          ) : (
            <OAuthBrokerCard
              key={broker.broker_id}
              meta={broker}
              status={statuses[broker.broker_id]}
              uiConfig={uiConfig}
              onRefresh={handleRefresh}
            />
          );
        })}
      </div>

      {/* Divider */}
      <div className="flex items-center gap-3">
        <div className="flex-1 border-t border-gray-800" />
        <span className="text-xs text-gray-700 shrink-0 px-2">
          or import manually (free · works with any broker)
        </span>
        <div className="flex-1 border-t border-gray-800" />
      </div>

      {/* CSV Import */}
      <div className="border border-gray-800 rounded-2xl p-5 bg-gray-900/30">
        <CSVImport onImported={handleRefresh} />
      </div>

      {/* Security note */}
      <div className="border border-gray-800/60 rounded-xl p-3">
        <p className="text-xs text-gray-600 leading-relaxed">
          <span className="text-gray-500 font-medium">🔒 Security:</span>{" "}
          Credentials are stored in your MongoDB instance only. FinBoard AI is read-only —
          no orders are ever placed on your behalf. Kite/Upstox tokens expire daily; INDstocks tokens last 24h.
        </p>
      </div>
    </div>
  );
}
