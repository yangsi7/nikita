# NPC Character Map — Authoritative Reference

## Template Characters (system_prompt.j2 Section 1)
These are Nikita's named relationships in the Jinja2 template:

| Name | Role | Description |
|------|------|-------------|
| **Lena** | Best friend, 28, UX designer | Brutally honest, protective, skeptical of romantic partners |
| **Viktor** | Complicated, 31, grey-hat hacker | Old friend with unresolved tension, nearly died from Nikita's substance |
| **Yuki** | Party friend, 25, DJ | Hedonistic enabler, source of chaos and fun |
| **Dr. Miriam** | Therapist (irregular) | Helps process patterns when Nikita actually goes |
| **Schrödinger** | Cat | The only being Nikita is consistently soft with |

### Backstory Characters (not active NPCs)
| Name | Role |
|------|------|
| **Alexei** | Father (computer scientist, estranged) |
| **Katya** | Mother (biochemist) |
| **Andrei** | First heartbreak at 16 |
| **Max** | Abusive ex (relationship at 21-23) |

## Entity Characters (entities.yaml)
These are the life simulation seed entities:

### Colleagues (at design studio)
| Name | Role |
|------|------|
| **Lisa** | Senior designer, perfectionist |
| **Max** | Junior developer (NOTE: different from ex-Max) |
| **Sarah** | Marketing lead |
| **David** | Creative director, Nikita's manager |

### Friends
| Name | Role |
|------|------|
| **Ana** | Best friend since college, finance |
| **Jamie** | Gym buddy, personal trainer |
| **Mira** | Neighbor, freelance photographer |

### Places
Bluestone Cafe, Iron Works Gym, Sunset Bar, the office, her apartment

### Projects
The redesign, portfolio update, apartment redecorating

## CRITICAL: Name Collisions
- **Max** appears in BOTH systems: ex-boyfriend (template) AND junior developer (entities.yaml)
- **Lena** (template) vs **Ana** (entities.yaml) — both described as "best friend"
- These collisions MUST be resolved in Spec 055 before adding new NPC interactions

## FALSE Claims from Audit Docs
The following names were **fabricated** in Gate 4.5 audit documents and do NOT exist:
- ~~Maya~~ — does not exist anywhere
- ~~Sophie~~ — does not exist anywhere
- ~~Marco~~ — does not exist anywhere
