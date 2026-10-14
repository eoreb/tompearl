# player.js -> player.py - Желтая Душа (Yellow Soul) из Undertale
import math
import random
import os
import pygame
from audio import audio_manager
from utils import get_asset_path

class Player:
    def __init__(self, arena):
        self.arena = arena
        self.damage_sprite = None
        damage_path = get_asset_path(os.path.join('sprites', 'damage_5_0.png'))
        if os.path.exists(damage_path):
            try:
                self.damage_sprite = pygame.image.load(damage_path).convert_alpha()
            except Exception as e:
                print(f"[Player] Failed to load damage sprite: {e}")

        # Предварительно сгенерированный полигон сердца
        self.size = 18
        self.hitbox_radius = 5.5
        self.heart_surface = self._create_heart_surface(self.size, (255, 255, 0))

        self.reset()

    def _create_heart_surface(self, size, color):
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        s = size / 16.0
        # Точки формы сердца Undertale
        points = [
            (8 * s, 14 * s),
            (2 * s, 8 * s),
            (0 * s, 4 * s),
            (2 * s, 1 * s),
            (5 * s, 1 * s),
            (8 * s, 4 * s),
            (11 * s, 1 * s),
            (14 * s, 1 * s),
            (16 * s, 4 * s),
            (14 * s, 8 * s),
        ]
        pygame.draw.polygon(surf, color, points)
        # Блик в левом верхнем углу
        pygame.draw.circle(surf, (255, 255, 255), (int(5 * s), int(4 * s)), max(1, int(1.8 * s)))
        # Центральное ядро хитбокса
        pygame.draw.circle(surf, (255, 255, 255), (int(8 * s), int(7 * s)), 2)
        return surf

    def reset(self, difficulty=None):
        diff = difficulty or {'playerHp': 92, 'playerSpeed': 5.8, 'invulnerableDuration': 0.65, 'bulletDamage': 5}
        self.speed = diff.get('playerSpeed', 5.8)
        self.hp = diff.get('playerHp', 92)
        self.max_hp = self.hp
        self.bullet_damage = diff.get('bulletDamage', 5)
        self.invulnerable_duration = diff.get('invulnerableDuration', 0.65)
        self.invulnerable_timer = 0.0

        self.x = self.arena['x'] + self.arena['width'] / 2.0
        self.y = self.arena['y'] + self.arena['height'] - 40.0

        self.bullets = []
        self.shoot_cooldown = 0.0
        self.shoot_interval = 0.18

        self.damage_popups = []
        self.heal_popups = []

        self.shards = []
        self.is_dead = False

    def heal(self, amount=20):
        if self.is_dead:
            return
        old_hp = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        healed = self.hp - old_hp
        if healed > 0:
            self.heal_popups.append({
                'x': self.x,
                'y': self.y - 18,
                'text': f"+{healed} HP",
                'vy': -2.2,
                'alpha': 255
            })
            audio_manager.play_heal_sound()

    def take_damage(self, amount=5):
        if self.invulnerable_timer > 0 or self.is_dead:
            return

        self.hp = max(0, self.hp - amount)
        self.invulnerable_timer = self.invulnerable_duration
        audio_manager.play_player_hurt_sound()

        # Всплывающий спрайт урона «5.0»
        self.damage_popups.append({
            'x': self.x,
            'y': self.y - 15,
            'vy': -2.4,
            'alpha': 255,
            'scale': 1.0
        })

        if self.hp <= 0:
            self.die()

    def die(self):
        self.is_dead = True
        audio_manager.play_heart_shatter_sound()

        num_shards = 8
        self.shards = []
        for i in range(num_shards):
            angle = (i / num_shards) * math.pi * 2.0
            spd = 2.0 + random.random() * 4.0
            self.shards.append({
                'x': self.x,
                'y': self.y,
                'vx': math.cos(angle) * spd,
                'vy': math.sin(angle) * spd - 3.0,
                'rot': random.random() * 360.0,
                'vrot': (random.random() - 0.5) * 20.0,
                'size': int(5 + random.random() * 4)
            })

    def update(self, dt, keys, boss, attack_manager):
        if self.is_dead:
            for s in self.shards:
                s['x'] += s['vx'] * 60.0 * dt
                s['y'] += s['vy'] * 60.0 * dt
                s['vy'] += 0.3 * 60.0 * dt # гравитация
                s['rot'] += s['vrot'] * 60.0 * dt
            return

        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= dt

        # Обновление всплывающих спрайтов урона
        for dp in self.damage_popups[:]:
            dp['y'] += dp['vy'] * 60.0 * dt
            dp['vy'] += 0.08 * 60.0 * dt
            dp['alpha'] -= int(dt * 1.5 * 255)
            if dp['alpha'] <= 0:
                self.damage_popups.remove(dp)

        # Обновление всплывающих сообщений лечения
        for hp in self.heal_popups[:]:
            hp['y'] += hp['vy'] * 60.0 * dt
            hp['alpha'] -= int(dt * 1.2 * 255)
            if hp['alpha'] <= 0:
                self.heal_popups.remove(hp)

        # Движение (стрелки и WASD)
        dx = 0.0
        dy = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx -= 1.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1.0
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy -= 1.0
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy += 1.0

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        self.x += dx * self.speed * 60.0 * dt
        self.y += dy * self.speed * 60.0 * dt

        # Ограничение пределами арены (Battle Box)
        half = self.size / 2.0
        min_x = self.arena['x'] + half + 4
        max_x = self.arena['x'] + self.arena['width'] - half - 4
        min_y = self.arena['y'] + half + 4
        max_y = self.arena['y'] + self.arena['height'] - half - 4

        self.x = max(min_x, min(max_x, self.x))
        self.y = max(min_y, min(max_y, self.y))

        # Стрельба (клавиша Z или Пробел)
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= dt

        is_shooting = keys[pygame.K_z] or keys[pygame.K_SPACE]
        if is_shooting and self.shoot_cooldown <= 0:
            self.shoot()
            self.shoot_cooldown = self.shoot_interval

        # Обновление пуль игрока
        for b in self.bullets[:]:
            b['y'] -= b['speed'] * 60.0 * dt
            if boss and boss.check_hit(b):
                self.bullets.remove(b)
                continue
            if b['y'] < -20:
                self.bullets.remove(b)

    def shoot(self):
        self.bullets.append({
            'x': self.x - 4,
            'y': self.y - self.size,
            'width': 8,
            'height': 18,
            'speed': 18,
            'damage': self.bullet_damage
        })
        audio_manager.play_shoot_sound()

    def draw(self, screen, font):
        # 1. Пули игрока
        for b in self.bullets:
            rect = pygame.Rect(int(b['x']), int(b['y']), b['width'], b['height'])
            pygame.draw.rect(screen, (255, 255, 0), rect)
            inner = pygame.Rect(int(b['x'] + 2), int(b['y'] + 2), b['width'] - 4, b['height'] - 4)
            pygame.draw.rect(screen, (255, 255, 255), inner)

        # 2. Всплывающий спрайт урона «5.0»
        for dp in self.damage_popups:
            if self.damage_sprite:
                w, h = 42, 24
                scaled = pygame.transform.scale(self.damage_sprite, (w, h))
                scaled.set_alpha(max(0, min(255, dp['alpha'])))
                screen.blit(scaled, (int(dp['x'] - w / 2), int(dp['y'] - h / 2)))

        # 3. Всплывающий текст лечения (+HP)
        if font:
            for hp in self.heal_popups:
                alpha = max(0, min(255, hp['alpha']))
                txt_surf = font.render(hp['text'], True, (0, 255, 102))
                txt_surf.set_alpha(alpha)
                # Темная обводка/тень
                shadow_surf = font.render(hp['text'], True, (0, 40, 10))
                shadow_surf.set_alpha(alpha)
                rect = txt_surf.get_rect(center=(int(hp['x']), int(hp['y'])))
                screen.blit(shadow_surf, (rect.x + 1, rect.y + 1))
                screen.blit(txt_surf, rect)

        # 4. Если погиб — осколки сердца
        if self.is_dead:
            for s in self.shards:
                shard_surf = pygame.Surface((s['size'], s['size']), pygame.SRCALPHA)
                shard_surf.fill((255, 255, 0))
                rotated = pygame.transform.rotate(shard_surf, s['rot'])
                r_rect = rotated.get_rect(center=(int(s['x']), int(s['y'])))
                screen.blit(rotated, r_rect)
            return

        # 5. Мигание при неуязвимости (каждые 80мс)
        if self.invulnerable_timer > 0 and (int(pygame.time.get_ticks() / 80) % 2 == 0):
            return

        # 6. Отрисовка Жёлтой Души
        heart_rect = self.heart_surface.get_rect(center=(int(self.x), int(self.y)))
        screen.blit(self.heart_surface, heart_rect)
