"use client";

/**
 * Heartbeat Engine Model — Spec 215 Decision Brief (native portal page).
 *
 * Native React port of the math model documented in
 * docs/models/heartbeat-intensity.md and validated by
 * scripts/models/heartbeat_intensity_mc.py. Inline styles are intentional
 * (mirrors response-timing/page.tsx convention — research-lab artifacts
 * are self-contained, not portal feature surfaces, so they bypass
 * Tailwind/shadcn).
 *
 * All numeric constants MUST stay in lock-step with
 * nikita/heartbeat/intensity.py. The MC validator is the source of truth;
 * this page is a presentation layer that re-implements the equations in
 * TS for in-browser interactivity (no PNG embedding).
 *
 * Sections (10 total):
 *   01  Problem recap — why the engine exists
 *   02  Six-layer architecture
 *   03  Layer 1 — Activity distribution (24h von Mises mixture)
 *   04  Layer 2-4 — Marginal baseline λ_baseline(t, chapter, engagement)
 *   05  Layer 3 — Hawkes excitation (event-burst decay)
 *   06  Layer 6 — Inter-wake distribution (Ogata thinning, per chapter)
 *   07  Sample 1-week wake sequences (3 user archetypes)
 *   08  Stability — branching-ratio inspector
 *   09  Phase 1 / 2 / 3 roadmap
 *   10  Citations + cross-refs
 */

import React, { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

// ── Design tokens (mirror response-timing/page.tsx) ─────────────────
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

// ── Activity palette + chapter palette ──────────────────────────────
// Five activities: order canonical (matches ACTIVITIES in intensity.py:73)
const ACTIVITY_KEYS = ["sleep", "work", "eating", "personal", "social"] as const;
type ActivityKey = (typeof ACTIVITY_KEYS)[number];

const ACT_COLOR: Record<ActivityKey, string> = {
  sleep: "#5B6378",      // dusk-blue (sleep is quiet)
  work: "#7BAAC8",       // workshop-blue
  eating: "#E0B45A",     // amber (food)
  personal: "#A985D7",   // lavender-rose (hobby/free)
  social: "#F383BB",     // accent-pink (social/connection)
};
const ACT_LABEL: Record<ActivityKey, string> = {
  sleep: "Sleep",
  work: "Work",
  eating: "Eating",
  personal: "Personal",
  social: "Social",
};

// Chapter palette (pink → lavender gradient — mirrors response-timing)
const CH = ["#F383BB", "#D283D7", "#A985D7", "#8186D7", "#7BAAC8"] as const;
const CH_FEELS = [
  "Infatuation",
  "Eager",
  "Building",
  "Comfortable",
  "Settled",
] as const;

// ── Math constants (single source: nikita/heartbeat/intensity.py) ───

// ACTIVITY_PARAMS — von Mises mixture per activity. Each entry is
// [μ_radians, κ, weight_within_activity]. Mirrors intensity.py:85-100.
type VMComp = [number, number, number];
const ACTIVITY_PARAMS: Record<ActivityKey, VMComp[]> = {
  sleep: [
    [(2 * Math.PI * 2.0) / 24, 4.0, 0.6],   // 02:00
    [(2 * Math.PI * 23.0) / 24, 4.0, 0.4],  // 23:00
  ],
  work: [[(2 * Math.PI * 10.5) / 24, 4.0, 1.0]],  // 10:30
  eating: [
    [(2 * Math.PI * 12.5) / 24, 8.0, 0.5],  // lunch
    [(2 * Math.PI * 19.0) / 24, 8.0, 0.5],  // dinner
  ],
  personal: [
    [(2 * Math.PI * 8.0) / 24, 3.0, 0.4],   // morning hobby
    [(2 * Math.PI * 20.0) / 24, 2.5, 0.6],  // broad evening
  ],
  social: [[(2 * Math.PI * 21.0) / 24, 4.0, 1.0]],  // 21:00
};

// DIRICHLET_PRIOR — relative shares (intensity.py:111-117).
const DIRICHLET_PRIOR: Record<ActivityKey, number> = {
  sleep: 32,
  work: 22,
  eating: 5,
  personal: 28,
  social: 13,
};
const _TOTAL_PRIOR = Object.values(DIRICHLET_PRIOR).reduce((a, b) => a + b, 0);
const ACTIVITY_BASE_WEIGHTS: Record<ActivityKey, number> = ACTIVITY_KEYS.reduce(
  (acc, a) => ({ ...acc, [a]: DIRICHLET_PRIOR[a] / _TOTAL_PRIOR }),
  {} as Record<ActivityKey, number>,
);

const EPSILON_FLOOR = 0.03;  // intensity.py:131

// NU_PER_ACTIVITY (intensity.py:208-214) — heartbeats/hour conditional
// on activity.
const NU_PER_ACTIVITY: Record<ActivityKey, number> = {
  sleep: 0.05,
  work: 0.30,
  eating: 0.30,
  personal: 1.00,
  social: 0.40,
};

// CHAPTER_MULT (intensity.py:224-230) — multiplicative chapter modulator.
const CHAPTER_MULT: Record<number, number> = {
  1: 1.5, 2: 1.3, 3: 1.1, 4: 1.0, 5: 0.9,
};

// ENGAGEMENT_MULT (intensity.py:234-240).
const ENGAGEMENT_MULT: Record<string, number> = {
  calibrating: 1.4,
  in_zone: 1.0,
  fading: 0.7,
  distant: 0.4,
  clingy: 1.6,
};
const ENGAGEMENT_KEYS = Object.keys(ENGAGEMENT_MULT) as Array<keyof typeof ENGAGEMENT_MULT>;

// Hawkes constants (intensity.py:265-288).
const T_HALF_HRS = 3.0;
const BETA = Math.log(2) / T_HALF_HRS;            // ≈ 0.231 hr⁻¹
const ALPHA: Record<string, number> = {
  user_msg: 0.40,
  game_event: 0.15,
  internal: 0.05,
};
const R_MAX = 1.5;

// ── Math helpers (mirror Python implementations) ────────────────────

// Modified Bessel I_0(κ) — Abramowitz & Stegun 9.8.1/9.8.2. Same
// approximation as intensity.py:_i0 (max rel err ~2e-7 over κ ≤ 100).
function i0(kappa: number): number {
  const ax = Math.abs(kappa);
  if (ax < 3.75) {
    const t = (kappa / 3.75) ** 2;
    return 1.0 + t * (3.5156229 + t * (3.0899424 + t * (1.2067492 + t * (
      0.2659732 + t * (0.0360768 + t * 0.0045813)))));
  }
  const t = 3.75 / ax;
  return (Math.exp(ax) / Math.sqrt(ax)) * (
    0.39894228 + t * (0.01328592 + t * (0.00225319 + t * (-0.00157565 + t * (
      0.00916281 + t * (-0.02057706 + t * (0.02635537 + t * (
        -0.01647633 + t * 0.00392377)))))))
  );
}

function vonMisesMixture(tHours: number, components: VMComp[]): number {
  const phi = (2 * Math.PI * (((tHours % 24) + 24) % 24)) / 24;
  let s = 0;
  for (const [mu, kappa, w] of components) {
    s += (w * Math.exp(kappa * Math.cos(phi - mu))) / i0(kappa);
  }
  return s;
}

// p(a | t) — softmax composition + ε noise floor.
function activityDistribution(
  tHours: number,
  weights: Record<ActivityKey, number> = ACTIVITY_BASE_WEIGHTS,
  epsilon: number = EPSILON_FLOOR,
): Record<ActivityKey, number> {
  const A = ACTIVITY_KEYS.length;
  const raw = {} as Record<ActivityKey, number>;
  let total = 0;
  for (const a of ACTIVITY_KEYS) {
    const v = weights[a] * vonMisesMixture(tHours, ACTIVITY_PARAMS[a]);
    raw[a] = v;
    total += v;
  }
  const out = {} as Record<ActivityKey, number>;
  for (const a of ACTIVITY_KEYS) {
    const sm = raw[a] / total;
    out[a] = (1 - epsilon) * sm + epsilon / A;
  }
  return out;
}

function lambdaBaseline(
  tHours: number,
  chapter: number = 3,
  engagement: string = "in_zone",
  weights: Record<ActivityKey, number> = ACTIVITY_BASE_WEIGHTS,
  nu: Record<ActivityKey, number> = NU_PER_ACTIVITY,
  epsilon: number = EPSILON_FLOOR,
): number {
  const p = activityDistribution(tHours, weights, epsilon);
  let sum = 0;
  for (const a of ACTIVITY_KEYS) sum += p[a] * nu[a];
  return CHAPTER_MULT[chapter] * (ENGAGEMENT_MULT[engagement] ?? 1.0) * sum;
}

function hawkesDecay(R: number, dtHours: number): number {
  return R * Math.exp(-BETA * dtHours);
}
function hawkesUpdate(R: number, alphaK: number, weight: number = 1.0): number {
  return Math.min(R + alphaK * weight * BETA, R_MAX);
}
function lambdaTotal(
  tHours: number, R: number, chapter: number, engagement: string,
): number {
  return lambdaBaseline(tHours, chapter, engagement) + R;
}

// Exponential draw with rate λ. Math.random is impure; the seed-state
// in each consumer's useMemo deps drives re-evaluation on user resample.
function expovariate(rate: number): number {
  if (rate <= 0) return Infinity;
  let u = Math.random();
  if (u < 1e-12) u = 1e-12;
  return -Math.log(u) / rate;
}

// Uniform [0, hi) draw — same purity caveat as expovariate.
function uniform(hi: number): number {
  return Math.random() * hi;
}

// Ogata thinning sampler — mirrors intensity.py:sample_next_wakeup.
// Returns the inter-wake gap dt (hours) starting from t_now.
function sampleNextWake(
  tNow: number,
  RNow: number,
  chapter: number,
  engagement: string,
  tHorizon: number = 24.0,
): { dt: number; tNext: number; RNext: number; degenerate: boolean } {
  let t = tNow;
  let R = RNow;
  for (let iter = 0; iter < 2000; iter++) {
    // 13-pt upper bound on baseline in next-1h proposal window
    let lambdaMax = 0;
    for (let i = 0; i < 13; i++) {
      const s = t + (1.0 * i) / 12;
      const v = lambdaBaseline(s, chapter, engagement);
      if (v > lambdaMax) lambdaMax = v;
    }
    lambdaMax += R;
    if (lambdaMax <= 1e-9) {
      return { dt: tHorizon, tNext: tNow + tHorizon, RNext: R, degenerate: true };
    }
    const dt = expovariate(lambdaMax);
    const tCand = t + dt;
    if (tCand - tNow > tHorizon) {
      const Rh = hawkesDecay(R, tHorizon);
      return { dt: tHorizon, tNext: tNow + tHorizon, RNext: Rh, degenerate: true };
    }
    const RCand = hawkesDecay(R, dt);
    const lambdaActual = lambdaBaseline(tCand, chapter, engagement) + RCand;
    const u = uniform(lambdaMax);
    if (u <= lambdaActual) {
      return { dt: tCand - tNow, tNext: tCand, RNext: RCand, degenerate: false };
    }
    t = tCand;
    R = RCand;
  }
  return { dt: tHorizon, tNext: tNow + tHorizon, RNext: R, degenerate: true };
}

// Branching ratio: Σ_k α_k · E[w_k]. Stable iff < 1.
function branchingRatio(
  alpha: Record<string, number>,
  expectedWeight: Record<string, number>,
): number {
  let sum = 0;
  for (const k of Object.keys(alpha)) sum += alpha[k] * (expectedWeight[k] ?? 1.0);
  return sum;
}

// ── Style maps (mirror response-timing) ─────────────────────────────
const mono: React.CSSProperties = {
  fontFamily:
    "'JetBrains Mono', ui-monospace, 'SF Mono', 'Cascadia Code', monospace",
};
const sans: React.CSSProperties = {
  fontFamily: "ui-sans-serif, system-ui, -apple-system, sans-serif",
};

// ── Primitives (Card / CardLabel / SL / Tag / Slider / Btn) ─────────
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

// Convert a ReactNode label into a flat string for aria-label fallback.
function ariaText(node: React.ReactNode): string {
  if (node == null || typeof node === "boolean") return "slider";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(ariaText).join(" ");
  if (typeof node === "object" && "props" in node) {
    return ariaText((node as { props: { children?: React.ReactNode } }).props.children);
  }
  return "slider";
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
  const aria = ariaText(label);
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
        aria-label={aria}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
        aria-valuetext={format ? format(value) : String(value)}
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

const tipStyle = {
  background: T.surfaceUp,
  border: `1px solid ${T.border}`,
  borderRadius: 0,
  fontSize: 11,
  color: T.text,
  boxShadow: `0 8px 40px rgba(0,0,0,0.6), 0 0 20px ${T.accentGlow}`,
};

// ── Helpers for charts ──────────────────────────────────────────────
function fmtHr(h: number): string {
  if (h < 1) return `${(h * 60).toFixed(0)}min`;
  if (h < 24) return `${h.toFixed(1)}h`;
  return `${(h / 24).toFixed(1)}d`;
}
function fmtClock(h: number): string {
  const wrapped = ((h % 24) + 24) % 24;
  const hh = Math.floor(wrapped);
  const mm = Math.floor((wrapped - hh) * 60);
  return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
}

// ─────────────────────────────────────────────────────────────────────
// Section 03 — Activity distribution explorer (24h × 5 stacked area)
// ─────────────────────────────────────────────────────────────────────
function ActivityDistribution() {
  const [epsilon, setEpsilon] = useState(EPSILON_FLOOR);
  const [stepHrs, setStepHrs] = useState(0.25);

  const data = useMemo(() => {
    const rows: Array<Record<string, number | string>> = [];
    // Honor the slider directly; minimum 24 samples (1h granularity) keeps
    // the chart usable. No artificial 48-floor — that made stepHrs > 0.5
    // a no-op (LOW finding QA iter-1).
    const N = Math.max(24, Math.floor(24 / stepHrs));
    for (let i = 0; i <= N; i++) {
      const t = (24 * i) / N;
      const p = activityDistribution(t, ACTIVITY_BASE_WEIGHTS, epsilon);
      rows.push({
        t,
        clock: fmtClock(t),
        ...p,
      });
    }
    return rows;
  }, [epsilon, stepHrs]);

  // Daily mass per activity (∫ p(a|t) dt over 24h, by trapezoid).
  const dailyMass = useMemo(() => {
    const N = data.length - 1;
    const dt = 24 / N;
    const m: Record<ActivityKey, number> = {
      sleep: 0, work: 0, eating: 0, personal: 0, social: 0,
    };
    for (let i = 0; i < N; i++) {
      for (const a of ACTIVITY_KEYS) {
        const va = data[i][a] as number;
        const vb = data[i + 1][a] as number;
        m[a] += 0.5 * (va + vb) * dt;
      }
    }
    // Convert hours → percentage of day
    const total = Object.values(m).reduce((s, x) => s + x, 0);
    const pct: Record<ActivityKey, number> = { ...m };
    for (const a of ACTIVITY_KEYS) pct[a] = (m[a] / total) * 100;
    return pct;
  }, [data]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Card>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
          <div>
            <Tag color={T.accent} bg={T.accentDim}>Layer 1</Tag>
            <div style={{ ...mono, fontSize: 14, color: T.text, marginTop: 16, lineHeight: 1.6 }}>
              p(a | t) = (1 − ε) · softmax<sub>a</sub>(w<sub>a</sub> · vM<sub>a</sub>(t)) + ε / A
            </div>
            <p style={{ fontSize: 12, color: T.textDim, lineHeight: 1.7, marginTop: 12 }}>
              vM<sub>a</sub>(t) = Σ<sub>k</sub> w<sub>a,k</sub> · exp(κ<sub>a,k</sub> · cos(φ − μ<sub>a,k</sub>)) / I<sub>0</sub>(κ<sub>a,k</sub>),
              with phase φ = 2π · (t mod 24) / 24. Bessel normalization makes high-κ and low-κ
              components contribute comparable mass over the period — without it, sharp peaks
              (eating κ=8, exp(8)≈3000) dwarf broad ones (personal κ=2.5, exp(2.5)≈12).
            </p>
          </div>
          <div>
            <Tag color={T.lavender} bg={T.lavDim}>Parameters</Tag>
            <Slider
              label="ε  noise floor"
              value={epsilon}
              min={0.0}
              max={0.10}
              step={0.005}
              onChange={setEpsilon}
              format={(v) => `${v.toFixed(3)}  →  min p ≥ ${(v / 5).toFixed(3)}`}
            />
            <Slider
              label="Δt  resolution"
              value={stepHrs}
              min={0.05}
              max={1.0}
              step={0.05}
              onChange={setStepHrs}
              format={(v) => `${(v * 60).toFixed(0)}min`}
            />
          </div>
        </div>
      </Card>

      <Card>
        <CardLabel sub="Stacked p(a | t) over 24h. Each band is the probability of being in that activity at time t.">
          Activity probability — 24h
        </CardLabel>
        <div style={{ width: "100%", height: 360 }}>
          <ResponsiveContainer>
            <AreaChart data={data} stackOffset="expand">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="t"
                type="number"
                domain={[0, 24]}
                ticks={[0, 4, 8, 12, 16, 20, 24]}
                tickFormatter={(v) => `${v}h`}
                tick={{ fontSize: 10, fill: T.textDim }}
                axisLine={{ stroke: T.border }}
                tickLine={false}
              />
              <YAxis
                tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                tick={{ fontSize: 10, fill: T.textDim }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={tipStyle}
                labelFormatter={(v) => `t = ${fmtClock(v as number)}`}
                formatter={(v, n) => [`${((v as number) * 100).toFixed(1)}%`, ACT_LABEL[n as ActivityKey]]}
              />
              <Legend wrapperStyle={{ fontSize: 11, color: T.textMuted }} />
              {ACTIVITY_KEYS.map((a) => (
                <Area
                  key={a}
                  type="monotone"
                  dataKey={a}
                  stackId="a"
                  stroke={ACT_COLOR[a]}
                  fill={ACT_COLOR[a]}
                  fillOpacity={0.78}
                  name={ACT_LABEL[a]}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
        <Card>
          <CardLabel sub="Hours/day spent in each activity (∫ p(a | t) dt)">
            Daily mass
          </CardLabel>
          <div style={{ width: "100%", height: 220 }}>
            <ResponsiveContainer>
              <BarChart
                data={ACTIVITY_KEYS.map((a) => ({
                  name: ACT_LABEL[a],
                  hours: (dailyMass[a] / 100) * 24,
                  pct: dailyMass[a],
                  fill: ACT_COLOR[a],
                }))}
                layout="vertical"
              >
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis
                  type="number"
                  domain={[0, 14]}
                  ticks={[0, 2, 4, 6, 8, 10, 12, 14]}
                  tickFormatter={(v) => `${v}h`}
                  tick={{ fontSize: 10, fill: T.textDim }}
                  axisLine={{ stroke: T.border }}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 11, fill: T.textMuted }}
                  axisLine={false}
                  tickLine={false}
                  width={80}
                />
                <Tooltip
                  contentStyle={tipStyle}
                  formatter={(v) => `${(v as number).toFixed(2)}h`}
                />
                <Bar dataKey="hours" radius={0}>
                  {ACTIVITY_KEYS.map((a) => (
                    <Cell key={a} fill={ACT_COLOR[a]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <CardLabel sub="Dirichlet prior shares (intensity.py:111-117) — calibrate weights, not raw v-M heights">
            Prior weights (DIRICHLET_PRIOR)
          </CardLabel>
          <table style={{ ...mono, fontSize: 12, marginTop: 12, width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                {["", "α", "share", "ν", "peaks (clock)"].map((h, i) => (
                  <th
                    key={i}
                    style={{
                      textAlign: "left",
                      padding: "8px 12px 8px 0",
                      color: T.textDim,
                      fontWeight: 500,
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
              {ACTIVITY_KEYS.map((a) => (
                <tr key={a} style={{ borderBottom: `1px solid ${T.border}` }}>
                  <td style={{ padding: "10px 12px 10px 0" }}>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 8,
                      }}
                    >
                      <span
                        style={{
                          width: 7,
                          height: 7,
                          borderRadius: "50%",
                          background: ACT_COLOR[a],
                        }}
                      />
                      <span style={{ color: T.text }}>{ACT_LABEL[a]}</span>
                    </span>
                  </td>
                  <td style={{ padding: "10px 12px 10px 0", color: T.text }}>{DIRICHLET_PRIOR[a]}</td>
                  <td style={{ padding: "10px 12px 10px 0", color: T.accent }}>
                    {(ACTIVITY_BASE_WEIGHTS[a] * 100).toFixed(1)}%
                  </td>
                  <td style={{ padding: "10px 12px 10px 0", color: T.lavender }}>
                    {NU_PER_ACTIVITY[a].toFixed(2)}/h
                  </td>
                  <td style={{ padding: "10px 12px 10px 0", color: T.textMuted }}>
                    {ACTIVITY_PARAMS[a]
                      .map((c) => fmtClock((c[0] * 24) / (2 * Math.PI)))
                      .join(", ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Section 04 — Marginal heartbeat baseline λ_baseline(t, ch, eng)
// ─────────────────────────────────────────────────────────────────────
function MarginalBaseline() {
  const [chapter, setChapter] = useState(3);
  const [engagement, setEngagement] = useState<string>("in_zone");

  const data = useMemo(() => {
    const N = 96;
    const out: Array<Record<string, number>> = [];
    for (let i = 0; i <= N; i++) {
      const t = (24 * i) / N;
      const row: Record<string, number> = { t };
      for (let c = 1; c <= 5; c++) {
        row[`c${c}`] = lambdaBaseline(t, c, engagement);
      }
      out.push(row);
    }
    return out;
  }, [engagement]);

  // Engagement comparison at fixed chapter
  const engData = useMemo(() => {
    const N = 96;
    const out: Array<Record<string, number>> = [];
    for (let i = 0; i <= N; i++) {
      const t = (24 * i) / N;
      const row: Record<string, number> = { t };
      for (const e of ENGAGEMENT_KEYS) {
        row[e] = lambdaBaseline(t, chapter, e);
      }
      out.push(row);
    }
    return out;
  }, [chapter]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Card>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
          <div>
            <Tag color={T.accent} bg={T.accentDim}>Layers 2 + 4</Tag>
            <div style={{ ...mono, fontSize: 14, color: T.text, marginTop: 16, lineHeight: 1.6 }}>
              λ<sub>baseline</sub>(t) = M<sub>ch</sub> · M<sub>eng</sub> · Σ<sub>a</sub> p(a | t) · ν<sub>a</sub>
            </div>
            <p style={{ fontSize: 12, color: T.textDim, lineHeight: 1.7, marginTop: 12 }}>
              ν<sub>a</sub> is the per-activity heartbeat rate (heartbeats/hour). Personal time
              dominates because Nikita is hobby-driven; sleep contributes &lt;0.05/h (dream-state
              thoughts). Without Hawkes excitation, λ<sub>baseline</sub> is the entire intensity.
            </p>
          </div>
          <div>
            <Tag color={T.lavender} bg={T.lavDim}>Modulators</Tag>
            <table style={{ ...mono, fontSize: 12, marginTop: 16, width: "100%", borderCollapse: "collapse" }}>
              <tbody>
                {[
                  ["M[Ch 1..5]", "1.5, 1.3, 1.1, 1.0, 0.9", "infatuation → settled"],
                  ["M[engagement]", "calibrating 1.4 · in_zone 1.0", "scales with state"],
                  ["", "fading 0.7 · distant 0.4 · clingy 1.6", ""],
                  ["μ_base", "Σ w_a · ν_a", "≈ 0.45 / h prior"],
                ].map(([k, v, n], i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${T.border}` }}>
                    <td style={{ padding: "8px 12px 8px 0", color: T.textDim, width: 110 }}>{k}</td>
                    <td style={{ padding: "8px 12px 8px 0", color: T.accent, fontWeight: 500 }}>{v}</td>
                    <td style={{ padding: "8px 0", color: T.textDim }}>{n}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Card>

      <Card>
        <CardLabel sub={`λ_baseline(t) per chapter at engagement = ${engagement}`}>
          Chapter comparison
        </CardLabel>
        <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
          {ENGAGEMENT_KEYS.map((e) => (
            <Btn key={e} glow={engagement === e} onClick={() => setEngagement(e)}>
              {e}
            </Btn>
          ))}
        </div>
        <div style={{ width: "100%", height: 280 }}>
          <ResponsiveContainer>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="t"
                type="number"
                domain={[0, 24]}
                ticks={[0, 4, 8, 12, 16, 20, 24]}
                tickFormatter={(v) => `${v}h`}
                tick={{ fontSize: 10, fill: T.textDim }}
                axisLine={{ stroke: T.border }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: T.textDim }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => (v as number).toFixed(2)}
              />
              <Tooltip
                contentStyle={tipStyle}
                labelFormatter={(v) => `t = ${fmtClock(v as number)}`}
                formatter={(v, n) => [`${(v as number).toFixed(3)}/h`, n as string]}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <ReferenceArea x1={0} x2={5} fill="rgba(91,99,120,0.10)" />
              <ReferenceArea x1={22} x2={24} fill="rgba(91,99,120,0.10)" />
              {[1, 2, 3, 4, 5].map((c) => (
                <Line
                  key={c}
                  type="monotone"
                  dataKey={`c${c}`}
                  stroke={CH[c - 1]}
                  strokeWidth={1.6}
                  dot={false}
                  name={`Ch ${c} ${CH_FEELS[c - 1]}`}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card>
        <CardLabel sub={`λ_baseline(t) per engagement state at Ch ${chapter} (${CH_FEELS[chapter - 1]})`}>
          Engagement comparison
        </CardLabel>
        <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
          {[1, 2, 3, 4, 5].map((c) => (
            <Btn key={c} glow={chapter === c} onClick={() => setChapter(c)}>
              Ch {c}
            </Btn>
          ))}
        </div>
        <div style={{ width: "100%", height: 280 }}>
          <ResponsiveContainer>
            <LineChart data={engData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="t"
                type="number"
                domain={[0, 24]}
                ticks={[0, 4, 8, 12, 16, 20, 24]}
                tickFormatter={(v) => `${v}h`}
                tick={{ fontSize: 10, fill: T.textDim }}
                axisLine={{ stroke: T.border }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: T.textDim }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => (v as number).toFixed(2)}
              />
              <Tooltip
                contentStyle={tipStyle}
                labelFormatter={(v) => `t = ${fmtClock(v as number)}`}
                formatter={(v, n) => [`${(v as number).toFixed(3)}/h`, n as string]}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {ENGAGEMENT_KEYS.map((e, i) => {
                const palette = ["#7BAAC8", "#EBEBEB", "#E0B45A", "#D27F7F", "#F383BB"];
                return (
                  <Line
                    key={e}
                    type="monotone"
                    dataKey={e}
                    stroke={palette[i]}
                    strokeWidth={1.6}
                    dot={false}
                    name={e}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Section 05 — Hawkes excitation explorer
// ─────────────────────────────────────────────────────────────────────
const EVENT_PRESETS: Record<string, { label: string; events: Array<[number, string, number]> }> = {
  single: {
    label: "Single user msg",
    events: [[0.0, "user_msg", 1.0]],
  },
  burst5: {
    label: "5-msg burst (10min apart)",
    events: [
      [0.00, "user_msg", 1.0],
      [0.17, "user_msg", 1.0],
      [0.33, "user_msg", 1.0],
      [0.50, "user_msg", 1.0],
      [0.67, "user_msg", 1.0],
    ],
  },
  conversation: {
    label: "Sustained chat (12 msgs / 90min)",
    events: Array.from({ length: 12 }, (_, i) => [
      (1.5 * i) / 11,
      "user_msg",
      1.0,
    ]) as Array<[number, string, number]>,
  },
  emotional: {
    label: "Emotional msg (heavy)",
    events: [
      [0.0, "user_msg", 1.8],
      [0.5, "user_msg", 1.5],
    ],
  },
  game: {
    label: "Boss event + reaction",
    events: [
      [0.0, "game_event", 1.0],
      [0.3, "user_msg", 1.5],
      [1.0, "user_msg", 1.0],
    ],
  },
};

function HawkesExplorer() {
  const [preset, setPreset] = useState<keyof typeof EVENT_PRESETS>("burst5");
  const [chapter, setChapter] = useState(3);

  // Trace R(t) over 12 hours given the event sequence
  const trace = useMemo(() => {
    const events = EVENT_PRESETS[preset].events;
    const N = 240;
    const horizon = 12.0;
    const out: Array<{ t: number; R: number; lambda: number }> = [];
    let R = 0.0;
    let tCur = 0.0;  // current time the residual R is "at" — single source of truth
    let evtIdx = 0;
    for (let i = 0; i <= N; i++) {
      const t = (horizon * i) / N;
      // Apply any events with timestamp ≤ t that haven't been applied yet.
      // Decay R forward from tCur to each event's time, then update.
      while (evtIdx < events.length && events[evtIdx][0] <= t) {
        const [tEvt, kind, w] = events[evtIdx];
        const dtToEvt = tEvt - tCur;
        if (dtToEvt > 0) R = hawkesDecay(R, dtToEvt);
        R = hawkesUpdate(R, ALPHA[kind] ?? ALPHA.internal, w);
        tCur = tEvt;
        evtIdx++;
      }
      // Decay from tCur (last-applied event or last sample) forward to t.
      const dtToT = t - tCur;
      if (dtToT > 0) R = hawkesDecay(R, dtToT);
      tCur = t;
      out.push({
        t,
        R,
        lambda: lambdaBaseline(t, chapter, "in_zone") + R,
      });
    }
    return out;
  }, [preset, chapter]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Card>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
          <div>
            <Tag color={T.accent} bg={T.accentDim}>Layer 3</Tag>
            <div style={{ ...mono, fontSize: 14, color: T.text, marginTop: 16, lineHeight: 1.6 }}>
              R(t) = R(t<sub>−</sub>) · e<sup>−β·Δt</sup> + α<sub>k</sub> · w · β
            </div>
            <p style={{ fontSize: 12, color: T.textDim, lineHeight: 1.7, marginTop: 12 }}>
              Self-exciting kernel. Each event raises the residual by α<sub>k</sub>·w·β; between
              events the residual decays exponentially (T<sub>½</sub> = 3h, β ≈ 0.231/h).
              R is capped at R<sub>max</sub> = 1.5 to bound storm spikes.
            </p>
          </div>
          <div>
            <Tag color={T.lavender} bg={T.lavDim}>Per-event α</Tag>
            <table style={{ ...mono, fontSize: 12, marginTop: 16, width: "100%", borderCollapse: "collapse" }}>
              <tbody>
                {[
                  ["α[user_msg]", "0.40", "user message"],
                  ["α[game_event]", "0.15", "boss/chapter trigger"],
                  ["α[internal]", "0.05", "self-excitation floor"],
                  ["β", BETA.toFixed(3) + "/h", "T_½ = 3h"],
                  ["R_max", "1.5", "storm-spike cap"],
                ].map(([k, v, n], i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${T.border}` }}>
                    <td style={{ padding: "8px 12px 8px 0", color: T.textDim, width: 130 }}>{k}</td>
                    <td style={{ padding: "8px 12px 8px 0", color: T.accent, fontWeight: 500 }}>{v}</td>
                    <td style={{ padding: "8px 0", color: T.textDim }}>{n}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Card>

      <Card>
        <CardLabel sub="Pick an event burst pattern; trace R(t) and λ_total(t) over 12h.">
          Event-burst simulator
        </CardLabel>
        <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
          {(Object.keys(EVENT_PRESETS) as Array<keyof typeof EVENT_PRESETS>).map((k) => (
            <Btn key={k} glow={preset === k} onClick={() => setPreset(k)}>
              {EVENT_PRESETS[k].label}
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
        <div style={{ width: "100%", height: 320 }}>
          <ResponsiveContainer>
            <LineChart data={trace}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="t"
                type="number"
                domain={[0, 12]}
                ticks={[0, 2, 4, 6, 8, 10, 12]}
                tickFormatter={(v) => `${v}h`}
                tick={{ fontSize: 10, fill: T.textDim }}
                axisLine={{ stroke: T.border }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: T.textDim }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => (v as number).toFixed(2)}
              />
              <Tooltip
                contentStyle={tipStyle}
                labelFormatter={(v) => `t = +${(v as number).toFixed(2)}h`}
                formatter={(v, n) => [`${(v as number).toFixed(3)}`, n as string]}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <ReferenceLine y={R_MAX} stroke="rgba(255,255,255,0.12)" strokeDasharray="4 4" label={{ value: "R_max", position: "right", fill: T.textDim, fontSize: 10 }} />
              {EVENT_PRESETS[preset].events.map(([tEvt], i) => (
                <ReferenceLine
                  key={i}
                  x={tEvt}
                  stroke={T.accent}
                  strokeDasharray="2 4"
                  opacity={0.4}
                />
              ))}
              <Line
                type="monotone"
                dataKey="R"
                stroke={T.lavender}
                strokeWidth={1.6}
                dot={false}
                name="R(t) — Hawkes residual"
              />
              <Line
                type="monotone"
                dataKey="lambda"
                stroke={T.accent}
                strokeWidth={1.6}
                dot={false}
                name="λ_total(t)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p style={{ fontSize: 11, color: T.textDim, marginTop: 12, ...mono }}>
          dotted vertical lines = event timestamps · pink = total intensity · lavender = excitation residual
        </p>
      </Card>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Section 06 — Inter-wake distribution simulator (per chapter)
// ─────────────────────────────────────────────────────────────────────
function InterwakeDistribution() {
  const [N, setN] = useState(2000);
  const [seed, setSeed] = useState(0);
  const [engagement] = useState<string>("in_zone");

  const samples = useMemo(() => {
    // For each chapter, run N independent (t_now uniform on [0,24], R=0)
    // → sample one inter-wake gap.
    void seed;  // resample button toggles seed; useMemo deps include it
    const out: Record<number, number[]> = {};
    for (let c = 1; c <= 5; c++) {
      const arr: number[] = [];
      for (let i = 0; i < N; i++) {
        const t0 = uniform(24);
        const r = sampleNextWake(t0, 0.0, c, engagement, 24.0);
        if (!r.degenerate) arr.push(r.dt);
      }
      arr.sort((a, b) => a - b);
      out[c] = arr;
    }
    return out;
  }, [N, seed, engagement]);

  const stats = useMemo(() => {
    const o: Array<{ chapter: number; n: number; p25: number; median: number; p75: number; p90: number; p99: number; mean: number }> = [];
    for (let c = 1; c <= 5; c++) {
      const a = samples[c];
      if (!a.length) continue;
      const pct = (p: number) => a[Math.min(a.length - 1, Math.floor(p * a.length))];
      const mean = a.reduce((s, x) => s + x, 0) / a.length;
      o.push({ chapter: c, n: a.length, p25: pct(0.25), median: pct(0.5), p75: pct(0.75), p90: pct(0.9), p99: pct(0.99), mean });
    }
    return o;
  }, [samples]);

  const histo = useMemo(() => {
    // Log-bins from 0.05h to 24h
    const lo = Math.log(0.05);
    const hi = Math.log(24);
    const nBins = 32;
    const edges: number[] = [];
    for (let i = 0; i <= nBins; i++) edges.push(Math.exp(lo + (i / nBins) * (hi - lo)));
    const out: Array<Record<string, number | string>> = [];
    for (let i = 0; i < nBins; i++) {
      const r: Record<string, number | string> = {
        bl: fmtHr((edges[i] + edges[i + 1]) / 2),
        center: (edges[i] + edges[i + 1]) / 2,
      };
      for (let c = 1; c <= 5; c++) {
        const arr = samples[c];
        if (!arr) {
          r[`c${c}`] = 0;
          continue;
        }
        let count = 0;
        for (const x of arr) if (x >= edges[i] && x < edges[i + 1]) count++;
        r[`c${c}`] = count;
      }
      out.push(r);
    }
    return out;
  }, [samples]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Card>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <CardLabel
            sub={`${N.toLocaleString()} draws per chapter via Ogata thinning · t_now ~ U[0, 24)h · R = 0 · engagement = ${engagement}`}
          >
            Inter-wake gaps per chapter
          </CardLabel>
          <span style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
            <Btn glow onClick={() => setSeed((s) => s + 1)}>↻ Resample</Btn>
            <Btn onClick={() => setN(500)}>500</Btn>
            <Btn onClick={() => setN(2000)} glow={N === 2000}>2k</Btn>
            <Btn onClick={() => setN(5000)}>5k</Btn>
          </span>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", ...mono, fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                {["", "n", "p25", "median", "p75", "p90", "p99", "mean"].map((h, i) => (
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
              {stats.map((s) => (
                <tr key={s.chapter} style={{ borderBottom: `1px solid ${T.border}` }}>
                  <td style={{ padding: "10px 14px 10px 0" }}>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                      <span style={{ width: 6, height: 6, borderRadius: "50%", background: CH[s.chapter - 1] }} />
                      <span style={{ color: T.text }}>Ch {s.chapter} · {CH_FEELS[s.chapter - 1]}</span>
                    </span>
                  </td>
                  <td style={{ padding: "10px 14px 10px 0", color: T.textMuted }}>{s.n}</td>
                  <td style={{ padding: "10px 14px 10px 0", color: T.text }}>{fmtHr(s.p25)}</td>
                  <td style={{ padding: "10px 14px 10px 0", color: T.accent, fontWeight: 600 }}>{fmtHr(s.median)}</td>
                  <td style={{ padding: "10px 14px 10px 0", color: T.text }}>{fmtHr(s.p75)}</td>
                  <td style={{ padding: "10px 14px 10px 0", color: T.text }}>{fmtHr(s.p90)}</td>
                  <td style={{ padding: "10px 14px 10px 0", color: T.textMuted }}>{fmtHr(s.p99)}</td>
                  <td style={{ padding: "10px 14px 10px 0", color: T.lavender }}>{fmtHr(s.mean)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <CardLabel sub="Stacked histogram, log-spaced bins from 3min to 24h">
          Distribution of next-wake gaps
        </CardLabel>
        <div style={{ width: "100%", height: 280 }}>
          <ResponsiveContainer>
            <BarChart data={histo}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="bl"
                tick={{ fontSize: 9, fill: T.textDim }}
                interval={3}
                angle={-30}
                textAnchor="end"
                height={48}
                axisLine={{ stroke: T.border }}
                tickLine={false}
              />
              <YAxis tick={{ fontSize: 10, fill: T.textDim }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tipStyle} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
              <Legend wrapperStyle={{ fontSize: 11, color: T.textMuted }} />
              {[1, 2, 3, 4, 5].map((c) => (
                <Bar
                  key={c}
                  dataKey={`c${c}`}
                  fill={CH[c - 1]}
                  name={`Ch ${c}`}
                  stackId="a"
                  opacity={0.85}
                  radius={0}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Section 07 — Sample 1-week wake sequences (3 archetypes)
// ─────────────────────────────────────────────────────────────────────
type Archetype = "silent" | "occasional" | "chatty";

const ARCHETYPES: Record<Archetype, { label: string; color: string; chapter: number; engagement: string; events: Array<[number, number]> }> = {
  silent: {
    label: "Silent (no msgs)",
    color: "#7BAAC8",
    chapter: 4,
    engagement: "fading",
    events: [],
  },
  occasional: {
    label: "Occasional (3 msgs)",
    color: "#A985D7",
    chapter: 3,
    engagement: "in_zone",
    events: [
      [12.5, 1.0], [60.0, 1.2], [108.0, 0.9],
    ],
  },
  chatty: {
    label: "Chatty (12 msgs)",
    color: "#F383BB",
    chapter: 2,
    engagement: "calibrating",
    events: [
      [9.0, 1.0], [10.0, 1.0], [11.5, 1.5], [21.0, 1.0],
      [33.0, 1.0], [45.0, 1.5], [55.0, 1.0], [80.0, 1.0],
      [90.0, 2.0], [108.0, 1.0], [125.0, 1.0], [156.0, 0.8],
    ],
  },
};

function WeekSequences() {
  const [archetype, setArchetype] = useState<Archetype>("occasional");
  const [seed, setSeed] = useState(0);

  const trace = useMemo(() => {
    void seed;
    const cfg = ARCHETYPES[archetype];
    const horizon = 168.0;  // 7 days in hours
    let t = 0.0;
    let R = 0.0;
    let tCur = 0.0;  // current time R is "at" — advanced by event-decay AND wake-sample steps
    let evtIdx = 0;
    const wakes: Array<{ t: number; clock: number; day: number; lambda: number | undefined; R: number; kind: "wake" | "msg" }> = [];
    let safety = 0;
    while (t < horizon && safety++ < 5000) {
      // Apply any events with timestamp ≤ t before sampling next wake. Decay
      // R forward from tCur to each event's time, then update.
      while (evtIdx < cfg.events.length && cfg.events[evtIdx][0] <= t) {
        const [tEvt, w] = cfg.events[evtIdx];
        const dtToEvt = Math.max(0, tEvt - tCur);
        if (dtToEvt > 0) R = hawkesDecay(R, dtToEvt);
        R = hawkesUpdate(R, ALPHA.user_msg, w);
        tCur = tEvt;
        wakes.push({ t: tEvt, clock: ((tEvt % 24) + 24) % 24, day: Math.floor(tEvt / 24), lambda: undefined, R, kind: "msg" });
        evtIdx++;
      }
      const result = sampleNextWake(t, R, cfg.chapter, cfg.engagement, 24.0);
      if (result.degenerate && result.dt >= 24.0) {
        // Advance by 1h and try again (degenerate horizon hit)
        t += 1.0;
        R = hawkesDecay(R, 1.0);
        tCur = t;
        continue;
      }
      const tNext = result.tNext;
      if (tNext >= horizon) break;
      wakes.push({
        t: tNext,
        clock: ((tNext % 24) + 24) % 24,
        day: Math.floor(tNext / 24),
        lambda: lambdaTotal(tNext, result.RNext, cfg.chapter, cfg.engagement),
        R: result.RNext,
        kind: "wake",
      });
      t = tNext;
      R = result.RNext;
      tCur = tNext;
    }
    return wakes;
  }, [archetype, seed]);

  const wakeOnly = trace.filter((w) => w.kind === "wake");
  const msgOnly = trace.filter((w) => w.kind === "msg");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Card>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 16 }}>
          {(Object.keys(ARCHETYPES) as Archetype[]).map((k) => (
            <Btn key={k} glow={archetype === k} onClick={() => setArchetype(k)}>
              {ARCHETYPES[k].label}
            </Btn>
          ))}
          <Btn glow onClick={() => setSeed((s) => s + 1)} style={{ marginLeft: "auto" }}>
            ↻ Resample
          </Btn>
        </div>
        <CardLabel
          sub={`Ch ${ARCHETYPES[archetype].chapter} · engagement = ${ARCHETYPES[archetype].engagement} · ${wakeOnly.length} wakes over 7 days · ${msgOnly.length} user messages injected`}
        >
          7-day wake scatter (clock-hour vs day)
        </CardLabel>
        <div style={{ width: "100%", height: 320 }}>
          <ResponsiveContainer>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                type="number"
                dataKey="clock"
                domain={[0, 24]}
                ticks={[0, 4, 8, 12, 16, 20, 24]}
                tickFormatter={(v) => `${v}h`}
                tick={{ fontSize: 10, fill: T.textDim }}
                axisLine={{ stroke: T.border }}
                tickLine={false}
                label={{ value: "clock hour", position: "insideBottom", offset: -8, fill: T.textDim, fontSize: 11 }}
              />
              <YAxis
                type="number"
                dataKey="day"
                domain={[-0.5, 6.5]}
                ticks={[0, 1, 2, 3, 4, 5, 6]}
                tickFormatter={(v) => `D${v + 1}`}
                tick={{ fontSize: 10, fill: T.textDim }}
                axisLine={{ stroke: T.border }}
                tickLine={false}
                width={48}
              />
              <ZAxis dataKey="R" range={[20, 200]} />
              <Tooltip
                contentStyle={tipStyle}
                formatter={(v, n) => [n === "R" ? (v as number).toFixed(3) : (v as number).toFixed(1), n as string]}
                labelFormatter={() => ""}
              />
              <ReferenceArea x1={0} x2={5} fill="rgba(91,99,120,0.10)" />
              <ReferenceArea x1={22} x2={24} fill="rgba(91,99,120,0.10)" />
              <Scatter name="wake" data={wakeOnly} fill={ARCHETYPES[archetype].color} fillOpacity={0.7} />
              <Scatter name="user msg" data={msgOnly} fill={T.accent} shape="cross" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
        <p style={{ fontSize: 11, color: T.textDim, marginTop: 12, ...mono }}>
          shaded bands = sleep-trough hours (00:00-05:00, 22:00-24:00) · circles = sampled heartbeat wakes · cross marks = injected user messages
        </p>
      </Card>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Section 08 — Branching ratio + stability inspector
// ─────────────────────────────────────────────────────────────────────
function StabilityInspector() {
  const [eUser, setEUser] = useState(1.2);
  const [eGame, setEGame] = useState(1.0);
  const [eInternal, setEInternal] = useState(1.0);
  const [aUser, setAUser] = useState(ALPHA.user_msg);
  const [aGame, setAGame] = useState(ALPHA.game_event);
  const [aInternal, setAInternal] = useState(ALPHA.internal);

  const branching = useMemo(
    () =>
      branchingRatio(
        { user_msg: aUser, game_event: aGame, internal: aInternal },
        { user_msg: eUser, game_event: eGame, internal: eInternal },
      ),
    [aUser, aGame, aInternal, eUser, eGame, eInternal],
  );

  const margin = 1.0 - branching;
  const stable = branching < 1.0;

  // Decay envelope after a single user message
  const decay = useMemo(() => {
    const N = 80;
    const horizon = 12;
    return Array.from({ length: N + 1 }, (_, i) => {
      const t = (horizon * i) / N;
      const R0 = aUser * eUser * BETA;
      return { t, R: R0 * Math.exp(-BETA * t) };
    });
  }, [aUser, eUser]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Card>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
          <div>
            <Tag color={T.accent} bg={T.accentDim}>Stability</Tag>
            <div style={{ ...mono, fontSize: 14, color: T.text, marginTop: 16, lineHeight: 1.6 }}>
              n = Σ<sub>k</sub> α<sub>k</sub> · E[w<sub>k</sub>] &lt; 1
            </div>
            <p style={{ fontSize: 12, color: T.textDim, lineHeight: 1.7, marginTop: 12 }}>
              Hawkes branching ratio. n &lt; 1 means each event spawns &lt; 1 follow-on event in
              expectation; the system is stable. n ≥ 1 is critical/explosive — every event
              triggers more than one in expectation, so R diverges.
            </p>
            <div
              style={{
                marginTop: 20,
                padding: "16px 18px",
                background: stable ? "rgba(123,170,200,0.08)" : "rgba(243,131,187,0.12)",
                border: `1px solid ${stable ? "rgba(123,170,200,0.20)" : "rgba(243,131,187,0.30)"}`,
              }}
            >
              <div style={{ ...mono, fontSize: 11, color: T.textDim, letterSpacing: "0.1em", textTransform: "uppercase" }}>
                Current branching ratio
              </div>
              <div
                style={{
                  ...mono,
                  fontSize: 28,
                  fontWeight: 600,
                  color: stable ? "#7BAAC8" : T.accent,
                  marginTop: 4,
                  letterSpacing: "-0.02em",
                }}
              >
                {branching.toFixed(3)}
              </div>
              <div style={{ ...mono, fontSize: 11, color: T.textMuted, marginTop: 4 }}>
                {stable ? `STABLE — margin ${margin.toFixed(3)}` : "EXPLOSIVE — n ≥ 1"}
              </div>
            </div>
          </div>
          <div>
            <Tag color={T.lavender} bg={T.lavDim}>Tune α and E[w]</Tag>
            <Slider label="α[user_msg]" value={aUser} min={0} max={0.8} step={0.01} onChange={setAUser} format={(v) => v.toFixed(2)} />
            <Slider label="α[game_event]" value={aGame} min={0} max={0.5} step={0.01} onChange={setAGame} format={(v) => v.toFixed(2)} />
            <Slider label="α[internal]" value={aInternal} min={0} max={0.3} step={0.01} onChange={setAInternal} format={(v) => v.toFixed(2)} />
            <Slider label="E[w_user]" value={eUser} min={0.1} max={3.0} step={0.05} onChange={setEUser} format={(v) => v.toFixed(2)} />
            <Slider label="E[w_game]" value={eGame} min={0.1} max={3.0} step={0.05} onChange={setEGame} format={(v) => v.toFixed(2)} />
            <Slider label="E[w_internal]" value={eInternal} min={0.1} max={3.0} step={0.05} onChange={setEInternal} format={(v) => v.toFixed(2)} />
          </div>
        </div>
      </Card>

      <Card>
        <CardLabel sub="Single-event excitation decay (R₀ = α_user · E[w_user] · β; T_½ = 3h)">
          Single-event impulse response
        </CardLabel>
        <div style={{ width: "100%", height: 240 }}>
          <ResponsiveContainer>
            <LineChart data={decay}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="t"
                type="number"
                domain={[0, 12]}
                ticks={[0, 2, 4, 6, 8, 10, 12]}
                tickFormatter={(v) => `${v}h`}
                tick={{ fontSize: 10, fill: T.textDim }}
                axisLine={{ stroke: T.border }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: T.textDim }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => (v as number).toFixed(3)}
              />
              <Tooltip
                contentStyle={tipStyle}
                labelFormatter={(v) => `t = ${(v as number).toFixed(1)}h`}
                formatter={(v) => [`${(v as number).toFixed(4)}`, "R(t)"]}
              />
              <ReferenceLine x={T_HALF_HRS} stroke={T.accent} strokeDasharray="4 4" label={{ value: "T_½", position: "top", fill: T.accent, fontSize: 11 }} />
              <ReferenceLine x={2 * T_HALF_HRS} stroke="rgba(255,255,255,0.10)" strokeDasharray="4 4" label={{ value: "2·T_½", position: "top", fill: T.textDim, fontSize: 10 }} />
              <Line type="monotone" dataKey="R" stroke={T.accent} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Static section components (architecture, roadmap, citations)
// ─────────────────────────────────────────────────────────────────────
function ProblemRecap() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
      <Card>
        <Tag color={T.textMuted}>Today (reactive only)</Tag>
        <p style={{ fontSize: 13, color: T.textMuted, lineHeight: 1.7, marginTop: 16 }}>
          9 active pg_cron jobs as of 2026-04-17. Zero are dedicated to life simulation.
          LifeSimStage runs only inside the per-conversation pipeline — if a user goes silent
          for 3 days, no events generate. The first message triggers <em>post-hoc fabrication</em>{" "}
          of &ldquo;what Nikita has been doing.&rdquo;
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
            marginTop: 16,
          }}
        >
          nikita-process-conversations &nbsp;<span style={{ color: T.textDim }}>*/5min</span>
          <br />
          nikita-deliver &nbsp;<span style={{ color: T.textDim }}>*/5min</span>
          <br />
          nikita-decay &nbsp;<span style={{ color: T.textDim }}>hourly</span>
          <br />
          nikita-summary &nbsp;<span style={{ color: T.textDim }}>daily 23:59</span>
          <br />
          <span style={{ color: T.accent }}>… no heartbeat.</span>
        </div>
      </Card>
      <Card>
        <Tag color={T.accent} bg={T.accentDim}>Design intent</Tag>
        <p style={{ fontSize: 13, color: T.textMuted, lineHeight: 1.7, marginTop: 16 }}>
          A real heartbeat: distribution-based routine, never zero anywhere, smooth time-varying
          parameters. Sleep + work + personal + social overlays. Hourly safety-net cron always on,
          dynamic self-scheduling drops on top, function of (Nikita&apos;s life × user events).
        </p>
        <p style={{ fontSize: 12, color: T.textDim, lineHeight: 1.7, marginTop: 16 }}>
          User messages wake her immediately; she decides respond-now-vs-later; she also
          re-assesses ALL forward-looking schedule (HARD-REPLAN trigger).
        </p>
        <p style={{ fontSize: 11, color: T.textDim, lineHeight: 1.7, marginTop: 12, ...mono }}>
          Better than OpenClaw&apos;s fixed-interval + checklist. Inspired by Park et al. 2023 daily-arc model.
        </p>
      </Card>
    </div>
  );
}

function Architecture() {
  const layers: Array<[string, string, string, string]> = [
    ["1", "Activity distribution", "p(a | t)", "von Mises mixture · softmax · ε noise floor"],
    ["2", "Per-activity rate", "ν_a (heartbeats/h)", "5 hand-tuned constants · sleep 0.05 · personal 1.0"],
    ["3", "Hawkes excitation", "R(t)", "exponential kernel · T_½ = 3h · capped at R_max"],
    ["4", "Modulators", "M_ch · M_eng", "5 chapters × 5 engagement states multiply baseline"],
    ["5", "Total intensity", "λ_total = λ_baseline + R", "scalar > 0 everywhere"],
    ["6", "Self-scheduling", "Ogata thinning", "sample t_next from inhomogeneous Hawkes"],
  ];
  return (
    <Card>
      <table style={{ ...mono, fontSize: 13, width: "100%", borderCollapse: "collapse" }}>
        <tbody>
          {layers.map(([n, name, sym, desc]) => (
            <tr key={n} style={{ borderBottom: `1px solid ${T.border}` }}>
              <td style={{ padding: "12px 14px 12px 0", color: T.textDim, width: 48 }}>L{n}</td>
              <td style={{ padding: "12px 14px 12px 0", color: T.text, width: 200 }}>{name}</td>
              <td style={{ padding: "12px 14px 12px 0", color: T.accent }}>{sym}</td>
              <td style={{ padding: "12px 0", color: T.textDim }}>{desc}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function PhaseRoadmap() {
  const phases: Array<{ phase: string; eta: string; tag: string; color: string; bullets: string[] }> = [
    {
      phase: "Phase 1 — MVE",
      eta: "5-7 days",
      tag: "ships first",
      color: T.accent,
      bullets: [
        "Daily-plan + safety-net hourly cron (no Hawkes runtime)",
        "nikita_daily_plan table (RLS user-scoped read)",
        "POST /tasks/heartbeat + POST /tasks/generate-daily-arcs",
        "Math model offline only (this page validates parameters)",
        "Cost circuit breaker: $50/day cap",
      ],
    },
    {
      phase: "Phase 2 — Hawkes self-scheduling",
      eta: "5-7 days",
      tag: "after monitors clean 7d",
      color: T.lavender,
      bullets: [
        "Ogata thinning sampler wired to scheduled_events",
        "Watchdog hourly cron re-bootstraps degenerate users",
        "users.timezone IANA column (R6 fix)",
        "MC validator + live parity validator (KS-test nightly)",
      ],
    },
    {
      phase: "Phase 3 — Bayesian + reflection",
      eta: "7-10 days",
      tag: "after monitors clean 14d",
      color: "#7BAAC8",
      bullets: [
        "users.bayesian_state JSONB (admin-only RLS)",
        "Per-user Beta posteriors; Mardia-Jupp κ updater",
        "End-of-day reflection cycle (LLM) feeding next-day plan",
        "Shadow → 10% → full rollout per Doc 30 §11",
      ],
    },
  ];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1 }}>
      {phases.map((p) => (
        <Card key={p.phase}>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div>
              <Tag color={p.color} bg={`${p.color}1A`}>{p.tag}</Tag>
            </div>
            <div style={{ ...sans, fontSize: 16, fontWeight: 500, color: T.text }}>{p.phase}</div>
            <div style={{ ...mono, fontSize: 11, color: T.textDim }}>ETA {p.eta}</div>
            <ul style={{ paddingLeft: 16, color: T.textMuted, fontSize: 12, lineHeight: 1.7, marginTop: 4 }}>
              {p.bullets.map((b, i) => (
                <li key={i} style={{ marginBottom: 6 }}>{b}</li>
              ))}
            </ul>
          </div>
        </Card>
      ))}
    </div>
  );
}

function Citations() {
  const refs: Array<[string, string, string]> = [
    ["Park et al. 2023", "Generative Agents (UIST)", "arXiv:2304.03442"],
    ["Hawkes 1971", "Spectra of self-exciting point processes", "Biometrika 58(1):83"],
    ["Ozaki 1979", "MLE for Hawkes processes", "AISM 31(1):145-155"],
    ["Rizoiu et al. 2017", "Hawkes for social media (tutorial)", "arXiv:1708.06401"],
    ["Kobayashi & Lambiotte 2016", "TiDeH: time-dependent Hawkes for retweets", "arXiv:1603.09449"],
    ["Ye, Van Niekerk & Rue 2025", "Principled priors for Bayesian circular models", "arXiv:2502.18223"],
    ["Borbely 2016", "Two-process model reappraisal", "JSR sleep research"],
    ["BLS ATUS 2024", "American Time Use Survey", "bls.gov/news.release/atus"],
    ["NVIDIA NemoClaw 2026", "OpenClaw heartbeat reference", "Zylon technical post"],
  ];
  return (
    <Card>
      <table style={{ ...mono, fontSize: 12, width: "100%", borderCollapse: "collapse" }}>
        <tbody>
          {refs.map(([author, title, where], i) => (
            <tr key={i} style={{ borderBottom: `1px solid ${T.border}` }}>
              <td style={{ padding: "10px 14px 10px 0", color: T.text, width: 220 }}>{author}</td>
              <td style={{ padding: "10px 14px 10px 0", color: T.textMuted }}>{title}</td>
              <td style={{ padding: "10px 0", color: T.accent }}>{where}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Page default export
// ─────────────────────────────────────────────────────────────────────
export default function HeartbeatExplorerPage() {
  const [mounted, setMounted] = useState(false);
  // SSR-hydration mount-guard idiom (matches response-timing/page.tsx).
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <div style={{ background: T.bg, color: T.text, minHeight: "100vh", ...sans }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px 80px" }}>
          <header style={{ marginBottom: 40 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
              <Tag color={T.accent} bg={T.accentDim}>Spec 215</Tag>
              <Tag>von Mises × Hawkes × Ogata thinning</Tag>
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
              Heartbeat Engine Model — Decision Brief
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
            <Tag color={T.accent} bg={T.accentDim}>Spec 215</Tag>
            <Tag>von Mises × Hawkes × Ogata thinning</Tag>
            <Tag color={T.lavender} bg={T.lavDim}>2026-04-18</Tag>
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
            Heartbeat Engine Model — Decision Brief
          </h1>
          <p style={{ fontSize: 14, color: T.textMuted, lineHeight: 1.6, maxWidth: 720, marginTop: 0 }}>
            Stochastic life-simulation engine. Inhomogeneous Hawkes process with circadian
            baseline (von Mises mixture over 5 activities), per-event excitation, and Ogata
            thinning for self-scheduling. Source: <code style={{ ...mono, fontSize: 12, color: T.accent }}>nikita/heartbeat/intensity.py</code>
            {" "} · MC validator: <code style={{ ...mono, fontSize: 12, color: T.accent }}>scripts/models/heartbeat_intensity_mc.py</code>.
          </p>
        </header>

        {(
          [
            [1, "Problem recap", "why a dedicated heartbeat exists", ProblemRecap],
            [2, "Six-layer architecture", "math + interaction stack", Architecture],
            [3, "Activity distribution", "Layer 1 — von Mises × softmax × ε floor", ActivityDistribution],
            [4, "Marginal baseline", "Layer 2-4 — λ_baseline(t, ch, eng)", MarginalBaseline],
            [5, "Hawkes excitation", "Layer 3 — event-burst impulse response", HawkesExplorer],
            [6, "Inter-wake distribution", "Layer 6 — Ogata thinning per chapter", InterwakeDistribution],
            [7, "1-week wake sequences", "3 user archetypes over 7 days", WeekSequences],
            [8, "Stability inspector", "Hawkes branching ratio < 1", StabilityInspector],
            [9, "Phase 1 / 2 / 3 roadmap", "shipping order + safety nets", PhaseRoadmap],
            [10, "Citations + cross-refs", null, Citations],
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
          <span>Spec 215 PR 215-G · 2026-04-18</span>
          <span>nikita/heartbeat/intensity.py + scripts/models/heartbeat_intensity_mc.py</span>
        </footer>
      </div>
    </div>
  );
}
