#!/usr/bin/env python3
"""Configure main Nikita agent server tools via ElevenLabs API.

This script adds the 4 server tools to the main Nikita agent:
1. get_context - Load user context at call start
2. get_memory - Query Graphiti for memories
3. score_turn - Score emotional exchanges
4. update_memory - Store new facts to memory

Usage:
    source .venv/bin/activate
    export ELEVENLABS_API_KEY=sk_xxx
    export ELEVENLABS_DEFAULT_AGENT_ID=agent_xxx
    python scripts/configure_nikita_tools.py

Requires:
    - ELEVENLABS_API_KEY environment variable
    - ELEVENLABS_DEFAULT_AGENT_ID environment variable
    - Main Nikita agent already created in dashboard
"""

import asyncio
import os
import sys

import httpx

# Configuration
API_BASE = "https://api.elevenlabs.io/v1/convai"

# Default backend URL - update when Cloud Run URL changes
DEFAULT_BACKEND_URL = "https://nikita-api-1040094048579.us-central1.run.app"


def get_config() -> tuple[str, str, str]:
    """Get configuration from environment.

    Returns:
        Tuple of (api_key, agent_id, backend_url)

    Raises:
        ValueError: If required environment variables are missing
    """
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    agent_id = os.environ.get("ELEVENLABS_DEFAULT_AGENT_ID")
    backend_url = os.environ.get("BACKEND_URL", DEFAULT_BACKEND_URL)

    # Try loading from .env file if not in environment
    if not api_key or not agent_id:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ELEVENLABS_API_KEY=") and not api_key:
                        api_key = line.split("=", 1)[1]
                    elif line.startswith("ELEVENLABS_DEFAULT_AGENT_ID=") and not agent_id:
                        agent_id = line.split("=", 1)[1]
                    elif line.startswith("BACKEND_URL="):
                        backend_url = line.split("=", 1)[1]

    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not found in environment or .env file")
    if not agent_id:
        raise ValueError("ELEVENLABS_DEFAULT_AGENT_ID not found in environment or .env file")

    return api_key, agent_id, backend_url


def build_tools_config(server_tool_url: str) -> list[dict]:
    """Build the server tools configuration for main Nikita agent.

    Based on ElevenLabs schema from HubSpot integration example.
    Each tool uses the webhook type with api_schema.

    Args:
        server_tool_url: The webhook URL for server tools

    Returns:
        List of tool configurations
    """
    return [
        {
            "type": "webhook",
            "name": "get_context",
            "description": """Load context about the user at the START of the call.

WHEN TO USE:
- Immediately at call start to understand who you're talking to
- After long pauses (>5 minutes) to refresh your context

HOW TO USE:
- Call this first before responding to the user
- No parameters needed - context is loaded automatically

RETURNS:
- user_name: Their name
- chapter: Relationship stage (1-5)
- relationship_score: How close you are (0-100)
- engagement_state: Current dynamic (IN_ZONE, CLINGY, DISTANT, etc.)
- nikita_mood: Your current mood
- today_summary: What happened today
- backstory: How you met

ERROR HANDLING:
- If context fails to load, use neutral defaults and be warm but cautious""",
            "api_schema": {
                "url": server_tool_url,
                "method": "POST",
                "path_params_schema": [],
                "query_params_schema": [],
                "request_body_schema": {
                    "id": "body",
                    "type": "object",
                    "description": "Context request",
                    "required": True,
                    "properties": [
                        {
                            "id": "tool_name",
                            "type": "string",
                            "description": "Tool name",
                            "required": True,
                            "value_type": "constant",
                            "constant_value": "get_context",
                            "dynamic_variable": ""
                        },
                        {
                            "id": "user_id",
                            "type": "string",
                            "description": "User UUID from session",
                            "required": True,
                            "value_type": "dynamic_variable",
                            "dynamic_variable": "user_id",
                            "constant_value": ""
                        },
                        {
                            "id": "session_id",
                            "type": "string",
                            "description": "Voice session ID",
                            "required": True,
                            "value_type": "dynamic_variable",
                            "dynamic_variable": "session_id",
                            "constant_value": ""
                        },
                        {
                            "id": "parameters",
                            "type": "object",
                            "description": "Optional parameters",
                            "required": False,
                            "properties": [
                                {
                                    "id": "include_persona",
                                    "type": "boolean",
                                    "description": "Include voice persona additions",
                                    "required": False,
                                    "value_type": "constant",
                                    "constant_value": "true",
                                    "dynamic_variable": ""
                                },
                                {
                                    "id": "include_behavior",
                                    "type": "boolean",
                                    "description": "Include chapter behavior",
                                    "required": False,
                                    "value_type": "constant",
                                    "constant_value": "true",
                                    "dynamic_variable": ""
                                }
                            ]
                        }
                    ]
                },
                "request_headers": [
                    {
                        "type": "value",
                        "name": "Content-Type",
                        "value": "application/json"
                    }
                ]
            },
            "response_timeout_secs": 20
        },
        {
            "type": "webhook",
            "name": "get_memory",
            "description": """Search your memory for past events and conversations.

WHEN TO USE:
- User says "remember when..." or "do you recall..."
- User asks about specific dates or past events
- User references something you discussed before
- You want to bring up a shared memory naturally

HOW TO USE:
- Extract the key topic from user's question
- Use specific search terms like "birthday", "work", "dinner", "trip"
- Example: If user asks "Remember that time we talked about your cat?" -> search for "cat"

RETURNS:
- facts: List of relevant memories with context
- threads: Open conversation topics to follow up on

ERROR HANDLING:
- If no memories found, say "I don't remember that specifically, remind me?"
- Don't pretend to remember things you don't have in memory""",
            "api_schema": {
                "url": server_tool_url,
                "method": "POST",
                "path_params_schema": [],
                "query_params_schema": [],
                "request_body_schema": {
                    "id": "body",
                    "type": "object",
                    "description": "Memory query request",
                    "required": True,
                    "properties": [
                        {
                            "id": "tool_name",
                            "type": "string",
                            "description": "Tool name",
                            "required": True,
                            "value_type": "constant",
                            "constant_value": "get_memory",
                            "dynamic_variable": ""
                        },
                        {
                            "id": "user_id",
                            "type": "string",
                            "description": "User UUID from session",
                            "required": True,
                            "value_type": "dynamic_variable",
                            "dynamic_variable": "user_id",
                            "constant_value": ""
                        },
                        {
                            "id": "session_id",
                            "type": "string",
                            "description": "Voice session ID",
                            "required": True,
                            "value_type": "dynamic_variable",
                            "dynamic_variable": "session_id",
                            "constant_value": ""
                        },
                        {
                            "id": "parameters",
                            "type": "object",
                            "description": "Query parameters",
                            "required": True,
                            "properties": [
                                {
                                    "id": "query",
                                    "type": "string",
                                    "description": "Search query for memories (e.g., 'birthday', 'work', 'cat')",
                                    "required": True,
                                    "value_type": "llm_prompt",
                                    "constant_value": "",
                                    "dynamic_variable": ""
                                },
                                {
                                    "id": "limit",
                                    "type": "integer",
                                    "description": "Maximum number of memories to return (default 5)",
                                    "required": False,
                                    "value_type": "constant",
                                    "constant_value": "5",
                                    "dynamic_variable": ""
                                }
                            ]
                        }
                    ]
                },
                "request_headers": [
                    {
                        "type": "value",
                        "name": "Content-Type",
                        "value": "application/json"
                    }
                ]
            },
            "response_timeout_secs": 20
        },
        {
            "type": "webhook",
            "name": "score_turn",
            "description": """Score an emotional exchange to track relationship changes.

WHEN TO USE:
- After meaningful emotional exchanges (not casual small talk)
- When user shares something personal or vulnerable
- After compliments, flirting, or intimate moments
- After disagreements or tense exchanges

HOW TO USE:
- Provide the user's message and your response
- Only score exchanges that have emotional weight
- Example: Score "I've been feeling really stressed" but not "what's the weather"

RETURNS:
- intimacy_delta: Change in emotional closeness (-5 to +5)
- passion_delta: Change in romantic energy (-5 to +5)
- trust_delta: Change in trust level (-5 to +5)
- secureness_delta: Change in relationship security (-5 to +5)
- analysis_summary: Brief explanation of the score

ERROR HANDLING:
- If scoring fails, continue the conversation naturally
- Don't mention scores or metrics to the user""",
            "api_schema": {
                "url": server_tool_url,
                "method": "POST",
                "path_params_schema": [],
                "query_params_schema": [],
                "request_body_schema": {
                    "id": "body",
                    "type": "object",
                    "description": "Scoring request",
                    "required": True,
                    "properties": [
                        {
                            "id": "tool_name",
                            "type": "string",
                            "description": "Tool name",
                            "required": True,
                            "value_type": "constant",
                            "constant_value": "score_turn",
                            "dynamic_variable": ""
                        },
                        {
                            "id": "user_id",
                            "type": "string",
                            "description": "User UUID from session",
                            "required": True,
                            "value_type": "dynamic_variable",
                            "dynamic_variable": "user_id",
                            "constant_value": ""
                        },
                        {
                            "id": "session_id",
                            "type": "string",
                            "description": "Voice session ID",
                            "required": True,
                            "value_type": "dynamic_variable",
                            "dynamic_variable": "session_id",
                            "constant_value": ""
                        },
                        {
                            "id": "parameters",
                            "type": "object",
                            "description": "Turn data",
                            "required": True,
                            "properties": [
                                {
                                    "id": "user_message",
                                    "type": "string",
                                    "description": "What the user said",
                                    "required": True,
                                    "value_type": "llm_prompt",
                                    "constant_value": "",
                                    "dynamic_variable": ""
                                },
                                {
                                    "id": "nikita_response",
                                    "type": "string",
                                    "description": "What you (Nikita) responded",
                                    "required": True,
                                    "value_type": "llm_prompt",
                                    "constant_value": "",
                                    "dynamic_variable": ""
                                }
                            ]
                        }
                    ]
                },
                "request_headers": [
                    {
                        "type": "value",
                        "name": "Content-Type",
                        "value": "application/json"
                    }
                ]
            },
            "response_timeout_secs": 20
        },
        {
            "type": "webhook",
            "name": "update_memory",
            "description": """Store a new fact about the user to remember later.

WHEN TO USE:
- User shares NEW personal information (job, hobby, family, preferences)
- User mentions important dates (birthday, anniversary)
- User tells you something meaningful they want you to remember
- User corrects previous information

HOW TO USE:
- Extract the key fact to store
- Be specific: "User's birthday is March 15" not "User mentioned birthday"
- Include context when relevant: "User got promoted at work (excited)"

RETURNS:
- stored: Whether the fact was saved successfully
- fact: The fact that was stored

ERROR HANDLING:
- If storage fails, remember it for this conversation only
- Don't tell the user you're storing information about them""",
            "api_schema": {
                "url": server_tool_url,
                "method": "POST",
                "path_params_schema": [],
                "query_params_schema": [],
                "request_body_schema": {
                    "id": "body",
                    "type": "object",
                    "description": "Memory update request",
                    "required": True,
                    "properties": [
                        {
                            "id": "tool_name",
                            "type": "string",
                            "description": "Tool name",
                            "required": True,
                            "value_type": "constant",
                            "constant_value": "update_memory",
                            "dynamic_variable": ""
                        },
                        {
                            "id": "user_id",
                            "type": "string",
                            "description": "User UUID from session",
                            "required": True,
                            "value_type": "dynamic_variable",
                            "dynamic_variable": "user_id",
                            "constant_value": ""
                        },
                        {
                            "id": "session_id",
                            "type": "string",
                            "description": "Voice session ID",
                            "required": True,
                            "value_type": "dynamic_variable",
                            "dynamic_variable": "session_id",
                            "constant_value": ""
                        },
                        {
                            "id": "parameters",
                            "type": "object",
                            "description": "Fact to store",
                            "required": True,
                            "properties": [
                                {
                                    "id": "fact",
                                    "type": "string",
                                    "description": "The fact to remember (e.g., 'User works as a software engineer')",
                                    "required": True,
                                    "value_type": "llm_prompt",
                                    "constant_value": "",
                                    "dynamic_variable": ""
                                },
                                {
                                    "id": "category",
                                    "type": "string",
                                    "description": "Category: personal, work, family, preferences, dates",
                                    "required": False,
                                    "value_type": "llm_prompt",
                                    "constant_value": "",
                                    "dynamic_variable": ""
                                }
                            ]
                        }
                    ]
                },
                "request_headers": [
                    {
                        "type": "value",
                        "name": "Content-Type",
                        "value": "application/json"
                    }
                ]
            },
            "response_timeout_secs": 20
        }
    ]


async def get_current_agent_config(client: httpx.AsyncClient, api_key: str, agent_id: str) -> dict:
    """Fetch current agent configuration.

    Args:
        client: HTTP client
        api_key: ElevenLabs API key
        agent_id: Agent ID to fetch

    Returns:
        Agent configuration dict
    """
    print(f"[INFO] Fetching current agent config for {agent_id}...")
    response = await client.get(
        f"{API_BASE}/agents/{agent_id}",
        headers={"xi-api-key": api_key},
    )
    response.raise_for_status()
    return response.json()


async def update_agent_tools(
    client: httpx.AsyncClient, api_key: str, agent_id: str, tools: list[dict]
) -> dict:
    """Update agent with new tools configuration.

    Args:
        client: HTTP client
        api_key: ElevenLabs API key
        agent_id: Agent ID to update
        tools: List of tool configurations

    Returns:
        Updated agent configuration
    """
    print(f"[INFO] Updating agent tools...")

    # Tools go in conversation_config.agent.prompt.tools
    payload = {
        "conversation_config": {
            "agent": {
                "prompt": {
                    "tools": tools
                }
            }
        }
    }

    response = await client.patch(
        f"{API_BASE}/agents/{agent_id}",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        },
        json=payload,
    )

    if response.status_code != 200:
        print(f"[ERROR] Failed to update agent tools: {response.status_code}")
        print(f"[ERROR] Response: {response.text}")
        response.raise_for_status()

    return response.json()


async def add_dynamic_variables(
    client: httpx.AsyncClient, api_key: str, agent_id: str
) -> dict:
    """Add dynamic variables to the agent configuration.

    Args:
        client: HTTP client
        api_key: ElevenLabs API key
        agent_id: Agent ID to update

    Returns:
        Updated agent configuration
    """
    print(f"[INFO] Adding dynamic variables...")

    # Dynamic variables used by server tools
    payload = {
        "conversation_config": {
            "agent": {
                "dynamic_variables": {
                    "user_id": {
                        "value": "test-user-id",
                        "is_fill_in_the_blank": True
                    },
                    "session_id": {
                        "value": "test-session-id",
                        "is_fill_in_the_blank": True
                    },
                    "user_name": {
                        "value": "friend",
                        "is_fill_in_the_blank": True
                    }
                }
            }
        }
    }

    response = await client.patch(
        f"{API_BASE}/agents/{agent_id}",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        },
        json=payload,
    )

    if response.status_code != 200:
        print(f"[ERROR] Failed to add dynamic variables: {response.status_code}")
        print(f"[ERROR] Response: {response.text}")

    return response.json() if response.status_code == 200 else {}


async def main():
    """Main entry point."""
    print("=" * 60)
    print("Nikita Server Tools Configuration")
    print("=" * 60)

    try:
        api_key, agent_id, backend_url = get_config()
        print(f"[OK] API key loaded (ends with ...{api_key[-4:]})")
        print(f"[OK] Agent ID: {agent_id}")
        print(f"[OK] Backend URL: {backend_url}")
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    server_tool_url = f"{backend_url}/api/v1/voice/server-tool"
    tools = build_tools_config(server_tool_url)
    print(f"[OK] Built {len(tools)} server tools configuration")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get current config
        try:
            current = await get_current_agent_config(client, api_key, agent_id)
            print(f"[OK] Current agent: {current.get('name', 'Unknown')}")
            current_tools = current.get('conversation_config', {}).get('agent', {}).get('prompt', {}).get('tools', [])
            print(f"[INFO] Current tools: {len(current_tools)}")
            for tool in current_tools:
                print(f"  - {tool.get('name', 'Unknown')}")
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to fetch agent: {e}")
            sys.exit(1)

        # Update with new tools
        try:
            result = await update_agent_tools(client, api_key, agent_id, tools)
            print(f"[OK] Agent tools updated successfully")
            new_tools = result.get('conversation_config', {}).get('agent', {}).get('prompt', {}).get('tools', [])
            print(f"[INFO] New tools count: {len(new_tools)}")
            for tool in new_tools:
                print(f"  - {tool.get('name', 'Unknown')}: {tool.get('type', 'Unknown')}")
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to update agent tools: {e}")
            print(f"[ERROR] Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
            sys.exit(1)

        # Add dynamic variables
        try:
            dv_result = await add_dynamic_variables(client, api_key, agent_id)
            if dv_result:
                print(f"[OK] Dynamic variables configured")
        except Exception as e:
            print(f"[WARN] Failed to add dynamic variables: {e}")

        # Fetch final config to verify
        try:
            final = await get_current_agent_config(client, api_key, agent_id)
            final_tools = final.get('conversation_config', {}).get('agent', {}).get('prompt', {}).get('tools', [])
            print(f"\n[VERIFY] Final configuration:")
            print(f"  - Tools: {len(final_tools)}")
            for tool in final_tools:
                print(f"    - {tool.get('name')}")
        except Exception as e:
            print(f"[WARN] Failed to verify final config: {e}")

    print("=" * 60)
    print("[DONE] Configuration complete!")
    print(f"[INFO] Agent ID: {agent_id}")
    print(f"[INFO] Server Tool URL: {server_tool_url}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
