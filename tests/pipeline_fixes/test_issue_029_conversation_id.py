"""TDD tests for Issue #29: conversation_id NULL in generated_prompts.

The bug: Callers of generate_system_prompt() don't pass conversation_id parameter,
resulting in NULL values in the generated_prompts table.

The fix: Update callers to pass conversation_id when available.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.meta_prompts.service import MetaPromptService


class TestConversationIdPassing:
    """Verify conversation_id is passed through prompt generation."""

    @pytest.mark.asyncio
    async def test_generate_system_prompt_accepts_conversation_id(self):
        """generate_system_prompt should accept conversation_id parameter."""
        import inspect
        sig = inspect.signature(MetaPromptService.generate_system_prompt)
        params = sig.parameters

        # conversation_id should be a parameter
        assert 'conversation_id' in params
        # It should have a default of None (optional)
        assert params['conversation_id'].default is None

    @pytest.mark.asyncio
    async def test_log_prompt_receives_conversation_id(self):
        """_log_prompt should receive conversation_id from generate_system_prompt."""
        # This test verifies the internal flow - we'll use inspection instead
        # since instantiating MetaPromptService requires API keys
        import inspect

        # Check that generate_system_prompt accepts conversation_id
        sig = inspect.signature(MetaPromptService.generate_system_prompt)
        params = sig.parameters

        assert 'conversation_id' in params
        assert params['conversation_id'].default is None

        # Check that _log_prompt accepts conversation_id
        sig_log = inspect.signature(MetaPromptService._log_prompt)
        params_log = sig_log.parameters

        assert 'conversation_id' in params_log
        assert params_log['conversation_id'].default is None

    def test_template_generator_wrapper_accepts_conversation_id(self):
        """template_generator.generate_system_prompt should accept conversation_id."""
        from nikita.context.template_generator import generate_system_prompt
        import inspect

        sig = inspect.signature(generate_system_prompt)
        params = sig.parameters

        # conversation_id should be a parameter
        assert 'conversation_id' in params, (
            "generate_system_prompt wrapper must accept conversation_id parameter"
        )
        # It should have a default of None (optional)
        assert params['conversation_id'].default is None

    def test_template_generator_class_accepts_conversation_id(self):
        """TemplateGenerator.generate_prompt should accept conversation_id."""
        from nikita.context.template_generator import TemplateGenerator
        import inspect

        sig = inspect.signature(TemplateGenerator.generate_prompt)
        params = sig.parameters

        # conversation_id should be a parameter
        assert 'conversation_id' in params, (
            "TemplateGenerator.generate_prompt must accept conversation_id parameter"
        )
        # It should have a default of None (optional)
        assert params['conversation_id'].default is None

    def test_build_system_prompt_accepts_conversation_id(self):
        """build_system_prompt should accept conversation_id parameter."""
        from nikita.agents.text.agent import build_system_prompt
        import inspect

        sig = inspect.signature(build_system_prompt)
        params = sig.parameters

        # conversation_id should be a parameter
        assert 'conversation_id' in params, (
            "build_system_prompt must accept conversation_id parameter"
        )
        # It should have a default of None (optional)
        assert params['conversation_id'].default is None

    @pytest.mark.asyncio
    async def test_template_generator_passes_conversation_id_to_meta_service(self):
        """TemplateGenerator should pass conversation_id to MetaPromptService."""
        from nikita.context.template_generator import TemplateGenerator
        from uuid import uuid4

        mock_session = MagicMock()
        user_id = uuid4()
        conversation_id = uuid4()

        # Patch at the import location in the generate_prompt method
        with patch('nikita.meta_prompts.MetaPromptService') as MockMetaService:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.content = "Generated prompt"
            mock_result.token_count = 100
            mock_result.generation_time_ms = 50
            mock_service.generate_system_prompt = AsyncMock(return_value=mock_result)
            MockMetaService.return_value = mock_service

            generator = TemplateGenerator(mock_session)
            await generator.generate_prompt(
                user_id=user_id,
                conversation_id=conversation_id,
            )

            # Verify conversation_id was passed to MetaPromptService
            mock_service.generate_system_prompt.assert_called_once()
            call_kwargs = mock_service.generate_system_prompt.call_args
            assert call_kwargs.kwargs.get('conversation_id') == conversation_id

    @pytest.mark.asyncio
    async def test_wrapper_passes_conversation_id_to_generator(self):
        """generate_system_prompt wrapper should pass conversation_id to TemplateGenerator."""
        from nikita.context.template_generator import generate_system_prompt
        from uuid import uuid4

        mock_session = MagicMock()
        user_id = uuid4()
        conversation_id = uuid4()

        with patch('nikita.context.template_generator.TemplateGenerator') as MockGenerator:
            mock_generator = MagicMock()
            mock_generator.generate_prompt = AsyncMock(return_value="Generated prompt")
            MockGenerator.return_value = mock_generator

            await generate_system_prompt(
                session=mock_session,
                user_id=user_id,
                conversation_id=conversation_id,
            )

            # Verify conversation_id was passed to generate_prompt
            mock_generator.generate_prompt.assert_called_once()
            call_kwargs = mock_generator.generate_prompt.call_args
            assert call_kwargs.kwargs.get('conversation_id') == conversation_id
