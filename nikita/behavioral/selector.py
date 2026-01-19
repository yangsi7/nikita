"""Instruction Selection for Behavioral Meta-Instructions (Spec 024, T011-T014).

Selects relevant meta-instructions based on situation context.

Selection Process:
1. Load instruction library from YAML
2. Filter by situation type
3. Filter by conditions (chapter, relationship_score, conflict_states)
4. Sort by priority (1 = highest)
5. Return top N instructions
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from nikita.behavioral.models import (
    InstructionSet,
    MetaInstruction,
    SituationCategory,
    SituationContext,
    SituationType,
)

logger = logging.getLogger(__name__)

# Default path to instruction library
DEFAULT_INSTRUCTIONS_PATH = Path(__file__).parent.parent / "config_data" / "behavioral" / "instructions.yaml"


class InstructionSelector:
    """Selects meta-instructions based on situation context.

    Attributes:
        instruction_library: Loaded instructions by situation type.
        max_instructions: Maximum instructions to return per selection.
    """

    def __init__(
        self,
        instructions_path: Path | None = None,
        max_instructions: int = 5,
    ):
        """Initialize the selector.

        Args:
            instructions_path: Path to instructions YAML. Defaults to config_data.
            max_instructions: Maximum instructions to return. Defaults to 5.
        """
        self.instructions_path = instructions_path or DEFAULT_INSTRUCTIONS_PATH
        self.max_instructions = max_instructions
        self._instruction_library: dict[str, list[dict[str, Any]]] | None = None

    @property
    def instruction_library(self) -> dict[str, list[dict[str, Any]]]:
        """Lazy-load and cache instruction library."""
        if self._instruction_library is None:
            self._instruction_library = self._load_instructions()
        return self._instruction_library

    def _load_instructions(self) -> dict[str, list[dict[str, Any]]]:
        """Load instructions from YAML file.

        Returns:
            Dictionary mapping situation type to list of instruction dicts.

        Raises:
            FileNotFoundError: If instructions file doesn't exist.
        """
        if not self.instructions_path.exists():
            raise FileNotFoundError(f"Instructions file not found: {self.instructions_path}")

        with open(self.instructions_path) as f:
            data = yaml.safe_load(f)

        logger.debug("Loaded %d situation types from instructions", len(data))
        return data

    def select(
        self,
        context: SituationContext,
        max_instructions: int | None = None,
    ) -> InstructionSet:
        """Select relevant instructions for the given context.

        Args:
            context: Current situation context.
            max_instructions: Override default max. None uses instance default.

        Returns:
            InstructionSet containing selected instructions.
        """
        max_count = max_instructions if max_instructions is not None else self.max_instructions

        # Get raw instructions for this situation type
        situation_key = context.situation_type.value
        raw_instructions = self.instruction_library.get(situation_key, [])

        # Convert to MetaInstruction objects
        instructions = []
        for raw in raw_instructions:
            try:
                inst = self._parse_instruction(raw, context.situation_type)
                instructions.append(inst)
            except Exception as e:
                logger.warning("Failed to parse instruction %s: %s", raw.get("id"), e)

        # Filter by conditions
        applicable = [
            inst for inst in instructions
            if inst.applies_to_context(context)
        ]

        # Sort by priority (1 = highest priority)
        applicable.sort(key=lambda x: x.priority)

        # Take top N
        selected = applicable[:max_count]

        logger.debug(
            "Selected %d/%d instructions for situation=%s",
            len(selected),
            len(applicable),
            situation_key,
        )

        return InstructionSet(
            situation_type=context.situation_type,
            context=context,
            instructions=selected,
        )

    def _parse_instruction(
        self,
        raw: dict[str, Any],
        situation_type: SituationType,
    ) -> MetaInstruction:
        """Parse raw instruction dict into MetaInstruction model.

        Args:
            raw: Raw instruction dictionary from YAML.
            situation_type: The situation type this instruction belongs to.

        Returns:
            MetaInstruction model instance.
        """
        # Map category string to enum
        category_str = raw.get("category", "conversational")
        category = SituationCategory(category_str)

        return MetaInstruction(
            instruction_id=raw["id"],
            situation_type=situation_type,
            category=category,
            priority=raw.get("priority", 5),
            instruction=raw["instruction"],
            conditions=raw.get("conditions"),
            weight=raw.get("weight", 1.0),
        )

    def get_instructions_for_situation(
        self,
        situation_type: SituationType,
    ) -> list[MetaInstruction]:
        """Get all instructions for a situation type (without filtering).

        Args:
            situation_type: The situation type to get instructions for.

        Returns:
            List of all MetaInstruction objects for this situation.
        """
        situation_key = situation_type.value
        raw_instructions = self.instruction_library.get(situation_key, [])

        instructions = []
        for raw in raw_instructions:
            try:
                inst = self._parse_instruction(raw, situation_type)
                instructions.append(inst)
            except Exception as e:
                logger.warning("Failed to parse instruction %s: %s", raw.get("id"), e)

        return instructions

    def evaluate_conditions(
        self,
        instruction: MetaInstruction,
        context: SituationContext,
    ) -> bool:
        """Evaluate whether an instruction's conditions match the context.

        This is a convenience method that delegates to MetaInstruction.applies_to_context().

        Args:
            instruction: The instruction to evaluate.
            context: The context to evaluate against.

        Returns:
            True if all conditions are satisfied.
        """
        return instruction.applies_to_context(context)

    def clear_cache(self) -> None:
        """Clear the instruction library cache (for testing/reloading)."""
        self._instruction_library = None
