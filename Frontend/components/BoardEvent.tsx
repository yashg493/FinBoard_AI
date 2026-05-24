// components/BoardEvent.tsx
import { BoardEventData } from "../pages/boardroom";

const AGENT_COLORS: Record<string, string> = {
  "Sentinel Agent": "text-blue-400 border-blue-800",
  "Investment Agent": "text-green-400 border-green-800",
  "Risk Agent": "text-red-400 border-red-800",
  "Tax Agent": "text-purple-400 border-purple-800",
  "Orchestrator": "text-amber-400 border-amber-800",
  "Board": "text-gray-400 border-gray-700",
  "System": "text-gray-500 border-gray-800",
};

const AGENT_ICONS: Record<string, string> = {
  "Sentinel Agent": "👁",
  "Investment Agent": "📈",
  "Risk Agent": "🛡",
  "Tax Agent": "📊",
  "Orchestrator": "⚖",
  "Board": "🏛",
};

export default function BoardEvent({ event }: { event: BoardEventData }) {
  const colorClass = AGENT_COLORS[event.agent] || "text-gray-400 border-gray-700";
  const icon = AGENT_ICONS[event.agent] || "•";
  const isThinking = event.type === "agent_thinking";
  const isConsensus = event.type === "consensus";
  const isDebate = event.debate;
  const isPhase = event.type === "phase_start" || event.type === "debate_start";

  if (isPhase) {
    return (
      <div className="text-center py-2">
        <span className="text-xs text-gray-600 border border-gray-800 px-3 py-1 rounded-full">
          {event.message}
        </span>
      </div>
    );
  }

  if (isConsensus) {
    return (
      <div className="border border-amber-700 bg-amber-950/30 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-amber-400 text-sm font-semibold">⚖ Orchestrator — Consensus Reached</span>
        </div>
        <p className="text-amber-100 text-sm leading-relaxed">{event.message}</p>
        {event.data?.actions && (
          <div className="mt-3 space-y-1">
            <p className="text-xs text-amber-600 uppercase tracking-wider mb-2">Priority Actions</p>
            {(event.data.actions as Array<Record<string, string>>)
              .slice(0, 5)
              .map((action, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-amber-200">
                  <span className={`mt-0.5 px-1.5 py-0.5 rounded text-xs font-medium
                    ${action.urgency === "IMMEDIATE" ? "bg-red-900 text-red-300" :
                      action.urgency === "THIS_WEEK" ? "bg-orange-900 text-orange-300" :
                      "bg-gray-800 text-gray-400"}`}>
                    {action.urgency || "T" + (i + 1)}
                  </span>
                  <span>{action.action}</span>
                </div>
              ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`flex gap-3 ${isDebate ? "ml-6" : ""}`}>
      <div className={`mt-1 text-base shrink-0 ${isThinking ? "opacity-50" : ""}`}>
        {icon}
      </div>
      <div className={`flex-1 border-l-2 pl-3 ${colorClass}`}>
        <div className="flex items-center gap-2 mb-0.5">
          <span className={`text-xs font-semibold ${colorClass.split(" ")[0]}`}>
            {event.agent}
          </span>
          {event.simulation && (
            <span className="text-xs text-blue-500 border border-blue-800 px-1.5 rounded">SIM</span>
          )}
          {isThinking && (
            <span className="flex gap-0.5">
              <span className="w-1 h-1 bg-gray-500 rounded-full animate-bounce [animation-delay:0ms]" />
              <span className="w-1 h-1 bg-gray-500 rounded-full animate-bounce [animation-delay:150ms]" />
              <span className="w-1 h-1 bg-gray-500 rounded-full animate-bounce [animation-delay:300ms]" />
            </span>
          )}
        </div>
        <p className={`text-sm leading-relaxed ${isThinking ? "text-gray-600 italic" : "text-gray-200"}`}>
          {event.message}
        </p>
        {event.data?.confidence !== undefined && (
          <div className="mt-1 flex items-center gap-2">
            <div className="h-0.5 flex-1 bg-gray-800 rounded">
              <div
                className="h-0.5 bg-current rounded transition-all"
                style={{ width: `${Number(event.data.confidence) * 100}%` }}
              />
            </div>
            <span className="text-xs text-gray-600">
              {(Number(event.data.confidence) * 100).toFixed(0)}% confidence
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
