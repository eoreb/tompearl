// attacks.js - 10 эпических атак Тома Перла (тарелки, брызги, лазеры, ракеты, бомбы, серпы, квадро-бластеры)
class AttackManager {
  constructor(arena) {
    this.arena = arena;
    this.reset();
  }

  reset(difficulty = null) {
    const diff = difficulty || { speedMultiplier: 1.0, cooldownMultiplier: 1.0, healInterval: 40 };
    this.speedMultiplier = diff.speedMultiplier || 1.0;
    this.cooldownMultiplier = diff.cooldownMultiplier || 1.0;
    this.healInterval = diff.healInterval !== undefined ? diff.healInterval : 40;
    this.healAmount = diff.healAmount || 20;
    this.healTimer = 0;
    this.healPickups = [];

    this.projectiles = [];
    this.lasers = [];
    this.telegraphs = [];
    this.currentPattern = 0;
    this.patternCooldown = 0.3 * this.cooldownMultiplier;
    this.patternTime = 0;
    this.spiralAngle = 0;
    this.shakeAmount = 0;
  }

  onPhaseChange(phase) {
    // Очистить хёртбоксы при смене фазы, чтобы дать игроку передышку под реплику босса
    this.projectiles = this.projectiles.filter(p => p.type !== 'hurtbox');

    // Если не хардкор — выбрасываем восстанавливающий жемчуг здоровья (+HP)
    if (this.healAmount > 0) {
      this.spawnHealPickup(this.healAmount);
    }
  }

  spawnHealPickup(amount = 20) {
    const x = this.arena.x + 40 + Math.random() * (this.arena.width - 80);
    const y = this.arena.y + 40 + Math.random() * (this.arena.height - 80);
    this.healPickups.push({
      x: x,
      y: y,
      baseY: y,
      radius: 12,
      amount: amount,
      time: 0,
      life: 14.0, // висит 14 секунд
      update: function(dt) {
        this.time += dt * 3.5;
        this.y = this.baseY + Math.sin(this.time) * 5;
        this.life -= dt;
      },
      draw: function(ctx) {
        ctx.save();
        const pulse = 1.0 + Math.sin(this.time * 2) * 0.2;
        
        // Внешнее свечение
        ctx.shadowColor = '#00ff66';
        ctx.shadowBlur = 10;
        ctx.fillStyle = 'rgba(0, 255, 102, 0.35)';
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius * pulse * 1.35, 0, Math.PI * 2);
        ctx.fill();

        // Сердцевинка жемчужины
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius * pulse, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = '#00ff66';
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius * 0.7 * pulse, 0, Math.PI * 2);
        ctx.fill();

        // Крестик лечения (+)
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(this.x - 2, this.y - 6, 4, 12);
        ctx.fillRect(this.x - 6, this.y - 2, 12, 4);

        ctx.restore();
      }
    });
  }

  update(dt, player, boss) {
    if (!boss || boss.isDefeated || !player || player.isDead) return;

    this.patternTime += dt;

    if (this.shakeAmount > 0) {
      this.shakeAmount = Math.max(0, this.shakeAmount - dt * 25);
    }

    // Обновление предметов лечения (Heal Pickups)
    for (let i = this.healPickups.length - 1; i >= 0; i--) {
      const hp = this.healPickups[i];
      hp.update(dt);

      // Проверка подбора игроком
      const dx = player.x - hp.x;
      const dy = player.y - hp.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < hp.radius + player.size / 2) {
        player.heal(hp.amount);
        this.healPickups.splice(i, 1);
        continue;
      }

      if (hp.life <= 0) {
        this.healPickups.splice(i, 1);
      }
    }

    // Периодический спавн хилки в легком/нормальном режиме при низком HP
    if (this.healInterval > 0 && player.hp < player.maxHp * 0.6) {
      this.healTimer += dt;
      if (this.healTimer >= this.healInterval) {
        this.healTimer = 0;
        if (this.healPickups.length < 2) {
          this.spawnHealPickup(this.healAmount);
        }
      }
    }

    // 4 фазы боя (пропорционально максимальному HP босса)
    const p2Threshold = boss.maxHp * 0.75;
    const p3Threshold = boss.maxHp * 0.50;
    const p4Threshold = boss.maxHp * 0.20;

    const isPhase2 = boss.hp <= p2Threshold && boss.hp > p3Threshold;
    const isPhase3 = boss.hp <= p3Threshold && boss.hp > p4Threshold;
    const isPhase4 = boss.hp <= p4Threshold; // Final Stand

    // Динамическая смена 10 паттернов с учетом сложности
    const patternCycleTime = (isPhase4 ? 2.8 : isPhase3 ? 3.5 : isPhase2 ? 4.2 : 5.0) * this.cooldownMultiplier;
    if (this.patternTime > patternCycleTime) {
      this.patternTime = 0;
      this.currentPattern = (this.currentPattern + 1) % 10;
      this.patternCooldown = 0.15 * this.cooldownMultiplier;
    }

    // Фоновые препятствия в поздних фазах
    const maxBackgroundHurtboxes = isPhase4 ? 2 : (isPhase3 || isPhase2) ? 1 : 0;
    if (this.projectiles.filter(p => p.type === 'hurtbox').length < maxBackgroundHurtboxes) {
      this.spawnBouncingHurtbox((isPhase4 ? 5.5 : isPhase3 ? 4.8 : 4.0) * this.speedMultiplier);
    }

    // Запуск текущего активного паттерна
    this.runPattern(dt, player, boss, isPhase2, isPhase3, isPhase4);

    // Обновление снарядов
    for (let i = this.projectiles.length - 1; i >= 0; i--) {
      const p = this.projectiles[i];
      p.update(dt, this.arena, player);

      // Проверка столкновения с игроком
      if (this.checkCollision(p, player)) {
        player.takeDamage(p.damage || 5);
        if (p.destroyOnHit) {
          if (p.type === 'plate' && p.burstOnDestroy) {
            this.spawnPlateShrapnel(p.x, p.y);
          }
          this.projectiles.splice(i, 1);
          continue;
        }
      }

      // Если тарелка ударилась о пол арены, она взрывается на брызги
      if (p.type === 'plate' && p.y >= this.arena.y + this.arena.height - 10) {
        this.spawnPlateShrapnel(p.x, p.y);
        this.projectiles.splice(i, 1);
        continue;
      }

      // Если бомба взорвалась
      if (p.type === 'bomb' && p.exploded) {
        this.explodeBomb(p.x, p.y);
        this.projectiles.splice(i, 1);
        continue;
      }

      if (p.isDead) {
        this.projectiles.splice(i, 1);
      }
    }

    // Обновление лазеров
    for (let i = this.lasers.length - 1; i >= 0; i--) {
      const laser = this.lasers[i];
      laser.time += dt;

      if (laser.time >= laser.warningDuration && laser.time < laser.warningDuration + laser.activeDuration) {
        let hit = false;
        if (laser.axis === 'horizontal') {
          hit = player.y >= laser.pos - laser.thickness / 2 && player.y <= laser.pos + laser.thickness / 2;
        } else {
          hit = player.x >= laser.pos - laser.thickness / 2 && player.x <= laser.pos + laser.thickness / 2;
        }
        if (hit) {
          player.takeDamage(laser.damage || 5);
        }
      }

      if (laser.time >= laser.warningDuration + laser.activeDuration) {
        this.lasers.splice(i, 1);
      }
    }

    // Обновление телеграфов зон поражения (Мега-удар)
    for (let i = this.telegraphs.length - 1; i >= 0; i--) {
      const t = this.telegraphs[i];
      t.time += dt;

      if (t.time >= t.warningDuration && !t.triggered) {
        t.triggered = true;
        this.shakeAmount = 9;
        if (
          player.x >= t.x &&
          player.x <= t.x + t.w &&
          player.y >= t.y &&
          player.y <= t.y + t.h
        ) {
          player.takeDamage(10);
        }
      }

      if (t.time >= t.warningDuration + t.slamDuration) {
        this.telegraphs.splice(i, 1);
      }
    }
  }

  runPattern(dt, player, boss, isPhase2, isPhase3, isPhase4) {
    this.patternCooldown -= dt;

    const cdMult = this.cooldownMultiplier || 1.0;
    const spdMult = this.speedMultiplier || 1.0;

    switch (this.currentPattern) {
      case 0:
        // Паттерн 0: Скоростные хёртбоксы
        if (this.projectiles.filter(p => p.type === 'hurtbox').length < (isPhase4 ? 3 : isPhase3 ? 2 : 1)) {
          this.spawnBouncingHurtbox((isPhase4 ? 5.8 : isPhase3 ? 4.8 : 4.0) * spdMult);
        }
        break;

      case 1:
        // Паттерн 1: Падающие тарелки с разрывом на осколки
        if (this.patternCooldown <= 0) {
          this.spawnFallingPlate((isPhase4 ? 6.8 : isPhase3 ? 5.8 : isPhase2 ? 4.8 : 4.0) * spdMult);
          this.patternCooldown = (isPhase4 ? 0.35 : isPhase3 ? 0.5 : isPhase2 ? 0.65 : 0.85) * cdMult;
        }
        break;

      case 2:
        // Паттерн 2: Спиральный шквал жемчужин (Danmaku)
        if (this.patternCooldown <= 0) {
          this.spawnSpiralPearlWave(isPhase4 ? 3 : 2);
          this.patternCooldown = (isPhase4 ? 0.12 : isPhase3 ? 0.16 : 0.22) * cdMult;
        }
        break;

      case 3:
        // Паттерн 3: Лазерная сетка (Crossfire Lasers)
        if (this.patternCooldown <= 0) {
          this.spawnLaserGrid(isPhase3 || isPhase4);
          this.patternCooldown = (isPhase4 ? 1.1 : isPhase3 ? 1.4 : 1.9) * cdMult;
        }
        break;

      case 4:
        // Паттерн 4: Самонаводящиеся снаряды
        if (this.patternCooldown <= 0) {
          this.spawnHomingMissile(player, isPhase3 || isPhase4);
          this.patternCooldown = (isPhase4 ? 0.65 : isPhase3 ? 0.85 : 1.25) * cdMult;
        }
        break;

      case 5:
        // Паттерн 5: Мега-удар тарелкой по полу арены
        if (this.patternCooldown <= 0) {
          this.spawnMegaPlateSlam();
          this.patternCooldown = (isPhase4 ? 1.8 : isPhase3 ? 2.2 : 2.8) * cdMult;
        }
        break;

      case 6:
        // Паттерн 6: Таймер-Бомба Тома Перла (Diaper Bomb)
        if (this.patternCooldown <= 0 && this.projectiles.filter(p => p.type === 'bomb').length === 0) {
          this.spawnDiaperBomb();
          this.patternCooldown = (isPhase4 ? 2.5 : 3.2) * cdMult;
        }
        break;

      case 7:
        // Паттерн 7: Серповидные энергетические волны ауры
        if (this.patternCooldown <= 0) {
          this.spawnAuraSlash();
          this.patternCooldown = (isPhase4 ? 0.55 : isPhase3 ? 0.75 : 1.0) * cdMult;
        }
        break;

      case 8:
        // Паттерн 8: Каскадная лавина тарелок
        if (this.patternCooldown <= 0) {
          this.spawnPlateAvalanche(isPhase4);
          this.patternCooldown = (isPhase4 ? 0.25 : 0.35) * cdMult;
        }
        break;

      case 9:
        // Паттерн 9: Квадро-бластерный перекрёстный крест
        if (this.patternCooldown <= 0) {
          this.spawnQuadBlaster();
          this.patternCooldown = (isPhase4 ? 1.5 : 2.2) * cdMult;
        }
        break;
    }
  }

  // 1. Хёртбокс
  spawnBouncingHurtbox(speed = 4.0) {
    const size = 42;
    const p = {
      type: 'hurtbox',
      x: this.arena.x + 20 + Math.random() * (this.arena.width - 60),
      y: this.arena.y + 20,
      width: size,
      height: size,
      vx: (Math.random() > 0.5 ? 1 : -1) * speed,
      vy: (0.7 + Math.random() * 0.6) * speed,
      trail: [],
      life: 7.5,
      damage: 5,
      destroyOnHit: false,
      isDead: false,
      update: function(dt, arena) {
        this.trail.push({ x: this.x, y: this.y });
        if (this.trail.length > 4) this.trail.shift();

        this.x += this.vx * 60 * dt;
        this.y += this.vy * 60 * dt;

        if (this.x < arena.x + 4) {
          this.x = arena.x + 4;
          this.vx = Math.abs(this.vx);
        } else if (this.x + this.width > arena.x + arena.width - 4) {
          this.x = arena.x + arena.width - 4 - this.width;
          this.vx = -Math.abs(this.vx);
        }

        if (this.y < arena.y + 4) {
          this.y = arena.y + 4;
          this.vy = Math.abs(this.vy);
        } else if (this.y + this.height > arena.y + arena.height - 4) {
          this.y = arena.y + arena.height - 4 - this.height;
          this.vy = -Math.abs(this.vy);
        }

        this.life -= dt;
        if (this.life <= 0) this.isDead = true;
      },
      draw: function(ctx) {
        for (let t = 0; t < this.trail.length; t++) {
          const pt = this.trail[t];
          const a = (t + 1) / (this.trail.length + 1) * 0.25;
          ctx.fillStyle = `rgba(255, 30, 30, ${a})`;
          ctx.fillRect(pt.x, pt.y, this.width, this.height);
        }

        ctx.fillStyle = 'rgba(235, 35, 35, 0.65)';
        ctx.fillRect(this.x, this.y, this.width, this.height);
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.strokeRect(this.x, this.y, this.width, this.height);
      }
    };
    this.projectiles.push(p);
  }

  // 2. Падающая тарелка
  spawnFallingPlate(speed = 4.5) {
    const radius = 17;
    const laneX = this.arena.x + 25 + Math.random() * (this.arena.width - 50);
    const p = {
      type: 'plate',
      x: laneX,
      y: this.arena.y - 20,
      radius: radius,
      vy: speed + Math.random() * 1.5,
      rotation: 0,
      damage: 5,
      destroyOnHit: true,
      burstOnDestroy: true,
      isDead: false,
      update: function(dt) {
        this.y += this.vy * 60 * dt;
        this.rotation += 6 * dt;
      },
      draw: function(ctx) {
        ctx.save();
        ctx.translate(this.x, this.y);
        ctx.rotate(this.rotation);
        
        ctx.fillStyle = '#f5f5f5';
        ctx.beginPath();
        ctx.arc(0, 0, this.radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#444444';
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.fillStyle = '#3d2514';
        ctx.beginPath();
        ctx.arc(0, 0, this.radius * 0.58, 0, Math.PI * 2);
        ctx.fill();

        ctx.restore();
      }
    };
    this.projectiles.push(p);
  }

  // Разрыв тарелки на 3 брызги
  spawnPlateShrapnel(x, y) {
    for (let angle of [-2.4, -1.57, -0.74]) {
      const spd = 3.8 + Math.random() * 1.5;
      this.projectiles.push({
        type: 'shrapnel',
        x: x,
        y: y - 5,
        radius: 6,
        vx: Math.cos(angle) * spd,
        vy: Math.sin(angle) * spd,
        damage: 4,
        destroyOnHit: true,
        isDead: false,
        update: function(dt, arena) {
          this.x += this.vx * 60 * dt;
          this.y += this.vy * 60 * dt;
          this.vy += 0.22;
          if (
            this.x < arena.x - 10 ||
            this.x > arena.x + arena.width + 10 ||
            this.y > arena.y + arena.height + 10
          ) {
            this.isDead = true;
          }
        },
        draw: function(ctx) {
          ctx.fillStyle = '#7a4b27';
          ctx.beginPath();
          ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
          ctx.fill();
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      });
    }
  }

  // 3. Спиральный шквал жемчужин
  spawnSpiralPearlWave(arms = 2) {
    this.spiralAngle += 0.42;
    const originX = this.arena.x + this.arena.width / 2;
    const originY = this.arena.y + 15;

    for (let arm = 0; arm < arms; arm++) {
      const a = this.spiralAngle + (arm * (Math.PI * 2 / arms));
      const spd = 3.8;
      this.projectiles.push({
        type: 'spiral_pearl',
        x: originX,
        y: originY,
        radius: 6.5,
        vx: Math.cos(a) * spd,
        vy: Math.sin(a) * spd,
        damage: 5,
        destroyOnHit: true,
        isDead: false,
        update: function(dt, arena) {
          this.x += this.vx * 60 * dt;
          this.y += this.vy * 60 * dt;
          if (
            this.x < arena.x - 20 ||
            this.x > arena.x + arena.width + 20 ||
            this.y < arena.y - 20 ||
            this.y > arena.y + arena.height + 20
          ) {
            this.isDead = true;
          }
        },
        draw: function(ctx) {
          ctx.fillStyle = '#ffffff';
          ctx.beginPath();
          ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = '#ffff33';
          ctx.beginPath();
          ctx.arc(this.x - 1.5, this.y - 1.5, 2.5, 0, Math.PI * 2);
          ctx.fill();
        }
      });
    }
  }

  // 4. Лазерная сетка
  spawnLaserGrid(isPhase3) {
    const hY = this.arena.y + 30 + Math.random() * (this.arena.height - 60);
    this.lasers.push({
      axis: 'horizontal',
      pos: hY,
      thickness: 26,
      time: 0,
      warningDuration: isPhase3 ? 0.45 : 0.65,
      activeDuration: 0.3,
      damage: 5
    });

    if (isPhase3 && Math.random() < 0.65) {
      const vX = this.arena.x + 40 + Math.random() * (this.arena.width - 80);
      this.lasers.push({
        axis: 'vertical',
        pos: vX,
        thickness: 26,
        time: 0,
        warningDuration: 0.5,
        activeDuration: 0.3,
        damage: 5
      });
    }
  }

  // 5. Самонаводящаяся субстанция
  spawnHomingMissile(player, isPhase3) {
    const originX = this.arena.x + 30 + Math.random() * (this.arena.width - 60);
    const originY = this.arena.y + 5;
    this.projectiles.push({
      type: 'homing',
      x: originX,
      y: originY,
      radius: 8.5,
      vx: 0,
      vy: 2.0,
      speed: isPhase3 ? 4.2 : 3.2,
      life: 3.2,
      damage: 5,
      destroyOnHit: true,
      isDead: false,
      update: function(dt, arena, target) {
        this.life -= dt;
        if (this.life <= 0) {
          this.isDead = true;
          return;
        }

        if (target && !target.isDead) {
          const angle = Math.atan2(target.y - this.y, target.x - this.x);
          const steerSpeed = 2.5 * dt;
          const targetVx = Math.cos(angle) * this.speed;
          const targetVy = Math.sin(angle) * this.speed;
          this.vx += (targetVx - this.vx) * steerSpeed;
          this.vy += (targetVy - this.vy) * steerSpeed;
        }

        this.x += this.vx * 60 * dt;
        this.y += this.vy * 60 * dt;

        if (
          this.x < arena.x - 15 ||
          this.x > arena.x + arena.width + 15 ||
          this.y < arena.y - 15 ||
          this.y > arena.y + arena.height + 15
        ) {
          this.isDead = true;
        }
      },
      draw: function(ctx) {
        ctx.fillStyle = '#9e5a2b';
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#ffff00';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    });
  }

  // 6. Мега-удар тарелкой
  spawnMegaPlateSlam() {
    const halfWidth = this.arena.width * 0.48;
    const isLeft = Math.random() < 0.5;
    const slamX = isLeft ? this.arena.x + 4 : this.arena.x + this.arena.width - 4 - halfWidth;

    this.telegraphs.push({
      x: slamX,
      y: this.arena.y + 4,
      w: halfWidth,
      h: this.arena.height - 8,
      time: 0,
      warningDuration: 0.65,
      slamDuration: 0.35,
      triggered: false
    });
  }

  // 7. Таймер-Бомба Тома Перла (Diaper Bomb)
  spawnDiaperBomb() {
    this.projectiles.push({
      type: 'bomb',
      x: this.arena.x + this.arena.width / 2,
      y: this.arena.y + this.arena.height / 2 - 20,
      radius: 18,
      countdown: 2.2, // секунды до взрыва
      exploded: false,
      isDead: false,
      update: function(dt) {
        this.countdown -= dt;
        if (this.countdown <= 0) {
          this.exploded = true;
        }
      },
      draw: function(ctx) {
        ctx.save();
        ctx.translate(this.x, this.y);

        // Мигающая бомба
        const flash = Math.floor(Date.now() / 120) % 2 === 0;
        ctx.fillStyle = flash ? '#ff0055' : '#ffffff';
        ctx.beginPath();
        ctx.arc(0, 0, this.radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 3;
        ctx.stroke();

        // Таймер цифра
        ctx.fillStyle = '#000000';
        ctx.font = '12px "Press Start 2P", monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(Math.ceil(this.countdown).toString(), 0, 1);

        ctx.restore();
      }
    });
  }

  // Разлёт бомбы на 12 жемчужин кругом
  explodeBomb(x, y) {
    this.shakeAmount = 10;
    const count = 12;
    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2;
      const spd = 4.0;
      this.projectiles.push({
        type: 'bomb_shard',
        x: x,
        y: y,
        radius: 6.5,
        vx: Math.cos(angle) * spd,
        vy: Math.sin(angle) * spd,
        damage: 5,
        destroyOnHit: true,
        isDead: false,
        update: function(dt, arena) {
          this.x += this.vx * 60 * dt;
          this.y += this.vy * 60 * dt;
          if (
            this.x < arena.x - 20 ||
            this.x > arena.x + arena.width + 20 ||
            this.y < arena.y - 20 ||
            this.y > arena.y + arena.height + 20
          ) {
            this.isDead = true;
          }
        },
        draw: function(ctx) {
          ctx.fillStyle = '#ffffff';
          ctx.beginPath();
          ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
          ctx.fill();
          ctx.strokeStyle = '#ff0055';
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }
      });
    }
  }

  // 8. Серповидные волны ауры Тома Перла
  spawnAuraSlash() {
    const fromLeft = Math.random() < 0.5;
    const startX = fromLeft ? this.arena.x - 30 : this.arena.x + this.arena.width + 30;
    const startY = this.arena.y + 40 + Math.random() * (this.arena.height - 80);
    const vx = (fromLeft ? 1 : -1) * 4.6;

    this.projectiles.push({
      type: 'aura_slash',
      x: startX,
      y: startY,
      width: 24,
      height: 52,
      vx: vx,
      damage: 6,
      destroyOnHit: true,
      isDead: false,
      update: function(dt, arena) {
        this.x += this.vx * 60 * dt;
        if (this.x < arena.x - 50 || this.x > arena.x + arena.width + 50) {
          this.isDead = true;
        }
      },
      draw: function(ctx) {
        ctx.save();
        ctx.translate(this.x, this.y);

        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        // Серповидный разрез
        ctx.arc(0, 0, 24, -Math.PI / 2, Math.PI / 2, !fromLeft);
        ctx.closePath();
        ctx.fill();

        ctx.strokeStyle = '#00ffff';
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.restore();
      }
    });
  }

  // 9. Каскадная лавина тарелок
  spawnPlateAvalanche(isPhase4) {
    const count = isPhase4 ? 3 : 2;
    for (let i = 0; i < count; i++) {
      this.spawnFallingPlate(isPhase4 ? 6.5 : 5.0);
    }
  }

  // 10. Квадро-бластерный перекрёстный крест
  spawnQuadBlaster() {
    // Горизонтальный по центру
    this.lasers.push({
      axis: 'horizontal',
      pos: this.arena.y + this.arena.height / 2,
      thickness: 30,
      time: 0,
      warningDuration: 0.6,
      activeDuration: 0.35,
      damage: 6
    });

    // Вертикальный со смещением
    this.lasers.push({
      axis: 'vertical',
      pos: this.arena.x + this.arena.width / 2 + (Math.random() - 0.5) * 80,
      thickness: 30,
      time: 0.2, // с небольшой задержкой для ритма
      warningDuration: 0.6,
      activeDuration: 0.35,
      damage: 6
    });
  }

  checkCollision(p, player) {
    if (player.invulnerableTimer > 0 || player.isDead) return false;

    // Undertale-каноничный компактный хитбокс сердца (внутреннее ядро 5.5px)
    const core = player.hitboxRadius || 5.5;

    if (p.type === 'hurtbox' || p.type === 'aura_slash') {
      return (
        player.x + core > p.x &&
        player.x - core < p.x + p.width &&
        player.y + core > p.y &&
        player.y - core < p.y + p.height
      );
    } else if (p.radius) {
      const dx = player.x - p.x;
      const dy = player.y - p.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      return dist < (p.radius * 0.82) + core;
    }
    return false;
  }

  draw(ctx) {
    // 0. Предметы восстановления здоровья (+HP)
    for (const hp of this.healPickups) {
      hp.draw(ctx);
    }

    // 1. Телеграфы Мега-удара
    for (const t of this.telegraphs) {
      if (t.time < t.warningDuration) {
        const flash = Math.floor(Date.now() / 90) % 2 === 0;
        ctx.fillStyle = flash ? 'rgba(255, 0, 0, 0.35)' : 'rgba(255, 100, 0, 0.2)';
        ctx.fillRect(t.x, t.y, t.w, t.h);
        ctx.strokeStyle = '#ff0000';
        ctx.lineWidth = 3;
        ctx.strokeRect(t.x, t.y, t.w, t.h);

        ctx.fillStyle = '#ffff00';
        ctx.font = '12px "Press Start 2P", monospace';
        ctx.textAlign = 'center';
        ctx.fillText('! DANGER !', t.x + t.w / 2, t.y + t.h / 2);
      } else {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
        ctx.fillRect(t.x, t.y, t.w, t.h);
        ctx.fillStyle = 'rgba(180, 50, 20, 0.7)';
        ctx.fillRect(t.x + 8, t.y + 8, t.w - 16, t.h - 16);
      }
    }

    // 2. Лазеры
    for (const laser of this.lasers) {
      if (laser.axis === 'horizontal') {
        const top = laser.pos - laser.thickness / 2;
        if (laser.time < laser.warningDuration) {
          const alpha = Math.floor(Date.now() / 80) % 2 === 0 ? 0.35 : 0.8;
          ctx.fillStyle = `rgba(255, 50, 50, ${alpha})`;
          ctx.fillRect(this.arena.x + 4, laser.pos - 2, this.arena.width - 8, 4);
          ctx.fillStyle = '#ff0000';
          ctx.font = '10px "Press Start 2P", monospace';
          ctx.textAlign = 'left';
          ctx.fillText('!', this.arena.x + 12, laser.pos + 4);
          ctx.fillText('!', this.arena.x + this.arena.width - 24, laser.pos + 4);
        } else {
          ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
          ctx.fillRect(this.arena.x + 4, top, this.arena.width - 8, laser.thickness);
          ctx.fillStyle = 'rgba(255, 20, 20, 0.75)';
          ctx.fillRect(this.arena.x + 4, top + 4, this.arena.width - 8, laser.thickness - 8);
        }
      } else {
        const left = laser.pos - laser.thickness / 2;
        if (laser.time < laser.warningDuration) {
          const alpha = Math.floor(Date.now() / 80) % 2 === 0 ? 0.35 : 0.8;
          ctx.fillStyle = `rgba(255, 50, 50, ${alpha})`;
          ctx.fillRect(laser.pos - 2, this.arena.y + 4, 4, this.arena.height - 8);
        } else {
          ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
          ctx.fillRect(left, this.arena.y + 4, laser.thickness, this.arena.height - 8);
          ctx.fillStyle = 'rgba(255, 20, 20, 0.75)';
          ctx.fillRect(left + 4, this.arena.y + 4, laser.thickness - 8, this.arena.height - 8);
        }
      }
    }

    // 3. Снаряды
    for (const p of this.projectiles) {
      p.draw(ctx);
    }
  }
}

window.AttackManager = AttackManager;
