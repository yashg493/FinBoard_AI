// components/SimulationPanel.tsx
// Economic shock simulation panel — lets user pick and run scenarios

import { useState } from "react";
import { BoardEventData } from "../pages/boardroom";
import BoardEvent from "./BoardEvent";

interface SimulationPanelProps {
  onTrigger: (scenario: string) => void;
  isRunning: boolean;
  events: BoardEventData[];
}

interface Scenario {
  id: string;
  title: string;
  description: string;
  icon: string;
  severity: "HIGH" | "CRITICAL" | "MEDIUM";
  triggers: string[];
}

const SCENARIOS: Scenario[] = [
  {
    id: "india_recession",
    title: "India Recession",
    description: "GDP contracts -1.5%, unemployment spikes to 14.5%, Nifty crashes 15%",
    icon: "📉",
    severity: "CRITICAL",
    triggers: ["Job loss", "EMI stress", "Portfolio drawdown", "Emergency fund depletion"],
  },
  {
    id: "rate_hike",
    title: "RBI Emergency Rate Hike +100bps",
    description: "Inflation hits 8.2%, RBI hikes rates to 7.5%, bond yields surge to 8.8%",
    icon: "📈",
    severity: "HIGH",
    triggers: ["Debt fund losses", "EMI increase", "Equity correction", "FD opportunity"],
  },
  {
    id: "market_crash",
    title: "Market Crash -30%",
    description: "Global risk-off: Nifty falls 30% in 3 months, FIIs pull out ₹1L crore",
    icon: "💥",
    severity: "CRITICAL",
    triggers: ["SIP pause decision", "Rebalancing trigger", "Buying opportunity", "Tax-loss harvesting"],
  },
  {
    id: "job_loss",
    title: "Tech Sector Layoffs",
    description: "Mass layoffs in IT sector, 6-month income gap, startup slowdown",
    icon: "🏢",
    severity: "HIGH",
    triggers: ["Emergency fund burn", "SIP continuity", "Expense reduction", "EMI holiday"],
  },
  {
    id: "inflation_spike",
    title: "Inflation Spike to 10%",
    description: "Food inflation at 15%, fuel prices surge, purchasing power erosion",
    icon: "🔥",
    severity: "HIGH",
    triggers: ["Real returns negative", "Gold allocation", "TIPS equivalent", "Budget rebalance"],
  },
  {
    id: "custom",
    title: "Custom Scenario",
    description: "Describe your own scenario for the agents to analyze",
    icon: "⚙",
    severity: "MEDIUM",
    triggers: [],
  },
];

const SEVERITY_STYLE: Record<string, string> = {
  CRITICAL: "border-red-800 bg-red-950/20 text-red-400",
  HIGH:     "border-orange-800 bg-orange-950/20 text-orange-400",
  MEDIUM:   "border-gray-700 bg-gray-800/20 text-gray-400",
};

export default function SimulationPanel({ onTrigger, isRunning, events }: SimulationPanelProps) {
  const [selected, setSelected] = useState<string | null>(null);
  const [customText, setCustomText] = useState("");
  const [hasRun, setHasRun] = useState(false);

  const simEvents = events.filter((e) => e.simulation);

  function runScenario(scenario: Scenario) {
    if (isRunning) return;
    const scenarioText = scenario.id === "custom" ? customText : scenario.id;
    if (!scenarioText.trim()) return;
    setSelected(scenario.id);
    setHasRun(true);
    onTrigger(scenarioText);
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <h2 className="text-white font-medium mb-1">Economic Shock Simulation</h2>
        <p className="text-sm text-gray-500">
          Pick a scenario below. The full AI board will analyze its impact on your finances in real time.
        </p>
      </div>

      {/* Scenario Grid */}
      {!hasRun && (
        <div className="grid grid-cols-2 gap-3 mb-6">
          {SCENARIOS.map((scenario) => (
            <button
              key={scenario.id}
              onClick={() => scenario.id !== "custom" ? setSelected(scenario.id) : setSelected("custom")}
              disabled={isRunning}
              className={`text-left border rounded-lg p-4 transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                selected === scenario.id
                  ? SEVERITY_STYLE[scenario.severity]
                  : "border-gray-800 hover:border-gray-600 bg-transparent"
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <span className="text-xl">{scenario.icon}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded border ${SEVERITY_STYLE[scenario.severity]}`}>
                  {scenario.severity}
                </span>
              </div>
              <p className="text-sm font-medium text-gray-200 mb-1">{scenario.title}</p>
              <p className="text-xs text-gray-500 leading-snug">{scenario.description}</p>

              {scenario.triggers.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {scenario.triggers.slice(0, 3).map((t) => (
                    <span key={t} className="text-xs text-gray-600 border border-gray-800 rounded px-1.5 py-0.5">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Custom scenario input */}
      {selected === "custom" && !hasRun && (
        <div className="mb-4">
          <textarea
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            placeholder='e.g. "India enters stagflation with 9% inflation and -1% GDP growth for 2 years"'
            className="w-full bg-gray-900 border border-gray-700 rounded-lg p-3 text-sm text-gray-200 placeholder-gray-600 resize-none h-20 focus:outline-none focus:border-amber-600"
          />
        </div>
      )}

      {/* Run Button */}
      {selected && !hasRun && (
        <div className="mb-6">
          <button
            onClick={() => {
              const scenario = SCENARIOS.find((s) => s.id === selected);
              if (scenario) runScenario(scenario);
            }}
            disabled={isRunning || (selected === "custom" && !customText.trim())}
            className="w-full py-2.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-40 disabled:cursor-not-allowed text-black font-medium rounded-lg text-sm transition-colors"
          >
            {isRunning ? "Simulation running..." : `Run Simulation — ${SCENARIOS.find(s => s.id === selected)?.title}`}
          </button>
        </div>
      )}

      {/* Reset */}
      {hasRun && !isRunning && (
        <button
          onClick={() => { setHasRun(false); setSelected(null); setCustomText(""); }}
          className="mb-4 text-xs text-amber-500 hover:text-amber-400 border border-amber-800/50 rounded px-3 py-1.5 transition-colors"
        >
          ← Run another simulation
        </button>
      )}

      {/* Simulation Events */}
      {simEvents.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs text-gray-600 uppercase tracking-wider">
            Simulation: {SCENARIOS.find((s) => s.id === selected)?.title ?? selected}
          </p>
          {simEvents.map((event, i) => (
            <BoardEvent key={i} event={event} />
          ))}
        </div>
      )}
    </div>
  );
}
