#!/usr/bin/env python3
"""
Totem Voice Assistant
=====================

Standalone voice assistant that runs alongside the totem daemon.
Listens for the wake word "Hey Totem" using Vosk (offline), then:
  1. Records speech until silence
  2. Transcribes via ElevenLabs Scribe API
  3. Gets AI response from OpenClaw gateway
  4. Synthesizes speech via ElevenLabs TTS API
  5. Plays audio through the ReSpeaker HAT

Uses totem_ctl.py for face/LCD expression updates.

Usage:
    python voice.py
"""

import glob
import json
import os
import signal
import struct
import subprocess
import sys
import time
import uuid
import wave

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import requests
import vosk

# Load .env from the same directory as this script
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# Silence Vosk logs (set before creating any Vosk objects)
vosk.SetLogLevel(-1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CTL_PATH = os.path.join(SCRIPT_DIR, "totem_ctl.py")


class VoiceAssistant:
    """Totem voice assistant — wake word → record → STT → AI → TTS → play."""

    def __init__(self):
        # --- Configuration ---
        self._api_key = os.getenv("ELEVENLABS_API_KEY")
        self._voice_id = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
        self._gateway_url = os.getenv("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")
        self._gateway_token = os.getenv("OPENCLAW_GATEWAY_TOKEN", "")
        self._wake_word = os.getenv("WAKE_WORD", "hey totem").lower()
        self._vosk_model_path = os.path.expanduser(
            os.getenv("VOSK_MODEL_PATH", "~/vosk-model-small-en-us-0.15")
        )
        self._silence_threshold = int(os.getenv("SILENCE_THRESHOLD", "500"))
        self._max_recording_secs = int(os.getenv("MAX_RECORDING_SECONDS", "30"))
        self._silence_duration = float(os.getenv("SILENCE_DURATION_SECONDS", "1.5"))

        # --- Validate required config ---
        if not self._api_key:
            sys.exit("[VOICE] ERROR: ELEVENLABS_API_KEY not set in .env")
        if not self._gateway_token:
            sys.exit("[VOICE] ERROR: OPENCLAW_GATEWAY_TOKEN not set in .env")
        if not os.path.isdir(self._vosk_model_path):
            sys.exit(
                f"[VOICE] ERROR: Vosk model not found at {self._vosk_model_path}\n"
                "Download it:\n"
                "  cd ~ && wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip\n"
                "  unzip vosk-model-small-en-us-0.15.zip && rm vosk-model-small-en-us-0.15.zip"
            )

        # --- State ---
        self._running = False
        self._arecord_proc = None
        self._card_num = None

        # --- Clients ---
        self._eleven = ElevenLabs(api_key=self._api_key)

    # -----------------------------------------------------------------------
    # Setup
    # -----------------------------------------------------------------------

    def _find_respeaker(self):
        """Detect ReSpeaker HAT ALSA card number by scanning /proc/asound/cards."""
        try:
            with open("/proc/asound/cards") as f:
                for line in f:
                    if "seeed" in line.lower():
                        self._card_num = int(line.strip().split()[0])
                        print(f"[VOICE] Found ReSpeaker at card {self._card_num}")
                        return
        except FileNotFoundError:
            pass

        # Fallback: try arecord -l
        try:
            result = subprocess.run(
                ["arecord", "-l"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if "seeed" in line.lower():
                    self._card_num = int(line.split(":")[0].split()[-1])
                    print(f"[VOICE] Found ReSpeaker at card {self._card_num}")
                    return
        except Exception:
            pass

        sys.exit(
            "[VOICE] ERROR: ReSpeaker HAT not found in ALSA devices.\n"
            "Check: arecord -l | grep -i seeed"
        )

    def _init_vosk(self):
        """Load Vosk model and create recognizer."""
        print(f"[VOICE] Loading Vosk model from {self._vosk_model_path}...")
        model = vosk.Model(self._vosk_model_path)
        self._recognizer = vosk.KaldiRecognizer(model, 16000)
        print("[VOICE] Vosk model loaded.")

    # -----------------------------------------------------------------------
    # Wake word detection
    # -----------------------------------------------------------------------

    def _listen_for_wake_word(self):
        """Block until wake word is detected. Returns True if detected, False if interrupted."""
        proc = subprocess.Popen(
            [
                "arecord", "-D", f"plughw:{self._card_num},0",
                "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "raw", "-q",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self._arecord_proc = proc

        try:
            self._recognizer.Reset()
            while self._running:
                data = proc.stdout.read(4000)
                if not data:
                    break
                if self._recognizer.AcceptWaveform(data):
                    result = json.loads(self._recognizer.Result())
                    if self._wake_word in result.get("text", "").lower():
                        return True
                else:
                    partial = json.loads(self._recognizer.PartialResult())
                    if self._wake_word in partial.get("partial", "").lower():
                        return True
        finally:
            proc.terminate()
            proc.wait()
            self._arecord_proc = None

        return False

    # -----------------------------------------------------------------------
    # Speech recording
    # -----------------------------------------------------------------------

    def _record_speech(self):
        """Record speech until silence detected. Returns path to WAV file, or None."""
        rate = 16000
        chunk_size = 1600  # 0.05s per chunk at 16kHz 16-bit mono
        chunk_duration = chunk_size / (rate * 2)  # bytes / (samples_per_sec * bytes_per_sample)
        silence_limit = int(self._silence_duration / chunk_duration)
        max_chunks = int(self._max_recording_secs / chunk_duration)
        min_speech_chunks = int(0.5 / chunk_duration)

        silence_chunks = 0
        speech_detected = False
        speech_chunks = 0
        audio_data = bytearray()

        proc = subprocess.Popen(
            [
                "arecord", "-D", f"plughw:{self._card_num},0",
                "-f", "S16_LE", "-r", str(rate), "-c", "1", "-t", "raw", "-q",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        try:
            chunk_count = 0
            while self._running and chunk_count < max_chunks:
                data = proc.stdout.read(chunk_size)
                if not data:
                    break
                audio_data.extend(data)
                rms = self._calculate_rms(data)
                chunk_count += 1

                if rms > self._silence_threshold:
                    speech_detected = True
                    speech_chunks += 1
                    silence_chunks = 0
                else:
                    silence_chunks += 1

                if speech_detected and silence_chunks >= silence_limit:
                    break
        finally:
            proc.terminate()
            proc.wait()

        if not speech_detected or speech_chunks < min_speech_chunks:
            return None

        wav_path = self._get_temp_path(".wav")
        self._write_wav(wav_path, audio_data, rate)
        return wav_path

    def _calculate_rms(self, data):
        """Calculate RMS (root mean square) of raw PCM S16_LE audio data."""
        n_samples = len(data) // 2
        if n_samples == 0:
            return 0
        samples = struct.unpack(f"<{n_samples}h", data)
        return (sum(s * s for s in samples) / n_samples) ** 0.5

    def _write_wav(self, path, pcm_data, rate):
        """Write raw PCM data as a WAV file."""
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(pcm_data)

    # -----------------------------------------------------------------------
    # API integrations
    # -----------------------------------------------------------------------

    def _transcribe(self, wav_path):
        """Transcribe audio via ElevenLabs Scribe API."""
        try:
            with open(wav_path, "rb") as f:
                result = self._eleven.speech_to_text.convert(
                    file=f,
                    model_id="scribe_v1",
                    language_code="en",
                )
            return result.text.strip()
        except Exception as e:
            print(f"[VOICE] STT error: {e}", file=sys.stderr)
            return ""

    def _get_ai_response(self, text):
        """Send transcript to OpenClaw gateway, return AI response text."""
        try:
            url = f"{self._gateway_url}/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self._gateway_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "openclaw/default",
                "messages": [{"role": "user", "content": text}],
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[VOICE] AI error: {e}", file=sys.stderr)
            return ""

    def _synthesize(self, text):
        """Convert text to speech via ElevenLabs TTS. Returns path to WAV file."""
        try:
            audio = self._eleven.text_to_speech.convert(
                text=text,
                voice_id=self._voice_id,
                model_id="eleven_flash_v2_5",
                output_format="mp3_44100_128",
            )
            mp3_path = self._get_temp_path(".mp3")
            wav_path = self._get_temp_path(".wav")
            with open(mp3_path, "wb") as f:
                for chunk in audio:
                    f.write(chunk)
            # Convert MP3 to WAV for aplay
            subprocess.run(
                ["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", wav_path],
                capture_output=True, timeout=30,
            )
            self._cleanup_temp(mp3_path)
            return wav_path
        except Exception as e:
            print(f"[VOICE] TTS error: {e}", file=sys.stderr)
            return None

    # -----------------------------------------------------------------------
    # Audio playback
    # -----------------------------------------------------------------------

    def _play_audio(self, wav_path):
        """Play WAV file through ReSpeaker HAT."""
        try:
            subprocess.run(
                ["aplay", "-D", f"plughw:{self._card_num},0", "-q", wav_path],
                timeout=120,
            )
        except Exception as e:
            print(f"[VOICE] Playback error: {e}", file=sys.stderr)

    # -----------------------------------------------------------------------
    # Expression orchestration
    # -----------------------------------------------------------------------

    def _show_state(self, state, message=""):
        """Update face and LCD to reflect current voice assistant state."""
        ctl = [sys.executable, CTL_PATH]
        try:
            if state == "idle":
                subprocess.run(ctl + ["face", "animate", "idle_blink"],
                               timeout=5, capture_output=True)
            elif state == "listening":
                subprocess.run(ctl + ["face", "animate", "listening"],
                               timeout=5, capture_output=True)
                subprocess.run(ctl + ["lcd", "write", "I'm listening!", "--align", "center"],
                               timeout=5, capture_output=True)
            elif state == "thinking":
                subprocess.run(ctl + ["face", "animate", "thinking"],
                               timeout=5, capture_output=True)
                lcd_msg = message or "Thinking..."
                subprocess.run(ctl + ["lcd", "write", lcd_msg[:16], "--align", "center"],
                               timeout=5, capture_output=True)
            elif state == "speaking":
                subprocess.run(ctl + ["face", "animate", "speaking"],
                               timeout=5, capture_output=True)
                if message:
                    line1 = message[:16]
                    line2 = message[16:32] if len(message) > 16 else ""
                    cmd = ctl + ["lcd", "write", line1, "--align", "center"]
                    if line2:
                        cmd += ["--line2", line2]
                    subprocess.run(cmd, timeout=5, capture_output=True)
            elif state in ("error", "sad", "confused"):
                expr = "sad" if state == "error" else state
                cmd = ctl + ["express", expr]
                if message:
                    cmd += ["--message", message[:32]]
                subprocess.run(cmd, timeout=5, capture_output=True)
        except Exception as e:
            print(f"[VOICE] Display error: {e}", file=sys.stderr)

    # -----------------------------------------------------------------------
    # Temp file management
    # -----------------------------------------------------------------------

    def _get_temp_path(self, suffix):
        return f"/tmp/totem_voice_{uuid.uuid4().hex[:8]}{suffix}"

    def _cleanup_temp(self, *paths):
        for path in paths:
            try:
                if path and os.path.exists(path):
                    os.unlink(path)
            except OSError:
                pass

    def _cleanup_all_temp(self):
        for path in glob.glob("/tmp/totem_voice_*"):
            self._cleanup_temp(path)

    # -----------------------------------------------------------------------
    # Signal handling
    # -----------------------------------------------------------------------

    def _handle_signal(self, signum, frame):
        print(f"\n[VOICE] Received signal {signum}, shutting down...")
        self._running = False
        if self._arecord_proc:
            self._arecord_proc.terminate()

    def _shutdown(self):
        print("[VOICE] Shutting down...")
        try:
            self._show_state("idle")
        except Exception:
            pass
        self._cleanup_all_temp()
        print("[VOICE] Stopped.")

    # -----------------------------------------------------------------------
    # Main loop
    # -----------------------------------------------------------------------

    def run(self):
        """Main voice assistant loop."""
        self._running = True
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        # Setup
        self._find_respeaker()
        self._init_vosk()
        self._cleanup_all_temp()

        print("[VOICE] Ready. Listening for wake word...")
        self._show_state("idle")

        while self._running:
            try:
                # Phase 1: Wait for wake word
                if not self._listen_for_wake_word():
                    continue

                print("[VOICE] Wake word detected!")

                # Phase 2: Record user speech
                self._show_state("listening")
                wav_path = self._record_speech()

                if not wav_path:
                    print("[VOICE] No speech detected.")
                    self._show_state("idle")
                    continue

                # Phase 3: Transcribe
                self._show_state("thinking", "Transcribing...")
                transcript = self._transcribe(wav_path)
                self._cleanup_temp(wav_path)

                if not transcript:
                    print("[VOICE] Empty transcript.")
                    self._show_state("idle")
                    continue

                print(f"[VOICE] Transcript: {transcript}")

                # Phase 4: Get AI response
                self._show_state("thinking", "Thinking...")
                response = self._get_ai_response(transcript)

                if not response:
                    self._show_state("confused", "No response")
                    time.sleep(2)
                    self._show_state("idle")
                    continue

                print(f"[VOICE] Response: {response[:80]}...")

                # Phase 5: Synthesize and play
                self._show_state("speaking", response[:32])
                tts_path = self._synthesize(response)

                if tts_path:
                    self._play_audio(tts_path)
                    self._cleanup_temp(tts_path)

                # Back to idle
                self._show_state("idle")

            except Exception as e:
                print(f"[VOICE] Loop error: {e}", file=sys.stderr)
                self._show_state("error", "Error occurred")
                time.sleep(3)
                self._show_state("idle")

        self._shutdown()


def main():
    assistant = VoiceAssistant()
    assistant.run()


if __name__ == "__main__":
    main()
