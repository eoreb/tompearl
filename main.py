# main.py - Главный координатор игры «Fight Tom Pearl» (Pygame-CE Edition)
import sys
import os
import pygame
from audio import audio_manager
from player import Player
from boss import Boss
from attacks import AttackManager

from utils import get_asset_path

class GameState:
    START = 'START'
    INTRO = 'INTRO'
    BATTLE = 'BATTLE'
    PAUSE = 'PAUSE'
    GAMEOVER = 'GAMEOVER'
    VICTORY = 'VICTORY'

DIFFICULTIES = {
    'EASY': {
        'key': 'EASY',
        'name': 'ЛЕГКО',
        'sub': 'ЧИЛЛ',
        'playerHp': 120,
        'playerSpeed': 6.0,
        'invulnerableDuration': 0.90,
        'bulletDamage': 7,
        'bossMaxHp': 800,
        'speedMultiplier': 0.80,
        'cooldownMultiplier': 1.25,
        'healInterval': 25,
        'healAmount': 25,
        'desc': 'Больше HP (120), мягкая неуязвимость, замедленные атаки и частые хилки.'
    },
    'NORMAL': {
        'key': 'NORMAL',
        'name': 'КАНОН',
        'sub': '92 HP',
        'playerHp': 92,
        'playerSpeed': 5.8,
        'invulnerableDuration': 0.65,
        'bulletDamage': 5,
        'bossMaxHp': 1000,
        'speedMultiplier': 1.00,
        'cooldownMultiplier': 1.00,
        'healInterval': 40,
        'healAmount': 20,
        'desc': 'Каноничный баланс Undertale: 92 HP, урон 5.0, честные тайминги.'
    },
    'HARD': {
        'key': 'HARD',
        'name': 'ХАРДКОР',
        'sub': 'АУРА 5.0',
        'playerHp': 50,
        'playerSpeed': 5.5,
        'invulnerableDuration': 0.40,
        'bulletDamage': 4,
        'bossMaxHp': 1200,
        'speedMultiplier': 1.22,
        'cooldownMultiplier': 0.85,
        'healInterval': 0,
        'healAmount': 0,
        'desc': '50 HP, бешеные атаки, минимум неуязвимости. Настоящий ад!'
    }
}

class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()

        self.width = 800
        self.height = 640
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Fight Tom Pearl (Undertale Edition)")

        # Иконка окна
        icon_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(icon_surf, (255, 255, 0), (16, 16), 14)
        pygame.display.set_icon(icon_surf)

        self.clock = pygame.time.Clock()

        # Шрифты
        font_path = get_asset_path('PressStart2P.ttf')
        if not os.path.exists(font_path):
            font_path = None

        self.f_title = pygame.font.Font(font_path, 22) if font_path else pygame.font.SysFont('monospace', 26, bold=True)
        self.f_sub = pygame.font.Font(font_path, 13) if font_path else pygame.font.SysFont('monospace', 15)
        self.f_main = pygame.font.Font(font_path, 11) if font_path else pygame.font.SysFont('monospace', 12)
        self.f_small = pygame.font.Font(font_path, 9) if font_path else pygame.font.SysFont('monospace', 10)
        self.f_tiny = pygame.font.Font(font_path, 8) if font_path else pygame.font.SysFont('monospace', 9)

        # Параметры сложности
        self.difficulty_key = 'NORMAL'
        self.difficulty = DIFFICULTIES['NORMAL']

        # Параметры арены (Battle Box)
        self.arena = {
            'x': 180,
            'y': 300,
            'width': 440,
            'height': 250
        }

        self.state = GameState.START
        self.previous_state = GameState.START

        self.player = Player(self.arena)
        self.boss = Boss(self.width)
        self.attack_manager = AttackManager(self.arena)

        # Диалог интро
        self.intro_dialogue = [
            "Hi, my name is Tom Pearl...",
            "And today, I have something very special on my plate.",
            "Are you ready for the aura?"
        ]
        self.current_line_index = 0
        self.displayed_text = ""
        self.char_timer = 0.0
        self.line_pause_timer = 0.0
        self.intro_total_timer = 0.0

        # Статистика
        self.battle_timer = 0.0
        self.total_bullets_fired = 0

    def set_difficulty(self, key):
        if key in DIFFICULTIES:
            self.difficulty_key = key
            self.difficulty = DIFFICULTIES[key]

    def start_intro(self):
        self.state = GameState.INTRO
        self.current_line_index = 0
        self.displayed_text = ""
        self.char_timer = 0.0
        self.line_pause_timer = 0.0
        self.intro_total_timer = 0.0
        audio_manager.play_intro()

    def advance_intro(self):
        full_line = self.intro_dialogue[self.current_line_index]
        if len(self.displayed_text) < len(full_line):
            self.displayed_text = full_line
            self.line_pause_timer = 0.0
            return

        self.current_line_index += 1
        if self.current_line_index < len(self.intro_dialogue):
            self.displayed_text = ""
            self.char_timer = 0.0
            self.line_pause_timer = 0.0
        else:
            self.start_battle_directly()

    def start_battle_directly(self, is_restart=False):
        self.state = GameState.BATTLE
        self.player.reset(self.difficulty)
        self.boss.reset(self.difficulty)
        self.attack_manager.reset(self.difficulty)
        self.battle_timer = 0.0
        self.total_bullets_fired = 0
        audio_manager.play_battle(is_restart)

    def toggle_pause(self):
        if self.state == GameState.PAUSE:
            self.state = self.previous_state
        elif self.state in (GameState.BATTLE, GameState.INTRO):
            self.previous_state = self.state
            self.state = GameState.PAUSE

    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(60) / 1000.0, 0.1)

            # Обработка событий
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state in (GameState.BATTLE, GameState.PAUSE):
                            self.toggle_pause()
                        else:
                            running = False

                    elif event.key == pygame.K_p:
                        self.toggle_pause()

                    elif event.key == pygame.K_m:
                        audio_manager.toggle_mute()

                    elif event.key == pygame.K_r:
                        if self.state in (GameState.GAMEOVER, GameState.VICTORY):
                            self.start_battle_directly(is_restart=True)

                    # Стартовый экран
                    if self.state == GameState.START:
                        if event.key in (pygame.K_1, pygame.K_KP1):
                            self.set_difficulty('EASY')
                        elif event.key in (pygame.K_2, pygame.K_KP2):
                            self.set_difficulty('NORMAL')
                        elif event.key in (pygame.K_3, pygame.K_KP3):
                            self.set_difficulty('HARD')
                        elif event.key in (pygame.K_LEFT, pygame.K_a):
                            order = ['EASY', 'NORMAL', 'HARD']
                            idx = order.index(self.difficulty_key)
                            self.set_difficulty(order[(idx + 2) % 3])
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            order = ['EASY', 'NORMAL', 'HARD']
                            idx = order.index(self.difficulty_key)
                            self.set_difficulty(order[(idx + 1) % 3])
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                            self.start_intro()

                    # Интро
                    elif self.state == GameState.INTRO:
                        if event.key in (pygame.K_z, pygame.K_SPACE, pygame.K_RETURN):
                            self.advance_intro()

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.state == GameState.START:
                        # Кнопки выбора сложности
                        btn_y = 350
                        diff_btns = [
                            ('EASY', 230),
                            ('NORMAL', 350),
                            ('HARD', 470)
                        ]
                        for key, bx in diff_btns:
                            rect = pygame.Rect(bx, btn_y, 100, 48)
                            if rect.collidepoint(mouse_pos):
                                self.set_difficulty(key)

                        # Кнопка «НАЧАТЬ БИТВУ»
                        start_rect = pygame.Rect(280, 455, 240, 48)
                        if start_rect.collidepoint(mouse_pos):
                            self.start_intro()

                    elif self.state == GameState.INTRO:
                        self.advance_intro()

                    elif self.state == GameState.PAUSE:
                        resume_rect = pygame.Rect(300, 360, 200, 44)
                        if resume_rect.collidepoint(mouse_pos):
                            self.toggle_pause()

            # Обновление состояния
            self.update(dt)

            # Отрисовка
            self.render()
            pygame.display.flip()

        pygame.quit()
        sys.exit(0)

    def update(self, dt):
        if self.state in (GameState.PAUSE, GameState.START):
            return

        if self.state == GameState.INTRO:
            self.boss.update(dt)
            self.intro_total_timer += dt

            # Авто-переход в бой по окончании трека интро (14.5 сек)
            if self.intro_total_timer > 14.5:
                self.start_battle_directly()
                return

            current_line = self.intro_dialogue[self.current_line_index]
            if len(self.displayed_text) < len(current_line):
                self.char_timer += dt
                if self.char_timer >= 0.045:
                    self.char_timer = 0.0
                    self.displayed_text += current_line[len(self.displayed_text)]
                    if random.random() < 0.6:
                        audio_manager.play_text_blip()
            else:
                self.line_pause_timer += dt
                if self.line_pause_timer >= 1.2:
                    self.line_pause_timer = 0.0
                    self.current_line_index += 1
                    if self.current_line_index < len(self.intro_dialogue):
                        self.displayed_text = ""
                    else:
                        self.start_battle_directly()
            return

        if self.state == GameState.BATTLE:
            keys = pygame.key.get_pressed()
            self.battle_timer += dt
            self.player.update(dt, keys, self.boss, self.attack_manager)
            self.boss.update(dt, self.attack_manager)
            self.attack_manager.update(dt, self.player, self.boss)

            if self.player.is_dead:
                self.state = GameState.GAMEOVER
            elif self.boss.is_defeated:
                self.state = GameState.VICTORY
            return

        if self.state == GameState.GAMEOVER:
            self.player.update(dt, {}, None, None)
            return

        if self.state == GameState.VICTORY:
            self.boss.update(dt)
            return

    def render(self):
        self.screen.fill((0, 0, 0))

        if self.state == GameState.START:
            self.render_start_screen()
        elif self.state == GameState.INTRO:
            self.render_intro_screen()
        elif self.state in (GameState.BATTLE, GameState.PAUSE):
            self.render_battle_screen()
            if self.state == GameState.PAUSE:
                self.render_pause_overlay()
        elif self.state == GameState.GAMEOVER:
            self.render_gameover_screen()
        elif self.state == GameState.VICTORY:
            self.render_victory_screen()

    def render_start_screen(self):
        # Рамка окна
        pygame.draw.rect(self.screen, (255, 255, 255), (10, 10, self.width - 20, self.height - 20), 4)

        # Босс на фоне
        self.boss.draw(self.screen, self.f_small)

        # Затемняющая плашка
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        # Заголовок
        t_surf = self.f_title.render("FIGHT TOM PEARL", True, (255, 255, 0))
        t_shadow = self.f_title.render("FIGHT TOM PEARL", True, (255, 0, 85))
        rect = t_surf.get_rect(center=(self.width // 2, 75))
        self.screen.blit(t_shadow, (rect.x + 2, rect.y + 2))
        self.screen.blit(t_surf, rect)

        sub_surf = self.f_sub.render("UNDERTALE EDITION", True, (255, 153, 0))
        s_rect = sub_surf.get_rect(center=(self.width // 2, 110))
        self.screen.blit(sub_surf, s_rect)

        # Блок управления
        ctrl_y = 150
        ctrls = [
            ("[СТРЕЛКИ / WASD]", "Движение Жёлтой Души"),
            ("[ Z / ПРОБЕЛ ]", "Стрельба вверх / Пропуск диалога"),
            ("[ P ]", "Пауза   |   [ M ] Звук Вкл/Выкл")
        ]
        box_rect = pygame.Rect(140, ctrl_y, 520, 100)
        pygame.draw.rect(self.screen, (15, 15, 15), box_rect)
        pygame.draw.rect(self.screen, (80, 80, 80), box_rect, 2)

        for i, (k, desc) in enumerate(ctrls):
            k_s = self.f_small.render(k, True, (255, 255, 0))
            d_s = self.f_small.render(desc, True, (200, 200, 200))
            self.screen.blit(k_s, (160, ctrl_y + 16 + i * 26))
            self.screen.blit(d_s, (360, ctrl_y + 16 + i * 26))

        # Выбор сложности
        sec_title = self.f_small.render("ВЫБЕРИ СЛОЖНОСТЬ (КЛАВИШИ 1, 2, 3 ИЛИ СТРЕЛКИ):", True, (255, 153, 0))
        self.screen.blit(sec_title, sec_title.get_rect(center=(self.width // 2, 320)))

        diff_btns = [
            ('EASY', 230, 'ЛЕГКО', 'ЧИЛЛ', (0, 255, 102)),
            ('NORMAL', 350, 'КАНОН', '92 HP', (255, 255, 0)),
            ('HARD', 470, 'ХАРДКОР', 'АУРА 5.0', (255, 0, 85))
        ]
        btn_y = 345
        for key, bx, title, sub, col in diff_btns:
            rect = pygame.Rect(bx, btn_y, 100, 48)
            is_active = (self.difficulty_key == key)
            bg_col = (40, 40, 40) if is_active else (18, 18, 18)
            border_col = (255, 255, 0) if is_active else (70, 70, 70)

            pygame.draw.rect(self.screen, bg_col, rect)
            pygame.draw.rect(self.screen, border_col, rect, 3 if is_active else 1)

            t_t = self.f_small.render(title, True, col)
            t_s = self.f_tiny.render(sub, True, (220, 220, 220) if is_active else (140, 140, 140))
            self.screen.blit(t_t, t_t.get_rect(center=(bx + 50, btn_y + 18)))
            self.screen.blit(t_s, t_s.get_rect(center=(bx + 50, btn_y + 34)))

        # Описание выбранной сложности
        desc_surf = self.f_small.render(self.difficulty['desc'], True, (180, 180, 180))
        self.screen.blit(desc_surf, desc_surf.get_rect(center=(self.width // 2, 415)))

        # Кнопка «НАЧАТЬ БИТВУ»
        start_rect = pygame.Rect(280, 455, 240, 48)
        mouse_pos = pygame.mouse.get_pos()
        is_hover = start_rect.collidepoint(mouse_pos)
        pygame.draw.rect(self.screen, (255, 153, 0) if is_hover else (0, 0, 0), start_rect)
        pygame.draw.rect(self.screen, (255, 153, 0), start_rect, 3)

        btn_txt = self.f_sub.render("НАЧАТЬ БИТВУ", True, (0, 0, 0) if is_hover else (255, 255, 255))
        self.screen.blit(btn_txt, btn_txt.get_rect(center=start_rect.center))

    def render_intro_screen(self):
        # Босс
        self.boss.draw(self.screen, self.f_small)

        # Диалоговое окно Undertale
        box_x, box_y, box_w, box_h = 100, 350, 600, 190
        rect = pygame.Rect(box_x, box_y, box_w, box_h)
        pygame.draw.rect(self.screen, (0, 0, 0), rect)
        pygame.draw.rect(self.screen, (255, 255, 255), rect, 4)

        # Красная звездочка Undertale
        star = self.f_sub.render("*", True, (255, 0, 0))
        self.screen.blit(star, (box_x + 25, box_y + 35))

        # Текст реплики
        words = self.displayed_text.split(' ')
        lines = []
        cur_line = ""
        for w in words:
            test_line = (cur_line + " " + w).strip()
            if self.f_sub.size(test_line)[0] < box_w - 90:
                cur_line = test_line
            else:
                lines.append(cur_line)
                cur_line = w
        if cur_line:
            lines.append(cur_line)

        for idx, line in enumerate(lines):
            l_surf = self.f_sub.render(line, True, (255, 255, 255))
            self.screen.blit(l_surf, (box_x + 55, box_y + 35 + idx * 28))

        # Подсказка
        hint = self.f_small.render("[ Z / ПРОБЕЛ / КЛИК — ПРОПУСТИТЬ ]", True, (120, 120, 120))
        self.screen.blit(hint, hint.get_rect(center=(self.width // 2, box_y + box_h - 22)))

    def render_battle_screen(self):
        # Эффект тряски экрана
        shake_x = 0
        shake_y = 0
        if self.attack_manager.shake_amount > 0:
            s = self.attack_manager.shake_amount
            import random
            shake_x = int((random.random() - 0.5) * s)
            shake_y = int((random.random() - 0.5) * s)

        # 1. Босс Том Перл
        self.boss.draw(self.screen, self.f_small)

        # 2. Полоса здоровья Босса
        self.render_boss_health_bar()

        # 3. Рамка Battle Box
        arena_rect = pygame.Rect(
            self.arena['x'] + shake_x,
            self.arena['y'] + shake_y,
            self.arena['width'],
            self.arena['height']
        )
        pygame.draw.rect(self.screen, (0, 0, 0), arena_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), arena_rect, 4)

        # 4. Атаки босса
        self.attack_manager.draw(self.screen, self.f_small)

        # 5. Игрок
        self.player.draw(self.screen, self.f_small)

        # 6. HUD игрока
        self.render_player_hud()

    def render_boss_health_bar(self):
        bar_w = 300
        bar_h = 16
        bar_x = self.width // 2 - bar_w // 2
        bar_y = 242

        # Фон полосы
        pygame.draw.rect(self.screen, (50, 0, 0), (bar_x, bar_y, bar_w, bar_h))

        # Цвет полосы
        phase = self.boss.current_phase
        if phase == 1:
            bar_col = (0, 255, 0)
            p_name = "PHASE 1: THE TASTE"
        elif phase == 2:
            bar_col = (170, 255, 0)
            p_name = "PHASE 2: SUBSTANCE RUSH"
        elif phase == 3:
            bar_col = (255, 170, 0)
            p_name = "PHASE 3: PHONK AURA"
        else:
            bar_col = (255, 0, 85) if (int(pygame.time.get_ticks() / 120) % 2 == 0) else (255, 51, 0)
            p_name = "FINAL PHASE: LAST PLATE"

        hp_pct = max(0.0, self.boss.hp / float(self.boss.max_hp))
        pygame.draw.rect(self.screen, bar_col, (bar_x, bar_y, int(bar_w * hp_pct), bar_h))
        pygame.draw.rect(self.screen, (255, 255, 255), (bar_x, bar_y, bar_w, bar_h), 2)

        # Название фазы
        p_surf = self.f_small.render(f"[ {p_name} ]", True, (255, 0, 85) if phase == 4 else (255, 204, 0))
        self.screen.blit(p_surf, p_surf.get_rect(center=(self.width // 2, bar_y - 10)))

        # Числа HP
        num_surf = self.f_small.render(f"PEARL HP: {self.boss.hp} / {self.boss.max_hp}", True, (255, 255, 255))
        self.screen.blit(num_surf, num_surf.get_rect(center=(self.width // 2, bar_y + bar_h + 12)))

    def render_player_hud(self):
        hud_y = 585
        # Имя и Уровень
        lvl_s = self.f_sub.render("YOU   LV 19", True, (255, 255, 255))
        self.screen.blit(lvl_s, (self.arena['x'], hud_y))

        # Бейдж сложности
        d_col = (0, 255, 102) if self.difficulty_key == 'EASY' else (255, 0, 85) if self.difficulty_key == 'HARD' else (255, 204, 0)
        d_s = self.f_small.render(f"[{self.difficulty['name']}]", True, d_col)
        self.screen.blit(d_s, (self.arena['x'] + 130, hud_y + 2))

        # Метка HP
        hp_lbl = self.f_sub.render("HP", True, (255, 255, 255))
        self.screen.blit(hp_lbl, (self.arena['x'] + 225, hud_y))

        # Полоска здоровья
        bar_x = self.arena['x'] + 255
        bar_w = 105
        bar_h = 14
        pygame.draw.rect(self.screen, (190, 0, 0), (bar_x, hud_y - 2, bar_w, bar_h))

        p_pct = max(0.0, self.player.hp / float(self.player.max_hp))
        pygame.draw.rect(self.screen, (255, 255, 0), (bar_x, hud_y - 2, int(bar_w * p_pct), bar_h))

        # Цифры здоровья
        digits = self.f_sub.render(f"{self.player.hp} / {self.player.max_hp}", True, (255, 255, 255))
        self.screen.blit(digits, (bar_x + bar_w + 14, hud_y))

        # Подсказка
        hint = self.f_small.render("[СТРЕЛКИ/WASD] Движение   [Z / Пробел] Стрельба   [M] Звук   [P] Пауза", True, (120, 120, 120))
        self.screen.blit(hint, hint.get_rect(center=(self.width // 2, 625)))

    def render_pause_overlay(self):
        ov = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 180))
        self.screen.blit(ov, (0, 0))

        box = pygame.Rect(250, 220, 300, 200)
        pygame.draw.rect(self.screen, (0, 0, 0), box)
        pygame.draw.rect(self.screen, (255, 255, 255), box, 4)

        t = self.f_title.render("ПАУЗА", True, (255, 255, 0))
        self.screen.blit(t, t.get_rect(center=(self.width // 2, 270)))

        msg = self.f_small.render("Нажмите [ P ] чтобы продолжить", True, (200, 200, 200))
        self.screen.blit(msg, msg.get_rect(center=(self.width // 2, 320)))

        btn_rect = pygame.Rect(300, 360, 200, 44)
        pygame.draw.rect(self.screen, (255, 153, 0), btn_rect, 2)
        b_txt = self.f_small.render("ПРОДОЛЖИТЬ", True, (255, 153, 0))
        self.screen.blit(b_txt, b_txt.get_rect(center=btn_rect.center))

    def render_gameover_screen(self):
        self.player.draw(self.screen, self.f_small)

        t = self.f_title.render("GAME OVER", True, (255, 255, 255))
        self.screen.blit(t, t.get_rect(center=(self.width // 2, 215)))

        d_col = (0, 255, 102) if self.difficulty_key == 'EASY' else (255, 0, 85) if self.difficulty_key == 'HARD' else (255, 204, 0)
        d_badge = self.f_small.render(f"[ СЛОЖНОСТЬ: {self.difficulty['name']} - {self.difficulty['sub']} ]", True, d_col)
        self.screen.blit(d_badge, d_badge.get_rect(center=(self.width // 2, 255)))

        if self.difficulty_key == 'HARD':
            l1 = self.f_sub.render("Аура 5.0 оказалась беспощадной...", True, (200, 200, 200))
            l2 = self.f_sub.render("Том Перл не оставил шанса.", True, (200, 200, 200))
        else:
            l1 = self.f_sub.render("Не теряй свой жемчуг...", True, (200, 200, 200))
            l2 = self.f_sub.render("Тарелка Тома Перла оказалась сильнее.", True, (200, 200, 200))

        self.screen.blit(l1, l1.get_rect(center=(self.width // 2, 305)))
        self.screen.blit(l2, l2.get_rect(center=(self.width // 2, 340)))

        r_txt = self.f_sub.render("[ Нажмите R для перезапуска ]", True, (255, 255, 0))
        self.screen.blit(r_txt, r_txt.get_rect(center=(self.width // 2, 450)))

    def render_victory_screen(self):
        self.boss.draw(self.screen, self.f_small)

        t = self.f_title.render("ПОБЕДА!", True, (255, 255, 0))
        self.screen.blit(t, t.get_rect(center=(self.width // 2, 260)))

        d_col = (0, 255, 102) if self.difficulty_key == 'EASY' else (255, 0, 85) if self.difficulty_key == 'HARD' else (255, 204, 0)
        diff_info = self.f_small.render(f"СЛОЖНОСТЬ: {self.difficulty['name']} ({self.difficulty['sub']})", True, d_col)
        self.screen.blit(diff_info, diff_info.get_rect(center=(self.width // 2, 298)))

        sub1 = self.f_sub.render("Том Перл повержен!", True, (255, 255, 255))
        sub2 = self.f_sub.render(f"Время битвы: {self.battle_timer:.1f} сек", True, (255, 255, 255))
        sub3 = self.f_sub.render(f"Оставшееся HP: {self.player.hp} / {self.player.max_hp}", True, (255, 255, 255))

        self.screen.blit(sub1, sub1.get_rect(center=(self.width // 2, 335)))
        self.screen.blit(sub2, sub2.get_rect(center=(self.width // 2, 370)))
        self.screen.blit(sub3, sub3.get_rect(center=(self.width // 2, 405)))

        again = self.f_sub.render("[ Нажмите R чтобы сыграть снова ]", True, (255, 153, 0))
        self.screen.blit(again, again.get_rect(center=(self.width // 2, 490)))

if __name__ == '__main__':
    game = Game()
    game.run()
