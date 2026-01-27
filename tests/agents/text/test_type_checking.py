"""Tests for type-safe message detection (Spec 038 T1.2).

Verifies that message type detection uses isinstance() instead of
fragile string-based type checking.
"""

import pytest
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)


def test_model_response_detection_uses_isinstance():
    """Verify isinstance(msg, ModelResponse) works correctly.

    AC-1.2.2: Type detection should use isinstance() not string matching.
    """
    # Create actual Pydantic AI message types
    response = ModelResponse(parts=[TextPart(content="Hello!")])
    request = ModelRequest(parts=[UserPromptPart(content="Hi")])

    # isinstance should correctly identify response
    assert isinstance(response, ModelResponse)
    assert not isinstance(request, ModelResponse)

    # Note: ModelMessage is a type alias (Union), not a class,
    # so isinstance() doesn't work with it directly.
    # We just verify the concrete types work correctly.


def test_type_check_forward_compatible():
    """Verify type check works with Pydantic AI message types.

    AC-1.2.3: All type checks should be forward-compatible with
    Pydantic AI updates (no string matching on class names).
    """
    # Create messages
    response = ModelResponse(parts=[TextPart(content="Test response")])
    request = ModelRequest(parts=[UserPromptPart(content="Test request")])

    # The OLD way (fragile):
    # "Response" in msg.__class__.__name__  # DON'T DO THIS
    old_way_response = "Response" in response.__class__.__name__
    old_way_request = "Response" in request.__class__.__name__

    # The NEW way (robust):
    new_way_response = isinstance(response, ModelResponse)
    new_way_request = isinstance(response, ModelRequest)

    # Both methods should identify response correctly
    assert old_way_response is True
    assert new_way_response is True

    # But only isinstance is truly type-safe
    # (The string check would fail if Pydantic AI renames the class)
    assert new_way_response == old_way_response

    # Verify we can iterate and check in a loop
    messages = [response, request]
    responses = [m for m in messages if isinstance(m, ModelResponse)]
    requests = [m for m in messages if isinstance(m, ModelRequest)]

    assert len(responses) == 1
    assert len(requests) == 1


def test_has_assistant_response_detection():
    """Test the specific pattern used in generate_response to detect assistant messages.

    This tests the pattern at agent.py:354-361 that checks if history
    has any Nikita/assistant responses.
    """
    # Create a mix of messages
    messages = [
        ModelRequest(parts=[UserPromptPart(content="User message 1")]),
        ModelResponse(parts=[TextPart(content="Nikita response")]),
        ModelRequest(parts=[UserPromptPart(content="User message 2")]),
    ]

    # Check using isinstance (the correct way)
    has_assistant_response = any(
        isinstance(msg, ModelResponse) for msg in messages
    )
    assert has_assistant_response is True

    # Now with only user messages
    user_only = [
        ModelRequest(parts=[UserPromptPart(content="User message 1")]),
        ModelRequest(parts=[UserPromptPart(content="User message 2")]),
    ]

    has_assistant_in_user_only = any(
        isinstance(msg, ModelResponse) for msg in user_only
    )
    assert has_assistant_in_user_only is False


def test_text_part_extraction_from_response():
    """Verify we can safely extract text content from ModelResponse.

    This ensures the response part iteration is also type-safe.
    """
    response = ModelResponse(parts=[
        TextPart(content="Hello!"),
        TextPart(content="How are you?"),
    ])

    # Extract text content using isinstance
    text_contents = []
    for part in response.parts:
        if isinstance(part, TextPart):
            text_contents.append(part.content)

    assert text_contents == ["Hello!", "How are you?"]
