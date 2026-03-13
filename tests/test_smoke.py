from aiogram_jinja_ui import TelegramUIEngine, UIManager


def test_public_api_exports() -> None:
    assert TelegramUIEngine is not None
    assert UIManager is not None
