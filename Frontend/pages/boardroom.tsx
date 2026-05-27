// pages/boardroom.tsx — complete version with user chat input, portfolio tab, and all components

import { useEffect, useRef, useState, useCallback } from "react";
import Head from "next/head";
import Link from "next/link";
import BoardEvent from "../components/BoardEvent";
import AgentCard from "../components/AgentCard";
import ConsensusPanel from "../components/ConsensusPanel";
import MacroDashboard from "../components/MacroDashboard";
import SimulationPanel from "../components/SimulationPanel";
import HistoryPanel from "../components/HistoryPanel";
import UserInputPanel from "../components/UserInputPanel";

export type EventType =
  | "board_meeting_start" | "agent_thinking" | "agent_output"
  | "phase_start" | "debate_start" | "agent_debate"
  | "consensus" | "meeting_saved" | "board_meeting_end"
  | "simulation_start" | "simulation_end" | "simulation_data"
  | "user_input" | "user_response" | "constraint_acknowledged"
  | "pong";

export interface BoardEventData {
  type: EventType;
  agent: string;
  message: string;
  data?: Record<string, unknown>;
  icon?: string;
  debate?: boolean;
  simulation?: boolean;
  timestamp?: number;
}

const WS_URL  = process.env.NEXT_PUBLIC_WS_URL  ?? "ws://localhost:8000/ws";
const API_URL = process.env.NEXT_PUBLIC_API_URL  ?? "http://localhost:8000";
const USER_ID = "user_yash_001";

const AGENTS = [
  { name: "Sentinel Agent",   icon: "👁",  role: "Macro Monitor"      },
  { name: "Investment Agent", icon: "📈", role: "Portfolio Optimizer" },
  { name: "Risk Agent",       icon: "🛡",  role: "Risk & Emergency"   },
  { name: "Tax Agent",        icon: "📊", role: "Tax Efficiency"      },
  { name: "Orchestrator",     icon: "⚖",  role: "Board Chair"         },
];

type Tab = "boardroom" | "simulation" | "history";

export default function BoardroomPage() {
  const [events, setEvents]           = useState<BoardEventData[]>([]);
  const [isRunning, setIsRunning]     = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [consensus, setConsensus]     = useState<BoardEventData | null>(null);
  const [activeTab, setActiveTab]     = useState<Tab>("boardroom");
  const [governance, setGovernance]   = useState<"ADVISORY" | "COPILOT" | "AUTONOMOUS">("ADVISORY");
  const [constraints, setConstraints] = useState<string[]>([]);
  const [livePortfolio, setLivePortfolio] = useState<Record<string, unknown> | null>(null);

  const wsRef        = useRef<WebSocket | null>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  // Fetch live portfolio once on mount so board meeting uses real data
  useEffect(() => {
    fetch(`${API_URL}/api/portfolio/${USER_ID}/live`)
      .then((r) => r.json())
      .then((d) => { if (d.holdings?.length) setLivePortfolio(d); })
      .catch(() => {});
  }, []);

  useEffect(() => { connectWS(); return () => wsRef.current?.close(); }, []);
  useEffect(() => { eventsEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [events]);

  function connectWS() {
    const ws = new WebSocket(`${WS_URL}/${USER_ID}`);
    wsRef.current = ws;
    ws.onopen    = () => setIsConnected(true);
    ws.onclose   = () => { setIsConnected(false); setTimeout(connectWS, 3000); };
    ws.onmessage = (e) => handleEvent(JSON.parse(e.data) as BoardEventData);
  }

  function handleEvent(ev: BoardEventData) {
    if (ev.type === "board_meeting_start" || ev.type === "simulation_start") {
      setIsRunning(true);
      setEvents([]);
      setConsensus(null);
    }
    if (ev.type === "board_meeting_end" || ev.type === "simulation_end") {
      setIsRunning(false);
    }
    if (ev.type === "consensus") {
      setConsensus(ev);
      const mode = ev.data?.governance_mode as "ADVISORY" | "COPILOT" | "AUTONOMOUS" | undefined;
      if (mode) setGovernance(mode);
    }
    if (!["board_meeting_end", "simulation_end", "pong"].includes(ev.type)) {
      setEvents((prev) => [...prev, ev]);
    }
  }

  function send(payload: object) { wsRef.current?.send(JSON.stringify(payload)); }

  function triggerBoardMeeting() {
    const context: Record<string, unknown> = { source: "manual_trigger" };
    if (livePortfolio) context.live_portfolio = livePortfolio;
    if (constraints.length) context.user_constraints = constraints;
    send({ type: "trigger_board_meeting", context });
  }

  function triggerSimulation(scenario: string) { send({ type: "trigger_simulation", scenario }); }

  function handleUserInput(message: string, isConstraint: boolean) {
    if (isConstraint) {
      setConstraints((prev) => [...prev, message]);
    }
    send({ type: "user_input", message, is_constraint: isConstraint });
    // Immediately show on feed
    setActiveTab("boardroom");
  }

  const GOV_COLOR = {
    ADVISORY:   "text-blue-400 border-blue-800",
    COPILOT:    "text-amber-400 border-amber-700",
    AUTONOMOUS: "text-green-400 border-green-800",
  };

  return (
    <>
      <Head>
        <title>Boardroom AI — Financial Governance</title>
        <meta name="description" content="Autonomous multi-agent AI financial governance board. Real-time debate, portfolio analysis, and consensus-driven decisions." />
      </Head>
      <div className="min-h-screen bg-gray-950 text-gray-100 font-mono flex flex-col">

        {/* Header */}
        <header className="border-b border-gray-800 px-6 py-3 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 bg-amber-500 rounded flex items-center justify-center text-black font-bold text-xs">B</div>
            <span className="text-white font-semibold tracking-tight">Boardroom AI</span>
            <span className="text-gray-600 text-xs hidden sm:block">Autonomous Financial Governance</span>
            <span className={`text-xs px-2 py-0.5 border rounded hidden md:block ${GOV_COLOR[governance]}`}>{governance}</span>
            {livePortfolio && (
              <span className="text-xs px-2 py-0.5 border border-green-800 text-green-400 rounded hidden md:block">
                📊 Live Portfolio
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {/* Constraints indicator */}
            {constraints.length > 0 && (
              <span className="text-xs px-2 py-0.5 border border-blue-800 text-blue-400 rounded hidden md:block">
                📌 {constraints.length} constraint{constraints.length > 1 ? "s" : ""}
              </span>
            )}
            <div className={`flex items-center gap-1.5 text-xs ${isConnected ? "text-green-400" : "text-red-400"}`}>
              <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-green-400 animate-pulse" : "bg-red-400"}`} />
              <span className="hidden sm:inline">{isConnected ? "Live" : "Reconnecting"}</span>
            </div>
            <Link
              href="/portfolio"
              className="px-3 py-1.5 border border-gray-700 hover:border-gray-500 text-gray-400 hover:text-gray-200
                         text-xs rounded transition-colors hidden sm:block"
            >
              📈 Portfolio
            </Link>
            <button
              onClick={triggerBoardMeeting}
              disabled={isRunning || !isConnected}
              className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-40 disabled:cursor-not-allowed
                         text-black text-xs font-medium rounded transition-colors"
            >
              {isRunning ? "In Session…" : "⚡ Trigger Meeting"}
            </button>
          </div>
        </header>

        {/* Tabs */}
        <nav className="border-b border-gray-800 px-6 flex gap-5 shrink-0">
          {(["boardroom", "simulation", "history"] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2.5 text-xs capitalize border-b-2 transition-colors ${
                activeTab === tab ? "border-amber-500 text-amber-400" : "border-transparent text-gray-500 hover:text-gray-300"
              }`}
            >
              {tab === "boardroom" ? "🏛 Boardroom" : tab === "simulation" ? "⚗ Simulation" : "📜 History"}
            </button>
          ))}
        </nav>

        {/* Body */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left sidebar */}
          <aside className="w-56 border-r border-gray-800 p-3 flex-col gap-2 overflow-y-auto shrink-0 hidden md:flex">
            <p className="text-xs text-gray-600 uppercase tracking-wider px-1 pt-1 mb-1">Agents</p>
            {AGENTS.map((a) => (
              <AgentCard
                key={a.name}
                name={a.name}
                icon={a.icon}
                role={a.role}
                isActive={isRunning && events.some((e) => e.agent === a.name)}
                lastMessage={[...events].reverse().find((e) => e.agent === a.name)?.message}
              />
            ))}

            {/* Constraints Panel */}
            {constraints.length > 0 && (
              <div className="mt-4 pt-3 border-t border-gray-800">
                <p className="text-xs text-gray-600 uppercase tracking-wider px-1 mb-2">Your Constraints</p>
                <div className="space-y-1">
                  {constraints.map((c, i) => (
                    <div key={i} className="text-xs text-blue-400 bg-blue-950/20 border border-blue-900/40 rounded px-2 py-1 leading-snug">
                      📌 {c}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </aside>

          {/* Main content + input */}
          <div className="flex flex-col flex-1 overflow-hidden">
            <main className="flex-1 overflow-y-auto p-4 md:p-6">
              {activeTab === "boardroom" && (
                <div className="max-w-2xl mx-auto space-y-3">
                  {events.length === 0 && !isRunning && (
                    <div className="text-center py-20">
                      <div className="text-4xl mb-3">🏛</div>
                      <p className="text-gray-600 text-sm">The boardroom is ready.</p>
                      <p className="text-gray-700 text-xs mt-1">Click "Trigger Meeting" or ask the board a question below.</p>
                      {livePortfolio && (
                        <p className="text-green-600 text-xs mt-2">✓ Live portfolio connected — agents will analyze your real holdings.</p>
                      )}
                    </div>
                  )}
                  {events.map((ev, i) => <BoardEvent key={i} event={ev} />)}
                  <div ref={eventsEndRef} />
                </div>
              )}
              {activeTab === "simulation" && (
                <SimulationPanel onTrigger={triggerSimulation} isRunning={isRunning} events={events} />
              )}
              {activeTab === "history" && <HistoryPanel userId={USER_ID} />}
            </main>

            {/* User Input Panel — always visible in boardroom tab */}
            {activeTab === "boardroom" && (
              <UserInputPanel
                onSend={handleUserInput}
                isConnected={isConnected}
                isRunning={isRunning}
              />
            )}
          </div>

          {/* Right sidebar */}
          <aside className="w-72 border-l border-gray-800 p-4 overflow-y-auto shrink-0 hidden lg:block">
            {consensus
              ? <ConsensusPanel event={consensus} />
              : <div className="py-8 text-center"><p className="text-gray-700 text-xs">Consensus appears here after a board meeting.</p></div>
            }
            <MacroDashboard />
          </aside>
        </div>
      </div>
    </>
  );
}
