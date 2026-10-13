// boss.js - Логика, анимация и фазы босса Тома Перла (1000 HP, 4 фазы, реплики Undertale)
class Boss {
  constructor(canvasWidth) {
    this.canvasWidth = canvasWidth;
    this.image = new Image();
    this.image.src = 'sprites/tom.jpeg';
    this.isImageLoaded = false;
    this.image.onload = () => {
      this.isImageLoaded = true;
    };

    // Спрайт урона «5.0»
    this.damageSprite = new Image();
    this.damageSprite.src = 'sprites/damage_5_0.png';

    this.reset();
  }

  reset() {
    this.maxHp = 1000;
    this.hp = 1000;
    this.width = 200;
    this.height = 200;
    this.baseX = this.canvasWidth / 2;
    this.baseY = 125;
    this.x = this.baseX;
    this.y = this.baseY;

    this.time = 0;
    this.currentPhase = 1; // 1, 2, 3, 4
    this.speechBubble = null; // { text: "...", timer: 3.0 }

    this.hitFlashTimer = 0;
    this.shakeOffsetX = 0;
    this.shakeOffsetY = 0;

    this.damagePopups = [];
    this.particles = [];
    this.isDefeated = false;
    this.defeatTimer = 0;
  }

  update(dt) {
    this.time += dt;

    if (this.speechBubble) {
      this.speechBubble.timer -= dt;
      if (this.speechBubble.timer <= 0) {
        this.speechBubble = null;
      }
    }

    if (this.isDefeated) {
      this.defeatTimer += dt;
      this.shakeOffsetX = (Math.random() - 0.5) * 14;
      this.shakeOffsetY = (Math.random() - 0.5) * 14;

      if (Math.random() < 0.35) {
        this.spawnDefeatParticle();
      }
      this.updateParticles(dt);
      return;
    }

    // Проверка смены фаз
    if (this.currentPhase === 1 && this.hp <= 750) {
      this.currentPhase = 2;
      this.speechBubble = { text: "Is that all?\nTaste this plate!", timer: 3.2 };
      this.hitFlashTimer = 0.25;
    } else if (this.currentPhase === 2 && this.hp <= 500) {
      this.currentPhase = 3;
      this.speechBubble = { text: "Aura 5.0 kicking in!\nFeel the phonk!", timer: 3.2 };
      this.hitFlashTimer = 0.3;
    } else if (this.currentPhase === 3 && this.hp <= 200) {
      this.currentPhase = 4;
      this.speechBubble = { text: "IMPOSSIBLE!\nMY FINAL PLATE!", timer: 3.6 };
      this.hitFlashTimer = 0.4;
    }

    // Покачивание под бит (в финальной фазе интенсивнее)
    const bobSpeed = this.currentPhase === 4 ? 6.5 : this.currentPhase === 3 ? 5 : 4;
    const bobbing = Math.sin(this.time * bobSpeed) * (this.currentPhase === 4 ? 9 : 6);
    const sway = Math.cos(this.time * 2.5) * 4;
    this.x = this.baseX + sway + this.shakeOffsetX;
    this.y = this.baseY + bobbing + this.shakeOffsetY;

    // Вспышка урона
    if (this.hitFlashTimer > 0) {
      this.hitFlashTimer -= dt;
      this.shakeOffsetX = (Math.random() - 0.5) * (this.currentPhase === 4 ? 8 : 5);
      this.shakeOffsetY = (Math.random() - 0.5) * (this.currentPhase === 4 ? 8 : 5);
    } else {
      this.shakeOffsetX = 0;
      this.shakeOffsetY = 0;
    }

    // Обновление всплывающих спрайтов урона «5.0»
    for (let i = this.damagePopups.length - 1; i >= 0; i--) {
      const dp = this.damagePopups[i];
      dp.y += dp.vy * 60 * dt;
      dp.vy += 0.08;
      dp.alpha -= dt * 1.3;
      dp.scale = Math.max(0.85, dp.scale - dt * 0.3);
      if (dp.alpha <= 0) {
        this.damagePopups.splice(i, 1);
      }
    }

    this.updateParticles(dt);
  }

  updateParticles(dt) {
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.x += p.vx * 60 * dt;
      p.y += p.vy * 60 * dt;
      p.life -= dt;
      if (p.life <= 0) {
        this.particles.splice(i, 1);
      }
    }
  }

  spawnDefeatParticle() {
    const rx = this.x + (Math.random() - 0.5) * this.width;
    const ry = this.y + (Math.random() - 0.5) * this.height;
    this.particles.push({
      x: rx,
      y: ry,
      vx: (Math.random() - 0.5) * 6,
      vy: (Math.random() - 0.5) * 6,
      size: 5 + Math.random() * 8,
      color: Math.random() > 0.5 ? '#ffff00' : '#ff0055',
      life: 0.6 + Math.random() * 0.5
    });
  }

  checkHit(bullet) {
    if (this.isDefeated) return false;

    const left = this.x - this.width / 2 + 15;
    const right = this.x + this.width / 2 - 15;
    const top = this.y - this.height / 2 + 10;
    const bottom = this.y + this.height / 2;

    if (
      bullet.x + bullet.width > left &&
      bullet.x < right &&
      bullet.y + bullet.height > top &&
      bullet.y < bottom
    ) {
      this.takeDamage(5); // 5.0 урона за выстрел (всего 200 выстрелов на 1000 HP)
      return true;
    }
    return false;
  }

  takeDamage(amount = 5) {
    if (this.isDefeated) return;

    this.hp = Math.max(0, this.hp - amount);
    this.hitFlashTimer = 0.08;

    if (window.audioManager) {
      window.audioManager.playBossHitSound();
    }

    this.damagePopups.push({
      x: this.x + (Math.random() - 0.5) * 50,
      y: this.y - 25,
      vy: -2.6,
      alpha: 1.0,
      scale: 1.2
    });

    if (this.hp <= 0) {
      this.defeat();
    }
  }

  defeat() {
    this.isDefeated = true;
    this.speechBubble = { text: "NOOO...\nMY DELICIOUS...", timer: 5.0 };
    if (window.audioManager) {
      window.audioManager.stopBattle();
      window.audioManager.playVictorySound();
    }
  }

  draw(ctx) {
    ctx.save();

    const drawX = this.x - this.width / 2;
    const drawY = this.y - this.height / 2;

    // В финальной фазе 4 — неоновая пульсирующая аура
    if (this.currentPhase === 4 && !this.isDefeated) {
      const pulse = 15 + Math.sin(this.time * 8) * 10;
      ctx.save();
      ctx.shadowColor = '#ff0055';
      ctx.shadowBlur = pulse;
      ctx.fillStyle = 'rgba(255, 0, 85, 0.25)';
      ctx.fillRect(drawX - 8, drawY - 8, this.width + 16, this.height + 16);
      ctx.restore();
    }

    if (this.isImageLoaded) {
      ctx.save();
      ctx.beginPath();
      ctx.roundRect(drawX, drawY, this.width, this.height, 10);
      ctx.clip();

      ctx.drawImage(this.image, drawX, drawY, this.width, this.height);

      if (this.hitFlashTimer > 0) {
        ctx.fillStyle = 'rgba(255, 60, 60, 0.65)';
        ctx.fillRect(drawX, drawY, this.width, this.height);
      }

      ctx.restore();

      ctx.strokeStyle = this.currentPhase === 4 ? '#ff0055' : this.hitFlashTimer > 0 ? '#ff0000' : '#ffffff';
      ctx.lineWidth = 3;
      ctx.strokeRect(drawX, drawY, this.width, this.height);
    } else {
      ctx.fillStyle = '#444444';
      ctx.fillRect(drawX, drawY, this.width, this.height);
      ctx.fillStyle = '#ffffff';
      ctx.font = '14px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('TOM PEARL', this.x, this.y);
    }

    // Имя босса
    ctx.font = '16px "Press Start 2P", monospace';
    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    ctx.fillText('TOM PEARL', this.x, drawY - 14);

    // Отрисовка Undertale облачка диалога босса (Speech Bubble)
    if (this.speechBubble) {
      this.drawSpeechBubble(ctx, drawX + this.width + 12, drawY + 15, this.speechBubble.text);
    }

    // Частицы
    for (const p of this.particles) {
      ctx.fillStyle = p.color;
      ctx.fillRect(p.x, p.y, p.size, p.size);
    }

    // Отрисовка спрайта урона «5.0»
    for (const dp of this.damagePopups) {
      ctx.save();
      ctx.globalAlpha = Math.max(0, dp.alpha);
      const w = 50 * dp.scale;
      const h = 28 * dp.scale;
      if (this.damageSprite && this.damageSprite.complete && this.damageSprite.naturalWidth > 0) {
        ctx.drawImage(this.damageSprite, dp.x - w / 2, dp.y - h / 2, w, h);
      } else {
        ctx.font = '16px "Press Start 2P", monospace';
        ctx.fillStyle = '#ff2222';
        ctx.textAlign = 'center';
        ctx.fillText('-5.0', dp.x, dp.y);
      }
      ctx.restore();
    }

    ctx.restore();
  }

  // Облачко реплик в стиле Undertale
  drawSpeechBubble(ctx, x, y, text) {
    ctx.save();
    const bw = 175;
    const bh = 65;

    // Белое тело облачка
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(x, y, bw, bh);
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 3;
    ctx.strokeRect(x, y, bw, bh);

    // Хвостик облачка к рту Тома
    ctx.beginPath();
    ctx.moveTo(x, y + 25);
    ctx.lineTo(x - 12, y + 32);
    ctx.lineTo(x, y + 38);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.stroke();

    // Текст реплики
    ctx.fillStyle = '#000000';
    ctx.font = '9px "Press Start 2P", monospace';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    const lines = text.split('\n');
    lines.forEach((l, i) => {
      ctx.fillText(l, x + 10, y + 12 + i * 18);
    });

    ctx.restore();
  }
}

window.Boss = Boss;
