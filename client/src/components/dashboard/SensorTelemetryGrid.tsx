import { motion } from "framer-motion"
import { Activity, Gauge, RotateCcw, Zap, Compass, UserX } from "lucide-react"
import { useDashboard } from "@/context/DashboardContext"
import { AnimatedNumber } from "@/components/motion/animated-number"

export function SensorTelemetryGrid() {
  const { selectedTelemetry, activeAlert } = useDashboard()

  const isSos = activeAlert?.device_id === selectedTelemetry.device_id || selectedTelemetry.accident_detected

  const telemetry = {
    peak_g: selectedTelemetry.imu.total_g,
    jerk_gs: selectedTelemetry.imu.jerk,
    gyro_deg: selectedTelemetry.imu.gyro_delta,
    orientation_delta: selectedTelemetry.imu.lean_angle,
    post_motion: selectedTelemetry.imu.post_motion,
    speed_kmph: selectedTelemetry.speed_kmph,
  }

  const cards = [
    {
      title: "Peak Impact Force",
      value: telemetry.peak_g,
      unit: "G",
      decimals: 2,
      threshold: isSos ? "Threshold > 4.5G Exceeded" : "Nominal 1.0G Earth Gravity",
      status: telemetry.peak_g > 4.5 ? "critical" : "normal",
      icon: Zap,
      desc: "Measured via MPU6050 3-axis accelerometer",
    },
    {
      title: "Impact Jerk (dG/dt)",
      value: telemetry.jerk_gs,
      unit: "G/s",
      decimals: 1,
      threshold: isSos ? "Shockwave spike detected" : "Smooth motion rate",
      status: telemetry.jerk_gs > 20 ? "critical" : "normal",
      icon: Activity,
      desc: "Rate of change in acceleration on contact",
    },
    {
      title: "Angular Gyro Velocity",
      value: telemetry.gyro_deg,
      unit: "°/s",
      decimals: 1,
      threshold: isSos ? "Spin threshold > 90°/s" : "Normal steering velocity",
      status: telemetry.gyro_deg > 90 ? "critical" : "normal",
      icon: RotateCcw,
      desc: "Rapid tumble and rollover detection",
    },
    {
      title: "Vehicle Lean / Tilt",
      value: telemetry.orientation_delta,
      unit: "°",
      decimals: 1,
      threshold: telemetry.orientation_delta > 50 ? "Tipped on side (>55°)" : "Normal lean angle",
      status: telemetry.orientation_delta > 50 ? "critical" : "normal",
      icon: Compass,
      desc: "Quaternion tilt relative to normal horizon",
    },
    {
      title: "Post-Impact Motion",
      value: telemetry.post_motion,
      unit: "m/s²",
      decimals: 2,
      threshold: isSos ? "Rider motionless" : "Active movement detected",
      status: isSos && telemetry.post_motion < 0.1 ? "critical" : "normal",
      icon: UserX,
      desc: "Motion level measured by accelerometer",
    },
    {
      title: "GPS Doppler Speed",
      value: telemetry.speed_kmph,
      unit: "km/h",
      decimals: 1,
      threshold: "Real-time velocity",
      status: "normal",
      icon: Gauge,
      desc: "Speed recorded by Neo-6M GPS module",
    },
  ]

  return (
    <div className="w-full rounded-2xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-foreground tracking-tight flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            Sensor Fusion & Telemetry ({selectedTelemetry.device_id})
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Real-time MPU6050 IMU + GPS telemetry stream processed by ESP32 edge classification model
          </p>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border">
          100 Hz Sampling
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {cards.map((card, i) => {
          const Icon = card.icon
          const isCrit = card.status === "critical"
          return (
            <motion.div
              key={card.title}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04, duration: 0.25 }}
              className={`p-3.5 rounded-xl border transition-all ${
                isCrit 
                  ? "border-destructive/30 bg-destructive/5 dark:bg-destructive/10" 
                  : "border-border/70 bg-background/60"
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] font-medium text-muted-foreground leading-tight">{card.title}</span>
                <Icon className={`h-3.5 w-3.5 ${isCrit ? "text-destructive" : "text-primary"}`} />
              </div>

              <div className="flex items-baseline gap-1 my-1">
                <span className={`text-xl sm:text-2xl font-bold font-mono tracking-tight ${
                  isCrit ? "text-destructive" : "text-foreground"
                }`}>
                  <AnimatedNumber 
                    value={card.value} 
                    format={(v) => v.toFixed(card.decimals)}
                  />
                </span>
                <span className="text-xs text-muted-foreground font-sans font-medium">{card.unit}</span>
              </div>

              <div className="flex items-center justify-between text-[10px] mt-1 pt-1.5 border-t border-border/50">
                <span className={isCrit ? "text-destructive font-medium" : "text-muted-foreground"}>
                  {card.threshold}
                </span>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
