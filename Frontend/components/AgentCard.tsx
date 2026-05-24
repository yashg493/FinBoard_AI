// components/AgentCard.tsx
// Sidebar card showing each agent's live status and last message

interface AgentCardProps {
  name: string;
  icon: string;
  role: string;
  isActive: boolean;
  lastMessage?: string;
}

const AGENT_ACCENT: Record<string, string> = {
  "Sentinel Agent":   "border-blue-800 bg-blue-950/20",
  "Investment Agent": "border-green-800 bg-green-950/20",
  "Risk Agent":       "border-red-800 bg-red-950/20",
  "Tax Agent":        "border-purple-800 bg-purple-950/20",
  "Orchestrator":     "border-amber-700 bg-amber-950/20",
};

const AGENT_DOT: Record<string, string> = {
  "Sentinel Agent":   "bg-blue-400",
  "Investment Agent": "bg-green-400",
  "Risk Agent":       "bg-red-400",
  "Tax Agent":        "bg-purple-400",
  "Orchestrator":     "bg-amber-400",
};

const AGENT_TEXT: Record<string, string> = {
  "Sentinel Agent":   "text-blue-300",
  "Investment Agent": "text-green-300",
  "Risk Agent":       "text-red-300",
  "Tax Agent":        "text-purple-300",
  "Orchestrator":     "text-amber-300",
};

export default function AgentCard({ name, icon, role, isActive, lastMessage }: AgentCardProps) {
  const accent = AGENT_ACCENT[name] ?? "border-gray-800 bg-gray-900/20";
  const dot    = AGENT_DOT[name]    ?? "bg-gray-500";
  const text   = AGENT_TEXT[name]   ?? "text-gray-300";

  return (
    <div
      className={`border rounded-lg p-3 transition-all duration-300 ${
        isActive ? accent : "border-gray-800 bg-transparent"
      }`}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="text-base leading-none">{icon}</span>
        <span className={`text-xs font-medium flex-1 truncate ${isActive ? text : "text-gray-400"}`}>
          {name}
        </span>
        <div className={`w-1.5 h-1.5 rounded-full shrink-0 transition-all ${
          isActive ? `${dot} animate-pulse` : "bg-gray-700"
        }`} />
      </div>

      <p className="text-xs text-gray-600 mb-1">{role}</p>

      {lastMessage && isActive && (
        <p className="text-xs text-gray-400 truncate leading-relaxed border-t border-gray-800 pt-1 mt-1">
          {lastMessage.length > 60 ? lastMessage.slice(0, 58) + "…" : lastMessage}
        </p>
      )}

      {!isActive && (
        <p className="text-xs text-gray-700 italic">Standby</p>
      )}
    </div>
  );
}
