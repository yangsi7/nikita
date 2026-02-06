"""Pipeline template utilities."""
import os
from functools import lru_cache

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = os.path.dirname(__file__)


@lru_cache(maxsize=1)
def _get_env() -> Environment:
    """Get cached Jinja2 environment."""
    return Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=select_autoescape([]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_template(template_name: str, **context) -> str:
    """Render a Jinja2 template with the given context.

    Args:
        template_name: Name of the template file (e.g., "system_prompt.j2")
        **context: Template variables

    Returns:
        Rendered template string
    """
    env = _get_env()
    tmpl = env.get_template(template_name)
    return tmpl.render(**context)
