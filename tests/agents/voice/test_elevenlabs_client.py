"""Tests for ElevenLabsConversationsClient — httpx-mocked unit tests (GAP-001)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from nikita.agents.voice.elevenlabs_client import (
    ConversationDetail, ConversationStatus, ElevenLabsConversationsClient,
    TranscriptTurn, get_elevenlabs_client,
)


@pytest.fixture
def client():
    return ElevenLabsConversationsClient(api_key="test-key")


def _resp(status_code=200, json_data=None):
    r = MagicMock(spec=httpx.Response)
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.raise_for_status = MagicMock()
    if status_code >= 400:
        r.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"{status_code}", request=MagicMock(), response=r)
    return r


class TestInit:
    def test_raises_without_api_key(self):
        with patch("nikita.agents.voice.elevenlabs_client.get_settings") as ms:
            ms.return_value = MagicMock(elevenlabs_api_key=None)
            with pytest.raises(ValueError, match="API key is required"):
                ElevenLabsConversationsClient()

    def test_uses_explicit_key(self, client):
        assert client.api_key == "test-key"


class TestListConversations:
    @pytest.mark.asyncio
    async def test_builds_query_params(self, client):
        r = _resp(json_data={"conversations": [], "has_more": False})
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=r) as mg:
            await client.list_conversations(agent_id="a1", limit=5, cursor="abc")
            p = mg.call_args[1]["params"]
            assert p["agent_id"] == "a1"
            assert p["page_size"] == 5
            assert p["cursor"] == "abc"

    @pytest.mark.asyncio
    async def test_handles_429(self, client):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_resp(429)):
            with pytest.raises(httpx.HTTPStatusError):
                await client.list_conversations()


class TestGetConversation:
    @pytest.mark.asyncio
    async def test_parses_transcript(self, client):
        r = _resp(json_data={
            "agent_id": "a1", "conversation_id": "c1", "status": "done",
            "transcript": [
                {"role": "user", "message": "Hello", "time_in_call_secs": 1.0},
                {"role": "agent", "message": "Hi!", "time_in_call_secs": 2.5, "end_time_in_call_secs": 4.0},
            ],
        })
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=r):
            d = await client.get_conversation("c1")
        assert len(d.transcript) == 2
        assert d.transcript[0].role == "user"
        assert d.transcript[1].end_time_in_call_secs == 4.0

    @pytest.mark.asyncio
    async def test_handles_404(self, client):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_resp(404)):
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_conversation("missing")


class TestGetAgentConfig:
    @pytest.mark.asyncio
    async def test_extracts_settings(self, client):
        r = _resp(json_data={
            "agent_id": "a1", "name": "Nikita",
            "conversation_config": {
                "llm": {"system_prompt": "You are Nikita"},
                "conversation": {"first_message": "Hey babe"},
                "tts": {"voice_id": "v-123"},
            },
        })
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=r):
            cfg = await client.get_agent_config("a1")
        assert cfg.system_prompt == "You are Nikita"
        assert cfg.first_message == "Hey babe"
        assert cfg.voice_id == "v-123"


class TestToTranscriptData:
    def test_maps_roles(self, client):
        detail = ConversationDetail(
            agent_id="a1", conversation_id="c1", status=ConversationStatus.DONE,
            transcript=[
                TranscriptTurn(role="agent", message="Hi", time_in_call_secs=0),
                TranscriptTurn(role="user", message="Hey", time_in_call_secs=1),
            ],
        )
        td = client.to_transcript_data(detail)
        assert td.entries[0].speaker == "nikita"
        assert td.entries[1].speaker == "user"
        assert td.nikita_turns == 1 and td.user_turns == 1

    def test_handles_empty(self, client):
        detail = ConversationDetail(
            agent_id="a1", conversation_id="c1", status=ConversationStatus.DONE,
            transcript=[],
        )
        td = client.to_transcript_data(detail)
        assert td.entries == [] and td.user_turns == 0 and td.nikita_turns == 0


class TestGetLatestConversation:
    @pytest.mark.asyncio
    async def test_returns_none_when_empty(self, client):
        r = _resp(json_data={"conversations": [], "has_more": False})
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=r):
            assert await client.get_latest_conversation(agent_id="a1") is None

    @pytest.mark.asyncio
    async def test_returns_detail_for_latest(self, client):
        list_r = _resp(json_data={"conversations": [{
            "agent_id": "a1", "conversation_id": "c-latest",
            "start_time_unix_secs": 100, "call_duration_secs": 60,
            "message_count": 5, "status": "done",
        }], "has_more": False})
        det_r = _resp(json_data={
            "agent_id": "a1", "conversation_id": "c-latest",
            "status": "done", "transcript": [],
        })
        n = 0

        async def side_effect(*a, **kw):
            nonlocal n; n += 1
            return list_r if n == 1 else det_r

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=side_effect):
            result = await client.get_latest_conversation(agent_id="a1")
        assert result is not None and result.conversation_id == "c-latest"


class TestSaveTranscriptToFile:
    @pytest.mark.asyncio
    async def test_writes_formatted(self, client, tmp_path):
        r = _resp(json_data={
            "agent_id": "a1", "conversation_id": "c1", "status": "done",
            "transcript": [
                {"role": "agent", "message": "Hello!", "time_in_call_secs": 0.0},
                {"role": "user", "message": "Hi", "time_in_call_secs": 1.5},
            ],
        })
        out = str(tmp_path / "transcript.md")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=r):
            path = await client.save_transcript_to_file("c1", out)
        assert path == out
        content = open(out).read()
        assert "**Nikita**" in content and "**User**" in content


class TestFactory:
    def test_creates_instance(self):
        assert isinstance(get_elevenlabs_client(api_key="k"), ElevenLabsConversationsClient)

    def test_passes_key(self):
        assert get_elevenlabs_client(api_key="custom").api_key == "custom"
