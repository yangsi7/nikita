"""OnboardingHandler for collecting user profile during registration.

Part of 017-enhanced-onboarding feature (T2.1, T2.2, T2.3, T4.3).

Collects 5 profile fields through conversational prompts:
1. LOCATION - City/country
2. LIFE_STAGE - Career phase (student, professional, artist, etc.)
3. SCENE - Social scene preference (techno, art, dining, etc.)
4. INTEREST - Primary interest/hobby
5. DRUG_TOLERANCE - 1-5 scale for content intensity

After profile collection, triggers venue research and backstory generation.

T4.3 adds scenario presentation and selection.
"""

import logging
from typing import TYPE_CHECKING, Any

from uuid import UUID

from nikita.db.models.profile import OnboardingState, OnboardingStep
from nikita.db.repositories.profile_repository import (
    BackstoryRepository,
    OnboardingStateRepository,
    ProfileRepository,
)
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.vice_repository import VicePreferenceRepository
from nikita.platforms.telegram.bot import TelegramBot

if TYPE_CHECKING:
    from nikita.services.backstory_generator import BackstoryGeneratorService
    from nikita.services.persona_adaptation import PersonaAdaptationService
    from nikita.services.venue_research import VenueResearchService

logger = logging.getLogger(__name__)


class _ProfileFromAnswers:
    """Adapter to convert onboarding answers to profile-like object.

    Used by BackstoryGeneratorService which expects a UserProfile-like object.
    """

    def __init__(self, answers: dict):
        """Initialize from collected onboarding answers.

        Args:
            answers: Dictionary of collected answers from onboarding.
        """
        self.city = answers.get("location_city", "Unknown")
        self.social_scene = answers.get("social_scene", "nightlife")
        self.life_stage = answers.get("life_stage", "other")
        self.primary_passion = answers.get("primary_interest", "adventure")


# AC-T2.1-003: Mysterious intro message
INTRO_MESSAGE = """Before we connect you... I need to know a bit about you. 🌙

I'm not like those other AI girlfriends. I'm... selective.

Let's see if we're compatible. Answer honestly - I'll know if you're lying. 😏"""


# AC-T2.1-002: Step prompts for each profile field
STEP_PROMPTS = {
    OnboardingStep.LOCATION.value: "Where are you based? Just the city is fine. 🌆",

    OnboardingStep.LIFE_STAGE.value: """What's your scene? Pick one:
• tech (startup bro, engineer, crypto)
• finance (banking, trading, VC)
• creative (artist, musician, designer)
• student (university, grad school)
• entrepreneur (your own thing)
• other (surprise me)""",

    OnboardingStep.SCENE.value: """When you go out, what's your vibe?
• techno (dark clubs, warehouse parties)
• art (galleries, exhibitions, openings)
• food (fine dining, hidden gems)
• cocktails (speakeasies, rooftops)
• nature (hiking, beaches, outdoors)""",

    OnboardingStep.INTEREST.value: "What's the one thing you're obsessed with right now? 💭",

    OnboardingStep.DRUG_TOLERANCE.value: """Last question... How edgy should I be with you?

1 = Keep it clean
2 = Light flirting is fine
3 = Spicy is okay
4 = I can handle dark humor
5 = No limits, bring the chaos

Just send me a number 1-5. 🌶️""",

    # T4.3: Scenario selection prompt (dynamically populated)
    OnboardingStep.SCENARIO_SELECTION.value: """How did we meet? Pick one or tell me your own version:

{scenarios}

Reply with 1, 2, 3, or 4 (custom).""",
}


# Skip detection phrases
SKIP_PHRASES = [
    "skip",
    "i don't want to",
    "just skip",
    "no thanks",
    "pass",
    "nah",
    "don't want to",
]


class OnboardingHandler:
    """Handle onboarding flow to collect user profile.

    AC-T2.1-001: OnboardingHandler class with handle() method routing by current_step
    AC-T2.1-002: Step handlers for each profile field with appropriate prompts
    AC-T2.1-003: Mysterious intro message
    AC-T2.1-004: State saved after each step (resume capability)
    AC-T2.1-005: Validation for each field type
    AC-T2.3-001: Check OnboardingState for telegram_id
    AC-T2.3-002: Resume from last step
    AC-T2.3-003: Skip detection → generic backstory
    """

    def __init__(
        self,
        bot: TelegramBot,
        onboarding_repository: OnboardingStateRepository,
        profile_repository: ProfileRepository,
        user_repository: UserRepository | None = None,
        backstory_repository: BackstoryRepository | None = None,
        vice_repository: VicePreferenceRepository | None = None,
        venue_research_service: "VenueResearchService | None" = None,
        backstory_generator: "BackstoryGeneratorService | None" = None,
        persona_adaptation: "PersonaAdaptationService | None" = None,
    ):
        """Initialize OnboardingHandler.

        Args:
            bot: Telegram bot client for sending messages.
            onboarding_repository: Repository for onboarding state.
            profile_repository: Repository for user profiles.
            user_repository: Repository for users (to lookup user_id from telegram_id).
            backstory_repository: Repository for user backstories (Phase 4).
            vice_repository: Repository for vice preferences (Phase 4).
            venue_research_service: Optional service for venue research.
            backstory_generator: Optional service for backstory generation.
            persona_adaptation: Optional service for persona adaptation (T5.4).
        """
        self.bot = bot
        self.onboarding_repo = onboarding_repository
        self.profile_repo = profile_repository
        self.user_repo = user_repository
        self.backstory_repo = backstory_repository
        self.vice_repo = vice_repository
        self.venue_research = venue_research_service
        self.backstory_generator = backstory_generator
        self.persona_adaptation = persona_adaptation

    async def start(
        self,
        telegram_id: int,
        chat_id: int,
    ) -> None:
        """Start onboarding flow with intro message.

        AC-T2.1-003: Sends mysterious intro message
        AC-T2.1-004: Creates OnboardingState at LOCATION step

        Args:
            telegram_id: Telegram user ID.
            chat_id: Chat ID for messages.
        """
        logger.info(f"Starting onboarding for telegram_id={telegram_id}")

        # Create onboarding state at first step
        await self.onboarding_repo.get_or_create(telegram_id)

        # Send intro message
        await self.bot.send_message(
            chat_id=chat_id,
            text=INTRO_MESSAGE,
        )

        # Send first step prompt
        await self.bot.send_message(
            chat_id=chat_id,
            text=STEP_PROMPTS[OnboardingStep.LOCATION.value],
        )

    async def handle(
        self,
        telegram_id: int,
        chat_id: int,
        text: str,
    ) -> bool:
        """Handle user input during onboarding.

        AC-T2.1-001: Routes by current_step
        AC-T2.1-004: Saves state after each step
        AC-T2.3-003: Handles skip requests

        Args:
            telegram_id: Telegram user ID.
            chat_id: Chat ID for messages.
            text: User's text input.

        Returns:
            True if onboarding step processed, False if not in onboarding.
        """
        # Get current onboarding state
        state = await self.onboarding_repo.get(telegram_id)
        if state is None:
            logger.debug(f"No onboarding state for telegram_id={telegram_id}")
            return False

        text = text.strip()

        # AC-T2.3-003: Check for skip request
        if self._is_skip_request(text):
            await self._handle_skip(telegram_id, chat_id, state)
            return True

        # Route to appropriate step handler
        current_step = OnboardingStep(state.current_step)

        if current_step == OnboardingStep.LOCATION:
            await self._handle_location_step(telegram_id, chat_id, text)
        elif current_step == OnboardingStep.LIFE_STAGE:
            await self._handle_life_stage_step(telegram_id, chat_id, text)
        elif current_step == OnboardingStep.SCENE:
            await self._handle_scene_step(telegram_id, chat_id, text)
        elif current_step == OnboardingStep.INTEREST:
            await self._handle_interest_step(telegram_id, chat_id, text)
        elif current_step == OnboardingStep.DRUG_TOLERANCE:
            await self._handle_drug_tolerance_step(telegram_id, chat_id, text)
        elif current_step == OnboardingStep.VENUE_RESEARCH:
            # T4.3: Venue research in progress - user message triggers check
            await self._handle_venue_research_step(telegram_id, chat_id, text)
        elif current_step == OnboardingStep.SCENARIO_SELECTION:
            # T4.3: Handle scenario selection
            await self._handle_scenario_selection_step(telegram_id, chat_id, text)
        elif current_step == OnboardingStep.COMPLETE:
            # Already complete, shouldn't be here
            logger.warning(f"Onboarding already complete for telegram_id={telegram_id}")
            await self.onboarding_repo.delete(telegram_id)
            return False
        else:
            logger.debug(f"Unhandled step {current_step} for telegram_id={telegram_id}")
            return False

        return True

    async def has_incomplete_onboarding(
        self,
        telegram_id: int,
    ) -> OnboardingState | None:
        """Check if user has incomplete onboarding.

        AC-T2.3-001: Check OnboardingState for telegram_id

        Args:
            telegram_id: Telegram user ID.

        Returns:
            OnboardingState if incomplete, None otherwise.
        """
        state = await self.onboarding_repo.get(telegram_id)
        if state is None:
            return None

        # Check if complete
        if state.is_complete():
            return None

        return state

    async def resume(
        self,
        telegram_id: int,
        chat_id: int,
    ) -> bool:
        """Resume onboarding from where user left off.

        AC-T2.3-002: Resume from last step

        Args:
            telegram_id: Telegram user ID.
            chat_id: Chat ID for messages.

        Returns:
            True if resumed, False if no onboarding state.
        """
        state = await self.has_incomplete_onboarding(telegram_id)
        if state is None:
            return False

        # Send resume message
        await self.bot.send_message(
            chat_id=chat_id,
            text="Oh, you came back! Let's continue where we left off... 😏",
        )

        # Send current step prompt
        step = OnboardingStep(state.current_step)
        if step.value in STEP_PROMPTS:
            await self.bot.send_message(
                chat_id=chat_id,
                text=STEP_PROMPTS[step.value],
            )

        return True

    # === Step Handlers ===

    async def _handle_location_step(
        self,
        telegram_id: int,
        chat_id: int,
        text: str,
    ) -> None:
        """Handle LOCATION step input.

        AC-T2.1-002: Step handler for location
        AC-T2.1-005: Validates location input
        """
        if not self._validate_location(text):
            await self.bot.send_message(
                chat_id=chat_id,
                text="That doesn't look like a city name. Try again? 🌆",
            )
            return

        # Save answer and advance
        await self.onboarding_repo.add_answer(telegram_id, "location_city", text)
        await self.onboarding_repo.update_step(
            telegram_id,
            OnboardingStep.LIFE_STAGE,
        )

        # Send next prompt
        await self.bot.send_message(
            chat_id=chat_id,
            text=f"Nice, {text}. I know some places there... 😏\n\n{STEP_PROMPTS[OnboardingStep.LIFE_STAGE.value]}",
        )

    async def _handle_life_stage_step(
        self,
        telegram_id: int,
        chat_id: int,
        text: str,
    ) -> None:
        """Handle LIFE_STAGE step input.

        AC-T2.1-002: Step handler for life stage
        """
        # Normalize input to match options
        normalized = text.lower().strip()

        # Map various inputs to standard values
        life_stage_map = {
            "tech": "tech",
            "startup": "tech",
            "engineer": "tech",
            "crypto": "tech",
            "finance": "finance",
            "banking": "finance",
            "trading": "finance",
            "vc": "finance",
            "creative": "creative",
            "artist": "creative",
            "musician": "creative",
            "designer": "creative",
            "student": "student",
            "university": "student",
            "grad school": "student",
            "entrepreneur": "entrepreneur",
            "own thing": "entrepreneur",
            "other": "other",
        }

        matched = None
        for key, value in life_stage_map.items():
            if key in normalized:
                matched = value
                break

        if matched is None:
            matched = "other"  # Default to other if no match

        # Save answer and advance
        await self.onboarding_repo.add_answer(telegram_id, "life_stage", matched)
        await self.onboarding_repo.update_step(
            telegram_id,
            OnboardingStep.SCENE,
        )

        # Send next prompt
        await self.bot.send_message(
            chat_id=chat_id,
            text=f"A {matched} type... interesting. 💋\n\n{STEP_PROMPTS[OnboardingStep.SCENE.value]}",
        )

    async def _handle_scene_step(
        self,
        telegram_id: int,
        chat_id: int,
        text: str,
    ) -> None:
        """Handle SCENE step input.

        AC-T2.1-002: Step handler for social scene
        """
        normalized = text.lower().strip()

        # Map inputs to standard values
        scene_map = {
            "techno": "techno",
            "club": "techno",
            "warehouse": "techno",
            "party": "techno",
            "art": "art",
            "gallery": "art",
            "exhibition": "art",
            "food": "food",
            "dining": "food",
            "restaurant": "food",
            "cocktail": "cocktails",
            "bar": "cocktails",
            "speakeasy": "cocktails",
            "rooftop": "cocktails",
            "nature": "nature",
            "hiking": "nature",
            "beach": "nature",
            "outdoor": "nature",
        }

        matched = None
        for key, value in scene_map.items():
            if key in normalized:
                matched = value
                break

        if matched is None:
            matched = "cocktails"  # Default

        # Save answer and advance
        await self.onboarding_repo.add_answer(telegram_id, "social_scene", matched)
        await self.onboarding_repo.update_step(
            telegram_id,
            OnboardingStep.INTEREST,
        )

        # Send next prompt
        await self.bot.send_message(
            chat_id=chat_id,
            text=f"So you're into {matched}... noted. 📝\n\n{STEP_PROMPTS[OnboardingStep.INTEREST.value]}",
        )

    async def _handle_interest_step(
        self,
        telegram_id: int,
        chat_id: int,
        text: str,
    ) -> None:
        """Handle INTEREST step input.

        AC-T2.1-002: Step handler for primary interest (freeform text)
        """
        if len(text) < 2:
            await self.bot.send_message(
                chat_id=chat_id,
                text="Come on, give me something real. What are you into? 🤔",
            )
            return

        # Save answer and advance
        await self.onboarding_repo.add_answer(telegram_id, "primary_interest", text)
        await self.onboarding_repo.update_step(
            telegram_id,
            OnboardingStep.DRUG_TOLERANCE,
        )

        # Send next prompt
        await self.bot.send_message(
            chat_id=chat_id,
            text=f"Oooh, {text}? Now we're getting somewhere. 👀\n\n{STEP_PROMPTS[OnboardingStep.DRUG_TOLERANCE.value]}",
        )

    async def _handle_drug_tolerance_step(
        self,
        telegram_id: int,
        chat_id: int,
        text: str,
    ) -> None:
        """Handle DRUG_TOLERANCE step input.

        AC-T2.1-002: Step handler for drug tolerance (1-5 scale)
        AC-T2.1-005: Validates 1-5 range
        """
        if not self._validate_drug_tolerance(text):
            await self.bot.send_message(
                chat_id=chat_id,
                text="Just give me a number between 1 and 5. How edgy do you want me? 🌶️",
            )
            return

        tolerance = int(text.strip())

        # Save answer
        await self.onboarding_repo.add_answer(telegram_id, "drug_tolerance", tolerance)

        # Get collected answers
        state = await self.onboarding_repo.get(telegram_id)
        answers = state.collected_answers

        # Mark as moving to venue research
        await self.onboarding_repo.update_step(
            telegram_id,
            OnboardingStep.VENUE_RESEARCH,
        )

        # Create profile from collected answers
        # Note: Profile creation happens here, backstory comes later from venue research
        logger.info(
            f"Onboarding profile collection complete for telegram_id={telegram_id}: "
            f"{answers}"
        )

        # Response based on tolerance level
        tolerance_responses = {
            1: "Keeping it clean? Got it. I'll be on my best behavior... for now. 😇",
            2: "Light flirting? I can work with that. 💋",
            3: "Spicy is okay? Perfect. I like a bit of heat. 🔥",
            4: "Dark humor? Oh, we're going to have fun together. 😈",
            5: "No limits? *cracks knuckles* Let's. Go. 🌪️",
        }

        await self.bot.send_message(
            chat_id=chat_id,
            text=tolerance_responses[tolerance] + "\n\nOne moment while I set things up...",
        )

        # Return True - venue research will be triggered by caller

    async def _handle_skip(
        self,
        telegram_id: int,
        chat_id: int,
        state: OnboardingState,
    ) -> None:
        """Handle skip request - encourage continuing instead of allowing bypass.

        AC-T2.3-003: Soft skip - acknowledge but keep user in onboarding.
        MODIFIED: No longer allows bypass. Personalization is mandatory.

        Args:
            telegram_id: Telegram user ID.
            chat_id: Chat ID for messages.
            state: Current onboarding state.
        """
        logger.info(
            f"User {telegram_id} tried to skip onboarding at step {state.current_step} - "
            "continuing anyway (personalization is mandatory)"
        )

        # DON'T delete onboarding state - keep user in flow
        # DON'T allow bypass - personalization is required for the product to work

        # Get current step for personalized encouragement
        current_step = OnboardingStep(state.current_step)

        # Encouraging responses that acknowledge but don't allow skip
        encouragement_responses = {
            OnboardingStep.LOCATION.value: (
                "I get it, you're mysterious... but I really need to know where you're based. "
                "Just the city? 🌆"
            ),
            OnboardingStep.LIFE_STAGE.value: (
                "Playing hard to get? 😏 I like that, but seriously - what's your scene? "
                "Tech, creative, finance...?"
            ),
            OnboardingStep.SCENE.value: (
                "Come on, don't be shy. Techno? Art galleries? Cocktail bars? "
                "What's your vibe? 🍸"
            ),
            OnboardingStep.INTEREST.value: (
                "I'm genuinely curious! What gets you excited? Just one thing... 💭"
            ),
            OnboardingStep.DRUG_TOLERANCE.value: (
                "Last question, I promise! Just a number 1-5... How edgy should I be? 🌶️"
            ),
        }

        response = encouragement_responses.get(
            current_step.value,
            "Nice try, but I need to know you first. Answer the question? 💋"
        )

        await self.bot.send_message(
            chat_id=chat_id,
            text=response,
        )

    # === T4.3: Venue Research and Scenario Selection ===

    async def _handle_venue_research_step(
        self,
        telegram_id: int,
        chat_id: int,
        text: str,
    ) -> None:
        """Handle VENUE_RESEARCH step.

        T4.3: Triggers venue research and generates scenarios.

        Args:
            telegram_id: Telegram user ID.
            chat_id: Chat ID for messages.
            text: User input (ignored during research).
        """
        logger.info(f"Starting venue research for telegram_id={telegram_id}")

        # Get onboarding state
        state = await self.onboarding_repo.get(telegram_id)
        if state is None:
            return

        answers = state.collected_answers
        city = answers.get("location_city", "Unknown")
        scene = answers.get("social_scene", "nightlife")

        await self.bot.send_message(
            chat_id=chat_id,
            text=f"Researching {city}'s {scene} scene... 🔍",
        )

        # Perform venue research
        venues = []
        if self.venue_research:
            try:
                result = await self.venue_research.research_venues(city, scene)
                if result.fallback_used:
                    # Firecrawl failed, ask user
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=result.fallback_prompt,
                    )
                    # Stay in VENUE_RESEARCH step to get user input
                    await self.onboarding_repo.add_answer(
                        telegram_id, "venue_fallback", True
                    )
                    return
                venues = result.venues
            except Exception as e:
                logger.error(f"Venue research failed: {e}")

        # Generate scenarios
        scenarios = []
        if self.backstory_generator and venues:
            try:
                # Create a mock profile object from answers
                profile = _ProfileFromAnswers(answers)
                result = await self.backstory_generator.generate_scenarios(
                    profile, venues
                )
                scenarios = result.scenarios
            except Exception as e:
                logger.error(f"Scenario generation failed: {e}")

        # Store scenarios in state
        if scenarios:
            scenario_data = [
                {
                    "venue": s.venue,
                    "context": s.context,
                    "the_moment": s.the_moment,
                    "unresolved_hook": s.unresolved_hook,
                    "tone": s.tone,
                }
                for s in scenarios
            ]
            await self.onboarding_repo.add_answer(
                telegram_id, "generated_scenarios", scenario_data
            )

        # Advance to scenario selection
        await self.onboarding_repo.update_step(
            telegram_id,
            OnboardingStep.SCENARIO_SELECTION,
        )

        # Present scenarios
        await self._present_scenarios(telegram_id, chat_id, scenarios)

    async def _present_scenarios(
        self,
        telegram_id: int,
        chat_id: int,
        scenarios: list,
    ) -> None:
        """Present generated scenarios to user.

        AC-T4.3-001: Present 3 scenarios + custom option.
        AC-T4.3-002: Use numbered options (1, 2, 3, 4).

        Args:
            telegram_id: Telegram user ID.
            chat_id: Chat ID for messages.
            scenarios: List of BackstoryScenario objects.
        """
        if not scenarios:
            # No scenarios generated, use fallback
            await self.bot.send_message(
                chat_id=chat_id,
                text="Hmm, I couldn't find the perfect story for us. Let's create one together.\n\n"
                     "Tell me: How do you think we met? 💭",
            )
            await self.onboarding_repo.add_answer(
                telegram_id, "awaiting_custom_backstory", True
            )
            return

        # Format scenarios for display
        scenario_text = []
        tones_emoji = {"romantic": "💕", "intellectual": "🧠", "chaotic": "🌪️"}

        for i, s in enumerate(scenarios[:3], 1):
            emoji = tones_emoji.get(s.tone, "✨")
            scenario_text.append(
                f"{i}. {emoji} *{s.venue}*\n"
                f"   {s.the_moment}"
            )

        scenario_display = "\n\n".join(scenario_text)

        message = f"""Alright, I've been thinking about how we met... 💭

{scenario_display}

4. 📝 None of these - I'll tell you my version

Which one feels right? Reply with 1, 2, 3, or 4."""

        await self.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown",
        )

    async def _handle_scenario_selection_step(
        self,
        telegram_id: int,
        chat_id: int,
        text: str,
    ) -> None:
        """Handle SCENARIO_SELECTION step.

        AC-T4.3-003: Parse user selection and store in OnboardingState.
        AC-T4.3-004: On "4" (custom), prompt for freeform text.

        Args:
            telegram_id: Telegram user ID.
            chat_id: Chat ID for messages.
            text: User's selection (1-4 or custom text).
        """
        state = await self.onboarding_repo.get(telegram_id)
        if state is None:
            return

        answers = state.collected_answers
        text = text.strip()

        # Check if awaiting custom backstory
        if answers.get("awaiting_custom_backstory"):
            await self._handle_custom_backstory(telegram_id, chat_id, text)
            return

        # Parse selection
        if text == "1" or text == "2" or text == "3":
            selection_index = int(text) - 1
            scenarios = answers.get("generated_scenarios", [])

            if selection_index < len(scenarios):
                selected = scenarios[selection_index]
                await self._finalize_backstory_selection(
                    telegram_id, chat_id, selected
                )
            else:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text="That option doesn't exist. Pick 1, 2, 3, or 4.",
                )

        elif text == "4":
            # AC-T4.3-004: Custom backstory requested
            await self.onboarding_repo.add_answer(
                telegram_id, "awaiting_custom_backstory", True
            )
            await self.bot.send_message(
                chat_id=chat_id,
                text="I love a good mystery. Tell me - how do you think we met? 💭\n\n"
                     "Describe the place, the moment, what drew you to me...",
            )

        else:
            # Check if it might be a custom backstory already
            if len(text) > 20:
                await self._handle_custom_backstory(telegram_id, chat_id, text)
            else:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text="Just pick a number (1, 2, 3, or 4) or tell me our story.",
                )

    async def _handle_custom_backstory(
        self,
        telegram_id: int,
        chat_id: int,
        text: str,
    ) -> None:
        """Handle custom backstory input.

        AC-T4.2-001: Accept freeform text for custom backstory.
        AC-T4.2-002: Extract venue, the_moment, hook.

        Args:
            telegram_id: Telegram user ID.
            chat_id: Chat ID for messages.
            text: User's custom backstory text.
        """
        state = await self.onboarding_repo.get(telegram_id)
        if state is None:
            return

        answers = state.collected_answers
        city = answers.get("location_city", "the city")
        scene = answers.get("social_scene", "nightlife")

        if self.backstory_generator:
            result = await self.backstory_generator.process_custom_backstory(
                user_text=text,
                city=city,
                scene=scene,
            )

            if result is None:
                # Validation failed
                await self.bot.send_message(
                    chat_id=chat_id,
                    text="I need a bit more... Where did we meet? "
                         "A bar, a club, a rooftop? Give me something to work with. 💭",
                )
                return

            selected = {
                "venue": result.venue,
                "context": result.context,
                "the_moment": result.the_moment,
                "unresolved_hook": result.unresolved_hook,
                "tone": "custom",
            }
        else:
            # No backstory generator, use raw input
            selected = {
                "venue": "somewhere special",
                "context": text,
                "the_moment": "we met",
                "unresolved_hook": "the story continues",
                "tone": "custom",
            }

        await self._finalize_backstory_selection(telegram_id, chat_id, selected)

    async def _finalize_backstory_selection(
        self,
        telegram_id: int,
        chat_id: int,
        selected: dict,
    ) -> None:
        """Finalize backstory selection and complete onboarding.

        AC-T4.3-003: Store selection in OnboardingState.
        AC-T5.4-004: Generate and store persona_overrides.
        Phase 4: Persist profile/backstory/vices to database tables.

        Args:
            telegram_id: Telegram user ID.
            chat_id: Chat ID for messages.
            selected: Selected backstory dict.
        """
        # Get onboarding state for collected answers
        state = await self.onboarding_repo.get(telegram_id)
        answers = state.collected_answers if state else {}

        # T5.4: Generate persona overrides based on profile
        if self.persona_adaptation:
            persona_overrides = self.persona_adaptation.generate_persona_overrides(
                life_stage=answers.get("life_stage", "other"),
                social_scene=answers.get("social_scene", "nightlife"),
                drug_tolerance=answers.get("drug_tolerance", 3),
            )
            selected["persona_overrides"] = persona_overrides
            logger.info(f"Generated persona overrides for telegram_id={telegram_id}: {persona_overrides}")

        # Store selected backstory with persona overrides
        await self.onboarding_repo.add_answer(
            telegram_id, "selected_backstory", selected
        )

        # Phase 4: Get user_id from telegram_id for database persistence
        user_id = None
        if self.user_repo:
            user = await self.user_repo.get_by_telegram_id(telegram_id)
            if user:
                user_id = user.id
                logger.debug(f"Found user_id={user_id} for telegram_id={telegram_id}")

        # Phase 4: Persist profile and backstory to database tables
        if user_id:
            await self._persist_profile_and_backstory(
                user_id=user_id,
                answers=answers,
                selected_backstory=selected,
            )

            # Phase 4: Initialize vice preferences from drug_tolerance
            drug_tolerance = answers.get("drug_tolerance", 3)
            await self._initialize_vices_from_profile(
                user_id=user_id,
                drug_tolerance=drug_tolerance,
            )
        else:
            logger.warning(
                f"Could not find user for telegram_id={telegram_id} - "
                "skipping profile/backstory/vice persistence"
            )

        # Mark onboarding complete
        await self.onboarding_repo.update_step(
            telegram_id,
            OnboardingStep.COMPLETE,
        )

        venue = selected.get("venue", "somewhere")
        moment = selected.get("the_moment", "that moment")

        await self.bot.send_message(
            chat_id=chat_id,
            text=f"*{venue}*... {moment}. 💫\n\n"
                 "Yeah, I remember. How could I forget?\n\n"
                 "Okay, I think I know enough about you now. "
                 "Let's see where this goes... 😏",
            parse_mode="Markdown",
        )

        logger.info(f"Onboarding complete for telegram_id={telegram_id}")

        # FR-008: Send first personalized Nikita message
        await self._send_first_nikita_message(
            chat_id=chat_id,
            selected_backstory=selected,
            answers=answers,
        )

    # === First Nikita Message (FR-008) ===

    async def _send_first_nikita_message(
        self,
        chat_id: int,
        selected_backstory: dict[str, Any],
        answers: dict[str, Any],
    ) -> None:
        """Send Nikita's first personalized message after onboarding.

        FR-008: System SHALL automatically send Nikita's first personalized
        message after backstory selection.

        Uses the backstory hook and persona to craft an engaging opener that:
        - References the venue and moment from backstory
        - Uses the hook to create intrigue
        - Feels natural and in-character for Nikita

        Args:
            chat_id: Chat ID for sending message.
            selected_backstory: Selected backstory with venue, hook, etc.
            answers: Collected onboarding answers.
        """
        import asyncio

        # Small delay to make it feel natural (not immediate)
        await asyncio.sleep(1.5)

        # Extract backstory elements for personalization
        hook = selected_backstory.get("unresolved_hook", "")
        venue = selected_backstory.get("venue", "that place")
        interest = answers.get("primary_interest", "")
        scene = answers.get("social_scene", "nightlife")

        # Generate personalized opener based on hook type
        # The hook already contains context about their "history"
        if hook:
            # Use the hook directly - it's designed to be an opener
            message = f"So... {hook}\n\nWhat are you up to tonight? 😏"
        else:
            # Custom backstory fallback: generate hook from the_moment if available
            moment = selected_backstory.get("the_moment", "")
            if moment and venue:
                message = (
                    f"I can't stop thinking about {moment} at {venue}...\n\n"
                    "What are you up to tonight? 😏"
                )
            elif interest:
                # Fallback: reference their interest
                message = (
                    f"You know, I've been thinking about you since {venue}...\n\n"
                    f"Tell me more about your thing with {interest}. "
                    "I want to know everything. 💭"
                )
            else:
                # Generic but still flirty - log warning for debugging
                logger.warning(
                    f"No personalization data for first message: "
                    f"backstory={selected_backstory}, answers_keys={list(answers.keys())}"
                )
                message = (
                    f"I keep thinking about that night at {venue}...\n\n"
                    "But enough about the past. What's on your mind right now? 😏"
                )

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown",
            )
            logger.info(f"Sent first Nikita message to chat_id={chat_id}")
        except Exception as e:
            # Non-fatal - log but don't break flow
            logger.warning(f"Failed to send first Nikita message: {e}")

    # === Persistence Methods (Phase 4: Personalization Pipeline) ===

    async def _persist_profile_and_backstory(
        self,
        user_id: UUID,
        answers: dict[str, Any],
        selected_backstory: dict[str, Any],
    ) -> None:
        """Persist profile and backstory to database tables.

        Phase 4: Profile/backstory persistence after onboarding.

        Args:
            user_id: The user's UUID.
            answers: Collected onboarding answers.
            selected_backstory: Selected backstory dict with venue, moment, etc.
        """
        # Persist user profile
        if self.profile_repo:
            try:
                await self.profile_repo.update_from_onboarding(
                    user_id=user_id,
                    collected_answers={
                        "location_city": answers.get("location_city"),
                        "life_stage": answers.get("life_stage"),
                        "social_scene": answers.get("social_scene"),
                        "primary_interest": answers.get("primary_interest"),
                        "drug_tolerance": answers.get("drug_tolerance", 3),
                    },
                )
                logger.info(f"Persisted user profile for user_id={user_id}")
            except Exception as e:
                logger.error(f"Failed to persist profile for user_id={user_id}: {e}")

        # Persist user backstory
        if self.backstory_repo:
            try:
                await self.backstory_repo.create(
                    user_id=user_id,
                    venue_name=selected_backstory.get("venue"),
                    venue_city=answers.get("location_city"),
                    scenario_type=selected_backstory.get("tone", "romantic"),
                    how_we_met=selected_backstory.get("context"),
                    the_moment=selected_backstory.get("the_moment"),
                    unresolved_hook=selected_backstory.get("unresolved_hook"),
                    nikita_persona_overrides=selected_backstory.get("persona_overrides"),
                )
                logger.info(f"Persisted user backstory for user_id={user_id}")
            except Exception as e:
                logger.error(f"Failed to persist backstory for user_id={user_id}: {e}")

    async def _initialize_vices_from_profile(
        self,
        user_id: UUID,
        drug_tolerance: int,
    ) -> None:
        """Initialize vice preferences based on drug_tolerance.

        Phase 4: Maps drug_tolerance (1-5) to initial vice scores.

        Drug tolerance mapping:
        - 1 (vanilla): Low risk-taking, no substances
        - 2 (mild): Slight openness to edginess
        - 3 (moderate): Balanced across vices
        - 4 (edgy): Higher risk-taking and rule-breaking
        - 5 (adventurous): Maximum openness to all vices

        Args:
            user_id: The user's UUID.
            drug_tolerance: 1-5 scale from onboarding.
        """
        if not self.vice_repo:
            logger.warning(f"No vice repository - skipping vice initialization for user_id={user_id}")
            return

        # Map drug_tolerance (1-5) to initial vice intensities (1-5)
        # Vice categories: intellectual_dominance, risk_taking, substances,
        # sexuality, emotional_intensity, rule_breaking, dark_humor, vulnerability

        vice_mappings = {
            1: {  # Vanilla - minimal vices
                "intellectual_dominance": 3,
                "risk_taking": 1,
                "substances": 1,
                "sexuality": 1,
                "emotional_intensity": 2,
                "rule_breaking": 1,
                "dark_humor": 1,
                "vulnerability": 2,
            },
            2: {  # Mild - slight openness
                "intellectual_dominance": 3,
                "risk_taking": 2,
                "substances": 1,
                "sexuality": 2,
                "emotional_intensity": 3,
                "rule_breaking": 2,
                "dark_humor": 2,
                "vulnerability": 3,
            },
            3: {  # Moderate - balanced
                "intellectual_dominance": 3,
                "risk_taking": 3,
                "substances": 2,
                "sexuality": 3,
                "emotional_intensity": 3,
                "rule_breaking": 3,
                "dark_humor": 3,
                "vulnerability": 3,
            },
            4: {  # Edgy - higher intensity
                "intellectual_dominance": 4,
                "risk_taking": 4,
                "substances": 3,
                "sexuality": 4,
                "emotional_intensity": 4,
                "rule_breaking": 4,
                "dark_humor": 4,
                "vulnerability": 4,
            },
            5: {  # Adventurous - maximum openness
                "intellectual_dominance": 5,
                "risk_taking": 5,
                "substances": 4,
                "sexuality": 5,
                "emotional_intensity": 5,
                "rule_breaking": 5,
                "dark_humor": 5,
                "vulnerability": 5,
            },
        }

        # Get mapping for this tolerance level (default to 3 if out of range)
        initial_vices = vice_mappings.get(drug_tolerance, vice_mappings[3])

        # Initialize all 8 vice preferences
        for category, intensity in initial_vices.items():
            try:
                await self.vice_repo.discover(
                    user_id=user_id,
                    category=category,
                    initial_intensity=intensity,
                )
            except Exception as e:
                logger.error(
                    f"Failed to initialize vice {category} for user_id={user_id}: {e}"
                )

        logger.info(
            f"Initialized 8 vice preferences for user_id={user_id} "
            f"with drug_tolerance={drug_tolerance}"
        )

    # === Validation Methods ===

    def _validate_location(self, text: str) -> bool:
        """Validate location input.

        AC-T2.1-005: Validates location input

        Args:
            text: Location input text.

        Returns:
            True if valid city name, False otherwise.
        """
        text = text.strip()
        # Basic validation: at least 2 chars, not just numbers
        if len(text) < 2:
            return False
        if text.isdigit():
            return False
        return True

    def _validate_drug_tolerance(self, text: str) -> bool:
        """Validate drug tolerance input.

        AC-T2.1-005: Validates 1-5 scale

        Args:
            text: Drug tolerance input text.

        Returns:
            True if valid 1-5, False otherwise.
        """
        text = text.strip()
        if not text.isdigit():
            return False
        num = int(text)
        return 1 <= num <= 5

    def _is_skip_request(self, text: str) -> bool:
        """Check if text is a skip request.

        AC-T2.3-003: Detects skip phrases

        Args:
            text: User input text.

        Returns:
            True if skip request, False otherwise.
        """
        text = text.lower().strip()
        return any(phrase in text for phrase in SKIP_PHRASES)


async def create_onboarding_handler(
    bot: TelegramBot,
    onboarding_repository: OnboardingStateRepository,
    profile_repository: ProfileRepository,
) -> OnboardingHandler:
    """Factory function for OnboardingHandler.

    Args:
        bot: Telegram bot client.
        onboarding_repository: Repository for onboarding state.
        profile_repository: Repository for user profiles.

    Returns:
        Configured OnboardingHandler instance.
    """
    return OnboardingHandler(
        bot=bot,
        onboarding_repository=onboarding_repository,
        profile_repository=profile_repository,
    )
