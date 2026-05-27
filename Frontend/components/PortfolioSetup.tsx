// components/PortfolioSetup.tsx
// Form to add, edit, and delete individual stock/MF holdings
// Uses NSE ticker autocomplete from /api/market/tickers

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Holding {
  symbol: string;
  name?: string;
  quantity: number;
  avg_cost: number;
  asset_type: string;
  sector?: string;
}

interface TickerOption {
  symbol: string;
  name: string;
  sector: string;
}

interface PortfolioSetupProps {
  userId: string;
  existingHoldings: Holding[];
  onSaved: () => void;
}

const ASSET_TYPES = ["equity", "mf", "etf", "sgb", "fd", "other"];

function HoldingRow({
  holding,
  onDelete,
}: {
  holding: Holding;
  onDelete: (symbol: string) => void;
}) {
  return (
    <div className="flex items-center gap-2 py-2 border-b border-gray-800/60 group">
      <div className="flex-1 min-w-0">
        <span className="text-sm font-medium text-gray-200">{holding.symbol}</span>
        {holding.name && (
          <span className="text-xs text-gray-600 ml-2 truncate hidden sm:inline">{holding.name}</span>
        )}
      </div>
      <span className="text-xs text-gray-500 w-16 text-right font-mono">{holding.quantity} units</span>
      <span className="text-xs text-gray-500 w-24 text-right font-mono">₹{holding.avg_cost.toLocaleString("en-IN")}</span>
      <span className="text-xs px-2 py-0.5 bg-gray-800 text-gray-500 rounded w-16 text-center">
        {holding.asset_type}
      </span>
      <button
        onClick={() => onDelete(holding.symbol)}
        className="text-gray-700 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100 text-xs px-2"
      >
        ✕
      </button>
    </div>
  );
}

export default function PortfolioSetup({ userId, existingHoldings, onSaved }: PortfolioSetupProps) {
  const [holdings, setHoldings]           = useState<Holding[]>(existingHoldings);
  const [tickers, setTickers]             = useState<TickerOption[]>([]);
  const [saving, setSaving]               = useState(false);
  const [showForm, setShowForm]           = useState(false);
  const [search, setSearch]               = useState("");
  const [filtered, setFiltered]           = useState<TickerOption[]>([]);

  // New holding form state
  const [symbol, setSymbol]       = useState("");
  const [name, setName]           = useState("");
  const [sector, setSector]       = useState("");
  const [quantity, setQuantity]   = useState("");
  const [avgCost, setAvgCost]     = useState("");
  const [assetType, setAssetType] = useState("equity");
  const [formError, setFormError] = useState("");

  useEffect(() => {
    setHoldings(existingHoldings);
  }, [existingHoldings]);

  useEffect(() => {
    fetch(`${API_URL}/api/market/tickers`)
      .then((r) => r.json())
      .then((d) => setTickers(d.tickers ?? []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!search) { setFiltered([]); return; }
    const q = search.toLowerCase();
    setFiltered(
      tickers
        .filter((t) => t.symbol.toLowerCase().includes(q) || t.name.toLowerCase().includes(q))
        .slice(0, 8)
    );
  }, [search, tickers]);

  function selectTicker(t: TickerOption) {
    setSymbol(t.symbol);
    setName(t.name);
    setSector(t.sector);
    setSearch(`${t.symbol} — ${t.name}`);
    setFiltered([]);
  }

  function resetForm() {
    setSymbol(""); setName(""); setSector(""); setSearch("");
    setQuantity(""); setAvgCost(""); setAssetType("equity");
    setFormError(""); setFiltered([]);
  }

  async function handleAdd() {
    if (!symbol || !quantity || !avgCost) {
      setFormError("Symbol, quantity, and average cost are required.");
      return;
    }
    const newHolding: Holding = {
      symbol: symbol.toUpperCase(),
      name: name || undefined,
      sector: sector || undefined,
      quantity: parseFloat(quantity),
      avg_cost: parseFloat(avgCost),
      asset_type: assetType,
    };

    // Optimistically add to local state
    setHoldings((prev) => {
      const exists = prev.findIndex((h) => h.symbol.toUpperCase() === newHolding.symbol);
      if (exists >= 0) {
        const updated = [...prev];
        updated[exists] = newHolding;
        return updated;
      }
      return [...prev, newHolding];
    });

    // Persist to backend
    try {
      await fetch(`${API_URL}/api/portfolio/${userId}/holdings/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newHolding),
      });
      onSaved();
    } catch {
      setFormError("Failed to save. Please try again.");
    }

    resetForm();
    setShowForm(false);
  }

  async function handleDelete(symbolToDelete: string) {
    setHoldings((prev) => prev.filter((h) => h.symbol !== symbolToDelete));
    try {
      await fetch(`${API_URL}/api/portfolio/${userId}/holdings/${symbolToDelete}`, {
        method: "DELETE",
      });
      onSaved();
    } catch {
      // Rollback optimistic update
      setHoldings(existingHoldings);
    }
  }

  async function handleSaveAll() {
    setSaving(true);
    try {
      await fetch(`${API_URL}/api/portfolio/${userId}/holdings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ holdings }),
      });
      onSaved();
    } catch {
      setFormError("Failed to save holdings.");
    }
    setSaving(false);
  }

  return (
    <div className="space-y-4">
      {/* Holdings List */}
      {holdings.length > 0 ? (
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-gray-500 uppercase tracking-wider">
              Your Holdings ({holdings.length})
            </p>
            <button
              onClick={() => setShowForm(!showForm)}
              className="text-xs px-3 py-1.5 bg-amber-500/10 hover:bg-amber-500/20
                         text-amber-400 border border-amber-800 rounded-lg transition-colors"
            >
              + Add Holding
            </button>
          </div>
          <div className="border border-gray-800 rounded-xl overflow-hidden bg-gray-900/40 px-3">
            {holdings.map((h) => (
              <HoldingRow key={h.symbol} holding={h} onDelete={handleDelete} />
            ))}
          </div>
        </div>
      ) : (
        <div className="text-center py-8 border border-dashed border-gray-800 rounded-xl">
          <div className="text-3xl mb-3">📈</div>
          <p className="text-gray-500 text-sm mb-3">No holdings added yet</p>
          <button
            onClick={() => setShowForm(true)}
            className="text-xs px-4 py-2 bg-amber-500 hover:bg-amber-400 text-black rounded-lg
                       font-medium transition-colors"
          >
            + Add Your First Holding
          </button>
        </div>
      )}

      {/* Add Holding Form */}
      {showForm && (
        <div className="border border-gray-700 rounded-xl p-4 bg-gray-900/60 space-y-3">
          <p className="text-xs text-gray-400 uppercase tracking-wider font-medium">Add / Update Holding</p>

          {/* Ticker Search */}
          <div className="relative">
            <input
              type="text"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setSymbol(""); }}
              placeholder="Search NSE symbol or company name…"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm
                         text-gray-200 placeholder-gray-600 focus:outline-none focus:border-amber-700"
            />
            {filtered.length > 0 && (
              <div className="absolute z-10 top-full left-0 right-0 mt-1 bg-gray-900 border border-gray-700
                              rounded-lg shadow-xl overflow-hidden">
                {filtered.map((t) => (
                  <button
                    key={t.symbol}
                    onClick={() => selectTicker(t)}
                    className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-gray-800
                               text-left transition-colors"
                  >
                    <div>
                      <span className="text-sm font-medium text-gray-200">{t.symbol}</span>
                      <span className="text-xs text-gray-500 ml-2">{t.name}</span>
                    </div>
                    <span className="text-xs text-gray-600">{t.sector}</span>
                  </button>
                ))}
              </div>
            )}
            {/* Manual symbol entry if not in list */}
            {symbol === "" && search && filtered.length === 0 && (
              <button
                onClick={() => { setSymbol(search.toUpperCase()); setFiltered([]); }}
                className="absolute right-2 top-2 text-xs text-amber-500 hover:text-amber-400"
              >
                Use "{search.toUpperCase()}"
              </button>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-600 mb-1 block">Quantity / Units *</label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="e.g. 50"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm
                           text-gray-200 placeholder-gray-600 focus:outline-none focus:border-amber-700"
              />
            </div>
            <div>
              <label className="text-xs text-gray-600 mb-1 block">Avg Buy Price (₹) *</label>
              <input
                type="number"
                value={avgCost}
                onChange={(e) => setAvgCost(e.target.value)}
                placeholder="e.g. 2800"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm
                           text-gray-200 placeholder-gray-600 focus:outline-none focus:border-amber-700"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-gray-600 mb-1 block">Asset Type</label>
            <div className="flex flex-wrap gap-2">
              {ASSET_TYPES.map((t) => (
                <button
                  key={t}
                  onClick={() => setAssetType(t)}
                  className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                    assetType === t
                      ? "border-amber-600 bg-amber-600/20 text-amber-400"
                      : "border-gray-700 text-gray-500 hover:border-gray-600"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {formError && <p className="text-xs text-red-400">{formError}</p>}

          <div className="flex gap-2 pt-1">
            <button
              onClick={handleAdd}
              className="flex-1 py-2 bg-amber-500 hover:bg-amber-400 text-black text-xs font-medium
                         rounded-lg transition-colors"
            >
              + Add to Portfolio
            </button>
            <button
              onClick={() => { setShowForm(false); resetForm(); }}
              className="px-4 py-2 border border-gray-700 text-gray-500 hover:text-gray-300 text-xs
                         rounded-lg transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {formError && !showForm && (
        <p className="text-xs text-red-400">{formError}</p>
      )}
    </div>
  );
}
