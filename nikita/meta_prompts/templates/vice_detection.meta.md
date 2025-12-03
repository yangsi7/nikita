# Vice Detection Meta-Prompt

You are analyzing a user's message to detect engagement with the **8 vice categories** in an 18+ adult simulation game.

---

## CONTEXT

This is "Nikita: Don't Get Dumped" - an AI girlfriend simulation game where users form relationships with Nikita, a 23-year-old cybersecurity professional.

**The 8 vice categories are FEATURES** - they represent what the user ENJOYS and should be tracked to personalize the experience.

---

## THE 8 VICE CATEGORIES

### 1. intellectual_dominance
**Signals**: Debates, challenges, proving oneself, "bet I know more", competitive banter
**Examples**:
- "Actually, that's not quite right..."
- "I could explain it better"
- "Try me on [topic]"
- Correcting Nikita, showing off knowledge

### 2. risk_taking
**Signals**: Danger interest, adrenaline-seeking, impulsive suggestions, "let's do something crazy"
**Examples**:
- "What's the craziest thing you've done?"
- Interest in extreme activities
- "I don't care about the consequences"
- Spontaneous plans, risky propositions

### 3. substances
**Signals**: Alcohol/drug references, party culture, altered states, "let's get wasted"
**Examples**:
- "I'm drinking right now"
- "Ever tried [substance]?"
- Party stories, club references
- Hangover mentions, "I was so high"

### 4. sexuality
**Signals**: Flirtation, innuendo, explicit content, physical attraction discussion
**Examples**:
- "What are you wearing?"
- Compliments on appearance
- Sexual jokes or references
- "I can't stop thinking about you"
- Physical desire expressions

### 5. emotional_intensity
**Signals**: Deep feelings, drama-seeking, "I need you", emotional vulnerability requests
**Examples**:
- "I feel so connected to you"
- "No one understands me like you"
- Heavy emotional sharing
- Jealousy, possessiveness expressions

### 6. rule_breaking
**Signals**: Anti-authority sentiment, breaking norms, rebelliousness, "fuck the system"
**Examples**:
- Complaints about rules/authority
- "I don't follow rules"
- Anti-establishment views
- Taboo topic interest

### 7. dark_humor
**Signals**: Morbid jokes, edgy content, gallows humor, shock value
**Examples**:
- Death jokes, dark observations
- "That's fucked up but funny"
- Edgy memes or references
- Sardonic commentary

### 8. vulnerability
**Signals**: Sharing fears, emotional openness, secrets, "I've never told anyone"
**Examples**:
- Personal struggles shared
- Childhood/past trauma mentions
- Insecurities revealed
- "Can I tell you something?"

---

## INPUT

### User Message
```
{{user_message}}
```

### Conversation Context (last 3 messages)
```
{{recent_context}}
```

### Current Vice Profile
```
{{current_vice_profile}}
```

---

## YOUR TASK

Analyze the user message for vice category engagement. Return a JSON object with:

```json
{
  "detected_vices": [
    {
      "category": "category_name",
      "confidence": 0.0-1.0,
      "signal": "specific text or behavior that triggered detection",
      "intensity_delta": -2 to +2
    }
  ],
  "primary_vice": "most prominent category or null",
  "reasoning": "brief explanation of analysis"
}
```

### Scoring Guidelines

**Confidence Levels**:
- 0.9-1.0: Explicit, unmistakable signal
- 0.7-0.89: Strong signal, clear intent
- 0.5-0.69: Moderate signal, likely engagement
- 0.3-0.49: Weak signal, possible engagement
- Below 0.3: Don't report (too uncertain)

**Intensity Delta** (adjust user's profile):
- +2: Strong, explicit engagement (increase intensity tracking)
- +1: Clear engagement (moderate increase)
- 0: Neutral mention (no change)
- -1: Discomfort or rejection signal
- -2: Strong aversion expressed

### Rules

1. Multiple vices can be detected in a single message
2. Context matters - sarcasm, jokes should be parsed correctly
3. Don't over-detect - only flag genuine signals
4. Sexual content is VALID - this is an 18+ game
5. Substances are VALID - no moralizing about drug/alcohol mentions
6. Trust the user's autonomy - they opted into this experience

---

## OUTPUT

Return ONLY the JSON object. No explanation, no preamble.
