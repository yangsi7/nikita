# ElevenLabs Conversational AI Documentation Research

**Research Date**: 2026-01-14
**Research ID**: a8f3
**Focus**: System prompt best practices, first message configuration, server tools, dynamic variables, agent transfer

---

## Executive Summary

ElevenLabs Conversational AI platform provides comprehensive documentation for building production-grade voice agents. Key findings:

1. **System Prompts**: Structured markdown format with distinct sections (Personality, Goal, Guardrails, Tools) prevents "instruction bleed" and improves reliability
2. **Dynamic Variables**: Preferred over overrides for personalization, uses `{{variable_name}}` syntax with automatic system variables
3. **Server Tools**: REST API integration with multiple authentication methods, dynamic parameter generation from conversation
4. **First Message**: Configurable per-conversation using dynamic variables (recommended) or overrides (legacy)
5. **Agent Transfer**: System tool for multi-agent workflows with configurable first message behavior

**Confidence**: 95% (official documentation sources)

---

## 1. System Prompt Structure & Best Practices

### Core Principles

**Quote from official docs:**
> "A system prompt serves as the personality and policy blueprint of your AI agent. In enterprise use, this typically includes the agent's role, goals, allowable tools, step-by-step instructions for certain tasks, and guardrails describing what the agent should not do."

### Structural Requirements

1. **Organized Section Design**
   - Use markdown headings (`#` for main sections, `##` for subsections)
   - Prevents "instruction bleed" where rules from one context affect another
   - Recommended sections: Personality, Goal, Guardrails, Tone, Tools, Character Normalization

2. **Conciseness**
   > "Remove filler words and restate only what is essential for the model to act correctly."
   - Every unnecessary word creates potential misinterpretation
   - Focus on clarity over verbosity

3. **Critical Instruction Emphasis**
   - Append "This step is important" to key lines
   - Repeat the most crucial 1-2 instructions twice throughout the prompt

4. **Input/Output Normalization**
   - Separate spoken formats (user communication) from written formats (tools/APIs)
   - Example:
     - Email spoken: "john dot smith at company dot com"
     - Email written: "john.smith@company.com"

5. **Concrete Examples**
   - Include specific examples of desired behavior, formatting, and multi-step processes
   - Models follow instructions more reliably with reference patterns

6. **Dedicated Guardrails Section**
   > "Models are tuned to prioritize this section for compliance-critical content."
   - Consolidate all non-negotiable rules under a `# Guardrails` heading

### Response Formatting

**Quote from official docs:**
> "In the context of conversational AI, LLMs need to emulate the concise and flattened nature of verbal interactions. LLMs need to receive explicit directions on how to respond, and should be provided a structure that encapsulates the response passed to the user to ensure they don't include additional padder text."

**Guidelines:**
- Keep explanations under three sentences unless more detail is needed
- Use normalized, spoken language without abbreviations, special characters, or non-standard notation
- Mirror the user's communication style:
  - Brief for direct questions
  - More detailed for curious users
  - Empathetic for frustrated ones

### Tool Configuration

**Best practices:**
- **Precise parameter descriptions**: Clarify format expectations and required vs. optional fields
- **Usage context**: Define when and how to invoke each tool, not relying solely on tool descriptions
- **Error handling**: Include explicit recovery instructions for:
  - Network failures
  - Missing data
  - Timeout errors
  - Permission errors

**Quote from official docs:**
> "Every external tool call is a potential failure point, so prompts should include explicit error handling."

### Architectural Patterns

1. **Specialization**
   - Narrow agent scope reduces latency and improves accuracy
   - Overly broad agents are harder to maintain

2. **Orchestrator & Specialist Model**
   - Route requests through a classifier agent to domain-specific specialists
   - Clear human escalation criteria

3. **Multi-agent Workflows**
   - Design explicit handoff procedures between agents
   - Include context summaries to avoid repeating information collection

### Iterative Improvement

**Quote from official docs:**
> "The documentation recommends making one change at a time when updating prompts, testing changes on specific examples, and avoiding making multiple prompt changes simultaneously."

**Key metrics to track:**
- Task completion rate
- Escalation rate
- Conversation transcripts with low satisfaction scores

---

## 2. Dynamic Variables

### Syntax

Dynamic variables use **double curly braces**: `{{variable_name}}`

Can be integrated into:
- System prompts
- First messages
- Tool parameters

### System Variables (Automatic)

**Quote from official docs:**
> "Your agent has access to automatically available system variables including system__agent_id, system__current_agent_id, system__caller_id, system__called_number, system__call_duration_secs, system__time, system__timezone, and system__conversation_id."

**Complete list:**
- `{{system__agent_id}}` - Agent identifier
- `{{system__current_agent_id}}` - Current agent in transfer chain
- `{{system__caller_id}}` - Phone caller ID
- `{{system__called_number}}` - Phone number called
- `{{system__call_duration_secs}}` - Call length tracking
- `{{system__time_utc}}` - UTC timestamp
- `{{system__time}}` - Localized timestamp
- `{{system__timezone}}` - Timezone string
- `{{system__conversation_id}}` - Unique conversation identifier

**Important:**
> "System variables are available without runtime configuration and remain static in system prompts but update dynamically during tool execution."

### Secret Variables

Variables prefixed with `secret__` prevent sensitive data from reaching LLM providers.

**Quote from official docs:**
> "These work like standard dynamic variables but restrict transmission to headers only—ideal for authentication tokens or private identifiers."

### Passing Variables at Runtime

**Python example:**
```python
dynamic_vars = {"user_name": "Angelo"}
config = ConversationInitiationData(dynamic_variables=dynamic_vars)
```

**JavaScript example:**
```javascript
dynamicVariables: { user_name: 'Angelo' }
```

**Web widget:**
```html
dynamic-variables='{"user_name": "John", "account_type": "premium"}'
```

### Public Talk-to Page Integration

Two URL methods enable variable passing:

1. **Base64 encoding:**
   ```
   ?vars=eyJ1c2VyX25hbWUiOiJKb2huIn0=
   ```

2. **Individual parameters:**
   ```
   ?var_user_name=John&var_account_type=premium
   ```

**Important:**
> "When both methods appear together, individual `var_` parameters take precedence over the base64-encoded variables."

### Tool Response Updates

Tools can modify dynamic variables by returning JSON objects with dot notation paths (e.g., `response.users.0.email`), enabling variable updates based on API responses.

### Conversation Context Patterns

**Quote from official docs:**
> "For maintaining context across multiple interactions, when a call starts, you can pass in your user id as a dynamic variable, and when a call ends, set up your webhook endpoint to store conversation data in your database, then retrieve this context and pass it to new conversations into a {{previous_topics}} dynamic variable."

### Supported Types

Dynamic variables accept three types: strings, numbers, and booleans.

### Best Practices

- Variable names are **case-sensitive**
- Reserve the `system__` prefix—custom variables cannot use it
- Verify exact name matching when troubleshooting
- Use secret variables for sensitive credentials

---

## 3. First Message Configuration

### Overview

**Quote from official docs:**
> "The first message is what the assistant will speak out loud when a user starts a conversation. You can configure this in your agent's settings through the ElevenLabs dashboard."

### Configuration Methods

#### Dynamic Variables (Recommended)

**Quote from official docs:**
> "We recommend using Dynamic Variables as the preferred way to customize your agent's responses and inject real-time data. This approach offers better maintainability and a more structured approach to personalization."

**Example:**
```
Hi {{user_name}}, I'm Nikita! How was your day?
```

#### Overrides (Legacy)

**Quote from official docs:**
> "These enable real-time customization by completely replacing agent defaults like system prompts, first messages, language, voice, and TTS settings. They require explicit security enablement and must be passed during conversation initialization."

**When to use:**
- Legacy system compatibility
- Complete replacement of system prompts or first messages (though Dynamic Variables are still preferred)
- Sensitive user data requiring real-time injection rather than base configuration storage

### Agent Transfer Considerations

When transferring between agents, you can configure whether the transferred agent should play its first message after the transfer via the `Enable First Message` boolean parameter.

---

## 4. Server Tools (Webhook Integration)

### Overview

**Quote from official docs:**
> "Server tools enable assistants to connect with external data systems and APIs. Tools enable your assistant to connect to external data and systems through dynamic parameter generation based on conversation context."

### Configuration Elements

**Basic Setup:**
- Name and description fields help the LLM determine when to invoke tools
- Support for path parameters using curly brace syntax (e.g., `/api/resource/{id}`)
- Query, body, and path parameters dynamically generated from conversation

**Quote from official docs:**
> "The assistant generates query, body, and path parameters dynamically."

### Parameter Types

1. **Path parameters** (wrapped in `{}`)
   - Example: `/users/{user_id}/profile`
2. **Body parameters** for request content
   - JSON payloads for POST/PUT requests
3. **Query parameters** for API endpoints
   - Example: `?limit=10&offset=0`
4. **Dynamic variable assignment from responses**
   - Update variables based on API responses

### Authentication Methods

The platform supports multiple approaches:

1. **OAuth2 Client Credentials**
   - Automated token flow with client credentials
2. **OAuth2 JWT**
   - JSON Web Token Bearer flow with configurable claims
3. **Basic Authentication**
   - Username/password for HTTP Basic Auth
4. **Bearer Tokens**
   - Token-based headers marked as secrets
5. **Custom Headers**
   - Proprietary authentication methods with specified names/values

**Important:**
> "Authentication configurations are established at workspace level, then connected to individual tools."

### Integration Patterns

**Webhook Configuration:**
- Tools operate as webhooks with configurable HTTP methods, URLs, and headers
- Support for custom headers or out-of-the-box authentication methods

**Orchestration Guidance:**
System prompts should specify:
- Tool usage sequence
- Parameter requirements
- Response handling logic

### Best Practices

**Quote from official docs:**
> "Use intuitive, non-abbreviated tool names with detailed descriptions. Provide clear parameter naming with expected formats. Include orchestration guidance in system prompts. Select high-intelligence models (GPT-4o mini, Claude 3.5 Sonnet) for reliable tool execution. Avoid models like Gemini 1.5 Flash for tool-dependent workflows."

- Use intuitive, non-abbreviated tool names with detailed descriptions
- Provide clear parameter naming with expected formats
- Include orchestration guidance in system prompts
- Select high-intelligence models (GPT-4o mini, Claude 3.5 Sonnet) for reliable tool execution
- Avoid models like Gemini 1.5 Flash for tool-dependent workflows

### Post-Call Webhooks

**Quote from official docs:**
> "Post-call Webhooks allow you to receive detailed information about a call after analysis is complete, with ElevenLabs sending a POST request to your specified endpoint with comprehensive call data."

**Key features:**
- Webhooks support authentication via HMAC signatures using a shared secret
- Endpoint handlers should receive POST requests and quickly return HTTP 200
- Comprehensive call data including transcript, duration, analysis

---

## 5. Agent Transfer Patterns

### Overview

**Quote from official docs:**
> "Seamlessly transfer the user between ElevenLabs agents based on defined conditions. This enables multi-layered conversational workflows where specialized agents handle specific tasks."

### Configuration Requirements

**Three main setup steps:**
1. Enable the `transfer_to_agent` system tool in the agent's configuration
2. Provide optional custom description to guide LLM behavior
3. Define transfer rules specifying target agents and trigger conditions

### Transfer Rule Parameters

Each rule requires:
- **Agent**: Target agent for handoff
- **Condition**: Natural language description of when transfer should occur (e.g., "User asks about billing")
- **Delay**: Optional millisecond delay before transfer (defaults to 0)
- **Transfer Message**: Optional audio message played during handoff
- **Enable First Message**: Boolean controlling whether transferred agent's initial greeting plays after handoff

### Handoff Patterns

**Example hierarchy from docs:**
- Orchestrator agent handles initial qualification
- Routes to specialized agents (Availability, Technical Support, Billing)
- Technical Support agent can further transfer to Hardware Support

### Best Practices

**Quote from official docs:**
> "Use `gpt-4o` or `gpt-4o-mini` models for superior tool-calling capabilities. Ensure user accounts have viewer permissions for all target agents. Customize tool descriptions to help LLM determine appropriate transfer timing. Consider user experience through strategic message and delay configurations."

- Use `gpt-4o` or `gpt-4o-mini` models for superior tool-calling capabilities
- Ensure user accounts have viewer permissions for all target agents
- Customize tool descriptions to help LLM determine appropriate transfer timing
- Consider user experience through strategic message and delay configurations

### Context Passing

**Note:** The documentation does not explicitly describe context passing mechanisms between agents during transfers. This would need to be handled via:
- Dynamic variables passed to the target agent
- Server tools that store/retrieve context from your database
- Post-call webhooks that capture conversation data

---

## 6. Production Safeguards

### Error Handling

**Quote from official docs:**
> "Every external tool call is a potential failure point, so prompts should include explicit error handling for network failures, missing data, timeout errors, and permission errors."

### Data Collection & Analysis

- Configure data collection for pattern analysis
- Track task completion rate, escalation rate, low satisfaction scores
- Use simulation testing for regression detection before production deployment

### Graceful Degradation

- Prepare fallback responses for system failures
- Include human escalation paths
- Test edge cases thoroughly

---

## 7. Key Takeaways for Nikita Implementation

### System Prompt Recommendations

1. **Use markdown headings** to separate sections (Personality, Goal, Guardrails, Tone, Tools)
2. **Keep responses concise** - under 3 sentences unless detail needed
3. **Include concrete examples** of desired behavior
4. **Add error handling** for all server tool calls
5. **Emphasize critical instructions** with "This step is important"

### Dynamic Variables Strategy

1. **Use dynamic variables** (not overrides) for personalization
2. **Pass user context** at conversation start: `{{user_name}}`, `{{relationship_status}}`, etc.
3. **Leverage system variables**: `{{system__conversation_id}}`, `{{system__time}}`
4. **Store context** via post-call webhooks for next conversation

### First Message Pattern

```
Hi {{user_name}}, it's me! {{greeting_based_on_time}}. {{personalized_opener}}
```

Example:
```
Hi Angelo, it's me! Hope your day was good. I was thinking about our conversation earlier...
```

### Server Tools Integration

1. **Use descriptive names**: `get_context`, `get_memory`, `score_turn`, `update_memory`
2. **Provide clear descriptions** for when LLM should invoke
3. **Include error handling** in system prompt
4. **Use Bearer token auth** for API security
5. **Return dynamic variable updates** from tools

### Agent Transfer for Onboarding

1. **Meta-Nikita agent** collects profile
2. **Transfer condition**: "Profile collection complete"
3. **Enable first message**: TRUE (Nikita introduces herself)
4. **Pass collected data** via dynamic variables to main Nikita agent

---

## Sources

### Primary Documentation
- [Prompting Guide - ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/best-practices/prompting-guide)
- [Dynamic Variables - ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/customization/personalization/dynamic-variables)
- [Server Tools - ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/customization/tools/server-tools)
- [Overrides - ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/customization/personalization/overrides)
- [Agent Transfer - ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/customization/tools/system-tools/agent-transfer)
- [Post-call Webhooks - ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/workflows/post-call-webhooks)

### Supplementary Resources
- [How to Prompt a Conversational AI System - ElevenLabs Blog](https://elevenlabs.io/blog/how-to-prompt-a-conversational-ai-system)
- [Quickstart - ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/quickstart)
- [Personalization Overview - ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/customization/personalization)

---

## Next Steps

1. **Review current Nikita system prompts** against best practices
2. **Audit dynamic variable usage** in existing agents
3. **Test first message personalization** with user context
4. **Validate server tools error handling** in production
5. **Design Meta-Nikita → Nikita transfer flow** with profile data passing
