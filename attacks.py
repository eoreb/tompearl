# attacks.py - Атаки Тома Перла (Undertale Edition)
import os
import math
import random
import pygame

from utils import get_asset_path

class AttackManager:
    def __init__(self, arena):
        self.arena = arena

        # 1. Спрайт Лика Тома (круглая мини-голова с золотым ореолом ауры)
        self.tom_head_surf = None
        tom_path = get_asset_path(os.path.join('sprites', 'tom.jpeg'))
        if os.path.exists(tom_path):
            try:
                raw_img = pygame.image.load(tom_path)
                if pygame.display.get_init() and pygame.display.get_surface():
                    raw_img = raw_img.convert()
                raw_scaled = pygame.transform.scale(raw_img, (44, 44))
                mask_surf = pygame.Surface((44, 44), pygame.SRCALPHA)
                pygame.draw.circle(mask_surf, (255, 255, 255, 255), (22, 22), 21)
                self.tom_head_surf = pygame.Surface((44, 44), pygame.SRCALPHA)
                self.tom_head_surf.blit(raw_scaled, (0, 0))
                self.tom_head_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                pygame.draw.circle(self.tom_head_surf, (255, 215, 0), (22, 22), 21, 2)
            except Exception as e:
                print(f"[Attacks] Failed to load Tom head: {e}")

        if not self.tom_head_surf:
            self.tom_head_surf = pygame.Surface((44, 44), pygame.SRCALPHA)
            pygame.draw.circle(self.tom_head_surf, (255, 220, 150), (22, 22), 20)
            pygame.draw.circle(self.tom_head_surf, (255, 215, 0), (22, 22), 20, 3)

        # 2. Спрайт Вантуза (Plunger)
        self.plunger_surf = pygame.Surface((38, 22), pygame.SRCALPHA)
        # Деревянная ручка
        pygame.draw.rect(self.plunger_surf, (175, 115, 55), (0, 8, 22, 6), border_radius=2)
        pygame.draw.rect(self.plunger_surf, (115, 70, 30), (0, 8, 22, 6), 1, border_radius=2)
        # Резиновый колокол присоски
        pts = [(20, 3), (36, 1), (36, 21), (20, 19)]
        pygame.draw.polygon(self.plunger_surf, (215, 35, 35), pts)
        pygame.draw.polygon(self.plunger_surf, (140, 20, 20), pts, 2)
        pygame.draw.ellipse(self.plunger_surf, (160, 25, 25), (33, 1, 5, 20))

        # 3. Спрайт Рулона туалетной бумаги (TP roll)
        self.tp_roll_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(self.tp_roll_surf, (245, 245, 245), (15, 15), 14)
        pygame.draw.circle(self.tp_roll_surf, (220, 220, 220), (15, 15), 10)
        pygame.draw.circle(self.tp_roll_surf, (155, 115, 75), (15, 15), 5)
        pygame.draw.circle(self.tp_roll_surf, (85, 60, 35), (15, 15), 3)
        pygame.draw.circle(self.tp_roll_surf, (190, 190, 190), (15, 15), 14, 2)

        self.reset()

    def reset(self, difficulty=None):
        diff = difficulty or {'speedMultiplier': 1.0, 'cooldownMultiplier': 1.0, 'healInterval': 40, 'healAmount': 20}
        self.speed_multiplier = diff.get('speedMultiplier', 1.0)
        self.cooldown_multiplier = diff.get('cooldownMultiplier', 1.0)
        self.heal_interval = diff.get('healInterval', 40)
        self.heal_amount = diff.get('healAmount', 20)
        self.heal_timer = 0.0
        self.heal_pickups = []

        self.projectiles = []
        self.lasers = []
        self.telegraphs = []
        self.geysers = []
        self.current_pattern = 0
        self.pattern_cooldown = 0.3 * self.cooldown_multiplier
        self.pattern_time = 0.0
        self.spiral_angle = 0.0
        self.shake_amount = 0.0

    def on_phase_change(self, phase):
        # Очистить снаряды и гейзеры при смене фазы, чтобы дать игроку передышку
        self.projectiles = [p for p in self.projectiles if p.get('type') != 'tom_head']
        self.geysers = []
        self.telegraphs = []

        # Выбросить восстанавливающий жемчуг здоровья (+HP)
        if self.heal_amount > 0:
            self.spawn_heal_pickup(self.heal_amount)

    def spawn_heal_pickup(self, amount=20):
        x = self.arena['x'] + 40 + random.random() * (self.arena['width'] - 80)
        y = self.arena['y'] + 40 + random.random() * (self.arena['height'] - 80)
        self.heal_pickups.append({
            'x': x,
            'y': y,
            'base_y': y,
            'radius': 12,
            'amount': amount,
            'time': 0.0,
            'life': 14.0
        })

    def update(self, dt, player, boss):
        if not boss or boss.is_defeated or not player or player.is_dead:
            return

        self.pattern_time += dt

        if self.shake_amount > 0:
            self.shake_amount = max(0.0, self.shake_amount - dt * 25.0)

        # Обновление предметов лечения (Heal Pickups)
        for hp in self.heal_pickups[:]:
            hp['time'] += dt * 3.5
            hp['y'] = hp['base_y'] + math.sin(hp['time']) * 5.0
            hp['life'] -= dt

            # Проверка подбора игроком
            dx = player.x - hp['x']
            dy = player.y - hp['y']
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < hp['radius'] + player.size / 2.0:
                player.heal(hp['amount'])
                self.heal_pickups.remove(hp)
                continue

            if hp['life'] <= 0:
                self.heal_pickups.remove(hp)

        # Периодический спавн жемчуга здоровья
        if self.heal_interval > 0:
            self.heal_timer += dt
            if self.heal_timer >= self.heal_interval:
                self.heal_timer = 0.0
                self.spawn_heal_pickup(self.heal_amount)

        # Фазы босса
        p2_th = boss.max_hp * 0.75
        p3_th = boss.max_hp * 0.50
        p4_th = boss.max_hp * 0.20
        is_p2 = boss.hp <= p2_th and boss.hp > p3_th
        is_p3 = boss.hp <= p3_th and boss.hp > p4_th
        is_p4 = boss.hp <= p4_th

        # Динамическая смена 10 паттернов
        pattern_cycle_time = (2.8 if is_p4 else 3.5 if is_p3 else 4.2 if is_p2 else 5.0) * self.cooldown_multiplier
        if self.pattern_time > pattern_cycle_time:
            self.pattern_time = 0.0
            self.current_pattern = (self.current_pattern + 1) % 10
            self.pattern_cooldown = 0.15 * self.cooldown_multiplier

        # Фоновый летающий Лик Тома в поздних фазах (вместо старых красных кубов)
        max_bg = 2 if is_p4 else 1 if is_p3 else 0
        current_heads = len([p for p in self.projectiles if p.get('type') == 'tom_head'])
        if current_heads < max_bg:
            spd = (5.2 if is_p4 else 4.2) * self.speed_multiplier
            self.spawn_bouncing_tom_head(spd)

        # Запуск активного паттерна
        self.run_pattern(dt, player, boss, is_p2, is_p3, is_p4)

        # Обновление снарядов
        for p in self.projectiles[:]:
            self._update_projectile(p, dt, player)

            # Проверка столкновения
            if self.check_collision(p, player):
                player.take_damage(p.get('damage', 5))
                if p.get('destroy_on_hit', False):
                    if p.get('type') == 'plate' and p.get('burst_on_destroy', False):
                        self.spawn_plate_shrapnel(p['x'], p['y'])
                    self.projectiles.remove(p)
                    continue

            # Тарелка ударилась о пол арены -> разрыв на брызги
            if p.get('type') == 'plate' and p['y'] >= self.arena['y'] + self.arena['height'] - 10:
                self.spawn_plate_shrapnel(p['x'], p['y'])
                self.projectiles.remove(p)
                continue

            # Взрыв бомбы по таймеру
            if p.get('type') == 'bomb' and p.get('exploded', False):
                self.explode_bomb(p['x'], p['y'])
                self.projectiles.remove(p)
                continue

            if p.get('is_dead', False):
                self.projectiles.remove(p)

        # Обновление гейзеров жижи ("Special on my plate")
        for g in self.geysers[:]:
            g['time'] += dt
            if g['state'] == 'warning':
                if g['time'] >= g['warning_duration']:
                    g['state'] = 'erupting'
                    g['time'] = 0.0
                    self.shake_amount = max(self.shake_amount, 6.0)
            elif g['state'] == 'erupting':
                core = player.hitbox_radius
                if (player.x + core > g['x'] and
                    player.x - core < g['x'] + g['w'] and
                    player.y + core > g['y'] - g['h'] and
                    player.y - core < g['y']):
                    player.take_damage(g.get('damage', 7))

                if g['time'] >= g['erupt_duration']:
                    self.geysers.remove(g)

        # Обновление лазеров
        for laser in self.lasers[:]:
            laser['time'] += dt
            if laser['time'] >= laser['warning_duration'] and laser['time'] < laser['warning_duration'] + laser['active_duration']:
                hit = False
                if laser['axis'] == 'horizontal':
                    hit = (player.y >= laser['pos'] - laser['thickness'] / 2.0 and
                           player.y <= laser['pos'] + laser['thickness'] / 2.0)
                else:
                    hit = (player.x >= laser['pos'] - laser['thickness'] / 2.0 and
                           player.x <= laser['pos'] + laser['thickness'] / 2.0)
                if hit:
                    player.take_damage(laser.get('damage', 5))

            if laser['time'] >= laser['warning_duration'] + laser['active_duration']:
                self.lasers.remove(laser)

        # Обновление телеграфов зон поражения (Мега-удар)
        for t in self.telegraphs[:]:
            t['time'] += dt
            if t['time'] >= t['warning_duration'] and not t.get('triggered', False):
                t['triggered'] = True
                self.shake_amount = 9.0
                if (player.x >= t['x'] and player.x <= t['x'] + t['w'] and
                    player.y >= t['y'] and player.y <= t['y'] + t['h']):
                    player.take_damage(10)

            if t['time'] >= t['warning_duration'] + t['slam_duration']:
                self.telegraphs.remove(t)

    def _update_projectile(self, p, dt, player):
        ptype = p.get('type')

        if ptype == 'tom_head':
            p['trail'].append((p['x'], p['y']))
            if len(p['trail']) > 5:
                p['trail'].pop(0)

            p['x'] += p['vx'] * 60.0 * dt
            p['y'] += p['vy'] * 60.0 * dt
            p['angle'] += p['rot_speed'] * 60.0 * dt

            # Отскоки от стенок арены
            r = p['radius']
            if p['x'] - r < self.arena['x'] + 4:
                p['x'] = self.arena['x'] + 4 + r
                p['vx'] = abs(p['vx'])
                p['rot_speed'] = -p['rot_speed']
            elif p['x'] + r > self.arena['x'] + self.arena['width'] - 4:
                p['x'] = self.arena['x'] + self.arena['width'] - 4 - r
                p['vx'] = -abs(p['vx'])
                p['rot_speed'] = -p['rot_speed']

            if p['y'] - r < self.arena['y'] + 4:
                p['y'] = self.arena['y'] + 4 + r
                p['vy'] = abs(p['vy'])
            elif p['y'] + r > self.arena['y'] + self.arena['height'] - 4:
                p['y'] = self.arena['y'] + self.arena['height'] - 4 - r
                p['vy'] = -abs(p['vy'])

            p['life'] -= dt
            if p['life'] <= 0:
                p['is_dead'] = True

        elif ptype == 'plunger':
            p['x'] += p['vx'] * 60.0 * dt
            p['y'] += p['vy'] * 60.0 * dt
            # Вылет за арену с запасом
            if (p['x'] < self.arena['x'] - 50 or p['x'] > self.arena['x'] + self.arena['width'] + 50 or
                p['y'] < self.arena['y'] - 50 or p['y'] > self.arena['y'] + self.arena['height'] + 50):
                p['is_dead'] = True

        elif ptype == 'tp_roll':
            p['trail'].append((p['x'], p['y']))
            if len(p['trail']) > 16:
                p['trail'].pop(0)

            p['x'] += p['vx'] * 60.0 * dt
            p['y'] += p['vy'] * 60.0 * dt
            p['angle'] += p['rot_speed'] * 60.0 * dt

            r = p['radius']
            if p['x'] - r < self.arena['x'] + 4:
                p['x'] = self.arena['x'] + 4 + r
                p['vx'] = abs(p['vx'])
            elif p['x'] + r > self.arena['x'] + self.arena['width'] - 4:
                p['x'] = self.arena['x'] + self.arena['width'] - 4 - r
                p['vx'] = -abs(p['vx'])

            if p['y'] - r < self.arena['y'] + 4:
                p['y'] = self.arena['y'] + 4 + r
                p['vy'] = abs(p['vy'])
            elif p['y'] + r > self.arena['y'] + self.arena['height'] - 4:
                p['y'] = self.arena['y'] + self.arena['height'] - 4 - r
                p['vy'] = -abs(p['vy'])

            p['life'] -= dt
            if p['life'] <= 0:
                p['is_dead'] = True

        elif ptype == 'plate':
            p['y'] += p['vy'] * 60.0 * dt
            p['rotation'] += 6.0 * dt

        elif ptype == 'shrapnel':
            p['x'] += p['vx'] * 60.0 * dt
            p['y'] += p['vy'] * 60.0 * dt
            p['vy'] += 0.12 * 60.0 * dt # гравитация
            p['life'] -= dt
            if p['life'] <= 0:
                p['is_dead'] = True

        elif ptype == 'pearl':
            p['x'] += p['vx'] * 60.0 * dt
            p['y'] += p['vy'] * 60.0 * dt
            if (p['x'] < self.arena['x'] - 50 or p['x'] > self.arena['x'] + self.arena['width'] + 50 or
                p['y'] < self.arena['y'] - 50 or p['y'] > self.arena['y'] + self.arena['height'] + 50):
                p['is_dead'] = True

        elif ptype == 'missile':
            p['life'] -= dt
            if p['life'] <= 0:
                p['is_dead'] = True
            else:
                target_ang = math.atan2(player.y - p['y'], player.x - p['x'])
                diff = (target_ang - p['angle'] + math.pi) % (2 * math.pi) - math.pi
                p['angle'] += max(-p['turn_rate'], min(p['turn_rate'], diff))
                p['x'] += math.cos(p['angle']) * p['speed'] * 60.0 * dt
                p['y'] += math.sin(p['angle']) * p['speed'] * 60.0 * dt

        elif ptype == 'bomb':
            p['timer'] -= dt
            p['scale'] = 1.0 + math.sin(p['timer'] * 12.0) * 0.15
            if p['timer'] <= 0:
                p['exploded'] = True

        elif ptype == 'aura_slash':
            p['x'] += p['vx'] * 60.0 * dt
            if p['vx'] > 0 and p['x'] > self.arena['x'] + self.arena['width'] + 40:
                p['is_dead'] = True
            elif p['vx'] < 0 and p['x'] < self.arena['x'] - 40:
                p['is_dead'] = True

    def check_collision(self, p, player):
        if player.invulnerable_timer > 0 or player.is_dead:
            return False

        core = player.hitbox_radius
        ptype = p.get('type')
        if ptype == 'aura_slash':
            return (player.x + core > p['x'] and
                    player.x - core < p['x'] + p['width'] and
                    player.y + core > p['y'] and
                    player.y - core < p['y'] + p['height'])
        elif 'radius' in p:
            dx = player.x - p['x']
            dy = player.y - p['y']
            dist = math.sqrt(dx * dx + dy * dy)
            return dist < (p['radius'] * 0.82) + core
        return False

    def run_pattern(self, dt, player, boss, is_p2, is_p3, is_p4):
        self.pattern_cooldown -= dt
        cd_mult = self.cooldown_multiplier
        spd_mult = self.speed_multiplier

        if self.current_pattern == 0:
            # 0. «Лик Великого Тома» - Летающие головы Тома Перла
            count = len([p for p in self.projectiles if p.get('type') == 'tom_head'])
            limit = 3 if is_p4 else 2 if is_p3 else 1
            if count < limit:
                spd = (5.5 if is_p4 else 4.6 if is_p3 else 3.8) * spd_mult
                self.spawn_bouncing_tom_head(spd)

        elif self.current_pattern == 1:
            # 1. Падающие тарелки с особым блюдом
            if self.pattern_cooldown <= 0:
                spd = (6.8 if is_p4 else 5.8 if is_p3 else 4.8 if is_p2 else 4.0) * spd_mult
                self.spawn_falling_plate(spd)
                self.pattern_cooldown = (0.35 if is_p4 else 0.5 if is_p3 else 0.65 if is_p2 else 0.85) * cd_mult

        elif self.current_pattern == 2:
            # 2. Спиральный шквал жемчужин (Danmaku)
            if self.pattern_cooldown <= 0:
                self.spawn_spiral_pearl_wave(3 if is_p4 else 2)
                self.pattern_cooldown = (0.12 if is_p4 else 0.16 if is_p3 else 0.22) * cd_mult

        elif self.current_pattern == 3:
            # 3. Вантузный шторм Тома Перла
            if self.pattern_cooldown <= 0:
                self.spawn_plunger_barrage(is_p3 or is_p4)
                self.pattern_cooldown = (0.75 if is_p4 else 0.95 if is_p3 else 1.3) * cd_mult

        elif self.current_pattern == 4:
            # 4. Особое блюдо: Шоколадные гейзеры
            if self.pattern_cooldown <= 0 and len(self.geysers) < (3 if is_p4 else 2):
                self.spawn_sludge_geyser(is_p3 or is_p4)
                self.pattern_cooldown = (1.2 if is_p4 else 1.5 if is_p3 else 1.9) * cd_mult

        elif self.current_pattern == 5:
            # 5. Мега-удар тарелкой
            if self.pattern_cooldown <= 0:
                self.spawn_mega_plate_slam()
                self.pattern_cooldown = (1.8 if is_p4 else 2.2 if is_p3 else 2.8) * cd_mult

        elif self.current_pattern == 6:
            # 6. Таймер-бомба Тома Перла (Памперс)
            if self.pattern_cooldown <= 0 and len([p for p in self.projectiles if p.get('type') == 'bomb']) == 0:
                self.spawn_diaper_bomb()
                self.pattern_cooldown = (2.5 if is_p4 else 3.2) * cd_mult

        elif self.current_pattern == 7:
            # 7. Серповидные волны ауры 5.0
            if self.pattern_cooldown <= 0:
                self.spawn_aura_slash()
                self.pattern_cooldown = (0.55 if is_p4 else 0.75 if is_p3 else 1.0) * cd_mult

        elif self.current_pattern == 8:
            # 8. Нашествие туалетной бумаги
            if self.pattern_cooldown <= 0:
                self.spawn_toilet_paper(is_p4)
                self.pattern_cooldown = (0.85 if is_p4 else 1.2) * cd_mult

        elif self.current_pattern == 9:
            # 9. Квадро-бластерный крест
            if self.pattern_cooldown <= 0:
                self.spawn_quad_blaster()
                self.pattern_cooldown = (1.5 if is_p4 else 2.2) * cd_mult

    # 1. Летающие головы Тома Перла (вместо красных кубов)
    def spawn_bouncing_tom_head(self, speed=4.2):
        r = 20
        self.projectiles.append({
            'type': 'tom_head',
            'x': self.arena['x'] + 30 + random.random() * (self.arena['width'] - 60),
            'y': self.arena['y'] + 30,
            'radius': r,
            'vx': (1 if random.random() > 0.5 else -1) * speed,
            'vy': (0.7 + random.random() * 0.6) * speed,
            'angle': random.random() * 360.0,
            'rot_speed': (2.0 if random.random() > 0.5 else -2.0) * (1.5 + random.random()),
            'trail': [],
            'life': 8.0,
            'damage': 6,
            'destroy_on_hit': False,
            'is_dead': False
        })

    # 2. Падающая тарелка
    def spawn_falling_plate(self, speed=4.5):
        lane_x = self.arena['x'] + 25 + random.random() * (self.arena['width'] - 50)
        self.projectiles.append({
            'type': 'plate',
            'x': lane_x,
            'y': self.arena['y'] - 20,
            'radius': 17,
            'vy': speed + random.random() * 1.5,
            'rotation': 0.0,
            'damage': 5,
            'destroy_on_hit': True,
            'burst_on_destroy': True,
            'is_dead': False
        })

    # Осколки тарелки и брызги особого блюда
    def spawn_plate_shrapnel(self, x, y):
        for ang in (-2.4, -1.57, -0.74):
            spd = (3.8 + random.random() * 1.5) * self.speed_multiplier
            self.projectiles.append({
                'type': 'shrapnel',
                'x': x,
                'y': y,
                'radius': 6,
                'vx': math.cos(ang) * spd,
                'vy': math.sin(ang) * spd,
                'life': 1.0,
                'damage': 5,
                'destroy_on_hit': True,
                'is_dead': False
            })

    # 3. Спираль жемчужин Тома Перла
    def spawn_spiral_pearl_wave(self, arms=2):
        self.spiral_angle += 0.28
        center_x = self.arena['x'] + self.arena['width'] / 2.0
        center_y = self.arena['y'] + 35.0
        spd = 3.8 * self.speed_multiplier
        for i in range(arms):
            ang = self.spiral_angle + (i * math.pi * 2.0 / arms)
            self.projectiles.append({
                'type': 'pearl',
                'x': center_x,
                'y': center_y,
                'radius': 9,
                'vx': math.cos(ang) * spd,
                'vy': math.sin(ang) * spd,
                'damage': 5,
                'destroy_on_hit': True,
                'is_dead': False
            })

    # 4. Вантузный шторм (Plunger Barrage)
    def spawn_plunger_barrage(self, is_p3=False):
        count = 3 if is_p3 else 2
        from_left = random.random() > 0.5
        for i in range(count):
            if from_left:
                sx = self.arena['x'] - 20
                sy = self.arena['y'] + 30 + (i + 0.5) * (self.arena['height'] - 60) / count
                target_x = self.arena['x'] + self.arena['width'] + 20
                target_y = sy + (random.random() - 0.5) * 50
            else:
                sx = self.arena['x'] + self.arena['width'] + 20
                sy = self.arena['y'] + 30 + (i + 0.5) * (self.arena['height'] - 60) / count
                target_x = self.arena['x'] - 20
                target_y = sy + (random.random() - 0.5) * 50

            ang = math.atan2(target_y - sy, target_x - sx)
            spd = (5.2 + random.random() * 1.5) * self.speed_multiplier
            self.projectiles.append({
                'type': 'plunger',
                'x': sx,
                'y': sy,
                'radius': 12,
                'angle': ang,
                'vx': math.cos(ang) * spd,
                'vy': math.sin(ang) * spd,
                'damage': 5,
                'destroy_on_hit': True,
                'is_dead': False
            })

    # 5. Особое блюдо: Шоколадные гейзеры со дна арены
    def spawn_sludge_geyser(self, is_p3=False):
        gw = 65 if is_p3 else 75
        gx = self.arena['x'] + 20 + random.random() * (self.arena['width'] - gw - 40)
        self.geysers.append({
            'x': gx,
            'y': self.arena['y'] + self.arena['height'] - 6,
            'w': gw,
            'h': self.arena['height'] - 60,
            'time': 0.0,
            'warning_duration': (0.75 if is_p3 else 0.95) / self.speed_multiplier,
            'erupt_duration': 0.60,
            'state': 'warning',
            'damage': 7
        })

    # 6. Мега-удар тарелкой
    def spawn_mega_plate_slam(self):
        left_side = random.random() > 0.5
        w = self.arena['width'] / 2.0 - 8
        h = self.arena['height'] - 16
        x = self.arena['x'] + 8 if left_side else self.arena['x'] + self.arena['width'] / 2.0
        y = self.arena['y'] + 8
        self.telegraphs.append({
            'x': x,
            'y': y,
            'w': w,
            'h': h,
            'time': 0.0,
            'warning_duration': 0.75 / self.speed_multiplier,
            'slam_duration': 0.35,
            'triggered': False
        })

    # 7. Таймер-бомба Тома Перла (Памперс)
    def spawn_diaper_bomb(self):
        self.projectiles.append({
            'type': 'bomb',
            'x': self.arena['x'] + self.arena['width'] / 2.0,
            'y': self.arena['y'] + self.arena['height'] / 2.0,
            'radius': 22,
            'timer': 2.8,
            'scale': 1.0,
            'exploded': False,
            'damage': 8,
            'destroy_on_hit': False,
            'is_dead': False
        })

    def explode_bomb(self, x, y):
        self.shake_amount = 12.0
        count = 8
        spd = 4.2 * self.speed_multiplier
        for i in range(count):
            ang = (i * math.pi * 2.0 / count)
            self.projectiles.append({
                'type': 'pearl',
                'x': x,
                'y': y,
                'radius': 8,
                'vx': math.cos(ang) * spd,
                'vy': math.sin(ang) * spd,
                'damage': 5,
                'destroy_on_hit': True,
                'is_dead': False
            })

    # 8. Серповидные волны ауры 5.0
    def spawn_aura_slash(self):
        from_left = random.random() > 0.5
        start_x = self.arena['x'] - 30 if from_left else self.arena['x'] + self.arena['width'] + 30
        lane_y = self.arena['y'] + 20 + random.random() * (self.arena['height'] - 60)
        spd = (5.5 if from_left else -5.5) * self.speed_multiplier
        self.projectiles.append({
            'type': 'aura_slash',
            'x': start_x,
            'y': lane_y,
            'width': 24,
            'height': 48,
            'vx': spd,
            'damage': 6,
            'destroy_on_hit': True,
            'is_dead': False
        })

    # 9. Нашествие рулонов туалетной бумаги
    def spawn_toilet_paper(self, is_p4=False):
        r = 14
        left = random.random() > 0.5
        sx = self.arena['x'] + r + 15 if left else self.arena['x'] + self.arena['width'] - r - 15
        sy = self.arena['y'] + 40
        spd = (4.8 + random.random() * 1.5) * self.speed_multiplier
        self.projectiles.append({
            'type': 'tp_roll',
            'x': sx,
            'y': sy,
            'radius': r,
            'vx': (spd if left else -spd),
            'vy': spd * 0.6,
            'angle': 0.0,
            'rot_speed': 6.0 if left else -6.0,
            'trail': [],
            'life': 7.5,
            'damage': 5,
            'destroy_on_hit': False,
            'is_dead': False
        })

    # 10. Квадро-бластер Тома Перла
    def spawn_quad_blaster(self):
        self.lasers.append({
            'axis': 'horizontal',
            'pos': self.arena['y'] + self.arena['height'] / 2.0,
            'thickness': 30,
            'time': 0.0,
            'warning_duration': 0.60 / self.speed_multiplier,
            'active_duration': 0.35,
            'damage': 6
        })
        self.lasers.append({
            'axis': 'vertical',
            'pos': self.arena['x'] + self.arena['width'] / 2.0,
            'thickness': 30,
            'time': 0.15,
            'warning_duration': 0.60 / self.speed_multiplier,
            'active_duration': 0.35,
            'damage': 6
        })

    def draw(self, screen, font=None):
        # 0. Предметы лечения (+HP жемчуг)
        for hp in self.heal_pickups:
            pulse = 1.0 + math.sin(hp['time'] * 2.0) * 0.2
            px, py = int(hp['x']), int(hp['y'])
            r = int(hp['radius'] * pulse)

            # Зеленое свечение
            glow_surf = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (0, 255, 102, 70), (r * 2, r * 2), int(r * 1.4))
            screen.blit(glow_surf, (px - r * 2, py - r * 2))

            # Жемчужина
            pygame.draw.circle(screen, (255, 255, 255), (px, py), r)
            pygame.draw.circle(screen, (0, 255, 102), (px, py), int(r * 0.7))

            # Белый крестик (+)
            pygame.draw.rect(screen, (255, 255, 255), (px - 2, py - 6, 4, 12))
            pygame.draw.rect(screen, (255, 255, 255), (px - 6, py - 2, 12, 4))

        # 1. Гейзеры жижи ("Special on my plate")
        for g in self.geysers:
            gx, gy, gw, gh = int(g['x']), int(g['y']), int(g['w']), int(g['h'])
            if g['state'] == 'warning':
                # Предупреждающая лужица на полу арены
                puddle = pygame.Rect(gx, gy - 8, gw, 14)
                pygame.draw.ellipse(screen, (100, 55, 20), puddle)
                pygame.draw.ellipse(screen, (255, 180, 50), puddle, 2)
                # Пузырьки
                bx = int(gx + (math.sin(g['time'] * 16.0) * 0.4 + 0.5) * gw)
                pygame.draw.circle(screen, (180, 110, 50), (bx, gy - 10), 4)
                if font:
                    warn_t = font.render("!", True, (255, 200, 0))
                    screen.blit(warn_t, (gx + gw // 2 - 4, gy - 26))
            elif g['state'] == 'erupting':
                # Извергающийся столб шоколадной жижи Тома Перла
                pillar = pygame.Rect(gx, gy - gh, gw, gh)
                pygame.draw.rect(screen, (85, 45, 15), pillar, border_top_left_radius=8, border_top_right_radius=8)
                pygame.draw.rect(screen, (160, 95, 35), pillar, 3, border_top_left_radius=8, border_top_right_radius=8)
                # Бурлящие пузыри внутри
                for i in range(4):
                    by = int(gy - (i + 0.8) * (gh / 4.5))
                    bx = int(gx + gw / 2.0 + math.sin(g['time'] * 22.0 + i * 1.5) * (gw / 3.5))
                    pygame.draw.circle(screen, (190, 120, 50), (bx, by), 5)

        # 2. Телеграфы Мега-удара тарелкой
        for t in self.telegraphs:
            rect = pygame.Rect(int(t['x']), int(t['y']), int(t['w']), int(t['h']))
            if t['time'] < t['warning_duration']:
                flash = (int(pygame.time.get_ticks() / 90) % 2 == 0)
                alpha = 90 if flash else 50
                warn_surf = pygame.Surface((int(t['w']), int(t['h'])), pygame.SRCALPHA)
                warn_surf.fill((255, 0, 0, alpha))
                screen.blit(warn_surf, rect)
                pygame.draw.rect(screen, (255, 0, 0), rect, 3)
                if font:
                    txt = font.render("! DANGER !", True, (255, 255, 0))
                    t_rect = txt.get_rect(center=rect.center)
                    screen.blit(txt, t_rect)
            else:
                slam_surf = pygame.Surface((int(t['w']), int(t['h'])), pygame.SRCALPHA)
                slam_surf.fill((255, 255, 255, 220))
                screen.blit(slam_surf, rect)
                inner = rect.inflate(-16, -16)
                inner_surf = pygame.Surface((inner.width, inner.height), pygame.SRCALPHA)
                inner_surf.fill((140, 75, 30, 200)) # цвет жижи на тарелке
                screen.blit(inner_surf, inner)

        # 3. Лазеры
        for laser in self.lasers:
            if laser['axis'] == 'horizontal':
                pos_y = int(laser['pos'])
                top_y = int(laser['pos'] - laser['thickness'] / 2.0)
                lx = int(self.arena['x'] + 4)
                lw = int(self.arena['width'] - 8)
                if laser['time'] < laser['warning_duration']:
                    alpha = 200 if (int(pygame.time.get_ticks() / 80) % 2 == 0) else 90
                    line_surf = pygame.Surface((lw, 4), pygame.SRCALPHA)
                    line_surf.fill((255, 50, 50, alpha))
                    screen.blit(line_surf, (lx, pos_y - 2))
                    if font:
                        t1 = font.render("!", True, (255, 0, 0))
                        screen.blit(t1, (lx + 12, pos_y - 6))
                        screen.blit(t1, (lx + lw - 24, pos_y - 6))
                else:
                    beam_surf = pygame.Surface((lw, int(laser['thickness'])), pygame.SRCALPHA)
                    beam_surf.fill((255, 255, 255, 240))
                    screen.blit(beam_surf, (lx, top_y))
                    core_surf = pygame.Surface((lw, int(laser['thickness'] - 8)), pygame.SRCALPHA)
                    core_surf.fill((255, 20, 20, 190))
                    screen.blit(core_surf, (lx, top_y + 4))
            else:
                pos_x = int(laser['pos'])
                left_x = int(laser['pos'] - laser['thickness'] / 2.0)
                ly = int(self.arena['y'] + 4)
                lh = int(self.arena['height'] - 8)
                if laser['time'] < laser['warning_duration']:
                    alpha = 200 if (int(pygame.time.get_ticks() / 80) % 2 == 0) else 90
                    line_surf = pygame.Surface((4, lh), pygame.SRCALPHA)
                    line_surf.fill((255, 50, 50, alpha))
                    screen.blit(line_surf, (pos_x - 2, ly))
                else:
                    beam_surf = pygame.Surface((int(laser['thickness']), lh), pygame.SRCALPHA)
                    beam_surf.fill((255, 255, 255, 240))
                    screen.blit(beam_surf, (left_x, ly))
                    core_surf = pygame.Surface((int(laser['thickness'] - 8), lh), pygame.SRCALPHA)
                    core_surf.fill((255, 20, 20, 190))
                    screen.blit(core_surf, (left_x + 4, ly))

        # 4. Снаряды
        for p in self.projectiles:
            ptype = p.get('type')
            px, py = int(p['x']), int(p['y'])

            if ptype == 'tom_head':
                r = p['radius']
                # Шлейф аур
                for idx, pt in enumerate(p['trail']):
                    a = int((idx + 1) / (len(p['trail']) + 1) * 75)
                    scaled_t = pygame.transform.scale(self.tom_head_surf, (r * 2, r * 2))
                    scaled_t.set_alpha(a)
                    screen.blit(scaled_t, scaled_t.get_rect(center=(int(pt[0]), int(pt[1]))))

                # Вращение головы Тома
                rot_surf = pygame.transform.rotate(self.tom_head_surf, p['angle'])
                # Золотистый ореол ауры
                glow = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 215, 0, 45), (int(r * 1.5), int(r * 1.5)), int(r * 1.3))
                screen.blit(glow, (px - int(r * 1.5), py - int(r * 1.5)))
                screen.blit(rot_surf, rot_surf.get_rect(center=(px, py)))

            elif ptype == 'plunger':
                # Вантуз Тома Перла
                deg = -math.degrees(p['angle'])
                rot_p = pygame.transform.rotate(self.plunger_surf, deg)
                screen.blit(rot_p, rot_p.get_rect(center=(px, py)))

            elif ptype == 'tp_roll':
                # Рулон туалетной бумаги со шлейфом
                if len(p['trail']) > 1:
                    pts = [(int(pt[0]), int(pt[1])) for pt in p['trail']]
                    pygame.draw.lines(screen, (245, 245, 245), False, pts, 4)
                    pygame.draw.lines(screen, (180, 180, 180), False, pts, 1)

                rot_tp = pygame.transform.rotate(self.tp_roll_surf, p['angle'])
                screen.blit(rot_tp, rot_tp.get_rect(center=(px, py)))

            elif ptype == 'plate':
                r = p['radius']
                pygame.draw.circle(screen, (240, 235, 220), (px, py), r)
                pygame.draw.circle(screen, (200, 190, 175), (px, py), int(r * 0.75))
                # Особое блюдо в центре тарелки
                pygame.draw.circle(screen, (90, 50, 20), (px, py), int(r * 0.45))
                pygame.draw.circle(screen, (255, 255, 255), (px, py), r, 2)

            elif ptype == 'shrapnel':
                r = p['radius']
                # Брызги блюда Тома
                pygame.draw.circle(screen, (110, 65, 25), (px, py), r)
                pygame.draw.circle(screen, (70, 35, 15), (px, py), max(1, int(r * 0.5)))
                pygame.draw.circle(screen, (255, 200, 100), (px, py), r, 1)

            elif ptype == 'pearl':
                r = p['radius']
                pygame.draw.circle(screen, (255, 255, 0), (px, py), r)
                pygame.draw.circle(screen, (255, 255, 255), (px, py), max(1, int(r * 0.55)))

            elif ptype == 'missile':
                r = p['radius']
                pygame.draw.circle(screen, (255, 40, 40), (px, py), r)
                pygame.draw.circle(screen, (255, 255, 0), (px, py), max(1, int(r * 0.55)))
                tip_x = int(px + math.cos(p['angle']) * (r + 4))
                tip_y = int(py + math.sin(p['angle']) * (r + 4))
                pygame.draw.circle(screen, (255, 255, 255), (tip_x, tip_y), 3)

            elif ptype == 'bomb':
                r = int(p['radius'] * p['scale'])
                pygame.draw.circle(screen, (255, 255, 255), (px, py), r)
                pygame.draw.circle(screen, (255, 0, 85), (px, py), int(r * 0.8))
                pygame.draw.circle(screen, (0, 0, 0), (px, py), r, 2)
                if font:
                    sec = max(0, int(math.ceil(p['timer'])))
                    t_sec = font.render(str(sec), True, (255, 255, 255))
                    s_rect = t_sec.get_rect(center=(px, py))
                    screen.blit(t_sec, s_rect)

            elif ptype == 'aura_slash':
                pw, ph = p['width'], p['height']
                slash_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
                pygame.draw.ellipse(slash_surf, (255, 0, 85, 220), (0, 0, pw, ph))
                pygame.draw.ellipse(slash_surf, (255, 255, 255, 255), (2, 2, pw - 4, ph - 4))
                screen.blit(slash_surf, (px, py))
