"""
ВК чат-бот с обработкой команд
"""

from functools import wraps
from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple, List

from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll
from vk_api.bot_longpoll import VkBotEventType, VkBotMessageEvent

from loguru import logger

from .command_parser import Command, parse_command

from .config import VK_BOT_TOKEN, VK_USER_TOKEN, VK_GROUP_ID


SubCommands = List[str]
CommandCallback = Callable[[Command, "EventContext"], None]
AttachmentCallback = Callable[[str, "EventContext"], None]


@dataclass
class EventContext:
    """Кастомный ивент сообщения от пользователя"""

    peer_id: int
    message_id: int
    attachments: Dict[str, Any] | None

    raw_event: Any


class CommandHandler:
    """Обработчик поступающих команд и прикрепленных медиа"""

    def __init__(self, prefixes: str) -> None:
        self._prefixes = prefixes
        self._registered_commands: Dict[
            str, Tuple[CommandCallback, SubCommands | None]
        ] = {}

        self._registered_attachment_events: Dict[str, AttachmentCallback] = {}

    def on_command(
        self, command: str, subcommands: List[str] | None = None
    ) -> CommandCallback:
        """Декоратор на вызов команды"""

        def _on_command(func: CommandCallback):
            @wraps(func)
            def wrapper(*args, **kwargs):
                func(*args, **kwargs)

            self._registered_commands[command] = (wrapper, subcommands)

            return wrapper

        return _on_command

    def on_attachment(self, attachment_type: str) -> AttachmentCallback:
        """Декоратор на появление прикрепленных медиа с указанным типом"""

        def _on_attachment(func: AttachmentCallback):
            @wraps(func)
            def wrapper(*args, **kwargs):
                func(*args, **kwargs)

            self._registered_attachment_events[attachment_type] = wrapper

            return wrapper

        return _on_attachment

    def handle_attachment(
        self, attachment: Dict[str, Any], EventContext: EventContext = None
    ) -> None:
        """Обрабатывает прикрепленные медиа и вызывает callback на первый попавшийся тип"""

        for reg_attach_event in self._registered_attachment_events.items():
            attachment_type, callback = reg_attach_event

            if attachment["type"] != attachment_type:
                continue

            callback(EventContext)

    def parse(self, raw_input: str, EventContext: EventContext = None) -> None:
        """Парсит сообщение пользователя и при наличии команды вызывает её callback"""
        for reg_comm in self._registered_commands.items():
            name, comm = reg_comm
            callback, subcommands = comm

            try:
                return callback(
                    parse_command(raw_input, self._prefixes, name, subcommands),
                    EventContext,
                )
            except ValueError:
                continue

        raise ValueError(f"Некорректная команда: '{raw_input}'. Сигнатура не найдена.")


class Bot:
    """Основной ВК бот"""

    def __init__(
        self,
        group_id: str | None = VK_GROUP_ID,
        user_token: str | None = VK_USER_TOKEN,
        bot_token: str | None = VK_BOT_TOKEN,
        log_unknown_events: bool = False,
    ) -> None:
        self.bot_api = VkApi(token=bot_token)
        self.user_api = VkApi(token=user_token)
        self.longpoll = VkBotLongPoll(self.bot_api, group_id)

        self._log_unknown_events = log_unknown_events

        self.command_handler = CommandHandler("/!$%")

    def run(self) -> None:
        """Запускает ВК-поллинг"""
        for event in self.longpoll.listen():
            self._handle_event(event)

    def send_message(
        self,
        peer_id: int,
        text: str,
        reply_to: int | None = None,
        attachment: List[str] | str | None = None,
        keyboard: str | None = None,
    ) -> int:
        """Отправляет сообщение в чат по peer_id"""
        if attachment:
            raise NotImplementedError("Отправка вложений не реализована!")

        if keyboard:
            raise NotImplementedError("Отправка клавиатуры не реализована!")

        params = {
            "random_id": 0,
            "peer_id": peer_id,
            "message": text,
            "reply_to": reply_to,
            "keyboard": keyboard,
            "attachment": attachment,
        }

        return self.bot_api.method("messages.send", params)

    def edit_message(
        self,
        message_id: int,
        peer_id: int,
        text: str,
        attachment: List[str] | str | None = None,
        keyboard: str | None = None,
    ) -> None:
        """Изменяет сообщение по peer_id и message_id"""
        if attachment:
            raise NotImplementedError("Отправка вложений не реализована!")

        if keyboard:
            raise NotImplementedError("Отправка клавиатуры не реализована!")

        params = {
            "peer_id": peer_id,
            "message_id": message_id,
            "message": text,
            "keyboard": keyboard,
            "attachment": attachment,
        }

        return self.bot_api.method("messages.edit", params)

    def _handle_event(self, event: Any) -> None:
        match event.type:
            case VkBotEventType.MESSAGE_NEW:
                logger.debug("Событие: MESSAGE_NEW")
                self._handle_message_event(event)

            case _:
                if self._log_unknown_events:
                    logger.debug(f"Неопределенное событие: {event.type}")

    def _handle_message_event(self, event: VkBotMessageEvent) -> None:
        message = event.raw["object"]["message"]
        peer_id = message["peer_id"]
        message_id = message["id"]
        text = message["text"]
        attachments = (
            message["attachments"] if "attachments" in message.keys() else None
        )

        event_context = EventContext(
            peer_id=peer_id,
            attachments=attachments,
            message_id=message_id,
            raw_event=event.raw,
        )

        if attachments:
            return self.command_handler.handle_attachment(attachments[0], event_context)

        try:
            return self.command_handler.parse(text, event_context)
        except Exception:
            logger.error("Не удалось обработать событие сообщения!")
