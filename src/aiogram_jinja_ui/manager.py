"""Session-aware UI synchronization manager for aiogram bots."""

from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass
from typing import Dict, Optional, TypeAlias

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    BufferedInputFile,
    FSInputFile,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    ReplyKeyboardMarkup,
    URLInputFile,
)

Markup: TypeAlias = InlineKeyboardMarkup | ReplyKeyboardMarkup | None
PhotoInput: TypeAlias = str | io.BytesIO | BufferedInputFile


@dataclass(slots=True)
class UISession:
    """Single UI node info for a chat participant.

    Attributes
    ----------
    chat_id:
        Telegram chat identifier.
    message_id:
        Active message that should be edited/synchronized.
    """

    chat_id: int
    message_id: int


class UIManager:
    """Synchronize rendered UI between users or per-user sessions.

    Typical session examples:
    - ``session_id='user_123'`` for private UI
    - ``session_id='game_room_42'`` for shared room state
    """

    def __init__(self, bot: Bot) -> None:
        """Create manager bound to aiogram :class:`Bot` instance."""
        self.bot = bot
        self.sessions: Dict[str, Dict[int, UISession]] = {}

    def register(self, session_id: str, chat_id: int, message_id: int) -> None:
        """Register or update node for ``session_id`` and ``chat_id``."""
        self.sessions.setdefault(session_id, {})[chat_id] = UISession(
            chat_id=chat_id,
            message_id=message_id,
        )

    def unregister(self, session_id: str, chat_id: int) -> None:
        """Remove node from session if present."""
        if session_id in self.sessions:
            self.sessions[session_id].pop(chat_id, None)
            if not self.sessions[session_id]:
                self.sessions.pop(session_id, None)

    async def sync(
        self,
        session_id: str,
        text: str,
        markup: Markup,
        photo: Optional[PhotoInput] = None,
    ) -> None:
        """Sync UI state to all registered nodes in a session."""
        group = self.sessions.get(session_id)
        if not group:
            return

        await asyncio.gather(
            *[
                self._update_node(session_id, chat_id, session, text, markup, photo)
                for chat_id, session in list(group.items())
            ]
        )

    async def _update_node(
        self,
        session_id: str,
        chat_id: int,
        session: UISession,
        text: str,
        markup: Markup,
        photo: Optional[PhotoInput] = None,
    ) -> None:
        """Update a single UI node, fallback to resend when editing fails."""
        try:
            if photo is not None:
                await self.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=session.message_id,
                    media=InputMediaPhoto(
                        media=self._resolve_photo(photo),
                        caption=text,
                        parse_mode="HTML",
                    ),
                    reply_markup=markup,
                )
            else:
                await self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=session.message_id,
                    text=text,
                    reply_markup=markup,
                    parse_mode="HTML",
                )
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc):
                return
            await self._resend_ui(session_id, chat_id, text, markup, photo)
        except Exception:
            await self._resend_ui(session_id, chat_id, text, markup, photo)

    async def _resend_ui(
        self,
        session_id: str,
        chat_id: int,
        text: str,
        markup: Markup,
        photo: Optional[PhotoInput],
    ) -> None:
        """Send a fresh message and rebind session node to new message id."""
        try:
            if photo is not None:
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

            self.register(session_id, chat_id, sent.message_id)
        except Exception:
            self.unregister(session_id, chat_id)

    @staticmethod
    def _resolve_photo(photo: PhotoInput):
        """Normalize photo input into aiogram-compatible file object."""
        if isinstance(photo, str):
            if photo.startswith("http"):
                return URLInputFile(photo)
            return FSInputFile(photo)
        if isinstance(photo, io.BytesIO):
            return BufferedInputFile(photo.getvalue(), filename="ui_update.png")
        return photo
