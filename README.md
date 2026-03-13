# aiogram-jinja-ui

[![CI](https://github.com/dEN5-tech/aiogram-jinja-ui/actions/workflows/ci.yml/badge.svg)](https://github.com/dEN5-tech/aiogram-jinja-ui/actions/workflows/ci.yml)
[![Release](https://github.com/dEN5-tech/aiogram-jinja-ui/actions/workflows/release.yml/badge.svg)](https://github.com/dEN5-tech/aiogram-jinja-ui/actions/workflows/release.yml)

Production-ready Jinja2 UI engine for **aiogram** with:
- template-driven Telegram text rendering,
- inline/reply keyboard DSL,
- optional photo marker support,
- sync manager for real-time UI updates across sessions.

---

## EN

### Features

- `TelegramUIEngine` for rendering Jinja2 templates into Telegram-ready text + markup.
- `UIManager` for synchronized UI updates (`edit` with resend fallback).
- Keyboard DSL in templates via special comment blocks (`TG_KB_START/TG_KB_END`).
- Strong fit for bots with dynamic dashboards, menus, and collaborative views.

### Installation

```bash
poetry add aiogram-jinja-ui
```

Or from wheel:

```bash
pip install aiogram_jinja_ui-<version>-py3-none-any.whl
```

### Minimal usage

```python
from aiogram_jinja_ui import TelegramUIEngine

ui = TelegramUIEngine("templates")
text, markup, photo = ui.render(
    "pages/start.html",
    username="den5",
)
```

### Versioning & releases

- Use semantic tags: `vMAJOR.MINOR.PATCH` (example: `v1.2.0`).
- `CI` workflow runs tests/build on push/PR.
- `Release` workflow builds wheel+sdist and creates GitHub Release on tag push.
- Optional PyPI publish is supported via `PYPI_API_TOKEN` secret.

### Local development

```bash
poetry install --with dev
poetry run pytest -q
poetry build
```

---

## RU

### Возможности

- `TelegramUIEngine` рендерит Jinja2-шаблоны в Telegram-текст и клавиатуры.
- `UIManager` синхронизирует интерфейс между сессиями (с fallback на resend).
- DSL для клавиатур через блоки `TG_KB_START/TG_KB_END`.
- Подходит для сложных ботов: дашборды, меню, совместные экраны.

### Установка

```bash
poetry add aiogram-jinja-ui
```

Или из wheel:

```bash
pip install aiogram_jinja_ui-<version>-py3-none-any.whl
```

### Минимальный пример

```python
from aiogram_jinja_ui import TelegramUIEngine

ui = TelegramUIEngine("templates")
text, markup, photo = ui.render(
    "pages/start.html",
    username="den5",
)
```

### Версионирование и релизы

- Используйте семантические теги: `vMAJOR.MINOR.PATCH` (например `v1.2.0`).
- Workflow `CI` запускает тесты и сборку на push/PR.
- Workflow `Release` публикует артефакты (`wheel` + `sdist`) в GitHub Releases по тегу.
- Публикация в PyPI поддерживается через секрет `PYPI_API_TOKEN`.

### Локальная разработка

```bash
poetry install --with dev
poetry run pytest -q
poetry build
```

---

## GitHub quick start

```bash
git init
git add .
git commit -m "feat: production-ready packaging, README EN/RU, CI/release workflows"
git branch -M main
git remote add origin https://github.com/dEN5-tech/aiogram-jinja-ui.git
git push -u origin main
```

Create first release:

```bash
git tag v1.0.0
git push origin v1.0.0
```
