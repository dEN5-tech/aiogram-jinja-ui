"""Template rendering engine for aiogram-ready UI payloads."""

import re
from typing import Any, Final, Optional, TypeAlias

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from jinja2 import Environment, FileSystemLoader

from .exceptions import TemplateRenderError
from .extension import TelegramKeyboardExtension
from .parser import KeyboardParser

Markup: TypeAlias = InlineKeyboardMarkup | ReplyKeyboardMarkup
RenderResult: TypeAlias = tuple[str, Optional[Markup], Optional[str]]

_PHOTO_RE: Final[re.Pattern[str]] = re.compile(r"<!--TG_PHOTO:(.*?)-->")
_KEYBOARD_RE: Final[re.Pattern[str]] = re.compile(
    r"<!--TG_KB_START:(inline|reply)-->(.*?)<!--TG_KB_END-->", re.DOTALL
)


class TelegramUIEngine:
    """Render Jinja templates into Telegram text, keyboard markup and photo hint.

    Notes
    -----
    Template may include special markers:

    - ``<!--TG_PHOTO:<path-or-url>-->``
    - ``<!--TG_KB_START:inline|reply--> ... <!--TG_KB_END-->``
    """

    def __init__(self, templates_dir: str):
        """Initialize rendering environment.

        Parameters
        ----------
        templates_dir:
            Path to directory containing Jinja templates.
        """
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            extensions=[TelegramKeyboardExtension],
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,
        )

    def render(self, template_name: str, **context: Any) -> RenderResult:
        """Render template and extract Telegram-specific metadata.

        Parameters
        ----------
        template_name:
            Relative template file name.
        **context:
            Arbitrary values exposed to Jinja rendering context.

        Returns
        -------
        tuple[str, Optional[Markup], Optional[str]]
            ``(text, keyboard_markup, photo)``
        """
        try:
            template = self.env.get_template(template_name)
            rendered_raw = template.render(**context)
        except Exception as exc:
            raise TemplateRenderError(f"Failed to render {template_name}: {exc}")

        photo_match = _PHOTO_RE.search(rendered_raw)
        photo = photo_match.group(1).strip() if photo_match else None
        if photo_match:
            rendered_raw = rendered_raw.replace(photo_match.group(0), "")

        matches = _KEYBOARD_RE.findall(rendered_raw)

        if not matches:
            return rendered_raw.strip(), None, photo

        kb_types = {kb_type for kb_type, _ in matches}
        if len(kb_types) > 1:
            raise TemplateRenderError(
                f"Mixed keyboard types in {template_name}: {sorted(kb_types)}"
            )

        kb_type = matches[0][0]
        kb_content = "\n".join(content.strip() for _, content in matches if content)
        clean_text = _KEYBOARD_RE.sub("", rendered_raw).strip()

        try:
            if kb_type == "inline":
                markup = KeyboardParser.parse_inline(kb_content)
            else:
                markup = KeyboardParser.parse_reply(kb_content)
        except Exception as exc:
            raise TemplateRenderError(
                f"Keyboard parse error in {template_name}: {exc}"
            )

        return clean_text, markup, photo