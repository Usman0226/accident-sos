import { motion } from "framer-motion"
import { CheckCircle2, Clock, Radio } from "lucide-react"
import { useDashboard } from "@/context/DashboardContext"

export function IncidentLifecycleTimeline() {
  const { activeAlert } = useDashboard()

  const timeline = activeAlert?.timeline || [
    { time: "T+0.0s", title: "Impact Detected", description: "8.7G peak shockwave recorded on MPU6050", status: "done" },
    { time: "T+0.8s", title: "Sensor Fusion Analysis", description: "Crash confirmed with 94% confidence rating", status: "done" },
    { time: "T+2.0s", title: "SOS Broadcast Fired", description: "Emergency alert sent via GSM SIM800L & Cloud API", status: "done" },
    { time: "T+1.5m", title: "Contact Dashboard Live", description: "Waiting for emergency contact response", status: "current" },
  ]

  return (
    <div className="w-full rounded-2xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground tracking-tight flex items-center gap-2">
          <Clock className="h-4 w-4 text-primary" />
          Event Lifecycle & State Machine
        </h3>
        <span className="text-[11px] font-medium text-muted-foreground">
          {activeAlert ? "Active Progression" : "Standby"}
        </span>
      </div>

      <div className="space-y-3 relative before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[2px] before:bg-border">
        {timeline.map((step, i) => {
          const isDone = step.status === "done"
          const isCurrent = step.status === "current"

          return (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05, duration: 0.2 }}
              className="relative flex items-start gap-3 pl-1"
            >
              <div className={`relative z-10 h-5 w-5 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                isDone 
                  ? "bg-accent text-white" 
                  : isCurrent 
                    ? "bg-primary text-white animate-pulse ring-4 ring-primary/20" 
                    : "bg-muted text-muted-foreground border border-border"
              }`}>
                {isDone ? (
                  <CheckCircle2 className="h-3 w-3 stroke-[3]" />
                ) : isCurrent ? (
                  <Radio className="h-3 w-3 animate-spin" />
                ) : (
                  <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-baseline justify-between gap-2">
                  <span className={`text-xs font-semibold ${isCurrent ? "text-primary" : "text-foreground"}`}>
                    {step.title}
                  </span>
                  <span className="font-mono text-[10px] text-muted-foreground shrink-0">{step.time}</span>
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed mt-0.5">{step.description}</p>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
