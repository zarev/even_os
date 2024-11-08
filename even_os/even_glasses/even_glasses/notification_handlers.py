import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Union, List
from uuid import UUID
import binascii
import logging
from even_glasses.models import (
    Command,
    SubCommand,
    MicStatus,
    ScreenAction,
    AIStatus,
)

logger = logging.getLogger(__name__)
DEBUG = True

class CommandLogger:
    COMMAND_TYPES = {
        Command.START_AI: "Start Even AI",
        Command.OPEN_MIC: "Mic Control",
        Command.MIC_RESPONSE: "Mic Response",
        Command.RECEIVE_MIC_DATA: "Mic Data",
        Command.INIT: "Initialize",
        Command.HEARTBEAT: "Heartbeat",
        Command.SEND_RESULT: "AI Result",
        Command.QUICK_NOTE: "Quick Note",
        Command.DASHBOARD: "Dashboard",
        Command.NOTIFICATION: "Notification",
    }

    def __init__(self):
        # Use a project-relative path for logs
        current_dir = Path(__file__).resolve().parent
        self.data_dir = current_dir.parent.parent / "logs" / "notification_logs"
        self.data_dir.parent.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.data_dir / "notification_logs.json"
        self.command_history: Dict[str, List[Dict]] = {}
        self._load_existing_logs()

    # Rest of the class implementation remains the same
    def _parse_command(self, data: bytes) -> Dict:
        if not data:
            return self._create_error_parse("Empty data received")

        try:
            cmd = data[0]
            parsed = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "command": {
                    "hex": f"0x{cmd:02X}",
                    "int": cmd,
                    "type": self.COMMAND_TYPES.get(
                        cmd, f"Unknown command: 0x{cmd:02X}"
                    ),
                },
                "raw": {
                    "hex": data.hex(),
                    "hex_dump": binascii.hexlify(data).decode("ascii"),
                    "pretty_hex": " ".join(f"{b:02x}" for b in data),
                    "bytes": str(data),
                    "int_array": list(data),
                    "crc32": f"0x{binascii.crc32(data):08x}",
                },
            }

            if cmd == Command.START_AI:
                subcmd = data[1] if len(data) > 1 else None
                parsed["subcmd"] = {
                    "hex": f"0x{subcmd:02X}" if subcmd is not None else None,
                    "int": subcmd,
                    "description": {
                        SubCommand.EXIT: "Exit to dashboard",
                        SubCommand.PAGE_CONTROL: "Page up/down control",
                        SubCommand.START: "Start Even AI",
                        SubCommand.STOP: "Stop Even AI recording",
                    }.get(
                        subcmd,
                        f"Unknown subcmd: 0x{subcmd:02X}"
                        if subcmd is not None
                        else "No subcmd",
                    ),
                }

            elif cmd == Command.OPEN_MIC:
                enable = data[1] if len(data) > 1 else None
                parsed["mic_control"] = {
                    "hex": f"0x{enable:02X}" if enable is not None else None,
                    "int": enable,
                    "status": "Enable MIC"
                    if enable == MicStatus.ENABLE
                    else "Disable MIC",
                }

            elif cmd == Command.SEND_RESULT:
                if len(data) >= 9:
                    parsed["ai_result"] = {
                        "sequence": data[1],
                        "total_packages": data[2],
                        "current_package": data[3],
                        "screen_status": {
                            "action": data[4] & 0x0F,
                            "ai_status": data[4] & 0xF0,
                            "description": self._get_screen_status_description(data[4]),
                        },
                        "page_info": {"current": data[7], "total": data[8]},
                    }

            elif cmd == Command.NOTIFICATION:
                if len(data) >= 4:
                    parsed["notification"] = {
                        "notify_id": data[1],
                        "total_chunks": data[2],
                        "current_chunk": data[3],
                    }

            return parsed

        except Exception as e:
            return self._create_error_parse(f"Error parsing command: {str(e)}")

    def _get_screen_status_description(self, status: int) -> str:
        action = status & 0x0F
        ai_status = status & 0xF0

        action_desc = (
            "New content" if action == ScreenAction.NEW_CONTENT else "Unknown action"
        )
        ai_desc = {
            AIStatus.DISPLAYING: "Displaying (auto)",
            AIStatus.DISPLAY_COMPLETE: "Complete",
            AIStatus.MANUAL_MODE: "Manual mode",
            AIStatus.NETWORK_ERROR: "Network error",
        }.get(ai_status, "Unknown AI status")

        return f"{action_desc} - {ai_desc}"

    def _create_error_parse(self, error_msg: str) -> Dict:
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error": error_msg,
            "command": {"type": "Error"},
        }

    def log_command(self, sender: Union[UUID, int, str], data: Union[bytes, bytearray]):
        sender_key = str(sender)
        if isinstance(data, bytearray):
            data = bytes(data)

        parsed_cmd = self._parse_command(data)
        current_time = parsed_cmd["timestamp"]

        cmd_identifier = json.dumps(
            {
                k: v
                for k, v in parsed_cmd.items()
                if k != "timestamp"
            },
            sort_keys=True,
        )

        if sender_key not in self.command_history:
            self.command_history[sender_key] = {}

        if cmd_identifier not in self.command_history[sender_key]:
            self.command_history[sender_key][cmd_identifier] = {
                "command": parsed_cmd,
                "timestamps": [current_time],
            }
        else:
            self.command_history[sender_key][cmd_identifier]["timestamps"].append(
                current_time
            )

        self._save_logs()
        return self.command_history[sender_key][cmd_identifier]

    def _save_logs(self):
        try:
            serializable_history = {}
            for sender, commands in self.command_history.items():
                serializable_history[sender] = []
                for cmd_data in commands.values():
                    entry = cmd_data["command"].copy()
                    entry["timestamps"] = cmd_data["timestamps"]
                    serializable_history[sender].append(entry)

            with open(self.log_file, "w") as f:
                json.dump(serializable_history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving command logs: {e}")

    def _load_existing_logs(self):
        if self.log_file.exists():
            try:
                with open(self.log_file, "r") as f:
                    loaded_data = json.load(f)
                    self.command_history = {}

                    for sender, commands in loaded_data.items():
                        self.command_history[sender] = {}
                        for entry in commands:
                            timestamps = entry.pop("timestamps", [])
                            cmd_identifier = json.dumps(entry, sort_keys=True)
                            self.command_history[sender][cmd_identifier] = {
                                "command": entry,
                                "timestamps": timestamps,
                            }
            except json.JSONDecodeError:
                self.command_history = {}


command_logger = CommandLogger()


def debug_command_logs(sender: UUID | int | str, data: bytes | bytearray):
    cmd_log = command_logger.log_command(sender, data)
    logger.debug(f"Command received: {json.dumps(cmd_log, indent=2)}")

    sender_key = str(sender)
    if isinstance(data, bytearray):
        data = bytes(data)

    message = data.decode("utf-8", errors="ignore")
    data_hex = data.hex()
    logger.debug(f"Raw notification from {sender_key}: {message}")
    logger.debug(f"Notification data (hex): {data_hex}")


async def handle_incoming_notification(sender: UUID | int | str, data: bytes | bytearray):
    if DEBUG:
        debug_command_logs(sender, data)

    sender_key = str(sender)
    if isinstance(data, bytearray):
        data = bytes(data)

    message = data.decode("utf-8", errors="ignore")
    data_hex = data.hex()
    logger.info(f"Received notification from {sender_key}: {message}")
    logger.debug(f"Notification data (hex): {data_hex}")
