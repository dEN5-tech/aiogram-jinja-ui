import asyncio
import os
import re
from pathlib import Path
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, FSInputFile
from dotenvy import load_env, read_file
import aiohttp

# Импортируем ваши классы из пакета
from aiogram_jinja_ui import TelegramUIEngine, UIManager

BASE_DIR = os.path.dirname(__file__)
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    load_env(read_file(env_path))

TOKEN = os.getenv("BOT_TOKEN", "")
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
DOWNLOADS_DIR = Path(BASE_DIR) / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

ui = TelegramUIEngine(templates_dir=TEMPLATES_DIR)
ui_manager = UIManager(bot) # Теперь инициализация правильная

USERS_DB: dict[int, dict] = {}


def get_user_state(user_id: int, name: str):
    if user_id not in USERS_DB:
        USERS_DB[user_id] = {
            "name": name,
            "awaiting_url": False,
            "last_file_name": "",
        }
    return USERS_DB[user_id]


def sanitize_filename(url: str) -> str:
    name = url.rstrip("/").split("/")[-1] or "download.bin"
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return name[:120] or "download.bin"


async def update_start_screen(user_id: int, name: str):
    state = get_user_state(user_id, name)
    text, markup, photo = ui.render(
        "pages/start.html",
        awaiting_url=state.get("awaiting_url", False),
    )
    await ui_manager.sync(
        session_id=str(user_id),
        text=text,
        markup=markup,
        photo=photo,
    )


async def update_progress(user_id: int, percent: int, status_text: str, file_name: str):
    text, markup, photo = ui.render(
        "pages/progress.html",
        percent=percent,
        status_text=status_text,
        file_name=file_name,
    )
    await ui_manager.sync(
        session_id=str(user_id),
        text=text,
        markup=markup,
        photo=photo,
    )


async def download_with_aiohttp(user_id: int, url: str, file_path: Path):
    await update_progress(user_id, 0, "Установка соединения...", file_path.name)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) aiogram-downloader"
    }
    timeout = aiohttp.ClientTimeout(total=600)
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        try:
            async with session.get(url) as response:
                if response.status >= 400:
                    status_text = f"Ошибка сервера: {response.status} ❌"
                    if response.status == 500:
                        status_text = "Ошибка 500: Сервер файла перегружен"
                    await update_progress(user_id, 0, status_text, file_path.name)
                    return False

                total_size = int(response.headers.get("Content-Length", 0) or 0)
                if total_size > 50 * 1024 * 1024:
                    await update_progress(
                        user_id,
                        0,
                        "Ошибка: Файл больше 50 МБ ⛔️",
                        file_path.name,
                    )
                    return False

                downloaded = 0
                last_percent = -1

                with open(file_path, "wb") as target:
                    async for chunk in response.content.iter_chunked(1024 * 512):
                        if not chunk:
                            continue
                        target.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            if percent > last_percent:
                                last_percent = percent
                                await update_progress(
                                    user_id,
                                    min(percent, 99),
                                    f"Получено {downloaded // 1024} КБ",
                                    file_path.name,
                                )
                                await asyncio.sleep(0.5)
        except aiohttp.ClientError as exc:
            await update_progress(user_id, 0, f"Ошибка: {type(exc).__name__}", file_path.name)
            return False

    await update_progress(user_id, 100, "Загрузка завершена! Отправка...", file_path.name)
    return True

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    user = message.from_user
    state = get_user_state(user.id, user.full_name)
    state["awaiting_url"] = False

    text, markup, photo = ui.render(
        "pages/start.html",
        awaiting_url=False,
    )

    sent = await message.answer(
        text,
        reply_markup=markup,
        parse_mode="HTML",
    )
    ui_manager.register(str(user.id), user.id, sent.message_id)

@router.callback_query(F.data == "start_download")
async def handle_start_download(callback: CallbackQuery):
    state = get_user_state(callback.from_user.id, callback.from_user.full_name)
    state["awaiting_url"] = not state.get("awaiting_url", False)
    await update_start_screen(callback.from_user.id, callback.from_user.full_name)
    await callback.answer(
        "Отправьте ссылку на файл" if state["awaiting_url"] else "Отменено"
    )


@router.message()
async def handle_url_message(message: Message):
    user = message.from_user
    state = get_user_state(user.id, user.full_name)
    if not state.get("awaiting_url"):
        return

    url = message.text.strip() if message.text else ""
    if not url.startswith("http"):
        await message.reply("Пожалуйста, отправьте корректный URL.")
        return

    state["awaiting_url"] = False
    file_name = sanitize_filename(url)
    file_path = DOWNLOADS_DIR / file_name

    await update_progress(user.id, 0, "Запуск загрузки...", file_name)
    success = await download_with_aiohttp(user.id, url, file_path)
    if success:
        if file_path.exists() and file_path.stat().st_size > 0:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > 49.9:
                await message.answer(
                    "⚠️ Файл скачан, но он слишком велик для Bot API (50МБ+)."
                )
            else:
                await update_progress(user.id, 100, "Отправка файла в Telegram...", file_name)
                try:
                    await message.answer_document(
                        document=FSInputFile(file_path),
                        caption=f"✅ {file_name}\nРазмер: {size_mb:.2f} МБ",
                    )
                except Exception as exc:
                    await message.answer(f"❌ Ошибка Telegram при отправке: {str(exc)[:50]}")
        else:
            await message.answer("❌ Файл не был создан или пуст.")
    await update_start_screen(user.id, user.full_name)

async def main():
    if not TOKEN:
        raise RuntimeError("Set BOT_TOKEN in environment")
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())