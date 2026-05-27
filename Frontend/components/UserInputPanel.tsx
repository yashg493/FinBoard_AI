// components/UserInputPanel.tsx
// Chat-style input bar for user to speak to the board mid-meeting
// Supports questions and constraints (stated goals / restrictions)

import { useState, useRef } from "react";

interface UserInputPanelProps {
  onSend: (message: string, isConstraint: boolean) => void;
  isConnected: boolean;
  isRunning: boolean;
}

const QUICK_QUESTIONS = [
  "Should I exit my large-cap positions now?",
  "Am I over-exposed to IT sector?",
  "Is my emergency fund sufficient?",
  "How will a rate hike affect my portfolio?",
];

const QUICK_CONSTRAINTS = [
  "I'm buying a house in 2 years",
  "I cannot invest more than ₹50,000/month",
  "I need liquidity in 6 months",
  "I want to retire in 15 years",
];

export default function UserInputPanel({ onSend, isConnected, isRunning }: UserInputPanelProps) {
  const [message, setMessage]         = useState("");
  const [isConstraint, setIsConstraint] = useState(false);
  const [showQuick, setShowQuick]     = useState(false);
  const inputRef                       = useRef<HTMLTextAreaElement>(null);

  function handleSend() {
    const trimmed = message.trim();
    if (!trimmed || !isConnected) return;
    onSend(trimmed, isConstraint);
    setMessage("");
    setShowQuick(false);
    inputRef.current?.focus();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleQuick(text: string) {
    onSend(text, isConstraint);
    setShowQuick(false);
  }

  const quickList = isConstraint ? QUICK_CONSTRAINTS : QUICK_QUESTIONS;

  return (
    <div className="border-t border-gray-800 bg-gray-950 px-4 py-3 shrink-0">
      {/* Mode Toggle */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs text-gray-600">Board input:</span>
        <div className="flex rounded-lg overflow-hidden border border-gray-800 text-xs">
          <button
            onClick={() => setIsConstraint(false)}
            className={`px-3 py-1 transition-colors ${
              !isConstraint
                ? "bg-amber-500/20 text-amber-400 border-r border-amber-800"
                : "text-gray-500 hover:text-gray-300 border-r border-gray-800"
            }`}
          >
            ❓ Question
          </button>
          <button
            onClick={() => setIsConstraint(true)}
            className={`px-3 py-1 transition-colors ${
              isConstraint
                ? "bg-blue-500/20 text-blue-400"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            📌 State Constraint
          </button>
        </div>
        <button
          onClick={() => setShowQuick(!showQuick)}
          className="ml-auto text-xs text-gray-600 hover:text-gray-400 transition-colors"
        >
          {showQuick ? "▲ hide" : "▼ quick"}
        </button>
      </div>

      {/* Quick Suggestions */}
      {showQuick && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {quickList.map((q) => (
            <button
              key={q}
              onClick={() => handleQuick(q)}
              className="text-xs px-2.5 py-1 rounded-full border border-gray-700 text-gray-400
                         hover:border-amber-700 hover:text-amber-400 transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input Area */}
      <div className="flex gap-2 items-end">
        <div className="flex-1 relative">
          <textarea
            ref={inputRef}
            rows={1}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isConstraint
                ? "State a constraint e.g. 'I'm buying a house in 18 months'…"
                : "Ask the board e.g. 'Should I reduce equity exposure?'…"
            }
            disabled={!isConnected}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2.5
                       text-sm text-gray-200 placeholder-gray-600 resize-none
                       focus:outline-none focus:border-amber-700
                       disabled:opacity-40 disabled:cursor-not-allowed
                       transition-colors"
            style={{ minHeight: "40px", maxHeight: "120px" }}
            onInput={(e) => {
              const el = e.currentTarget;
              el.style.height = "auto";
              el.style.height = Math.min(el.scrollHeight, 120) + "px";
            }}
          />
          {!isConnected && (
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xs text-gray-600">Connecting…</span>
            </div>
          )}
        </div>
        <button
          onClick={handleSend}
          disabled={!message.trim() || !isConnected}
          className={`shrink-0 px-4 py-2.5 rounded-lg text-xs font-medium transition-all
            disabled:opacity-40 disabled:cursor-not-allowed
            ${isConstraint
              ? "bg-blue-600 hover:bg-blue-500 text-white"
              : "bg-amber-500 hover:bg-amber-400 text-black"
            }`}
        >
          {isConstraint ? "📌 Add" : "⚡ Ask"}
        </button>
      </div>

      <p className="mt-1.5 text-xs text-gray-700">
        {isConstraint
          ? "Constraints are remembered and factor into all board decisions."
          : "Enter to send · Shift+Enter for new line"}
      </p>
    </div>
  );
}
