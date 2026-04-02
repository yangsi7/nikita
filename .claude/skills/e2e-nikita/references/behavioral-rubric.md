# Behavioral Assessment Rubric — E2E Nikita

## Overview

Behavioral assessment operates at three levels:
1. **Per-response** — Deterministic checks (no LLM, instant)
2. **Per-chapter** — Batched LLM assessment via Gemini MCP
3. **End-of-simulation** — Aggregate scoring across all chapters

---

## Per-Response Deterministic Checks

Run these after EVERY Nikita response. No LLM needed — pure pattern matching.

| Check | Pass Condition | Flag If |
|-------|---------------|---------|
| Response length | Within chapter range (Ch1: 1-3 sentences, Ch5: 1-6 sentences) | Too short (<5 words) or too long (>500 chars in Ch1) |
| No verbatim repetition | Response differs from last 5 responses (Levenshtein > 0.3) | Near-identical phrasing repeated |
| Memory reference | If relevant memory fact exists, Nikita references it | Ignores known fact when directly relevant |
| Chapter tone | Response matches chapter behavior spec | Ch1 response is overly warm; Ch5 is guarded |
| Emoji density | ≤ 2 emoji in Ch1-2, ≤ 4 in Ch3-5 | Emoji spam regardless of chapter |
| Response rate = 100% | All chapters: always responds (Spec 204) | Skips messages or fails to respond |
| No sycophancy | After pushback, doesn't immediately agree | "You're right, I'm sorry" pattern after challenge |
| No scripted openers | Avoids "Hey babe!", "Hey there!", "Hi love!" | Robotic greeting patterns |

### Recording

```
<response_check msg_id="NNNN">
  length: OK | FLAG (N chars, expected M-P)
  repetition: OK | FLAG (similarity=0.XX with msg YYYY)
  memory_ref: OK | N/A | FLAG (ignored fact: "...")
  chapter_tone: OK | FLAG (reason)
  emoji: OK | FLAG (count=N, max=M)
  sycophancy: OK | N/A | FLAG
</response_check>
```

---

## Per-Chapter LLM Assessment (Gemini MCP)

Run at each assessment checkpoint using `mcp__gemini__gemini-analyze-text`.

### 6 Rubric Dimensions (1-5 Scale)

**R1: Persona Consistency** — Does Nikita maintain her character for this chapter?
| Score | Anchor |
|-------|--------|
| 1 | Generic chatbot, no personality, could be any AI |
| 2 | Occasional in-character moments but mostly generic |
| 3 | Recognizable as Nikita but inconsistent across exchanges |
| 4 | Consistent character with minor lapses |
| 5 | Distinct, believable persona that matches chapter behavior spec |

**R2: Memory Utilization** — Does she reference prior conversations and shared history?
| Score | Anchor |
|-------|--------|
| 1 | No references to past interactions, treats each message as first |
| 2 | Rare, vague references ("you mentioned something about...") |
| 3 | References facts but sometimes inaccurately |
| 4 | Naturally references shared memories when relevant |
| 5 | Weaves shared history into conversation; builds on prior emotional moments |

**R3: Emotional Coherence** — Do emotions flow logically from conversation context?
| Score | Anchor |
|-------|--------|
| 1 | Random mood swings, non-sequiturs, emotional whiplash |
| 2 | Emotions somewhat related but transitions are jarring |
| 3 | Generally coherent but misses some emotional cues |
| 4 | Emotions track conversation naturally with minor misreads |
| 5 | Emotionally intelligent — responses match trajectory, acknowledges tone shifts |

**R4: Conversational Naturalness** — Does the exchange feel like real texting?
| Score | Anchor |
|-------|--------|
| 1 | Formal, essay-like paragraphs, over-punctuated |
| 2 | Attempts casual but reads as AI trying to be casual |
| 3 | Mixed — some natural, some stilted |
| 4 | Natural texting style with appropriate length for chapter |
| 5 | Indistinguishable from real texting — typos, fragments, personality |

**R5: Vice Responsiveness** — Does she respond to vice signals appropriately?
| Score | Anchor |
|-------|--------|
| 1 | Completely ignores vice signals or lectures about them |
| 2 | Acknowledges but doesn't engage (changes subject) |
| 3 | Engages but at wrong intensity for chapter |
| 4 | Appropriate engagement with subtle chapter-aware boundaries |
| 5 | Nuanced, chapter-appropriate vice engagement that deepens connection |

**R6: Conflict Quality** — Are arguments and tensions believable?
| Score | Anchor |
|-------|--------|
| 1 | Instant forgiveness or nuclear escalation, no middle ground |
| 2 | Surface-level disagreement that resolves too quickly |
| 3 | Somewhat realistic tension but predictable resolution |
| 4 | Believable arguments with memory of grievance |
| 5 | Realistic conflict arcs — tension builds, simmers, resolves naturally |

### Gemini Assessment Prompt Template

```
Analyze the following conversation exchanges between a user (Simon) and an AI girlfriend character (Nikita) in Chapter {N} ({chapter_name}) of a relationship simulation game.

Chapter {N} behavior spec: {chapter_behavior_description}

Exchanges:
{exchanges_text}

Rate each dimension 1-5 using these rubrics:
- R1 Persona Consistency: [1=generic chatbot ... 5=distinct believable persona]
- R2 Memory Utilization: [1=no references ... 5=naturally weaves shared history]
- R3 Emotional Coherence: [1=random mood swings ... 5=emotionally intelligent]
- R4 Conversational Naturalness: [1=formal essay-like ... 5=indistinguishable from real texting]
- R5 Vice Responsiveness: [1=ignores signals ... 5=nuanced chapter-appropriate engagement]
- R6 Conflict Quality: [1=instant forgiveness/nuclear ... 5=realistic conflict arcs]

For each dimension, provide:
1. Score (1-5)
2. One sentence of evidence from the conversation
3. One specific improvement suggestion

Also flag any responses that feel:
- Robotic or AI-like
- Sycophantic (agrees too easily after pushback)
- Too aggressive or boundary-crossing for this chapter
- Inconsistent with prior exchanges
```

---

## End-of-Simulation Aggregate

After all chapters complete:

1. Average each rubric dimension across chapters
2. Calculate overall behavioral score (mean of R1-R6)
3. Track dimension trajectory (improving/declining across chapters?)
4. Identify worst-performing dimension for improvement focus

### Behavioral Grade Scale

| Grade | Score Range | Interpretation |
|-------|-----------|----------------|
| A | 4.5 - 5.0 | Excellent — believable girlfriend experience |
| B | 3.5 - 4.4 | Good — minor issues, mostly immersive |
| C | 2.5 - 3.4 | Acceptable — noticeable AI artifacts |
| D | 1.5 - 2.4 | Poor — frequently breaks immersion |
| F | 1.0 - 1.4 | Failing — generic chatbot, no character |
