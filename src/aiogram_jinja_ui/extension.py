"""Jinja2 extension for keyboard DSL blocks."""

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.parser import Parser


class TelegramKeyboardExtension(Extension):
    """Add support for ``{% keyboard inline|reply %}`` blocks.

    The extension wraps block content into explicit markers that are later
    parsed by :class:`aiogram_jinja_ui.parser.KeyboardParser`.
    """

    tags = {"keyboard"}

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse custom keyboard block from template source."""
        lineno = next(parser.stream).lineno

        kb_type_token = parser.stream.expect("name")
        kb_type = kb_type_token.value

        if kb_type not in ("inline", "reply"):
            parser.fail(
                f"Invalid keyboard type '{kb_type}'. Expected 'inline' or 'reply'.",
                lineno,
            )

        body = parser.parse_statements(["name:endkeyboard"], drop_needle=True)

        return (
            nodes.CallBlock(
                self.call_method("_render_kb", [nodes.Const(kb_type)]),
                [],
                [],
                body,
            )
            .set_lineno(lineno)
        )

    def _render_kb(self, kb_type: str, caller) -> str:
        """Render keyboard block with parser markers.

        Parameters
        ----------
        kb_type:
            Keyboard kind: ``inline`` or ``reply``.
        caller:
            Jinja-generated callback returning the block body.
        """
        content = caller().strip()
        return f"\n<!--TG_KB_START:{kb_type}-->\n{content}\n<!--TG_KB_END-->\n"