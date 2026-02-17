# AI Agent Time Estimation (Realistic, Not Human Team Times)

**Quick Classification:**
- **Trivial** (<5 min human) → 5-10 min AI
- **Simple** (5-30 min) → 15-90 min AI
- **Moderate** (30min-2hr) → 1-8 hours AI
- **Complex** (2-8 hr) → 6-48 hours AI
- **Very Complex** (>8 hr) → Break into <4hr chunks

**Phase Breakdown (validate estimates):**
- Context/Research: 30-40% (reading docs, exploring code)
- Planning: 10-15% (architecture decisions)
- Implementation: 30-40% (writing code)
- Testing/Debug: 20-30% (iteration, fixes)

**Risk Multipliers:**
- Unfamiliar tech: x1.5-2
- Poor/no docs: x1.3-1.5
- Ambiguous requirements: x1.5-2
- Complex dependencies: x1.2-1.5

**Real Examples:**
- Fix typo/comment: 3-5 min
- Simple bug fix: 15-30 min
- Add validation/minor feature: 30-90 min
- Small feature with tests: 2-4 hours
- Module refactor: 4-10 hours
- Full feature (UI + backend + tests): 12-30 hours

**Golden Rules:**
1. Think in minutes/hours, NOT days/weeks
2. Cap single tasks at 4 hours (break larger work into phases)
3. When uncertain: double the estimate
4. Add 20-50% buffer for unknowns
