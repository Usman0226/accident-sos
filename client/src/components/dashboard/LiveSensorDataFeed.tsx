import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { 
  Activity, 
  Gauge, 
  Zap, 
  Compass, 
  RotateCcw, 
  Battery, 
  MapPin, 
  Code2, 
  Copy, 
  CheckCircle2, 
  Radio
} from "lucide-react"
import { useDashboard } from "@/context/DashboardContext"
import { AnimatedNumber } from "@/components/motion/animated-number"

export function LiveSensorDataFeed() {
  const { devices, selectedDeviceId, setSelectedDeviceId, selectedTelemetry } = useDashboard()
  const [showJsonInspector, setShowJsonInspector] = useState(true)
  const [copied, setCopied] = useState(false)

  const copyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(selectedTelemetry.rawContractJson, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const isAccident = selectedTelemetry.accident_detected

  return (
    <div className="w-full rounded-2xl border border-border bg-card p-5 shadow-sm space-y-5">
      {/* Header & Fleet Device Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
        <div>
          <h3 className="text-sm font-bold text-foreground tracking-tight flex items-center gap-2 font-display text-base">
            <Activity className="h-4 w-4 text-primary" />
            Live Embedded Sensor Stream (Continuous Telemetry)
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Real-time telemetry ingested from ESP32 + MPU6050 6-DOF IMU + Neo-6M GPS modules
          </p>
        </div>

        {/* Device Switcher Pills */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-background border border-border overflow-x-auto">
          {devices.map((d) => {
            const isSelected = d.device_id === selectedDeviceId
            const isSos = d.status === "sos_confirmed"

            return (
              <button
                key={d.device_id}
                onClick={() => setSelectedDeviceId(d.device_id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
                  isSelected
                    ? isSos
                      ? "bg-destructive text-white shadow-sm"
                      : "bg-primary text-white shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
              >
                <span className={`h-2 w-2 rounded-full ${isSos ? "bg-white animate-pulse" : isSelected ? "bg-white" : "bg-accent"}`} />
                <span>{d.device_id}</span>
                <span className="opacity-70 text-[10px]">({d.rider_name?.split(" ")[0]})</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Active Node Live Status Strip */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-background/80 border border-border text-xs">
        <div className="flex items-center gap-3">
          <div className={`h-8 w-8 rounded-lg flex items-center justify-center font-bold text-xs ${
            isAccident ? "bg-destructive text-white" : "bg-accent/15 text-accent"
          }`}>
            {selectedTelemetry.device_id.replace("VEH_", "")}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-foreground">{selectedTelemetry.rider_name}</span>
              <span className="text-muted-foreground">· {selectedTelemetry.vehicle_model}</span>
            </div>
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground mt-0.5">
              <MapPin className="h-3 w-3 text-primary" />
              <span>{selectedTelemetry.location.address}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
            isAccident 
              ? "bg-destructive text-white animate-pulse" 
              : selectedTelemetry.status === "UNREACHABLE"
                ? "bg-muted text-muted-foreground"
                : "bg-accent/15 text-accent"
          }`}>
            {isAccident ? "🚨 SOS CRASH CONFIRMED" : selectedTelemetry.status === "UNREACHABLE" ? "⚠️ Offline" : "✓ Normal Safe Riding"}
          </span>

          <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border flex items-center gap-1">
            <Radio className="h-3 w-3 text-accent animate-pulse" />
            100 Hz Stream
          </span>
        </div>
      </div>

      {/* 6-Metric Live Sensor Readout Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* 1. Live Speedometer */}
        <div className="p-3 rounded-xl bg-background/70 border border-border space-y-1">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>Live Speed</span>
            <Gauge className="h-3.5 w-3.5 text-primary" />
          </div>
          <div className="flex items-baseline gap-1 my-0.5">
            <span className="text-xl font-bold font-mono text-foreground">
              <AnimatedNumber value={selectedTelemetry.speed_kmph} format={(v) => v.toFixed(1)} />
            </span>
            <span className="text-[10px] text-muted-foreground font-medium">km/h</span>
          </div>
          <span className="text-[10px] text-muted-foreground block">GPS Doppler Speed</span>
        </div>

        {/* 2. Total Acceleration Magnitude */}
        <div className={`p-3 rounded-xl border space-y-1 ${
          isAccident ? "bg-destructive/10 border-destructive/30" : "bg-background/70 border-border"
        }`}>
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>Resultant Force</span>
            <Zap className={`h-3.5 w-3.5 ${isAccident ? "text-destructive" : "text-primary"}`} />
          </div>
          <div className="flex items-baseline gap-1 my-0.5">
            <span className={`text-xl font-bold font-mono ${isAccident ? "text-destructive" : "text-foreground"}`}>
              <AnimatedNumber value={selectedTelemetry.imu.total_g} format={(v) => v.toFixed(2)} />
            </span>
            <span className="text-[10px] text-muted-foreground font-medium">G</span>
          </div>
          <span className="text-[10px] text-muted-foreground block">
            {isAccident ? "Threshold > 4.5G" : "1.0G Earth Gravity"}
          </span>
        </div>

        {/* 3. Lean / Roll Angle */}
        <div className="p-3 rounded-xl bg-background/70 border border-border space-y-1">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>Lean Angle</span>
            <Compass className="h-3.5 w-3.5 text-primary" />
          </div>
          <div className="flex items-baseline gap-1 my-0.5">
            <span className={`text-xl font-bold font-mono ${selectedTelemetry.imu.lean_angle > 50 ? "text-destructive" : "text-foreground"}`}>
              <AnimatedNumber value={selectedTelemetry.imu.lean_angle} format={(v) => v.toFixed(1)} />
            </span>
            <span className="text-[10px] text-muted-foreground font-medium">°</span>
          </div>
          <span className="text-[10px] text-muted-foreground block">
            {selectedTelemetry.imu.lean_angle > 50 ? "Rollover (>55°)" : "Cornering Lean"}
          </span>
        </div>

        {/* 4. Gyro Tumble Velocity */}
        <div className="p-3 rounded-xl bg-background/70 border border-border space-y-1">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>Gyro Angular</span>
            <RotateCcw className="h-3.5 w-3.5 text-primary" />
          </div>
          <div className="flex items-baseline gap-1 my-0.5">
            <span className="text-xl font-bold font-mono text-foreground">
              <AnimatedNumber value={selectedTelemetry.imu.gyro_delta} format={(v) => v.toFixed(1)} />
            </span>
            <span className="text-[10px] text-muted-foreground font-medium">°/s</span>
          </div>
          <span className="text-[10px] text-muted-foreground block">Tumble Rate</span>
        </div>

        {/* 5. GPS Satellite Lock */}
        <div className="p-3 rounded-xl bg-background/70 border border-border space-y-1">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>GPS Satellites</span>
            <Radio className="h-3.5 w-3.5 text-accent" />
          </div>
          <div className="flex items-baseline gap-1 my-0.5">
            <span className="text-xl font-bold font-mono text-foreground">
              <AnimatedNumber value={selectedTelemetry.location.satellite_count} />
            </span>
            <span className="text-[10px] text-muted-foreground font-medium">Sats</span>
          </div>
          <span className="text-[10px] text-accent font-medium block">
            {selectedTelemetry.location.gps_fix ? "3D RTK Fix" : "Approximate"}
          </span>
        </div>

        {/* 6. Battery Subsystem */}
        <div className="p-3 rounded-xl bg-background/70 border border-border space-y-1">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>Battery Level</span>
            <Battery className="h-3.5 w-3.5 text-accent" />
          </div>
          <div className="flex items-baseline gap-1 my-0.5">
            <span className={`text-xl font-bold font-mono ${selectedTelemetry.battery_pct < 20 ? "text-destructive" : "text-foreground"}`}>
              <AnimatedNumber value={selectedTelemetry.battery_pct} />
            </span>
            <span className="text-[10px] text-muted-foreground font-medium">%</span>
          </div>
          <span className="text-[10px] text-muted-foreground block">3.7V LiPo</span>
        </div>
      </div>

      {/* 3-Axis Real-Time IMU Vectors Display */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
        <div className="p-3 rounded-xl bg-background/60 border border-border flex items-center justify-between">
          <div className="space-y-0.5">
            <span className="text-[11px] font-semibold text-foreground">X-Axis (Longitudinal Acceleration)</span>
            <span className="text-[10px] text-muted-foreground block">Braking & Forward Impact Shock</span>
          </div>
          <span className="font-mono text-sm font-bold text-primary">
            {selectedTelemetry.imu.accel_x > 0 ? `+${selectedTelemetry.imu.accel_x.toFixed(2)}` : selectedTelemetry.imu.accel_x.toFixed(2)} G
          </span>
        </div>

        <div className="p-3 rounded-xl bg-background/60 border border-border flex items-center justify-between">
          <div className="space-y-0.5">
            <span className="text-[11px] font-semibold text-foreground">Y-Axis (Lateral Force)</span>
            <span className="text-[10px] text-muted-foreground block">Side Slip & Centripetal Turn</span>
          </div>
          <span className="font-mono text-sm font-bold text-accent">
            {selectedTelemetry.imu.accel_y > 0 ? `+${selectedTelemetry.imu.accel_y.toFixed(2)}` : selectedTelemetry.imu.accel_y.toFixed(2)} G
          </span>
        </div>

        <div className="p-3 rounded-xl bg-background/60 border border-border flex items-center justify-between">
          <div className="space-y-0.5">
            <span className="text-[11px] font-semibold text-foreground">Z-Axis (Vertical Earth Gravity)</span>
            <span className="text-[10px] text-muted-foreground block">Gravity Reference (1.0G Normal)</span>
          </div>
          <span className="font-mono text-sm font-bold text-foreground">
            {selectedTelemetry.imu.accel_z > 0 ? `+${selectedTelemetry.imu.accel_z.toFixed(2)}` : selectedTelemetry.imu.accel_z.toFixed(2)} G
          </span>
        </div>
      </div>

      {/* Raw JSON Contract Inspector per PRD Section 5.1 */}
      <div className="border-t border-border pt-4">
        <div className="flex items-center justify-between mb-2">
          <button
            onClick={() => setShowJsonInspector(!showJsonInspector)}
            className="flex items-center gap-1.5 text-xs font-semibold text-foreground hover:text-primary transition-colors"
          >
            <Code2 className="h-4 w-4 text-primary" />
            <span>Backend Data Contract JSON (`PRD Section 5.1 & API Schema`)</span>
            <span className="text-[10px] font-normal text-muted-foreground">({showJsonInspector ? "Click to Collapse" : "Click to View Raw JSON"})</span>
          </button>

          <button
            onClick={copyJson}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-background hover:bg-muted text-[11px] font-medium text-muted-foreground hover:text-foreground border border-border transition-colors shadow-xs"
          >
            {copied ? <CheckCircle2 className="h-3 w-3 text-accent" /> : <Copy className="h-3 w-3" />}
            <span>{copied ? "JSON Copied!" : "Copy Payload"}</span>
          </button>
        </div>

        <AnimatePresence>
          {showJsonInspector && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <pre className="p-3.5 rounded-xl bg-background border border-border font-mono text-[11px] text-foreground leading-relaxed overflow-x-auto max-h-56">
                {JSON.stringify(selectedTelemetry.rawContractJson, null, 2)}
              </pre>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
