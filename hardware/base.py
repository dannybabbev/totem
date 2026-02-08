"""
HardwareModule - Abstract Base Class
=====================================

Every hardware component (face, lcd, servo, sensors, etc.) implements this
interface. The daemon discovers and manages modules through this contract.

See CONTRIBUTING.md for a full guide on adding new hardware modules.
"""

from abc import ABC, abstractmethod


class HardwareModule(ABC):
    """
    Base class for all Totem hardware modules.

    Properties:
        name (str):        Short identifier used in CLI commands (e.g. "face", "lcd").
        description (str): Human-readable summary of the module.

    Lifecycle:
        1. __init__()       - Module is instantiated (no hardware access yet).
        2. init()           - Hardware is initialized (SPI/I2C/GPIO setup).
        3. handle_command() - Called for each incoming command.
        4. cleanup()        - Hardware is released on shutdown.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short module identifier (e.g. 'face', 'lcd', 'servo')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of this hardware module."""
        ...

    @abstractmethod
    def init(self) -> None:
        """
        Initialize the hardware (open SPI/I2C buses, set GPIO modes, etc.).
        Called once by the daemon at startup.
        Raise an exception if initialization fails.
        """
        ...

    @abstractmethod
    def cleanup(self) -> None:
        """
        Release hardware resources safely.
        Called by the daemon on shutdown. Must not raise.
        """
        ...

    @abstractmethod
    def handle_command(self, action: str, params: dict) -> dict:
        """
        Execute a command on this module.

        Args:
            action: The action to perform (e.g. "expression", "write", "angle").
            params: Dictionary of parameters for the action.

        Returns:
            {"ok": True, "data": {...}}  on success
            {"ok": False, "error": "..."} on failure
        """
        ...

    @abstractmethod
    def get_state(self) -> dict:
        """
        Return current state of the hardware module.

        Returns:
            Dict with module-specific state information.
            Example: {"current_expression": "happy", "brightness": 128}
        """
        ...

    @abstractmethod
    def get_capabilities(self) -> list:
        """
        Return the list of actions this module supports.

        Returns:
            List of dicts, each describing one action:
            [
                {
                    "action": "expression",
                    "description": "Set a named facial expression",
                    "params": {
                        "name": {
                            "type": "str",
                            "required": True,
                            "description": "Expression name",
                            "options": ["happy", "sad", ...]
                        }
                    }
                },
                ...
            ]
        """
        ...

    def _ok(self, data=None):
        """Helper: build a success response."""
        result = {"ok": True}
        if data is not None:
            result["data"] = data
        return result

    def _err(self, message):
        """Helper: build an error response."""
        return {"ok": False, "error": message}
