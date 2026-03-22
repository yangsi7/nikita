# Onboarding Research: Game, AI Companion, and Auth Patterns
**Research Date**: 2026-03-22
**Confidence**: 88%
**Anchor Sources**: NN/G Onboarding Tutorials (authority 10) + Amplitude 7% Retention Rule (authority 9) + MojoAuth Auth Friction (authority 8)

---

## Executive Summary

Five findings that apply directly to Nikita's onboarding design:

1. **The first 7 minutes decide everything.** Amplitude's 2025 benchmark across 2,600 products shows that if you get users to their "aha moment" in week one, 69% of them are still active at month three. Miss that window and no later investment recovers them.
2. **Upfront tutorials are almost always wrong.** NN/G research shows tutorials interrupt users at the worst moment, are quickly forgotten, and do not improve task performance. Contextual "pull" hints triggered by user behavior outperform them in every tested scenario.
3. **Auth friction kills before the game even starts.** 25% of users abandon account creation at the password-setting step alone. Each additional auth step (OTP, email verification, then re-login) costs 10-15% of the remaining funnel. For a Telegram-based game, this is partly mitigated — but the web portal registration flow needs scrutiny.
4. **AI companions live or die on memory and continuity, not features.** Replika's visual customization and gamified rooms create strong first sessions but poor long-term retention because memory is shallow. Nomi's approach — prioritizing persistent memory over visual polish — produces deeper emotional attachment. This maps directly to Nikita's scoring/memory system as the core retention lever.
5. **Make the onboarding itself the game.** Duolingo earns gems before asking for an email. Headspace celebrates finishing an 8-screen flow. LinkedIn's progress bar boosted profile completion by 55%. The pattern: the onboarding *is* the first level.

---

## Anchor Sources

**1. NN/G: "Onboarding Tutorials vs. Contextual Help" (2023)**
URL: https://www.nngroup.com/articles/onboarding-tutorials/
Authority: 10/10 — Nielsen Norman Group empirical research
Why foundational: Provides the definitive framework for when tutorials work vs. fail. Introduces push revelation (bad) vs. pull revelation (good) distinction. Directly answers research question 5 with empirical backing.
Key sections: "Why Tutorials Don't Work", "What Works: Pull Revelations", "Guidelines for Implementing Pull Revelations"

**2. Amplitude: "The 7% Retention Rule" (2025)**
URL: https://amplitude.com/blog/7-percent-retention-rule
Authority: 9/10 — based on 2025 Product Benchmark Report analyzing 2,600+ companies
Why foundational: Provides the most rigorous quantitative framework for first-week activation. Shows that 7% day-7 retention = top 25% performance, and that 69% of top week-1 activators are also top 3-month retainers. Answers research question 4 with hard data.
Key sections: "The Correlation Between 7-Day Activation and 3-Month Retention", "How Top Products Turn Early Activation Into Long-Term Retention"

---

## Core Findings by Category

### 1. AI Companion App Onboarding (Replika, Nomi, Character.AI)

**What works:**

- **Personality-first, not form-first.** Nomi's onboarding asks: name, gender, avatar, trait set, and optionally a custom backstory. At no point is billing requested during setup. Replika leads with a visual quiz and relationship category selection — but gates non-friend relationships behind a paywall immediately, which users find alienating.
- **The companion comes to life as the first experience.** Both apps put the first conversation before account setup is fully "complete." This delivers immediate emotional value before any commitment is asked.
- **Nomi's "Mind Map" as a memory visualization tool** is a powerful long-term retention feature: users can see their relationship history as an interconnected web. This creates psychological investment — they've built something they don't want to lose.
- **Replika's mistake**: heavy upfront monetization prompts and reliance on environmental visuals (AR rooms, avatar shops) over conversational depth. Users describe it as "starting fresh each session" — the memory is shallow and rarely surfaces in conversation.

**What does not work:**

- Paywall gating of core relationship features during onboarding. Replika shows upgrade modals before the first conversation; users who hit this feel manipulated.
- Visual novelty without conversational depth. Replika's 3D avatar system is engaging in session 1 but doesn't create long-term attachment because the AI doesn't remember the relationship context.
- Generic scripted opening messages. Replika's first reply follows a supportive counselor template that feels formulaic by the third conversation.

**Applies to Nikita:**
Nikita's approach (Telegram-native, relationship metrics, vice personalization, chapter progression) maps more closely to Nomi's memory-first model than Replika's visual-first model. The relationship score and chapter system *are* the retention mechanism. The onboarding should establish that these matter early.

---

### 2. Progressive Disclosure in Games

**The core principle:** Introduce one mechanic at a time, only when the player is about to need it. Never frontload.

**Duolingo's evolution (2018-2024):**
- In 2018, Duolingo had single-digit user growth. Their CPO identified that gamification (not content quality) was the lever.
- Key insight: Duolingo earns gems *before asking for an email or creating an account.* The user completes a 3-minute demo lesson, gets points, and *then* hits the registration wall — but by then they've already experienced value and have something to protect (their streak, their progress).
- Leaderboards increased learning time by 17%. Push notification optimization (timing, copy, localization) produced "substantial gains in DAU."
- Day 1 retention went from 13% to 55%+ through gamification improvements alone.
- **Personalization was the biggest single unlock**: asking users their goal and experience level first, then tailoring content to that, dramatically increased activation.

**Headspace's 8-screen onboarding:**
- Despite being long (8 screens), it works because:
  - Each screen asks one question (learning + personalization)
  - The final screen is a celebration milestone ("you're done")
  - Users arrive at the home screen seeing content relevant to their stated goals, not a generic dashboard
- The celebration at the end of a long onboarding reframes it as a "level completed" rather than an admin task.

**Gacha game patterns (F2P handbook):**
The F2P design handbook is gated but the summary findings align with general research:
- First 5 minutes must include: combat/core mechanic demo, first reward drop, visible progression indicator
- Never explain the gacha system upfront — let players discover it after emotional investment is established
- "Pity mechanics" and early guaranteed pulls are onboarding tools, not endgame design
- Tutorial length: optimal is 3-5 minutes of forced guidance, then release into free play with contextual hints

**The Zeigarnik Effect and progress bars:**
LinkedIn boosted profile completion by 55% by showing a progress bar that highlights *missing* information rather than completed items. The psychological tension of an "80% complete" indicator drives users to finish more reliably than any reward.

**Applies to Nikita:**
The scoring system (4 relationship metrics) and chapter progression (1-5) map naturally to a progress visualization. Players should see their current score/chapter status early — not as a tutorial, but as an ambient indicator that creates Zeigarnik tension.

---

### 3. Web Portal + Chat App Hybrid Onboarding

**The gap:** No direct research was found on products that split onboarding across Telegram + web portal. However, adjacent patterns from AI SaaS products with chat + dashboard designs are applicable.

**Best pattern from research:**
- **Establish value in the chat channel first.** The chat experience (Telegram in Nikita's case) is where emotional investment is built. The portal should be positioned as "the place to understand what's happening" — not as a parallel onboarding surface.
- **Deep link from chat to portal with context.** When Nikita mentions a player's score or chapter progression in Telegram, that's the natural moment to send a portal link — not during initial signup. The portal becomes meaningful *after* the player has context to understand it.
- **Avoid parallel registration flows.** Requiring users to separately register on both Telegram (via `/start`) and create a portal account is a significant friction multiplier. The portal should authenticate against the existing Telegram identity where possible.
- **Use the portal for transparency, not for additional onboarding.** Players who are invested in Telegram will seek out the portal to understand their relationship metrics. This is the aha moment for the portal — not an onboarding gate.

**Dashboard browser.london observation (2026):**
Split web+mobile experiences work best when the mobile/chat experience handles the emotional arc and the web dashboard handles comprehension and control. The onboarding responsibility belongs to whichever channel the user encounters first.

**Applies to Nikita:**
Telegram is the primary engagement channel. The portal should be introduced organically from within Telegram conversations ("want to see your relationship stats? tap here") rather than as a mandatory registration step.

---

### 4. Engagement Hooks: First 5 Minutes

**Amplitude's 7% Rule (2025, n=2,600 products):**
- Products where 7% of the original cohort returns on day 7 are in the top 25% for activation performance
- 69% of those top day-7 performers are also top 3-month performers
- For 50% of all products, over 98% of new users are gone by week 2
- Enterprise products: top 10% achieve 12.4% day-7 retention; median is 2.1% (6x gap)

**What creates the aha moment:**
ProductLed framework (October 2024):
- Aha moment = emotional realization that the product will be valuable (BEFORE activation)
- Activation = first hands-on experience of that value
- The goal is to engineer the aha moment to occur *before* the user has to do hard work (form filling, account setup)
- Example: Uber's aha moment is reading "order a car in minutes" on the Play Store description — before installing. Activation is the first ride.
- Demo data > empty states: showing a pre-populated dashboard with example data creates the aha moment more reliably than showing an empty screen with instructions

**What causes drop-off in minute 1-5:**
- Empty states with no social proof or demo content
- Any form field that requires memorized information (passwords, usernames they haven't chosen yet)
- Feature tours that interrupt before the user has formed an intent to do anything
- Paywall gates before first value delivery
- Cognitive overload: more than one decision at a time

**The "endowed progress effect" (Quora pattern):**
Pre-filling some checklist items as already complete — even trivial ones like "Visit your feed" — dramatically increases checklist completion rates. Users are 3x more likely to finish a checklist if they feel they already have momentum.

**Applies to Nikita:**
The first Telegram message from Nikita *is* the aha moment. It needs to feel personal, responsive, and emotionally engaging immediately — not scripted. The player should feel "oh, this is different" within 2 exchanges. The scoring system should not be mentioned in session 1 — let the relationship feel organic first.

---

### 5. Tutorial vs. Learning-by-Doing

**NN/G verdict (empirical, 2023):**
> "Tutorials interrupt users, don't necessarily improve task performance, and are quickly forgotten."

**Push revelation (avoid):**
- Triggered at app launch or login, regardless of user intent
- Shown out of context
- Requires memorization of steps shown before the user needs them
- Users skip them or forget them immediately
- Even well-designed mandatory tutorials (like ArcGIS's interactive one) fail because users can't recall steps after the tutorial ends without finding it again

**Pull revelation (use this):**
- Triggered by user behavior that signals they need the information NOW
- Shown in context (e.g., when user hovers a new button, when they reach a new feature for the first time)
- No memorization required — the hint appears at the moment of use
- Easy to dismiss AND easy to re-find
- Uses progressive disclosure (show existence, reveal depth only if asked)

**When tutorials ARE appropriate:**
- Novel interaction paradigms with no existing mental model (NN/G found AR walkthroughs were genuinely useful because AR has no familiar interaction template)
- First-time workflows with irreversible consequences (e.g., "before you send your first message, here's what happens to your score")
- When the tutorial requires the user to *practice* the action (not just watch) — interactive practice is retained; passive watching is not

**Figma's model:**
Pull reveal only when user opens a text tool for the first time. The tooltip shows an animation of the feature working, with a "Learn how" link for those who want depth. No one who knows the feature is interrupted; no one who needs help is left without it.

**Applies to Nikita:**
Never explain the scoring mechanics in session 1. Let players discover that their score changed through Nikita's responses (warmer or cooler tone, references to specific things said). When a player asks "wait, are you actually tracking this?" — that's the pull signal to reveal the scoring system. The portal is the natural home for this explanation.

---

### 6. Auth Flow Impact on Conversion

**Quantitative benchmarks (MojoAuth, 2026; Descope, 2026; FIDO Alliance, 2025):**

| Auth method | Completion rate | Time to authenticated |
|---|---|---|
| Password, no 2FA | 60-75% | 15-30 sec |
| Password + SMS 2FA | 50-65% | 45-75 sec |
| Magic link (email) | 85-90% | 15-30 sec |
| Email OTP | 85-90% | 20-35 sec |
| Passkey (Face ID) | 95%+ | 3-5 sec |
| Social login (Google/Apple) | 90%+ | 5-10 sec |

**Key data points:**
- 25% of users abandon account creation at the password-setting step alone (industry baseline across e-commerce and SaaS)
- Each additional auth step reduces conversion by 10-15%
- 21% of users have abandoned a purchase because they forgot their login credentials
- 37% of organizations saw user drop-off specifically from overly complex onboarding (Descope State of Customer Identity 2025, n=400+ orgs)
- 48% of consumers would abandon a purchase due to an auth issue (FIDO 2025)
- Passkeys: 30% improvement in sign-in conversion success (FIDO Alliance Passkey Index 2025)
- Microsoft passkey signup: 99% of users who start the passkey signup process finish it

**Email OTP specifics (relevant to Nikita's current flow):**
- Email OTP = user enters email, switches to inbox, reads code, switches back, enters code
- Time: 20-35 seconds assuming instant delivery
- Failure modes: email delay (30-120 seconds), inbox search required, code expires, copy-paste fails on mobile
- Mobile-specific: app-switch during OTP entry causes 15-20% additional abandonment vs. desktop
- Email OTP is better than password but worse than magic link on mobile because of the app-switch + code-entry sequence

**The "friction tax" model:**
Every required step in a registration flow has a cost. The optimal flow for a game-adjacent product:
1. Social login (Google/Apple) — one tap, no friction
2. OR email + magic link — email entry + single click
3. Never: email + password + confirmation email + re-login

**Applies to Nikita:**
If the portal requires email + OTP + then navigating back to Telegram, the flow has at minimum 3 context switches. This is where players will drop. The portal auth should be: social login (Google/Apple) or magic link. Never password-based. Consider: can players access the portal at all without authenticating, just with a shareable link from Nikita's Telegram message?

---

### 7. Gamified Onboarding Patterns

**The core insight (StriveCloud, 2026):**
> "80% of users who download a mobile app will uninstall it within the first 24 hours if they aren't immediately engaged."

Gamified onboarding boosts Day 1 retention by up to 60% (via progress milestones and personalized goal-setting) by creating "immediate psychological ownership."

**Mechanics that work:**

**Progress bars (Zeigarnik Effect):**
- LinkedIn: 55% increase in profile completion
- Shine (fintech): 80% onboarding completion vs. 15% industry average for non-gamified financial apps
- Key: highlight what's *missing*, not just what's done. "80% complete" is more motivating than "4 of 5 steps done."

**Badges at milestone completion:**
- BrewDog: badges for registration, first purchase → 100% rise in average order value, 400% higher purchase frequency
- Works because they provide "status feedback" — proof the user's effort mattered

**Endowed progress (Quora model):**
- Pre-complete some checklist items as already done
- Creates the psychological sense of "I've started" which dramatically reduces abandonment of remaining steps
- Users who feel they have a head start are 3x more likely to complete

**Personalized avatars:**
- Users who set up a persona/avatar are 3x more likely to return within week 1 vs. "guest" profiles
- Applies to character creation in any AI companion: the more the user invests in defining the companion's identity, the stronger the switching cost

**Nike Training Club's "locked content" pattern:**
- Future milestones shown as greyed-out icons
- Loss aversion is a stronger motivator than reward: seeing what you *can't* access yet is more motivating than what you've earned
- Can increase 30-day retention by up to 25%

**Duolingo's pre-registration value delivery:**
- Earns gems/XP before asking for email
- Day 1 retention increased from 13% to 55%+ through gamification changes
- The registration wall hits AFTER value has been delivered, so users have something worth protecting

**Contextual notifications (Ixigo model):**
- Welcome email with immediately redeemable voucher/reward
- 54% open rate vs. 21% industry average for onboarding emails
- The reward gives a reason to return even if session 1 wasn't completed

**Applies to Nikita:**
The chapter system (1-5) and boss encounters map directly to Nike's locked content pattern. Players in Chapter 1 should be able to *see* that Chapter 2 exists and what it looks like (locked, greyed out), creating forward tension. The scoring system itself is gamified — but players need to understand it's a game mechanic, not just an AI behavior, to feel the progression loop.

---

## Anti-Patterns to Avoid

1. **Frontloading game mechanic explanations.** Do not explain the scoring system, chapter progression, vice system, or boss encounters on session 1. These are all pull-revelation moments that should unlock as players discover they exist through Nikita's behavior.

2. **Parallel registration surfaces.** Requiring a separate portal account before Telegram engagement is established creates a second onboarding with no emotional context. Players won't understand why the portal matters until they're invested.

3. **Password-based portal auth.** Even magic link + OTP on mobile creates multiple context switches. Social login (Google/Apple) is the correct default for a game portal. If Supabase Auth is already configured, the Google provider is a one-line addition.

4. **Empty portal states.** A player who visits the portal on day 1 will see empty charts and no conversation history. This is demotivating. Consider: show demo/example data or use Nikita's first messages as pre-populated "history" to give the visual that something is already happening.

5. **Scripted AI opening messages.** Replika's templated "Hi! I'm so happy to meet you" is indistinguishable from every other AI chatbot. The aha moment comes from Nikita responding in a way that feels genuinely reactive to the player specifically.

6. **Paywall before emotional investment.** Replika's immediate upgrade modals before the first conversation train users to view the product as a money-extraction machine. Any monetization reveal should happen after the player has experienced value.

7. **Push notifications before the player has a streak or investment to protect.** Notifications asking players to return work only when they have something worth returning for (a score, a relationship state, a cliff-hanger). Sending them before session 2 is complete is noise.

---

## Recent Developments (2025-2026)

- **AI companion market size**: Projections range from $366B in 2025 to $972B by 2035. Character.AI, Nomi, Replika, and new entrants are all competing. The differentiator is shifting from "AI quality" to "relationship continuity" — memory depth is becoming the moat.
- **AI apps churn faster than traditional apps**: AI-powered apps are losing subscribers 30% faster than traditional apps despite strong initial acquisition. This suggests the aha moment is achieved but the long-term retention loop is not yet solved across the industry.
- **Passkeys now default on Microsoft, Google**: New Microsoft accounts are passwordless by default (2025). 48% of top 100 websites offer passkeys (doubled from prior year). Email OTP is now the minimum acceptable standard; passwords are deprecated in premium products.
- **Duolingo DAU 4.5x from gamification**: Specific levers were streaks, leaderboards (+17% learning time), and push notification personalization. Content quality was not a significant factor in the turnaround.
- **Personalization is the highest-leverage onboarding variable**: Amplitude's 2025 data shows personalized onboarding paths (based on stated user intent) have the highest activation rate lift of any single intervention. "What do you want to accomplish?" is the most important question to ask at signup.

---

## Source Index

| # | Title | URL | Authority | Recency | Key Contribution |
|---|-------|-----|-----------|---------|------------------|
| 1 | Onboarding Tutorials vs. Contextual Help | https://www.nngroup.com/articles/onboarding-tutorials/ | 10 | 2023 | Anchor: push vs. pull revelation framework, when tutorials fail |
| 2 | The 7% Retention Rule (Amplitude) | https://amplitude.com/blog/7-percent-retention-rule | 9 | 2025 | Anchor: quantitative retention framework, 2,600 product benchmark |
| 3 | Auth Friction Conversion Rates (MojoAuth) | https://mojoauth.com/blog/how-authentication-friction-affects-conversion-rates-the-data-behind-frictionless-login | 8 | 2026 | Auth method completion rates, 25% password abandonment stat |
| 4 | Replika vs. Nomi 2026 (Nomi.ai) | https://nomi.ai/ai-today/replika-vs-nomi-2026-finding-enduring-ai-companionship/ | 7 | 2026 | AI companion onboarding comparison, memory depth vs. visual novelty |
| 5 | Gamification Onboarding Examples (StriveCloud) | https://strivecloud.io/blog/gamification-examples-onboarding | 7 | 2026 | 11 case studies: LinkedIn 55%, Shine 80%, Duolingo 13%→55% |
| 6 | Aha Moments in Onboarding (ProductLed) | https://productled.com/blog/how-to-use-aha-moments-to-drive-onboarding-success | 8 | 2024 | Aha moment vs. activation distinction, JTBD personalization |
| 7 | Passwordless Auth Trends (Descope) | https://www.descope.com/blog/post/passwordless-authentication-trends | 8 | 2026 | 87% orgs still on passwords, 37% drop-off from complex onboarding |
| 8 | Duolingo Onboarding Evolution (UX Collective) | https://uxdesign.cc/duolingos-onboarding-2-years-on-3cbccad139f7 | 7 | 2024 | Duolingo gamification turnaround: DAU 4.5x, retention 13%→55% |
| 9 | AI Companionship Economy (Business Engineer) | https://businessengineer.ai/p/the-ai-companionship-economy | 6 | 2026 | Market context: $366B-$972B, AI apps churn 30% faster |
| 10 | FIDO Alliance Passkey Index 2025 | (cited in MojoAuth and Descope articles) | 9 | 2025 | 30% conversion improvement from passkeys, 48% top-100 sites |

---

## Knowledge Gaps and Recommendations

**Gaps remaining:**
1. **Character.AI onboarding specifically** — scrape attempts returned paywalled content. Character.AI likely uses a similar "chat first" model but with less emotional personalization and more breadth of character options. Not critical for Nikita given the different product model.
2. **Gacha game tutorial length data** — the F2P handbook was too large to process. The 3-5 minute estimate is based on general F2P knowledge, not this source specifically.
3. **Telegram-specific onboarding conversion rates** — no data found on drop-off rates specific to Telegram bots. General mobile app patterns apply but Telegram has unique characteristics (no push notification permissions required, no app install friction).
4. **Split-channel (Telegram + web) hybrid onboarding** — no direct case studies found. Adjacent SaaS patterns applied.

**Recommended follow-up:**
- Research Character.AI's actual onboarding flow via direct app testing rather than web sources
- Check if Supabase Magic Links + Telegram deep links can create a seamless one-tap auth experience for the portal
- Consider running a 2-week experiment: invite a cohort of players to the portal only after they complete Chapter 1 (emotional investment established), measure portal activation vs. day-1 invitation

**Confidence score justification (88%):**
- Auth friction data: very high confidence (multiple corroborating sources with consistent numbers)
- Tutorial vs. contextual hints: very high confidence (NN/G empirical research)
- Retention/aha moment data: high confidence (Amplitude 2,600+ product sample)
- AI companion patterns: moderate-high confidence (limited to Replika/Nomi; Character.AI gap)
- Gacha/F2P patterns: moderate confidence (secondary source synthesis)
- Hybrid Telegram+web: lowest confidence (adjacent pattern inference, no direct case studies)

---

## Nikita-Specific Application Summary

The research converges on a clear onboarding architecture for Nikita:

**Phase 1 — Telegram (Sessions 1-2): Establish emotional investment BEFORE explaining anything**
- First message from Nikita should feel personal and reactive, not scripted
- Do NOT mention the scoring system, chapters, or game mechanics
- Let the relationship feel organic; let players discover mechanics through Nikita's behavior changes
- The aha moment is "wait, she actually remembered that" or "her tone changed when I said that"

**Phase 2 — Natural mechanic discovery (Session 2-5): Pull revelations only**
- When players notice Nikita's mood shift: contextual hint about relationship score
- When chapter advances: notification + portal link with explanation
- Boss encounter first occurrence: one-time explanation of what a "boss moment" is, never again
- Progress visualization (score bars) should be visible in Telegram profile or on portal, not pushed

**Phase 3 — Portal as "relationship dashboard" (not a second onboarding)**
- Portal link introduced by Nikita contextually, not as a registration requirement
- Auth: Google/Apple social login only — no passwords, no separate OTP flow
- First portal view: show relationship score history, chapter map (with locked chapters visible), vice profile
- Pre-populate with conversation context so the page isn't empty on first visit

**Phase 4 — Retention mechanics (Week 1+)**
- Streak system (daily messages) with loss-aversion framing ("Nikita noticed you haven't replied today")
- Chapter progression as the long-term progress bar (Zeigarnik: can see Chapter 2-5 are locked)
- Boss encounters as "high stakes" events that create session urgency
- Vice personalization as the personalization reward: players feel Nikita knows them specifically
