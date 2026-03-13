"""Keyboard DSL parser for Telegram markups.

This module parses keyboard blocks extracted from templates and produces
aiogram-native keyboard markup objects.
"""

import re

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.types.web_app_info import WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from .exceptions import KeyboardParseError


class KeyboardParser:
    """Parse inline/reply keyboard DSL blocks into aiogram markup objects."""

    BTN_PATTERN = re.compile(r"\[\s*(.+?)\s*(?:\|\s*(.+?)\s*)?\]")
    GRID_PATTERN = re.compile(r"<!--\s*grid:\s*(\d+)\s*-->")

    @classmethod
    def parse_inline(cls, raw_text: str) -> InlineKeyboardMarkup:
        """Parse inline keyboard DSL.

        Supported actions:
        - ``cb:<data>`` (or raw callback data)
        - ``url:<https://...>``
        - ``webapp:<https://...>``

        Optional layout marker:
        ``<!-- grid: N -->`` where ``N`` is row width.
        """
        grid_match = cls.GRID_PATTERN.search(raw_text)
        grid_width = int(grid_match.group(1)) if grid_match else 0
        builder = InlineKeyboardBuilder()
        all_buttons: list[InlineKeyboardButton] = []

        for line in raw_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("<!--"):
                continue

            for match in cls.BTN_PATTERN.finditer(line):
                text = match.group(1).strip()
                action = match.group(2)

                if not action:
                    raise KeyboardParseError(
                        f"Inline button '{text}' missing action (callback_data or url)"
                    )

                action = action.strip()
                if action.startswith("url:"):
                    button = InlineKeyboardButton(text=text, url=action[4:])
                elif action.startswith("webapp:"):
                    button = InlineKeyboardButton(
                        text=text, web_app=WebAppInfo(url=action[7:])
                    )
                else:
                    cb_data = action[3:] if action.startswith("cb:") else action
                    button = InlineKeyboardButton(text=text, callback_data=cb_data)

                all_buttons.append(button)
                if not grid_width:
                    builder.row(button)

        if grid_width:
            builder.add(*all_buttons)
            builder.adjust(grid_width)

        return builder.as_markup()

    @classmethod
    def parse_reply(cls, raw_text: str) -> ReplyKeyboardMarkup:
        """Parse reply keyboard DSL.

        Supported special actions:
        - ``request_contact``
        - ``request_location``
        """
        builder = ReplyKeyboardBuilder()

        for line in raw_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            row = []
            for match in cls.BTN_PATTERN.finditer(line):
                text = match.group(1).strip()
                action = match.group(2)

                if action == "request_contact":
                    row.append(KeyboardButton(text=text, request_contact=True))
                elif action == "request_location":
                    row.append(KeyboardButton(text=text, request_location=True))
                else:
                    row.append(KeyboardButton(text=text))

            if row:
                builder.row(*row)

        return builder.as_markup(resize_keyboard=True)