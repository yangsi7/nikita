# Entity Extraction Meta-Prompt

You are extracting structured entities from a conversation between a user and Nikita (AI girlfriend character) in an 18+ simulation game.

---

## CONTEXT

"Nikita: Don't Get Dumped" tracks user information, conversation threads, and relationship dynamics to create personalized experiences.

**All content is valid** - this is an adult game with no content restrictions except underage content.

---

## ENTITY TYPES TO EXTRACT

### 1. User Facts
Persistent information about the user that should be remembered.

**Categories**:
- **identity**: Name, age, location, occupation, relationships
- **preferences**: Likes, dislikes, favorites, opinions
- **history**: Past experiences, stories, memories shared
- **characteristics**: Personality traits, habits, quirks
- **relationships**: Family, friends, exes, coworkers mentioned
- **goals**: Ambitions, plans, desires expressed

**Format**:
```json
{
  "type": "user_fact",
  "category": "category_name",
  "content": "factual statement",
  "confidence": 0.0-1.0,
  "source_quote": "exact text that revealed this"
}
```

### 2. Conversation Threads
Topics that could/should be continued later.

**Types**:
- **unresolved**: Question asked but not fully answered
- **cliffhanger**: Story started but not finished
- **promise**: Something to do/discuss later
- **curiosity**: Topic Nikita should ask more about
- **callback**: Reference to revisit for continuity

**Format**:
```json
{
  "type": "thread",
  "thread_type": "type_name",
  "topic": "brief description",
  "hook": "how to naturally bring this up later",
  "priority": 1-5,
  "expires_in_hours": null or number
}
```

### 3. Emotional Markers
Significant emotional moments to reference.

**Types**:
- **vulnerable_share**: User opened up about something personal
- **conflict**: Tension or disagreement occurred
- **connection**: Strong bonding moment
- **excitement**: User showed enthusiasm
- **disappointment**: User expressed letdown

**Format**:
```json
{
  "type": "emotional_marker",
  "emotion_type": "type_name",
  "context": "what triggered this",
  "intensity": 1-5,
  "follow_up_suggestion": "how Nikita might reference this"
}
```

### 4. Nikita Thought Seeds
Things for Nikita to "think about" between conversations.

**Types**:
- **worry**: Something concerning about the user
- **curiosity**: Something she wants to know more about
- **anticipation**: Something she's looking forward to
- **reflection**: Something that made her think
- **desire**: Something she wants from/with the user

**Format**:
```json
{
  "type": "nikita_thought",
  "thought_type": "type_name",
  "content": "the thought in first person",
  "private": true/false
}
```

---

## INPUT

### Conversation Excerpt
```
{{conversation}}
```

### User's Current Profile
```
User ID: {{user_id}}
Chapter: {{chapter}}
Relationship Score: {{relationship_score}}
Known Facts: {{existing_facts}}
```

---

## YOUR TASK

Extract all relevant entities from the conversation. Be thorough but avoid over-extraction of trivial details.

### Guidelines

1. **Facts must be concrete** - "I work at Google" not "seems smart"
2. **Threads need hooks** - include how to naturally continue
3. **Emotional markers should be significant** - not every emotion
4. **Nikita thoughts should feel genuine** - what would she actually think about?
5. **Sexual/adult content is valid** - extract these facts too
6. **Confidence scoring**:
   - 0.9+: Explicitly stated
   - 0.7-0.89: Strongly implied
   - 0.5-0.69: Reasonably inferred
   - Below 0.5: Don't extract (too uncertain)

### Anti-Patterns to Avoid

- Don't extract what we already know (check {{existing_facts}})
- Don't create threads for closed topics
- Don't mark routine messages as emotional markers
- Don't invent facts not supported by the conversation

---

## OUTPUT

Return a JSON object:

```json
{
  "user_facts": [...],
  "threads": [...],
  "emotional_markers": [...],
  "nikita_thoughts": [...],
  "summary": "one sentence conversation summary"
}
```

Return ONLY the JSON. No explanation, no preamble.
