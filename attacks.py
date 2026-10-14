# attacks.js -> attacks.py - 10 атак Тома Перла и баланс
import math
import random
import pygame

class AttackManager:
    def __init__(self, arena):
        self.arena = arena
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
        self.current_pattern = 0
        self.pattern_cooldown = 0.3 * self.cooldown_multiplier
        self.pattern_time = 0.0
        self.spiral_angle = 0.0
        self.shake_amount = 0.0

    def on_phase_change(self, phase):
        # Очистить хёртбоксы при смене фазы, чтобы дать игроку передышку
        self.projectiles = [p for p in self.projectiles if p.get('type') != 'hurtbox']

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

        # Периодический спавн хилки при низком HP
        if self.heal_interval > 0 and player.hp < player.max_hp * 0.6:
            self.heal_timer += dt
            if self.heal_timer >= self.heal_interval:
                self.heal_timer = 0.0
                if len(self.heal_pickups) < 2:
                    self.spawn_heal_pickup(self.heal_amount)

        # 4 фазы боя (пропорционально максимальному HP)
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

        # Фоновые хёртбоксы в поздних фазах
        max_bg = 2 if is_p4 else 1 if (is_p3 or is_p2) else 0
        current_hurtboxes = len([p for p in self.projectiles if p.get('type') == 'hurtbox'])
        if current_hurtboxes < max_bg:
            spd = (5.5 if is_p4 else 4.8 if is_p3 else 4.0) * self.speed_multiplier
            self.spawn_bouncing_hurtbox(spd)

        # Запуск паттерна
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

            # Тарелка ударилась о пол арены -> разрыв на осколки
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
        if ptype == 'hurtbox':
            p['trail'].append((p['x'], p['y']))
            if len(p['trail']) > 4:
                p['trail'].pop(0)

            p['x'] += p['vx'] * 60.0 * dt
            p['y'] += p['vy'] * 60.0 * dt

            # Отскоки от стенок арены
            if p['x'] < self.arena['x'] + 4:
                p['x'] = self.arena['x'] + 4
                p['vx'] = abs(p['vx'])
            elif p['x'] + p['width'] > self.arena['x'] + self.arena['width'] - 4:
                p['x'] = self.arena['x'] + self.arena['width'] - 4 - p['width']
                p['vx'] = -abs(p['vx'])

            if p['y'] < self.arena['y'] + 4:
                p['y'] = self.arena['y'] + 4
                p['vy'] = abs(p['vy'])
            elif p['y'] + p['height'] > self.arena['y'] + self.arena['height'] - 4:
                p['y'] = self.arena['y'] + self.arena['height'] - 4 - p['height']
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
            # Вылет за пределы арены с запасом
            if (p['x'] < self.arena['x'] - 50 or p['x'] > self.arena['x'] + self.arena['width'] + 50 or
                p['y'] < self.arena['y'] - 50 or p['y'] > self.arena['y'] + self.arena['height'] + 50):
                p['is_dead'] = True

        elif ptype == 'missile':
            p['life'] -= dt
            if p['life'] <= 0:
                p['is_dead'] = True
            else:
                # Плавный доворот на Жёлтую Душу
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

        # Undertale-каноничный компактный хитбокс сердца (5.5px)
        core = player.hitbox_radius

        ptype = p.get('type')
        if ptype in ('hurtbox', 'aura_slash'):
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
            # 0. Скоростные хёртбоксы
            count = len([p for p in self.projectiles if p.get('type') == 'hurtbox'])
            limit = 3 if is_p4 else 2 if is_p3 else 1
            if count < limit:
                spd = (5.8 if is_p4 else 4.8 if is_p3 else 4.0) * spd_mult
                self.spawn_bouncing_hurtbox(spd)

        elif self.current_pattern == 1:
            # 1. Падающие тарелки
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
            # 3. Лазерная сетка
            if self.pattern_cooldown <= 0:
                self.spawn_laser_grid(is_p3 or is_p4)
                self.pattern_cooldown = (1.1 if is_p4 else 1.4 if is_p3 else 1.9) * cd_mult

        elif self.current_pattern == 4:
            # 4. Самонаводящиеся снаряды
            if self.pattern_cooldown <= 0:
                self.spawn_homing_missile(player, is_p3 or is_p4)
                self.pattern_cooldown = (0.65 if is_p4 else 0.85 if is_p3 else 1.25) * cd_mult

        elif self.current_pattern == 5:
            # 5. Мега-удар тарелкой
            if self.pattern_cooldown <= 0:
                self.spawn_mega_plate_slam()
                self.pattern_cooldown = (1.8 if is_p4 else 2.2 if is_p3 else 2.8) * cd_mult

        elif self.current_pattern == 6:
            # 6. Таймер-бомба Тома Перла
            if self.pattern_cooldown <= 0 and len([p for p in self.projectiles if p.get('type') == 'bomb']) == 0:
                self.spawn_diaper_bomb()
                self.pattern_cooldown = (2.5 if is_p4 else 3.2) * cd_mult

        elif self.current_pattern == 7:
            # 7. Серповидные волны ауры
            if self.pattern_cooldown <= 0:
                self.spawn_aura_slash()
                self.pattern_cooldown = (0.55 if is_p4 else 0.75 if is_p3 else 1.0) * cd_mult

        elif self.current_pattern == 8:
            # 8. Лавина тарелок
            if self.pattern_cooldown <= 0:
                self.spawn_plate_avalanche(is_p4)
                self.pattern_cooldown = (0.25 if is_p4 else 0.35) * cd_mult

        elif self.current_pattern == 9:
            # 9. Квадро-бластерный крест
            if self.pattern_cooldown <= 0:
                self.spawn_quad_blaster()
                self.pattern_cooldown = (1.5 if is_p4 else 2.2) * cd_mult

    # 1. Хёртбокс
    def spawn_bouncing_hurtbox(self, speed=4.0):
        size = 42
        self.projectiles.append({
            'type': 'hurtbox',
            'x': self.arena['x'] + 20 + random.random() * (self.arena['width'] - 60),
            'y': self.arena['y'] + 20,
            'width': size,
            'height': size,
            'vx': (1 if random.random() > 0.5 else -1) * speed,
            'vy': (0.7 + random.random() * 0.6) * speed,
            'trail': [],
            'life': 7.5,
            'damage': 5,
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

    # Осколки тарелки
    def spawn_plate_shrapnel(self, x, y):
        for ang in (-2.4, -1.57, -0.74):
            spd = (3.8 + random.random() * 1.5) * self.speed_multiplier
            self.projectiles.append({
                'type': 'shrapnel',
                'x': x,
                'y': y - 5,
                'radius': 7,
                'vx': math.cos(ang) * spd,
                'vy': math.sin(ang) * spd - 2.0,
                'life': 2.4,
                'damage': 4,
                'destroy_on_hit': True,
                'is_dead': False
            })

    # 3. Спираль жемчужин
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

    # 4. Лазерная сетка
    def spawn_laser_grid(self, is_p3=False):
        h_y = self.arena['y'] + 30 + random.random() * (self.arena['height'] - 60)
        self.lasers.append({
            'axis': 'horizontal',
            'pos': h_y,
            'thickness': 28,
            'time': 0.0,
            'warning_duration': (0.45 if is_p3 else 0.65) / self.speed_multiplier,
            'active_duration': 0.30,
            'damage': 5
        })
        if is_p3 and random.random() < 0.65:
            v_x = self.arena['x'] + 30 + random.random() * (self.arena['width'] - 60)
            self.lasers.append({
                'axis': 'vertical',
                'pos': v_x,
                'thickness': 28,
                'time': 0.0,
                'warning_duration': 0.55 / self.speed_multiplier,
                'active_duration': 0.30,
                'damage': 5
            })

    # 5. Самонаводящаяся ракета
    def spawn_homing_missile(self, player, is_p3=False):
        ox = self.arena['x'] + 30 + random.random() * (self.arena['width'] - 60)
        oy = self.arena['y'] - 10
        init_ang = math.atan2(player.y - oy, player.x - ox)
        self.projectiles.append({
            'type': 'missile',
            'x': ox,
            'y': oy,
            'radius': 11,
            'angle': init_ang,
            'speed': (4.2 if is_p3 else 3.2) * self.speed_multiplier,
            'turn_rate': 0.045 if is_p3 else 0.035,
            'life': 3.2,
            'damage': 6,
            'destroy_on_hit': True,
            'is_dead': False
        })

    # 6. Мега-удар
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

    # 7. Бомба Тома Перла
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

    # 8. Серповидные волны ауры
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

    # 9. Лавина тарелок
    def spawn_plate_avalanche(self, is_p4=False):
        count = 3 if is_p4 else 2
        for _ in range(count):
            rx = self.arena['x'] + 20 + random.random() * (self.arena['width'] - 40)
            self.projectiles.append({
                'type': 'plate',
                'x': rx,
                'y': self.arena['y'] - 15 - random.random() * 30,
                'radius': 14,
                'vy': (4.5 + random.random() * 2.5) * self.speed_multiplier,
                'rotation': 0.0,
                'damage': 5,
                'destroy_on_hit': True,
                'burst_on_destroy': False,
                'is_dead': False
            })

    # 10. Квадро-бластер
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

        # 1. Телеграфы Мега-удара
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
                # Зона падения тарелки
                slam_surf = pygame.Surface((int(t['w']), int(t['h'])), pygame.SRCALPHA)
                slam_surf.fill((255, 255, 255, 220))
                screen.blit(slam_surf, rect)
                inner = rect.inflate(-16, -16)
                inner_surf = pygame.Surface((inner.width, inner.height), pygame.SRCALPHA)
                inner_surf.fill((180, 50, 20, 180))
                screen.blit(inner_surf, inner)

        # 2. Лазеры
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

        # 3. Снаряды
        for p in self.projectiles:
            ptype = p.get('type')
            px, py = int(p['x']), int(p['y'])

            if ptype == 'hurtbox':
                # Трейл
                for idx, pt in enumerate(p['trail']):
                    a = int((idx + 1) / (len(p['trail']) + 1) * 65)
                    t_surf = pygame.Surface((p['width'], p['height']), pygame.SRCALPHA)
                    t_surf.fill((255, 30, 30, a))
                    screen.blit(t_surf, (int(pt[0]), int(pt[1])))

                box_surf = pygame.Surface((p['width'], p['height']), pygame.SRCALPHA)
                box_surf.fill((235, 35, 35, 170))
                screen.blit(box_surf, (px, py))
                pygame.draw.rect(screen, (255, 255, 255), (px, py, p['width'], p['height']), 2)

            elif ptype == 'plate':
                r = p['radius']
                pygame.draw.circle(screen, (240, 235, 220), (px, py), r)
                pygame.draw.circle(screen, (200, 190, 175), (px, py), int(r * 0.75))
                pygame.draw.circle(screen, (70, 45, 25), (px, py), int(r * 0.45))
                pygame.draw.circle(screen, (255, 255, 255), (px, py), r, 2)

            elif ptype == 'shrapnel':
                r = p['radius']
                pygame.draw.circle(screen, (230, 225, 215), (px, py), r)
                pygame.draw.circle(screen, (60, 40, 20), (px, py), max(1, int(r * 0.5)))
                pygame.draw.circle(screen, (255, 255, 255), (px, py), r, 1)

            elif ptype == 'pearl':
                r = p['radius']
                pygame.draw.circle(screen, (255, 255, 0), (px, py), r)
                pygame.draw.circle(screen, (255, 255, 255), (px, py), max(1, int(r * 0.55)))

            elif ptype == 'missile':
                r = p['radius']
                pygame.draw.circle(screen, (255, 40, 40), (px, py), r)
                pygame.draw.circle(screen, (255, 255, 0), (px, py), max(1, int(r * 0.55)))
                # Хвостик ракеты
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
                # Серп
                pygame.draw.ellipse(slash_surf, (255, 0, 85, 220), (0, 0, pw, ph))
                pygame.draw.ellipse(slash_surf, (255, 255, 255, 255), (2, 2, pw - 4, ph - 4))
                screen.blit(slash_surf, (px, py))
