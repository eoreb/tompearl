// audio.js - Управление аудиофайлами и синтезом звуков (Web Audio API)
class AudioManager {
  constructor() {
    this.ctx = null;
    this.isMuted = false;
    
    // Аудио элементы для треков пользователя из папки sounds/
    this.introAudio = new Audio('sounds/hi-my-name-is-tom-pearl.mp3');
    this.introAudio.preload = 'auto';

    this.battleAudio = new Audio(encodeURI('sounds/Yara Yara Ya Phonk (Slowed).mp3'));
    this.battleAudio.preload = 'auto';
    this.battleAudio.loop = true;

    this.isAudioUnlocked = false;
  }

  initContext() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
    this.isAudioUnlocked = true;
  }

  playIntro() {
    this.initContext();
    this.introAudio.currentTime = 0;
    this.introAudio.muted = this.isMuted;
    this.introAudio.volume = 1.0;
    const p1 = this.introAudio.play();
    if (p1 !== undefined) {
      p1.catch(err => console.log('Intro play blocked:', err));
    }

    // Музыка фонка включается сразу без задержки
    this.battleAudio.currentTime = 0;
    this.battleAudio.muted = this.isMuted;
    this.battleAudio.volume = 0.7;
    const p2 = this.battleAudio.play();
    if (p2 !== undefined) {
      p2.catch(err => console.log('Battle music play blocked:', err));
    }
  }

  stopIntro() {
    try {
      this.introAudio.pause();
      this.introAudio.currentTime = 0;
    } catch (e) {}
  }

  playBattle(forceRestart = false) {
    this.initContext();
    this.stopIntro();
    this.battleAudio.muted = this.isMuted;
    this.battleAudio.volume = 1.0;
    if (forceRestart || this.battleAudio.paused) {
      this.battleAudio.currentTime = 0;
      const promise = this.battleAudio.play();
      if (promise !== undefined) {
        promise.catch(err => console.log('Battle music play blocked:', err));
      }
    }
  }

  stopBattle() {
    try {
      this.battleAudio.pause();
      this.battleAudio.currentTime = 0;
    } catch (e) {}
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    this.introAudio.muted = this.isMuted;
    this.battleAudio.muted = this.isMuted;
    return this.isMuted;
  }

  // Процедурные звуковые эффекты на Web Audio API
  playTextBlip() {
    if (this.isMuted || !this.ctx) return;
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      
      osc.type = 'square';
      osc.frequency.setValueAtTime(260 + Math.random() * 40, this.ctx.currentTime);
      
      gain.gain.setValueAtTime(0.06, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.04);
      
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      
      osc.start();
      osc.stop(this.ctx.currentTime + 0.04);
    } catch (e) {}
  }

  playShootSound() {
    if (this.isMuted || !this.ctx) return;
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(800, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(150, this.ctx.currentTime + 0.12);
      
      gain.gain.setValueAtTime(0.12, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.12);
      
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      
      osc.start();
      osc.stop(this.ctx.currentTime + 0.12);
    } catch (e) {}
  }

  playBossHitSound() {
    if (this.isMuted || !this.ctx) return;
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(220, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(60, this.ctx.currentTime + 0.1);
      
      gain.gain.setValueAtTime(0.2, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.1);
      
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      
      osc.start();
      osc.stop(this.ctx.currentTime + 0.1);
    } catch (e) {}
  }

  playPlayerHurtSound() {
    if (this.isMuted || !this.ctx) return;
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      
      osc.type = 'square';
      osc.frequency.setValueAtTime(160, this.ctx.currentTime);
      osc.frequency.linearRampToValueAtTime(70, this.ctx.currentTime + 0.2);
      
      gain.gain.setValueAtTime(0.25, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.22);
      
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      
      osc.start();
      osc.stop(this.ctx.currentTime + 0.22);
    } catch (e) {}
  }

  playHeartShatterSound() {
    if (this.isMuted || !this.ctx) return;
    try {
      // Имитация треска разлетающегося сердца
      const bufferSize = this.ctx.sampleRate * 0.3;
      const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (this.ctx.sampleRate * 0.08));
      }

      const noise = this.ctx.createBufferSource();
      noise.buffer = buffer;
      const gain = this.ctx.createGain();
      gain.gain.setValueAtTime(0.3, this.ctx.currentTime);
      noise.connect(gain);
      gain.connect(this.ctx.destination);
      noise.start();
    } catch (e) {}
  }

  playVictorySound() {
    if (this.isMuted || !this.ctx) return;
    try {
      const notes = [330, 392, 493, 587, 659];
      notes.forEach((freq, i) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, this.ctx.currentTime + i * 0.1);
        gain.gain.setValueAtTime(0.15, this.ctx.currentTime + i * 0.1);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + i * 0.1 + 0.35);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(this.ctx.currentTime + i * 0.1);
        osc.stop(this.ctx.currentTime + i * 0.1 + 0.35);
      });
    } catch (e) {}
  }

  playHealSound() {
    if (this.isMuted || !this.ctx) return;
    try {
      const notes = [523.25, 659.25, 783.99, 1046.5]; // C5, E5, G5, C6
      notes.forEach((freq, i) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, this.ctx.currentTime + i * 0.05);
        gain.gain.setValueAtTime(0.12, this.ctx.currentTime + i * 0.05);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + i * 0.05 + 0.18);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(this.ctx.currentTime + i * 0.05);
        osc.stop(this.ctx.currentTime + i * 0.05 + 0.18);
      });
    } catch (e) {}
  }
}

window.audioManager = new AudioManager();
