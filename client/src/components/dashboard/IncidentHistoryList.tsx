import { motion } from "framer-motion"
import { History, CheckCircle2, ShieldAlert, Radio, BellRing } from "lucide-react"
import { useDashboard } from "@/context/DashboardContext"

export function IncidentHistoryList() {
  const { events } = useDashboard()

  const formatTimestamp = (ts: number) => {
    if (!ts) return "Just now"
    const d = new Date(ts)
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
  }

  return (
    <div className="w-full rounded-2xl border border-border bg-card p-5 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground tracking-tight flex items-center gap-2">
          <History className="h-4 w-4 text-primary" />
          Live Event Audit Log (Database Stream)
        </h3>
        <span className="text-[11px] text-muted-foreground font-mono">
          {events.length} Stored Events
        </span>
      </div>

      <div className="space-y-2 max-h-72 overflow-y-auto">
        {events.length === 0 ? (
          <div className="text-center py-6 text-xs text-muted-foreground italic">
            No events recorded in the database yet.
          </div>
        ) : (
          events.slice(0, 5).map((evt, i) => {
            const payload = (evt.payload || {}) as Record<string, any>
            const isImpact = evt.type === "impact"
            const isSos = evt.type === "sos_dispatch"
            const isAck = evt.type === "alert_acknowledged"

            return (
              <motion.div
                key={evt.id}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                className="p-3 rounded-xl border border-border bg-background/80 flex items-center justify-between gap-3 text-xs"
              >
                <div className="flex items-start gap-3">
                  <div className={`h-7 w-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                    isImpact 
                      ? "bg-destructive/15 text-destructive" 
                      : isSos 
                        ? "bg-amber-500/15 text-amber-500"
                        : isAck 
                          ? "bg-accent/15 text-accent"
                          : "bg-muted text-muted-foreground"
                  }`}>
                    {isImpact ? (
                      <ShieldAlert className="h-3.5 w-3.5" />
                    ) : isSos ? (
                      <BellRing className="h-3.5 w-3.5" />
                    ) : isAck ? (
                      <CheckCircle2 className="h-3.5 w-3.5" />
                    ) : (
                      <Radio className="h-3.5 w-3.5" />
                    )}
                  </div>

                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-foreground">{evt.device_id}</span>
                      <span className="text-[10px] font-mono bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
                        EVT-{evt.id}
                      </span>
                      <span className="text-[11px] font-medium text-foreground uppercase tracking-wider">
                        · {evt.type.replace("_", " ")}
                      </span>
                    </div>

                    <div className="text-[11px] text-muted-foreground mt-0.5 font-mono">
                      {isImpact ? (
                        <span>Impact: {payload.impact_g || 0}G · Gyro: {payload.gyro_delta || 0}°/s</span>
                      ) : isSos ? (
                        <span>Dispatched via {payload.method || "SMS"} · Attempt {payload.attempt || 1}</span>
                      ) : isAck ? (
                        <span>Acknowledged by {payload.actor || "human_operator"}</span>
                      ) : (
                        <span>Heartbeat · Batt: {payload.battery_pct || 0}% · Speed: {payload.speed_kmph || 0} km/h</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className="font-mono text-[10px] text-muted-foreground block">
                    {formatTimestamp(evt.timestamp)}
                  </span>
                </div>
              </motion.div>
            )
          })
        )}
      </div>
    </div>
  )
}
