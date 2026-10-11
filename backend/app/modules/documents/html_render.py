"""P7-B03: HTML/CSS templates for engine-rendered documents.

Jinja2 with autoescape ON - patient names, notes and the facility's header/
footer text are untrusted strings and must never be interpreted as markup.
"""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "html_templates"),
    autoescape=select_autoescape(["html"]),
)


_env.filters["money"] = lambda value: f"{float(value or 0):,.2f}"


def render_html(template_name: str, **context) -> str:
    return _env.get_template(template_name).render(**context)
