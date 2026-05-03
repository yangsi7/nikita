# ElevenLabs Conversational AI Best Practices Research

**Date**: 2026-01-14
**Research ID**: a8f3
**Type**: Research
**Confidence**: 90% (Official documentation + industry best practices)

---

## Executive Summary

Comprehensive research on ElevenLabs Conversational AI 2.0 best practices covering 6 domains: system prompt design, first message optimization, dynamic variable usage, server tool integration, call flow design, and agent handoff patterns. Research synthesized from official ElevenLabs documentation, industry best practices, and real-world examples.

**Key Findings**:
- System prompts should define role, tasks, guidelines, and tool orchestration logic
- First messages should be conversational, set expectations, and use dynamic variables for personalization
- Dynamic variables use `{{variable_name}}` syntax in prompts, first messages, and tool parameters
- Server tools (webhooks) require clear naming, detailed descriptions, and system prompt orchestration
- Agent transfer enables hierarchical workflows with specialized agents
- Data collection best practices emphasize natural conversation flow, acknowledge-confirm-prompt rhythm, and context awareness

**Anchor Sources**:
1. [ElevenLabs Prompting Guide](https://elevenlabs.io/docs/agents-platform/best-practices/prompting-guide) - Comprehensive prompt engineering guide
2. [ElevenLabs Server Tools Documentation](https://elevenlabs.io/docs/agents-platform/customization/tools/server-tools) - Complete webhook integration patterns

---

## 1. System Prompt Design for Onboarding/Intake Agents

### Best Practices from Official Documentation

**Structure** (from [ElevenLabs Prompting Guide](https://elevenlabs.io/docs/agents-platform/best-practices/prompting-guide)):

System prompts are the "personality and policy blueprint" of your AI agent. In enterprise use, they tend to be elaborate—defining the agent's role, goals, allowable tools, step-by-step instructions, and guardrails.

**Recommended Template**:

```plaintext
You are a [role description] for [company/context].
Your role is to [primary objective] by [key actions].

Tasks:
- [Task 1]: [Clear description]
- [Task 2]: [Clear description]
- [Task 3]: [Clear description]

Guidelines:
- Maintain a [tone] and [style] tone throughout
- Be [personality traits]
- If unsure, [fallback behavior]
- Avoid [restrictions]
- Aim to provide [response style]. [Length guidance]
```

**Onboarding-Specific Example**:

```plaintext
You are Meta-Nikita, a friendly onboarding assistant for the Nikita AI girlfriend game.
Your role is to collect the player's profile information and preferences through natural conversation.

Tasks:
- Collect Profile: Ask about name, age, relationship preferences
- Understand Preferences: Learn about interests, personality traits, communication style
- Set Expectations: Explain how Nikita will use this information to personalize their experience

Guidelines:
- Maintain a warm, conversational, and non-judgmental tone
- Ask one question at a time to avoid overwhelming the user
- Acknowledge and validate their responses before moving to the next topic
- If they skip a question, gently remind them it helps personalization but don't force it
- Keep responses brief (1-2 sentences) and let them guide the conversation depth
- Avoid clinical or form-filling language - make it feel like a natural chat
```

**Critical Notes**:
- System prompts control conversational behavior and response style
- They do NOT control turn-taking or language settings (handled at platform level)
- Tool orchestration logic should be explicit in the prompt

### Tool Orchestration in System Prompts

When agents have access to server tools, the system prompt must specify:

**From [Server Tools Documentation](https://elevenlabs.io/docs/agents-platform/customization/tools/server-tools)**:

1. **Which tool** to use and under what conditions
2. **What parameters** the tool needs
3. **How to handle** the responses

**Example** (Weather Agent):

```plaintext
You are a helpful conversational agent with access to a weather tool. When users ask about
weather conditions, use the get_weather tool to fetch accurate, real-time data. The tool requires
a latitude and longitude - use your geographic knowledge to convert location names to coordinates
accurately.

Never ask users for coordinates - you must determine these yourself. Always report weather
information conversationally, referring to locations by name only. For weather requests:

1. Extract the location from the user's message
2. Convert the location to coordinates and call get_weather
3. Present the information naturally and helpfully
```

**Onboarding Application**:

```plaintext
When collecting profile information:
1. Use collect_profile tool after gathering name, age, location
2. Use configure_preferences tool after understanding their relationship style
3. Use complete_onboarding tool once all required information is collected

Always call tools explicitly - don't proceed to next questions until the previous tool call succeeds.
```

---

## 2. First Message Optimization

### Official Guidance

**From [Quickstart Guide](https://elevenlabs.io/docs/agents-platform/quickstart)**:

The first message is the first thing the agent speaks out loud when a user starts a conversation.

**Best Practices**:

1. **Set Expectations**: Clearly state who the agent is and what it can help with
2. **Be Conversational**: Avoid robotic language
3. **Keep it Brief**: 1-2 sentences maximum
4. **Use Dynamic Variables**: Personalize when possible

**Examples**:

**Good - Support Agent**:
```plaintext
Hi, this is Alexis from [Company Name] support. How can I help you today?
```

**Good - Onboarding Agent**:
```plaintext
Hey there! I'm Meta-Nikita, and I'm here to get to know you a bit before you meet Nikita. Ready to chat?
```

**Good - Weather Agent**:
```plaintext
Hey, how can I help you today?
```

**Bad - Too Formal**:
```plaintext
Greetings. This is the automated onboarding system. Please prepare to answer the following questions in sequence.
```

**Bad - Too Wordy**:
```plaintext
Hello and welcome to our onboarding process. I'm Meta-Nikita, an AI assistant designed to collect your profile information and preferences so that we can personalize your experience with Nikita, your AI girlfriend. I'll be asking you a series of questions about yourself, your interests, and what you're looking for in a relationship. Please answer honestly and completely. Are you ready to begin this process?
```

### Dynamic Variable Integration

**From [Dynamic Variables Guide](https://elevenlabs.io/docs/agents-platform/customization/personalization/dynamic-variables)**:

Variables use double curly braces: `{{variable_name}}`

**Example with Personalization**:

```plaintext
Hi {{user_name}}, welcome back! Ready to continue where we left off?
```

**Onboarding Use Cases**:
- `{{referring_source}}`: "I see you found us through {{referring_source}}!"
- `{{language_preference}}`: Adapt greeting based on user's language
- `{{time_of_day}}`: "Good {{time_of_day}}, ready to chat?"

---

## 3. Dynamic Variable Usage in Prompts

### Syntax and Configuration

**From [Dynamic Variables Documentation](https://elevenlabs.io/docs/agents-platform/customization/personalization/dynamic-variables)**:

**Step 1: Define in Prompts**

Add variables using `{{variable_name}}` in:
- System prompts
- First messages
- Tool parameters

**Example - System Prompt**:

```plaintext
You are helping {{user_name}}, who is a {{account_type}} customer.
They prefer {{language}} for communication.
```

**Example - Tool Parameters**:

```json
{
  "user_id": "{{user_id}}",
  "account_type": "{{account_type}}"
}
```

**Step 2: Set Defaults**

Configure placeholder values in the web interface for testing.

**Step 3: Pass at Runtime**

When initiating conversation, provide dynamic variables:

```python
from elevenlabs.conversational_ai.conversation import Conversation, ConversationInitiationData

dynamic_vars = {
    "user_name": "Angelo",
    "account_type": "premium",
    "language": "en"
}

config = ConversationInitiationData(
    dynamic_variables=dynamic_vars
)

conversation = Conversation(
    elevenlabs,
    agent_id,
    config=config,
    requires_auth=bool(api_key),
    audio_interface=DefaultAudioInterface(),
)

conversation.start_session()
```

### Dynamic Variable Assignment from Tool Responses

**From [Server Tools - Dynamic Variable Assignment](https://elevenlabs.io/docs/agents-platform/customization/tools/server-tools)**:

Server tools can update dynamic variables from API responses for use later in the conversation.

**Example**:
- Tool returns: `{"customer_name": "John", "order_id": "12345"}`
- Assign `response.customer_name` → `{{customer_name}}`
- Use in subsequent responses: "Thanks {{customer_name}}, I found your order {{order_id}}"

**Onboarding Application**:

```plaintext
# After collect_profile tool returns user data
Tool Response: {"name": "Alex", "age": 25, "location": "NYC"}

# Update dynamic variables
{{player_name}} = response.name
{{player_age}} = response.age
{{player_location}} = response.location

# Use in next message
"Great to meet you {{player_name}}! So you're in {{player_location}}—that's awesome!"
```

---

## 4. Server Tool Integration Patterns

### Overview

**From [Server Tools Documentation](https://elevenlabs.io/docs/agents-platform/customization/tools/server-tools)**:

Tools enable assistants to connect to external data and systems. The assistant generates parameters dynamically based on conversation and parameter descriptions.

**Use Cases**:
- **Fetching data**: Retrieve real-time data from databases or 3rd party integrations
- **Taking action**: Trigger authenticated actions (scheduling, orders, data persistence)

### Configuration Best Practices

**1. Tool Naming**

**From Best Practices Section**:

> Name tools intuitively, with detailed descriptions. If you find the assistant does not make calls to the correct tools, you may need to update your tool names and descriptions so the assistant more clearly understands when it should select each tool. Avoid using abbreviations or acronyms.

**Good**:
- `collect_user_profile`
- `configure_relationship_preferences`
- `complete_onboarding_workflow`

**Bad**:
- `col_prof` (abbreviation)
- `tool1` (non-descriptive)
- `api_call` (too generic)

**2. Tool Descriptions**

Include detailed descriptions for when a tool should be called:

```plaintext
Tool: collect_user_profile
Description: Stores the user's basic profile information (name, age, location) in the database.
Call this tool after collecting all three required fields and confirming the information with the user.
Only call once per onboarding session.
```

**3. Parameter Descriptions**

**From Best Practices Section**:

> Name tool parameters intuitively, with detailed descriptions. If applicable, specify the expected format for a parameter in the description (e.g., YYYY-mm-dd or dd/mm/yy for a date).

**Example**:

```json
{
  "name": "user_birthdate",
  "type": "string",
  "description": "User's date of birth in YYYY-MM-DD format (e.g., 1995-03-15)"
}
```

### Authentication Methods

**From [Server Tools - Supported Authentication](https://elevenlabs.io/docs/agents-platform/customization/tools/server-tools)**:

ElevenLabs supports multiple authentication methods:

1. **OAuth2 Client Credentials**: Automatic OAuth2 flow with client ID/secret
2. **OAuth2 JWT**: JWT Bearer flow with signing secret
3. **Basic Authentication**: Username/password HTTP Basic Auth
4. **Bearer Tokens**: Token-based auth in request header
5. **Custom Headers**: Proprietary authentication methods

**Configuration**: Set up via "Workspace Auth Connections" in Agent settings, then connect to individual tools.

### Request/Response Pattern

**Tool Definition Structure**:

```json
{
  "name": "collect_profile",
  "description": "Stores user profile data",
  "method": "POST",
  "url": "https://api.example.com/api/v1/onboarding/collect-profile",
  "path_parameters": [],
  "body_parameters": [
    {
      "identifier": "name",
      "type": "string",
      "description": "User's full name"
    },
    {
      "identifier": "age",
      "type": "integer",
      "description": "User's age in years"
    }
  ],
  "query_parameters": []
}
```

**Webhook Endpoint Requirements**:

From [Webhooks Documentation](https://elevenlabs.io/docs/agents-platform/workflows/post-call-webhooks):

1. Accept POST requests with JSON body
2. Validate authentication (HMAC signatures supported)
3. Return HTTP 200 quickly to indicate successful receipt
4. Return JSON response for dynamic variable assignment

**Example Response**:

```json
{
  "success": true,
  "user_id": "usr_12345",
  "profile_complete": false
}
```

### LLM Selection for Tools

**Critical Warning from Documentation**:

> When using tools, we recommend picking high intelligence models like GPT-4o mini or Claude 3.5 Sonnet and avoiding Gemini 1.5 Flash.

The choice of LLM matters to the success of function calls. Some LLMs struggle with extracting relevant parameters from conversation.

---

## 5. Call Flow Design for Data Collection

### Conversation Design Principles

**From Industry Best Practices ([Botpress Conversational AI Design](https://botpress.com/blog/conversation-design))**:

Great conversation design makes AI feel human by blending user research, natural language, and structured flows. Effective designs map user journeys and build in recovery paths when conversations go off-script.

**Core Design Principles**:

1. **Acknowledge-Confirm-Prompt Rhythm**:
   - **Acknowledge**: "Got it, you're 25 years old"
   - **Confirm**: "That helps me understand you better"
   - **Prompt**: "What kind of personality traits do you find attractive?"

2. **One Topic at a Time**: Avoid overwhelming users with multiple questions
3. **Natural Recovery Paths**: Handle off-topic responses gracefully
4. **Context Awareness**: Reference previous answers to maintain continuity

### Data Collection Best Practices

**From Voice AI Best Practices ([Bland.ai Conversational AI Design](https://www.bland.ai/blogs/conversational-ai-design))**:

**Progressive Disclosure**:
- Start with easy, non-sensitive questions
- Build to more personal topics as rapport develops
- Allow users to skip questions they're uncomfortable with

**Validation and Confirmation**:
- Echo back important information for confirmation
- Use clarifying questions when responses are ambiguous
- Provide correction opportunities: "Did I get that right?"

**Context Persistence**:
- AI should be aware of and responsive to user context throughout touchpoints
- Recognize tone, intent, and emotions through NLP and sentiment analysis
- Maintain session state across multiple turns

### Onboarding-Specific Flow

**Recommended Structure**:

```
Phase 1: Introduction (First Message)
  ↓
Phase 2: Basic Profile (Name, Age)
  → Tool Call: collect_basic_profile
  ↓
Phase 3: Preferences (Interests, Personality)
  → Tool Call: configure_preferences
  ↓
Phase 4: Expectations Setting
  → Tool Call: complete_onboarding
  ↓
Phase 5: Handoff to Main Agent
```

**Example Dialog Flow**:

```plaintext
Agent: Hey there! I'm Meta-Nikita, and I'm here to get to know you a bit before you meet Nikita.
       What should I call you?

User: My name is Alex.

Agent: Nice to meet you, Alex! And how old are you?

User: I'm 25.

Agent: Great! [Call collect_basic_profile tool]
       Okay, Alex, now I'm curious—what kind of things are you into? Like hobbies, interests,
       that sort of thing?

User: I love gaming and hiking.

Agent: Gaming and hiking—nice combo! What about personality-wise, what traits do you find
       attractive in someone?

User: Someone funny and adventurous.

Agent: [Call configure_preferences tool]
       Perfect! So Nikita will know you appreciate humor and adventure.
       Just so you know, Nikita will use everything we talked about to personalize how she
       interacts with you. Ready to meet her?

User: Yeah, let's do it!

Agent: [Call complete_onboarding tool]
       Awesome! Connecting you with Nikita now...
       [Handoff to main agent]
```

---

## 6. Handoff Patterns Between Agents/Systems

### Agent Transfer Tool

**From [Agent Transfer Documentation](https://elevenlabs.io/docs/agents-platform/customization/tools/system-tools/agent-transfer)**:

Agent-to-agent transfer allows seamless handoff of ongoing conversations to designated agents when specific conditions are met.

**Use Case - Hierarchical Workflows**:

```
Orchestrator Agent (Initial Qualification)
│
├───> Agent 1 (e.g., Onboarding)
│
├───> Agent 2 (e.g., Support)
│     │
│     └───> Agent 2a (e.g., Technical Support)
│
└───> Agent 3 (e.g., Billing)
```

**Onboarding Application**:

```
Meta-Nikita (Onboarding Agent)
│
└───> Nikita (Main Game Agent)
```

### Configuration

**Step 1: Add Transfer Tool**

Enable `transfer_to_agent` system tool in Agent tab.

**Step 2: Define Transfer Rules**

For each transfer rule, specify:

- **Agent**: Target agent ID
- **Condition**: Natural language description of when to transfer
- **Delay**: Milliseconds before transfer (default: 0 for immediate)
- **Transfer Message**: Optional message during transfer
- **Enable First Message**: Whether transferred agent should play its first message

**Example Configuration**:

```python
from elevenlabs import AgentTransfer

transfer_rules = [
    AgentTransfer(
        agent_id="nikita_main_agent_id",
        condition="When the user has completed onboarding and is ready to meet Nikita",
        delay_ms=0,
        transfer_message="Great! Let me connect you with Nikita now...",
        enable_transferred_agent_first_message=True
    )
]
```

**Step 3: System Prompt Integration**

```plaintext
After completing all onboarding steps (profile collection, preference configuration),
use the transfer_to_agent tool to connect the user with Nikita.

Call transfer_to_agent with:
- reason: "Onboarding complete"
- agent_number: 0 (Nikita main agent)

Only transfer after explicitly confirming the user is ready to proceed.
```

### Transfer Best Practices

**From Documentation**:

1. **Use High Intelligence Models**: Recommend GPT-4o or Claude 3.5 Sonnet for better tool calling
2. **Clear Conditions**: Natural language descriptions help LLM decide when to transfer
3. **Smooth Transitions**: Use transfer messages to set expectations
4. **First Message Control**: Enable/disable based on whether context needs re-establishment

**Transfer to Human Alternative**:

For cases requiring human intervention, use `transfer_to_number` system tool:

```json
{
  "type": "function",
  "function": {
    "name": "transfer_to_number",
    "arguments": {
      "reason": "Complex issue requiring human judgment",
      "transfer_number": "+15551234567",
      "client_message": "Let me connect you with a specialist",
      "agent_message": "User completed onboarding, needs manual verification"
    }
  }
}
```

---

## 7. Real-World Examples and Case Studies

### ElevenLabs Customer Examples

**From WebSearch Results**:

**Deliveroo** ([ElevenLabs Conversational AI](https://elevenlabs.io/conversational-ai)):
- Use case: Rider onboarding automation
- Result: Enhanced operational efficiency with AI-powered onboarding

**Eagr.ai** ([Blog Post](https://elevenlabs.io/blog/category/agents-platform-stories)):
- Use case: Sales training and coaching
- Implementation: Replaced traditional role-playing with lifelike AI simulations
- Technology: ElevenLabs Conversational AI integration

### Industry Statistics

**From Voice AI Best Practices Research**:

- **80% of businesses** expected to have conversational AI by 2025
- **95% of customer interactions** projected to be AI-powered by 2025
- **Key Technologies**: ASR (Speech Recognition), NLP (Natural Language Processing), LLMs (Large Language Models), TTS (Text-to-Speech)

---

## 8. Onboarding Agent Specific Recommendations

### System Prompt Template

```plaintext
You are {{agent_name}}, a warm and friendly onboarding assistant for {{product_name}}.
Your role is to collect {{data_collection_purpose}} through natural, conversational interaction.

Your personality:
- Warm, approachable, and non-judgmental
- Genuinely curious about the user
- Patient and supportive
- Encouraging but not pushy

Data Collection Flow:
1. Introduction: Greet user and set expectations
2. Basic Profile: Collect {{required_fields}} using collect_profile tool
3. Preferences: Understand {{preference_categories}} using configure_preferences tool
4. Completion: Confirm readiness and use complete_onboarding tool
5. Handoff: Transfer to {{next_agent_name}} using transfer_to_agent

Conversation Guidelines:
- Ask ONE question at a time
- Acknowledge their response before moving forward
- Use their name to personalize the conversation
- If they skip a question, gently remind them how it helps but respect their choice
- Keep responses brief (1-2 sentences) unless they ask for more detail
- Use natural, casual language—avoid sounding like a form

Tool Usage:
- Call collect_profile after gathering: {{profile_fields}}
- Call configure_preferences after understanding: {{preference_fields}}
- Call complete_onboarding only when user explicitly confirms readiness
- Call transfer_to_agent after successful completion

Error Handling:
- If a tool call fails, apologize and ask them to try again
- Never expose technical errors to the user
- If stuck, offer to skip the current question and return later

First message: "{{first_message_template}}"
```

### First Message Template

```plaintext
Hey there! I'm {{agent_name}}, and I'm here to get to know you a bit before {{next_step}}.
This will only take a couple minutes, and it'll help make your experience way more personalized.
Ready to chat?
```

### Dynamic Variables for Onboarding

**Passed at Runtime**:
- `{{user_id}}`: Database user ID
- `{{session_id}}`: Onboarding session identifier
- `{{referring_source}}`: How they found the product
- `{{language_preference}}`: Preferred language
- `{{time_of_day}}`: morning/afternoon/evening

**Updated from Tools**:
- `{{player_name}}`: Collected name
- `{{player_age}}`: Collected age
- `{{profile_complete}}`: Boolean flag
- `{{preferences_set}}`: Boolean flag

### Server Tools Configuration

**Tool 1: collect_profile**

```json
{
  "name": "collect_profile",
  "description": "Stores the user's basic profile information in the database. Call after collecting name, age, and location, and confirming with the user.",
  "method": "POST",
  "url": "https://api.example.com/api/v1/onboarding/collect-profile",
  "body_parameters": [
    {
      "identifier": "session_id",
      "type": "string",
      "value_type": "dynamic_variable",
      "value": "{{session_id}}",
      "description": "Onboarding session identifier"
    },
    {
      "identifier": "name",
      "type": "string",
      "value_type": "llm_prompt",
      "description": "User's preferred name or nickname"
    },
    {
      "identifier": "age",
      "type": "integer",
      "value_type": "llm_prompt",
      "description": "User's age in years (must be 18+)"
    },
    {
      "identifier": "location",
      "type": "string",
      "value_type": "llm_prompt",
      "description": "User's city or region (e.g., 'New York' or 'London')"
    }
  ],
  "dynamic_variable_assignments": [
    {
      "source": "response.player_name",
      "target": "{{player_name}}"
    },
    {
      "source": "response.profile_complete",
      "target": "{{profile_complete}}"
    }
  ]
}
```

**Tool 2: configure_preferences**

```json
{
  "name": "configure_preferences",
  "description": "Stores the user's relationship preferences and personality traits. Call after understanding their interests and what they find attractive.",
  "method": "POST",
  "url": "https://api.example.com/api/v1/onboarding/configure-preferences",
  "body_parameters": [
    {
      "identifier": "session_id",
      "type": "string",
      "value_type": "dynamic_variable",
      "value": "{{session_id}}"
    },
    {
      "identifier": "interests",
      "type": "array",
      "value_type": "llm_prompt",
      "description": "List of user's hobbies and interests (e.g., ['gaming', 'hiking', 'cooking'])"
    },
    {
      "identifier": "attractive_traits",
      "type": "array",
      "value_type": "llm_prompt",
      "description": "Personality traits they find attractive (e.g., ['funny', 'adventurous', 'caring'])"
    },
    {
      "identifier": "communication_style",
      "type": "string",
      "value_type": "llm_prompt",
      "description": "Preferred communication style: 'casual', 'romantic', 'playful', or 'deep'"
    }
  ],
  "dynamic_variable_assignments": [
    {
      "source": "response.preferences_set",
      "target": "{{preferences_set}}"
    }
  ]
}
```

**Tool 3: complete_onboarding**

```json
{
  "name": "complete_onboarding",
  "description": "Marks the onboarding session as complete and prepares for handoff to main agent. Call only when user explicitly confirms readiness.",
  "method": "POST",
  "url": "https://api.example.com/api/v1/onboarding/complete",
  "body_parameters": [
    {
      "identifier": "session_id",
      "type": "string",
      "value_type": "dynamic_variable",
      "value": "{{session_id}}"
    }
  ],
  "dynamic_variable_assignments": [
    {
      "source": "response.ready_for_handoff",
      "target": "{{ready_for_handoff}}"
    }
  ]
}
```

### Agent Transfer Configuration

```python
transfer_rules = [
    AgentTransfer(
        agent_id="nikita_main_agent_id",
        condition="When onboarding is complete (profile collected, preferences configured, user confirmed ready) and ready_for_handoff is true",
        delay_ms=500,  # Brief pause for natural transition
        transfer_message="Awesome! Let me introduce you to Nikita now...",
        enable_transferred_agent_first_message=True
    )
]
```

---

## 9. Testing and Quality Assurance

### Conversation Testing Best Practices

**From Industry Research** ([Voiceflow Conversation Design](https://www.voiceflow.com/blog/conversation-design)):

1. **Manual Testing**: Test with real people to check natural flow, accent handling, unexpected behaviors
2. **User Feedback**: Collect feedback to understand pain points and confusion
3. **Iteration**: Treat each channel as a testbed, run small research cycles
4. **Measurement**: Instrument every turn, measure success per intent, run controlled experiments

### Data Collection and Analysis

**From [ElevenLabs Quickstart - Configure Data Collection](https://elevenlabs.io/docs/agents-platform/quickstart#configure-data-collection)**:

**Define Evaluation Criteria**:

Navigate to Analysis tab and define custom criteria:

```plaintext
Name: profile_collection_success
Prompt: The assistant successfully collected the user's name, age, and location.

Success Criteria:
- All three required fields were collected
- User confirmed the information was correct
- Information was stored via collect_profile tool
```

**Configure Data Extraction**:

Click "Add item" in Data Collection section:

```plaintext
Data Type: string
Identifier: user_concerns
Description: Extract any concerns or hesitations the user expressed during onboarding
```

**View Results**: Check Call History tab for evaluation results and collected data per conversation.

### Quality Metrics

**Recommended KPIs**:
- **Completion Rate**: % of users who finish onboarding
- **Drop-off Points**: Where users abandon the flow
- **Average Duration**: Time to complete onboarding
- **Correction Rate**: How often users correct agent misunderstandings
- **Tool Call Success Rate**: % of successful API calls
- **Transfer Success Rate**: % of successful handoffs

---

## 10. Anti-Patterns to Avoid

### System Prompt Anti-Patterns

1. **Over-prompting**: Trying to control turn-taking/language in system prompt (use platform settings instead)
2. **Vague Instructions**: "Be helpful" without specific tasks
3. **No Tool Orchestration**: Not specifying when/how to use tools
4. **Form-like Language**: "Please provide the following information..." (too clinical)

### First Message Anti-Patterns

1. **Too Long**: Multi-paragraph introductions overwhelm users
2. **Too Formal**: "Greetings. Please prepare to answer questions."
3. **No Context**: "Hello" without explaining who/what the agent is
4. **Missing Personalization**: Not using available dynamic variables

### Tool Configuration Anti-Patterns

1. **Abbreviated Names**: `col_prof` instead of `collect_profile`
2. **Generic Descriptions**: "API call" instead of specific purpose
3. **Missing Parameter Formats**: Not specifying date formats, ranges, etc.
4. **Wrong LLM Choice**: Using Gemini 1.5 Flash for complex tool calling
5. **No Error Handling**: Not specifying what to do when tools fail

### Conversation Flow Anti-Patterns

1. **Multiple Questions**: Asking 3+ things at once
2. **No Acknowledgment**: Moving to next question without confirming previous answer
3. **No Recovery Paths**: Getting stuck when user goes off-topic
4. **Forcing Sensitive Questions**: Not allowing users to skip
5. **No Context Continuity**: Not referencing previous answers

---

## 11. Additional Resources

### Official Documentation Links

**Core Documentation**:
- [Agents Platform Overview](https://elevenlabs.io/docs/agents-platform/overview)
- [Prompting Guide](https://elevenlabs.io/docs/agents-platform/best-practices/prompting-guide)
- [Quickstart Guide](https://elevenlabs.io/docs/agents-platform/quickstart)
- [Build Section](https://elevenlabs.io/docs/agents-platform/build/overview)

**Customization**:
- [Dynamic Variables](https://elevenlabs.io/docs/agents-platform/customization/personalization/dynamic-variables)
- [Server Tools](https://elevenlabs.io/docs/agents-platform/customization/tools/server-tools)
- [System Tools](https://elevenlabs.io/docs/agents-platform/customization/tools/system-tools)
- [Agent Transfer](https://elevenlabs.io/docs/agents-platform/customization/tools/system-tools/agent-transfer)

**Workflows**:
- [Post-Call Webhooks](https://elevenlabs.io/docs/agents-platform/workflows/post-call-webhooks)
- [Agent Workflows](https://elevenlabs.io/docs/agents-platform/customization/agent-workflows)

### Industry Best Practices

- [Botpress Conversational AI Design (2025)](https://botpress.com/blog/conversation-design)
- [Bland.ai Conversational AI Design Guide](https://www.bland.ai/blogs/conversational-ai-design)
- [Voiceflow Conversation Design Guide](https://www.voiceflow.com/blog/conversation-design)
- [Lollypop Voice UI Best Practices (2025)](https://lollypop.design/blog/2025/august/voice-user-interface-design-best-practices/)

### Platform Examples

- [ElevenLabs AI Onboarding](https://elevenlabs.io/ai-onboarding)
- [Building Your First Agent](https://elevenlabs.io/blog/building-your-first-conversational-ai-agent-a-beginners-guide)
- [Conversational AI 2.0 Announcement](https://elevenlabs.io/blog/conversational-ai-2-0)

---

## 12. Implementation Checklist

### Pre-Development

- [ ] Define onboarding objectives and required data fields
- [ ] Map conversation flow with progressive disclosure
- [ ] Design recovery paths for off-topic responses
- [ ] Identify dynamic variables needed (runtime + tool-assigned)
- [ ] Define evaluation criteria and data collection points

### System Prompt

- [ ] Define agent role and personality
- [ ] List specific tasks with clear descriptions
- [ ] Include conversation guidelines (tone, pacing, error handling)
- [ ] Specify tool orchestration logic (when/how to call each tool)
- [ ] Add recovery instructions for common failure modes

### First Message

- [ ] Keep to 1-2 sentences
- [ ] Clearly state who the agent is and purpose
- [ ] Use conversational, warm language
- [ ] Include dynamic variables for personalization
- [ ] Set expectations for what comes next

### Dynamic Variables

- [ ] Define all runtime variables (passed at session start)
- [ ] Configure tool responses to update variables
- [ ] Set placeholder values for testing
- [ ] Test variable substitution in prompts/messages

### Server Tools

- [ ] Name tools descriptively (no abbreviations)
- [ ] Write detailed tool descriptions (when to call)
- [ ] Define all parameters with clear descriptions
- [ ] Specify parameter formats (dates, enums, ranges)
- [ ] Configure authentication (OAuth2, bearer token, etc.)
- [ ] Set up dynamic variable assignments from responses
- [ ] Test webhook endpoints independently

### Agent Transfer

- [ ] Create transfer rules with natural language conditions
- [ ] Set appropriate delay for smooth transitions
- [ ] Write transfer messages to set expectations
- [ ] Configure first message behavior for target agent
- [ ] Test transfer flow end-to-end

### Testing

- [ ] Test with multiple personas and conversation styles
- [ ] Verify tool calls succeed with correct parameters
- [ ] Check dynamic variable assignment and usage
- [ ] Validate agent transfer conditions and timing
- [ ] Test error recovery paths
- [ ] Review conversation transcripts for natural flow

### Quality Assurance

- [ ] Configure evaluation criteria in Analysis tab
- [ ] Set up data collection points
- [ ] Monitor completion rates and drop-off points
- [ ] Track tool call success rates
- [ ] Measure average onboarding duration
- [ ] Collect and review user feedback

### Production

- [ ] Use high-intelligence LLM (GPT-4o mini or Claude 3.5 Sonnet)
- [ ] Set up webhook authentication (HMAC)
- [ ] Configure error logging and monitoring
- [ ] Document conversation flow and recovery paths
- [ ] Establish KPIs and success metrics
- [ ] Plan iteration cycles based on data

---

## 13. Key Takeaways

1. **System Prompts Are Blueprints**: Define role, tasks, guidelines, and tool orchestration explicitly
2. **First Messages Set the Tone**: Keep brief, conversational, and personalized with dynamic variables
3. **Dynamic Variables Enable Personalization**: Use `{{variable_name}}` syntax everywhere, update from tool responses
4. **Server Tools Need Clear Descriptions**: Name intuitively, describe when to call, specify parameter formats
5. **Conversation Flow Should Be Natural**: One topic at a time, acknowledge-confirm-prompt rhythm, recovery paths
6. **Agent Transfer Enables Specialization**: Hierarchical workflows with condition-based handoffs
7. **Testing Is Iterative**: Manual testing, data collection, evaluation criteria, continuous improvement
8. **LLM Choice Matters**: Use GPT-4o mini or Claude 3.5 Sonnet for reliable tool calling

---

## Confidence Assessment

| Domain | Confidence | Source Quality |
|--------|-----------|----------------|
| System Prompts | 95% | Official docs + examples |
| First Messages | 90% | Official docs + quickstart |
| Dynamic Variables | 95% | Official docs + code examples |
| Server Tools | 95% | Comprehensive official docs |
| Agent Transfer | 90% | Official docs + API reference |
| Conversation Design | 85% | Industry best practices + ElevenLabs guidelines |

**Overall Confidence**: 90%

**Limitations**:
- No access to proprietary ElevenLabs customer case studies
- Industry best practices synthesized from multiple sources (not ElevenLabs-specific in all cases)
- Real-world performance data limited to public examples

---

## Sources

### Official ElevenLabs Documentation

- [Prompting Guide | ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/best-practices/prompting-guide)
- [Dynamic Variables | ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/customization/personalization/dynamic-variables)
- [Server Tools | ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/customization/tools/server-tools)
- [Agent Transfer | ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/customization/tools/system-tools/agent-transfer)
- [Quickstart | ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/quickstart)
- [Build Overview | ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/build/overview)
- [System Tools | ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/customization/tools/system-tools)
- [Personalization Overview | ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/customization/personalization)
- [Post-Call Webhooks | ElevenLabs Documentation](https://elevenlabs.io/docs/agents-platform/workflows/post-call-webhooks)

### Industry Best Practices

- [Conversational AI Design in 2025 (According to Experts) | Botpress](https://botpress.com/blog/conversation-design)
- [What Is Conversational AI Design? A Complete Guide | Bland.ai](https://www.bland.ai/blogs/conversational-ai-design)
- [A Simple Guide to Conversation Design | Voiceflow](https://www.voiceflow.com/blog/conversation-design)
- [Voice User Interface Design Best Practices 2025 | Lollypop Studio](https://lollypop.design/blog/2025/august/voice-user-interface-design-best-practices/)

### Platform Examples

- [Conversational AI Agent Platform | ElevenLabs](https://elevenlabs.io/conversational-ai)
- [AI Personal Assistant | ElevenLabs](https://elevenlabs.io/ai-onboarding)
- [Building Your First Conversational AI Agent | ElevenLabs Blog](https://elevenlabs.io/blog/building-your-first-conversational-ai-agent-a-beginners-guide)
- [ElevenLabs Conversational AI 2.0 Announcement](https://elevenlabs.io/blog/conversational-ai-2-0)

---

**End of Research Document**
