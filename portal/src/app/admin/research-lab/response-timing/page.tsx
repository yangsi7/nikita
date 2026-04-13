"use client";

/**
 * Response Timing Model — Spec 210 v2 Decision Brief (native portal page).
 *
 * Native React port of the standalone HTML artifact at
 * docs/models/response-timing-explorer.html. Inline styles are preserved
 * intentionally — this page is a self-contained "research lab" artifact,
 * not a portal feature surface, so it does NOT use Tailwind/shadcn. The
 * design tokens are scoped to this component subtree and do not bleed.
 *
 * Sections (9 total):
 *   01  Problem recap
 *   02  Proposed model
 *   03  Monte Carlo simulator
 *   04  Chapter 1 floor
 *   05  Momentum layer (formula + trace simulator + feedback-spiral demo)
 *   06  Bayesian equivalence (EWMA ↔ Normal-Normal conjugate posterior)
 *   07  Old vs new
 *   08  Why log-normal + excitement-fades
 *   09  Citations + next steps
 */

import React, { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// ── Design tokens ────────────────────────────────────────────────
const T = {
  bg: "#020202",
  surface: "#0A0A0A",
  surfaceUp: "#141414",
  border: "rgba(255,255,255,0.07)",
  text: "#EBEBEB",
  textMuted: "rgba(235,235,235,0.55)",
  textDim: "rgba(235,235,235,0.28)",
  accent: "#F383BB",
  accentDim: "rgba(243,131,187,0.12)",
  accentGlow: "rgba(243,131,187,0.2)",
  lavender: "#8186D7",
  lavDim: "rgba(129,134,215,0.12)",
} as const;

// Chapter palette (pink → lavender gradient)
const CH = ["#F383BB", "#D283D7", "#A985D7", "#8186D7", "#7BAAC8"] as const;
const CH_LABELS = ["Ch 1", "Ch 2", "Ch 3", "Ch 4", "Ch 5"] as const;
const CH_FEELS = [
  "Infatuation",
  "Very eager",
  "Attentive",
  "Comfortable",
  "Settled",
] as const;

// Per-chapter caps (seconds) — Spec 210 v2
const CAPS_S: Record<number, number> = { 1: 10, 2: 60, 3: 300, 4: 900, 5: 1800 };
// Per-chapter EWMA prior baselines (seconds)
const BASELINES_S: Record<number, number> = {
  1: 300,
  2: 240,
  3: 180,
  4: 120,
  5: 90,
};
// Momentum bounds + alpha
const ALPHA = 0.35;
const M_LO = 0.1;
const M_HI = 5.0;

const PRESETS = {
  tighter: {
    label: "Current proposal",
    coeffs: [0.15, 0.3, 0.5, 0.75, 1.0],
    cap: 1800,
    mu: 2.996,
    sigma: 1.714,
  },
  research: {
    label: "Research baseline",
    coeffs: [0.35, 0.6, 1.0, 1.75, 2.75],
    cap: 3600,
    mu: 2.996,
    sigma: 1.714,
  },
  ultra: {
    label: "Ultra-aggressive",
    coeffs: [0.1, 0.15, 0.25, 0.4, 0.6],
    cap: 900,
    mu: 2.996,
    sigma: 1.714,
  },
} as const;

const TRACE_PRESETS: Record<string, number[]> = {
  fast: [5, 8, 6, 7, 9, 5, 6, 8, 7, 6],
  normal: [180, 200, 160, 180, 210, 170, 190, 180, 200, 180],
  slow: [600, 720, 540, 800, 660, 780, 700, 600, 720, 800],
  accelerating: [400, 360, 280, 200, 140, 100, 80, 60, 40, 25],
  decelerating: [25, 40, 60, 80, 100, 140, 200, 280, 360, 400],
};

// ── Math helpers ──────────────────────────────────────────────────
function bm(): number {
  let u = Math.random();
  const v = Math.random();
  if (u < 1e-12) u = 1e-12;
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function sample(
  N: number,
  mu: number,
  sig: number,
  c: number,
  cap: number,
): Float64Array {
  const o = new Float64Array(N);
  for (let i = 0; i < N; i++) {
    o[i] = Math.min(cap, Math.max(0, Math.exp(mu + sig * bm()) * c));
  }
  return o;
}

function pct(s: number[], p: number): number {
  return s[Math.min(s.length - 1, Math.max(0, Math.floor(p * s.length)))];
}

function st(d: Float64Array) {
  const s = Array.from(d).sort((a, b) => a - b);
  return {
    min: s[0],
    p25: pct(s, 0.25),
    median: pct(s, 0.5),
    p75: pct(s, 0.75),
    p90: pct(s, 0.9),
    p99: pct(s, 0.99),
    max: s[s.length - 1],
    sorted: s,
  };
}

function fmt(s: number | null | undefined): string {
  if (s == null || Number.isNaN(s)) return "—";
  if (s < 1) return `${(s * 1e3) | 0}ms`;
  if (s < 60) return `${s.toFixed(1)}s`;
  if (s < 3600) return `${(s / 60).toFixed(1)}m`;
  return `${(s / 3600).toFixed(2)}h`;
}

function logBins(cap: number, n = 36): number[] {
  const lo = Math.log(0.1),
    hi = Math.log(Math.max(cap, 1.1)),
    step = (hi - lo) / n,
    e: number[] = [];
  for (let i = 0; i <= n; i++) e.push(Math.exp(lo + i * step));
  return e;
}

function bin(d: Float64Array, edges: number[]): number[] {
  const c = new Array(edges.length - 1).fill(0);
  for (let i = 0; i < d.length; i++) {
    let lo = 0,
      hi = edges.length - 1;
    while (lo < hi - 1) {
      const m = (lo + hi) >> 1;
      if (d[i] < edges[m]) hi = m;
      else lo = m;
    }
    c[lo]++;
  }
  return c;
}

// EWMA momentum: returns the M coefficient AT EACH STEP (oldest first).
function ewmaTrace(
  gaps: number[],
  baseline: number,
  alpha = ALPHA,
): number[] {
  const out: number[] = [];
  let s = baseline;
  for (const g of gaps) {
    s = alpha * g + (1 - alpha) * s;
    const m = Math.max(M_LO, Math.min(M_HI, s / baseline));
    out.push(m);
  }
  return out;
}

// Feedback-spiral simulation: user mirrors Nikita's last delay with rho.
function feedbackSim(rho: number, chapter: number, steps = 20) {
  const baseline = BASELINES_S[chapter];
  const cap = CAPS_S[chapter];
  const coeff = [0.15, 0.3, 0.5, 0.75, 1.0][chapter - 1];
  let s = baseline;
  let userGap = baseline;
  const userSeries: number[] = [];
  const nikSeries: number[] = [];
  for (let i = 0; i < steps; i++) {
    s = ALPHA * userGap + (1 - ALPHA) * s;
    const m = Math.max(M_LO, Math.min(M_HI, s / baseline));
    const nikDelay = Math.min(cap, Math.exp(2.996 + 1.714 * bm()) * coeff * m);
    userSeries.push(userGap);
    nikSeries.push(nikDelay);
    // Next user gap mirrors Nikita's delay with weight rho, plus log-normal noise.
    const noise = Math.exp(0.5 * bm()) * baseline * 0.5;
    userGap = rho * nikDelay + (1 - rho) * noise;
    if (userGap < 1) userGap = 1;
  }
  return { userSeries, nikSeries };
}

// ── Style maps ────────────────────────────────────────────────────
const mono: React.CSSProperties = {
  fontFamily:
    "'JetBrains Mono', ui-monospace, 'SF Mono', 'Cascadia Code', monospace",
};
const sans: React.CSSProperties = {
  fontFamily:
    "ui-sans-serif, system-ui, -apple-system, sans-serif",
};

// ── Primitives ────────────────────────────────────────────────────
function Card({
  children,
  className = "",
  style = {},
}: {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      className={className}
      style={{
        background: T.surface,
        padding: "24px 28px",
        border: `1px solid ${T.border}`,
        borderRadius: 0,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

function CardLabel({
  children,
  sub,
}: {
  children: React.ReactNode;
  sub?: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div
        style={{
          ...mono,
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          color: T.textMuted,
        }}
      >
        {children}
      </div>
      {sub && (
        <div style={{ fontSize: 12, color: T.textDim, marginTop: 3 }}>
          {sub}
        </div>
      )}
    </div>
  );
}

function SL({
  num,
  title,
  sub,
}: {
  num: number | string;
  title: string;
  sub?: React.ReactNode;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        gap: 12,
        marginBottom: 24,
      }}
    >
      <span
        style={{
          ...mono,
          color: T.textDim,
          fontSize: 11,
          letterSpacing: "0.1em",
        }}
      >
        {String(num).padStart(2, "0")}
      </span>
      <h2
        style={{
          ...sans,
          color: T.text,
          fontSize: 18,
          fontWeight: 500,
          letterSpacing: "-0.01em",
          margin: 0,
        }}
      >
        {title}
      </h2>
      {sub && <span style={{ fontSize: 12, color: T.textMuted }}>{sub}</span>}
    </div>
  );
}

function Tag({
  children,
  color = T.textMuted,
  bg = "rgba(255,255,255,0.04)",
}: {
  children: React.ReactNode;
  color?: string;
  bg?: string;
}) {
  return (
    <span
      style={{
        ...mono,
        display: "inline-block",
        fontSize: 10,
        fontWeight: 500,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        padding: "3px 8px",
        borderRadius: 0,
        color,
        background: bg,
      }}
    >
      {children}
    </span>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  step,
  onChange,
  format,
}: {
  label: React.ReactNode;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
  format?: (v: number) => string;
}) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 6,
        }}
      >
        <span style={{ fontSize: 12, color: T.textMuted }}>{label}</span>
        <span style={{ ...mono, fontSize: 11, color: T.accent }}>
          {format ? format(value) : value}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        style={{ width: "100%", accentColor: T.accent, height: 2 }}
      />
    </div>
  );
}

function Btn({
  children,
  onClick,
  glow,
  style: sx = {},
}: {
  children: React.ReactNode;
  onClick: () => void;
  glow?: boolean;
  style?: React.CSSProperties;
}) {
  const base: React.CSSProperties = {
    ...mono,
    fontSize: 11,
    padding: "7px 16px",
    border: `1px solid ${T.border}`,
    cursor: "pointer",
    background: glow ? T.accentDim : T.surfaceUp,
    color: glow ? T.accent : T.textMuted,
    borderColor: glow ? "rgba(243,131,187,0.25)" : T.border,
    borderRadius: 0,
    ...sx,
  };
  return (
    <button onClick={onClick} style={base}>
      {children}
    </button>
  );
}

// ── Section 03: Monte Carlo Simulator ────────────────────────────
function Sim() {
  const [mu, setMu] = useState(2.996);
  const [sig, setSig] = useState(1.714);
  const [cap, setCap] = useState(1800);
  const [N, setN] = useState(10000);
  const [co, setCo] = useState<number[]>([0.15, 0.3, 0.5, 0.75, 1.0]);
  const [seed, setSeed] = useState(0);

  const setC = (i: number, v: number) => {
    const n = [...co];
    n[i] = v;
    setCo(n);
  };
  const load = (k: keyof typeof PRESETS) => {
    const p = PRESETS[k];
    setCo([...p.coeffs]);
    setCap(p.cap);
    setMu(p.mu);
    setSig(p.sigma);
    setSeed((s) => s + 1);
  };

  const smp = useMemo(
    () => co.map((c) => sample(N, mu, sig, c, cap)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [N, mu, sig, cap, co, seed],
  );
  const sts = useMemo(() => smp.map(st), [smp]);
  const edges = useMemo(() => logBins(cap, 36), [cap]);

  const hd = useMemo(() => {
    const bc = smp.map((s) => bin(s, edges));
    return Array.from({ length: edges.length - 1 }, (_, i) => {
      const r: Record<string, string | number> = { bl: fmt(edges[i]) };
      for (let c = 0; c < 5; c++) r[`c${c + 1}`] = bc[c][i];
      return r;
    });
  }, [smp, edges]);

  const cd = useMemo(() => {
    const g: number[] = [];
    const nG = 60;
    for (let i = 0; i < nG; i++) {
      const f = i / (nG - 1);
      g.push(Math.exp(Math.log(0.1) + f * (Math.log(cap) - Math.log(0.1))));
    }
    return g.map((x) => {
      const r: Record<string, number> = { x };
      for (let c = 0; c < 5; c++) {
        const s = sts[c].sorted;
        let lo = 0,
          hi = s.length;
        while (lo < hi) {
          const m = (lo + hi) >> 1;
          if (s[m] < x) lo = m + 1;
          else hi = m;
        }
        r[`c${c + 1}`] = lo / s.length;
      }
      return r;
    });
  }, [sts, cap]);

  const tip = {
    background: T.surfaceUp,
    border: `1px solid ${T.border}`,
    borderRadius: 0,
    fontSize: 11,
    color: T.text,
    boxShadow: `0 8px 40px rgba(0,0,0,0.6), 0 0 20px ${T.accentGlow}`,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 8,
          marginBottom: 16,
        }}
      >
        {Object.entries(PRESETS).map(([k, p]) => (
          <Btn key={k} onClick={() => load(k as keyof typeof PRESETS)}>
            {p.label}
          </Btn>
        ))}
        <Btn glow onClick={() => setSeed((s) => s + 1)} style={{ marginLeft: "auto" }}>
          ↻ Resample
        </Btn>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 1 }}>
        <Card>
          <CardLabel>Distribution</CardLabel>
          <Slider
            label="μ  log-median"
            value={mu}
            min={1.5}
            max={4.5}
            step={0.01}
            onChange={setMu}
            format={(v) => `${v.toFixed(2)}  →  ${Math.exp(v).toFixed(1)}s`}
          />
          <Slider
            label="σ  log-spread"
            value={sig}
            min={0.3}
            max={2.5}
            step={0.01}
            onChange={setSig}
            format={(v) => v.toFixed(3)}
          />
          <Slider
            label="Hard cap"
            value={cap}
            min={60}
            max={7200}
            step={60}
            onChange={setCap}
            format={fmt}
          />
          <Slider
            label="N samples"
            value={N}
            min={1000}
            max={100000}
            step={1000}
            onChange={setN}
            format={(v) => v.toLocaleString()}
          />
        </Card>
        <Card>
          <CardLabel>Chapter coefficients</CardLabel>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 32px" }}>
            {co.map((c, i) => (
              <Slider
                key={i}
                label={
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span
                      style={{
                        width: 7,
                        height: 7,
                        borderRadius: "50%",
                        background: CH[i],
                        display: "inline-block",
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ color: T.text }}>Ch {i + 1}</span>
                    <span style={{ color: T.textDim, fontSize: 11 }}>{CH_FEELS[i]}</span>
                  </span>
                }
                value={c}
                min={0.02}
                max={3.0}
                step={0.01}
                onChange={(v) => setC(i, v)}
                format={(v) => `×${v.toFixed(2)}`}
              />
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <CardLabel
          sub={`log-normal(${mu.toFixed(2)}, ${sig.toFixed(2)}) × coeff · cap ${fmt(cap)} · n = ${N.toLocaleString()}`}
        >
          Percentiles
        </CardLabel>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", ...mono, fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                {["", "Coeff", "p50", "p75", "p90", "p99", "Max", "@ cap"].map((h, i) => (
                  <th
                    key={i}
                    style={{
                      textAlign: "left",
                      padding: "8px 14px 8px 0",
                      fontWeight: 500,
                      color: T.textDim,
                      fontSize: 10,
                      letterSpacing: "0.1em",
                      textTransform: "uppercase",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sts.map((s, i) => {
                const ac = Array.from(smp[i]).reduce((a, v) => a + (v >= cap - 0.01 ? 1 : 0), 0);
                return (
                  <tr key={i} style={{ borderBottom: `1px solid ${T.border}` }}>
                    <td style={{ padding: "10px 14px 10px 0" }}>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                        <span style={{ width: 6, height: 6, borderRadius: "50%", background: CH[i] }} />
                        <span style={{ color: T.text }}>Ch {i + 1}</span>
                      </span>
                    </td>
                    <td style={{ padding: "10px 14px 10px 0", color: T.textMuted }}>
                      ×{co[i].toFixed(2)}
                    </td>
                    <td style={{ padding: "10px 14px 10px 0", color: T.accent, fontWeight: 600 }}>
                      {fmt(s.median)}
                    </td>
                    <td style={{ padding: "10px 14px 10px 0", color: T.text }}>{fmt(s.p75)}</td>
                    <td style={{ padding: "10px 14px 10px 0", color: T.text }}>{fmt(s.p90)}</td>
                    <td style={{ padding: "10px 14px 10px 0", color: T.text }}>{fmt(s.p99)}</td>
                    <td style={{ padding: "10px 14px 10px 0", color: T.textMuted }}>{fmt(s.max)}</td>
                    <td style={{ padding: "10px 14px 10px 0", color: T.textDim }}>
                      {((ac / N) * 100).toFixed(2)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
        <Card>
          <CardLabel>Histogram</CardLabel>
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <BarChart data={hd}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis
                  dataKey="bl"
                  tick={{ fontSize: 9, fill: T.textDim }}
                  interval={4}
                  angle={-30}
                  textAnchor="end"
                  height={44}
                  axisLine={{ stroke: T.border }}
                  tickLine={false}
                />
                <YAxis tick={{ fontSize: 10, fill: T.textDim }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tip} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                <Legend wrapperStyle={{ fontSize: 11, color: T.textMuted }} />
                {[0, 1, 2, 3, 4].map((i) => (
                  <Bar
                    key={i}
                    dataKey={`c${i + 1}`}
                    fill={CH[i]}
                    name={CH_LABELS[i]}
                    stackId="a"
                    opacity={0.85}
                    radius={0}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <CardLabel>CDF — P(delay ≤ x)</CardLabel>
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <LineChart data={cd}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis
                  dataKey="x"
                  scale="log"
                  domain={[0.5, cap]}
                  type="number"
                  tickFormatter={fmt}
                  tick={{ fontSize: 10, fill: T.textDim }}
                  allowDataOverflow
                  axisLine={{ stroke: T.border }}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 1]}
                  tickFormatter={(v) => `${(v * 100) | 0}%`}
                  tick={{ fontSize: 10, fill: T.textDim }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={tip}
                  labelFormatter={(v) => `delay ≤ ${fmt(v as number)}`}
                  formatter={(v) => `${((v as number) * 100).toFixed(1)}%`}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <ReferenceLine y={0.5} stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
                <ReferenceLine y={0.9} stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
                {[0, 1, 2, 3, 4].map((i) => (
                  <Line
                    key={i}
                    type="monotone"
                    dataKey={`c${i + 1}`}
                    stroke={CH[i]}
                    strokeWidth={1.5}
                    dot={false}
                    name={CH_LABELS[i]}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  );
}

// ── Section 04: Chapter 1 floor ─────────────────────────────────
function Ch1Floor() {
  const ch1Cdf = useMemo(() => {
    const samples = sample(20000, 2.996, 1.714, 0.15, CAPS_S[1]);
    const sorted = Array.from(samples).sort((a, b) => a - b);
    const out: { x: number; p: number }[] = [];
    const n = 50;
    for (let i = 0; i < n; i++) {
      const x = (i / (n - 1)) * CAPS_S[1] * 1.1;
      let lo = 0,
        hi = sorted.length;
      while (lo < hi) {
        const m = (lo + hi) >> 1;
        if (sorted[m] < x) lo = m + 1;
        else hi = m;
      }
      out.push({ x, p: lo / sorted.length });
    }
    return out;
  }, []);
  const tip = {
    background: T.surfaceUp,
    border: `1px solid ${T.border}`,
    borderRadius: 0,
    fontSize: 11,
    color: T.text,
  };
  return (
    <Card>
      <div style={{ display: "grid", gridTemplateColumns: "2fr 3fr", gap: 32 }}>
        <div>
          <Tag color={T.accent} bg={T.accentDim}>
            Ch 1 has a 10s ceiling
          </Tag>
          <p style={{ fontSize: 13, color: T.textMuted, lineHeight: 1.7, marginTop: 16 }}>
            With coeff 0.15 the median Ch 1 delay is ≈ 3 seconds. The 10-second hard cap guarantees no
            tail sample escapes — even at a 10σ Z value, the clamped result remains ≤ 10s.
          </p>
          <p style={{ fontSize: 12, color: T.textDim, lineHeight: 1.7, marginTop: 12 }}>
            Users in the infatuation phase rarely wait more than a heartbeat, satisfying the &ldquo;almost
            never any wait&rdquo; design intent.
          </p>
        </div>
        <div style={{ width: "100%", height: 240 }}>
          <ResponsiveContainer>
            <LineChart data={ch1Cdf}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="x"
                type="number"
                domain={[0, 11]}
                tickFormatter={(v) => `${v}s`}
                tick={{ fontSize: 10, fill: T.textDim }}
                axisLine={{ stroke: T.border }}
                tickLine={false}
              />
              <YAxis
                domain={[0, 1]}
                tickFormatter={(v) => `${(v * 100) | 0}%`}
                tick={{ fontSize: 10, fill: T.textDim }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={tip}
                formatter={(v) => `${((v as number) * 100).toFixed(1)}%`}
                labelFormatter={(v) => `delay ≤ ${(v as number).toFixed(1)}s`}
              />
              <ReferenceLine x={10} stroke={T.accent} strokeDasharray="4 4" label={{ value: "cap = 10s", position: "top", fill: T.accent, fontSize: 11 }} />
              <Line type="monotone" dataKey="p" stroke={CH[0]} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Card>
  );
}

// ── Section 05: Momentum simulator ───────────────────────────────
function MomentumSim() {
  const [chapter, setChapter] = useState(3);
  const [trace, setTrace] = useState<keyof typeof TRACE_PRESETS>("normal");
  const [rho, setRho] = useState(0.5);
  const [feedbackChapter, setFeedbackChapter] = useState(3);
  const [feedbackSeed, setFeedbackSeed] = useState(0);

  const baseline = BASELINES_S[chapter];
  const traceData = useMemo(() => {
    const ms = ewmaTrace(TRACE_PRESETS[trace], baseline);
    return ms.map((m, i) => ({ idx: i + 1, M: m, gap: TRACE_PRESETS[trace][i] }));
  }, [trace, baseline]);

  const fb = useMemo(
    () => feedbackSim(rho, feedbackChapter),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [rho, feedbackChapter, feedbackSeed],
  );
  const fbData = fb.userSeries.map((u, i) => ({
    step: i + 1,
    user: u,
    nikita: fb.nikSeries[i],
  }));

  const tip = {
    background: T.surfaceUp,
    border: `1px solid ${T.border}`,
    borderRadius: 0,
    fontSize: 11,
    color: T.text,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
      {/* Formula card */}
      <Card>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
          <div>
            <Tag color={T.accent} bg={T.accentDim}>
              Formula
            </Tag>
            <div
              style={{
                ...mono,
                fontSize: 17,
                color: T.text,
                marginTop: 16,
                lineHeight: 1.4,
              }}
            >
              M = clip( EWMA<sub>α</sub>(g<sub>1..N</sub>) / B<sub>ch</sub>, 0.1, 5.0 )
            </div>
            <p style={{ fontSize: 12, color: T.textDim, lineHeight: 1.7, marginTop: 12 }}>
              Multiplicative coefficient applied AFTER the chapter coefficient. EWMA seeded at the
              chapter baseline so the prior dominates on cold start.
            </p>
          </div>
          <div>
            <Tag color={T.lavender} bg={T.lavDim}>
              Constants
            </Tag>
            <table style={{ ...mono, fontSize: 12, marginTop: 16, width: "100%", borderCollapse: "collapse" }}>
              <tbody>
                {[
                  ["α", "0.35", "EWMA smoothing"],
                  ["B[1..5]", "300, 240, 180, 120, 90 s", "chapter prior"],
                  ["M_LO", "0.1", "lower clip"],
                  ["M_HI", "5.0", "upper clip"],
                  ["window", "last 10 user gaps", "≤15-min session filter"],
                ].map(([k, v, n], i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${T.border}` }}>
                    <td style={{ padding: "8px 12px 8px 0", color: T.textDim }}>{k}</td>
                    <td style={{ padding: "8px 12px 8px 0", color: T.accent, fontWeight: 500 }}>{v}</td>
                    <td style={{ padding: "8px 0", color: T.textDim }}>{n}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Card>

      {/* Trace simulator */}
      <Card>
        <CardLabel sub={`Chapter baseline B = ${baseline}s · α = 0.35`}>
          Trace simulator — M vs message index
        </CardLabel>
        <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
          {(Object.keys(TRACE_PRESETS) as Array<keyof typeof TRACE_PRESETS>).map((k) => (
            <Btn key={k} glow={trace === k} onClick={() => setTrace(k)}>
              {k}
            </Btn>
          ))}
          <span style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
            {[1, 2, 3, 4, 5].map((c) => (
              <Btn key={c} glow={chapter === c} onClick={() => setChapter(c)}>
                Ch {c}
              </Btn>
            ))}
          </span>
        </div>
        <div style={{ width: "100%", height: 260 }}>
          <ResponsiveContainer>
            <LineChart data={traceData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="idx" tick={{ fontSize: 10, fill: T.textDim }} axisLine={{ stroke: T.border }} tickLine={false} />
              <YAxis
                domain={[0, 5.2]}
                tick={{ fontSize: 10, fill: T.textDim }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip contentStyle={tip} formatter={(v, n) => (n === "M" ? (v as number).toFixed(3) : `${(v as number).toFixed(0)}s`)} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <ReferenceLine y={1} stroke={T.textDim} strokeDasharray="4 4" label={{ value: "neutral", position: "right", fill: T.textDim, fontSize: 10 }} />
              <ReferenceLine y={M_LO} stroke="rgba(255,255,255,0.12)" strokeDasharray="2 4" />
              <ReferenceLine y={M_HI} stroke="rgba(255,255,255,0.12)" strokeDasharray="2 4" />
              <Line type="monotone" dataKey="M" stroke={CH[chapter - 1]} strokeWidth={2} dot={{ r: 3 }} name="M" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p style={{ fontSize: 11, color: T.textDim, marginTop: 12, ...mono }}>
          gaps = {TRACE_PRESETS[trace].map((g) => g.toFixed(0)).join(", ")}s
        </p>
      </Card>

      {/* Feedback-spiral demo */}
      <Card>
        <CardLabel sub={`User mirrors Nikita's prior delay with weight ρ; runs 20 message steps.`}>
          Feedback-spiral demo
        </CardLabel>
        <div style={{ display: "flex", gap: 16, alignItems: "flex-end", marginBottom: 16 }}>
          <div style={{ flex: 1, maxWidth: 320 }}>
            <Slider
              label={`ρ  user mirror weight`}
              value={rho}
              min={0}
              max={1}
              step={0.05}
              onChange={setRho}
              format={(v) => v.toFixed(2)}
            />
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            {[1, 2, 3, 4, 5].map((c) => (
              <Btn key={c} glow={feedbackChapter === c} onClick={() => setFeedbackChapter(c)}>
                Ch {c}
              </Btn>
            ))}
          </div>
          <Btn glow onClick={() => setFeedbackSeed((s) => s + 1)}>
            ↻ Resample
          </Btn>
        </div>
        <div style={{ width: "100%", height: 260 }}>
          <ResponsiveContainer>
            <LineChart data={fbData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="step" tick={{ fontSize: 10, fill: T.textDim }} axisLine={{ stroke: T.border }} tickLine={false} />
              <YAxis tickFormatter={fmt} tick={{ fontSize: 10, fill: T.textDim }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tip} formatter={(v) => fmt(v as number)} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="user" stroke={T.lavender} strokeWidth={1.5} dot={{ r: 2 }} name="User gap" />
              <Line type="monotone" dataKey="nikita" stroke={T.accent} strokeWidth={1.5} dot={{ r: 2 }} name="Nikita delay" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p style={{ fontSize: 11, color: T.textDim, marginTop: 12, lineHeight: 1.7 }}>
          Even at ρ = 1 (full mirror), the system stays bounded — caps + M_HI prevent runaway escalation.
        </p>
      </Card>
    </div>
  );
}

// ── Shared regimes for the new plot suite (06-10) ────────────────
const USER_REGIMES: { key: string; label: string; gapSec: number; color: string }[] = [
  { key: "hyper", label: "1s — hyper", gapSec: 1, color: "#F383BB" },
  { key: "fast", label: "10s — fast", gapSec: 10, color: "#E58FCF" },
  { key: "normal", label: "1m — normal", gapSec: 60, color: "#C28DD7" },
  { key: "slow", label: "5m — slow", gapSec: 300, color: "#A98AD7" },
  { key: "veryslow", label: "10m — very slow", gapSec: 600, color: "#8E89D7" },
  { key: "cold", label: "30m — cold", gapSec: 1800, color: "#7BAAC8" },
];
const CHAPTER_COEFFS = [0.15, 0.3, 0.5, 0.75, 1.0] as const;
const MU_DEFAULT = 2.996;
const SIGMA_DEFAULT = 1.714;
const EXP_MU = Math.exp(MU_DEFAULT); // ≈20s

// Chapter selector chip (shared by sections 06-09)
function ChapterChips({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  return (
    <div
      style={{
        display: "flex",
        gap: 10,
        marginBottom: 20,
        padding: "14px 16px",
        background: T.surfaceUp,
        border: `1px solid ${T.border}`,
        alignItems: "center",
        flexWrap: "wrap",
      }}
    >
      <span
        style={{
          ...mono,
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          color: T.textMuted,
        }}
      >
        Chapter selector →
      </span>
      {[1, 2, 3, 4, 5].map((c) => (
        <button
          key={c}
          onClick={() => onChange(c)}
          style={{
            ...mono,
            fontSize: 12,
            padding: "8px 18px",
            border: `1px solid ${value === c ? T.accent : T.border}`,
            background: value === c ? T.accentDim : T.bg,
            color: value === c ? T.accent : T.textMuted,
            cursor: "pointer",
            borderRadius: 0,
            fontWeight: value === c ? 600 : 400,
            boxShadow: value === c ? `0 0 12px ${T.accentGlow}` : "none",
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-start",
            gap: 2,
            minWidth: 90,
          }}
        >
          <span>Ch {c}</span>
          <span style={{ fontSize: 9, color: value === c ? T.accent : T.textDim, letterSpacing: 0 }}>
            {CH_FEELS[c - 1]}
          </span>
        </button>
      ))}
    </div>
  );
}

// Compute E[delay] sequence for a constant user gap g across N msgs (deterministic).
// delay_t = chapter * exp(mu) * M_t, where M_t = clip(ewma_t / B_ch, M_LO, M_HI)
function deterministicSeq(
  gapSec: number,
  chapter: number,
  N: number,
): { idx: number; delay: number; M: number }[] {
  const baseline = BASELINES_S[chapter];
  const coeff = CHAPTER_COEFFS[chapter - 1];
  const cap = CAPS_S[chapter];
  const out: { idx: number; delay: number; M: number }[] = [];
  let ewma = baseline;
  for (let t = 1; t <= N; t++) {
    ewma = ALPHA * gapSec + (1 - ALPHA) * ewma;
    const m = Math.max(M_LO, Math.min(M_HI, ewma / baseline));
    const raw = coeff * EXP_MU * m;
    out.push({ idx: t, delay: Math.min(cap, raw), M: m });
  }
  return out;
}

// Compute one stochastic sample sequence (uses Box-Muller noise per step).
function stochasticSeq(
  gapSec: number,
  chapter: number,
  N: number,
): { idx: number; delay: number }[] {
  const baseline = BASELINES_S[chapter];
  const coeff = CHAPTER_COEFFS[chapter - 1];
  const cap = CAPS_S[chapter];
  const out: { idx: number; delay: number }[] = [];
  let ewma = baseline;
  for (let t = 1; t <= N; t++) {
    ewma = ALPHA * gapSec + (1 - ALPHA) * ewma;
    const m = Math.max(M_LO, Math.min(M_HI, ewma / baseline));
    const raw = coeff * Math.exp(MU_DEFAULT + SIGMA_DEFAULT * bm()) * m;
    out.push({ idx: t, delay: Math.min(cap, Math.max(0.01, raw)) });
  }
  return out;
}

// ── Section 06: Conversation transient (deterministic + stochastic) ──
function ConversationTransient() {
  const [chapter, setChapter] = useState(3);
  const [seed, setSeed] = useState(0);
  const N = 15;

  const detData = useMemo(() => {
    const seqs = USER_REGIMES.map((r) => deterministicSeq(r.gapSec, chapter, N));
    return Array.from({ length: N }, (_, i) => {
      const row: Record<string, number | string> = { idx: i + 1 };
      USER_REGIMES.forEach((r, ri) => {
        row[r.key] = seqs[ri][i].delay;
      });
      return row;
    });
  }, [chapter]);

  const sampData = useMemo(() => {
    const seqs = USER_REGIMES.map((r) => stochasticSeq(r.gapSec, chapter, N));
    return Array.from({ length: N }, (_, i) => {
      const row: Record<string, number | string> = { idx: i + 1 };
      USER_REGIMES.forEach((r, ri) => {
        row[r.key] = seqs[ri][i].delay;
      });
      return row;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapter, seed]);

  const cap = CAPS_S[chapter];
  const tip = {
    background: T.surfaceUp,
    border: `1px solid ${T.border}`,
    borderRadius: 0,
    fontSize: 11,
    color: T.text,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Card>
        <ChapterChips value={chapter} onChange={setChapter} />
        <p style={{ fontSize: 12, color: T.textDim, lineHeight: 1.7, margin: "0 0 10px" }}>
          Each curve = a user with a constant inter-message gap (1s → 30m). X-axis = consecutive
          new-conversation events. Y-axis = Nikita&rsquo;s response time (log scale, seconds).
        </p>
        <div
          style={{
            background: T.bg,
            border: `1px solid ${T.border}`,
            padding: "12px 14px",
            marginBottom: 8,
          }}
        >
          <div style={{ ...mono, fontSize: 10, fontWeight: 600, color: T.accent, letterSpacing: "0.1em", marginBottom: 6 }}>
            READING THE TRANSIENT
          </div>
          <ul style={{ fontSize: 12, color: T.textMuted, lineHeight: 1.75, margin: 0, paddingLeft: 18 }}>
            <li>
              <strong style={{ color: T.text }}>Slow-user curves rise</strong>, fast-user curves fall — monotone convergence to
              their steady state. No overshoot.
            </li>
            <li>
              The transient is the <strong style={{ color: T.accent }}>Bayesian prior at B<sub>ch</sub></strong> being
              overridden by observations. At message 1, <code style={{ ...mono, color: T.lavender }}>M_1 = 0.35·(g/B) + 0.65</code>{" "}
              — two-thirds prior, one-third observation. After ~3-5 messages, <code style={{ ...mono, color: T.lavender }}>M ≈ g/B</code>{" "}
              (the ratio).
            </li>
            <li>
              <strong style={{ color: T.text }}>Not driven by the cap.</strong> The cap only engages at extremes (e.g., a 30-min
              user on Ch 1: steady-state 15s → clamped to the 10s cap). Most curves plateau well below cap.
            </li>
            <li>
              Plots deliberately <strong style={{ color: T.text }}>ignore the ≥15min new-conversation gate</strong> — in
              production, in-session pings return 0 delay. This shows pure momentum dynamics.
            </li>
          </ul>
        </div>
      </Card>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
        <Card>
          <CardLabel sub="E[delay] = chapter × exp(μ) × M(t) — pure momentum signal, no log-normal noise">
            Deterministic transient
          </CardLabel>
          <div style={{ width: "100%", height: 300 }}>
            <ResponsiveContainer>
              <LineChart data={detData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis
                  dataKey="idx"
                  tick={{ fontSize: 10, fill: T.textDim }}
                  axisLine={{ stroke: T.border }}
                  tickLine={false}
                  label={{ value: "msg #", position: "bottom", fill: T.textDim, fontSize: 10, offset: -8 }}
                />
                <YAxis
                  scale="log"
                  domain={[0.05, cap * 1.2]}
                  tickFormatter={fmt}
                  tick={{ fontSize: 10, fill: T.textDim }}
                  axisLine={false}
                  tickLine={false}
                  type="number"
                  allowDataOverflow
                />
                <Tooltip
                  contentStyle={tip}
                  formatter={(v, n) => [fmt(v as number), USER_REGIMES.find((r) => r.key === n)?.label || n]}
                />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <ReferenceLine y={cap} stroke={T.accent} strokeDasharray="4 4" label={{ value: `cap ${cap}s`, position: "right", fill: T.accent, fontSize: 10 }} />
                {USER_REGIMES.map((r) => (
                  <Line
                    key={r.key}
                    type="monotone"
                    dataKey={r.key}
                    stroke={r.color}
                    strokeWidth={1.6}
                    dot={false}
                    name={r.label}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <CardLabel sub="One sampled trajectory per regime — log-normal noise around the deterministic curve">
            Stochastic trajectory
            <span style={{ marginLeft: 12 }}>
              <Btn glow onClick={() => setSeed((s) => s + 1)}>↻ resample</Btn>
            </span>
          </CardLabel>
          <div style={{ width: "100%", height: 300 }}>
            <ResponsiveContainer>
              <LineChart data={sampData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="idx" tick={{ fontSize: 10, fill: T.textDim }} axisLine={{ stroke: T.border }} tickLine={false} />
                <YAxis
                  scale="log"
                  domain={[0.05, cap * 1.2]}
                  tickFormatter={fmt}
                  tick={{ fontSize: 10, fill: T.textDim }}
                  axisLine={false}
                  tickLine={false}
                  type="number"
                  allowDataOverflow
                />
                <Tooltip
                  contentStyle={tip}
                  formatter={(v, n) => [fmt(v as number), USER_REGIMES.find((r) => r.key === n)?.label || n]}
                />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <ReferenceLine y={cap} stroke={T.accent} strokeDasharray="4 4" />
                {USER_REGIMES.map((r) => (
                  <Line
                    key={r.key}
                    type="monotone"
                    dataKey={r.key}
                    stroke={r.color}
                    strokeWidth={1.4}
                    dot={{ r: 2 }}
                    name={r.label}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  );
}

// ── Section 07: Cold-start distribution after 10-msg warm-up ──────
function ColdStartDistribution() {
  const [chapter, setChapter] = useState(3);
  const [seed, setSeed] = useState(0);
  const N_TRIALS = 4000;
  const N_WARMUP = 10;

  // For each regime: simulate 4000 trials of 10-message warm-up at that avg gap,
  // then sample one Nikita response. Bin into log-spaced histogram.
  const data = useMemo(() => {
    const baseline = BASELINES_S[chapter];
    const coeff = CHAPTER_COEFFS[chapter - 1];
    const cap = CAPS_S[chapter];
    const edges = logBins(cap, 28);

    const perRegime: Record<string, number[]> = {};
    USER_REGIMES.forEach((r) => {
      const samples: number[] = [];
      for (let t = 0; t < N_TRIALS; t++) {
        let ewma = baseline;
        for (let i = 0; i < N_WARMUP; i++) {
          // gaps drawn from log-normal centered at regime
          const g = Math.exp(Math.log(r.gapSec) + 0.4 * bm());
          ewma = ALPHA * g + (1 - ALPHA) * ewma;
        }
        const m = Math.max(M_LO, Math.min(M_HI, ewma / baseline));
        const delay = Math.min(cap, Math.max(0.01, coeff * Math.exp(MU_DEFAULT + SIGMA_DEFAULT * bm()) * m));
        samples.push(delay);
      }
      perRegime[r.key] = samples;
    });

    // Build chart rows: { bl: edge label, hyper: count, fast: count, ... }
    return Array.from({ length: edges.length - 1 }, (_, i) => {
      const row: Record<string, number | string> = { bl: fmt(edges[i]) };
      USER_REGIMES.forEach((r) => {
        let c = 0;
        for (const v of perRegime[r.key]) {
          if (v >= edges[i] && v < edges[i + 1]) c++;
        }
        row[r.key] = c / N_TRIALS;
      });
      return row;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapter, seed]);

  const tip = {
    background: T.surfaceUp,
    border: `1px solid ${T.border}`,
    borderRadius: 0,
    fontSize: 11,
    color: T.text,
  };

  return (
    <Card>
      <ChapterChips value={chapter} onChange={setChapter} />
      <p style={{ fontSize: 12, color: T.textDim, lineHeight: 1.7, margin: "0 0 16px" }}>
        After 10 prior user messages at average gap g, what does Nikita&rsquo;s next response time
        distribution look like? Each regime is 4&thinsp;000 trials. Fast-user regimes pile up at the low
        end (M clamped to 0.1); slow-user regimes shift right and saturate at the chapter cap.
        <span style={{ marginLeft: 12 }}>
          <Btn glow onClick={() => setSeed((s) => s + 1)}>↻ resample</Btn>
        </span>
      </p>
      <div style={{ width: "100%", height: 320 }}>
        <ResponsiveContainer>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis
              dataKey="bl"
              tick={{ fontSize: 9, fill: T.textDim }}
              interval={3}
              angle={-30}
              textAnchor="end"
              height={50}
              axisLine={{ stroke: T.border }}
              tickLine={false}
            />
            <YAxis
              tickFormatter={(v) => `${(v * 100).toFixed(1)}%`}
              tick={{ fontSize: 10, fill: T.textDim }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={tip}
              formatter={(v, n) => [`${((v as number) * 100).toFixed(2)}%`, USER_REGIMES.find((r) => r.key === n)?.label || n]}
            />
            <Legend wrapperStyle={{ fontSize: 10 }} />
            {USER_REGIMES.map((r) => (
              <Bar key={r.key} dataKey={r.key} fill={r.color} name={r.label} opacity={0.6} radius={0} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

// ── Section 08: Chapter × cadence heatmap ─────────────────────────
function ChapterCadenceHeatmap() {
  // Compute median Nikita response time for each (chapter, regime) cell using 2000 trials.
  const cells = useMemo(() => {
    const out: { ch: number; key: string; label: string; gap: number; median: number; cap: number }[] = [];
    for (let ch = 1; ch <= 5; ch++) {
      const baseline = BASELINES_S[ch];
      const coeff = CHAPTER_COEFFS[ch - 1];
      const cap = CAPS_S[ch];
      for (const r of USER_REGIMES) {
        const samples: number[] = [];
        for (let t = 0; t < 2000; t++) {
          let ewma = baseline;
          for (let i = 0; i < 10; i++) {
            const g = Math.exp(Math.log(r.gapSec) + 0.4 * bm());
            ewma = ALPHA * g + (1 - ALPHA) * ewma;
          }
          const m = Math.max(M_LO, Math.min(M_HI, ewma / baseline));
          const d = Math.min(cap, Math.max(0.01, coeff * Math.exp(MU_DEFAULT + SIGMA_DEFAULT * bm()) * m));
          samples.push(d);
        }
        samples.sort((a, b) => a - b);
        out.push({ ch, key: r.key, label: r.label, gap: r.gapSec, median: samples[samples.length >> 1], cap });
      }
    }
    return out;
  }, []);

  // Color scale: log-time mapped to gradient pink (low) → lavender (mid) → cool (high).
  function color(median: number, cap: number): string {
    const t = Math.max(0, Math.min(1, Math.log(median + 0.5) / Math.log(cap + 0.5)));
    // Interpolate among 5 stops to mirror chapter palette
    const stops = [
      { p: 0, c: [243, 131, 187] }, // pink
      { p: 0.25, c: [210, 131, 215] },
      { p: 0.5, c: [169, 138, 215] },
      { p: 0.75, c: [129, 134, 215] }, // lavender
      { p: 1, c: [123, 170, 200] },
    ];
    let lo = stops[0],
      hi = stops[stops.length - 1];
    for (let i = 0; i < stops.length - 1; i++) {
      if (t >= stops[i].p && t <= stops[i + 1].p) {
        lo = stops[i];
        hi = stops[i + 1];
        break;
      }
    }
    const span = hi.p - lo.p;
    const f = span > 0 ? (t - lo.p) / span : 0;
    const rgb = lo.c.map((cc, i) => Math.round(cc + (hi.c[i] - cc) * f));
    const alpha = 0.35 + 0.55 * t; // brighter for higher delays
    return `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${alpha.toFixed(2)})`;
  }

  return (
    <Card>
      <p style={{ fontSize: 12, color: T.textDim, lineHeight: 1.7, margin: "0 0 16px" }}>
        Median Nikita response time per (chapter × user-cadence) cell, after a 10-message warm-up at
        the row&rsquo;s avg gap. The diagonal shape shows where momentum interacts with chapter caps.
        Top-left = ultra-fast (Ch 1 + hyper user) ≈ 0.3s; bottom-right = slow (Ch 5 + cold user) ≈
        cap.
      </p>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", ...mono, fontSize: 11 }}>
          <thead>
            <tr>
              <th style={{ padding: "8px 10px", color: T.textDim, fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase", textAlign: "left" }}>
                user cadence ↓ / chapter →
              </th>
              {[1, 2, 3, 4, 5].map((ch) => (
                <th key={ch} style={{ padding: "8px 10px", color: T.text, fontSize: 11, textAlign: "center", borderBottom: `1px solid ${T.border}` }}>
                  Ch {ch}
                  <div style={{ fontSize: 9, color: T.textDim, marginTop: 2 }}>{CH_FEELS[ch - 1]}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {USER_REGIMES.map((r) => (
              <tr key={r.key}>
                <td style={{ padding: "10px", color: T.text, borderRight: `1px solid ${T.border}` }}>
                  <span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
                    <span style={{ width: 8, height: 8, background: r.color, display: "inline-block" }} />
                    {r.label}
                  </span>
                </td>
                {[1, 2, 3, 4, 5].map((ch) => {
                  const cell = cells.find((c) => c.ch === ch && c.key === r.key)!;
                  return (
                    <td
                      key={ch}
                      style={{
                        padding: "12px 10px",
                        background: color(cell.median, cell.cap),
                        textAlign: "center",
                        color: cell.median > cell.cap * 0.4 ? T.text : T.bg,
                        fontWeight: 500,
                        border: `1px solid ${T.border}`,
                      }}
                      title={`Ch ${ch} · ${r.label} · cap ${cell.cap}s`}
                    >
                      {fmt(cell.median)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ── Section 09: Persona day ───────────────────────────────────────
type Persona = { name: string; color: string; gen: () => number[] };
const PERSONAS: Persona[] = [
  {
    name: "Ghoster",
    color: "#7BAAC8",
    gen: () => {
      // Long silences punctuated by short bursts.
      const out: number[] = [];
      while (out.length < 24) {
        if (Math.random() < 0.7) {
          out.push(3600 + Math.exp(Math.log(3600) + bm()));
        } else {
          out.push(Math.exp(Math.log(15) + 0.5 * bm()));
        }
      }
      return out.slice(0, 24);
    },
  },
  {
    name: "Chatty Cathy",
    color: "#F383BB",
    gen: () => {
      const out: number[] = [];
      for (let i = 0; i < 24; i++) {
        out.push(Math.max(1, Math.exp(Math.log(20) + 0.6 * bm())));
      }
      return out;
    },
  },
  {
    name: "Bored-replier",
    color: "#A985D7",
    gen: () => {
      const out: number[] = [];
      for (let i = 0; i < 24; i++) {
        out.push(Math.max(1, Math.exp(Math.log(300) + 0.5 * bm())));
      }
      return out;
    },
  },
];

function PersonaDay() {
  const [chapter, setChapter] = useState(3);
  const [seed, setSeed] = useState(0);

  const data = useMemo(() => {
    const baseline = BASELINES_S[chapter];
    const coeff = CHAPTER_COEFFS[chapter - 1];
    const cap = CAPS_S[chapter];
    const series: Record<string, { idx: number; userGap: number; nikDelay: number }[]> = {};
    PERSONAS.forEach((p) => {
      const gaps = p.gen();
      let ewma = baseline;
      const persona: { idx: number; userGap: number; nikDelay: number }[] = [];
      for (let i = 0; i < gaps.length; i++) {
        const g = gaps[i];
        // session filter — drop gaps >= 900 from EWMA (matches _compute_user_gaps)
        if (g < 900) {
          ewma = ALPHA * Math.max(1, g) + (1 - ALPHA) * ewma;
        }
        const m = Math.max(M_LO, Math.min(M_HI, ewma / baseline));
        // gate: if user gap < 900, in-session → 0 delay; else new-conv → log-normal × M
        const gateFires = g >= 900;
        const nik = gateFires
          ? Math.min(cap, Math.max(0.01, coeff * Math.exp(MU_DEFAULT + SIGMA_DEFAULT * bm()) * m))
          : 0;
        persona.push({ idx: i + 1, userGap: g, nikDelay: nik });
      }
      series[p.name] = persona;
    });

    // Build flat rows: { idx, ghoster_user, ghoster_nik, chatty_user, ... }
    return Array.from({ length: 24 }, (_, i) => {
      const row: Record<string, number | string> = { idx: i + 1 };
      PERSONAS.forEach((p) => {
        const key = p.name.toLowerCase().replace(/[^a-z]/g, "");
        row[`${key}_user`] = series[p.name][i].userGap;
        row[`${key}_nik`] = series[p.name][i].nikDelay || 0.5; // floor for log scale
      });
      return row;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapter, seed]);

  const cap = CAPS_S[chapter];
  const tip = {
    background: T.surfaceUp,
    border: `1px solid ${T.border}`,
    borderRadius: 0,
    fontSize: 11,
    color: T.text,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Card>
        <ChapterChips value={chapter} onChange={setChapter} />
        <p style={{ fontSize: 12, color: T.textDim, lineHeight: 1.7, margin: "0 0 4px" }}>
          Three caricature users across a 24-message synthetic day. The new-conversation gate (≥ 15min)
          is applied: in-session pings show Nikita delay = 0, new-conversation events trigger the
          full model. Watch the Ghoster&rsquo;s long silences trigger model fires while Chatty
          Cathy&rsquo;s bursts mostly don&rsquo;t.
        </p>
        <span>
          <Btn glow onClick={() => setSeed((s) => s + 1)}>↻ resample</Btn>
        </span>
      </Card>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
        <Card>
          <CardLabel sub="solid = user inter-message gaps">User cadence</CardLabel>
          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="idx" tick={{ fontSize: 10, fill: T.textDim }} axisLine={{ stroke: T.border }} tickLine={false} />
                <YAxis
                  scale="log"
                  domain={[0.5, 14400]}
                  tickFormatter={fmt}
                  tick={{ fontSize: 10, fill: T.textDim }}
                  axisLine={false}
                  tickLine={false}
                  type="number"
                  allowDataOverflow
                />
                <Tooltip contentStyle={tip} formatter={(v) => fmt(v as number)} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <ReferenceLine y={900} stroke={T.accent} strokeDasharray="4 4" label={{ value: "session break (15m)", position: "right", fill: T.accent, fontSize: 10 }} />
                {PERSONAS.map((p) => (
                  <Line
                    key={p.name}
                    type="monotone"
                    dataKey={`${p.name.toLowerCase().replace(/[^a-z]/g, "")}_user`}
                    stroke={p.color}
                    strokeWidth={1.5}
                    dot={{ r: 2 }}
                    name={p.name}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <CardLabel sub="dashed = Nikita response time (gate-aware)">Nikita response</CardLabel>
          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="idx" tick={{ fontSize: 10, fill: T.textDim }} axisLine={{ stroke: T.border }} tickLine={false} />
                <YAxis
                  scale="log"
                  domain={[0.5, cap * 1.2]}
                  tickFormatter={fmt}
                  tick={{ fontSize: 10, fill: T.textDim }}
                  axisLine={false}
                  tickLine={false}
                  type="number"
                  allowDataOverflow
                />
                <Tooltip contentStyle={tip} formatter={(v) => fmt(v as number)} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <ReferenceLine y={cap} stroke={T.accent} strokeDasharray="4 4" />
                {PERSONAS.map((p) => (
                  <Line
                    key={p.name}
                    type="monotone"
                    dataKey={`${p.name.toLowerCase().replace(/[^a-z]/g, "")}_nik`}
                    stroke={p.color}
                    strokeWidth={1.5}
                    strokeDasharray="6 3"
                    dot={{ r: 2 }}
                    name={p.name}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  );
}

// ── Section 10: Life-sim integration (placeholder) ────────────────
function LifeSimPlaceholder() {
  return (
    <Card>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
        <div>
          <Tag color={T.lavender} bg={T.lavDim}>
            Future spec — life simulation coupling
          </Tag>
          <p style={{ fontSize: 13, color: T.textMuted, lineHeight: 1.7, marginTop: 16 }}>
            None of the plots above account for Nikita being asleep, at the gym, or in a meeting. The
            log-normal × chapter × momentum model assumes she is reachable. Production should layer a
            <em> life-state mask</em> on top: when Nikita is sleeping at 03:00, response time is{" "}
            <span style={{ color: T.accent }}>not 5s even if M is low</span> — it&rsquo;s
            &ldquo;until-she-wakes&rdquo;.
          </p>
          <p style={{ fontSize: 12, color: T.textDim, lineHeight: 1.7, marginTop: 12 }}>
            Cross-references: spec 022 (life simulation), spec 055 (activity-aware delays), and the
            Nikita-state introspection pipeline. A follow-up spec will define the multiplicative or
            additive coupling.
          </p>
        </div>
        <div>
          <Tag>Proposed coupling sketch</Tag>
          <div
            style={{
              ...mono,
              fontSize: 11,
              color: T.text,
              background: T.bg,
              padding: "14px 16px",
              border: `1px solid ${T.border}`,
              marginTop: 16,
              lineHeight: 1.7,
            }}
          >
            base = exp(μ + σ·Z) · c<sub>ch</sub> · M
            <br />
            life_mult = mask(state, time_of_day)
            <br />
            delay = min(cap<sub>ch</sub>, base · life_mult)
            <br />
            <br />
            <span style={{ color: T.textDim }}># mask examples</span>
            <br />
            sleeping → mask = ∞ (defer to wake)
            <br />
            working → mask = 4.0 (slower)
            <br />
            free_time → mask = 1.0 (baseline)
            <br />
            on_phone → mask = 0.5 (faster)
          </div>
          <p style={{ fontSize: 11, color: T.textDim, marginTop: 12, lineHeight: 1.7 }}>
            Out of scope for Spec 210. To be specced separately after life-sim module review.
          </p>
        </div>
      </div>
    </Card>
  );
}

// ── Section 11: Bayesian equivalence ─────────────────────────────
function BayesEquivalence() {
  return (
    <Card>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
        <div>
          <Tag color={T.accent} bg={T.accentDim}>
            EWMA intuition
          </Tag>
          <p style={{ fontSize: 13, color: T.textMuted, lineHeight: 1.8, marginTop: 16 }}>
            Each new gap nudges the running mean toward itself with weight α; the prior keeps a
            (1 − α) share. Older observations decay geometrically. The chapter baseline B<sub>ch</sub>
            seeds the EWMA so a single fast reply doesn&rsquo;t produce M = 0.02 — the prior keeps the
            posterior in check.
          </p>
          <div
            style={{
              ...mono,
              fontSize: 12,
              color: T.text,
              background: T.bg,
              padding: "14px 16px",
              border: `1px solid ${T.border}`,
              marginTop: 16,
              lineHeight: 1.7,
            }}
          >
            S<sub>0</sub> = B<sub>ch</sub>
            <br />
            S<sub>n</sub> = α · g<sub>n</sub> + (1 − α) · S<sub>n−1</sub>
            <br />
            M = clip( S<sub>N</sub> / B<sub>ch</sub>, 0.1, 5.0 )
          </div>
        </div>
        <div>
          <Tag color={T.lavender} bg={T.lavDim}>
            Bayesian equivalence
          </Tag>
          <p style={{ fontSize: 13, color: T.textMuted, lineHeight: 1.8, marginTop: 16 }}>
            Treat log(g) as Normal-distributed observations. The EWMA seeded at log(B) is the posterior
            mean under a Normal-Normal conjugate update. Setting{" "}
            <code style={{ ...mono, color: T.accent }}>α ≈ σ²ₒₚₛ / (σ²ₒₚₛ + σ²ₚᵣᵢₒᵣ · N)</code>{" "}
            recovers the exact conjugate weight.
          </p>
          <div
            style={{
              ...mono,
              fontSize: 11,
              color: T.text,
              background: T.bg,
              padding: "14px 16px",
              border: `1px solid ${T.border}`,
              marginTop: 16,
              lineHeight: 1.7,
            }}
          >
            prior: μ<sub>p</sub> ~ N(log B, σ²<sub>prior</sub>=0.8²)
            <br />
            obs: log g | μ<sub>p</sub> ~ N(μ<sub>p</sub>, σ²<sub>obs</sub>=0.6²)
            <br />
            posterior contracts after ~3 obs
          </div>
          <p style={{ fontSize: 11, color: T.textDim, marginTop: 12, lineHeight: 1.7 }}>
            No PyMC, no particle filter — same epistemic content, ~10 lines of Python.
          </p>
        </div>
      </div>
    </Card>
  );
}

// ── Section 07: Old vs new ───────────────────────────────────────
function OldVsNew() {
  const rows: [string, string, string][] = [
    ["Ch 1 median", "≈ 4.1h", "≈ 3s"],
    ["Ch 5 median", "≈ 17.5min", "≈ 20s"],
    ["Distribution", "Gaussian / arbitrary", "Log-normal × coeff × momentum"],
    ["Direction", "Inverted (Ch 1 longest)", "Correct (Ch 1 shortest)"],
    ["Fires on", "Every message", "New conversations only"],
    ["Chapter caps", "Single global 1800s", "Per-chapter {10, 60, 300, 900, 1800}"],
    ["Pacing reciprocity", "None", "EWMA momentum × user-turn gaps"],
    ["Skip rates", "60%/20%/0%/0%/0% drops", "Removed — every msg responds"],
  ];
  return (
    <Card>
      <table style={{ width: "100%", borderCollapse: "collapse", ...mono, fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${T.border}` }}>
            {["", "Old", "New"].map((h, i) => (
              <th
                key={i}
                style={{
                  textAlign: "left",
                  padding: "8px 16px 8px 0",
                  fontWeight: 500,
                  color: T.textDim,
                  fontSize: 10,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(([l, o, n], i) => (
            <tr key={i} style={{ borderBottom: `1px solid ${T.border}` }}>
              <td style={{ padding: "10px 16px 10px 0", color: T.textMuted }}>{l}</td>
              <td style={{ padding: "10px 16px 10px 0", color: T.textDim }}>{o}</td>
              <td style={{ padding: "10px 16px 10px 0", color: i < 2 ? T.accent : T.text }}>{n}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

// ── Section 08: Why log-normal + excitement-fades ────────────────
function WhyDistributionAndShape() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
      <Card>
        <Tag color={T.accent} bg={T.accentDim}>
          Why log-normal
        </Tag>
        <p style={{ fontSize: 12, color: T.textMuted, lineHeight: 1.9, marginTop: 16 }}>
          Stouffer et al. (2006) showed log-normal fits human response times better than Barabási&rsquo;s
          power-law once circadian constraints are modeled. Multiplicative latency (read → unlock →
          compose → send) yields CLT-on-log-scale.
        </p>
        <p style={{ fontSize: 12, color: T.textDim, lineHeight: 1.9, marginTop: 12 }}>
          Rejected: Gaussian (negative tail), Exponential (memoryless), Pareto (infinite variance),
          Weibull (wrong regime), Uniform (no concentration).
        </p>
      </Card>
      <Card>
        <Tag color={T.lavender} bg={T.lavDim}>
          Why excitement fades
        </Tag>
        <p style={{ fontSize: 12, color: T.textMuted, lineHeight: 1.9, marginTop: 16 }}>
          Ch 1 is fastest, Ch 5 slowest. Fisher (2004) — dopamine flooding during infatuation. Berger &
          Calabrese (1975) — Uncertainty Reduction Theory predicts dense early exchange. Scissors et al.
          (2014) — established couples reply slower.
        </p>
        <p style={{ fontSize: 12, color: T.textDim, lineHeight: 1.9, marginTop: 12 }}>
          Rejected: &ldquo;investment deepens&rdquo; (Ch 1 slow, Ch 5 fast). Would fit pre-mutual-interest
          but contradicts Nikita&rsquo;s explicitly eager Ch 1 narrative.
        </p>
      </Card>
    </div>
  );
}

// ── Section 09: Citations + next steps ───────────────────────────
function CitationsAndNext() {
  const refs = [
    { a: "Barabási (2005)", t: "The origin of bursts and heavy tails", v: "Nature 435", n: "Power-law model for inter-event times." },
    { a: "Stouffer et al. (2006)", t: "Log-normal provides superior fit", v: "—", n: "Outperforms power-law with circadian constraints." },
    { a: "Wu et al. (2010)", t: "Bimodal distribution in human communication", v: "PNAS 107(44)", n: "New-conversation ≠ within-session bursts." },
    { a: "Malmgren et al. (2009)", t: "Universality of human correspondence", v: "Science 325", n: "Cascading task model — multiplicative interpretation." },
    { a: "Hawkes (1971)", t: "Spectra of self-exciting point processes", v: "Biometrika 58", n: "Theoretical alternative; rejected as overkill here." },
    { a: "Jacobson (1988)", t: "Congestion avoidance and control", v: "ACM SIGCOMM", n: "EWMA smoothing for RTT — direct analogue." },
    { a: "Fisher (2004)", t: "Why We Love", v: "Henry Holt", n: "Infatuation hyper-responsiveness." },
    { a: "Berger & Calabrese (1975)", t: "Explorations in initial interaction", v: "HCR 1(2)", n: "Uncertainty Reduction Theory." },
    { a: "Scissors et al. (2014)", t: "In Text We Trust", v: "—", n: "Established couples reply slower." },
  ];
  const items: [string, string][] = [
    ["Approve chapter coefficients [0.15, 0.30, 0.50, 0.75, 1.00]?", "Default / tweak / load preset"],
    ["Approve per-chapter caps {1:10, 2:60, 3:300, 4:900, 5:1800}s?", "Or bump Ch 1 to 15s"],
    ["Approve momentum (EWMA, α=0.35, [0.1, 5.0])?", "Or set α=0.25 / 0.5"],
    ["Approve baselines B = [300, 240, 180, 120, 90]s?", "Tune after playtesting"],
    ["Approve MC validator workflow?", "scripts/models + docs/models + .claude/rules"],
  ];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
      <Card>
        <CardLabel>Citations · 9 sources</CardLabel>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {refs.map((r, i) => (
            <div key={i} style={{ paddingLeft: 16, borderLeft: `1px solid ${T.border}` }}>
              <div style={{ fontSize: 12, color: T.text, fontWeight: 500 }}>{r.a}</div>
              <div style={{ fontSize: 11, color: T.textMuted, fontStyle: "italic" }}>
                {r.t} — {r.v}
              </div>
              <div style={{ fontSize: 11, color: T.textDim, marginTop: 2 }}>{r.n}</div>
            </div>
          ))}
        </div>
      </Card>
      <Card>
        <CardLabel>Next steps · approve & ship</CardLabel>
        <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {items.map(([q, a], i) => (
            <div
              key={i}
              style={{
                padding: "12px 14px",
                background: T.bg,
                border: `1px solid ${T.border}`,
              }}
            >
              <div style={{ ...mono, fontSize: 11, color: T.accent, fontWeight: 500, marginBottom: 4 }}>
                {i + 1}. {q}
              </div>
              <div style={{ fontSize: 12, color: T.textDim }}>{a}</div>
            </div>
          ))}
        </div>
        <p style={{ fontSize: 11, color: T.textDim, marginTop: 16, lineHeight: 1.7 }}>
          After review → spec FR-005/6/13/14/15 update, MC validator script, stochastic-models rule,
          proceed to Gate 2 (6 parallel validators).
        </p>
      </Card>
    </div>
  );
}

// ── Page export ──────────────────────────────────────────────────
// Mount-guard: every interactive section computes data via Math.random()
// (Box-Muller in `bm()`), which produces different output server-side vs
// client-side and triggers a Next.js hydration mismatch. The guard ensures
// the explorer only renders client-side. Server-rendered HTML is the
// loading skeleton; client first-render also shows the skeleton (matching
// the SSR'd HTML), then useEffect flips `mounted` and re-renders the real
// content. Equivalent to `next/dynamic({ ssr: false })` without the
// server/client component split.
export default function ResponseTimingExplorerPage() {
  const [mounted, setMounted] = useState(false);
  // Intentional setState-in-effect: classic SSR-hydration mount-guard idiom.
  // React's lint rule warns against this in general, but it's the canonical
  // way to detect "we are now on the client" for a one-shot render swap.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <div style={{ background: T.bg, color: T.text, minHeight: "100vh", ...sans }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px 80px" }}>
          <header style={{ marginBottom: 40 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
              <Tag color={T.accent} bg={T.accentDim}>Spec 210 v2</Tag>
              <Tag>log-normal × chapter × momentum</Tag>
            </div>
            <h1
              style={{
                ...sans,
                fontSize: 30,
                fontWeight: 600,
                letterSpacing: "-0.03em",
                color: T.text,
                lineHeight: 1.15,
                margin: "0 0 8px",
              }}
            >
              Response Timing Model — Decision Brief
            </h1>
            <p style={{ ...mono, fontSize: 12, color: T.textDim, marginTop: 24 }}>
              loading interactive explorer…
            </p>
          </header>
        </div>
      </div>
    );
  }

  return (
    <div style={{ background: T.bg, color: T.text, minHeight: "100vh", ...sans }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px 80px" }}>
        <header style={{ marginBottom: 40 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
            <Tag color={T.accent} bg={T.accentDim}>Spec 210 v2</Tag>
            <Tag>log-normal × chapter × momentum</Tag>
            <Tag color={T.lavender} bg={T.lavDim}>2026-04-13</Tag>
          </div>
          <h1
            style={{
              ...sans,
              fontSize: 30,
              fontWeight: 600,
              letterSpacing: "-0.03em",
              color: T.text,
              lineHeight: 1.15,
              margin: "0 0 8px",
            }}
          >
            Response Timing Model — Decision Brief
          </h1>
          <p style={{ fontSize: 14, color: T.textMuted, lineHeight: 1.6, maxWidth: 720, marginTop: 0 }}>
            Stochastic delay model for Nikita&rsquo;s new-conversation responses. Log-normal base,
            per-chapter coefficient + hard cap, multiplied by an EWMA momentum coefficient that adapts
            to the user&rsquo;s recent reply cadence.
          </p>
        </header>

        {(
          [
            [1, "Problem recap", "why we are changing the model", ProblemRecap],
            [2, "Proposed model", "the formula", ProposedModel],
            [3, "Monte Carlo simulator", "drag sliders — charts update live", Sim],
            [4, "Chapter 1 floor", "10s hard cap on infatuation", Ch1Floor],
            [5, "Momentum layer", "EWMA over user-turn gaps", MomentumSim],
            [6, "Conversation transient", "deterministic + stochastic curves over msg index", ConversationTransient],
            [7, "Cold-start distribution", "Nikita response after 10-msg warm-up", ColdStartDistribution],
            [8, "Chapter × cadence heatmap", "median delay across 5×6 grid", ChapterCadenceHeatmap],
            [9, "Persona day", "ghoster / chatty / bored across 24 messages", PersonaDay],
            [10, "Life-sim integration", "future coupling — out of Spec 210 scope", LifeSimPlaceholder],
            [11, "Why EWMA / Bayesian equivalence", "normal-normal conjugate", BayesEquivalence],
            [12, "Old vs new", null, OldVsNew],
            [13, "Why log-normal + excitement-fades", null, WhyDistributionAndShape],
            [14, "Citations + next steps", null, CitationsAndNext],
          ] as Array<[number, string, string | null, () => React.ReactElement]>
        ).map(([n, t, s, C]) => (
          <div key={n} style={{ marginBottom: 48 }}>
            <SL num={n} title={t} sub={s ?? undefined} />
            <C />
          </div>
        ))}

        <footer
          style={{
            borderTop: `1px solid ${T.border}`,
            paddingTop: 24,
            ...mono,
            fontSize: 11,
            color: T.textDim,
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          <span>Spec 210 v2 · 2026-04-13</span>
          <span>nikita/agents/text/timing.py + conversation_rhythm.py</span>
        </footer>
      </div>
    </div>
  );
}

// ── Static section components (kept at bottom for readability) ───
function ProblemRecap() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Tag color={T.textMuted} bg="rgba(255,255,255,0.04)">
            Old model
          </Tag>
        </div>
        <p style={{ fontSize: 13, color: T.textMuted, lineHeight: 1.7, marginBottom: 16 }}>
          Gaussian over five per-chapter ranges — direction was{" "}
          <span style={{ color: T.accent, fontWeight: 500 }}>inverted</span> from design intent. Ch 1
          produced the longest delays and silently dropped 60% of incoming messages.
        </p>
        <div
          style={{
            ...mono,
            fontSize: 11,
            color: T.textDim,
            background: T.bg,
            padding: "14px 16px",
            lineHeight: 1.8,
            border: `1px solid ${T.border}`,
          }}
        >
          TIMING_RANGES = {"{"}
          <br />
          &nbsp;&nbsp;1: (600, 28800), &nbsp;&nbsp;
          <span style={{ color: T.accent }}>← 10min–8h</span>
          <br />
          &nbsp;&nbsp;5: (300, 1800), &nbsp;&nbsp;&nbsp;
          <span style={{ color: T.textDim }}>← 5min–30min</span>
          <br />
          {"}"}
        </div>
      </Card>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Tag color={T.accent} bg={T.accentDim}>
            User verdict
          </Tag>
        </div>
        <blockquote
          style={{
            fontSize: 13,
            color: T.text,
            lineHeight: 1.7,
            fontStyle: "italic",
            borderLeft: `2px solid ${T.accent}`,
            paddingLeft: 16,
            marginBottom: 16,
          }}
        >
          &ldquo;Makes the experience really sh*t&rdquo; — Ch 1 players lose messages and responses
          arrive hours late.
        </blockquote>
        <div style={{ fontSize: 12, color: T.textDim, lineHeight: 2 }}>
          Skip rates removed.
          <br />
          Delay fires only on new conversations (≥ 15 min gap).
          <br />
          Ongoing ping-pong → <span style={{ color: T.accent }}>0 delay</span>.<br />
          Boss fights → <span style={{ color: T.accent }}>0 delay</span>.
        </div>
      </Card>
    </div>
  );
}

function ProposedModel() {
  return (
    <Card>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
        <div>
          <Tag color={T.accent} bg={T.accentDim}>
            Formula
          </Tag>
          <div
            style={{
              ...mono,
              fontSize: 17,
              color: T.text,
              marginTop: 16,
              fontWeight: 400,
              letterSpacing: "-0.02em",
            }}
          >
            delay = min( cap<sub>ch</sub>, e<sup>μ + σ·Z</sup> · c<sub>ch</sub> · M )
          </div>
          <p style={{ fontSize: 12, color: T.textDim, lineHeight: 1.7, marginTop: 12 }}>
            Z ~ N(0, 1). Log-normal base — best single-distribution fit for casual messaging latency.
            Chapter coefficient scales; per-chapter cap truncates tails; momentum M adjusts for the
            user&rsquo;s recent cadence.
          </p>
        </div>
        <div>
          <Tag color={T.lavender} bg={T.lavDim}>
            Defaults
          </Tag>
          <table style={{ ...mono, fontSize: 12, marginTop: 16, width: "100%", borderCollapse: "collapse" }}>
            <tbody>
              {[
                ["μ", "2.996", "median ≈ 20s"],
                ["σ", "1.714", "p90 ≈ 3min"],
                ["caps", "{10, 60, 300, 900, 1800}s", "per-chapter ceilings"],
                ["c[1…5]", "0.15 → 1.00", "excitement fades"],
                ["M", "EWMA(g) / B_ch", "user-cadence multiplier"],
                ["α (EWMA)", "0.35", "smoothing"],
                ["B[1…5]", "300, 240, 180, 120, 90 s", "EWMA prior"],
              ].map(([k, v, n], i) => (
                <tr key={i} style={{ borderBottom: `1px solid ${T.border}` }}>
                  <td style={{ padding: "8px 12px 8px 0", color: T.textDim, width: 70 }}>{k}</td>
                  <td style={{ padding: "8px 12px 8px 0", color: T.accent, fontWeight: 500 }}>{v}</td>
                  <td style={{ padding: "8px 0", color: T.textDim }}>{n}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
}
