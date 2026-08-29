import { motion } from "framer-motion"
import { Cpu, Battery, Radio } from "lucide-react"
import { useDashboard } from "@/context/DashboardContext"
import { AnimatedNumber } from "@/components/motion/animated-number"

export function HardwareFleetMonitor() {
  const { devices } = useDashboard()

  return (
    <div className="w-full rounded-2xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground tracking-tight flex items-center gap-2">
          <Cpu className="h-4 w-4 text-primary" />
          Hardware Nodes & Device Fleet
        </h3>
        <span className="text-[11px] font-medium text-accent flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
          {devices.filter((d) => d.status !== "unreachable").length}/{devices.length} Online
        </span>
      </div>

      <div className="space-y-2.5">
        {devices.map((device, i) => {
          const isSos = device.status === "sos_confirmed"
          const isOffline = device.status === "unreachable"

          return (
            <motion.div
              key={device.device_id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className={`p-3 rounded-xl border transition-all flex items-center justify-between gap-3 ${
                isSos 
                  ? "border-destructive/40 bg-destructive/5" 
                  : isOffline 
                    ? "border-border/60 bg-muted/40 opacity-75" 
                    : "border-border bg-background/80"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`h-8 w-8 rounded-lg flex items-center justify-center shrink-0 ${
                  isSos ? "bg-destructive text-white" : isOffline ? "bg-muted text-muted-foreground" : "bg-accent/15 text-accent"
                }`}>
                  <Radio className="h-4 w-4" />
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-foreground">{device.rider_name || device.device_id}</span>
                    <span className="text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.2 rounded border border-border">
                      {device.device_id}
                    </span>
                  </div>
                  <span className="text-[11px] text-muted-foreground block">
                    {device.vehicle_model || "Motorcycle Unit"} · ESP32 + MPU6050
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3 text-right">
                <div className="flex items-center gap-1 text-xs font-medium text-foreground">
                  <Battery className={`h-3.5 w-3.5 ${device.battery_pct < 20 ? "text-destructive" : "text-accent"}`} />
                  <span>
                    <AnimatedNumber value={device.battery_pct || 80} />%
                  </span>
                </div>

                <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider ${
                  isSos 
                    ? "bg-destructive text-white animate-pulse" 
                    : isOffline 
                      ? "bg-muted text-muted-foreground" 
                      : "bg-accent/15 text-accent"
                }`}>
                  {isSos ? "🚨 SOS ACTIVE" : isOffline ? "Offline" : "Healthy"}
                </span>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
