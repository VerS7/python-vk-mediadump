"""
Парсер команд
"""

from __future__ import annotations

from typing import List
from dataclasses import dataclass


@dataclass
class Command:
    """Базовая команда. Может содержать аргументы и подкоманды"""

    command: str | None
    args: List[str] | None
    prefixes: List[str] | None
    subcommands: List[Command] | None


def parse_command(
    command_str: str,
    prefixes: str,
    main_command: str,
    subcommands: List[str] | None = None,
) -> Command:
    """Парсит строку с коммандой"""
    all_prefixes = list(prefixes) if prefixes else None

    used_prefix = None
    for prefix in prefixes:
        if command_str.startswith(prefix):
            used_prefix = prefix
            command_str = command_str[len(prefix) :]
            break

    if used_prefix is None and prefixes:
        raise ValueError(f"Команда должна начинаться с одного из префиксов: {prefixes}")

    parts = command_str.split()
    if not parts:
        raise ValueError("Пустая команда после префикса")

    if parts[0] != main_command:
        raise ValueError(f"Ожидалась '{main_command}', передана '{parts[0]}'")

    cmd_subcommands = []
    remaining_parts = parts[1:]

    if subcommands:
        i = 0
        while i < len(remaining_parts):
            current_part = remaining_parts[i]
            if current_part in subcommands:
                subcommand_args = []
                i += 1
                while (
                    i < len(remaining_parts) and remaining_parts[i] not in subcommands
                ):
                    subcommand_args.append(remaining_parts[i])
                    i += 1
                cmd_subcommands.append(
                    Command(
                        command=current_part,
                        args=subcommand_args or None,
                        prefixes=None,
                        subcommands=None,
                    )
                )
            else:
                raise ValueError(
                    f"Неожиданный аргумент '{current_part}', ожидались подкоманды из: {subcommands}"
                )

    if subcommands and not cmd_subcommands:
        raise ValueError(f"Ожидалась как минимум одна подкоманда из: {subcommands}")

    return Command(
        command=main_command,
        args=None,
        prefixes=all_prefixes,
        subcommands=cmd_subcommands if cmd_subcommands else None,
    )
