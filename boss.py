# boss.js -> boss.py - Логика, анимация и фазы Тома Перла (Undertale Boss)
import math
import random
import os
import pygame
from audio import audio_manager
from utils import get_asset_path

class Boss:
    def __init__(self, canvas_width=800):
        self.canvas_width = canvas_width
        self.image = None
        tom_path = get_asset_path(os.path.join('sprites', 'tom.jpeg'))
        if os.path.exists(tom_path):
            try:
                raw_img = pygame.image.load(tom_path).convert()
                self.image = pygame.transform.scale(raw_img, (200, 200))
            except Exception as e:
                print(f"[Boss] Failed to load Tom sprite: {e}")

        self.damage_sprite = None
        dmg_path = get_asset_path(os.path.join('sprites', 'damage_5_0.png'))
        if os.path.exists(dmg_path):
            try:
                self.damage_sprite = pygame.image.load(dmg_path).convert_alpha()
            except Exception as e:
                print(f"[Boss] Failed to load damage sprite: {e}")

        self.reset()

    def reset(self, difficulty=None):
        diff = difficulty or {'bossMaxHp': 1000}
        self.max_hp = diff.get('bossMaxHp', 1000)
        self.hp = self.max_hp
        self.width = 200
        self.height = 200
        self.base_x = self.canvas_width / 2.0
        self.base_y = 125.0
        self.x = self.base_x
        self.y = self.base_y

        self.time = 0.0
        self.current_phase = 1
        self.speech_bubble = None # {'text': '...', 'timer': 3.0}

        self.hit_flash_timer = 0.0
        self.shake_offset_x = 0.0
        self.shake_offset_y = 0.0

        self.damage_popups = []
        self.particles = []
        self.is_defeated = False
        self.defeat_timer = 0.0

    def update(self, dt, attack_manager=None):
        self.time += dt

        if self.speech_bubble:
            self.speech_bubble['timer'] -= dt
            if self.speech_bubble['timer'] <= 0:
                self.speech_bubble = None

        if self.is_defeated:
            self.defeat_timer += dt
            self.shake_offset_x = (random.random() - 0.5) * 14.0
            self.shake_offset_y = (random.random() - 0.5) * 14.0
            if random.random() < 0.35:
                self.spawn_defeat_particle()
            self._update_particles(dt)
            return

        # Проверка смены фаз
        p2_th = self.max_hp * 0.75
        p3_th = self.max_hp * 0.50
        p4_th = self.max_hp * 0.20

        if self.current_phase == 1 and self.hp <= p2_th:
            self.current_phase = 2
            self.speech_bubble = {'text': "Is that all?\nTaste this plate!", 'timer': 3.2}
            self.hit_flash_timer = 0.25
            if attack_manager:
                attack_manager.on_phase_change(2)
        elif self.current_phase == 2 and self.hp <= p3_th:
            self.current_phase = 3
            self.speech_bubble = {'text': "Aura 5.0 kicking in!\nFeel the phonk!", 'timer': 3.2}
            self.hit_flash_timer = 0.30
            if attack_manager:
                attack_manager.on_phase_change(3)
        elif self.current_phase == 3 and self.hp <= p4_th:
            self.current_phase = 4
            self.speech_bubble = {'text': "IMPOSSIBLE!\nMY FINAL PLATE!", 'timer': 3.6}
            self.hit_flash_timer = 0.40
            if attack_manager:
                attack_manager.on_phase_change(4)

        # Покачивание под бит музыки
        bob_speed = 6.5 if self.current_phase == 4 else 5.0 if self.current_phase == 3 else 4.0
        bobbing = math.sin(self.time * bob_speed) * (9.0 if self.current_phase == 4 else 6.0)
        sway = math.cos(self.time * 2.5) * 4.0
        self.x = self.base_x + sway + self.shake_offset_x
        self.y = self.base_y + bobbing + self.shake_offset_y

        # Вспышка урона и встряска
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= dt
            mag = 8.0 if self.current_phase == 4 else 5.0
            self.shake_offset_x = (random.random() - 0.5) * mag
            self.shake_offset_y = (random.random() - 0.5) * mag
        else:
            self.shake_offset_x = 0.0
            self.shake_offset_y = 0.0

        # Обновление всплывающих спрайтов «5.0» над боссом
        for dp in self.damage_popups[:]:
            dp['y'] += dp['vy'] * 60.0 * dt
            dp['vy'] += 0.08 * 60.0 * dt
            dp['alpha'] -= int(dt * 1.3 * 255)
            dp['scale'] = max(0.85, dp['scale'] - dt * 0.3)
            if dp['alpha'] <= 0:
                self.damage_popups.remove(dp)

        self._update_particles(dt)

    def _update_particles(self, dt):
        for p in self.particles[:]:
            p['x'] += p['vx'] * 60.0 * dt
            p['y'] += p['vy'] * 60.0 * dt
            p['life'] -= dt
            if p['life'] <= 0:
                self.particles.remove(p)

    def spawn_defeat_particle(self):
        self.particles.append({
            'x': self.x + (random.random() - 0.5) * self.width,
            'y': self.y + (random.random() - 0.5) * self.height,
            'vx': (random.random() - 0.5) * 6.0,
            'vy': (random.random() - 0.5) * 6.0,
            'size': int(5 + random.random() * 8),
            'color': (255, 255, 0) if random.random() > 0.5 else (255, 0, 85),
            'life': 0.6 + random.random() * 0.5
        })

    def check_hit(self, bullet):
        if self.is_defeated:
            return False

        left = self.x - self.width / 2.0 + 15
        right = self.x + self.width / 2.0 - 15
        top = self.y - self.height / 2.0 + 10
        bottom = self.y + self.height / 2.0

        if (bullet['x'] + bullet['width'] > left and
            bullet['x'] < right and
            bullet['y'] + bullet['height'] > top and
            bullet['y'] < bottom):
            dmg = bullet.get('damage', 5)
            self.take_damage(dmg)
            return True
        return False

    def take_damage(self, amount=5):
        if self.is_defeated:
            return

        self.hp = max(0, self.hp - amount)
        self.hit_flash_timer = 0.08
        audio_manager.play_boss_hit_sound()

        self.damage_popups.append({
            'x': self.x + (random.random() - 0.5) * 50.0,
            'y': self.y - 25.0,
            'vy': -2.6,
            'alpha': 255,
            'scale': 1.2
        })

        if self.hp <= 0:
            self.defeat()

    def defeat(self):
        self.is_defeated = True
        self.speech_bubble = {'text': "NOOO...\nMY DELICIOUS...", 'timer': 5.0}
        audio_manager.stop_battle()
        audio_manager.play_victory_sound()

    def draw(self, screen, font=None):
        draw_x = int(self.x - self.width / 2.0)
        draw_y = int(self.y - self.height / 2.0)

        # Фаза 4: Неоновое пульсирующее свечение ауры
        if self.current_phase == 4 and not self.is_defeated:
            pulse = int(12 + math.sin(self.time * 8.0) * 8)
            aura_surf = pygame.Surface((self.width + pulse * 2, self.height + pulse * 2), pygame.SRCALPHA)
            pygame.draw.rect(aura_surf, (255, 0, 85, 90), aura_surf.get_rect(), border_radius=10)
            screen.blit(aura_surf, (draw_x - pulse, draw_y - pulse))

        # Отрисовка спрайта Тома Перла
        if self.image:
            if self.hit_flash_timer > 0:
                # Белая вспышка урона
                flash_surf = self.image.copy()
                flash_surf.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGB_ADD)
                screen.blit(flash_surf, (draw_x, draw_y))
            else:
                screen.blit(self.image, (draw_x, draw_y))
        else:
            # Заглушка, если файл спрайта не найден
            pygame.draw.rect(screen, (100, 80, 60), (draw_x, draw_y, self.width, self.height))

        # Рамка портрета
        border_color = (255, 0, 85) if self.current_phase == 4 else (255, 255, 255)
        pygame.draw.rect(screen, border_color, (draw_x, draw_y, self.width, self.height), 3)

        # Отрисовка частиц поражения
        for p in self.particles:
            pygame.draw.rect(screen, p['color'], (int(p['x']), int(p['y']), p['size'], p['size']))

        # Всплывающие спрайты урона над боссом
        for dp in self.damage_popups:
            if self.damage_sprite:
                w = int(52 * dp['scale'])
                h = int(30 * dp['scale'])
                scaled = pygame.transform.scale(self.damage_sprite, (w, h))
                scaled.set_alpha(max(0, min(255, dp['alpha'])))
                screen.blit(scaled, (int(dp['x'] - w / 2), int(dp['y'] - h / 2)))

        # Диалоговое облачко реплики (Undertale Speech Balloon)
        if self.speech_bubble and font:
            self._draw_speech_bubble(screen, font)

    def _draw_speech_bubble(self, screen, font):
        text = self.speech_bubble['text']
        lines = text.split('\n')

        bw, bh = 220, 75
        bx = int(self.x + self.width / 2.0 + 20)
        by = int(self.y - 30)

        # Если облако выходит за правый край, сдвинуть влево
        if bx + bw > self.canvas_width - 10:
            bx = int(self.x - self.width / 2.0 - bw - 20)

        # Тело облачка
        bubble_rect = pygame.Rect(bx, by, bw, bh)
        pygame.draw.rect(screen, (255, 255, 255), bubble_rect, border_radius=6)
        pygame.draw.rect(screen, (0, 0, 0), bubble_rect, 3, border_radius=6)

        # Хвостик облачка, указывающий на Тома
        tail_points = [
            (bx if bx > self.x else bx + bw, by + 30),
            (bx - 12 if bx > self.x else bx + bw + 12, by + 36),
            (bx if bx > self.x else bx + bw, by + 42)
        ]
        pygame.draw.polygon(screen, (255, 255, 255), tail_points)
        pygame.draw.polygon(screen, (0, 0, 0), tail_points, 2)

        # Текст реплики
        y_offset = by + 12
        for line in lines:
            txt_surf = font.render(line, True, (0, 0, 0))
            screen.blit(txt_surf, (bx + 14, y_offset))
            y_offset += 24
