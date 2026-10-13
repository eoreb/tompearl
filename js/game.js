// game.js - Главный координатор игры «Fight Tom Pearl»
const GameState = {
  START: 'START',
  INTRO: 'INTRO',
  BATTLE: 'BATTLE',
  PAUSE: 'PAUSE',
  GAMEOVER: 'GAMEOVER',
  VICTORY: 'VICTORY'
};

class Game {
  constructor() {
    this.canvas = document.getElementById('gameCanvas');
    this.ctx = this.canvas.getContext('2d');
    this.ctx.imageSmoothingEnabled = false;

    // Параметры Battle Box
    this.arena = {
      x: 180,
      y: 300,
      width: 440,
      height: 250
    };

    this.keys = {};
    this.state = GameState.START;
    this.previousState = GameState.START;

    this.player = new Player(this.arena);
    this.boss = new Boss(this.canvas.width);
    this.attackManager = new AttackManager(this.arena);

    // Диалог интро
    this.introDialogue = [
      "Hi, my name is Tom Pearl...",
      "And today, I have something very special on my plate.",
      "Are you ready for the aura?"
    ];
    this.currentLineIndex = 0;
    this.displayedText = "";
    this.charTimer = 0;
    this.linePauseTimer = 0;
    this.introTotalTimer = 0;

    // Статистика
    this.battleTimer = 0;
    this.totalBulletsFired = 0;

    this.lastTime = performance.now();

    this.initEvents();
  }

  initEvents() {
    window.addEventListener('keydown', (e) => {
      this.keys[e.code] = true;
      this.keys[e.key] = true;

      // Горячие клавиши
      if (e.code === 'KeyP' || e.key === 'p' || e.key === 'P' || e.key === 'з' || e.key === 'З') {
        this.togglePause();
      }

      if (e.code === 'KeyM' || e.key === 'm' || e.key === 'M' || e.key === 'ь' || e.key === 'Ь') {
        const muted = window.audioManager.toggleMute();
        console.log('Audio muted:', muted);
      }

      if (this.state === GameState.START) {
        if (e.code === 'Enter' || e.code === 'Space' || e.code === 'KeyZ') {
          const startBtn = document.getElementById('start-btn');
          if (startBtn) startBtn.click();
        }
      }

      if (e.code === 'KeyR' || e.key === 'r' || e.key === 'R' || e.key === 'к' || e.key === 'К') {
        if (this.state === GameState.GAMEOVER || this.state === GameState.VICTORY) {
          this.startBattleDirectly(true);
        }
      }

      // Пропуск диалога на Z, Пробел или Enter
      if (this.state === GameState.INTRO) {
        if (e.code === 'KeyZ' || e.code === 'Space' || e.code === 'Enter' || e.key === 'z' || e.key === 'Z' || e.key === 'я' || e.key === 'Я' || e.key === 'Enter') {
          this.advanceIntro();
        }
      }
    });

    window.addEventListener('keyup', (e) => {
      this.keys[e.code] = false;
      this.keys[e.key] = false;
    });

    // Клик по экрану для промотки интро
    this.canvas.addEventListener('click', () => {
      if (this.state === GameState.INTRO) {
        this.advanceIntro();
      }
    });

    // Кнопка старта
    const startBtn = document.getElementById('start-btn');
    if (startBtn) {
      startBtn.addEventListener('click', () => {
        document.getElementById('start-overlay').classList.add('hidden');
        this.startIntro();
      });
    }

    // Кнопка продолжить в паузе
    const resumeBtn = document.getElementById('resume-btn');
    if (resumeBtn) {
      resumeBtn.addEventListener('click', () => {
        this.togglePause();
      });
    }
  }

  startIntro() {
    this.state = GameState.INTRO;
    this.currentLineIndex = 0;
    this.displayedText = "";
    this.charTimer = 0;
    this.linePauseTimer = 0;
    this.introTotalTimer = 0;
    window.audioManager.playIntro();
  }

  advanceIntro() {
    // Если текущая строка еще печатается - показать целиком
    const fullLine = this.introDialogue[this.currentLineIndex];
    if (this.displayedText.length < fullLine.length) {
      this.displayedText = fullLine;
      this.linePauseTimer = 0;
      return;
    }

    // Иначе сразу перейти к следующей строке или сразу в бой
    this.currentLineIndex++;
    if (this.currentLineIndex < this.introDialogue.length) {
      this.displayedText = "";
      this.charTimer = 0;
      this.linePauseTimer = 0;
    } else {
      this.startBattleDirectly();
    }
  }

  startBattleDirectly(isRestart = false) {
    this.state = GameState.BATTLE;
    this.player.reset();
    this.boss.reset();
    this.attackManager.reset();
    this.battleTimer = 0;
    this.totalBulletsFired = 0;

    window.audioManager.playBattle(isRestart);
  }

  togglePause() {
    if (this.state === GameState.PAUSE) {
      this.state = this.previousState;
      document.getElementById('pause-overlay').classList.add('hidden');
    } else if (this.state === GameState.BATTLE || this.state === GameState.INTRO) {
      this.previousState = this.state;
      this.state = GameState.PAUSE;
      document.getElementById('pause-overlay').classList.remove('hidden');
    }
  }

  start() {
    requestAnimationFrame((t) => this.loop(t));
  }

  loop(currentTime) {
    const dt = Math.min((currentTime - this.lastTime) / 1000, 0.1);
    this.lastTime = currentTime;

    this.update(dt);
    this.render();

    requestAnimationFrame((t) => this.loop(t));
  }

  update(dt) {
    if (this.state === GameState.PAUSE || this.state === GameState.START) {
      return;
    }

    if (this.state === GameState.INTRO) {
      this.updateIntro(dt);
      return;
    }

    if (this.state === GameState.BATTLE) {
      this.battleTimer += dt;
      this.player.update(dt, this.keys, this.boss, this.attackManager);
      this.boss.update(dt);
      this.attackManager.update(dt, this.player, this.boss);

      if (this.player.isDead) {
        this.state = GameState.GAMEOVER;
      } else if (this.boss.isDefeated) {
        this.state = GameState.VICTORY;
      }
      return;
    }

    if (this.state === GameState.GAMEOVER) {
      this.player.update(dt, this.keys, null);
      return;
    }

    if (this.state === GameState.VICTORY) {
      this.boss.update(dt);
      return;
    }
  }

  updateIntro(dt) {
    this.boss.update(dt);
    this.introTotalTimer += dt;

    // Автоматический переход в бой по окончании интро-трека (14 сек)
    if (this.introTotalTimer > 14.5) {
      this.startBattleDirectly();
      return;
    }

    const currentLine = this.introDialogue[this.currentLineIndex];
    if (this.displayedText.length < currentLine.length) {
      this.charTimer += dt;
      if (this.charTimer >= 0.045) {
        this.charTimer = 0;
        this.displayedText += currentLine[this.displayedText.length];
        if (Math.random() < 0.6) {
          window.audioManager.playTextBlip();
        }
      }
    } else {
      this.linePauseTimer += dt;
      if (this.linePauseTimer >= 1.2) {
        this.linePauseTimer = 0;
        this.currentLineIndex++;
        if (this.currentLineIndex < this.introDialogue.length) {
          this.displayedText = "";
        } else {
          this.startBattleDirectly();
        }
      }
    }
  }

  render() {
    this.ctx.fillStyle = '#000000';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    if (this.state === GameState.START) {
      this.renderStartScreen();
      return;
    }

    if (this.state === GameState.INTRO) {
      this.renderIntroScreen();
      return;
    }

    if (this.state === GameState.BATTLE || this.state === GameState.PAUSE) {
      this.renderBattleScreen();
      return;
    }

    if (this.state === GameState.GAMEOVER) {
      this.renderGameOverScreen();
      return;
    }

    if (this.state === GameState.VICTORY) {
      this.renderVictoryScreen();
      return;
    }
  }

  renderStartScreen() {
    // Вступительный черный экран перед кликом
    this.boss.draw(this.ctx);
  }

  renderIntroScreen() {
    // Босс
    this.boss.draw(this.ctx);

    // Диалоговое окно Undertale
    const boxX = 100;
    const boxY = 350;
    const boxW = 600;
    const boxH = 190;

    this.ctx.fillStyle = '#000000';
    this.ctx.fillRect(boxX, boxY, boxW, boxH);
    this.ctx.strokeStyle = '#ffffff';
    this.ctx.lineWidth = 4;
    this.ctx.strokeRect(boxX, boxY, boxW, boxH);

    // Сброс выравнивания текста для корректного отображения внутри окна
    this.ctx.textAlign = 'left';
    this.ctx.textBaseline = 'top';

    // Звездочка Undertale
    this.ctx.fillStyle = '#ff0000';
    this.ctx.font = '16px "Press Start 2P", monospace';
    this.ctx.fillText('*', boxX + 25, boxY + 38);

    // Текст
    this.ctx.fillStyle = '#ffffff';
    this.ctx.font = '13px "Press Start 2P", monospace';
    this.wrapText(this.displayedText, boxX + 55, boxY + 38, boxW - 80, 26);

    // Подсказка пропуска
    this.ctx.fillStyle = '#888888';
    this.ctx.font = '10px "Press Start 2P", monospace';
    this.ctx.textAlign = 'right';
    this.ctx.textBaseline = 'bottom';
    this.ctx.fillText('[ Z / Пробел ] Пропустить', boxX + boxW - 20, boxY + boxH - 14);
  }

  wrapText(text, x, y, maxWidth, lineHeight) {
    this.ctx.textAlign = 'left';
    this.ctx.textBaseline = 'top';
    const words = text.split(' ');
    let line = '';
    let currentY = y;

    for (let n = 0; n < words.length; n++) {
      const testLine = line + words[n] + ' ';
      const metrics = this.ctx.measureText(testLine);
      const testWidth = metrics.width;
      if (testWidth > maxWidth && n > 0) {
        this.ctx.fillText(line, x, currentY);
        line = words[n] + ' ';
        currentY += lineHeight;
      } else {
        line = testLine;
      }
    }
    this.ctx.fillText(line, x, currentY);
  }

  renderBattleScreen() {
    this.ctx.save();
    if (this.attackManager && this.attackManager.shakeAmount > 0) {
      const s = this.attackManager.shakeAmount;
      this.ctx.translate((Math.random() - 0.5) * s, (Math.random() - 0.5) * s);
    }

    // 1. Отрисовка Босса Тома Перла
    this.boss.draw(this.ctx);

    // 2. Полоса здоровья Босса (Undertale Boss Bar)
    this.renderBossHealthBar();

    // 3. Рамка Battle Box
    this.ctx.fillStyle = '#000000';
    this.ctx.fillRect(this.arena.x, this.arena.y, this.arena.width, this.arena.height);
    this.ctx.strokeStyle = '#ffffff';
    this.ctx.lineWidth = 4;
    this.ctx.strokeRect(this.arena.x, this.arena.y, this.arena.width, this.arena.height);

    // 4. Отрисовка атак босса (хёртбоксы, тарелки, лазеры)
    this.attackManager.draw(this.ctx);

    // 5. Отрисовка игрока (Желтой Души) и его пуль
    this.player.draw(this.ctx);

    // 6. HUD игрока (Undertale HP Bar)
    this.renderPlayerHUD();

    this.ctx.restore();
  }

  renderBossHealthBar() {
    const barW = 300;
    const barH = 16;
    const barX = this.canvas.width / 2 - barW / 2;
    const barY = 242;

    // Фон полосы
    this.ctx.fillStyle = '#330000';
    this.ctx.fillRect(barX, barY, barW, barH);

    // Цвет полосы в зависимости от фазы
    const phase = this.boss.currentPhase || 1;
    let barColor = '#00ff00';
    let phaseName = 'PHASE 1: THE TASTE';
    if (phase === 2) {
      barColor = '#aaff00';
      phaseName = 'PHASE 2: SUBSTANCE RUSH';
    } else if (phase === 3) {
      barColor = '#ffaa00';
      phaseName = 'PHASE 3: PHONK AURA';
    } else if (phase === 4) {
      barColor = Math.floor(Date.now() / 120) % 2 === 0 ? '#ff0055' : '#ff3300';
      phaseName = 'FINAL PHASE: LAST PLATE';
    }

    const hpPercent = Math.max(0, this.boss.hp / this.boss.maxHp);
    this.ctx.fillStyle = barColor;
    this.ctx.fillRect(barX, barY, barW * hpPercent, barH);

    // Рамка
    this.ctx.strokeStyle = '#ffffff';
    this.ctx.lineWidth = 2;
    this.ctx.strokeRect(barX, barY, barW, barH);

    // Текст
    this.ctx.font = '9px "Press Start 2P", monospace';
    this.ctx.fillStyle = '#ffffff';
    this.ctx.textAlign = 'center';
    this.ctx.fillText(`PEARL HP: ${this.boss.hp} / ${this.boss.maxHp}`, this.canvas.width / 2, barY + barH + 14);

    this.ctx.fillStyle = phase === 4 ? '#ff0055' : '#ffcc00';
    this.ctx.fillText(`[ ${phaseName} ]`, this.canvas.width / 2, barY - 8);
  }

  renderPlayerHUD() {
    const hudY = 585;

    this.ctx.font = '14px "Press Start 2P", monospace';
    this.ctx.textAlign = 'left';
    
    // Имя и Уровень
    this.ctx.fillStyle = '#ffffff';
    this.ctx.fillText('YOU   LV 19', this.arena.x, hudY);

    // Метка HP
    this.ctx.font = '12px "Press Start 2P", monospace';
    this.ctx.fillText('HP', this.arena.x + 180, hudY);

    // Полоска здоровья
    const hpBarX = this.arena.x + 215;
    const hpBarW = 120;
    const hpBarH = 14;

    this.ctx.fillStyle = '#c00000';
    this.ctx.fillRect(hpBarX, hudY - 12, hpBarW, hpBarH);

    const playerHpPercent = Math.max(0, this.player.hp / this.player.maxHp);
    this.ctx.fillStyle = '#ffff00';
    this.ctx.fillRect(hpBarX, hudY - 12, hpBarW * playerHpPercent, hpBarH);

    // Цифры здоровья
    this.ctx.fillStyle = '#ffffff';
    this.ctx.fillText(`${this.player.hp} / ${this.player.maxHp}`, hpBarX + hpBarW + 15, hudY);

    // Подсказка управления
    this.ctx.font = '9px "Press Start 2P", monospace';
    this.ctx.fillStyle = '#777777';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('[СТРЕЛКИ/WASD] Движение   [Z / Пробел] Стрельба   [M] Звук', this.canvas.width / 2, 625);
  }

  renderGameOverScreen() {
    // Отрисовка осколков
    this.player.draw(this.ctx);

    this.ctx.textAlign = 'center';

    this.ctx.fillStyle = '#ffffff';
    this.ctx.font = '32px "Press Start 2P", monospace';
    this.ctx.fillText('GAME OVER', this.canvas.width / 2, 220);

    this.ctx.font = '13px "Press Start 2P", monospace';
    this.ctx.fillStyle = '#cccccc';
    this.ctx.fillText('Не теряй свой жемчуг...', this.canvas.width / 2, 300);
    this.ctx.fillText('Тарелка Тома Перла оказалась сильнее.', this.canvas.width / 2, 335);

    this.ctx.font = '14px "Press Start 2P", monospace';
    this.ctx.fillStyle = '#ffff00';
    this.ctx.fillText('[ Нажмите R для перезапуска ]', this.canvas.width / 2, 450);
  }

  renderVictoryScreen() {
    this.boss.draw(this.ctx);

    this.ctx.textAlign = 'center';

    this.ctx.fillStyle = '#ffff00';
    this.ctx.font = '28px "Press Start 2P", monospace';
    this.ctx.fillText('ПОБЕДА!', this.canvas.width / 2, 270);

    this.ctx.fillStyle = '#ffffff';
    this.ctx.font = '13px "Press Start 2P", monospace';
    this.ctx.fillText('Том Перл повержен!', this.canvas.width / 2, 330);
    this.ctx.fillText(`Время битвы: ${this.battleTimer.toFixed(1)} сек`, this.canvas.width / 2, 365);
    this.ctx.fillText(`Оставшееся HP: ${this.player.hp} / ${this.player.maxHp}`, this.canvas.width / 2, 400);

    this.ctx.font = '14px "Press Start 2P", monospace';
    this.ctx.fillStyle = '#ff9900';
    this.ctx.fillText('[ Нажмите R чтобы сыграть снова ]', this.canvas.width / 2, 490);
  }
}

// Запуск игры после загрузки DOM
window.addEventListener('DOMContentLoaded', () => {
  window.game = new Game();
  window.game.start();
});
