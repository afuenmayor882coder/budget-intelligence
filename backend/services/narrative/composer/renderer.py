"""Jinja2 template renderer for narrative generation."""
import hashlib
import os
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from services.narrative.filters import register_filters
from services.narrative.transitions import pick_transition
from services.narrative.synonyms import pick_synonym

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    register_filters(env)

    # Add globals
    env.globals["pick_transition"] = pick_transition
    env.globals["pick_synonym"] = pick_synonym

    def pick_variant(seed_str: str, n: int = 5) -> int:
        h = int(hashlib.md5(str(seed_str).encode()).hexdigest(), 16)
        return h % n

    env.globals["pick_variant"] = pick_variant

    return env


_env = None


def get_env() -> Environment:
    global _env
    if _env is None:
        _env = _make_env()
    return _env


def render_template(template_path: str, context: dict[str, Any]) -> str:
    """Render a Jinja2 template with the given context."""
    env = get_env()
    try:
        template = env.get_template(template_path)
        result = template.render(**context)
        return result.strip()
    except Exception as e:
        return f"[Narrative generation error: {e}]"


def render_string(template_str: str, context: dict[str, Any]) -> str:
    """Render an inline template string."""
    env = get_env()
    try:
        template = env.from_string(template_str)
        return template.render(**context).strip()
    except Exception as e:
        return f"[Render error: {e}]"
