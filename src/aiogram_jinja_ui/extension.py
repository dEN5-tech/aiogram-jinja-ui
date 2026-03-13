from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.parser import Parser


class TelegramKeyboardExtension(Extension):
    """
    Добавляет поддержку тега {% keyboard TYPE %} ... {% endkeyboard %}
    TYPE может быть 'inline' или 'reply'.
    """

    tags = {"keyboard"}

    def parse(self, parser: Parser) -> nodes.Node:
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
        content = caller().strip()
        return f"\n<!--TG_KB_START:{kb_type}-->\n{content}\n<!--TG_KB_END-->\n"