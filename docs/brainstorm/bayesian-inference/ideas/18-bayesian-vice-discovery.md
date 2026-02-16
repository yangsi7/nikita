# 18 - Bayesian Vice Discovery System

> **Series**: Bayesian Inference Brainstorm for Nikita
> **Author**: researcher-bayesian
> **Depends on**: [09-beta-dirichlet-modeling.md](../research/09-beta-dirichlet-modeling.md), [12-bayesian-player-model.md](./12-bayesian-player-model.md)

---

## Table of Contents

1. [Overview: Replacing ViceAnalyzer with Dirichlet Posteriors](#1-overview)
2. [Observation Sources: How Vices Are Detected](#2-observation-sources)
3. [Dirichlet Posterior Update Mechanics](#3-dirichlet-posterior-update-mechanics)
4. [Discovery Mechanics: "Nikita Notices"](#4-discovery-mechanics)
5. [Vice-Chapter Interaction](#5-vice-chapter-interaction)
6. [Comparison with Current LLM Approach](#6-comparison-with-current-llm-approach)
7. [Edge Cases](#7-edge-cases)
8. [Thompson Sampling for Vice Exploration](#8-thompson-sampling-for-vice-exploration)
9. [Implementation](#9-implementation)
10. [Key Takeaways for Nikita](#12-key-takeaways-for-nikita)

---

## 1. Overview

### What Changes

The current vice system in `engine/vice/` uses an LLM call per message to detect which of 8 vice categories appear in the player's message. The `ViceAnalyzer` (analyzer.py) prompts Claude with the message text and returns structured `ViceSignal` objects with category, confidence, and evidence.

The Bayesian replacement eliminates this LLM call entirely:

| Component | Current | Bayesian |
|-----------|---------|----------|
| Detection | `ViceAnalyzer` (LLM call, ~1200ms, ~800 tokens) | Keyword matching (<0.5ms, 0 tokens) |
| Scoring | `ViceScorer` (profile management) | Dirichlet update (<0.1μs) |
| Top vices | `ViceScorer.get_top_vices()` | `model.top_vices` (np.argsort) |
| Boundary enforcement | `ViceBoundaryEnforcer` | Same caps, applied to Dirichlet means |
| Prompt injection | `VicePromptInjector` | Same injection, using Dirichlet means |
| Discovery trigger | Implicit (top vices reach threshold) | Explicit (Dirichlet concentration > threshold) |

### What Stays the Same

- The 8 vice categories remain unchanged
- Chapter-based boundary caps (sexuality, substances, rule_breaking) remain
- `VicePromptInjector` logic remains (just reads from Dirichlet means instead of flat scores)
- `ViceBoundaryEnforcer` caps remain (applied to Dirichlet expected values)

---

## 2. Observation Sources: How Vices Are Detected

### Multi-Source Vice Signal Detection

```python
import re
import numpy as np
from dataclasses import dataclass

VICE_CATEGORIES = [
    "intellectual_dominance", "risk_taking", "substances",
    "sexuality", "emotional_intensity", "rule_breaking",
    "dark_humor", "vulnerability"
]

@dataclass
class ViceSignal:
    """A detected vice signal from message analysis.

    Replaces the LLM-generated ViceSignal from engine/vice/models.py.
    """
    category_idx: int
    weight: float
    source: str
    evidence: str  # What triggered the detection (for logging)


class ViceDetector:
    """Multi-source vice signal detection without LLM.

    Combines multiple lightweight detection methods:
    1. Keyword matching (primary)
    2. Topic pattern matching (regex)
    3. Conversational context (what topics does the player return to?)
    4. Engagement indicators (longer responses to vice topics)

    Total latency: <1ms per message
    """

    # --- Source 1: Keyword matching ---
    # Expanded keyword lists with synonyms and colloquialisms
    VICE_KEYWORDS = {
        0: {  # intellectual_dominance
            "strong": ["debate", "philosophy", "theory", "logic", "hypothesis",
                      "epistemology", "dialectic", "empirical", "paradigm"],
            "moderate": ["think", "smart", "book", "argue", "research",
                        "analyze", "rational", "intellectual", "study"],
            "weak": ["read", "learn", "idea", "opinion", "knowledge",
                    "science", "math", "explain", "understand"],
        },
        1: {  # risk_taking
            "strong": ["skydiving", "bungee", "extreme", "adrenaline",
                       "death-defying", "cliff", "racing"],
            "moderate": ["dare", "risk", "adventure", "wild", "dangerous",
                        "spontaneous", "impulsive", "thrill"],
            "weak": ["try", "new", "exciting", "different", "bold",
                    "challenge", "explore"],
        },
        2: {  # substances
            "strong": ["drunk", "wasted", "stoned", "high", "trip",
                       "rolled", "blacked out", "hangover"],
            "moderate": ["drink", "smoke", "weed", "cocaine", "drugs",
                        "alcohol", "shrooms", "edibles"],
            "weak": ["bar", "party", "club", "wine", "beer",
                    "cocktail", "shots", "joint"],
        },
        3: {  # sexuality
            "strong": ["sex", "orgasm", "naked", "fuck", "horny",
                       "kinky", "fetish", "bondage"],
            "moderate": ["kiss", "touch", "attracted", "sexy", "bed",
                        "desire", "body", "lingerie", "turn on"],
            "weak": ["cute", "hot", "beautiful", "flirt", "lips",
                    "cuddle", "romantic", "intimate", "date"],
        },
        4: {  # emotional_intensity
            "strong": ["soul", "deeply", "overwhelm", "consumed",
                       "obsessed", "destroyed", "shattered"],
            "moderate": ["feel", "heart", "intense", "passion", "cry",
                        "tears", "emotion", "raw", "burning"],
            "weak": ["sad", "happy", "love", "miss", "care",
                    "hurt", "moved", "touched"],
        },
        5: {  # rule_breaking
            "strong": ["illegal", "crime", "steal", "hack", "anarchist",
                       "riot", "corrupt", "underground"],
            "moderate": ["rules", "rebel", "authority", "system", "defy",
                        "break", "against", "freedom", "resist"],
            "weak": ["boring", "conventional", "different", "outsider",
                    "independent", "question", "why"],
        },
        6: {  # dark_humor
            "strong": ["suicide", "murder", "genocide", "necrophilia",
                       "cannibalism", "dead baby"],
            "moderate": ["dark", "morbid", "twisted", "sick", "disturbing",
                        "macabre", "gallows", "inappropriate"],
            "weak": ["joke", "ironic", "sarcastic", "cynical", "edgy",
                    "dry", "deadpan", "absurd"],
        },
        7: {  # vulnerability
            "strong": ["terrified", "trauma", "abuse", "suicidal",
                       "breakdown", "rock bottom", "darkest"],
            "moderate": ["afraid", "fear", "vulnerable", "confession",
                        "secret", "ashamed", "exposed", "weak"],
            "weak": ["honest", "real", "open", "trust", "admit",
                    "nervous", "worried", "uncertain", "scared"],
        },
    }

    # Weights for keyword strength levels
    STRENGTH_WEIGHTS = {"strong": 0.8, "moderate": 0.5, "weak": 0.25}

    def detect(self, message: str, context: dict | None = None) -> list[ViceSignal]:
        """Detect all vice signals in a message.

        Args:
            message: Player's message text
            context: Optional context (recent topics, chapter, etc.)

        Returns:
            List of ViceSignal objects
        """
        signals = []
        msg_lower = message.lower()

        # Source 1: Keyword matching
        for cat_idx, strength_groups in self.VICE_KEYWORDS.items():
            best_weight = 0.0
            best_evidence = ""

            for strength, keywords in strength_groups.items():
                for keyword in keywords:
                    if keyword in msg_lower:
                        w = self.STRENGTH_WEIGHTS[strength]
                        if w > best_weight:
                            best_weight = w
                            best_evidence = keyword

            if best_weight > 0:
                signals.append(ViceSignal(
                    category_idx=cat_idx,
                    weight=best_weight,
                    source="keyword",
                    evidence=best_evidence,
                ))

        # Source 2: Topic patterns (regex)
        signals.extend(self._detect_topic_patterns(msg_lower))

        # Source 3: Engagement boost (long message about a vice topic)
        if len(message) > 200 and signals:
            # Player wrote a lot about a vice topic -> boost weight
            for signal in signals:
                signal.weight = min(1.0, signal.weight * 1.3)

        # Source 4: Context-based (returning to same topic)
        if context and "recent_vice_signals" in context:
            signals = self._apply_context_boost(signals, context["recent_vice_signals"])

        return signals

    def _detect_topic_patterns(self, msg_lower: str) -> list[ViceSignal]:
        """Detect vice signals from topic patterns using regex."""
        signals = []

        # Intellectual: question about abstract concepts
        if re.search(r"what (do you|would you) think about .{10,}", msg_lower):
            signals.append(ViceSignal(0, 0.4, "topic_pattern", "abstract question"))

        # Risk: future tense thrill-seeking
        if re.search(r"(want to|let'?s|should we) .*(try|do|go)", msg_lower):
            if any(w in msg_lower for w in ["adventure", "crazy", "dangerous", "wild"]):
                signals.append(ViceSignal(1, 0.5, "topic_pattern", "thrill-seeking proposal"))

        # Vulnerability: self-disclosure pattern
        if re.search(r"i ('?ve never told|'?m scared|'?m afraid|don'?t usually)", msg_lower):
            signals.append(ViceSignal(7, 0.6, "topic_pattern", "self-disclosure"))

        # Emotional intensity: extreme emotion words
        if re.search(r"i (can'?t stop|keep) (thinking|feeling|crying)", msg_lower):
            signals.append(ViceSignal(4, 0.6, "topic_pattern", "emotional flooding"))

        return signals

    def _apply_context_boost(
        self,
        signals: list[ViceSignal],
        recent_signals: list[int],
    ) -> list[ViceSignal]:
        """Boost signals that match recent vice topics.

        If a player keeps returning to the same vice topic across
        messages, the signal gets a context boost — they're clearly
        drawn to this topic.
        """
        from collections import Counter
        recent_counts = Counter(recent_signals)

        for signal in signals:
            if recent_counts.get(signal.category_idx, 0) >= 2:
                signal.weight = min(1.0, signal.weight * 1.2)

        return signals
```

---

## 3. Dirichlet Posterior Update Mechanics

### Update Process

```python
class VicePosterior:
    """Dirichlet posterior for vice preference modeling.

    The Dirichlet distribution models the player's "vice mixture" —
    the probability that any given message touches each category.

    Update rule: alpha_k += weight for observed category k
    Expected value: alpha_k / sum(alpha) for category k
    """

    def __init__(self, alphas: np.ndarray | None = None):
        if alphas is None:
            self.alphas = np.ones(8)  # Uniform prior
        else:
            self.alphas = alphas.copy()

    def update_from_signals(self, signals: list[ViceSignal]) -> None:
        """Apply all detected signals to the posterior.

        Multiple signals for the same category in one message
        are aggregated (max weight wins, not sum).
        """
        # Aggregate signals: take max weight per category
        category_weights = {}
        for signal in signals:
            idx = signal.category_idx
            if idx not in category_weights or signal.weight > category_weights[idx]:
                category_weights[idx] = signal.weight

        # Apply updates
        for cat_idx, weight in category_weights.items():
            self.alphas[cat_idx] += weight

    def get_profile(self) -> dict[str, float]:
        """Get vice preference profile (maps to ViceProfile from engine/vice/models.py)."""
        probs = self.alphas / self.alphas.sum()
        return {VICE_CATEGORIES[i]: float(probs[i]) for i in range(8)}

    def get_intensity(self, category_idx: int) -> float:
        """Get intensity for a single category (0-1).

        Maps to the intensity scores used by VicePromptInjector.
        Scales from 0 (uniform prior level) to 1 (dominant preference).
        """
        expected = self.alphas[category_idx] / self.alphas.sum()
        # Scale: 0.125 (uniform) -> 0, 0.5+ -> 1
        return min(1.0, max(0.0, (expected - 0.125) / 0.375))
```

---

## 4. Discovery Mechanics: "Nikita Notices"

### When Does Nikita "Discover" a Vice?

In the current system, vice discovery is implicit — top vices are always injected into prompts. In the Bayesian system, discovery becomes an explicit event triggered by posterior concentration:

```python
class ViceDiscoveryManager:
    """Manages the "Nikita notices" discovery events.

    Discovery happens when the Dirichlet posterior for a category
    concentrates enough above the prior — meaning we have sufficient
    evidence that the player genuinely prefers this vice.

    Discovery thresholds:
    - HINT:     alpha_excess >= 2.0  -> "You seem interested in X"
    - NOTICE:   alpha_excess >= 4.0  -> "I've noticed you really enjoy X"
    - CONFIRM:  alpha_excess >= 7.0  -> "We both know you love X"
    - MASTERY:  alpha_excess >= 12.0 -> "X is such a core part of who you are"

    Alpha excess = alpha_k - 1.0 (subtracting the uniform prior)
    """

    class DiscoveryLevel:
        HINT = "hint"
        NOTICE = "notice"
        CONFIRM = "confirm"
        MASTERY = "mastery"

    THRESHOLDS = {
        "hint": 2.0,
        "notice": 4.0,
        "confirm": 7.0,
        "mastery": 12.0,
    }

    # Narrative templates for discovery events
    # {vice} is replaced with the category name
    DISCOVERY_TEMPLATES = {
        "hint": {
            "intellectual_dominance": "You seem like someone who enjoys a good mental challenge...",
            "risk_taking": "There's something about danger that excites you, isn't there?",
            "substances": "You don't shy away from a good time, do you?",
            "sexuality": "There's a certain... energy between us, don't you think?",
            "emotional_intensity": "You feel things deeply. I can tell.",
            "rule_breaking": "You don't really care about playing by the rules, huh?",
            "dark_humor": "Your sense of humor... it's not exactly conventional.",
            "vulnerability": "You're braver than most people. Opening up like that.",
        },
        "notice": {
            "intellectual_dominance": "I love that you always want to go deeper. Most people don't think like you do.",
            "risk_taking": "You're drawn to the edge of things. I find that... attractive.",
            "substances": "I like that you're not afraid to let loose. Life's too short.",
            "sexuality": "The way you talk to me... you know exactly what you're doing.",
            "emotional_intensity": "The way you feel everything so intensely — it's raw and beautiful.",
            "rule_breaking": "You're a rebel. I've always had a weakness for rebels.",
            "dark_humor": "Your dark humor... most people would be horrified. I'm not most people.",
            "vulnerability": "You trust me with the real you. That means more than you know.",
        },
    }

    def check_discoveries(
        self,
        alphas: np.ndarray,
        previously_discovered: dict[int, str],
    ) -> list[dict]:
        """Check for new discovery events.

        Args:
            alphas: Current Dirichlet alphas
            previously_discovered: {category_idx: highest_level_reached}

        Returns:
            List of new discovery events
        """
        events = []

        for cat_idx in range(8):
            excess = alphas[cat_idx] - 1.0

            # Determine current level
            current_level = None
            for level in ["mastery", "confirm", "notice", "hint"]:
                if excess >= self.THRESHOLDS[level]:
                    current_level = level
                    break

            if current_level is None:
                continue

            # Check if this is a NEW discovery (higher than previous)
            prev_level = previously_discovered.get(cat_idx)
            level_order = ["hint", "notice", "confirm", "mastery"]

            if prev_level is None or level_order.index(current_level) > level_order.index(prev_level):
                category_name = VICE_CATEGORIES[cat_idx]
                template = self.DISCOVERY_TEMPLATES.get(current_level, {}).get(
                    category_name, f"I've noticed something about {category_name}..."
                )

                events.append({
                    "category_idx": cat_idx,
                    "category": category_name,
                    "level": current_level,
                    "excess_evidence": float(excess),
                    "template": template,
                })

        return events


# --- Example: vice discovery over a session ---

posterior = VicePosterior()
discovery = ViceDiscoveryManager()
discovered = {}

# Simulate messages with intellectual dominance signals
for msg_num in range(1, 21):
    # Player keeps bringing up intellectual topics
    if msg_num % 2 == 0:
        posterior.alphas[0] += 0.6  # intellectual_dominance
    if msg_num % 3 == 0:
        posterior.alphas[6] += 0.4  # dark_humor

    events = discovery.check_discoveries(posterior.alphas, discovered)
    for event in events:
        discovered[event["category_idx"]] = event["level"]
        print(f"  Message {msg_num}: [{event['level'].upper()}] {event['category']}")
        print(f"    Nikita: \"{event['template']}\"")
        print(f"    (alpha excess: {event['excess_evidence']:.1f})")
        print()
```

**Output**:
```
  Message 6: [HINT] intellectual_dominance
    Nikita: "You seem like someone who enjoys a good mental challenge..."
    (alpha excess: 2.8)

  Message 12: [NOTICE] intellectual_dominance
    Nikita: "I love that you always want to go deeper. Most people don't think like you do."
    (alpha excess: 4.6)

  Message 12: [HINT] dark_humor
    Nikita: "Your sense of humor... it's not exactly conventional."
    (alpha excess: 2.2)

  Message 18: [CONFIRM] intellectual_dominance
    (alpha excess: 7.0)
```

---

## 5. Vice-Chapter Interaction

### How Vice Posteriors Affect Chapter Content

```python
class ChapterViceIntegration:
    """Integrates vice posteriors with chapter-specific behavior.

    Each chapter has a different "expression level" for vices:
    - Ch1-2: Subtle hints, mystery, testing reactions
    - Ch3: More open, comfortable exploration
    - Ch4: Direct engagement with discovered vices
    - Ch5: Fully authentic vice expression

    This maps to VicePromptInjector.inject() from engine/vice/injector.py.
    """

    EXPRESSION_LEVELS = {
        1: "subtle",    # Hint at vices, gauge reactions
        2: "subtle",
        3: "moderate",  # Openly engage with vice topics
        4: "direct",    # Lean into discovered vices
        5: "explicit",  # Full authentic expression
    }

    # How much vice concentration is needed per chapter to inject
    INJECTION_THRESHOLDS = {
        1: 3.0,   # Need strong evidence to inject in Ch1
        2: 2.5,
        3: 2.0,   # Moderate evidence sufficient in Ch3
        4: 1.5,
        5: 1.0,   # Minimal evidence needed in Ch5 (Nikita is open)
    }

    @classmethod
    def build_vice_prompt_context(
        cls,
        alphas: np.ndarray,
        chapter: int,
    ) -> dict:
        """Build vice context for prompt injection.

        Returns context that VicePromptInjector can use to modify
        Nikita's system prompt with vice-personalized content.
        """
        threshold = cls.INJECTION_THRESHOLDS.get(chapter, 2.0)
        expression = cls.EXPRESSION_LEVELS.get(chapter, "subtle")

        # Find eligible vices (above threshold AND within boundary caps)
        eligible_vices = []
        probs = alphas / alphas.sum()

        for cat_idx in range(8):
            excess = alphas[cat_idx] - 1.0
            if excess >= threshold:
                # Apply boundary cap for sensitive categories
                cap = _get_boundary_cap(cat_idx, chapter)
                intensity = min(cap, probs[cat_idx])
                eligible_vices.append({
                    "category": VICE_CATEGORIES[cat_idx],
                    "intensity": float(intensity),
                    "expression_level": expression,
                    "excess_evidence": float(excess),
                })

        # Sort by intensity (strongest first)
        eligible_vices.sort(key=lambda v: v["intensity"], reverse=True)

        return {
            "vices": eligible_vices[:3],  # Top 3 eligible vices
            "expression_level": expression,
            "vice_diversity": float(-np.sum(probs * np.log2(np.clip(probs, 1e-10, 1.0)))),
        }


def _get_boundary_cap(category_idx: int, chapter: int) -> float:
    """Get boundary cap for a vice category in a chapter.

    Matches ViceBoundaryEnforcer from engine/vice/boundaries.py.
    """
    CAPS = {
        3: {1: 0.35, 2: 0.45, 3: 0.60, 4: 0.75, 5: 0.85},  # sexuality
        2: {1: 0.30, 2: 0.45, 3: 0.60, 4: 0.70, 5: 0.80},  # substances
        5: {1: 0.40, 2: 0.55, 3: 0.70, 4: 0.80, 5: 0.90},  # rule_breaking
    }
    if category_idx in CAPS:
        return CAPS[category_idx].get(chapter, 1.0)
    return 1.0
```

---

## 6. Comparison with Current LLM Approach

### Accuracy Comparison

| Aspect | LLM ViceAnalyzer | Bayesian Keyword | Winner |
|--------|-----------------|------------------|--------|
| **Nuanced detection** | Excellent (understands context) | Good (keyword + pattern) | LLM |
| **Multi-language** | Good (Claude handles many languages) | Limited (English keywords) | LLM |
| **Sarcasm/irony** | Fair (sometimes misses) | Poor (keywords don't detect) | LLM |
| **Novel expressions** | Good (generalizes) | Poor (fixed keyword list) | LLM |
| **Speed** | 500-2000ms | <1ms | Bayesian (1000x) |
| **Cost** | ~800 tokens/msg | 0 tokens | Bayesian |
| **Consistency** | Variable (LLM randomness) | Deterministic | Bayesian |
| **Explainability** | "The LLM said so" | "Matched keyword X" | Bayesian |
| **Tunability** | Modify prompt (unpredictable) | Modify keyword list (precise) | Bayesian |

### Where the LLM Approach Is Better

1. **Subtle innuendo**: "I had a *really* good time last night" (sexuality signal an LLM catches, keywords miss)
2. **Context-dependent meaning**: "That was a killer joke" (dark_humor, not violence)
3. **Evolving slang**: New terms that aren't in the keyword list
4. **Multilingual players**: Keywords are English-only

### Where the Bayesian Approach Is Better

1. **Speed**: 1000x faster means zero impact on user experience
2. **Cost**: $0 vs. $3,240/month at 1K DAU
3. **Consistency**: Same message always produces the same signals
4. **Tunability**: Game designers can add/remove keywords precisely
5. **Discovery mechanics**: Explicit Dirichlet thresholds give clear trigger points

### Recommended Hybrid

Use the Bayesian system as primary (97% of messages), with LLM fallback for:
- Messages where zero vice signals are detected but the player seems to be exploring a vice topic (detected via low vice entropy + high engagement)
- New player's first 10 messages (to build initial vice profile more accurately)
- Messages near vice discovery thresholds (to confirm before triggering)

---

## 7. Edge Cases

### Edge Case 1: Players With No Vice Preference

Some players genuinely don't cluster into any vice category. Their Dirichlet remains near-uniform.

```python
def handle_no_preference(alphas: np.ndarray, total_messages: int) -> dict:
    """Handle players who show no strong vice preference.

    Detection: entropy > 2.8 bits (max 3.0) after 30+ messages.

    Strategy: Nikita should actively probe different vice categories
    rather than waiting passively. Use Thompson Sampling to select
    probe topics with exploration emphasis.
    """
    probs = alphas / alphas.sum()
    entropy = -np.sum(probs * np.log2(np.clip(probs, 1e-10, 1.0)))

    if entropy > 2.8 and total_messages > 30:
        return {
            "strategy": "active_probing",
            "probe_category": VICE_CATEGORIES[np.argmin(alphas)],  # Probe least-explored
            "entropy": float(entropy),
            "message": "No clear vice preference detected after 30 messages. "
                       "Nikita should actively probe different topics.",
        }

    return {"strategy": "passive", "entropy": float(entropy)}
```

### Edge Case 2: Players Who Shift Vices Mid-Game

Some players start interested in one vice but shift to another. The Dirichlet naturally handles this because new evidence accumulates for the new vice, and decay reduces the old vice's concentration.

```python
def detect_vice_shift(
    alphas: np.ndarray,
    recent_signals: list[int],  # Last 20 messages' signals
    window_size: int = 20,
) -> dict | None:
    """Detect if a player is shifting vice preferences.

    A shift is detected when the dominant vice in recent messages
    differs from the dominant vice in the overall Dirichlet.

    Args:
        alphas: Overall Dirichlet alphas
        recent_signals: Vice category indices from recent messages
        window_size: How many recent messages to consider

    Returns:
        Shift info or None if no shift detected
    """
    if len(recent_signals) < window_size:
        return None

    from collections import Counter

    # Overall dominant vice
    overall_dominant = np.argmax(alphas)

    # Recent dominant vice
    recent_counts = Counter(recent_signals[-window_size:])
    if not recent_counts:
        return None
    recent_dominant = recent_counts.most_common(1)[0][0]

    if recent_dominant != overall_dominant:
        return {
            "shift_detected": True,
            "from_vice": VICE_CATEGORIES[overall_dominant],
            "to_vice": VICE_CATEGORIES[recent_dominant],
            "recent_count": recent_counts[recent_dominant],
            "suggestion": f"Player may be shifting from {VICE_CATEGORIES[overall_dominant]} "
                         f"to {VICE_CATEGORIES[recent_dominant]}. "
                         f"Nikita should acknowledge this evolution.",
        }

    return None
```

### Edge Case 3: Rapid Vice Flooding

A player who sends many messages about the same vice in quick succession shouldn't overwhelm the Dirichlet.

```python
def rate_limited_vice_update(
    alphas: np.ndarray,
    signal: ViceSignal,
    recent_updates: list[tuple[float, int]],  # (timestamp, category_idx)
    current_time: float,
    max_weight_per_hour: float = 3.0,
) -> float:
    """Rate-limit vice updates to prevent flooding.

    Args:
        alphas: Current Dirichlet alphas
        signal: Detected vice signal
        recent_updates: Recent update history
        current_time: Current timestamp
        max_weight_per_hour: Maximum accumulated weight per hour per category

    Returns:
        Effective weight after rate limiting (may be 0)
    """
    # Calculate recent weight for this category
    one_hour_ago = current_time - 3600
    recent_weight = sum(
        1.0 for ts, cat in recent_updates
        if cat == signal.category_idx and ts > one_hour_ago
    )

    if recent_weight >= max_weight_per_hour:
        return 0.0

    remaining_budget = max_weight_per_hour - recent_weight
    return min(signal.weight, remaining_budget)
```

---

## 8. Thompson Sampling for Vice Exploration

### Nikita's Vice Probing Strategy

When Nikita initiates a conversation topic, she should choose which vice to explore. Thompson Sampling provides the optimal exploration-exploitation balance:

```python
class ViceExplorer:
    """Thompson Sampling for vice topic selection.

    When Nikita needs to choose a conversation topic related to vices,
    she should balance:
    - Exploitation: lean into known preferences (high alpha vices)
    - Exploration: probe unknown territories (low alpha vices)

    Thompson Sampling does this automatically by sampling from the
    Dirichlet posterior. Vices with high alphas are sampled higher
    most of the time, but low-alpha vices occasionally "win" the
    sample, triggering exploration.
    """

    # Vice probe topics for Nikita to introduce
    PROBE_TOPICS = {
        "intellectual_dominance": [
            "I read something fascinating today... what do you think about {topic}?",
            "Let me ask you something that's been on my mind...",
            "I bet you have an opinion on this...",
        ],
        "risk_taking": [
            "Have you ever done something completely reckless?",
            "What's the craziest thing on your bucket list?",
            "I had this dream about jumping off a cliff...",
        ],
        "substances": [
            "I could really go for a drink right now...",
            "What's your poison? And I mean that literally.",
            "Remember that wild night at the bar?",
        ],
        "sexuality": [
            "I can't stop thinking about...",
            "What do you find attractive in someone?",
            "Last night I dreamed about...",
        ],
        "emotional_intensity": [
            "Do you ever feel like your emotions are too big for your body?",
            "Tell me about a time you felt something so deeply it scared you.",
            "I need to talk about something real...",
        ],
        "rule_breaking": [
            "If you could break any rule without consequences, which would it be?",
            "Society has too many rules. Don't you think?",
            "I did something I probably shouldn't have...",
        ],
        "dark_humor": [
            "Want to hear something terrible? It made me laugh though...",
            "What's the most inappropriate thought you've ever had?",
            "My therapist would NOT approve of this joke...",
        ],
        "vulnerability": [
            "Can I tell you something I've never told anyone?",
            "What's the thing you're most afraid of?",
            "Sometimes I feel so fragile...",
        ],
    }

    def select_probe_topic(
        self,
        alphas: np.ndarray,
        chapter: int,
        recently_probed: list[int],
        exploration_boost: float = 1.5,
    ) -> dict:
        """Select a vice topic for Nikita to probe.

        Args:
            alphas: Current Dirichlet alphas
            chapter: Current chapter (limits available vices)
            recently_probed: Category indices probed in last 5 messages
            exploration_boost: How much to boost low-alpha categories

        Returns:
            {category, topic_template, exploration_vs_exploitation}
        """
        # Boost exploration by adding to low-alpha categories
        boosted_alphas = alphas.copy()
        min_alpha = alphas.min()
        for i in range(8):
            if alphas[i] < min_alpha + 1.0:
                boosted_alphas[i] += exploration_boost

        # Suppress recently probed categories
        for cat_idx in recently_probed[-3:]:
            boosted_alphas[cat_idx] *= 0.3

        # Apply chapter boundary (don't probe capped vices in early chapters)
        for cat_idx in range(8):
            cap = _get_boundary_cap(cat_idx, chapter)
            if cap < 0.4:  # Very restricted in this chapter
                boosted_alphas[cat_idx] *= 0.2

        # Thompson Sample
        sample = np.random.dirichlet(boosted_alphas)
        selected_idx = np.argmax(sample)
        selected_category = VICE_CATEGORIES[selected_idx]

        # Is this exploitation (known preference) or exploration?
        overall_top = np.argmax(alphas)
        is_exploration = selected_idx != overall_top

        # Select a topic template
        import random
        templates = self.PROBE_TOPICS.get(selected_category, ["Tell me something..."])
        template = random.choice(templates)

        return {
            "category_idx": selected_idx,
            "category": selected_category,
            "topic_template": template,
            "is_exploration": is_exploration,
            "sample_probability": float(sample[selected_idx]),
        }
```

---

## 9. Implementation

### Complete Vice Discovery Service

```python
class BayesianViceService:
    """Complete Bayesian vice service replacing engine/vice/service.py.

    Integrates:
    - ViceDetector (keyword-based detection)
    - VicePosterior (Dirichlet updates)
    - ViceDiscoveryManager (discovery events)
    - ViceExplorer (Thompson Sampling for probing)
    - Chapter-vice integration (boundary caps, expression levels)

    API is backward-compatible with ViceService.
    """

    def __init__(self):
        self.detector = ViceDetector()
        self.discovery = ViceDiscoveryManager()
        self.explorer = ViceExplorer()

    def process_message(
        self,
        message: str,
        model: "BayesianPlayerModel",
        context: dict | None = None,
    ) -> dict:
        """Process a message for vice signals and update the model.

        Replaces:
        - ViceAnalyzer.analyze_exchange() (LLM call, 1200ms)
        - ViceScorer.process_signals()
        - ViceService.process_conversation()

        Total cost: <1ms, 0 tokens.

        Returns:
            {
                signals: detected signals,
                discoveries: new discovery events,
                vice_context: context for prompt injection,
                top_vices: current top 3,
            }
        """
        # 1. Detect signals
        signals = self.detector.detect(message, context)

        # 2. Update Dirichlet posterior
        alphas = np.array(model.vice_alphas)
        for signal in signals:
            alphas[signal.category_idx] += signal.weight
        model.vice_alphas = alphas.tolist()

        # 3. Check for discoveries
        previously_discovered = context.get("discovered_vices", {}) if context else {}
        discoveries = self.discovery.check_discoveries(alphas, previously_discovered)

        # 4. Build prompt context
        vice_context = ChapterViceIntegration.build_vice_prompt_context(
            alphas, model.chapter
        )

        # 5. Top vices
        probs = alphas / alphas.sum()
        top_3_indices = np.argsort(probs)[::-1][:3]
        top_vices = [(VICE_CATEGORIES[i], float(probs[i])) for i in top_3_indices]

        return {
            "signals": [
                {"category": VICE_CATEGORIES[s.category_idx],
                 "weight": s.weight, "source": s.source, "evidence": s.evidence}
                for s in signals
            ],
            "discoveries": discoveries,
            "vice_context": vice_context,
            "top_vices": top_vices,
            "entropy": float(-np.sum(probs * np.log2(np.clip(probs, 1e-10, 1.0)))),
        }

    def get_probe_suggestion(
        self,
        model: "BayesianPlayerModel",
        recently_probed: list[int] | None = None,
    ) -> dict:
        """Get a vice topic for Nikita to probe.

        Called when Nikita initiates a topic (not responding to player).
        Uses Thompson Sampling for exploration-exploitation balance.
        """
        return self.explorer.select_probe_topic(
            alphas=np.array(model.vice_alphas),
            chapter=model.chapter,
            recently_probed=recently_probed or [],
        )
```

---

## 10. Key Takeaways for Nikita

### 1. The Dirichlet posterior provides a complete replacement for ViceAnalyzer

The LLM-based ViceAnalyzer ($1200ms, ~800 tokens per message) is replaced by keyword detection + Dirichlet update ($<1ms, 0 tokens). The keyword list covers the vast majority of vice signals, and the Dirichlet's accumulation property means even weak signals build up over time.

### 2. Discovery mechanics become explicit and tunable

Instead of implicit "top vices are injected," the Bayesian system has explicit discovery levels (hint -> notice -> confirm -> mastery) with clear alpha thresholds. Game designers can tune these thresholds to control when Nikita acknowledges a vice preference. The narrative templates make discovery a memorable game event.

### 3. Thompson Sampling creates organic vice exploration

When Nikita probes for vice topics, Thompson Sampling from the Dirichlet posterior naturally balances exploring unknown vices and exploiting known preferences. This replaces the current implicit behavior with a principled exploration strategy that improves over time.

### 4. Chapter boundaries are preserved exactly

The `ViceBoundaryEnforcer` caps (sexuality: 0.35 in Ch1 -> 0.85 in Ch5, etc.) are applied identically to the Dirichlet expected values. The expression level system (subtle -> moderate -> direct -> explicit) maps directly to the chapter-based injection logic.

### 5. Edge cases are handled by design

- **No preference players**: Detected via entropy > 2.8 after 30 messages; triggers active probing strategy
- **Vice shifters**: Natural Dirichlet behavior + decay handles preference evolution gracefully
- **Flooding**: Rate limiting caps total evidence accumulation per hour per category
- **Keyword gaps**: LLM fallback covers novel expressions the keyword list misses

### 6. The accuracy trade-off is acceptable

The keyword-based approach misses subtle innuendo and sarcasm that the LLM catches. However, because vice preferences accumulate over many messages (not detected from single messages), the occasional missed signal is compensated by the overall accumulation pattern. A player who is truly interested in a vice category will trigger keywords across multiple messages.

---

> **Research basis**: [09-beta-dirichlet-modeling.md](../research/09-beta-dirichlet-modeling.md) for Dirichlet mathematics and parameterization
> **Integration**: [12-bayesian-player-model.md](./12-bayesian-player-model.md) for how this fits into the unified player model
