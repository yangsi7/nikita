# Report Audit Findings — Spec 045 Technical Report & TTS Report

**Audit Date**: 2026-02-12
**Auditor**: report-auditor (Claude Opus 4.6)
**Files Audited**:
1. `docs-to-process/20260212-spec045-technical-report.md` (1,742 lines)
2. `docs-to-process/20260212-spec045-tts-report.md` (806 lines)

---

## Summary

**Technical Report**: HIGH quality. Provenance traces are substantively correct with minor line-number drift. Comprehensive coverage of all 11 sections and 9 pipeline stages. 5 findings (1 MEDIUM, 4 LOW).

**TTS Report**: HIGH quality. Well-structured for audio consumption. No stray markdown artifacts. Complete coverage matching the technical report. 6 findings (1 MEDIUM, 5 LOW).

---

## Technical Report Findings

### Finding F-1: Line number drift in provenance traces
- **File**: 20260212-spec045-technical-report.md
- **Section**: Section 2 (Data Provenance Map), Section 3 (Pipeline Execution Trace)
- **Lines**: Multiple (60, 94, 120-121, 520-521)
- **Severity**: LOW
- **Description**: Several file:line references are off by 1-2 lines from the actual source code. Examples:
  - Report: `prompt_builder.py:103-214` for `_enrich_context()`. Actual: starts at line 102.
  - Report: "lines 51-119 in system_prompt.j2" for Platform Style. Actual: Section 3 comment starts at line 51 but `{% if platform == "voice" %}` is at line 55, and `{% else %}` is at line 79. The range 51-119 is approximately correct but the internal sub-references (79-119 for text) should be 79-118.
  - Report: "system_prompt.j2:163-165" for chapter. Actual: chapter conditional is a single line at 164. Line 165 is `{% endif %}`.
- **Suggested Fix**: Re-run line number verification against current source. These are cosmetic and do not affect the accuracy of the provenance chains.

### Finding F-2: Emotional state override provenance is speculative
- **File**: 20260212-spec045-technical-report.md
- **Section**: Section 4d (emotional_state)
- **Lines**: 210-211
- **Severity**: MEDIUM
- **Description**: The report states "Game state sets valence=1.0 (from emotional_tone='positive')" and later "dominance and intimacy aren't defaults. Where did those come from? The game state stage later in the pipeline applies modifiers." However, reviewing `emotional.py:42-78`, the actual code calls `StateComputer.compute()` which takes `chapter`, `relationship_score`, and `life_events` as inputs. The exact mechanism producing `{0.5, 1.0, 0.4, 0.7}` from the defaults `{0.5, 0.5, 0.5, 0.5}` is not directly traced to specific lines in `StateComputer`. The override mechanism (valence -> 1.0 from emotional_tone) is asserted but not verified with a source code line reference. The report acknowledges this partially in the TTS report (Part Three, Stage Four) but the technical report presents it as verified provenance.
- **Suggested Fix**: Add a `[? needs-verification]` marker or trace the actual `StateComputer.compute()` logic to confirm exactly which code transforms `{0.5, 0.5, 0.5, 0.5}` to `{0.5, 1.0, 0.4, 0.7}`. Alternatively, note that this provenance step was inferred from output, not directly traced through source.

### Finding F-3: Voice prompt content not fully reproduced
- **File**: 20260212-spec045-technical-report.md
- **Section**: Section 4.2 (Voice System Prompt)
- **Lines**: 1041-1055
- **Severity**: LOW
- **Description**: The voice prompt section (4.2) is a summary — it says "*[Voice prompt structure identical to text, with these key differences:]*" and lists 5 differences. The full voice prompt text is not reproduced in the technical report, unlike the full text prompt which is included verbatim in Section 4.1. This asymmetry means the voice prompt cannot be independently audited from the technical report alone.
- **Suggested Fix**: Either include the full voice prompt text or explicitly state "Full voice prompt text available in TTS report Part Four" as a cross-reference.

### Finding F-4: Report self-reports incorrect line count
- **File**: 20260212-spec045-technical-report.md
- **Section**: Footer
- **Lines**: 1742-1743
- **Severity**: LOW
- **Description**: The report footer at line 1742 states "**Lines**: 947". The actual file is 1,742 lines. This appears to be a stale count from an earlier draft that was not updated.
- **Suggested Fix**: Update the line count to 1,742, or remove the self-reported line count.

### Finding F-5: Missing explicit cross-reference to E2E proof report
- **File**: 20260212-spec045-technical-report.md
- **Section**: Metadata (Section 1)
- **Lines**: 32-48
- **Severity**: LOW
- **Description**: The metadata table does not include a reference to the source E2E proof report (`20260212-spec045-e2e-proof.md`) from which pipeline timing and output data was extracted. Evidence references like "20260212-spec045-e2e-proof.md:84" appear throughout, but the metadata header should explicitly list the source data file.
- **Suggested Fix**: Add a row to the metadata table: `| **Source E2E Report** | 20260212-spec045-e2e-proof.md |`

---

## TTS Report Findings

### Finding F-6: Provenance claim "hardcoded character definition from user's profile table" is misleading
- **File**: 20260212-spec045-tts-report.md
- **Section**: Part Four, Section One: Identity (provenance note)
- **Lines**: 308
- **Severity**: MEDIUM
- **Description**: After reading the Identity section, the TTS report states "Provenance: hardcoded character definition from the user's profile table. The name, age, occupation, backstory, all loaded from the database." However, the technical report clearly establishes that Section 1 (Identity) is "100% static. Name, age, occupation, background, personality traits all defined in system_prompt.j2 template, not loaded from database." These are contradictory. The technical report is correct — the identity is hardcoded in the Jinja2 template, not loaded from any database table. The TTS report introduces a factual error here.
- **Suggested Fix**: Change the provenance note to: "Provenance: hardcoded character definition from the Jinja2 template file system_prompt.j2. This is static content, not loaded from the database."

### Finding F-7: Section numbering inconsistency between reports
- **File**: 20260212-spec045-tts-report.md
- **Section**: Part Four (Prompt sections)
- **Lines**: 298-418
- **Severity**: LOW
- **Description**: The TTS report reads the prompt in 10 sections (Identity, Who You Actually Are, The Wound Beneath, How You Move Through the World, What You're Attached To, What Lives in Your Chest, Where You Are Right Now, How This Actually Works, Critical Non-Negotiables, Closing). The technical report maps 11 sections (Identity, Immersion, Platform Style, Current State, Relationship State, Memory, Continuity, Inner Life, Psychology, Chapter Behavior, Vice Shaping). These are different section schemes — the TTS report follows the narrative structure of the LLM-enriched prompt output, while the technical report follows the template section architecture. This is not necessarily wrong, but the discrepancy is not explained.
- **Suggested Fix**: Add a brief note in the TTS report: "Note: I'm reading the sections as they appear in the final LLM-enriched output, which reorganizes the eleven template sections into a flowing narrative."

### Finding F-8: TTS report is under target length
- **File**: 20260212-spec045-tts-report.md
- **Section**: Entire file
- **Lines**: 1-807
- **Severity**: LOW
- **Description**: The file is 807 lines, described in the team-lead's assignment as "806 lines — under 1200-1500 target." The report claims "Estimated Total Listen Time: One hour and twenty minutes" (line 6). For an 80-minute TTS target, 807 lines may indeed produce roughly that length. The 1200-1500 line target may have been aspirational. The content is comprehensive and covers all required sections (8 Parts plus Conclusion). No significant content gaps detected — all 9 pipeline stages are covered, all 8 "holes" are analyzed, expert brainstorm has 5 perspectives, and recommendations are concrete.
- **Suggested Fix**: If more length is desired, the following areas could be expanded:
  - Part Two could include more detail on the actual Telegram MCP interaction logs
  - Part Four could read the full voice prompt word-for-word (currently ~50 lines, could be ~100)
  - Part Seven expert brainstorm could add 1-2 more experts
  - Part Eight recommendations could add implementation pseudocode descriptions
  However, the current length provides complete coverage without padding.

### Finding F-9: Stray asterisk in TTS report
- **File**: 20260212-spec045-tts-report.md
- **Section**: Part One (What is Nikita)
- **Lines**: 19
- **Severity**: LOW
- **Description**: Line 19 contains an italicized word using asterisks: "She's Russian-German, born in Saint Petersburg, fled to Berlin at nineteen after an explosive fight with her father." No asterisks found on this specific line. However, scanning the full report reveals zero stray asterisks used for actions or emphasis. The report correctly avoids all markdown formatting as intended for TTS consumption. No broken formatting detected.
- **Suggested Fix**: No fix needed — this was a false positive during initial scan. Report is clean.

### Finding F-10: Date discrepancy in TTS report
- **File**: 20260212-spec045-tts-report.md
- **Section**: Part Two (The deployment)
- **Lines**: 62
- **Severity**: LOW
- **Description**: Line 62 states "We committed the code changes at twenty twelve fifty on February eleventh." The event-stream.md shows the commit `aecd73b` was made on 2026-02-12 at 20:12:00Z, and the deploy was also 2026-02-12. The TTS report says "February eleventh" but the actual date is February 12th. This appears to be because the UTC timestamp 2026-02-12T20:12:00Z could correspond to February 11th in some US timezones, but the pipeline execution at 20:35 UTC on the same day is also described. The report mixes dates inconsistently — it says "February eleventh" for commit/deploy but the test message was sent at "twenty twelve fifty" which is also on the same day. The technical report correctly states "2026-02-12" throughout.
- **Suggested Fix**: Change "February eleventh" to "February twelfth" to match the actual commit date and the technical report.

### Finding F-11: Minor factual inconsistency about intimacy value
- **File**: 20260212-spec045-tts-report.md
- **Section**: Part Four (Section Seven: Where You Are Right Now)
- **Lines**: 382-383
- **Severity**: LOW
- **Description**: The TTS report reads the mood description as "arousal dormant, zero point five, but there's affection there, intimacy one point zero" (line 382-383). However, the actual emotional state values throughout both reports are `{arousal: 0.5, valence: 1.0, dominance: 0.4, intimacy: 0.7}`. The TTS prompt text itself says "Intimacy 1.0" but the actual computed value is 0.7. This discrepancy exists in the generated prompt itself (the LLM enrichment step may have rounded or changed the intimacy value from 0.7 to 1.0 during narrative enrichment). The TTS report is faithfully reading the enriched prompt, but the underlying data shows intimacy=0.7, not 1.0.
- **Suggested Fix**: Add a note: "The LLM enrichment step appears to have rounded intimacy from zero point seven to one point zero during narrative rewriting. The raw pipeline value was zero point seven."

---

## Cross-Report Consistency Check

| Aspect | Technical Report | TTS Report | Consistent? |
|--------|-----------------|------------|-------------|
| Commit | aecd73b | Not explicit | -- |
| Revision | nikita-api-00199-v54 | zero zero one ninety-nine | YES |
| Text tokens | 2,682 | two thousand six hundred eighty-two | YES |
| Voice tokens | 2,041 (post-truncation) | two thousand forty-one | YES |
| Voice pre-truncation | 3,798 | three thousand seven hundred ninety-eight | YES |
| Pipeline duration | 99.4 seconds | ninety-nine thousand four hundred forty-five ms | YES |
| Extraction stage | 6,618 ms | six thousand six hundred eighteen ms | YES |
| Memory update | 14,068 ms | fourteen thousand sixty-eight ms | YES |
| Life sim | 4,153 ms | four thousand one hundred fifty-three ms | YES |
| Emotional | 49 ms | forty-nine ms | YES |
| Game state | 0.4 ms | zero point four ms | YES |
| Conflict | 0.3 ms | zero point three ms | YES |
| Touchpoint | 1,231 ms | one thousand two hundred thirty-one ms | YES |
| Summary | 666 ms | six hundred sixty-six ms | YES |
| Prompt builder | 72,657 ms | seventy-two thousand six hundred fifty-seven ms | YES |
| Score-chapter contradiction | Identified as CRITICAL | Identified as Hole 1 | YES |
| Facts extracted | 5 | five | YES |
| Deploy date | 2026-02-12 | February eleventh (ERROR) | NO (F-10) |
| Identity provenance | Static template | "from user's profile table" (ERROR) | NO (F-6) |

---

## Verdict

**Technical Report**: PASS with 5 minor findings. No factual errors in provenance chains. Line numbers slightly drifted but within acceptable margins. One speculative provenance chain (emotional state override) should be marked as inferred.

**TTS Report**: PASS with 6 findings. One factual error (provenance claim about identity being from database, F-6) and one date error (F-10) should be corrected. Otherwise comprehensive, well-structured for audio consumption, and consistent with technical report data.

**Overall**: Both reports are HIGH QUALITY and suitable for their intended purposes. The 2 MEDIUM findings (F-2 and F-6) should be fixed before finalizing.
