/**
 * Web Audio API synthesizer for emergency notifications.
 * Pure native audio - zero external assets or MP3 dependencies.
 */

class AudioAlertService {
  private ctx: AudioContext | null = null
  private isMuted: boolean = false

  constructor() {
    // Lazy initialize on first interaction to comply with browser autoplay policies
  }

  private initContext() {
    if (!this.ctx && typeof window !== "undefined") {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      if (AudioCtx) {
        this.ctx = new AudioCtx()
      }
    }
  }

  public setMuted(muted: boolean) {
    this.isMuted = muted
  }

  public getMuted(): boolean {
    return this.isMuted
  }

  public toggleMute(): boolean {
    this.isMuted = !this.isMuted
    return this.isMuted
  }

  /**
   * Plays a dual-tone attention chime for active emergencies
   */
  public playEmergencyChime() {
    if (this.isMuted) return
    this.initContext()
    if (!this.ctx) return

    if (this.ctx.state === "suspended") {
      this.ctx.resume()
    }

    const now = this.ctx.currentTime

    // Tone 1: 880 Hz (A5)
    const osc1 = this.ctx.createOscillator()
    const gain1 = this.ctx.createGain()
    osc1.type = "sine"
    osc1.frequency.setValueAtTime(880, now)
    gain1.gain.setValueAtTime(0.15, now)
    gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.35)
    osc1.connect(gain1)
    gain1.connect(this.ctx.destination)
    osc1.start(now)
    osc1.stop(now + 0.35)

    // Tone 2: 1174.66 Hz (D6)
    const osc2 = this.ctx.createOscillator()
    const gain2 = this.ctx.createGain()
    osc2.type = "sine"
    osc2.frequency.setValueAtTime(1174.66, now + 0.15)
    gain2.gain.setValueAtTime(0.2, now + 0.15)
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.55)
    osc2.connect(gain2)
    gain2.connect(this.ctx.destination)
    osc2.start(now + 0.15)
    osc2.stop(now + 0.55)
  }

  /**
   * Plays a soft confirmation beep on action acknowledgment
   */
  public playAcknowledgeBeep() {
    if (this.isMuted) return
    this.initContext()
    if (!this.ctx) return

    if (this.ctx.state === "suspended") {
      this.ctx.resume()
    }

    const now = this.ctx.currentTime
    const osc = this.ctx.createOscillator()
    const gain = this.ctx.createGain()
    osc.type = "triangle"
    osc.frequency.setValueAtTime(587.33, now) // D5
    gain.gain.setValueAtTime(0.12, now)
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25)
    osc.connect(gain)
    gain.connect(this.ctx.destination)
    osc.start(now)
    osc.stop(now + 0.25)
  }
}

export const audioAlert = new AudioAlertService()
