"""Custom exception hierarchy for :mod:`aiogram_jinja_ui`."""


class TelegramUIError(Exception):
    """Base exception for all library-specific errors."""


class TemplateRenderError(TelegramUIError):
    """Raised when template rendering or extraction fails."""


class KeyboardParseError(TelegramUIError):
    """Raised when Telegram keyboard DSL is invalid."""