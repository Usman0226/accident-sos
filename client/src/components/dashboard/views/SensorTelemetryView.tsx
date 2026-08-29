import { useEffect, useState } from "react"
import { Zap, RotateCcw, Cpu, Database, Send, CheckCircle2, RefreshCw } from "lucide-react"
import { api, type RawSensorData } from "@/services/api"
import { useDashboard } from "@/context/DashboardContext"
import { AnimatedNumber } from "@/components/motion/animated-number"

export function SensorTelemetryView() {
  const { selectedTelemetry, devices, selectedDeviceId, setSelectedDeviceId } = useDashboard()
  const [rawSensors, setRawSensors] = useState<RawSensorData[] | string[]>([])
  const [isPosting, setIsPosting] = useState(false)
  const [postSuccess, setPostSuccess] = useState(false)

  const fetchRawSensors = async () => {
    try {
      const data = await api.getRawSensor()
      setRawSensors(data)
    } catch {
      // fallback
    }
  }

  useEffect(() => {
    fetchRawSensors()
  }, [])

  const handlePostSample = async () => {
    setIsPosting(true)
    try {
      await api.postRawSensor({
        sensor_type: "mpu6050_imu_6dof",
        readings: [
          selectedTelemetry.imu.accel_x,
          selectedTelemetry.imu.accel_y,
          selectedTelemetry.imu.accel_z,
          selectedTelemetry.imu.gyro_x,
          selectedTelemetry.imu.gyro_y,
          selectedTelemetry.imu.gyro_z,
        ],
        timestamp: Date.now(),
      })
      setPostSuccess(true)
      setTimeout(() => setPostSuccess(false), 2000)
      await fetchRawSensors()
    } catch (err) {
      console.warn("Failed to post raw sensor:", err)
    } finally {
      setIsPosting(false)
    }
  }

  const isAccident = selectedTelemetry.accident_detected
  const accelX = Math.abs(selectedTelemetry.imu.accel_x)
  const accelY = Math.abs(selectedTelemetry.imu.accel_y)
  const accelZ = Math.abs(selectedTelemetry.imu.accel_z)
  const maxForce = Math.max(accelX, accelY, accelZ, 1.0)

  return (
    <div className="w-full max-w-[1440px] mx-auto p-4 sm:p-6 space-y-5">
      {/* Header Bar with Device Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-2xl border border-border bg-card shadow-sm">
        <div>
          <h2 className="text-lg font-bold text-foreground tracking-tight font-display flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            Sensor Fusion & Telemetry Studio ({selectedTelemetry.device_id})
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Real-time MPU6050 6-DOF IMU wave processing, derivative jerk, and live stream telemetry
          </p>
        </div>

        {/* Device Switcher Pills */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-background border border-border overflow-x-auto">
          {devices.map((d) => {
            const isSelected = d.device_id === selectedDeviceId
            return (
              <button
                key={d.device_id}
                onClick={() => setSelectedDeviceId(d.device_id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
                  isSelected
                    ? "bg-primary text-white shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
              >
                <span>{d.device_id}</span>
                <span className="opacity-70 text-[10px]">({d.rider_name?.split(" ")[0]})</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Sensor Breakdown Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* Accelerometer 3-Axis Force */}
        <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground tracking-tight flex items-center gap-2">
              <Zap className="h-4 w-4 text-primary" />
              3-Axis Acceleration (MPU6050)
            </h3>
            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
              isAccident ? "text-destructive bg-destructive/15" : "text-accent bg-accent/15"
            }`}>
              {selectedTelemetry.imu.total_g.toFixed(2)}G TOTAL
            </span>
          </div>

          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-muted-foreground">X-Axis (Longitudinal)</span>
                <span className="font-mono font-bold text-foreground">
                  <AnimatedNumber value={selectedTelemetry.imu.accel_x} format={(v) => `${v.toFixed(2)}G`} />
                </span>
              </div>
              <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                <div 
                  className={`h-full rounded-full ${accelX > 4.0 ? "bg-destructive" : "bg-primary"}`} 
                  style={{ width: `${Math.min(100, (accelX / (maxForce * 1.2)) * 100)}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-muted-foreground">Y-Axis (Lateral Side Force)</span>
                <span className="font-mono font-bold text-foreground">
                  <AnimatedNumber value={selectedTelemetry.imu.accel_y} format={(v) => `${v.toFixed(2)}G`} />
                </span>
              </div>
              <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                <div 
                  className={`h-full rounded-full ${accelY > 3.0 ? "bg-amber-500" : "bg-accent"}`} 
                  style={{ width: `${Math.min(100, (accelY / (maxForce * 1.2)) * 100)}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-muted-foreground">Z-Axis (Vertical Earth Gravity)</span>
                <span className="font-mono font-bold text-foreground">
                  <AnimatedNumber value={selectedTelemetry.imu.accel_z} format={(v) => `${v.toFixed(2)}G`} />
                </span>
              </div>
              <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                <div 
                  className="h-full bg-primary rounded-full" 
                  style={{ width: `${Math.min(100, (accelZ / (maxForce * 1.2)) * 100)}%` }}
                />
              </div>
            </div>
          </div>

          <p className="text-[11px] text-muted-foreground border-t border-border pt-3">
            Resultant Vector Magnitude: <span className="font-bold text-foreground font-mono">{selectedTelemetry.imu.total_g.toFixed(2)}G</span>
            {isAccident ? " (Exceeds 4.5G threshold)" : " (Nominal safe range)"}.
          </p>
        </div>

        {/* Gyroscope Angular Velocity */}
        <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground tracking-tight flex items-center gap-2">
              <RotateCcw className="h-4 w-4 text-primary" />
              Gyro Angular Velocity (Roll & Pitch)
            </h3>
            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
              selectedTelemetry.imu.gyro_delta > 90 ? "text-destructive bg-destructive/15" : "text-accent bg-accent/15"
            }`}>
              {selectedTelemetry.imu.gyro_delta.toFixed(1)}°/s
            </span>
          </div>

          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-muted-foreground">Roll Rate (Bike Tumble)</span>
                <span className="font-mono font-bold text-foreground">
                  <AnimatedNumber value={selectedTelemetry.imu.gyro_x} format={(v) => `${v.toFixed(1)}°/s`} />
                </span>
              </div>
              <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                <div 
                  className={`h-full rounded-full ${selectedTelemetry.imu.gyro_x > 90 ? "bg-destructive" : "bg-primary"}`} 
                  style={{ width: `${Math.min(100, (Math.abs(selectedTelemetry.imu.gyro_x) / 160) * 100)}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-muted-foreground">Pitch Rate</span>
                <span className="font-mono font-bold text-foreground">
                  <AnimatedNumber value={selectedTelemetry.imu.gyro_y} format={(v) => `${v.toFixed(1)}°/s`} />
                </span>
              </div>
              <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                <div 
                  className="h-full bg-primary rounded-full" 
                  style={{ width: `${Math.min(100, (Math.abs(selectedTelemetry.imu.gyro_y) / 100) * 100)}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-muted-foreground">Yaw Rate (Fishtail / Spin)</span>
                <span className="font-mono font-bold text-foreground">
                  <AnimatedNumber value={selectedTelemetry.imu.gyro_z} format={(v) => `${v.toFixed(1)}°/s`} />
                </span>
              </div>
              <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                <div 
                  className="h-full bg-accent rounded-full" 
                  style={{ width: `${Math.min(100, (Math.abs(selectedTelemetry.imu.gyro_z) / 100) * 100)}%` }}
                />
              </div>
            </div>
          </div>

          <p className="text-[11px] text-muted-foreground border-t border-border pt-3">
            Vehicle Lean Angle: <span className="font-bold text-foreground font-mono">{selectedTelemetry.imu.lean_angle.toFixed(1)}°</span>.
          </p>
        </div>

        {/* Impact Jerk & Immobility */}
        <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground tracking-tight flex items-center gap-2">
              <Cpu className="h-4 w-4 text-accent" />
              Impact Jerk & Motion Sensor
            </h3>
            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
              isAccident ? "text-destructive bg-destructive/15" : "text-accent bg-accent/15"
            }`}>
              {isAccident ? "CRASH VERIFIED" : "NORMAL"}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-center">
            <div className="p-3 rounded-xl bg-background/80 border border-border">
              <span className="text-[10px] text-muted-foreground block">Peak Jerk (dG/dt)</span>
              <span className={`text-xl font-bold font-mono ${selectedTelemetry.imu.jerk > 20 ? "text-destructive" : "text-foreground"}`}>
                <AnimatedNumber value={selectedTelemetry.imu.jerk} format={(v) => v.toFixed(1)} />
              </span>
              <span className="text-[10px] text-muted-foreground block">G/s</span>
            </div>

            <div className="p-3 rounded-xl bg-background/80 border border-border">
              <span className="text-[10px] text-muted-foreground block">Post-Impact Motion</span>
              <span className={`text-xl font-bold font-mono ${isAccident && selectedTelemetry.imu.post_motion < 0.1 ? "text-destructive" : "text-foreground"}`}>
                <AnimatedNumber value={selectedTelemetry.imu.post_motion} format={(v) => v.toFixed(2)} />
              </span>
              <span className="text-[10px] text-muted-foreground block">m/s²</span>
            </div>
          </div>

          <div className={`p-2.5 rounded-xl text-[11px] font-medium border ${
            isAccident 
              ? "bg-destructive/10 text-destructive border-destructive/20" 
              : "bg-accent/10 text-accent border-accent/20"
          }`}>
            {isAccident 
              ? "⚠️ Rider immobility detected. Emergency SOS triggered." 
              : "✓ Rider active movement confirmed. System nominal."}
          </div>
        </div>
      </div>

      {/* Raw Sensor API Inspector (/api/sensor) */}
      <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold text-foreground tracking-tight">
              Raw Sensor API Stream (<code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">/api/sensor</code>)
            </h3>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePostSample}
              disabled={isPosting}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-primary hover:bg-primary/90 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              {postSuccess ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Send className="h-3.5 w-3.5" />}
              <span>{postSuccess ? "Packet Sent!" : "Transmit Sample Packet (POST)"}</span>
            </button>

            <button
              onClick={fetchRawSensors}
              className="p-1.5 rounded-xl bg-background hover:bg-muted text-muted-foreground hover:text-foreground border border-border transition-colors"
              title="Refresh Raw Sensor Stream"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-background/90 border border-border font-mono text-xs max-h-48 overflow-y-auto">
          {Array.isArray(rawSensors) && rawSensors.length > 0 ? (
            <pre className="text-muted-foreground text-[11px] whitespace-pre-wrap">
              {JSON.stringify(rawSensors, null, 2)}
            </pre>
          ) : (
            <span className="text-muted-foreground text-xs italic">
              No raw sensor packets received yet. Tap "Transmit Sample Packet" to append data to /api/sensor.
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
