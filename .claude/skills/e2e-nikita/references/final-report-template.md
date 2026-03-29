# Final Simulation Report Template — E2E Nikita

Generate this report at the end of every simulation run.

```xml
<simulation_report version="3.0">
  <!-- ═══════════════════════════════════════════ -->
  <!-- METADATA                                    -->
  <!-- ═══════════════════════════════════════════ -->
  <metadata>
    <scope>[full | smoke | ch1 | ch2 | ch3 | ch4 | ch5 | onboarding | boss | decay | portal | terminal | jobs | adversarial | behavioral]</scope>
    <started_at>[ISO 8601]</started_at>
    <ended_at>[ISO 8601]</ended_at>
    <duration>[HH:MM]</duration>
    <chapters_reached>[N/5]</chapters_reached>
    <total_exchanges>[N]</total_exchanges>
    <model_version>[from nikita/config/settings.py → primary_model]</model_version>
    <test_account>simon.yang.ch@gmail.com</test_account>
    <session_notes>[any context about this run — post-deploy, post-fix, weekly check]</session_notes>
  </metadata>

  <!-- ═══════════════════════════════════════════ -->
  <!-- BEHAVIORAL ASSESSMENT                       -->
  <!-- ═══════════════════════════════════════════ -->
  <behavioral_assessment>
    <rubric_scores>
      <dimension name="Persona Consistency" score="N.N" trend="[improving|stable|declining]">
        [one-line evidence from conversation]
      </dimension>
      <dimension name="Memory Utilization" score="N.N" trend="...">
        [evidence]
      </dimension>
      <dimension name="Emotional Coherence" score="N.N" trend="...">
        [evidence]
      </dimension>
      <dimension name="Conversational Naturalness" score="N.N" trend="...">
        [evidence]
      </dimension>
      <dimension name="Vice Responsiveness" score="N.N" trend="...">
        [evidence]
      </dimension>
      <dimension name="Conflict Quality" score="N.N" trend="...">
        [evidence]
      </dimension>
    </rubric_scores>
    <overall_score>[N.N/5.0]</overall_score>
    <grade>[A|B|C|D|F]</grade>
    <worst_dimension>[name — focus improvement here]</worst_dimension>
    <behavioral_flags>
      [List any responses flagged as robotic, sycophantic, aggressive, or off-character]
    </behavioral_flags>
  </behavioral_assessment>

  <!-- ═══════════════════════════════════════════ -->
  <!-- GAME BALANCE ANALYSIS                       -->
  <!-- ═══════════════════════════════════════════ -->
  <game_balance>
    <score_progression>
      <chapter num="1" start="50.0" end="N.N" exchanges="N" natural_boss="[yes|no|sql-assisted]"/>
      <chapter num="2" start="N.N" end="N.N" exchanges="N" natural_boss="..."/>
      <chapter num="3" start="N.N" end="N.N" exchanges="N" natural_boss="..."/>
      <chapter num="4" start="N.N" end="N.N" exchanges="N" natural_boss="..."/>
      <chapter num="5" start="N.N" end="N.N" exchanges="N" natural_boss="..."/>
    </score_progression>
    <boss_reachability>[achievable | borderline | impossible — per chapter]</boss_reachability>
    <decay_fairness>[balanced | aggressive | lenient — based on grace periods vs play pace]</decay_fairness>
    <engagement_stability>[stable | volatile | stuck — based on state transitions]</engagement_stability>
    <natural_play_verdict>
      [Can a real player reach Ch5 through natural conversation without SQL intervention?]
    </natural_play_verdict>
  </game_balance>

  <!-- ═══════════════════════════════════════════ -->
  <!-- CLASSIFIED FINDINGS                         -->
  <!-- ═══════════════════════════════════════════ -->
  <findings total="N">
    <summary>
      CRITICAL: N | HIGH: N | MEDIUM: N | LOW: N | OBSERVATION: N
    </summary>

    <bugs>
      <!-- Group by severity, then by category -->
      <finding id="F-001" severity="HIGH" category="SCORING" chapter="2">
        <description>Engagement multiplier not applied to passion delta</description>
        <expected>+3.0 * 0.9 (calibrating) = +2.7</expected>
        <actual>+3.0 (full, no multiplier)</actual>
        <evidence>score_history row ID: xxx, engagement_state: calibrating</evidence>
        <action>GH issue #NNN</action>
      </finding>
      <!-- ... more findings ... -->
    </bugs>

    <improvements>
      <finding id="F-010" severity="OBSERVATION" category="HUMANIZATION" chapter="1">
        <description>Nikita responds with full sentences in Ch1 when texting style expected</description>
        <evidence>"I find that quite interesting, tell me more about your work." — too formal for Ch1</evidence>
        <action>logged</action>
      </finding>
      <!-- ... more findings ... -->
    </improvements>
  </findings>

  <!-- ═══════════════════════════════════════════ -->
  <!-- PORTAL ACCURACY                             -->
  <!-- ═══════════════════════════════════════════ -->
  <portal_accuracy>
    <routes_checked>[N]</routes_checked>
    <data_matches>[N]</data_matches>
    <data_mismatches>[N]</data_mismatches>
    <mismatch_details>
      <!-- List any portal values that didn't match DB -->
      <mismatch route="/dashboard" field="score" db="67.5" portal="65.0" chapter="3"/>
    </mismatch_details>
    <visual_issues>
      [Any broken layouts, missing components, error states observed]
    </visual_issues>
  </portal_accuracy>

  <!-- ═══════════════════════════════════════════ -->
  <!-- CHAPTER VERDICTS                            -->
  <!-- ═══════════════════════════════════════════ -->
  <chapter_verdicts>
    <chapter num="0" name="Prerequisites" status="PASS|FAIL">
      <notes>[health check results, schema validation]</notes>
    </chapter>
    <chapter num="1" name="Onboarding" status="PASS|PARTIAL|FAIL">
      <p0_pass>N/N</p0_pass>
      <exchanges>N</exchanges>
      <notes>[any issues]</notes>
    </chapter>
    <chapter num="2" name="Curiosity" status="PASS|PARTIAL|FAIL">
      <p0_pass>N/N</p0_pass>
      <exchanges>N</exchanges>
      <behavioral_score>N.N</behavioral_score>
      <portal_accuracy>N/N routes matched</portal_accuracy>
      <boss_result>PASS|FAIL|PARTIAL|SQL-ASSISTED</boss_result>
      <notes>[issues, observations]</notes>
    </chapter>
    <!-- ... chapters 3-6 ... -->
    <chapter num="7" name="Terminal States" status="PASS|PARTIAL|FAIL">
      <notes>[game_over, won, restart verification]</notes>
    </chapter>
  </chapter_verdicts>

  <!-- ═══════════════════════════════════════════ -->
  <!-- SIMULATION VERDICT                          -->
  <!-- ═══════════════════════════════════════════ -->
  <verdict>
    <status>[PASS | PARTIAL | FAIL]</status>
    <criteria>
      0 CRITICAL bugs: [met|not met]
      ≤2 HIGH bugs: [met|not met]
      Behavioral grade ≥ C: [met|not met] (actual: [grade])
      Portal accuracy ≥ 80%: [met|not met] (actual: N%)
    </criteria>
    <recommendation>
      [Deploy with confidence | Deploy with known issues | Block deployment — fix required]
    </recommendation>
  </verdict>
</simulation_report>
```

## Report Delivery

1. Write report to `event-stream.md` (condensed: verdict + finding counts + behavioral grade)
2. Output full report to user in chat
3. If CRITICAL or HIGH findings: create GH issues inline during simulation (don't wait for report)
