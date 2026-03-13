class TelegramUIError(Exception):
    """Базовое исключение пакета"""


class TemplateRenderError(TelegramUIError):
    """Ошибка при рендеринге Jinja-шаблона"""


class KeyboardParseError(TelegramUIError):
    """Ошибка при парсинге DSL клавиатуры"""