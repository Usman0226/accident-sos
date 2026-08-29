import { useState, type ReactNode } from "react"
import { PhoneCall, HeartPulse, Volume2, VolumeX } from "lucide-react"
import { ThemeToggle } from "@/components/motion/theme-toggle"
import { useDashboard } from "@/context/DashboardContext"
import { audioAlert } from "@/services/audioAlert"

interface TopNavbarProps {
  trigger?: ReactNode
}

export function TopNavbar({ trigger }: TopNavbarProps) {
  const { activeAlert, isBackendConnected } = useDashboard()
  const [isMuted, setIsMuted] = useState(audioAlert.getMuted())

  const toggleSound = () => {
    const next = audioAlert.toggleMute()
    setIsMuted(next)
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 w-full items-center justify-between border-b border-border bg-background/95 backdrop-blur-sm px-4 sm:px-6">
      <div className="flex items-center gap-3">
        {/* Mobile menu trigger */}
        {trigger}

        {/* System Status */}
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${activeAlert ? "bg-destructive" : "bg-accent"}`}></span>
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${activeAlert ? "bg-destructive" : "bg-accent"}`}></span>
          </span>
          <span className="text-xs font-semibold text-foreground tracking-tight">
            {activeAlert ? "EMERGENCY ACTIVE" : "SYSTEM OPERATIONAL"}
          </span>
          <span className="text-muted-foreground text-xs hidden md:inline">
            · {isBackendConnected ? "FastAPI Live Polling (2.5s)" : "Standalone Simulation"}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        {/* Audio Siren Toggle */}
        <button
          onClick={toggleSound}
          title={isMuted ? "Unmute Emergency Chimes" : "Mute Emergency Chimes"}
          className="p-2 rounded-xl bg-muted/60 hover:bg-muted text-muted-foreground hover:text-foreground border border-border transition-colors text-xs flex items-center gap-1"
        >
          {isMuted ? <VolumeX className="h-4 w-4 text-muted-foreground" /> : <Volume2 className="h-4 w-4 text-accent animate-pulse" />}
        </button>

        {/* Quick Emergency 112 Dial Helper */}
        <a
          href="tel:112"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-destructive/15 text-destructive hover:bg-destructive/25 text-xs font-bold border border-destructive/30 transition-colors"
        >
          <PhoneCall className="h-3.5 w-3.5" />
          <span>Dial 112</span>
        </a>

        {/* Registered Contact Identity */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-muted/60 border border-border text-xs">
          <HeartPulse className="h-3.5 w-3.5 text-primary" />
          <span className="text-muted-foreground">Emergency Contact:</span>
          <span className="font-semibold text-foreground">Family & Guardians</span>
        </div>

        {/* Theme Toggle (beUI) */}
        <ThemeToggle />
      </div>
    </header>
  )
}
