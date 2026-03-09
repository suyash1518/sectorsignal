import { useState, useEffect, useCallback } from "react";

// ── Change this to your Render URL after deploying ──
const API_BASE = import.meta.env.VITE_API_URL || "https://sectorsignal-api.onrender.com";

const REGIONS = [
  { id: "india", label: "🇮🇳 India", index: "NIFTY 50" },
  { id: "us", label: "🇺🇸 United States", index: "S&P 500" },
  { id: "japan", label: "🇯🇵 Japan", index: "Nikkei 225" },
];

const SIGNAL = {
  BUY:   { bg: "rgba(34,197,94,0.13)",  border: "#22c55e", text: "#4ade80" },
  WATCH: { bg: "rgba(251,191,36,0.12)", border: "#fbbf24", text: "#fcd34d" },
  AVOID: { bg: "rgba(239,68,68,0.12)",  border: "#ef4444", text: "#f87171" },
};

const SECTOR_COLORS = [
  "#f59e0b","#22c55e","#6366f1","#8b5cf6","#06b6d4","#f97316","#ec4899","#14b8a6"
];

function MiniChart({ data, color }) {
  if (!data || data.length < 2) return null;
  const w = 120, h = 38;
  const max = Math.max(...data), min = Math.min(...data);
  const norm = v => h - ((v - min) / (max - min || 1)) * (h - 8) - 4;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${norm(v)}`).join(" ");
  const area = `${pts} ${w},${h} 0,${h}`;
  const id = `g${color.replace(/[^a-z0-9]/gi, "")}`;
  return (
    <svg width={w} height={h} style={{ overflow: "visible", display: "block" }}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#${id})`} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

function ScoreRing({ score, color }) {
  const r = 26, cx = 32, cy = 32, circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  return (
    <svg width="64" height="64">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="5" />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth="5"
        strokeDasharray={`${dash} ${circ}`} strokeDashoffset={circ * 0.25}
        strokeLinecap="round" style={{ transition: "stroke-dasharray 0.8s ease" }} />
      <text x={cx} y={cy + 5} textAnchor="middle" fill="white" fontSize="13" fontWeight="700" fontFamily="monospace">{Math.round(score)}</text>
    </svg>
  );
}

function BarStat({ label, value, max = 100, color }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: "#64748b" }}>{label}</span>
        <span style={{ fontSize: 11, color, fontFamily: "monospace" }}>{value !== null && value !== undefined ? Math.round(value) : "–"}</span>
      </div>
      <div style={{ height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 2 }}>
        <div style={{ height: "100%", width: `${Math.min(100, Math.max(0, (value / max) * 100))}%`, background: color, borderRadius: 2, transition: "width 0.6s ease" }} />
      </div>
    </div>
  );
}

function Skeleton({ w = "100%", h = 16, style = {} }) {
  return <div style={{ width: w, height: h, borderRadius: 6, background: "rgba(255,255,255,0.06)", animation: "pulse 1.5s ease-in-out infinite", ...style }} />;
}

export default function App() {
  const [region, setRegion] = useState("india");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const loadData = useCallback(async (r) => {
    setLoading(true);
    setError(null);
    setSelected(null);
    try {
      const res = await fetch(`${API_BASE}/api/sectors/${r}`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const json = await res.json();
      setData(json);
      setLastUpdated(new Date(json.generated_at));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(region); }, [region, loadData]);

  const sectors = data?.sectors || [];
  const selectedSector = selected ? sectors.find(s => s.id === selected) : null;
  const buys = sectors.filter(s => s.signal === "BUY");

  return (
    <div style={{ minHeight: "100vh", background: "#070d1a", fontFamily: "'DM Sans', sans-serif", color: "#e2e8f0" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=Space+Mono:wght@400;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; } ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }
        .hoverable { transition: transform 0.2s, border-color 0.2s, background 0.2s; cursor: pointer; }
        .hoverable:hover { transform: translateY(-2px); }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
        .fade-up { animation: fadeUp 0.4s ease both; }
      `}</style>

      {/* Header */}
      <header style={{ background: "rgba(255,255,255,0.02)", borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "18px 32px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
              <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#22c55e", boxShadow: "0 0 8px #22c55e" }} />
              <span style={{ fontFamily: "'Space Mono'", fontSize: 10, color: "#475569", letterSpacing: 3, textTransform: "uppercase" }}>Live · Yahoo Finance</span>
            </div>
            <h1 style={{ fontFamily: "'Space Mono'", fontSize: 20, fontWeight: 700, background: "linear-gradient(120deg,#f1f5f9,#64748b)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              SectorSignal
            </h1>
          </div>

          <div style={{ display: "flex", gap: 6 }}>
            {REGIONS.map(r => (
              <button key={r.id} onClick={() => setRegion(r.id)}
                style={{
                  padding: "7px 15px", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer",
                  border: `1px solid ${region === r.id ? "#6366f1" : "rgba(255,255,255,0.08)"}`,
                  background: region === r.id ? "rgba(99,102,241,0.18)" : "rgba(255,255,255,0.03)",
                  color: region === r.id ? "#a5b4fc" : "#64748b",
                  transition: "all 0.2s",
                }}>
                {r.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1100, margin: "0 auto", padding: "28px 32px" }}>

        {/* Status bar */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 8 }}>
          <span style={{ fontFamily: "'Space Mono'", fontSize: 10, color: "#334155", letterSpacing: 2, textTransform: "uppercase" }}>
            {REGIONS.find(r => r.id === region)?.index} · Sector Scores
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {loading && <div style={{ width: 14, height: 14, border: "2px solid #334155", borderTopColor: "#6366f1", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />}
            {lastUpdated && !loading && (
              <span style={{ fontSize: 11, color: "#334155" }}>
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <button onClick={() => loadData(region)} style={{ fontSize: 11, color: "#475569", background: "none", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 6, padding: "4px 10px", cursor: "pointer" }}>
              ↻ Refresh
            </button>
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 12, padding: "16px 20px", marginBottom: 24, color: "#fca5a5" }}>
            <strong>API Error:</strong> {error}
            <div style={{ fontSize: 12, color: "#f87171", marginTop: 4 }}>Make sure your Render backend is running. Check <code>VITE_API_URL</code> in your .env</div>
          </div>
        )}

        {/* Top BUY picks */}
        <section style={{ marginBottom: 28 }}>
          <div style={{ fontFamily: "'Space Mono'", fontSize: 10, color: "#475569", letterSpacing: 2, textTransform: "uppercase", marginBottom: 14 }}>
            ● Top Buy Signals
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
            {loading
              ? [0,1,2].map(i => (
                  <div key={i} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 14, padding: "20px" }}>
                    <Skeleton w="60%" h={12} style={{ marginBottom: 10 }} />
                    <Skeleton w="80%" h={18} style={{ marginBottom: 8 }} />
                    <Skeleton w="40%" h={10} />
                  </div>
                ))
              : buys.map((s, i) => {
                  const color = SECTOR_COLORS[sectors.indexOf(s) % SECTOR_COLORS.length];
                  return (
                    <div key={s.id} className="hoverable fade-up" onClick={() => setSelected(s.id === selected ? null : s.id)}
                      style={{
                        animationDelay: `${i * 0.08}s`,
                        background: selected === s.id ? "rgba(34,197,94,0.07)" : "rgba(255,255,255,0.03)",
                        border: `1px solid ${selected === s.id ? "rgba(34,197,94,0.35)" : "rgba(255,255,255,0.07)"}`,
                        borderRadius: 14, padding: "18px 20px",
                      }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
                        <div>
                          <div style={{ fontFamily: "'Space Mono'", fontSize: 10, color: "#475569", marginBottom: 4 }}>#{i + 1} PICK</div>
                          <div style={{ fontSize: 15, fontWeight: 600, color: "#f1f5f9" }}>{s.name}</div>
                          <div style={{ fontSize: 11, color: "#334155", marginTop: 3 }}>{s.tickers?.[0]}</div>
                        </div>
                        <ScoreRing score={s.score} color={color} />
                      </div>
                      <MiniChart data={s.price_trend} color={color} />
                      {s.pct_from_52w_high !== null && (
                        <div style={{ marginTop: 10, fontSize: 12, color: s.pct_from_52w_high < 0 ? "#4ade80" : "#f87171" }}>
                          {s.pct_from_52w_high > 0 ? "+" : ""}{s.pct_from_52w_high}% from 52W high
                        </div>
                      )}
                    </div>
                  );
                })
            }
          </div>
        </section>

        {/* Expanded detail panel */}
        {selectedSector && (() => {
          const color = SECTOR_COLORS[sectors.indexOf(selectedSector) % SECTOR_COLORS.length];
          return (
            <section className="fade-up" style={{
              background: "rgba(255,255,255,0.025)", border: `1px solid ${color}33`,
              borderRadius: 16, padding: "24px 28px", marginBottom: 28,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
                <div>
                  <div style={{ fontSize: 17, fontWeight: 700, color: "#f8fafc" }}>{selectedSector.name}</div>
                  <div style={{ fontSize: 12, color: "#475569", marginTop: 2 }}>{selectedSector.tickers?.join(" · ")}</div>
                </div>
                <span style={{
                  padding: "5px 14px", borderRadius: 20, fontSize: 11, fontWeight: 700, fontFamily: "'Space Mono'", letterSpacing: 1,
                  background: SIGNAL[selectedSector.signal].bg,
                  border: `1px solid ${SIGNAL[selectedSector.signal].border}`,
                  color: SIGNAL[selectedSector.signal].text,
                }}>● {selectedSector.signal}</span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
                <div>
                  <BarStat label="Sentiment Score" value={selectedSector.sentiment_score} color="#6366f1" />
                  <BarStat label="Macro Alignment" value={selectedSector.macro_score} color="#f59e0b" />
                  {selectedSector.pe_ratio && <BarStat label="P/E Ratio" value={selectedSector.pe_ratio} max={50} color="#22c55e" />}
                  <BarStat label="Composite Score" value={selectedSector.score} color={color} />
                </div>
                <div>
                  <div style={{ fontSize: 11, color: "#475569", marginBottom: 8, fontFamily: "'Space Mono'", letterSpacing: 1, textTransform: "uppercase" }}>Macro Driver</div>
                  <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 14, lineHeight: 1.6, padding: "10px 14px", background: "rgba(255,255,255,0.04)", borderRadius: 8, borderLeft: `3px solid ${color}` }}>
                    {selectedSector.macro_description || "General market conditions"}
                  </div>

                  {selectedSector.sample_headlines?.length > 0 && (
                    <>
                      <div style={{ fontSize: 11, color: "#475569", marginBottom: 8, fontFamily: "'Space Mono'", letterSpacing: 1, textTransform: "uppercase" }}>
                        Latest Headlines ({selectedSector.headline_count} analyzed)
                      </div>
                      {selectedSector.sample_headlines.map((h, i) => (
                        <div key={i} style={{ fontSize: 12, color: "#64748b", padding: "7px 10px", borderBottom: i < selectedSector.sample_headlines.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none", lineHeight: 1.5 }}>
                          {h}
                        </div>
                      ))}
                    </>
                  )}
                </div>
              </div>
            </section>
          );
        })()}

        {/* Full sector table */}
        <section style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 14, overflow: "hidden" }}>
          <div style={{ padding: "14px 22px", borderBottom: "1px solid rgba(255,255,255,0.05)", display: "flex", justifyContent: "space-between" }}>
            <span style={{ fontFamily: "'Space Mono'", fontSize: 10, color: "#475569", letterSpacing: 2, textTransform: "uppercase" }}>All Sectors</span>
            <span style={{ fontSize: 11, color: "#1e293b" }}>Ranked by score ↓</span>
          </div>

          {loading
            ? [0,1,2,3,4].map(i => (
                <div key={i} style={{ display: "flex", gap: 14, padding: "14px 22px", borderBottom: "1px solid rgba(255,255,255,0.04)", alignItems: "center" }}>
                  <Skeleton w={24} h={12} />
                  <Skeleton w="25%" h={14} />
                  <Skeleton w={120} h={38} style={{ marginLeft: "auto" }} />
                  <Skeleton w={40} h={20} />
                  <Skeleton w={60} h={22} style={{ borderRadius: 20 }} />
                </div>
              ))
            : sectors.map((s, i) => {
                const color = SECTOR_COLORS[i % SECTOR_COLORS.length];
                return (
                  <div key={s.id} className="hoverable" onClick={() => setSelected(s.id === selected ? null : s.id)}
                    style={{
                      display: "flex", alignItems: "center", gap: 14, padding: "13px 22px",
                      borderBottom: i < sectors.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none",
                      background: selected === s.id ? "rgba(255,255,255,0.04)" : "transparent",
                    }}>
                    <span style={{ fontFamily: "monospace", fontSize: 11, color: "#1e293b", width: 18 }}>{i + 1}</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0" }}>{s.name}</div>
                      <div style={{ fontSize: 11, color: "#334155" }}>{s.tickers?.[0]}</div>
                    </div>
                    <div style={{ display: "none", "@media(min-width:640px)": { display: "block" } }}>
                      <MiniChart data={s.price_trend} color={color} />
                    </div>
                    <div style={{ textAlign: "center", minWidth: 42 }}>
                      <div style={{ fontSize: 16, fontWeight: 700, color }}>{Math.round(s.score)}</div>
                      <div style={{ fontSize: 9, color: "#334155" }}>SCORE</div>
                    </div>
                    <span style={{
                      padding: "3px 10px", borderRadius: 20, fontSize: 10, fontWeight: 700, minWidth: 56, textAlign: "center",
                      fontFamily: "'Space Mono'", background: SIGNAL[s.signal].bg,
                      border: `1px solid ${SIGNAL[s.signal].border}33`, color: SIGNAL[s.signal].text,
                    }}>
                      {s.signal}
                    </span>
                    {s.pct_from_52w_high !== null && (
                      <span style={{ fontFamily: "monospace", fontSize: 12, color: s.pct_from_52w_high < 0 ? "#4ade80" : "#ef4444", minWidth: 60, textAlign: "right" }}>
                        {s.pct_from_52w_high > 0 ? "+" : ""}{s.pct_from_52w_high}%
                      </span>
                    )}
                  </div>
                );
              })
          }
        </section>

        <footer style={{ marginTop: 32, textAlign: "center" }}>
          <p style={{ fontSize: 11, color: "#1e293b" }}>
            Data via Yahoo Finance · Sentiment via VADER NLP · Not financial advice
          </p>
        </footer>
      </main>
    </div>
  );
}
