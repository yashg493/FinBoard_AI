// components/ConsensusPanel.tsx
// Right sidebar: board consensus output, financial health score, priority actions

import { BoardEventData } from "../pages/boardroom";

interface ConsensusPanelProps {
  event: BoardEventData;
}

type ConsensusAction = {
  tier?: number;
  action?: string;
  domain?: string;
  urgency?: string;
  estimated_impact?: string;
  responsible_agent?: string;
  requires_user_approval?: boolean;
};

const URGENCY_STYLE: Record<string, string> = {
  IMMEDIATE:     "bg-red-900/60 text-red-300 border-red-800",
  THIS_WEEK:     "bg-orange-900/60 text-orange-300 border-orange-800",
  THIS_MONTH:    "bg-yellow-900/60 text-yellow-300 border-yellow-800",
  THIS_QUARTER:  "bg-gray-800 text-gray-400 border-gray-700",
};

const DOMAIN_ICON: Record<string, string> = {
  INVESTMENT:  "📈",
  RISK:        "🛡",
  TAX:         "📊",
  GOVERNANCE:  "⚖",
};

function HealthScore({ score }: { score: number }) {
  const color =
    score >= 75 ? "text-green-400" :
    score >= 50 ? "text-amber-400" :
    score >= 30 ? "text-orange-400" : "text-red-400";

  const barColor =
    score >= 75 ? "bg-green-500" :
    score >= 50 ? "bg-amber-500" :
    score >= 30 ? "bg-orange-500" : "bg-red-500";

  return (
    <div className="mb-4">
      <div className="flex items-baseline gap-2 mb-1.5">
        <span className={`text-3xl font-mono font-bold ${color}`}>{score}</span>
        <span className="text-gray-600 text-sm">/100</span>
        <span className="text-xs text-gray-500 ml-auto">Financial Health</span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${barColor}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

export default function ConsensusPanel({ event }: ConsensusPanelProps) {
  const data = event.data as Record<string, unknown> | undefined;
  const actions = (data?.actions ?? []) as ConsensusAction[];
  const conflicts = (data?.conflicts ?? []) as Array<{ between: string[]; conflict_description: string; resolution: string }>;
  const healthScore = Number(data?.financial_health_score ?? 0);
  const govMode = String(data?.governance_mode ?? "ADVISORY");
  const disagreement = Number(data?.disagreement_score ?? 0);
  const nextReview = String(data?.next_review_trigger ?? "");

  const GOV_STYLE: Record<string, string> = {
    ADVISORY:   "text-blue-400 border-blue-800 bg-blue-950/30",
    COPILOT:    "text-amber-400 border-amber-700 bg-amber-950/30",
    AUTONOMOUS: "text-green-400 border-green-800 bg-green-950/30",
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-gray-500 uppercase tracking-wider">Board Consensus</span>
        <span className={`text-xs px-2 py-0.5 rounded border font-medium ${GOV_STYLE[govMode] ?? GOV_STYLE.ADVISORY}`}>
          {govMode}
        </span>
      </div>

      {/* Health Score */}
      {healthScore > 0 && <HealthScore score={healthScore} />}

      {/* Verdict */}
      <div className="border border-amber-800/50 bg-amber-950/20 rounded-lg p-3">
        <p className="text-xs text-amber-600 mb-1.5 uppercase tracking-wider">Board Verdict</p>
        <p className="text-sm text-amber-100 leading-relaxed">{event.message}</p>
      </div>

      {/* Disagreement Score */}
      {disagreement > 0 && (
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500 shrink-0">Agent disagreement</span>
          <div className="flex gap-0.5 flex-1">
            {Array.from({ length: 10 }).map((_, i) => (
              <div
                key={i}
                className={`flex-1 h-1 rounded-sm ${
                  i < disagreement
                    ? disagreement <= 3 ? "bg-green-600" : disagreement <= 6 ? "bg-amber-500" : "bg-red-500"
                    : "bg-gray-800"
                }`}
              />
            ))}
          </div>
          <span className="text-xs text-gray-400 shrink-0">{disagreement}/10</span>
        </div>
      )}

      {/* Priority Actions */}
      {actions.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Priority Actions</p>
          <div className="space-y-2">
            {actions.slice(0, 6).map((action, i) => {
              const urgency = String(action.urgency ?? "THIS_QUARTER");
              const urgencyStyle = URGENCY_STYLE[urgency] ?? URGENCY_STYLE.THIS_QUARTER;
              const icon = DOMAIN_ICON[String(action.domain ?? "")] ?? "•";
              return (
                <div key={i} className="flex gap-2 items-start">
                  <span className="text-sm mt-0.5 shrink-0">{icon}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-200 leading-snug">{String(action.action ?? "")}</p>
                    {action.estimated_impact && (
                      <p className="text-xs text-gray-600 mt-0.5 truncate">{String(action.estimated_impact)}</p>
                    )}
                  </div>
                  <span className={`shrink-0 text-xs px-1.5 py-0.5 rounded border ${urgencyStyle}`}>
                    {urgency === "IMMEDIATE" ? "NOW" :
                     urgency === "THIS_WEEK" ? "WEEK" :
                     urgency === "THIS_MONTH" ? "MONTH" : "QTR"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Conflicts */}
      {conflicts.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
            Agent Conflicts Resolved ({conflicts.length})
          </p>
          <div className="space-y-2">
            {conflicts.map((c, i) => (
              <div key={i} className="border border-gray-800 rounded p-2">
                <p className="text-xs text-gray-400">
                  <span className="text-gray-300">{c.between?.join(" vs ")}</span>
                </p>
                <p className="text-xs text-gray-500 mt-0.5 leading-snug">{c.resolution}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Next Review */}
      {nextReview && (
        <div className="border-t border-gray-800 pt-3">
          <p className="text-xs text-gray-600">
            <span className="text-gray-500">Next review trigger: </span>
            {nextReview}
          </p>
        </div>
      )}
    </div>
  );
}
