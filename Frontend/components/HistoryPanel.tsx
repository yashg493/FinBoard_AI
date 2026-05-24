// components/HistoryPanel.tsx
// Past board meetings loaded from /api/history endpoint

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Meeting {
  meeting_id: string;
  timestamp: number;
  agent_outputs: {
    sentinel?: { recommendation: string };
    orchestrator?: { recommendation: string; confidence: number };
  };
  consensus_actions?: Array<{ action: string; urgency: string; domain: string }>;
}

const DOMAIN_ICON: Record<string, string> = {
  INVESTMENT: "📈",
  RISK: "🛡",
  TAX: "📊",
  GOVERNANCE: "⚖",
};

export default function HistoryPanel({ userId }: { userId: string }) {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_URL}/api/history/${userId}?limit=10`);
        const data = await res.json();
        setMeetings(data.meetings ?? []);
      } catch {
        setMeetings([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [userId]);

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto py-10 text-center">
        <p className="text-gray-600 text-sm animate-pulse">Loading meeting history...</p>
      </div>
    );
  }

  if (meetings.length === 0) {
    return (
      <div className="max-w-2xl mx-auto py-10 text-center">
        <p className="text-gray-600 text-sm">No past board meetings yet.</p>
        <p className="text-gray-700 text-xs mt-1">Trigger your first board meeting to see history here.</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-4">
        <h2 className="text-white font-medium">Board Meeting History</h2>
        <p className="text-xs text-gray-500 mt-0.5">{meetings.length} meetings on record</p>
      </div>

      <div className="space-y-3">
        {meetings.map((meeting) => {
          const date = new Date(meeting.timestamp * 1000);
          const isOpen = expanded === meeting.meeting_id;
          const verdict = meeting.agent_outputs?.orchestrator?.recommendation ?? "No verdict recorded";
          const confidence = meeting.agent_outputs?.orchestrator?.confidence ?? 0;
          const trigger = meeting.agent_outputs?.sentinel?.recommendation ?? "";

          return (
            <div
              key={meeting.meeting_id}
              className="border border-gray-800 rounded-lg overflow-hidden"
            >
              {/* Header row */}
              <button
                onClick={() => setExpanded(isOpen ? null : meeting.meeting_id)}
                className="w-full flex items-start gap-3 p-4 text-left hover:bg-gray-900/40 transition-colors"
              >
                <div className="w-8 h-8 rounded bg-amber-950/50 border border-amber-800/50 flex items-center justify-center text-amber-400 text-xs font-bold shrink-0">
                  ⚖
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-gray-300 font-medium">
                      {date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
                    </span>
                    <span className="text-gray-700">·</span>
                    <span className="text-xs text-gray-500">
                      {date.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                    </span>
                    <span className="ml-auto text-xs text-gray-600">
                      {(confidence * 100).toFixed(0)}% confidence
                    </span>
                  </div>
                  <p className="text-sm text-gray-300 leading-snug truncate">{verdict}</p>
                  {trigger && (
                    <p className="text-xs text-blue-500/70 mt-0.5 truncate">Trigger: {trigger}</p>
                  )}
                </div>
                <span className="text-gray-600 text-xs ml-2 mt-1 shrink-0">{isOpen ? "▲" : "▼"}</span>
              </button>

              {/* Expanded actions */}
              {isOpen && meeting.consensus_actions && meeting.consensus_actions.length > 0 && (
                <div className="border-t border-gray-800 px-4 py-3 bg-gray-900/20">
                  <p className="text-xs text-gray-600 uppercase tracking-wider mb-2">Actions from this meeting</p>
                  <div className="space-y-2">
                    {meeting.consensus_actions.slice(0, 5).map((action, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <span className="text-sm shrink-0">
                          {DOMAIN_ICON[action.domain] ?? "•"}
                        </span>
                        <p className="text-xs text-gray-300 leading-snug flex-1">{action.action}</p>
                        <span className={`text-xs shrink-0 px-1.5 py-0.5 rounded ${
                          action.urgency === "IMMEDIATE" ? "bg-red-900/50 text-red-400" :
                          action.urgency === "THIS_WEEK" ? "bg-orange-900/50 text-orange-400" :
                          "bg-gray-800 text-gray-500"
                        }`}>
                          {action.urgency?.replace("_", " ")}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
