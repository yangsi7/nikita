# Nikita System Diagrams

Architecture and system diagrams for the Nikita: Don't Get Dumped AI girlfriend game.

## Tier 1 — Core Diagrams

| Diagram | Purpose | Audience | Systems Covered |
|---------|---------|----------|-----------------|
| [01-full-stack-architecture](01-full-stack-architecture.excalidraw) | 4-layer system overview (User, Compute, AI, Data) | All | All 14 subsystems |
| [02-conversation-pipeline](02-conversation-pipeline.excalidraw) | 11-stage async post-processing pipeline | Developers | Pipeline, Memory, Life Sim, Vice, Scoring |
| [03-prompt-assembly](03-prompt-assembly.excalidraw) | 12-input convergence into token-budgeted prompt | AI/ML Engineers | Context Engineering, Psyche, Memory, Prompts |
| [04-emotional-machinery](04-emotional-machinery.excalidraw) | 4D emotional state + life simulation + conflict | All | Emotional State, Life Sim, Conflict |
| [05-game-mechanics-loop](05-game-mechanics-loop.excalidraw) | 5 chapters, bosses, scoring formula, decay, engagement | All | Scoring, Chapters, Decay, Engagement |
| [06-user-journey-map](06-user-journey-map.excalidraw) | 3-platform 120-day timeline with personality evolution | Stakeholders | All platforms, Chapter behaviors |

## Tier 2 — Detailed Subsystem Diagrams

| Diagram | Purpose | Systems Covered |
|---------|---------|-----------------|
| [07-memory-knowledge](07-memory-knowledge.excalidraw) | pgVector memory with 3 fact types and 95% dedup | Memory, pgVector, Embeddings |
| [08-engagement-fsm](08-engagement-fsm.excalidraw) | 6-state engagement FSM with scoring multipliers | Engagement, Scoring |
| [09-vice-personalization](09-vice-personalization.excalidraw) | 8 vice categories with chapter-gated boundaries | Vice Detection, Personalization |
| [10-auth-bridge](10-auth-bridge.excalidraw) | Zero-click Telegram-to-Portal auth sequence | Auth, Telegram, Portal |
| [11-inner-world](11-inner-world.excalidraw) | Life sim + psyche agent + conflict = she's alive | Life Sim, Psyche, Conflict |

## Viewing

Open `.excalidraw` files at [excalidraw.com](https://excalidraw.com) or view the rendered `.png` files directly.

## Color Key

| Color | Meaning |
|-------|---------|
| Orange | User entry points, inputs, triggers |
| Blue | Backend services, pipeline stages |
| Purple | AI/LLM services, emotional state |
| Green | Outputs, data layer, success states |
| Red | Critical stages, failures, game over |
| Amber | Decisions, bosses, chapter thresholds |
| Dark | Code/data evidence artifacts |
