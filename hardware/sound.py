"""
Sound Module - Audio Playback
==============================

Controls audio playback through pygame.mixer. Supports WAV, OGG, and MP3 files
with volume control, pause/resume, and looping.

Hardware: Speaker via GPIO 18 PWM (transistor circuit) or USB/3.5mm audio
Wiring:   GPIO18 -> 1kOhm Resistor -> S8050 Base, Collector -> Speaker(-),
          Speaker(+) -> 5V, Emitter -> GND
"""

import os

from hardware.base import HardwareModule


class SoundModule(HardwareModule):

    # --- HardwareModule interface -------------------------------------------

    @property
    def name(self):
        return "sound"

    @property
    def description(self):
        return "Audio playback via pygame mixer (WAV/OGG/MP3)"

    def init(self):
        import pygame
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)

        # State tracking
        self._volume = 80          # 0-100 (percentage)
        self._current_file = None
        self._sound = None         # Current pygame.mixer.Sound object
        self._channel = None       # Current playback channel
        self._paused = False

    def cleanup(self):
        try:
            import pygame
            pygame.mixer.quit()
        except Exception:
            pass

    def get_state(self):
        playing = False
        if self._channel is not None:
            playing = self._channel.get_busy() and not self._paused
        return {
            "volume": self._volume,
            "playing": playing,
            "paused": self._paused,
            "current_file": self._current_file,
        }

    def get_capabilities(self):
        return [
            {
                "action": "play",
                "description": "Play an audio file (WAV, OGG, or MP3)",
                "params": {
                    "file": {
                        "type": "str",
                        "required": True,
                        "description": "Path to audio file",
                    },
                    "volume": {
                        "type": "float",
                        "required": False,
                        "description": "Playback volume (0.0 to 1.0)",
                        "min": 0.0,
                        "max": 1.0,
                        "default": "uses current master volume",
                    },
                    "loop": {
                        "type": "bool",
                        "required": False,
                        "default": False,
                        "description": "Loop the sound continuously until stopped",
                    },
                },
            },
            {
                "action": "stop",
                "description": "Stop all audio playback",
                "params": {},
            },
            {
                "action": "volume",
                "description": "Set master volume level",
                "params": {
                    "level": {
                        "type": "int",
                        "required": True,
                        "description": "Volume percentage",
                        "min": 0,
                        "max": 100,
                    },
                },
            },
            {
                "action": "pause",
                "description": "Pause current playback",
                "params": {},
            },
            {
                "action": "resume",
                "description": "Resume paused playback",
                "params": {},
            },
        ]

    def handle_command(self, action, params):
        try:
            if action == "play":
                return self._cmd_play(params)
            elif action == "stop":
                return self._cmd_stop(params)
            elif action == "volume":
                return self._cmd_volume(params)
            elif action == "pause":
                return self._cmd_pause(params)
            elif action == "resume":
                return self._cmd_resume(params)
            else:
                return self._err(f"Unknown sound action: {action}")
        except Exception as e:
            return self._err(str(e))

    # --- Internal command handlers ------------------------------------------

    def _cmd_play(self, params):
        file_path = params.get("file")
        if not file_path:
            return self._err("Missing required param: file")

        if not os.path.isfile(file_path):
            return self._err(f"File not found: {file_path}")

        # Stop any current playback
        self._stop_playback()

        import pygame
        self._sound = pygame.mixer.Sound(file_path)

        # Set volume: use param if provided, otherwise use master volume
        vol = params.get("volume")
        if vol is not None:
            vol = max(0.0, min(1.0, float(vol)))
        else:
            vol = self._volume / 100.0
        self._sound.set_volume(vol)

        # Loop: -1 means infinite loop in pygame, 0 means play once
        loop = params.get("loop", False)
        loops = -1 if loop else 0

        self._channel = self._sound.play(loops=loops)
        self._current_file = file_path
        self._paused = False

        return self._ok({
            "file": file_path,
            "volume": vol,
            "looping": bool(loop),
        })

    def _cmd_stop(self, params):
        self._stop_playback()
        return self._ok()

    def _cmd_volume(self, params):
        level = params.get("level")
        if level is None:
            return self._err("Missing required param: level")

        level = max(0, min(100, int(level)))
        self._volume = level

        # Apply to current sound if playing
        if self._sound is not None:
            self._sound.set_volume(level / 100.0)

        return self._ok({"volume": level})

    def _cmd_pause(self, params):
        import pygame
        if self._channel is not None and self._channel.get_busy():
            pygame.mixer.pause()
            self._paused = True
            return self._ok({"paused": True})
        return self._err("Nothing is currently playing")

    def _cmd_resume(self, params):
        import pygame
        if self._paused:
            pygame.mixer.unpause()
            self._paused = False
            return self._ok({"paused": False})
        return self._err("Nothing is currently paused")

    # --- Internal helpers ---------------------------------------------------

    def _stop_playback(self):
        """Stop all playback and reset state."""
        import pygame
        pygame.mixer.stop()
        self._sound = None
        self._channel = None
        self._current_file = None
        self._paused = False
