import { useState } from "react"
import { motion } from "framer-motion"
import { Cpu, Battery, Radio, Send, CheckCircle2, Clock, AlertTriangle, WifiOff, Activity } from "lucide-react"
import { useDashboard } from "@/context/DashboardContext"
import { api, type SensorDataPayload } from "@/services/api"
import { AnimatedNumber } from "@/components/motion/animated-number"

export function FleetView() {
  const { devices } = useDashboard()
  const [sendingHeartbeat, setSendingHeartbeat] = useState(false)
  const [successId, setSuccessId] = useState<string | null>(null)

  const handleSendHeartbeat = async (deviceId: string) => {
    setSendingHeartbeat(true)
    try {
      const payload: SensorDataPayload = {
        device_id: deviceId,
        sos_type: "NONE",
        timestamp: Date.now(),
        accel_x: 0.1, accel_y: 0.1, accel_z: 9.8,
        gyro_x: 0.0, gyro_y: 0.0, gyro_z: 0.0,
        impact_g: 0.0, vibration: false,
        temperature: 25.0, humidity: 50.0,
        gps_lat: 28.6139,
        gps_lon: 77.2090,
        gps_fix: true,
        gps_speed_kmph: 0.0,
        battery_pct: 92,
      }
      await api.postSos(payload)
      setSuccessId(deviceId)
      setTimeout(() => setSuccessId(null), 2500)
    } catch (err) {
      console.warn("Heartbeat error:", err)
    } finally {
      setSendingHeartbeat(false)
    }
  }

  return (
    <div className="w-full max-w-[1440px] mx-auto p-4 sm:p-6 space-y-5">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-2xl border border-border bg-card shadow-sm">
        <div>
          <h2 className="text-lg font-bold text-foreground tracking-tight font-display flex items-center gap-2">
            <Cpu className="h-5 w-5 text-primary" />
            ESP32 Hardware Fleet & Node Diagnostics
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Fleet health monitoring, SIM800L GSM connectivity, battery health, and heartbeat telemetry
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="px-3 py-1 rounded-full bg-accent/15 text-accent font-semibold flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
            {devices.filter((d) => d.status !== "unreachable").length} of {devices.length} Nodes Active
          </span>
        </div>
      </div>

      {/* Fleet Node Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {devices.map((device, i) => {
          const isSos = device.status === "sos_confirmed"
          const isOffline = device.status === "unreachable"

          return (
            <motion.div
              key={device.device_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className={`p-5 rounded-2xl border bg-card shadow-sm transition-all space-y-4 ${
                isSos 
                  ? "border-destructive/40 bg-gradient-to-b from-destructive/10 via-card to-card" 
                  : isOffline 
                    ? "border-border/60 opacity-80" 
                    : "border-border"
              }`}
            >
              {/* Card Header */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-3">
                  <div className={`h-10 w-10 rounded-xl flex items-center justify-center shrink-0 ${
                    isSos ? "bg-destructive text-white" : isOffline ? "bg-muted text-muted-foreground" : "bg-accent/15 text-accent"
                  }`}>
                    <Radio className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-foreground">{device.rider_name || device.device_id}</h3>
                    <span className="text-[11px] font-mono text-muted-foreground">{device.device_id}</span>
                  </div>
                </div>

                <span className={`px-2.5 py-0.5 flex items-center gap-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                  isSos 
                    ? "bg-destructive text-white animate-pulse" 
                    : isOffline 
                      ? "bg-muted text-muted-foreground" 
                      : "bg-accent/15 text-accent"
                }`}>
                  {isSos ? <><AlertTriangle className="h-3.5 w-3.5" /> SOS ACTIVE</> : isOffline ? <><WifiOff className="h-3.5 w-3.5" /> Offline</> : <><Activity className="h-3.5 w-3.5" /> Healthy</>}
                </span>
              </div>

              {/* Hardware Specs Breakdown */}
              <div className="p-3 rounded-xl bg-background/80 border border-border space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Vehicle:</span>
                  <span className="font-semibold text-foreground">{device.vehicle_model || "Motorcycle Unit"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Embedded MCU:</span>
                  <span className="font-mono text-foreground">ESP32-WROOM-32</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Sensors:</span>
                  <span className="font-mono text-foreground">MPU6050 + Neo-6M GPS</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Modem:</span>
                  <span className="font-mono text-foreground">SIM800L GPRS/SMS</span>
                </div>
              </div>

              {/* Telemetry Readouts */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded-xl bg-background/60 border border-border">
                  <div className="flex items-center gap-1 text-muted-foreground text-[10px] mb-1">
                    <Battery className="h-3 w-3" />
                    <span>Battery Level</span>
                  </div>
                  <span className={`font-mono text-sm font-bold ${device.battery_pct < 20 ? "text-destructive" : "text-foreground"}`}>
                    <AnimatedNumber value={device.battery_pct || 85} />%
                  </span>
                </div>

                <div className="p-2.5 rounded-xl bg-background/60 border border-border">
                  <div className="flex items-center gap-1 text-muted-foreground text-[10px] mb-1">
                    <Clock className="h-3 w-3" />
                    <span>Last Heartbeat</span>
                  </div>
                  <span className="font-mono text-xs font-semibold text-foreground">
                    {isOffline ? ">10m ago" : "5s ago"}
                  </span>
                </div>
              </div>

              {/* Heartbeat Action Button */}
              <button
                onClick={() => handleSendHeartbeat(device.device_id)}
                disabled={sendingHeartbeat}
                className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-secondary hover:bg-secondary/80 text-foreground font-semibold text-xs border border-border transition-colors disabled:opacity-50"
              >
                {successId === device.device_id ? (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5 text-accent" />
                    <span>Heartbeat Acknowledged (200 OK)</span>
                  </>
                ) : (
                  <>
                    <Send className="h-3.5 w-3.5" />
                    <span>Ping Heartbeat (POST /api/heartbeat)</span>
                  </>
                )}
              </button>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
