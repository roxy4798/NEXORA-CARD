"""Conversation states for Telegram position wizard."""

from enum import IntEnum, auto


class PositionState(IntEnum):
    WAITING_COIN = auto()
    WAITING_SIDE = auto()
    WAITING_ENTRY = auto()
    WAITING_LEVERAGE = auto()
    WAITING_MARGIN = auto()
    WAITING_MARGIN_RATIO = auto()
    WAITING_EDIT_SELECT = auto()
    WAITING_EDIT_VALUE = auto()
