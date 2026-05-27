// components/CSVImport.tsx
// Drag-and-drop CSV uploader for Zerodha Console, Groww, and other broker exports
// Completely FREE — no API keys needed

import { useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const USER_ID = "user_yash_001";

const BROKER_STEPS: Record<string, { name: string; steps: string[]; link: string; icon: string }> = {
  zerodha: {
    name: "Zerodha Console",
    icon: "🟠",
    link: "https://console.zerodha.com/portfolio/holdings",
    steps: [
      "Go to console.zerodha.com → Portfolio → Holdings",
      "Click the XLSX button (top right corner)",
      "Open in Excel / Google Sheets",
      "File → Save As → CSV (Comma delimited)",
      "Upload the CSV file below",
    ],
  },
  groww: {
    name: "Groww",
    icon: "🟢",
    link: "https://groww.in/portfolio",
    steps: [
      "Go to groww.in → Portfolio → Stocks",
      "Click ⋮ menu → Download Portfolio",
      "Upload the downloaded CSV below",
    ],
  },
  indmoney: {
    name: "INDmoney",
    icon: "🔵",
    link: "https://indmoney.com",
    steps: [
      "Go to INDmoney → Investments → Stocks",
      "Download statement (Tax Report section)",
      "Upload the CSV file below",
    ],
  },
  generic: {
    name: "Any Broker (Generic CSV)",
    icon: "📄",
    link: "",
    steps: [
      "Create a CSV with columns: Symbol, Quantity, Avg Cost",
      "Add one row per holding",
      "Upload the CSV file below",
    ],
  },
};

interface ImportResult {
  broker_detected: string;
  imported_count: number;
  total_holdings: number;
  skipped: string[];
  message: string;
}

interface CSVImportProps {
  onImported: () => void;
}

export default function CSVImport({ onImported }: CSVImportProps) {
  const [selectedBroker, setSelectedBroker] = useState<string>("zerodha");
  const [dragging, setDragging]             = useState(false);
  const [uploading, setUploading]           = useState(false);
  const [result, setResult]                 = useState<ImportResult | null>(null);
  const [error, setError]                   = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const info = BROKER_STEPS[selectedBroker];

  async function uploadFile(file: File) {
    if (!file.name.endsWith(".csv") && !file.name.endsWith(".txt")) {
      setError("Please upload a .csv file. For XLSX files: open in Excel → File → Save As → CSV.");
      return;
    }

    setUploading(true); setError(""); setResult(null);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_URL}/api/broker/${USER_ID}/import/csv`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Import failed");
      setResult(data);
      onImported();
    } catch (e: any) {
      setError(e.message);
    }
    setUploading(false);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault(); setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
    e.target.value = "";
  }

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-sm font-semibold text-gray-300">📂 Import from CSV</h3>
        <p className="text-xs text-gray-600 mt-0.5">
          Free — no API key needed. Export from your broker and upload here.
        </p>
      </div>

      {/* Broker Selector */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(BROKER_STEPS).map(([id, b]) => (
          <button
            key={id}
            onClick={() => setSelectedBroker(id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs transition-colors ${
              selectedBroker === id
                ? "border-amber-600 bg-amber-600/20 text-amber-400"
                : "border-gray-700 text-gray-500 hover:border-gray-600 hover:text-gray-400"
            }`}
          >
            {b.icon} {b.name}
          </button>
        ))}
      </div>

      {/* Step-by-step instructions */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">
            How to export from {info.name}
          </p>
          {info.link && (
            <a
              href={info.link}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-amber-500 hover:text-amber-400 hover:underline"
            >
              Open {info.name} ↗
            </a>
          )}
        </div>
        <ol className="space-y-1.5">
          {info.steps.map((step, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-gray-500">
              <span className="text-amber-600 font-mono shrink-0">{i + 1}.</span>
              {step}
            </li>
          ))}
        </ol>
      </div>

      {/* Drop Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
          dragging
            ? "border-amber-500 bg-amber-950/20"
            : uploading
            ? "border-gray-700 bg-gray-900/30 cursor-not-allowed"
            : "border-gray-700 hover:border-gray-500 hover:bg-gray-900/30"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.txt"
          onChange={handleFileChange}
          className="hidden"
          disabled={uploading}
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <div className="flex gap-1">
              {[0,1,2].map((i) => (
                <div key={i} className="w-2 h-2 bg-amber-500 rounded-full animate-bounce"
                  style={{ animationDelay: `${i*150}ms` }} />
              ))}
            </div>
            <p className="text-xs text-gray-500">Parsing and importing holdings…</p>
          </div>
        ) : (
          <>
            <div className="text-3xl mb-2">{dragging ? "📂" : "📄"}</div>
            <p className="text-sm text-gray-400">
              {dragging ? "Drop your CSV here" : "Drop CSV file here or click to browse"}
            </p>
            <p className="text-xs text-gray-600 mt-1">.csv files only · XLSX → save as CSV first</p>
          </>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="border border-red-800 bg-red-950/20 rounded-lg p-3">
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}

      {/* Success Result */}
      {result && (
        <div className="border border-green-800 bg-green-950/20 rounded-xl p-4 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-green-400 text-sm">✓ Import Successful</span>
            <span className="text-xs text-gray-600 border border-gray-700 px-2 py-0.5 rounded">
              {result.broker_detected}
            </span>
          </div>
          <p className="text-xs text-green-300">
            {result.message}
          </p>
          <div className="flex gap-4 text-xs text-gray-500">
            <span>📈 Imported: <strong className="text-gray-300">{result.imported_count}</strong></span>
            <span>📂 Total holdings: <strong className="text-gray-300">{result.total_holdings}</strong></span>
          </div>
          {result.skipped.length > 0 && (
            <div className="pt-2 border-t border-green-800/30">
              <p className="text-xs text-yellow-600 mb-1">Warnings:</p>
              {result.skipped.map((s, i) => (
                <p key={i} className="text-xs text-yellow-700">⚠ {s}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Generic CSV template download */}
      <div className="text-center">
        <button
          onClick={() => {
            const csv = "Symbol,Quantity,Avg Cost\nRELIANCE,50,2800\nINFY,100,1750\nHDFCBANK,30,1600\n";
            const blob = new Blob([csv], { type: "text/csv" });
            const url  = URL.createObjectURL(blob);
            const a    = document.createElement("a");
            a.href = url; a.download = "portfolio_template.csv"; a.click();
          }}
          className="text-xs text-gray-600 hover:text-gray-400 transition-colors underline"
        >
          ↓ Download blank CSV template
        </button>
      </div>
    </div>
  );
}
