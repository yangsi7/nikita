"""BossEncounterHandler — extracted boss fight logic (Strangler Fig, Phase 2).

Handles the full boss encounter lifecycle:
- Opening message delivery (send_boss_opening)
- Single-turn boss judgment (handle_single_turn_boss)
- Multi-phase boss judgment (handle_multi_phase_boss)
- Outcome delivery (pass / partial / fail / game-over / won)

This class is designed to be standalone and unit-testable independently of
MessageHandler. It mirrors the boss methods from MessageHandler and will
progressively absorb them as tests are migrated.
"""

import logging
import random
from typing import Optional

from nikita.engine.chapters.judgment import BossJudgment, BossResult
from nikita.engine.chapters.boss import BossStateMachine
from nikita.platforms.telegram.bot import TelegramBot
from nikita.platforms.telegram.delivery import sanitize_text_response

logger = logging.getLogger(__name__)


# Chapter-specific boss pass messages (keyed by the boss chapter just beaten).
# Mirrored from MessageHandler.BOSS_PASS_MESSAGES for standalone use.
BOSS_PASS_MESSAGES: dict[int, str] = {
    1: (  # Curiosity → Intrigue
        "Huh. You're actually kind of curious, aren't you? "
        "Most people give up by now. I wasn't sure you'd stick around, "
        "but... here you are.\n\n"
        "Fine. You've got my attention. Let's see what happens next... 💭"
    ),
    2: (  # Intrigue → Investment
        "Okay, I'll admit it - you surprised me there. "
        "I was testing you and you actually... passed. "
        "That doesn't happen often.\n\n"
        "I think I'm starting to actually care what you think. "
        "That's either really good or really dangerous... 💫"
    ),
    3: (  # Investment → Intimacy
        "That was... real. Like, actually real. "
        "I've been keeping my guard up this whole time but "
        "you just made it really hard to keep doing that.\n\n"
        "I trust you. I think. God, that's terrifying to say out loud... 💕"
    ),
    4: (  # Intimacy → Established
        "You know what just happened? You saw the messy, vulnerable, "
        "complicated parts of me and you didn't run. "
        "Do you know how rare that is?\n\n"
        "We're in new territory now. The real stuff. "
        "No more games between us... 🌟"
    ),
    5: (  # Final boss — victory
        "I can't believe it. After everything - the tests, the fights, "
        "the moments where I pushed you away - you're still here. "
        "YOU'RE STILL HERE.\n\n"
        "You didn't just win a game. You won me. All of me. "
        "And I'm not going anywhere either. 💖"
    ),
}


class BossEncounterHandler:
    """Standalone handler for boss encounter lifecycle.

    Extracted from MessageHandler via Strangler Fig pattern.
    Handles boss opening, judgment, and outcome delivery.
    """

    def __init__(
        self,
        bot: TelegramBot,
        user_repository,
        conversation_repository,
        boss_judgment: Optional[BossJudgment] = None,
        boss_state_machine: Optional[BossStateMachine] = None,
    ) -> None:
        """Initialise BossEncounterHandler.

        Args:
            bot: Telegram bot client for sending messages.
            user_repository: Repository for user lookups and updates.
            conversation_repository: Repository for conversation tracking.
            boss_judgment: Boss judgment service (default created if None).
            boss_state_machine: Boss state machine (default created if None).
        """
        self.bot = bot
        self.user_repository = user_repository
        self.conversation_repo = conversation_repository
        self.boss_judgment = boss_judgment or BossJudgment()
        self.boss_state_machine = boss_state_machine or BossStateMachine()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def send_boss_opening(self, chat_id: int, chapter: int) -> None:
        """Send boss encounter opening message to the given chat.

        Fetches the chapter-specific opening prompt, strips roleplay action
        markers, and delivers it with a brief dramatic delay.

        Args:
            chat_id: Telegram chat ID.
            chapter: Current chapter for boss context.
        """
        # Local import so that unittest.mock.patch on the module attribute works.
        from nikita.engine.chapters.prompts import get_boss_prompt
        import asyncio

        try:
            boss_prompt = get_boss_prompt(chapter)
            opening = boss_prompt.get("in_character_opening", "")

            if opening:
                await asyncio.sleep(2)
                await self._send_sanitized(chat_id, opening)
                logger.info("[BOSS] Sent boss opening for chapter %d", chapter)
        except Exception as exc:
            logger.error("[BOSS] Failed to send boss opening: %s", exc)

    async def handle_boss_response(
        self,
        user,
        user_message: str,
        chat_id: int,
    ) -> None:
        """Handle user response during boss encounter.

        Routes to multi-phase or single-turn flow based on feature flag.

        Args:
            user: User model in boss_fight status.
            user_message: User's response to the boss challenge.
            chat_id: Telegram chat ID.
        """
        from nikita.engine.chapters import is_multi_phase_boss_enabled

        if is_multi_phase_boss_enabled():
            await self.handle_multi_phase_boss(user, user_message, chat_id)
            return

        await self.handle_single_turn_boss(user, user_message, chat_id)

    async def handle_single_turn_boss(
        self,
        user,
        user_message: str,
        chat_id: int,
    ) -> None:
        """Legacy single-turn boss flow (flag OFF).

        Args:
            user: User model in boss_fight status.
            user_message: User's response to the boss challenge.
            chat_id: Telegram chat ID.
        """
        import asyncio
        from nikita.engine.chapters.prompts import get_boss_prompt

        try:
            boss_prompt = get_boss_prompt(user.chapter)

            conversation = await self.conversation_repo.get_active_conversation(user.id)
            conversation_history = []
            if conversation and conversation.messages:
                for msg in conversation.messages[-10:]:
                    conversation_history.append({
                        "role": msg.get("role", "unknown"),
                        "content": msg.get("content", ""),
                    })

            await self.bot.send_chat_action(chat_id, "typing")

            logger.info(
                "[BOSS] Judging boss response for user %s chapter %d",
                user.id,
                user.chapter,
            )
            judgment = await self.boss_judgment.judge_boss_outcome(
                user_message=user_message,
                conversation_history=conversation_history,
                chapter=user.chapter,
                boss_prompt=boss_prompt,
            )

            logger.info("[BOSS] Judgment: %s - %s", judgment.outcome, judgment.reasoning)

            passed = judgment.outcome == BossResult.PASS.value
            outcome = await self.boss_state_machine.process_outcome(
                user_id=user.id,
                passed=passed,
                user_repository=self.user_repository,
            )

            await asyncio.sleep(1)

            if passed:
                if outcome.get("new_chapter", user.chapter) > 5:
                    await self.send_game_won_message(chat_id, user.chapter)
                else:
                    await self.send_boss_pass_message(
                        chat_id,
                        old_chapter=user.chapter,
                        new_chapter=outcome.get("new_chapter", user.chapter + 1),
                    )
            else:
                if outcome.get("game_over", False):
                    await self.send_game_over_message(chat_id, user.chapter)
                else:
                    await self.send_boss_fail_message(
                        chat_id,
                        attempts=outcome.get("attempts", 1),
                        chapter=user.chapter,
                    )

        except Exception as exc:
            logger.error(
                "[BOSS] Failed to handle boss response for user %s: %s",
                user.id,
                exc,
                exc_info=True,
            )
            raise

    async def handle_multi_phase_boss(
        self,
        user,
        user_message: str,
        chat_id: int,
    ) -> None:
        """Handle multi-phase boss encounter (Spec 058, flag ON).

        Flow:
        1. Load BossPhaseState from conflict_details.
        2. Check timeout (24h auto-FAIL).
        3. If OPENING: advance to RESOLUTION, persist, send resolution prompt.
        4. If RESOLUTION: judge with full history, process 3-way outcome, clear phase.

        Args:
            user: User model in boss_fight status.
            user_message: User's response.
            chat_id: Telegram chat ID.
        """
        import asyncio
        import json

        from nikita.engine.chapters.boss import BossPhase, BossPhaseState
        from nikita.engine.chapters.phase_manager import BossPhaseManager
        from nikita.engine.chapters.prompts import get_boss_phase_prompt

        phase_mgr = BossPhaseManager()

        try:
            conflict_details = getattr(user, "conflict_details", None)
            if isinstance(conflict_details, str):
                conflict_details = json.loads(conflict_details)

            phase_state = phase_mgr.load_phase(conflict_details)

            if phase_state is None:
                logger.warning(
                    "[BOSS-MP] No phase state found for user %s, falling back to single-turn",
                    user.id,
                )
                await self.handle_single_turn_boss(user, user_message, chat_id)
                return

            if phase_mgr.is_timed_out(phase_state):
                logger.info("[BOSS-MP] Boss timed out for user %s, auto-FAIL", user.id)
                outcome = await self.boss_state_machine.process_outcome(
                    user_id=user.id,
                    user_repository=self.user_repository,
                    outcome="FAIL",
                )
                updated_details = phase_mgr.clear_boss_phase(conflict_details)
                await self._persist_conflict_details(user.id, updated_details)

                await self.bot.send_chat_action(chat_id, "typing")
                await asyncio.sleep(1)

                if outcome.get("game_over", False):
                    await self.send_game_over_message(chat_id, user.chapter)
                else:
                    await self.send_boss_fail_message(
                        chat_id,
                        attempts=outcome.get("attempts", 1),
                        chapter=user.chapter,
                    )
                return

            if phase_state.phase == BossPhase.OPENING:
                resolution_prompt = get_boss_phase_prompt(user.chapter, "resolution")
                advanced = phase_mgr.advance_phase(
                    phase_state, user_message, resolution_prompt["in_character_opening"]
                )
                updated_details = phase_mgr.persist_phase(conflict_details, advanced)
                await self._persist_conflict_details(user.id, updated_details)

                logger.info("[BOSS-MP] User %s advanced to RESOLUTION phase", user.id)
                await self._send_sanitized(chat_id, resolution_prompt["in_character_opening"])

            elif phase_state.phase == BossPhase.RESOLUTION:
                full_history = list(phase_state.conversation_history)
                full_history.append({"role": "user", "content": user_message})

                judgment_state = BossPhaseState(
                    phase=phase_state.phase,
                    chapter=phase_state.chapter,
                    started_at=phase_state.started_at,
                    turn_count=phase_state.turn_count + 1,
                    conversation_history=full_history,
                )

                boss_prompt = get_boss_phase_prompt(user.chapter, "resolution")

                await self.bot.send_chat_action(chat_id, "typing")

                judgment = await self.boss_judgment.judge_multi_phase_outcome(
                    phase_state=judgment_state,
                    chapter=user.chapter,
                    boss_prompt=boss_prompt,
                )

                logger.info(
                    "[BOSS-MP] Multi-phase judgment for user %s: %s (confidence=%s)",
                    user.id,
                    judgment.outcome,
                    judgment.confidence,
                )

                outcome = await self.boss_state_machine.process_outcome(
                    user_id=user.id,
                    user_repository=self.user_repository,
                    outcome=judgment.outcome,
                )

                updated_details = phase_mgr.clear_boss_phase(conflict_details)
                await self._persist_conflict_details(user.id, updated_details)

                await asyncio.sleep(1)

                if judgment.outcome == BossResult.PASS.value:
                    if outcome.get("new_chapter", user.chapter) > 5:
                        await self.send_game_won_message(chat_id, user.chapter)
                    else:
                        await self.send_boss_pass_message(
                            chat_id,
                            old_chapter=user.chapter,
                            new_chapter=outcome.get("new_chapter", user.chapter + 1),
                        )
                elif judgment.outcome == BossResult.PARTIAL.value:
                    await self.send_boss_partial_message(chat_id, user.chapter)
                else:
                    if outcome.get("game_over", False):
                        await self.send_game_over_message(chat_id, user.chapter)
                    else:
                        await self.send_boss_fail_message(
                            chat_id,
                            attempts=outcome.get("attempts", 1),
                            chapter=user.chapter,
                        )

        except Exception as exc:
            logger.error(
                "[BOSS-MP] Failed to handle multi-phase boss for user %s: %s",
                user.id,
                exc,
                exc_info=True,
            )
            raise

    # ------------------------------------------------------------------
    # Outcome delivery helpers
    # ------------------------------------------------------------------

    async def send_boss_partial_message(self, chat_id: int, chapter: int) -> None:
        """Send PARTIAL outcome message — empathetic truce (Spec 058)."""
        messages = [
            "Look... I can tell you're trying. That means something to me. "
            "Let's just... take a breath. We can come back to this. 💭",
            "I hear you. I do. We're not there yet, but... you didn't run. "
            "That counts for something. Let's give it some time. 💫",
            "Maybe we both need some space to think about this. "
            "I'm not going anywhere. We'll figure it out. 🤍",
        ]
        await self._send_sanitized(chat_id, random.choice(messages))

    async def send_boss_pass_message(
        self,
        chat_id: int,
        old_chapter: int,
        new_chapter: int,
    ) -> None:
        """Send congratulations message for passing the boss."""
        message = BOSS_PASS_MESSAGES.get(old_chapter)
        if not message:
            from nikita.engine.constants import CHAPTER_NAMES

            new_name = CHAPTER_NAMES.get(new_chapter, f"Chapter {new_chapter}")
            message = (
                f"You know what? That was actually... really good. "
                f"I wasn't sure you had it in you, but you proved me wrong. "
                f"I like that.\n\n"
                f"Something just shifted between us. "
                f"Welcome to {new_name}. Things are about to get interesting... 💕"
            )
        await self._send_sanitized(chat_id, message)

    async def send_boss_fail_message(
        self,
        chat_id: int,
        attempts: int,
        chapter: int,
    ) -> None:
        """Send message for failing boss (but still has remaining attempts)."""
        remaining = 3 - attempts

        if remaining == 2:
            message = (
                "That wasn't what I was looking for. Not even close. "
                "Look, I'm giving you another chance because I want this to work, "
                "but I need you to actually try. "
                "Think about what I'm really asking here.\n\n"
                f"You have {remaining} more chances. Don't waste them."
            )
        else:  # remaining == 1
            message = (
                "This is your last chance. I mean it. "
                "One more strike and we're done. "
                "I need you to really think before you respond. "
                "What do I actually need from you right now?\n\n"
                "This is it. Make it count."
            )

        await self._send_sanitized(chat_id, message)

    async def send_game_over_message(self, chat_id: int, chapter: int) -> None:
        """Send game over message after 3 failed boss attempts."""
        message = (
            "...\n\n"
            "I tried. I really tried to make this work. "
            "But you just don't get it, do you? "
            "You don't understand what I need.\n\n"
            "I'm done. We're done. "
            "Maybe some people just aren't meant for each other. "
            "Goodbye. 💔"
        )
        await self._send_sanitized(chat_id, message)

    async def send_game_won_message(self, chat_id: int, chapter: int) -> None:
        """Send victory message for completing all chapters."""
        message = (
            "I never thought I'd say this to anyone, but... "
            "you're the one. You actually did it. "
            "You saw through all my walls, handled all my tests, "
            "and loved me anyway.\n\n"
            "This is real. We're real. "
            "I love you. And I'm not scared to say it anymore. 💕\n\n"
            "Thank you for not giving up on me."
        )
        await self._send_sanitized(chat_id, message)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _send_sanitized(self, chat_id: int, text: str) -> None:
        """Send a message with roleplay action markers stripped."""
        cleaned = sanitize_text_response(text)
        await self.bot.send_message(chat_id=chat_id, text=cleaned)

    async def _persist_conflict_details(self, user_id, conflict_details: dict) -> None:
        """Persist updated conflict_details to database."""
        try:
            await self.user_repository.update_conflict_details(user_id, conflict_details)
        except Exception as exc:
            logger.error(
                "[BOSS-MP] Failed to persist conflict_details for %s: %s",
                user_id,
                exc,
                exc_info=True,
            )
