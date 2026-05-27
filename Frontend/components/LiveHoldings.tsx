// components/LiveHoldings.tsx
// Real-time holdings table with LTP, P&L, day change — auto-refreshes every 60s

import { useEffect, useState, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Holding {
  symbol: string;
  name?: string;
  quantity: number;
  avg_cost: number;
  asset_type?: string;
  sector?: string;
  // Enriched by backend
  ltp?: number;
  current_value?: number;
  invested_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
  day_pnl?: number;
  day_change_pct?: number;
}

interface Summary {
  total_value: number;
  total_invested: number;
  total_pnl: number;
  total_pnl_pct: number;
  day_pnl: number;
  holdings_count: number;
}

interface LivePortfolioData {
  holdings: Holding[];
  summary: Summary;
}

function fmt(n: number, prefix = "₹") {
  if (!n && n !== 0) return "—";
  const abs = Math.abs(n);
  if (abs >= 10_000_000) return `${prefix}${(n / 10_000_000).toFixed(2)}Cr`;
  if (abs >= 100_000)    return `${prefix}${(n / 100_000).toFixed(2)}L`;
  return `${prefix}${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function PnlCell({ value, pct }: { value: number; pct?: number }) {
  const isPos = value >= 0;
  const color = isPos ? "text-green-400" : "text-red-400";
  return (
    <div className={`text-right ${color}`}>
      <div className="text-xs font-mono">{isPos ? "+" : ""}{fmt(value)}</div>
      {pct !== undefined && (
        <div className="text-xs opacity-70">{isPos ? "+" : ""}{pct.toFixed(2)}%</div>
      )}
    </div>
  );
}

export default function LiveHoldings({ userId }: { userId: string }) {
  const [data, setData]         = useState<LivePortfolioData | null>(null);
  const [loading, setLoading]   = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [error, setError]       = useState<string | null>(null);

  const fetchLive = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/portfolio/${userId}/live`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setLastRefresh(new Date());
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    fetchLive();
    const interval = setInterval(fetchLive, 60_000); // refresh every 60s
    return () => clearInterval(interval);
  }, [fetchLive]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40">
        <div className="flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <div key={i} className="w-2 h-2 bg-amber-500 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 150}ms` }} />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-400 text-sm">Failed to load live prices: {error}</p>
        <button onClick={fetchLive} className="mt-2 text-xs text-amber-400 hover:underline">
          Retry
        </button>
      </div>
    );
  }

  if (!data || data.holdings.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-3xl mb-3">📂</div>
        <p className="text-gray-500 text-sm">No holdings yet.</p>
        <p className="text-gray-700 text-xs mt-1">Add your stocks and mutual funds above.</p>
      </div>
    );
  }

  const { holdings, summary } = data;
  const summaryPnlColor = summary.total_pnl >= 0 ? "text-green-400" : "text-red-400";
  const dayPnlColor     = summary.day_pnl >= 0 ? "text-green-400" : "text-red-400";

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Current Value",  value: fmt(summary.total_value),                    color: "text-white" },
          { label: "Total Invested", value: fmt(summary.total_invested),                  color: "text-gray-300" },
          { label: "Total P&L",      value: `${summary.total_pnl >= 0 ? "+" : ""}${fmt(summary.total_pnl)} (${summary.total_pnl_pct.toFixed(2)}%)`, color: summaryPnlColor },
          { label: "Day P&L",        value: `${summary.day_pnl >= 0 ? "+" : ""}${fmt(summary.day_pnl)}`,                                            color: dayPnlColor },
        ].map((card) => (
          <div key={card.label}
            className="bg-gray-900 border border-gray-800 rounded-xl p-3">
            <p className="text-xs text-gray-600 mb-1">{card.label}</p>
            <p className={`text-sm font-mono font-semibold ${card.color}`}>{card.value}</p>
          </div>
        ))}
      </div>

      {/* Holdings Table */}
      <div className="overflow-x-auto rounded-xl border border-gray-800">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-800 bg-gray-900/50">
              <th className="text-left px-4 py-2.5 text-gray-600 font-medium">Symbol</th>
              <th className="text-right px-4 py-2.5 text-gray-600 font-medium">Qty</th>
              <th className="text-right px-4 py-2.5 text-gray-600 font-medium">Avg Cost</th>
              <th className="text-right px-4 py-2.5 text-gray-600 font-medium">LTP</th>
              <th className="text-right px-4 py-2.5 text-gray-600 font-medium">Curr. Value</th>
              <th className="text-right px-4 py-2.5 text-gray-600 font-medium">P&L</th>
              <th className="text-right px-4 py-2.5 text-gray-600 font-medium">Day</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/60">
            {holdings.map((h) => {
              const ltpColor = (h.ltp ?? 0) >= h.avg_cost ? "text-green-400" : "text-red-400";
              return (
                <tr key={h.symbol}
                  className="hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-200">{h.symbol}</div>
                    {h.name && <div className="text-gray-600 mt-0.5 truncate max-w-[120px]">{h.name}</div>}
                    {h.sector && (
                      <span className="inline-block mt-1 px-1.5 py-0.5 bg-gray-800 text-gray-500 rounded text-xs">
                        {h.sector}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300 font-mono">{h.quantity}</td>
                  <td className="px-4 py-3 text-right text-gray-500 font-mono">₹{h.avg_cost.toLocaleString("en-IN")}</td>
                  <td className={`px-4 py-3 text-right font-mono font-semibold ${ltpColor}`}>
                    {h.ltp ? `₹${h.ltp.toLocaleString("en-IN")}` : "—"}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300 font-mono">
                    {h.current_value ? fmt(h.current_value) : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <PnlCell value={h.unrealized_pnl ?? 0} pct={h.unrealized_pnl_pct} />
                  </td>
                  <td className="px-4 py-3">
                    {h.day_pnl !== undefined
                      ? <PnlCell value={h.day_pnl} pct={h.day_change_pct} />
                      : <span className="text-gray-700 text-xs block text-right">—</span>
                    }
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {lastRefresh && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-700">
            Last updated: {lastRefresh.toLocaleTimeString("en-IN")} · Auto-refreshes every 60s
          </p>
          <button
            onClick={fetchLive}
            className="text-xs text-amber-600 hover:text-amber-400 transition-colors flex items-center gap-1"
          >
            ↻ Refresh now
          </button>
        </div>
      )}
    </div>
  );
}
