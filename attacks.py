# attacks.py - Атаки Тома Перла (Undertale / Omega Flowey Edition)
import os
import math
import random
import pygame

from utils import get_asset_path
from audio import audio_manager

def dist_to_segment(px, py, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)

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
        pygame.draw.rect(self.plunger_surf, (175, 115, 55), (0, 8, 22, 6), border_radius=2)
        pygame.draw.rect(self.plunger_surf, (115, 70, 30), (0, 8, 22, 6), 1, border_radius=2)
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

        # 4. Спрайт Руки-Пушки Омега Флауи (Finger Gun)
        self.finger_gun_surf = pygame.Surface((56, 32), pygame.SRCALPHA)
        # Рука и ладонь
        pygame.draw.ellipse(self.finger_gun_surf, (210, 180, 150), (4, 8, 30, 18))
        pygame.draw.ellipse(self.finger_gun_surf, (140, 110, 85), (4, 8, 30, 18), 2)
        # Вытянутый палец-ствол
        pygame.draw.rect(self.finger_gun_surf, (225, 195, 165), (26, 10, 26, 8), border_radius=3)
        pygame.draw.rect(self.finger_gun_surf, (140, 110, 85), (26, 10, 26, 8), 2, border_radius=3)
        # Взведенный большой палец (курок)
        pygame.draw.polygon(self.finger_gun_surf, (215, 185, 155), [(14, 10), (18, 0), (25, 6), (20, 10)])
        pygame.draw.polygon(self.finger_gun_surf, (140, 110, 85), [(14, 10), (18, 0), (25, 6), (20, 10)], 2)
        # Ствол дула
        pygame.draw.circle(self.finger_gun_surf, (50, 40, 35), (51, 14), 4)

        self.reset()

    def reset(self, difficulty=None):
        diff = difficulty or {'speedMultiplier': 1.0, 'cooldownMultiplier': 1.0, 'healInterval': 40, 'healAmount': 20}
        self.speed_multiplier = diff.get('speedMultiplier', 1.0)
        self.cooldown_multiplier = diff.get('cooldownMultiplier', 1.0)
        self.heal_interval = diff.get('healInterval', 40)
        self.heal_amount = diff.get('healAmount', 20)
        self.heal_timer = 0.0
        self.heal_pickups = []

        # Коллекции атак в стиле Omega Flowey
        self.projectiles = []
        self.reticles = []        # 0. Прицелы и авиаудары бомбами
        self.vines = []           # 1. Омега-лозы с шипами
        self.mouth_beam = None    # 2. Колоссальный луч изо рта Тома Перла
        self.finger_guns = []     # 3. Руки-пушки с пальцами
        self.dentata_rings = []   # 4. Сжимающиеся кольца зубов/жемчужин
        self.geysers = []         # Гейзеры шоколадной жижи
        self.lasers = []          # Дополнительные квадро-бластеры
        self.telegraphs = []      # Зоны мега-ударов тарелкой
        self.glitch_banner = None # Баннер [ FILE 1 LOADED ]

        self.current_pattern = 0
        self.pattern_cooldown = 0.3 * self.cooldown_multiplier
        self.pattern_time = 0.0
        self.spiral_angle = 0.0
        self.shake_amount = 0.0

    def on_phase_change(self, phase):
        # Очистить опасные снаряды и лозы при смене фазы, дать игроку передышку
        self.projectiles = [p for p in self.projectiles if p.get('type') == 'tom_head']
        self.vines = []
        self.reticles = []
        self.finger_guns = []
        self.dentata_rings = []
        self.mouth_beam = None
        self.geysers = []
        self.telegraphs = []
        self.lasers = []

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
            if boss:
                boss.beam_charging = False
                boss.beam_firing = False
            return

        self.pattern_time += dt

        if self.shake_amount > 0:
            self.shake_amount = max(0.0, self.shake_amount - dt * 25.0)

        # 1. Обновление предметов лечения (Heal Pickups)
        for hp in self.heal_pickups[:]:
            hp['time'] += dt * 3.5
            hp['y'] = hp['base_y'] + math.sin(hp['time']) * 5.0
            hp['life'] -= dt

            dx = player.x - hp['x']
            dy = player.y - hp['y']
            dist = math.hypot(dx, dy)
            if dist < hp['radius'] + player.size / 2.0:
                player.heal(hp['amount'])
                audio_manager.play_heal_sound()
                self.heal_pickups.remove(hp)
                continue

            if hp['life'] <= 0:
                self.heal_pickups.remove(hp)

        if self.heal_interval > 0:
            self.heal_timer += dt
            if self.heal_timer >= self.heal_interval:
                self.heal_timer = 0.0
                self.spawn_heal_pickup(self.heal_amount)

        # 2. Определение фаз босса
        p2_th = boss.max_hp * 0.75
        p3_th = boss.max_hp * 0.50
        p4_th = boss.max_hp * 0.20
        is_p2 = boss.hp <= p2_th and boss.hp > p3_th
        is_p3 = boss.hp <= p3_th and boss.hp > p4_th
        is_p4 = boss.hp <= p4_th

        # Динамическая смена 10 паттернов в стиле Omega Flowey
        pattern_cycle_time = (3.2 if is_p4 else 3.8 if is_p3 else 4.4 if is_p2 else 5.0) * self.cooldown_multiplier
        if self.pattern_time > pattern_cycle_time:
            self.pattern_time = 0.0
            self.current_pattern = (self.current_pattern + 1) % 10
            self.pattern_cooldown = 0.15 * self.cooldown_multiplier

        # Фоновый летающий Лик Тома в поздних фазах
        max_bg = 2 if is_p4 else 1 if is_p3 else 0
        current_heads = len([p for p in self.projectiles if p.get('type') == 'tom_head'])
        if current_heads < max_bg:
            spd = (5.2 if is_p4 else 4.2) * self.speed_multiplier
            self.spawn_bouncing_tom_head(spd)

        # Запуск активного паттерна
        self.run_pattern(dt, player, boss, is_p2, is_p3, is_p4)

        # Обновление всех элементов боя
        self._update_reticles(dt, player)
        self._update_vines(dt, player)
        self._update_mouth_beam(dt, player, boss)
        self._update_finger_guns(dt, player)
        self._update_dentata_rings(dt, player)
        self._update_glitch_banner(dt)

        # Обновление снарядов
        for p in self.projectiles[:]:
            self._update_projectile(p, dt, player)

            if self.check_collision(p, player):
                player.take_damage(p.get('damage', 5))
                if p.get('destroy_on_hit', False):
                    if p.get('type') == 'plate' and p.get('burst_on_destroy', False):
                        self.spawn_plate_shrapnel(p['x'], p['y'])
                    self.projectiles.remove(p)
                    continue

            if p.get('type') == 'plate' and p['y'] >= self.arena['y'] + self.arena['height'] - 10:
                self.spawn_plate_shrapnel(p['x'], p['y'])
                self.projectiles.remove(p)
                continue

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

        # Обновление телеграфов зон поражения
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

    # ==================== ОМЕГА-ОБНОВЛЕНИЯ ====================

    def _update_reticles(self, dt, player):
        for r in self.reticles[:]:
            r['time'] += dt
            r['angle'] += dt * 3.5

            if r['state'] == 'tracking':
                # Плавное следование за позицией души игрока
                r['x'] += (player.x - r['x']) * 4.8 * dt
                r['y'] += (player.y - r['y']) * 4.8 * dt

                # Звуковые бипы при слежении
                r['beep_timer'] -= dt
                if r['beep_timer'] <= 0:
                    r['beep_timer'] = 0.22
                    audio_manager.play_target_beep()

                if r['time'] >= r['track_duration']:
                    r['state'] = 'locked'
                    r['time'] = 0.0
                    audio_manager.play_target_beep()

            elif r['state'] == 'locked':
                # Фиксация и мигание красным перед падением бомбы
                if r['time'] >= r['lock_duration']:
                    r['state'] = 'dropping'
                    r['bomb_y'] = self.arena['y'] - 40.0
                    r['bomb_speed'] = 650.0 * self.speed_multiplier

            elif r['state'] == 'dropping':
                # Скоростное падение бомбы/тарелки с неба
                r['bomb_y'] += r['bomb_speed'] * dt
                if r['bomb_y'] >= r['y']:
                    # Взрыв в точке прицела
                    self.shake_amount = max(self.shake_amount, 9.0)
                    dist = math.hypot(player.x - r['x'], player.y - r['y'])
                    if dist < 42.0 + player.hitbox_radius:
                        player.take_damage(8)

                    # Радиальный разлет 6 осколков-жемчужин
                    for i in range(6):
                        ang = i * (math.pi * 2.0 / 6.0)
                        spd = 4.2 * self.speed_multiplier
                        self.projectiles.append({
                            'type': 'pearl',
                            'x': r['x'],
                            'y': r['y'],
                            'radius': 7,
                            'vx': math.cos(ang) * spd,
                            'vy': math.sin(ang) * spd,
                            'damage': 5,
                            'destroy_on_hit': True,
                            'is_dead': False
                        })

                    self.reticles.remove(r)

    def _update_vines(self, dt, player):
        for v in self.vines[:]:
            v['time'] += dt
            if v['state'] == 'warning':
                if v['time'] >= v['warn_duration']:
                    v['state'] = 'striking'
                    v['time'] = 0.0
                    self.shake_amount = max(self.shake_amount, 5.0)
                    audio_manager.play_vine_whip()
            elif v['state'] == 'striking':
                # Проверка столкновения с шипастой лозой
                dist = dist_to_segment(player.x, player.y, v['x1'], v['y1'], v['x2'], v['y2'])
                if dist < (v['thickness'] * 0.45) + player.hitbox_radius:
                    player.take_damage(v.get('damage', 6))

                if v['time'] >= v['strike_duration']:
                    self.vines.remove(v)

    def _update_mouth_beam(self, dt, player, boss):
        if not self.mouth_beam:
            boss.beam_charging = False
            boss.beam_firing = False
            return

        mb = self.mouth_beam
        mb['time'] += dt

        if mb['state'] == 'charging':
            boss.beam_charging = True
            boss.beam_firing = False
            self.shake_amount = max(self.shake_amount, 2.5)

            # Слежение за позицией X игрока в начале заряда
            if mb['time'] < mb['charge_duration'] * 0.6:
                mb['x'] += (player.x - mb['x']) * 4.0 * dt

            if mb['time'] >= mb['charge_duration']:
                mb['state'] = 'firing'
                mb['time'] = 0.0
                boss.beam_charging = False
                boss.beam_firing = True
                self.shake_amount = max(self.shake_amount, 14.0)
                audio_manager.play_beam_fire()

        elif mb['state'] == 'firing':
            boss.beam_charging = False
            boss.beam_firing = True
            self.shake_amount = max(self.shake_amount, 8.0)

            # Проверка урона колоссального луча
            core = player.hitbox_radius
            hw = mb['width'] / 2.0
            if (player.x + core > mb['x'] - hw and
                player.x - core < mb['x'] + hw and
                player.y + core > mb['top_y'] and
                player.y - core < mb['bottom_y']):
                player.take_damage(mb.get('damage', 8))

            if mb['time'] >= mb['fire_duration']:
                boss.beam_firing = False
                self.mouth_beam = None

    def _update_finger_guns(self, dt, player):
        for fg in self.finger_guns[:]:
            fg['time'] += dt
            # Плавный выезд руки к арене
            if fg['anim_in']:
                fg['x'] += (fg['target_x'] - fg['x']) * 8.0 * dt
                fg['y'] += (fg['target_y'] - fg['y']) * 8.0 * dt
                if abs(fg['x'] - fg['target_x']) < 3.0:
                    fg['anim_in'] = False

            # Прицеливание пальца в душу игрока
            fg['angle'] = math.atan2(player.y - fg['y'], player.x - fg['x'])

            # Стрельба очередью жемчужин
            if fg['shots_left'] > 0:
                fg['shot_timer'] -= dt
                if fg['shot_timer'] <= 0:
                    fg['shot_timer'] = 0.16 / self.speed_multiplier
                    fg['shots_left'] -= 1
                    audio_manager.play_finger_pew()

                    # Спавн скоростной жемчужины из кончика пальца
                    tip_x = fg['x'] + math.cos(fg['angle']) * 32.0
                    tip_y = fg['y'] + math.sin(fg['angle']) * 32.0
                    spd = 5.6 * self.speed_multiplier
                    self.projectiles.append({
                        'type': 'pearl',
                        'x': tip_x,
                        'y': tip_y,
                        'radius': 8,
                        'vx': math.cos(fg['angle']) * spd,
                        'vy': math.sin(fg['angle']) * spd,
                        'damage': 5,
                        'destroy_on_hit': True,
                        'is_dead': False
                    })

            # Уход руки обратно за границу экрана
            if fg['shots_left'] <= 0 and fg['time'] > 1.2:
                fg['x'] += (fg['start_x'] - fg['x']) * 6.0 * dt
                if abs(fg['x'] - fg['start_x']) < 4.0:
                    self.finger_guns.remove(fg)

    def _update_dentata_rings(self, dt, player):
        for ring in self.dentata_rings[:]:
            ring['time'] += dt
            ring['radius'] -= ring['shrink_speed'] * dt
            ring['current_angle'] += ring['rot_speed'] * dt

            # Проверка столкновения с каждым зубом кольца
            core = player.hitbox_radius
            for ang in ring['teeth_angles']:
                tooth_ang = ring['current_angle'] + ang
                tx = ring['center_x'] + math.cos(tooth_ang) * ring['radius']
                ty = ring['center_y'] + math.sin(tooth_ang) * ring['radius']
                dist = math.hypot(player.x - tx, player.y - ty)
                if dist < 8.0 + core:
                    player.take_damage(ring.get('damage', 5))
                    break

            if ring['radius'] <= 16.0:
                self.dentata_rings.remove(ring)

    def _update_glitch_banner(self, dt):
        if self.glitch_banner:
            self.glitch_banner['timer'] -= dt
            if self.glitch_banner['timer'] <= 0:
                self.glitch_banner = None

    # ==================== ОБНОВЛЕНИЕ СНАРЯДОВ ====================

    def _update_projectile(self, p, dt, player):
        ptype = p.get('type')

        if ptype == 'tom_head':
            p['trail'].append((p['x'], p['y']))
            if len(p['trail']) > 5:
                p['trail'].pop(0)

            p['x'] += p['vx'] * 60.0 * dt
            p['y'] += p['vy'] * 60.0 * dt
            p['angle'] += p['rot_speed'] * 60.0 * dt

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
            p['vy'] += 0.12 * 60.0 * dt
            p['life'] -= dt
            if p['life'] <= 0:
                p['is_dead'] = True

        elif ptype == 'pearl':
            p['x'] += p['vx'] * 60.0 * dt
            p['y'] += p['vy'] * 60.0 * dt
            if (p['x'] < self.arena['x'] - 50 or p['x'] > self.arena['x'] + self.arena['width'] + 50 or
                p['y'] < self.arena['y'] - 50 or p['y'] > self.arena['y'] + self.arena['height'] + 50):
                p['is_dead'] = True

        elif ptype == 'sludge_bullet':
            p['x'] += p['vx'] * 60.0 * dt
            p['y'] += p['vy'] * 60.0 * dt
            p['scale'] = 1.0 + math.sin(p.get('time', 0.0) * 12.0) * 0.2
            p['time'] = p.get('time', 0.0) + dt
            if (p['x'] < self.arena['x'] - 30 or p['x'] > self.arena['x'] + self.arena['width'] + 30 or
                p['y'] < self.arena['y'] - 30 or p['y'] > self.arena['y'] + self.arena['height'] + 30):
                p['is_dead'] = True

        elif ptype == 'bomb':
            p['timer'] -= dt
            p['scale'] = 1.0 + math.sin(p['timer'] * 12.0) * 0.15
            if p['timer'] <= 0:
                p['exploded'] = True

    def check_collision(self, p, player):
        if player.invulnerable_timer > 0 or player.is_dead:
            return False

        core = player.hitbox_radius
        if 'radius' in p:
            dx = player.x - p['x']
            dy = player.y - p['y']
            dist = math.hypot(dx, dy)
            return dist < (p['radius'] * 0.82) + core
        return False

    # ==================== 10 ПАТТЕРНОВ OMEGA FLOWEY ====================

    def run_pattern(self, dt, player, boss, is_p2, is_p3, is_p4):
        self.pattern_cooldown -= dt
        cd_mult = self.cooldown_multiplier
        spd_mult = self.speed_multiplier

        if self.current_pattern == 0:
            # 0. Прицел и Авиаудар (Omega Target Reticles)
            if self.pattern_cooldown <= 0 and len(self.reticles) < (3 if is_p4 else 2):
                self.spawn_target_reticle(player)
                self.pattern_cooldown = (0.75 if is_p4 else 1.1 if is_p3 else 1.4) * cd_mult

        elif self.current_pattern == 1:
            # 1. Шипастые Омега-Лозы (Thorny Omega Vines)
            if self.pattern_cooldown <= 0 and len(self.vines) < (4 if is_p4 else 3):
                self.spawn_thorny_vine(player, is_p4)
                self.pattern_cooldown = (0.65 if is_p4 else 0.85 if is_p3 else 1.1) * cd_mult

        elif self.current_pattern == 2:
            # 2. Колоссальный Луч изо рта Тома Перла (Colossal Mouth Beam)
            if self.pattern_cooldown <= 0 and not self.mouth_beam:
                self.spawn_colossal_mouth_beam(boss, player)
                self.pattern_cooldown = (2.2 if is_p4 else 2.8) * cd_mult

        elif self.current_pattern == 3:
            # 3. Руки-Пушки с пальцами Омега Флауи (Finger Guns)
            if self.pattern_cooldown <= 0 and len(self.finger_guns) < (2 if is_p4 else 1):
                self.spawn_finger_gun(player)
                self.pattern_cooldown = (1.1 if is_p4 else 1.5) * cd_mult

        elif self.current_pattern == 4:
            # 4. Сжимающиеся кольца зубов (Dentata Teeth Rings)
            if self.pattern_cooldown <= 0 and len(self.dentata_rings) == 0:
                self.spawn_dentata_ring(player)
                self.pattern_cooldown = (2.4 if is_p4 else 3.0) * cd_mult

        elif self.current_pattern == 5:
            # 5. Огнемет шоколадной жижи Тома (Sludge Flamethrower)
            if self.pattern_cooldown <= 0:
                self.spawn_sludge_flamethrower_stream(boss)
                self.pattern_cooldown = (0.09 if is_p4 else 0.12 if is_p3 else 0.16) * cd_mult

        elif self.current_pattern == 6:
            # 6. Глитч-атака [ FILE 1 LOADED ] (SAVE/LOAD)
            if self.pattern_cooldown <= 0:
                self.trigger_file_load_glitch(boss, player)
                self.pattern_cooldown = (2.5 if is_p4 else 3.4) * cd_mult

        elif self.current_pattern == 7:
            # 7. Вантузная стена Тома Перла (Plunger Barrage Wall)
            if self.pattern_cooldown <= 0:
                self.spawn_plunger_wall()
                self.pattern_cooldown = (0.85 if is_p4 else 1.1 if is_p3 else 1.4) * cd_mult

        elif self.current_pattern == 8:
            # 8. Памперс-Бомба и Летающий Лик Тома (Diaper Bomb & Mini Tom)
            if self.pattern_cooldown <= 0 and len([p for p in self.projectiles if p.get('type') == 'bomb']) == 0:
                self.spawn_diaper_bomb()
                self.pattern_cooldown = (2.2 if is_p4 else 3.0) * cd_mult

        elif self.current_pattern == 9:
            # 9. Омега-Финал: Шквал ауры и дождь тарелок
            if self.pattern_cooldown <= 0:
                self.spawn_falling_plate(6.2 * spd_mult)
                if random.random() > 0.4:
                    self.spawn_spiral_pearl_wave(2 if is_p3 else 3)
                self.pattern_cooldown = (0.32 if is_p4 else 0.45) * cd_mult

    # ==================== СПАВНЕРЫ ПАТТЕРНОВ ====================

    # 0. Прицел и Авиаудар
    def spawn_target_reticle(self, player):
        offset_x = (random.random() - 0.5) * 60.0
        offset_y = (random.random() - 0.5) * 60.0
        self.reticles.append({
            'x': player.x + offset_x,
            'y': player.y + offset_y,
            'state': 'tracking',
            'time': 0.0,
            'track_duration': 0.85 / self.speed_multiplier,
            'lock_duration': 0.35 / self.speed_multiplier,
            'beep_timer': 0.0,
            'angle': 0.0,
            'bomb_y': 0.0,
            'bomb_speed': 600.0
        })

    # 1. Шипастые Омега-Лозы
    def spawn_thorny_vine(self, player, is_p4=False):
        ax = self.arena['x']
        ay = self.arena['y']
        aw = self.arena['width']
        ah = self.arena['height']

        mode = random.choice(['diag1', 'diag2', 'horiz', 'vert'])
        if mode == 'diag1':
            x1, y1 = ax, ay + random.random() * (ah * 0.4)
            x2, y2 = ax + aw, ay + ah - random.random() * (ah * 0.4)
        elif mode == 'diag2':
            x1, y1 = ax + aw, ay + random.random() * (ah * 0.4)
            x2, y2 = ax, ay + ah - random.random() * (ah * 0.4)
        elif mode == 'horiz':
            y = ay + 20 + random.random() * (ah - 40)
            x1, y1 = ax, y
            x2, y2 = ax + aw, y
        else: # vert
            x = ax + 20 + random.random() * (aw - 40)
            x1, y1 = x, ay
            x2, y2 = x, ay + ah

        self.vines.append({
            'x1': x1, 'y1': y1,
            'x2': x2, 'y2': y2,
            'state': 'warning',
            'time': 0.0,
            'warn_duration': (0.55 if is_p4 else 0.75) / self.speed_multiplier,
            'strike_duration': 0.32,
            'thickness': 22,
            'damage': 7
        })

    # 2. Колоссальный Луч изо рта Тома Перла
    def spawn_colossal_mouth_beam(self, boss, player):
        audio_manager.play_beam_charge()
        top_y = self.arena['y'] - 10
        bottom_y = self.arena['y'] + self.arena['height'] + 10
        self.mouth_beam = {
            'x': boss.x,
            'top_y': top_y,
            'bottom_y': bottom_y,
            'width': 92,
            'state': 'charging',
            'time': 0.0,
            'charge_duration': 0.85 / self.speed_multiplier,
            'fire_duration': 0.90,
            'damage': 8
        }

    # 3. Рука-Пушка Омега Флауи
    def spawn_finger_gun(self, player):
        from_left = random.random() > 0.5
        ay = self.arena['y'] + 40 + random.random() * (self.arena['height'] - 80)
        start_x = self.arena['x'] - 60 if from_left else self.arena['x'] + self.arena['width'] + 60
        target_x = self.arena['x'] + 25 if from_left else self.arena['x'] + self.arena['width'] - 25

        self.finger_guns.append({
            'x': start_x,
            'y': ay,
            'start_x': start_x,
            'target_x': target_x,
            'target_y': ay,
            'anim_in': True,
            'angle': 0.0,
            'time': 0.0,
            'shots_left': 4,
            'shot_timer': 0.35,
            'from_left': from_left
        })

    # 4. Сжимающиеся кольца зубов (Dentata)
    def spawn_dentata_ring(self, player):
        center_x = player.x + (random.random() - 0.5) * 30
        center_y = player.y + (random.random() - 0.5) * 30
        # Ограничение центром арены
        center_x = max(self.arena['x'] + 60, min(self.arena['x'] + self.arena['width'] - 60, center_x))
        center_y = max(self.arena['y'] + 60, min(self.arena['y'] + self.arena['height'] - 60, center_y))

        num_teeth = 14
        teeth_angles = []
        # Пропуск 2-3 зубов для прохода игрока (Escape Gap)
        gap_start = random.randint(0, num_teeth - 1)
        gap_span = 3
        for i in range(num_teeth):
            if (i - gap_start) % num_teeth >= gap_span:
                teeth_angles.append(i * (2.0 * math.pi / num_teeth))

        self.dentata_rings.append({
            'center_x': center_x,
            'center_y': center_y,
            'radius': 150.0,
            'shrink_speed': 72.0 * self.speed_multiplier,
            'current_angle': 0.0,
            'rot_speed': 1.6,
            'teeth_angles': teeth_angles,
            'time': 0.0,
            'damage': 6
        })

    # 5. Огнемет шоколадной жижи Тома (Sludge Flamethrower)
    def spawn_sludge_flamethrower_stream(self, boss):
        self.spiral_angle += 0.32
        sway = math.sin(self.spiral_angle) * 3.8
        spd = (5.5 + random.random() * 1.5) * self.speed_multiplier
        self.projectiles.append({
            'type': 'sludge_bullet',
            'x': boss.x + (random.random() - 0.5) * 20,
            'y': self.arena['y'] + 10,
            'radius': 9,
            'vx': sway,
            'vy': spd,
            'scale': 1.0,
            'time': 0.0,
            'damage': 5,
            'destroy_on_hit': True,
            'is_dead': False
        })

    # 6. Глитч-атака [ FILE 1 LOADED ]
    def trigger_file_load_glitch(self, boss, player):
        boss.trigger_glitch(0.7)
        self.shake_amount = 11.0
        file_num = 1 if boss.current_phase <= 2 else 2
        self.glitch_banner = {
            'text': f"[ FILE {file_num} LOADED ]",
            'timer': 1.4,
            'max_timer': 1.4
        }
        # Внезапная вспышка 8 глитч-снарядов вокруг игрока с разлетом
        spd = 3.6 * self.speed_multiplier
        for i in range(8):
            ang = i * (math.pi * 2.0 / 8.0)
            self.projectiles.append({
                'type': 'pearl',
                'x': player.x + math.cos(ang) * 95.0,
                'y': player.y + math.sin(ang) * 95.0,
                'radius': 7,
                'vx': math.cos(ang) * spd,
                'vy': math.sin(ang) * spd,
                'damage': 5,
                'destroy_on_hit': True,
                'is_dead': False
            })

    # 7. Вантузная стена Тома Перла
    def spawn_plunger_wall(self):
        from_left = random.random() > 0.5
        count = 5
        gap_idx = random.randint(1, count - 2)
        h = self.arena['height'] - 40
        spd = (4.8 + random.random() * 1.2) * self.speed_multiplier

        for i in range(count):
            if i == gap_idx or i == gap_idx + 1:
                continue # Окно для уворота
            sy = self.arena['y'] + 20 + (i + 0.5) * (h / count)
            sx = self.arena['x'] - 20 if from_left else self.arena['x'] + self.arena['width'] + 20
            ang = 0.0 if from_left else math.pi

            self.projectiles.append({
                'type': 'plunger',
                'x': sx,
                'y': sy,
                'radius': 12,
                'angle': ang,
                'vx': math.cos(ang) * spd,
                'vy': 0.0,
                'damage': 5,
                'destroy_on_hit': True,
                'is_dead': False
            })

    # 8. Памперс-Бомба Тома Перла
    def spawn_diaper_bomb(self):
        self.projectiles.append({
            'type': 'bomb',
            'x': self.arena['x'] + self.arena['width'] / 2.0,
            'y': self.arena['y'] + self.arena['height'] / 2.0,
            'radius': 22,
            'timer': 2.6,
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

    # 9. Летающая голова Тома
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

    # 10. Падающая тарелка и спираль
    def spawn_falling_plate(self, speed=5.0):
        lane_x = self.arena['x'] + 25 + random.random() * (self.arena['width'] - 50)
        self.projectiles.append({
            'type': 'plate',
            'x': lane_x,
            'y': self.arena['y'] - 20,
            'radius': 17,
            'vy': speed,
            'rotation': 0.0,
            'damage': 5,
            'destroy_on_hit': True,
            'burst_on_destroy': True,
            'is_dead': False
        })

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

    # ==================== ОТРИСОВКА (DRAW) ====================

    def draw(self, screen, font=None):
        # 0. Предметы лечения (+HP жемчуг)
        for hp in self.heal_pickups:
            pulse = 1.0 + math.sin(hp['time'] * 2.0) * 0.2
            px, py = int(hp['x']), int(hp['y'])
            r = int(hp['radius'] * pulse)

            glow_surf = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (0, 255, 102, 70), (r * 2, r * 2), int(r * 1.4))
            screen.blit(glow_surf, (px - r * 2, py - r * 2))

            pygame.draw.circle(screen, (255, 255, 255), (px, py), r)
            pygame.draw.circle(screen, (0, 255, 102), (px, py), int(r * 0.7))
            pygame.draw.rect(screen, (255, 255, 255), (px - 2, py - 6, 4, 12))
            pygame.draw.rect(screen, (255, 255, 255), (px - 6, py - 2, 12, 4))

        # 1. Колоссальный Луч изо рта Тома Перла (Colossal Mouth Beam)
        if self.mouth_beam:
            mb = self.mouth_beam
            bx = int(mb['x'])
            by1 = int(mb['top_y'])
            by2 = int(mb['bottom_y'])
            bw = int(mb['width'])
            bh = by2 - by1

            if mb['state'] == 'charging':
                alpha = 180 if (int(pygame.time.get_ticks() / 70) % 2 == 0) else 70
                warn_s = pygame.Surface((bw, bh), pygame.SRCALPHA)
                warn_s.fill((255, 40, 40, alpha))
                screen.blit(warn_s, (bx - bw // 2, by1))
                pygame.draw.rect(screen, (255, 220, 0), (bx - bw // 2, by1, bw, bh), 3)
                if font:
                    txt = font.render("! WARNING !", True, (255, 255, 0))
                    t_rect = txt.get_rect(center=(bx, by1 + bh // 2))
                    screen.blit(txt, t_rect)
            elif mb['state'] == 'firing':
                # Внешний ореол луча
                glow_s = pygame.Surface((bw + 28, bh), pygame.SRCALPHA)
                glow_s.fill((255, 40, 0, 160))
                screen.blit(glow_s, (bx - (bw + 28) // 2, by1))
                # Среднее пламя луча
                mid_s = pygame.Surface((bw, bh), pygame.SRCALPHA)
                mid_s.fill((255, 215, 0, 230))
                screen.blit(mid_s, (bx - bw // 2, by1))
                # Ядро луча
                core_s = pygame.Surface((max(4, bw - 24), bh), pygame.SRCALPHA)
                core_s.fill((255, 255, 255, 255))
                screen.blit(core_s, (bx - (bw - 24) // 2, by1))
                # Энергетические искры
                for _ in range(3):
                    spark_y = by1 + random.random() * bh
                    spark_x = bx + (random.random() - 0.5) * (bw + 10)
                    pygame.draw.circle(screen, (255, 255, 255), (int(spark_x), int(spark_y)), random.randint(3, 6))

        # 2. Омега-Лозы с шипами (Thorny Omega Vines)
        for v in self.vines:
            p1 = (int(v['x1']), int(v['y1']))
            p2 = (int(v['x2']), int(v['y2']))
            if v['state'] == 'warning':
                alpha = 220 if (int(pygame.time.get_ticks() / 75) % 2 == 0) else 90
                # Лазерная линия предупреждения
                line_surf = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
                pygame.draw.line(line_surf, (255, 30, 30, alpha), p1, p2, 4)
                screen.blit(line_surf, (0, 0))
            elif v['state'] == 'striking':
                # Мощный удар лозы
                pygame.draw.line(screen, (25, 90, 35), p1, p2, v['thickness'])
                pygame.draw.line(screen, (50, 175, 65), p1, p2, max(2, v['thickness'] - 6))
                pygame.draw.line(screen, (200, 255, 200), p1, p2, max(2, v['thickness'] - 14))
                # Шипы вдоль лозы
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                length = math.hypot(dx, dy)
                if length > 0:
                    ux = dx / length
                    uy = dy / length
                    nx, ny = -uy, ux # нормаль
                    step = 28.0
                    cur = 15.0
                    while cur < length - 15:
                        cx = p1[0] + ux * cur
                        cy = p1[1] + uy * cur
                        side = 1.0 if int(cur / step) % 2 == 0 else -1.0
                        th_tip = (int(cx + nx * side * 16.0), int(cy + ny * side * 16.0))
                        th_b1 = (int(cx - ux * 6.0), int(cy - uy * 6.0))
                        th_b2 = (int(cx + ux * 6.0), int(cy + uy * 6.0))
                        pygame.draw.polygon(screen, (255, 215, 0), [th_tip, th_b1, th_b2])
                        pygame.draw.polygon(screen, (255, 0, 50), [th_tip, th_b1, th_b2], 1)
                        cur += step

        # 3. Прицелы и Авиаудары (Target Reticles)
        for r in self.reticles:
            rx, ry = int(r['x']), int(r['y'])
            ang = r['angle']

            if r['state'] == 'tracking':
                color = (0, 255, 255)
                rad = int(26 + math.sin(r['time'] * 12.0) * 4)
            else: # locked or dropping
                flash = (int(pygame.time.get_ticks() / 60) % 2 == 0)
                color = (255, 0, 0) if flash else (255, 255, 255)
                rad = 22

            # Вращающийся прицел
            pygame.draw.circle(screen, color, (rx, ry), rad, 2)
            pygame.draw.circle(screen, color, (rx, ry), 4)
            for i in range(4):
                a = ang + i * (math.pi / 2.0)
                x1 = int(rx + math.cos(a) * (rad - 4))
                y1 = int(ry + math.sin(a) * (rad - 4))
                x2 = int(rx + math.cos(a) * (rad + 10))
                y2 = int(ry + math.sin(a) * (rad + 10))
                pygame.draw.line(screen, color, (x1, y1), (x2, y2), 2)

            if r['state'] == 'dropping':
                by = int(r['bomb_y'])
                # След падающей бомбы
                pygame.draw.line(screen, (255, 200, 0), (rx, max(by - 30, self.arena['y'])), (rx, by), 4)
                pygame.draw.circle(screen, (255, 50, 50), (rx, by), 8)

        # 4. Руки-Пушки (Finger Guns)
        for fg in self.finger_guns:
            deg = -math.degrees(fg['angle'])
            rot_hand = pygame.transform.rotate(self.finger_gun_surf, deg)
            hand_rect = rot_hand.get_rect(center=(int(fg['x']), int(fg['y'])))
            screen.blit(rot_hand, hand_rect)

            # Вспышка выстрела
            if fg['shots_left'] > 0 and fg['shot_timer'] < 0.05:
                fx = int(fg['x'] + math.cos(fg['angle']) * 34)
                fy = int(fg['y'] + math.sin(fg['angle']) * 34)
                pygame.draw.circle(screen, (255, 255, 0), (fx, fy), 9)
                pygame.draw.circle(screen, (255, 255, 255), (fx, fy), 4)

        # 5. Сжимающиеся кольца зубов (Dentata)
        for ring in self.dentata_rings:
            cx, cy = int(ring['center_x']), int(ring['center_y'])
            r = ring['radius']
            for ang in ring['teeth_angles']:
                tooth_ang = ring['current_angle'] + ang
                tx = cx + math.cos(tooth_ang) * r
                ty = cy + math.sin(tooth_ang) * r

                # Зуб направлен в центр кольца
                inward_ang = tooth_ang + math.pi
                p_tip = (int(tx + math.cos(inward_ang) * 14.0), int(ty + math.sin(inward_ang) * 14.0))
                p_b1 = (int(tx + math.cos(inward_ang + 1.8) * 7.0), int(ty + math.sin(inward_ang + 1.8) * 7.0))
                p_b2 = (int(tx + math.cos(inward_ang - 1.8) * 7.0), int(ty + math.sin(inward_ang - 1.8) * 7.0))
                pygame.draw.polygon(screen, (245, 245, 245), [p_tip, p_b1, p_b2])
                pygame.draw.polygon(screen, (255, 40, 40), [p_tip, p_b1, p_b2], 1)

        # 6. Гейзеры жижи ("Special on my plate")
        for g in self.geysers:
            gx, gy, gw, gh = int(g['x']), int(g['y']), int(g['w']), int(g['h'])
            if g['state'] == 'warning':
                puddle = pygame.Rect(gx, gy - 8, gw, 14)
                pygame.draw.ellipse(screen, (100, 55, 20), puddle)
                pygame.draw.ellipse(screen, (255, 180, 50), puddle, 2)
                bx = int(gx + (math.sin(g['time'] * 16.0) * 0.4 + 0.5) * gw)
                pygame.draw.circle(screen, (180, 110, 50), (bx, gy - 10), 4)
                if font:
                    warn_t = font.render("!", True, (255, 200, 0))
                    screen.blit(warn_t, (gx + gw // 2 - 4, gy - 26))
            elif g['state'] == 'erupting':
                pillar = pygame.Rect(gx, gy - gh, gw, gh)
                pygame.draw.rect(screen, (85, 45, 15), pillar, border_top_left_radius=8, border_top_right_radius=8)
                pygame.draw.rect(screen, (160, 95, 35), pillar, 3, border_top_left_radius=8, border_top_right_radius=8)
                for i in range(4):
                    by = int(gy - (i + 0.8) * (gh / 4.5))
                    bx = int(gx + gw / 2.0 + math.sin(g['time'] * 22.0 + i * 1.5) * (gw / 3.5))
                    pygame.draw.circle(screen, (190, 120, 50), (bx, by), 5)

        # 7. Лазеры
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
                else:
                    beam_surf = pygame.Surface((lw, int(laser['thickness'])), pygame.SRCALPHA)
                    beam_surf.fill((255, 255, 255, 240))
                    screen.blit(beam_surf, (lx, top_y))
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

        # 8. Снаряды
        for p in self.projectiles:
            ptype = p.get('type')
            px, py = int(p['x']), int(p['y'])

            if ptype == 'tom_head':
                r = p['radius']
                for idx, pt in enumerate(p['trail']):
                    a = int((idx + 1) / (len(p['trail']) + 1) * 75)
                    scaled_t = pygame.transform.scale(self.tom_head_surf, (r * 2, r * 2))
                    scaled_t.set_alpha(a)
                    screen.blit(scaled_t, scaled_t.get_rect(center=(int(pt[0]), int(pt[1]))))

                rot_surf = pygame.transform.rotate(self.tom_head_surf, p['angle'])
                glow = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 215, 0, 45), (int(r * 1.5), int(r * 1.5)), int(r * 1.3))
                screen.blit(glow, (px - int(r * 1.5), py - int(r * 1.5)))
                screen.blit(rot_surf, rot_surf.get_rect(center=(px, py)))

            elif ptype == 'plunger':
                deg = -math.degrees(p['angle'])
                rot_p = pygame.transform.rotate(self.plunger_surf, deg)
                screen.blit(rot_p, rot_p.get_rect(center=(px, py)))

            elif ptype == 'tp_roll':
                if len(p['trail']) > 1:
                    pts = [(int(pt[0]), int(pt[1])) for pt in p['trail']]
                    pygame.draw.lines(screen, (245, 245, 245), False, pts, 4)
                rot_tp = pygame.transform.rotate(self.tp_roll_surf, p['angle'])
                screen.blit(rot_tp, rot_tp.get_rect(center=(px, py)))

            elif ptype == 'plate':
                r = p['radius']
                pygame.draw.circle(screen, (240, 235, 220), (px, py), r)
                pygame.draw.circle(screen, (200, 190, 175), (px, py), int(r * 0.75))
                pygame.draw.circle(screen, (90, 50, 20), (px, py), int(r * 0.45))
                pygame.draw.circle(screen, (255, 255, 255), (px, py), r, 2)

            elif ptype == 'shrapnel':
                r = p['radius']
                pygame.draw.circle(screen, (110, 65, 25), (px, py), r)
                pygame.draw.circle(screen, (255, 200, 100), (px, py), r, 1)

            elif ptype == 'pearl':
                r = p['radius']
                pygame.draw.circle(screen, (255, 255, 0), (px, py), r)
                pygame.draw.circle(screen, (255, 255, 255), (px, py), max(1, int(r * 0.55)))

            elif ptype == 'sludge_bullet':
                r = int(p['radius'] * p.get('scale', 1.0))
                pygame.draw.circle(screen, (115, 60, 20), (px, py), r)
                pygame.draw.circle(screen, (255, 170, 30), (px, py), max(1, int(r * 0.6)))
                pygame.draw.circle(screen, (255, 255, 255), (px, py), max(1, int(r * 0.3)))

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

        # 9. Баннер [ FILE 1 LOADED ] (SAVE/LOAD)
        if self.glitch_banner and font:
            text_str = self.glitch_banner['text']
            bx = self.arena['x'] + self.arena['width'] // 2
            by = self.arena['y'] - 24
            # Эффект хроматической аберрации текста
            cyan_txt = font.render(text_str, True, (0, 255, 255))
            red_txt = font.render(text_str, True, (255, 0, 0))
            white_txt = font.render(text_str, True, (255, 255, 255))

            offset = int(math.sin(self.glitch_banner['timer'] * 35.0) * 4)
            c_rect = cyan_txt.get_rect(center=(bx + offset - 2, by))
            r_rect = red_txt.get_rect(center=(bx - offset + 2, by))
            w_rect = white_txt.get_rect(center=(bx, by))

            screen.blit(cyan_txt, c_rect)
            screen.blit(red_txt, r_rect)
            screen.blit(white_txt, w_rect)
