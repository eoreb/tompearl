# audio.py - Звуковой менеджер на Pygame Mixer
import math
import struct
import os
import random
import pygame

from utils import get_asset_path

class AudioManager:
    def __init__(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception as e:
            print(f"[Audio] Mixer init failed: {e}")

        self.is_muted = False
        self.intro_audio = None
        self.battle_music_path = get_asset_path(os.path.join('sounds', 'Yara Yara Ya Phonk (Slowed).mp3'))
        
        intro_path = get_asset_path(os.path.join('sounds', 'hi-my-name-is-tom-pearl.mp3'))
        if os.path.exists(intro_path):
            try:
                self.intro_audio = pygame.mixer.Sound(intro_path)
            except Exception as e:
                print(f"[Audio] Failed to load intro audio: {e}")

        # Предварительная генерация ретро звуковых эффектов
        self.snd_blip = self._synth_square(frequency=280, duration=0.04, volume=0.08)
        self.snd_shoot = self._synth_chirp(f_start=850, f_end=160, duration=0.10, wave_type='saw', volume=0.18)
        self.snd_boss_hit = self._synth_chirp(f_start=240, f_end=60, duration=0.09, wave_type='triangle', volume=0.25)
        self.snd_player_hurt = self._synth_chirp(f_start=180, f_end=70, duration=0.20, wave_type='square', volume=0.30)
        self.snd_shatter = self._synth_noise(duration=0.25, volume=0.35)
        self.snd_heal = self._synth_arpeggio([523.25, 659.25, 783.99, 1046.5], note_duration=0.05, volume=0.15)
        self.snd_victory = self._synth_arpeggio([330, 392, 493, 587, 659], note_duration=0.10, volume=0.18)

    def _synth_square(self, frequency=280, duration=0.04, volume=0.1):
        sr = 44100
        n = int(sr * duration)
        buf = bytearray()
        for i in range(n):
            t = i / sr
            s = 1.0 if math.sin(2 * math.pi * frequency * t) >= 0 else -1.0
            env = (1.0 - i / n)
            val = int(32767 * volume * s * env)
            buf.extend(struct.pack('<hh', val, val))
        try:
            return pygame.mixer.Sound(buffer=bytes(buf))
        except Exception:
            return None

    def _synth_chirp(self, f_start=800, f_end=150, duration=0.10, wave_type='saw', volume=0.2):
        sr = 44100
        n = int(sr * duration)
        buf = bytearray()
        phase = 0.0
        for i in range(n):
            t = i / n
            freq = f_start + (f_end - f_start) * t
            phase += 2 * math.pi * freq / sr
            if wave_type == 'saw':
                s = 2.0 * ((phase / (2 * math.pi)) % 1.0) - 1.0
            elif wave_type == 'triangle':
                s = 2.0 * abs(2.0 * ((phase / (2 * math.pi)) % 1.0) - 1.0) - 1.0
            else: # square
                s = 1.0 if math.sin(phase) >= 0 else -1.0
            env = math.exp(-3.5 * t)
            val = int(32767 * volume * s * env)
            buf.extend(struct.pack('<hh', val, val))
        try:
            return pygame.mixer.Sound(buffer=bytes(buf))
        except Exception:
            return None

    def _synth_noise(self, duration=0.25, volume=0.3):
        sr = 44100
        n = int(sr * duration)
        buf = bytearray()
        for i in range(n):
            t = i / n
            env = math.exp(-4.0 * t)
            sample = (random.random() * 2.0 - 1.0) * env
            val = int(32767 * volume * sample)
            buf.extend(struct.pack('<hh', val, val))
        try:
            return pygame.mixer.Sound(buffer=bytes(buf))
        except Exception:
            return None

    def _synth_arpeggio(self, freqs, note_duration=0.06, volume=0.15):
        sr = 44100
        buf = bytearray()
        for freq in freqs:
            n = int(sr * note_duration)
            for i in range(n):
                t = i / sr
                s = math.sin(2 * math.pi * freq * t)
                env = 1.0 - (i / n) * 0.8
                val = int(32767 * volume * s * env)
                buf.extend(struct.pack('<hh', val, val))
        try:
            return pygame.mixer.Sound(buffer=bytes(buf))
        except Exception:
            return None

    def play_intro(self):
        if self.is_muted:
            return
        self.stop_battle()
        if self.intro_audio:
            try:
                self.intro_audio.stop()
                self.intro_audio.set_volume(1.0)
                self.intro_audio.play()
            except Exception as e:
                print(f"[Audio] Intro play error: {e}")

        # Фоновый запуск музыки боя на 70% громкости
        if os.path.exists(self.battle_music_path):
            try:
                pygame.mixer.music.load(self.battle_music_path)
                pygame.mixer.music.set_volume(0.70)
                pygame.mixer.music.play(-1)
            except Exception as e:
                print(f"[Audio] Battle music start error: {e}")

    def stop_intro(self):
        if self.intro_audio:
            try:
                self.intro_audio.stop()
            except Exception:
                pass

    def play_battle(self, force_restart=False):
        self.stop_intro()
        if self.is_muted:
            return
        if os.path.exists(self.battle_music_path):
            try:
                pygame.mixer.music.set_volume(1.0)
                if force_restart or not pygame.mixer.music.get_busy():
                    pygame.mixer.music.load(self.battle_music_path)
                    pygame.mixer.music.play(-1)
            except Exception as e:
                print(f"[Audio] Battle music error: {e}")

    def stop_battle(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            pygame.mixer.music.set_volume(0.0)
            if self.intro_audio:
                self.intro_audio.set_volume(0.0)
        else:
            pygame.mixer.music.set_volume(1.0)
            if self.intro_audio:
                self.intro_audio.set_volume(1.0)
        return self.is_muted

    def play_text_blip(self):
        if not self.is_muted and self.snd_blip:
            self.snd_blip.play()

    def play_shoot_sound(self):
        if not self.is_muted and self.snd_shoot:
            self.snd_shoot.play()

    def play_boss_hit_sound(self):
        if not self.is_muted and self.snd_boss_hit:
            self.snd_boss_hit.play()

    def play_player_hurt_sound(self):
        if not self.is_muted and self.snd_player_hurt:
            self.snd_player_hurt.play()

    def play_heart_shatter_sound(self):
        if not self.is_muted and self.snd_shatter:
            self.snd_shatter.play()

    def play_heal_sound(self):
        if not self.is_muted and self.snd_heal:
            self.snd_heal.play()

    def play_victory_sound(self):
        if not self.is_muted and self.snd_victory:
            self.snd_victory.play()

audio_manager = AudioManager()
