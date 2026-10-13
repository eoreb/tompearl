// player.js - Желтая Душа (Yellow Soul) из Undertale со спрайтом урона «5.0»
class Player {
  constructor(arena) {
    this.arena = arena;
    this.damageSprite = new Image();
    this.damageSprite.src = 'sprites/damage_5_0.png';
    this.reset();
  }

  reset() {
    this.size = 18; // размер сердца
    this.x = this.arena.x + this.arena.width / 2;
    this.y = this.arena.y + this.arena.height - 40;
    this.speed = 5.8;
    
    this.hp = 100;
    this.maxHp = 100;
    
    this.invulnerableTimer = 0;
    this.invulnerableDuration = 0.6; // секунды неуязвимости
    
    this.bullets = [];
    this.shootCooldown = 0;
    this.shootInterval = 0.18; // интервал между выстрелами
    
    this.damagePopups = [];

    // Частицы раскола сердца при Game Over
    this.shards = [];
    this.isDead = false;
  }

  update(dt, keys, boss, attackManager) {
    if (this.isDead) {
      for (const shard of this.shards) {
        shard.x += shard.vx;
        shard.y += shard.vy;
        shard.vy += 0.3; // гравитация
        shard.rot += shard.vrot;
      }
      return;
    }

    if (this.invulnerableTimer > 0) {
      this.invulnerableTimer -= dt;
    }

    // Обновление всплывающих спрайтов урона над Сердцем
    for (let i = this.damagePopups.length - 1; i >= 0; i--) {
      const dp = this.damagePopups[i];
      dp.y += dp.vy * 60 * dt;
      dp.vy += 0.08;
      dp.alpha -= dt * 1.5;
      if (dp.alpha <= 0) {
        this.damagePopups.splice(i, 1);
      }
    }

    // Движение (стрелки и WASD)
    let dx = 0;
    let dy = 0;

    if (keys['ArrowLeft'] || keys['KeyA'] || keys['a'] || keys['A'] || keys['ф'] || keys['Ф']) dx -= 1;
    if (keys['ArrowRight'] || keys['KeyD'] || keys['d'] || keys['D'] || keys['в'] || keys['В']) dx += 1;
    if (keys['ArrowUp'] || keys['KeyW'] || keys['w'] || keys['W'] || keys['ц'] || keys['Ц']) dy -= 1;
    if (keys['ArrowDown'] || keys['KeyS'] || keys['s'] || keys['S'] || keys['ы'] || keys['Ы']) dy += 1;

    if (dx !== 0 && dy !== 0) {
      const invSqrt2 = 0.7071;
      dx *= invSqrt2;
      dy *= invSqrt2;
    }

    this.x += dx * this.speed * 60 * dt;
    this.y += dy * this.speed * 60 * dt;

    // Ограничение границами Battle Box
    const half = this.size / 2;
    const minX = this.arena.x + half + 4;
    const maxX = this.arena.x + this.arena.width - half - 4;
    const minY = this.arena.y + half + 4;
    const maxY = this.arena.y + this.arena.height - half - 4;

    this.x = Math.max(minX, Math.min(maxX, this.x));
    this.y = Math.max(minY, Math.min(maxY, this.y));

    // Стрельба (клавиша Z или Пробел)
    if (this.shootCooldown > 0) {
      this.shootCooldown -= dt;
    }

    const isShooting = keys['KeyZ'] || keys['z'] || keys['Z'] || keys['я'] || keys['Я'] || keys['Space'] || keys[' '];
    if (isShooting && this.shootCooldown <= 0) {
      this.shoot();
      this.shootCooldown = this.shootInterval;
    }

    // Обновление пуль
    for (let i = this.bullets.length - 1; i >= 0; i--) {
      const b = this.bullets[i];
      b.y -= b.speed * 60 * dt;

      // Проверка попадания в Тома Перла
      if (boss && boss.checkHit(b)) {
        this.bullets.splice(i, 1);
        continue;
      }

      // Вылет за верхний край экрана
      if (b.y < -20) {
        this.bullets.splice(i, 1);
      }
    }
  }

  shoot() {
    this.bullets.push({
      x: this.x - 4,
      y: this.y - this.size,
      width: 8,
      height: 18,
      speed: 18
    });
    if (window.audioManager) {
      window.audioManager.playShootSound();
    }
  }

  takeDamage(amount = 5) {
    if (this.invulnerableTimer > 0 || this.isDead) return;

    this.hp = Math.max(0, this.hp - amount);
    this.invulnerableTimer = this.invulnerableDuration;

    if (window.audioManager) {
      window.audioManager.playPlayerHurtSound();
    }

    // Всплывающий спрайт урона «5.0» над Сердцем
    this.damagePopups.push({
      x: this.x,
      y: this.y - 15,
      vy: -2.4,
      alpha: 1.0,
      scale: 1.0
    });

    if (this.hp <= 0) {
      this.die();
    }
  }

  die() {
    this.isDead = true;
    if (window.audioManager) {
      window.audioManager.playHeartShatterSound();
    }

    const numShards = 8;
    this.shards = [];
    for (let i = 0; i < numShards; i++) {
      const angle = (i / numShards) * Math.PI * 2;
      const speed = 2 + Math.random() * 4;
      this.shards.push({
        x: this.x,
        y: this.y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 3,
        rot: Math.random() * Math.PI,
        vrot: (Math.random() - 0.5) * 0.4,
        size: 5 + Math.random() * 4
      });
    }
  }

  draw(ctx) {
    // Рисование пуль
    ctx.fillStyle = '#ffff00';
    for (const b of this.bullets) {
      ctx.fillRect(b.x, b.y, b.width, b.height);
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(b.x + 2, b.y + 2, b.width - 4, b.height - 4);
      ctx.fillStyle = '#ffff00';
    }

    // Отрисовка всплывающего спрайта урона «5.0»
    for (const dp of this.damagePopups) {
      ctx.save();
      ctx.globalAlpha = Math.max(0, dp.alpha);
      const w = 42 * (dp.scale || 1);
      const h = 24 * (dp.scale || 1);
      if (this.damageSprite && this.damageSprite.complete && this.damageSprite.naturalWidth > 0) {
        ctx.drawImage(this.damageSprite, dp.x - w / 2, dp.y - h / 2, w, h);
      }
      ctx.restore();
    }

    if (this.isDead) {
      ctx.fillStyle = '#ffff00';
      for (const shard of this.shards) {
        ctx.save();
        ctx.translate(shard.x, shard.y);
        ctx.rotate(shard.rot);
        ctx.fillRect(-shard.size / 2, -shard.size / 2, shard.size, shard.size);
        ctx.restore();
      }
      return;
    }

    // Мигание при неуязвимости
    if (this.invulnerableTimer > 0 && Math.floor(Date.now() / 80) % 2 === 0) {
      return;
    }

    ctx.save();
    ctx.translate(this.x, this.y);
    this.drawHeart(ctx, this.size, '#ffff00');
    ctx.restore();
  }

  drawHeart(ctx, size, color) {
    ctx.fillStyle = color;
    ctx.beginPath();
    const s = size / 16;
    ctx.moveTo(0, -6 * s);
    ctx.bezierCurveTo(6 * s, -14 * s, 14 * s, -4 * s, 0, 10 * s);
    ctx.bezierCurveTo(-14 * s, -4 * s, -6 * s, -14 * s, 0, -6 * s);
    ctx.fill();

    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(-2 * s, -4 * s, 1.8 * s, 0, Math.PI * 2);
    ctx.fill();
  }
}

window.Player = Player;
