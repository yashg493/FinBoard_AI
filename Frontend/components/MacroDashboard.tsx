// components/MacroDashboard.tsx
// Compact macro indicator panel shown in the right sidebar

import { useEffect, useState } from "react";

interface MacroIndicator {
  label: string;
  value: string;
  change?: string;
  direction?: "up" | "down" | "flat";
  status?: "good" | "warn" | "bad" | "neutral";
}

const STATUS_COLOR: Record<string, string> = {
  good:    "text-green-400",
  warn:    "text-amber-400",
  bad:     "text-red-400",
  neutral: "text-gray-400",
};

const DIRECTION_ICON: Record<string, string> = {
  up:   "↑",
  down: "↓",
  flat: "→",
};

// Mock snapshot — replace with /api/macro endpoint in production
function getMockMacro(): MacroIndicator[] {
  return [
    { label: "RBI Repo Rate",    value: "6.50%",     change: "On hold",   direction: "flat", status: "neutral" },
    { label: "CPI Inflation",    value: "5.48%",     change: "↓ declining", direction: "down", status: "warn" },
    { label: "Nifty 50",         value: "24,100",    change: "-2.3% (1M)", direction: "down", status: "warn" },
    { label: "India VIX",        value: "13.5",      change: "Low vol",   direction: "flat", status: "good" },
    { label: "CMIE Unemployment",value: "8.1%",      change: "Stable",    direction: "flat", status: "warn" },
    { label: "GDP Growth",       value: "7.3%",      change: "Moderating",direction: "down", status: "good" },
    { label: "USD / INR",        value: "₹84.50",    change: "-1.8% YTD", direction: "down", status: "warn" },
    { label: "Brent Crude",      value: "$81.5",     change: "Stable",    direction: "flat", status: "neutral" },
  ];
}

export default function MacroDashboard() {
  const [indicators, setIndicators] = useState<MacroIndicator[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  useEffect(() => {
    setIndicators(getMockMacro());
    setLastUpdated(new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }));
  }, []);

  return (
    <div className="mt-4 pt-4 border-t border-gray-800">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-gray-500 uppercase tracking-wider">Macro Snapshot</span>
        {lastUpdated && (
          <span className="text-xs text-gray-700">{lastUpdated}</span>
        )}
      </div>

      <div className="space-y-1.5">
        {indicators.map((ind) => (
          <div key={ind.label} className="flex items-center justify-between gap-2">
            <span className="text-xs text-gray-600 truncate flex-1">{ind.label}</span>
            <div className="flex items-center gap-1.5 shrink-0">
              {ind.direction && (
                <span className={`text-xs ${
                  ind.direction === "up"   ? "text-green-500" :
                  ind.direction === "down" ? "text-red-500" : "text-gray-600"
                }`}>
                  {DIRECTION_ICON[ind.direction]}
                </span>
              )}
              <span className={`text-xs font-mono font-medium ${STATUS_COLOR[ind.status ?? "neutral"]}`}>
                {ind.value}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* India market session indicator */}
      <div className="mt-3 pt-2.5 border-t border-gray-800/60 flex items-center gap-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
        <span className="text-xs text-gray-600">NSE/BSE market open</span>
      </div>
    </div>
  );
}
