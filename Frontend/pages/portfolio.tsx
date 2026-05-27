import { useEffect, useState } from "react";
import Head from "next/head";
import Link from "next/link";
import LiveHoldings from "../components/LiveHoldings";
import PortfolioSetup from "../components/PortfolioSetup";
import BrokerConnect from "../components/BrokerConnect";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const USER_ID = "user_yash_001";

type PortfolioTab = "holdings" | "brokers" | "profile";

interface UserProfile {
  name?: string;
  age?: number;
  monthly_income?: number;
  monthly_expenses?: number;
  sip_monthly?: number;
  risk_tolerance?: string;
  investment_horizon_years?: number;
  tax_regime?: string;
  emergency_fund_months?: number;
  employer_sector?: string;
  portfolio?: { holdings: any[] };
}

const RISK_OPTIONS = ["conservative", "moderate", "moderate_aggressive", "aggressive"];
const TAX_OPTIONS  = ["new", "old"];

export default function PortfolioPage() {
  const [activeTab, setActiveTab]       = useState<PortfolioTab>("brokers");
  const [profile, setProfile]           = useState<UserProfile>({});
  const [loading, setLoading]           = useState(true);
  const [saving, setSaving]             = useState(false);
  const [saveMsg, setSaveMsg]           = useState("");
  const [refreshKey, setRefreshKey]     = useState(0);

  // Profile form fields
  const [income, setIncome]             = useState("");
  const [expenses, setExpenses]         = useState("");
  const [sip, setSip]                   = useState("");
  const [risk, setRisk]                 = useState("moderate");
  const [horizon, setHorizon]           = useState("");
  const [taxRegime, setTaxRegime]       = useState("new");
  const [emergFund, setEmergFund]       = useState("");
  const [sector, setSector]             = useState("");

  useEffect(() => {
    fetch(`${API_URL}/api/portfolio/${USER_ID}`)
      .then((r) => r.json())
      .then((d) => {
        const p = d.profile ?? {};
        setProfile(p);
        setIncome(p.monthly_income?.toString() ?? "");
        setExpenses(p.monthly_expenses?.toString() ?? "");
        setSip(p.sip_monthly?.toString() ?? "");
        setRisk(p.risk_tolerance ?? "moderate");
        setHorizon(p.investment_horizon_years?.toString() ?? "");
        setTaxRegime(p.tax_regime ?? "new");
        setEmergFund(p.emergency_fund_months?.toString() ?? "");
        setSector(p.employer_sector ?? "");
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  async function saveProfile() {
    setSaving(true);
    setSaveMsg("");
    try {
      await fetch(`${API_URL}/api/portfolio/${USER_ID}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          monthly_income:           income   ? parseInt(income)   : undefined,
          monthly_expenses:         expenses ? parseInt(expenses) : undefined,
          sip_monthly:              sip      ? parseInt(sip)      : undefined,
          risk_tolerance:           risk,
          investment_horizon_years: horizon  ? parseInt(horizon)  : undefined,
          tax_regime:               taxRegime,
          emergency_fund_months:    emergFund ? parseInt(emergFund) : undefined,
          employer_sector:          sector || undefined,
        }),
      });
      setSaveMsg("✓ Profile saved");
    } catch {
      setSaveMsg("✗ Save failed");
    }
    setSaving(false);
    setTimeout(() => setSaveMsg(""), 3000);
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="flex gap-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="w-2 h-2 bg-amber-500 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 150}ms` }} />
          ))}
        </div>
      </div>
    );
  }

  const holdings = profile.portfolio?.holdings ?? [];

  return (
    <>
      <Head>
        <title>Portfolio — Boardroom AI</title>
        <meta name="description" content="Manage your live portfolio and financial profile for AI-powered governance analysis" />
      </Head>

      <div className="min-h-screen bg-gray-950 text-gray-100 font-mono flex flex-col">

        {/* Header */}
        <header className="border-b border-gray-800 px-6 py-3 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <Link href="/boardroom" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
              <div className="w-7 h-7 bg-amber-500 rounded flex items-center justify-center text-black font-bold text-xs">B</div>
              <span className="text-white font-semibold tracking-tight">Boardroom AI</span>
            </Link>
            <span className="text-gray-700 text-xs">›</span>
            <span className="text-gray-400 text-xs">Portfolio</span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/boardroom"
              className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-black text-xs font-medium
                         rounded transition-colors flex items-center gap-1.5"
            >
              ⚡ Analyze with Board
            </Link>
          </div>
        </header>

        {/* Tabs */}
        <nav className="border-b border-gray-800 px-6 flex gap-5 shrink-0">
          {([
            { id: "brokers",  label: "🔗 Connect Broker" },
            { id: "holdings", label: "📈 Holdings & Live Prices" },
            { id: "profile",  label: "👤 Financial Profile" },
          ] as { id: PortfolioTab; label: string }[]).map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2.5 text-xs border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-amber-500 text-amber-400"
                  : "border-transparent text-gray-500 hover:text-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Body */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-5xl mx-auto">

            {/* Brokers Tab */}
          {activeTab === "brokers" && (
            <div className="space-y-6">
              <BrokerConnect
                onHoldingsSynced={() => {
                  setRefreshKey((k) => k + 1);
                  setActiveTab("holdings");
                }}
              />
            </div>
          )}

          {/* Holdings Tab */}
            {activeTab === "holdings" && (
              <div className="space-y-6">
                {/* Add / Manage Holdings */}
                <div>
                  <h2 className="text-sm font-semibold text-gray-300 mb-4">Manage Holdings</h2>
                  <PortfolioSetup
                    userId={USER_ID}
                    existingHoldings={holdings}
                    onSaved={() => setRefreshKey((k) => k + 1)}
                  />
                </div>

                {/* Live Price Table */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-sm font-semibold text-gray-300">Live Portfolio</h2>
                    <span className="text-xs text-gray-600">Prices via NSE · yfinance</span>
                  </div>
                  <LiveHoldings key={refreshKey} userId={USER_ID} />
                </div>

                {/* Board Analysis CTA */}
                {holdings.length > 0 && (
                  <div className="border border-amber-800/40 bg-amber-950/10 rounded-xl p-4 flex items-center justify-between">
                    <div>
                      <p className="text-sm text-amber-200 font-medium">Ready for board analysis?</p>
                      <p className="text-xs text-amber-700 mt-0.5">
                        Your live portfolio data will be passed to all agents during the next board meeting.
                      </p>
                    </div>
                    <Link
                      href="/boardroom"
                      className="shrink-0 ml-4 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-black
                                 text-xs font-medium rounded-lg transition-colors"
                    >
                      ⚡ Start Board Meeting
                    </Link>
                  </div>
                )}
              </div>
            )}

            {/* Profile Tab */}
            {activeTab === "profile" && (
              <div className="max-w-2xl space-y-6">
                <h2 className="text-sm font-semibold text-gray-300">Financial Profile</h2>
                <p className="text-xs text-gray-600">
                  This data feeds directly into every board meeting. Keep it up to date for accurate governance decisions.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {[
                    { label: "Monthly Income (₹)",    value: income,    setter: setIncome,    placeholder: "150000",  type: "number" },
                    { label: "Monthly Expenses (₹)",  value: expenses,  setter: setExpenses,  placeholder: "60000",   type: "number" },
                    { label: "Monthly SIP (₹)",        value: sip,       setter: setSip,       placeholder: "25000",   type: "number" },
                    { label: "Investment Horizon (yrs)", value: horizon, setter: setHorizon,   placeholder: "20",      type: "number" },
                    { label: "Emergency Fund (months)", value: emergFund, setter: setEmergFund, placeholder: "6",      type: "number" },
                    { label: "Employer Sector",        value: sector,    setter: setSector,    placeholder: "Technology", type: "text" },
                  ].map(({ label, value, setter, placeholder, type }) => (
                    <div key={label}>
                      <label className="text-xs text-gray-600 mb-1 block">{label}</label>
                      <input
                        type={type}
                        value={value}
                        onChange={(e) => setter(e.target.value)}
                        placeholder={placeholder}
                        className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm
                                   text-gray-200 placeholder-gray-600 focus:outline-none focus:border-amber-700
                                   transition-colors"
                      />
                    </div>
                  ))}
                </div>

                {/* Risk Tolerance */}
                <div>
                  <label className="text-xs text-gray-600 mb-2 block">Risk Tolerance</label>
                  <div className="flex flex-wrap gap-2">
                    {RISK_OPTIONS.map((r) => (
                      <button
                        key={r}
                        onClick={() => setRisk(r)}
                        className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                          risk === r
                            ? "border-amber-600 bg-amber-600/20 text-amber-400"
                            : "border-gray-700 text-gray-500 hover:border-gray-600 hover:text-gray-400"
                        }`}
                      >
                        {r.replace(/_/g, " ")}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Tax Regime */}
                <div>
                  <label className="text-xs text-gray-600 mb-2 block">Tax Regime</label>
                  <div className="flex gap-2">
                    {TAX_OPTIONS.map((t) => (
                      <button
                        key={t}
                        onClick={() => setTaxRegime(t)}
                        className={`text-xs px-4 py-1.5 rounded-lg border transition-colors ${
                          taxRegime === t
                            ? "border-amber-600 bg-amber-600/20 text-amber-400"
                            : "border-gray-700 text-gray-500 hover:border-gray-600"
                        }`}
                      >
                        {t.charAt(0).toUpperCase() + t.slice(1)} Regime
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={saveProfile}
                    disabled={saving}
                    className="px-5 py-2 bg-amber-500 hover:bg-amber-400 disabled:opacity-50
                               text-black text-xs font-medium rounded-lg transition-colors"
                  >
                    {saving ? "Saving…" : "Save Profile"}
                  </button>
                  {saveMsg && (
                    <span className={`text-xs ${saveMsg.startsWith("✓") ? "text-green-400" : "text-red-400"}`}>
                      {saveMsg}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </>
  );
}
