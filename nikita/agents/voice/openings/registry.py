"""Opening template registry — loads and caches YAML opening definitions."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import yaml

from nikita.agents.voice.openings.models import Opening

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


class OpeningRegistry:
    """Loads opening templates from YAML files and provides lookup."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        self._templates_dir = templates_dir or TEMPLATES_DIR
        self._openings: dict[str, Opening] = {}
        self._load()

    def _load(self) -> None:
        """Load all YAML files from templates directory."""
        if not self._templates_dir.exists():
            logger.warning(f"Opening templates directory not found: {self._templates_dir}")
            return

        for path in sorted(self._templates_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                if data is None:
                    continue
                opening = Opening.model_validate(data)
                self._openings[opening.id] = opening
                logger.debug(f"Loaded opening template: {opening.id}")
            except Exception:
                logger.exception(f"Failed to load opening template: {path}")

    def get(self, opening_id: str) -> Opening | None:
        """Get an opening by ID."""
        return self._openings.get(opening_id)

    def get_all(self) -> list[Opening]:
        """Get all loaded openings."""
        return list(self._openings.values())

    def get_fallback(self) -> Opening | None:
        """Get the fallback opening (is_fallback=True)."""
        for opening in self._openings.values():
            if opening.is_fallback:
                return opening
        # If no explicit fallback, try warm_intro
        return self._openings.get("warm_intro")

    def __len__(self) -> int:
        return len(self._openings)


@lru_cache
def get_opening_registry() -> OpeningRegistry:
    """Get cached singleton OpeningRegistry."""
    return OpeningRegistry()
