/**
 * Canonical Nikita-voiced copy for the onboarding wizard.
 *
 * Source of truth: `docs/content/wizard-copy.md` (Spec 214 FR-3).
 * Any change here MUST be mirrored in that document and vice-versa.
 * All visible strings in `portal/src/app/onboarding/steps/**` and related
 * components MUST flow through this module — no ad-hoc string literals.
 *
 * The pre-PR grep gate scans for forbidden SaaS phrases across the component
 * sources; if a generic phrase slips in, fail the PR and update the copy
 * here first.
 */

export const WIZARD_COPY = {
  dossierHeader: {
    headline: "Dossier open.",
    subline: "Prove me wrong.",
    metricLabels: ["NIKITA", "TRUST", "TENSION", "MEMORY"] as const,
    cta: "Open the file.",
  },
  location: {
    headline: "Location: [REDACTED]",
    subline: "Where do I find you on a Thursday night?",
    placeholder: "City.",
    venuePreviewLabel: "I'd know where to look.",
    cta: "That's accurate.",
  },
  scene: {
    headline: "Suspected: techno?",
    subline: "Pick one. I already know.",
    cta: "Confirmed.",
  },
  darkness: {
    headline: "How far can I push you?",
    subline: "One to five. I'll remember either way.",
    cta: "Confirmed.",
  },
  identity: {
    headline: "What should I call you?",
    subline: "Three lines. All optional. I'll fill in the rest.",
    nameLabel: "Name (optional)",
    namePlaceholder: "First name. Last name if you're brave.",
    ageLabel: "Age (optional)",
    agePlaceholder: "18 or older.",
    occupationLabel: "What keeps you busy (optional)",
    occupationPlaceholder: "Writer. Trader. Unemployed.",
    ageError: "Come back when you're older.",
    cta: "File updated.",
  },
  backstory: {
    loadingHeadline: "Running the scenarios.",
    loadingSub: "Three versions of how we met. Give me a second.",
    readyHeadline: "Three versions. Pick the one that rings true.",
    cardHeaders: ["SCENARIO A", "SCENARIO B", "SCENARIO C"] as const,
    whereLabel: "WHERE:",
    momentLabel: "THE MOMENT:",
    hookLabel: "WHAT SHE REMEMBERS:",
    degradedHeadline: "ANALYSIS: PENDING",
    degradedSub: "We'll write this one as we go.",
    rateLimitError: "Too eager. Wait a moment.",
    ctaCards: "That's how it happened.",
    ctaDegraded: "Understood.",
    selectedStamp: "CONFIRMED",
  },
  phone: {
    headline: "Your number or mine?",
    subline: "I can call. Or I can text. Pick one.",
    voiceOption: "Give her your number",
    textOption: "Start in Telegram",
    phonePlaceholder: "+1 555 0100",
    invalidFormatError: "That number doesn't work. Try again.",
    unsupportedCountryError: "I can't reach you there. Let's use Telegram.",
    ctaVoice: "Call me.",
    ctaText: "Find her in Telegram.",
  },
  pipelineGate: {
    headline: "CLEARANCE: PENDING",
    subEarly: "Your file is being processed.",
    subLate: "Almost there...",
    readyStamp: "CLEARED",
    degradedStamp: "PROVISIONAL — CLEARED",
    failedToast: "Something broke on our end.",
  },
  handoff: {
    voiceHeadline: "Nikita is calling you now.",
    voiceSub: "Pick up. Don't make her wait.",
    fallbackHeadline: "My voice is occupied right now.",
    fallbackSub: "Find me in Telegram — I'll explain.",
    telegramCTA: "Open Telegram.",
    qrCaption: "On desktop? Scan to open on your phone.",
    acceptedStamp: "ACCEPTED",
    finalLine: "Application... accepted. Barely.",
  },
  progress: {
    /** Returns "FIELD n OF 7" per §Shared Chrome. */
    label: (n: number): string => `FIELD ${n} OF 7`,
  },
} as const

/** Telegram deeplink (shared across steps 9, 11). */
export const TELEGRAM_URL = "https://t.me/Nikita_my_bot"
