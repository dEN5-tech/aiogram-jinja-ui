from __future__ import annotations
import asyncio
import io
from dataclasses import dataclass, field
from typing import Dict, Optional, Union, List

from aiogram import Bot
from aiogram.types import FSInputFile, URLInputFile, BufferedInputFile, InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest


@dataclass
class UISession:
    chat_id: int
    message_id: int


class UIManager:
    """
    Ultimate UI Manager для aiogram-jinja-ui.
    Поддерживает: 
    - Групповые сессии (игры, канбан)
    - Приватные сессии (личный кабинет)
    - Авто-фоллбэк (Resend если Edit невозможен)
    - Работа с фото (URL, File, BytesIO)
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        # Структура: { session_id: { chat_id: UISession } }
        self.sessions: Dict[str, Dict[int, UISession]] = {}

    def register(self, session_id: str, chat_id: int, message_id: int) -> None:
        """Регистрирует пользователя в конкретной сессии (игре или личном кабинете)"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        self.sessions[session_id][chat_id] = UISession(chat_id=chat_id, message_id=message_id)

    def unregister(self, session_id: str, chat_id: int) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].pop(chat_id, None)

    async def sync(
        self,
        session_id: str,
        text: str,
        markup,
        photo: Optional[Union[str, io.BytesIO, BufferedInputFile]] = None,
    ) -> None:
        """
        СИНХРОНИЗАЦИЯ: Обновляет экран у ВСЕХ участников данной сессии.
        """
        group = self.sessions.get(session_id)
        if not group:
            return

        tasks = []
        for chat_id, session in list(group.items()):
            tasks.append(self._update_node(session_id, chat_id, session, text, markup, photo))
        
        await asyncio.gather(*tasks)

    async def _update_node(
        self,
        session_id: str,
        chat_id: int,
        session: UISession,
        text: str,
        markup,
        photo: Optional[Union[str, io.BytesIO, BufferedInputFile]] = None,
    ) -> None:
        """Внутренний метод обновления конкретного узла интерфейса"""
        try:
            if photo:
                # Если фото есть, пробуем отредактировать медиа (InputMediaPhoto)
                # Это позволяет менять саму картинку в сообщении
                await self.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=session.message_id,
                    media=InputMediaPhoto(
                        media=self._resolve_photo(photo),
                        caption=text,
                        parse_mode="HTML"
                    ),
                    reply_markup=markup
                )
            else:
                await self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=session.message_id,
                    text=text,
                    reply_markup=markup,
                    parse_mode="HTML",
                )
        except TelegramBadRequest as e:
            if "message is not modified" in e.message:
                return # Всё ок, интерфейс уже актуален
            
            # Если сообщение нельзя отредактировать (удалено или сменился тип контента)
            # Включаем тяжелую артиллерию: ПЕРЕОТПРАВКУ
            await self._resend_ui(session_id, chat_id, text, markup, photo)
        except Exception:
            await self._resend_ui(session_id, chat_id, text, markup, photo)

    async def _resend_ui(self, session_id, chat_id, text, markup, photo):
        """Метод для 'спасения' интерфейса через новую отправку"""
        try:
            if photo:
                sent = await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=self._resolve_photo(photo),
                    caption=text,
                    reply_markup=markup,
                    parse_mode="HTML",
                )
            else:
                sent = await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=markup,
                    parse_mode="HTML",
                )
            # Обновляем реестр новым message_id
            self.register(session_id, chat_id, sent.message_id)
        except Exception:
            # Если даже отправить не вышло (юзер заблочил бота), удаляем из сессии
            self.unregister(session_id, chat_id)

    @staticmethod
    def _resolve_photo(photo: Union[str, io.BytesIO, BufferedInputFile]):
        if isinstance(photo, str):
            if photo.startswith("http"):
                return URLInputFile(photo)
            return FSInputFile(photo)
        if isinstance(photo, io.BytesIO):
            return BufferedInputFile(photo.getvalue(), filename="ui_update.png")
        return photo # Уже готовый BufferedInputFile