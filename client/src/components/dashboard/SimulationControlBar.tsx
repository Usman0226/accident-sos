import { useDashboard } from "@/context/DashboardContext"
import { Play, RotateCcw, AlertTriangle } from "lucide-react"

export function SimulationControlBar() {
  const { triggerSimulation, isBackendConnected } = useDashboard()

  return (
    <div className="w-full flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 rounded-xl border border-border/80 bg-muted/40 text-xs mb-5">
      <div className="flex items-center gap-2">
        <span className="font-semibold text-foreground uppercase tracking-wider text-[10px] bg-background px-2 py-0.5 rounded border border-border">
          Demo Simulator
        </span>
        <span className="text-muted-foreground hidden sm:inline">
          Test live hardware telemetry & SOS responder state machine:
        </span>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => triggerSimulation("severe_crash")}
          className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-destructive/15 hover:bg-destructive/25 text-destructive font-medium border border-destructive/30 transition-colors"
        >
          <AlertTriangle className="h-3.5 w-3.5" />
          <span>Simulate 8.7G Crash</span>
        </button>

        <button
          onClick={() => triggerSimulation("moderate_impact")}
          className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-700 dark:text-amber-400 font-medium border border-amber-500/30 transition-colors"
        >
          <Play className="h-3.5 w-3.5" />
          <span>Simulate 4.8G Impact</span>
        </button>

        <button
          onClick={() => triggerSimulation("clear")}
          className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-background hover:bg-muted text-muted-foreground hover:text-foreground font-medium border border-border transition-colors"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          <span>Reset All Clear</span>
        </button>

        <div className="flex items-center gap-1 text-[11px] text-muted-foreground pl-2 border-l border-border font-mono">
          <span className={`h-2 w-2 rounded-full ${isBackendConnected ? "bg-accent" : "bg-amber-500"}`} />
          <span>{isBackendConnected ? "FastAPI Connected" : "Local Mock Sync"}</span>
        </div>
      </div>
    </div>
  )
}
