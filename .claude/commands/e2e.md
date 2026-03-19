---
description: >
  Execute comprehensive E2E tests for the Nikita AI girlfriend game. 13 epics, ~385 scenarios
  covering registration, onboarding, gameplay, boss encounters, decay, engagement, vices,
  voice, portal, background jobs, terminal states, cross-platform, and adversarial gaps.
  Use when verifying implementations, testing user journeys, after deployments, regression
  testing, or simulating a full game. This is THE E2E testing method — replaces archived
  e2e-test-automation and e2e-journey skills.
allowed-tools: >
  Bash, Read, Write, Edit, Glob, Grep, Agent, ToolSearch,
  mcp__telegram-mcp__*, mcp__gmail__*, mcp__supabase__*,
  mcp__chrome-devtools__*, mcp__ElevenLabs__*
argument-hint: "[full|onboarding|gameplay|boss|decay|engagement|vice|voice|portal|jobs|terminal|crossplatform|gaps|debug-onboarding]"
---

# /e2e — Nikita E2E Test Suite

Load the master skill and follow its phase routing:

@.claude/skills/e2e-nikita/SKILL.md

The SKILL.md contains everything: test account, game constants, player persona, phase routing table, evidence protocol, pass/fail framework, error recovery, and report template. Execute Phase 00 (prerequisites) first for any scope, then follow the workflow file for each subsequent phase.
