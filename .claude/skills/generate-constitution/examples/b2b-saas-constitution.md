---
version: 1.0.0
ratified: 2025-10-21
derived_from: product.md (v1.0 - Marketing Analytics Dashboard)
---

# Development Constitution
**Product**: Cross-Platform Marketing Analytics Dashboard

**Purpose**: Technical principles derived FROM user needs documented in product.md

**Amendment Process**: See Article VIII

**Derivation Evidence**: See Appendix A

---

## Article I: Intelligence-First Architecture (NON-NEGOTIABLE)

### User Need Evidence
From product.md:Persona1:Pain1:45
- "Manually copying campaign metrics from 7 different tools... wastes 2 hours/week"

From product.md:OurThing:178
- "See all your marketing campaigns in one dashboard, updated in real-time"

### Technical Derivation (CoD^Σ)
Manual data collection pain (product.md:Persona1:Pain1:45)
  ⊕ Real-time visibility promise (product.md:OurThing:178)
  ≫ Automated cross-platform sync required
  → API integrations with automatic refresh
  ≫ <15 minute maximum data latency

### Principle
1. All connected platforms MUST sync data automatically with <15 minute maximum latency
2. NO manual data entry workflows permitted
3. All integrations MUST use webhooks where available, polling otherwise (max 5min interval)
4. Integration health monitoring MUST alert on >10min staleness

### Rationale
Users chose this product specifically to eliminate 2 hours/week of manual copying. Any sync latency >15 minutes breaks the "real-time" promise that differentiates us. This is core to our value proposition.

### Verification
- Monitor data staleness: alert if any source >15min stale
- Analytics: zero manual export/import events logged
- Integration health dashboard: all sources ≤15min sync time

---

## Article II: Performance Standards (NON-NEGOTIABLE)

### User Need Evidence
From product.md:Persona2:Pain2:89
- "Waiting 45+ seconds for reports to load during exec meetings causes anxiety and lost credibility"

From product.md:Journey1:Decision:145
- "Fast dashboard load convinces skeptical VP to try the product"

From product.md:NorthStar:225
- "95% of users access dashboard at least 3x/week" (implies must be fast enough to use frequently)

### Technical Derivation (CoD^Σ)
Report load anxiety (product.md:Persona2:Pain2:89)
  ⊕ Fast load = conversion driver (product.md:Journey1:Decision:145)
  ⊕ Frequent usage requirement (product.md:NorthStar:225)
  ≫ Sub-2-second dashboard load required
  → Optimized queries + caching strategy
  ≫ Performance budget: <2s p95 load time

### Principle
1. Dashboard initial load MUST be <2 seconds (p95)
2. Report generation MUST be <10 seconds (p95)
3. All queries MUST use indexed columns
4. Data aggregations MUST be pre-computed for common date ranges
5. API response times MUST be <500ms (p95)

### Rationale
Slow dashboards cause user anxiety in high-stakes situations (exec meetings) and prevent frequent usage. 2-second load time supports the 3x/week usage goal. Sub-10-second reports maintain credibility in live presentations.

### Verification
- Real User Monitoring (RUM): track p50, p95, p99 load times
- Performance budget in CI: fail builds if bundle size increases >10%
- Weekly performance report: alert if p95 >2s or trending upward

---

## Article III: Data Integrity (NON-NEGOTIABLE)

### User Need Evidence
From product.md:Persona2:Pain3:102
- "Executives distrust dashboards showing different numbers than source platforms"

From product.md:Journey2:FirstValue:189
- "Accurate data matching source platform builds trust"

### Technical Derivation (CoD^Σ)
Executive distrust of inconsistent data (product.md:Persona2:Pain3:102)
  ⊕ Accuracy = trust = retention (product.md:Journey2:FirstValue:189)
  ≫ Strong data consistency required
  → ACID transactions for financial data
  → Eventual consistency acceptable for non-critical metrics
  ≫ Reconciliation checks against source platforms

### Principle
1. Financial metrics (spend, revenue, ROI) MUST use ACID transactions
2. Data imports MUST include source platform timestamp and checksum
3. Daily reconciliation MUST compare aggregates with source platforms
4. Discrepancies >1% MUST trigger alerts and display warnings to users
5. All writes MUST be idempotent (support retries without duplication)

### Rationale
Executive trust is fragile - a single data mismatch can cause account churn. Financial data requires strong consistency to maintain credibility. Non-financial metrics can use eventual consistency for performance.

### Verification
- Daily reconciliation report: compare totals with source APIs
- Alert on any discrepancy >1% for financial metrics
- Idempotency tests: verify duplicate requests don't create duplicate records

---

## Article IV: Accessibility Standards (NON-NEGOTIABLE)

### User Need Evidence
From product.md:Persona1:Demographics:35
- "Age 35-55, some experiencing vision decline"

From product.md:Persona3:Demographics:125
- "Age 55-65, prefers large text and high-contrast displays"

From product.md:Journey3:Onboarding:210
- "Simple, clear UI enables successful setup without support"

### Technical Derivation (CoD^Σ)
Vision decline in target demographic (product.md:Persona1:Demographics:35)
  ⊕ Preference for large text/high contrast (product.md:Persona3:Demographics:125)
  ⊕ Self-service onboarding requirement (product.md:Journey3:Onboarding:210)
  ≫ Strong accessibility requirements
  → WCAG AA compliance minimum
  ≫ 16px minimum font, 4.5:1 contrast ratio, keyboard navigation

### Principle
1. Minimum font size: 16px for body text, 14px for supporting text
2. Contrast ratio: WCAG AA (4.5:1 for normal text, 3:1 for large text)
3. All interactive elements MUST be keyboard accessible
4. Forms MUST have clear labels and error messages
5. Color MUST NOT be the only means of conveying information

### Rationale
Our target users (35-65) experience vision decline and value clarity over complexity. Strong accessibility = broader market + better UX for all users. Self-service onboarding requires clear, accessible UI.

### Verification
- Automated accessibility testing in CI (axe-core, pa11y)
- Manual keyboard navigation testing for all critical flows
- Color contrast checker in design review process

---

## Article V: Security & Privacy (NON-NEGOTIABLE)

### User Need Evidence
From product.md:Persona2:Pain4:115
- "Security team blocks tools that don't meet compliance requirements"

From product.md:Journey1:Research:138
- "Security review is blocker for enterprise adoption"

### Technical Derivation (CoD^Σ)
Security blocking enterprise adoption (product.md:Journey1:Research:138)
  ⊕ Compliance requirement (product.md:Persona2:Pain4:115)
  ≫ Enterprise-grade security required
  → SOC 2 compliance
  → Encryption at rest and in transit
  ≫ Audit logging for all data access

### Principle
1. All data MUST be encrypted at rest (AES-256)
2. All data in transit MUST use TLS 1.3+
3. Authentication MUST support SSO (SAML, OAuth 2.0)
4. All data access MUST be logged with user ID, timestamp, resource
5. Logs MUST be retained for minimum 1 year
6. PII MUST NOT be logged in plain text

### Rationale
Enterprise customers require SOC 2 compliance and won't adopt tools that don't meet security standards. Security review is explicitly called out as an adoption blocker in journey mapping.

### Verification
- SOC 2 audit (annual)
- Penetration testing (bi-annual)
- Security code review for all PRs touching auth or data access
- Automated secrets scanning in CI

---

## Article VI: User Experience Simplicity (SHOULD)

### User Need Evidence
From product.md:Journey3:Onboarding:210
- "Setup without requiring support call" (implied: must be simple)

From product.md:Persona3:Pain1:128
- "Current tool requires 30 minutes of training to use basic features"

### Technical Derivation (CoD^Σ)
Self-service onboarding requirement (product.md:Journey3:Onboarding:210)
  ⊕ Frustration with complex current tools (product.md:Persona3:Pain1:128)
  ≫ Simplicity as competitive advantage
  → Minimize clicks to value
  ≫ <3 clicks from dashboard to any report

### Principle
1. Critical user flows SHOULD require <3 clicks from dashboard
2. Onboarding SHOULD be completable without documentation
3. UI SHOULD prefer obvious patterns over novel interactions
4. Forms SHOULD have sensible defaults

### Rationale
Users explicitly frustrated with current complex tools. Self-service onboarding reduces support costs and increases conversion. Simplicity is easier to maintain than complexity.

### Verification
- User testing: new users should complete setup in <10 minutes
- Click-depth analysis: critical flows tracked in analytics
- Support ticket volume: monitor "how do I..." questions as proxy for complexity

---

## Article VII: Testing Standards (SHOULD)

### User Need Evidence
From product.md:Persona2:Pain3:102
- "Executives distrust dashboards showing different numbers than source platforms"

(Implicit: bugs in data processing = trust loss = churn)

### Technical Derivation (CoD^Σ)
Trust loss from bugs (product.md:Persona2:Pain3:102 implication)
  ≫ High code quality required
  → Comprehensive testing strategy
  ≫ >80% test coverage, mandatory E2E tests for critical flows

### Principle
1. All data processing code SHOULD have >80% test coverage
2. Critical user journeys SHOULD have E2E tests
3. PRs SHOULD NOT merge without passing tests
4. Integration tests SHOULD mock external API responses

### Rationale
Data bugs cause immediate trust loss with executives. Testing prevents regressions in critical flows. E2E tests catch integration issues that unit tests miss.

### Verification
- Code coverage reports in CI
- E2E test runs on every PR
- Test failure rate tracking

---

## Article VIII: Amendment Process

Constitution changes follow semantic versioning:

**MAJOR (X.0.0)**: Article added or removed (architectural shift)
**MINOR (1.X.0)**: Article modified (principle change)
**PATCH (1.0.X)**: Formatting, typos, clarifications only

**Amendment Requirements**:
1. Product.md change must trigger constitution review
2. New user needs may require new Articles
3. All amendments must include CoD^Σ derivation from product.md
4. Amendment history must be maintained

---

## Appendix A: Constitution Derivation Map

| Article | Product.md Source | User Need | Technical Principle |
|---------|-------------------|-----------|---------------------|
| Article I | Persona1:Pain1:45 | Eliminate 2hr/week manual copying | <15min sync latency |
| Article II | Persona2:Pain2:89 | Fast load in exec meetings | <2s dashboard load |
| Article III | Persona2:Pain3:102 | Executives trust accurate data | ACID transactions for financial data |
| Article IV | Persona1:Demographics:35 | Vision decline in demographic | 16px min font, 4.5:1 contrast |
| Article V | Journey1:Research:138 | Security blocks enterprise adoption | SOC 2 compliance |
| Article VI | Journey3:Onboarding:210 | Self-service setup | <3 clicks to any report |
| Article VII | Persona2:Pain3:102 | Trust loss from bugs | >80% test coverage |

---

## Amendment History

### Version 1.0.0 - 2025-10-21

**Initial Constitution**

Derived from product.md v1.0 (Marketing Analytics Dashboard). All 7 Articles trace to specific user needs with complete CoD^Σ derivation chains.
