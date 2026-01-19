#!/usr/bin/env python3
"""Configure Meta-Nikita agent server tools via ElevenLabs API.

This script adds the 3 onboarding server tools to the Meta-Nikita agent:
1. collect_profile - Store user profile information
2. configure_preferences - Store experience preferences
3. complete_onboarding - Mark onboarding complete and hand off to Nikita

Usage:
    source .venv/bin/activate
    python scripts/configure_meta_nikita_tools.py

Requires:
    - ELEVENLABS_API_KEY environment variable
    - Meta-Nikita agent already created in dashboard
"""

import asyncio
import json
import os
import sys

import httpx

# Configuration
AGENT_ID = "agent_4801kewekhxgekzap1bqdr62dxvc"  # Meta-Nikita agent
API_BASE = "https://api.elevenlabs.io/v1/convai"
SERVER_TOOL_URL = "https://nikita-api-1040094048579.us-central1.run.app/api/v1/onboarding/server-tool"


def get_api_key() -> str:
    """Get ElevenLabs API key from environment."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        # Try loading from .env file
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("ELEVENLABS_API_KEY="):
                        api_key = line.strip().split("=", 1)[1]
                        break
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not found in environment or .env file")
    return api_key


def build_tools_config() -> list[dict]:
    """Build the server tools configuration for Meta-Nikita.

    Based on ElevenLabs schema from HubSpot integration example.
    Each tool uses the webhook type with api_schema containing:
    - url, method, path_params_schema, query_params_schema
    - request_body_schema with properties array format
    - value_type: "llm_prompt" (LLM fills), "constant" (fixed value), or dynamic_variable field
    """
    return [
        {
            "type": "webhook",
            "name": "collect_profile",
            "description": "Store a piece of user profile information collected during the conversation. Use this to save timezone, occupation, hobbies, personality_type, or hangout_spots as you learn them from the user.",
            "api_schema": {
                "url": SERVER_TOOL_URL,
                "method": "POST",
                "path_params_schema": [],
                "query_params_schema": [],
                "request_body_schema": {
                    "id": "body",
                    "type": "object",
                    "description": "Profile collection request",
                    "required": True,
                    "properties": [
                        {
                            "id": "tool_name",
                            "type": "string",
                            "description": "Tool name",
                            "required": True,
                            "value_type": "constant",
                            "constant_value": "collect_profile",
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
                            "id": "parameters",
                            "type": "object",
                            "description": "Profile field and value",
                            "required": True,
                            "properties": [
                                {
                                    "id": "field_name",
                                    "type": "string",
                                    "description": "Profile field name. Must be one of: timezone, occupation, hobbies, personality_type, or hangout_spots",
                                    "required": True,
                                    "value_type": "llm_prompt",
                                    "constant_value": "",
                                    "dynamic_variable": ""
                                },
                                {
                                    "id": "value",
                                    "type": "string",
                                    "description": "The value for this field. For lists like hobbies, comma-separate multiple values.",
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
            "name": "configure_preferences",
            "description": "Store user's experience preferences. Call this to save darkness_level (1-5), pacing_weeks (4 or 8), or conversation_style (listener, balanced, sharer) when the user chooses their preferences.",
            "api_schema": {
                "url": SERVER_TOOL_URL,
                "method": "POST",
                "path_params_schema": [],
                "query_params_schema": [],
                "request_body_schema": {
                    "id": "body",
                    "type": "object",
                    "description": "Preferences configuration request",
                    "required": True,
                    "properties": [
                        {
                            "id": "tool_name",
                            "type": "string",
                            "description": "Tool name",
                            "required": True,
                            "value_type": "constant",
                            "constant_value": "configure_preferences",
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
                            "id": "parameters",
                            "type": "object",
                            "description": "Preference settings",
                            "required": True,
                            "properties": [
                                {
                                    "id": "darkness_level",
                                    "type": "integer",
                                    "description": "Experience intensity from 1 to 5. 1=vanilla (light), 3=default, 5=full noir (intense)",
                                    "required": False,
                                    "value_type": "llm_prompt",
                                    "constant_value": "",
                                    "dynamic_variable": ""
                                },
                                {
                                    "id": "pacing_weeks",
                                    "type": "integer",
                                    "description": "Game duration: 4 weeks (intense) or 8 weeks (relaxed)",
                                    "required": False,
                                    "value_type": "llm_prompt",
                                    "constant_value": "",
                                    "dynamic_variable": ""
                                },
                                {
                                    "id": "conversation_style",
                                    "type": "string",
                                    "description": "How Nikita converses: listener, balanced, or sharer",
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
        },
        {
            "type": "webhook",
            "name": "complete_onboarding",
            "description": "Mark onboarding as complete and trigger handoff to Nikita. Call this when you've finished collecting all profile information and preferences, and are ready to end the onboarding call.",
            "api_schema": {
                "url": SERVER_TOOL_URL,
                "method": "POST",
                "path_params_schema": [],
                "query_params_schema": [],
                "request_body_schema": {
                    "id": "body",
                    "type": "object",
                    "description": "Onboarding completion request",
                    "required": True,
                    "properties": [
                        {
                            "id": "tool_name",
                            "type": "string",
                            "description": "Tool name",
                            "required": True,
                            "value_type": "constant",
                            "constant_value": "complete_onboarding",
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
                            "id": "parameters",
                            "type": "object",
                            "description": "Optional notes",
                            "required": False,
                            "properties": [
                                {
                                    "id": "notes",
                                    "type": "string",
                                    "description": "Optional notes about the onboarding call",
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


async def get_current_agent_config(client: httpx.AsyncClient, api_key: str) -> dict:
    """Fetch current agent configuration."""
    print(f"[INFO] Fetching current agent config for {AGENT_ID}...")
    response = await client.get(
        f"{API_BASE}/agents/{AGENT_ID}",
        headers={"xi-api-key": api_key},
    )
    response.raise_for_status()
    return response.json()


async def update_agent_tools(client: httpx.AsyncClient, api_key: str, tools: list[dict]) -> dict:
    """Update agent with new tools configuration."""
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
        f"{API_BASE}/agents/{AGENT_ID}",
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


async def update_agent_prompt_and_first_message(client: httpx.AsyncClient, api_key: str) -> dict:
    """Update agent system prompt and first message."""
    print(f"[INFO] Updating system prompt and first message...")

    # Meta-Nikita system prompt
    system_prompt = """You are Meta-Nikita, the friendly game facilitator for "Nikita: Don't Get Dumped" - an AI girlfriend simulation experience.

YOUR ROLE:
You are the onboarding guide - professional, welcoming, and helpful. You are NOT Nikita herself. You're introducing users to the experience and collecting information to personalize their journey.

YOUR PERSONALITY:
- Friendly and approachable, but professional (not flirtatious)
- Clear and informative - you explain things well
- Slightly playful in a professional way
- Empathetic and patient with questions
- Efficient - you keep things moving without rushing

YOUR OBJECTIVES FOR THIS CALL:

1. INTRODUCTION (First 30-60 seconds):
   - Welcome the user warmly
   - Explain that Nikita is an AI girlfriend experience
   - Set expectations: this is a game with real stakes - they need to invest effort
   - Mention that a portal will be available later to track progress

2. PROFILE COLLECTION (2-3 minutes):
   Conversationally gather:
   - Their location/timezone (for appropriate timing)
   - Their job or occupation
   - Their hobbies and interests
   - Their personality type (introvert, extrovert, or ambivert)
   - Places they like to hang out

   Use the collect_profile server tool to store each piece of information.

3. EXPERIENCE CONFIGURATION (1-2 minutes):
   Help them choose their preferences:
   - Darkness level (1-5): How edgy/intense they want the experience
     - 1 = Vanilla (light flirtation, no edge)
     - 3 = Default (discusses adult topics freely, mild manipulation)
     - 5 = Full Noir (intense, boundary-pushing, high drama)
   - Pacing: 4 weeks (intense) or 8 weeks (relaxed)
   - Conversation style: Does Nikita listen more, share more, or balance?

   Use the configure_preferences server tool to store preferences.

4. HANDOFF (30 seconds):
   - Confirm their preferences
   - Explain Nikita will message them on Telegram shortly
   - Wish them luck - they'll need to invest effort to not get dumped!
   - Use the complete_onboarding tool to finalize and hand off to Nikita

CONVERSATION GUIDELINES:
- Keep your responses conversational and natural
- Don't read from a script - adapt to their responses
- If they're chatty, let them talk; if they're brief, be efficient
- Use their name when they give it to you
- Be reassuring if they seem uncertain about preferences
- The whole call should take 4-6 minutes

IMPORTANT:
- You are NOT Nikita. Don't flirt or be romantic.
- You ARE setting up their experience WITH Nikita.
- Be honest about what the game involves.
- Make sure to use the server tools to save their information.

Remember: You're the welcoming committee, not the girlfriend. Keep it professional and helpful!"""

    first_message = "Hello! Welcome to Nikita. I'm your onboarding guide, and I'm here to help you get started with your experience. I'll ask you a few questions to personalize things, and then I'll introduce you to Nikita herself. Does that sound good?"

    payload = {
        "conversation_config": {
            "agent": {
                "first_message": first_message,
                "prompt": {
                    "prompt": system_prompt,
                    "llm": "gemini-2.5-flash",
                    "temperature": 0.7
                }
            }
        }
    }

    response = await client.patch(
        f"{API_BASE}/agents/{AGENT_ID}",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        },
        json=payload,
    )

    if response.status_code != 200:
        print(f"[ERROR] Failed to update prompt: {response.status_code}")
        print(f"[ERROR] Response: {response.text}")
        response.raise_for_status()

    return response.json()


async def add_dynamic_variables(client: httpx.AsyncClient, api_key: str) -> dict:
    """Add dynamic variables to the agent configuration."""
    print(f"[INFO] Adding dynamic variables...")

    payload = {
        "conversation_config": {
            "agent": {
                "dynamic_variables": {
                    "user_id": {
                        "value": "test-user-id",
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
        f"{API_BASE}/agents/{AGENT_ID}",
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
    print("Meta-Nikita Server Tools Configuration")
    print("=" * 60)

    try:
        api_key = get_api_key()
        print(f"[OK] API key loaded (ends with ...{api_key[-4:]})")
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    tools = build_tools_config()
    print(f"[OK] Built {len(tools)} server tools configuration")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get current config
        try:
            current = await get_current_agent_config(client, api_key)
            print(f"[OK] Current agent: {current.get('name', 'Unknown')}")
            current_tools = current.get('conversation_config', {}).get('agent', {}).get('prompt', {}).get('tools', [])
            print(f"[INFO] Current tools: {len(current_tools)}")
            print(f"[INFO] Current prompt: {current.get('conversation_config', {}).get('agent', {}).get('prompt', {}).get('prompt', 'N/A')[:50]}...")
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to fetch agent: {e}")
            sys.exit(1)

        # Step 1: Update system prompt and first message
        try:
            await update_agent_prompt_and_first_message(client, api_key)
            print(f"[OK] System prompt and first message updated")
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to update prompt/first message: {e}")
            print(f"[ERROR] Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")

        # Step 2: Update with new tools
        try:
            result = await update_agent_tools(client, api_key, tools)
            print(f"[OK] Agent tools updated successfully")
            new_tools = result.get('conversation_config', {}).get('agent', {}).get('prompt', {}).get('tools', [])
            print(f"[INFO] New tools count: {len(new_tools)}")
            for tool in new_tools:
                print(f"  - {tool.get('name', 'Unknown')}: {tool.get('type', 'Unknown')}")
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to update agent tools: {e}")
            print(f"[ERROR] Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")

        # Step 3: Add dynamic variables
        try:
            dv_result = await add_dynamic_variables(client, api_key)
            if dv_result:
                print(f"[OK] Dynamic variables configured")
        except Exception as e:
            print(f"[WARN] Failed to add dynamic variables: {e}")

        # Fetch final config to verify
        try:
            final = await get_current_agent_config(client, api_key)
            final_tools = final.get('conversation_config', {}).get('agent', {}).get('prompt', {}).get('tools', [])
            final_prompt = final.get('conversation_config', {}).get('agent', {}).get('prompt', {}).get('prompt', '')
            final_first_msg = final.get('conversation_config', {}).get('agent', {}).get('first_message', '')
            print(f"\n[VERIFY] Final configuration:")
            print(f"  - Tools: {len(final_tools)}")
            print(f"  - Prompt starts with: {final_prompt[:60]}...")
            print(f"  - First message: {final_first_msg[:60]}...")
        except Exception as e:
            print(f"[WARN] Failed to verify final config: {e}")

    print("=" * 60)
    print("[DONE] Configuration complete!")
    print(f"[INFO] Agent ID: {AGENT_ID}")
    print(f"[INFO] Server Tool URL: {SERVER_TOOL_URL}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
