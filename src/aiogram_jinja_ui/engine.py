import re
from typing import Optional, Tuple, Union

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from jinja2 import Environment, FileSystemLoader

from .exceptions import TemplateRenderError
from .extension import TelegramKeyboardExtension
from .parser import KeyboardParser


class TelegramUIEngine:
    def __init__(self, templates_dir: str):
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            extensions=[TelegramKeyboardExtension],
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,
        )

    def render(
        self, template_name: str, **context
    ) -> Tuple[
        str,
        Optional[Union[InlineKeyboardMarkup, ReplyKeyboardMarkup]],
        Optional[str],
    ]:
        try:
            template = self.env.get_template(template_name)
            rendered_raw = template.render(**context)
        except Exception as exc:
            raise TemplateRenderError(f"Failed to render {template_name}: {exc}")

        photo_match = re.search(r"<!--TG_PHOTO:(.*?)-->", rendered_raw)
        photo = photo_match.group(1).strip() if photo_match else None
        if photo_match:
            rendered_raw = rendered_raw.replace(photo_match.group(0), "")

        matches = re.findall(
            r"<!--TG_KB_START:(inline|reply)-->(.*?)<!--TG_KB_END-->",
            rendered_raw,
            re.DOTALL,
        )

        if not matches:
            return rendered_raw.strip(), None, photo

        kb_types = {kb_type for kb_type, _ in matches}
        if len(kb_types) > 1:
            raise TemplateRenderError(
                f"Mixed keyboard types in {template_name}: {sorted(kb_types)}"
            )

        kb_type = matches[0][0]
        kb_content = "\n".join(content.strip() for _, content in matches if content)
        clean_text = re.sub(
            r"<!--TG_KB_START:(inline|reply)-->(.*?)<!--TG_KB_END-->",
            "",
            rendered_raw,
            flags=re.DOTALL,
        ).strip()

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