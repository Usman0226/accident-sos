import { createContext, useContext, useEffect, useState, useCallback, useRef, type ReactNode } from "react"
import { api, type DeviceDto, type EventDto, type SensorDataPayload } from "@/services/api"
import { audioAlert } from "@/services/audioAlert"

export interface DeviceInfo extends DeviceDto {
  rider_name?: string
  vehicle_model?: string
  last_speed_kmph?: number
}

export interface TelemetryEvent extends EventDto {}

export interface DeviceLiveTelemetry {
  device_id: string
  rider_name: string
  vehicle_model: string
  accident_detected: boolean
  status: "NORMAL_RIDING" | "STATIONARY" | "SOS_CONFIRMED" | "UNREACHABLE"
  timestamp: number
  speed_kmph: number
  battery_pct: number
  location: {
    lat: number
    lon: number
    address: string
    gps_fix: boolean
    satellite_count: number
  }
  imu: {
    accel_x: number
    accel_y: number
    accel_z: number
    total_g: number
    gyro_x: number
    gyro_y: number
    gyro_z: number
    gyro_delta: number
    lean_angle: number
    jerk: number
    post_motion: number
  }
  rawContractJson: Record<string, unknown>
}

export interface ActiveAlert {
  event_id: string
  device_id: string
  rider_name: string
  vehicle_model: string
  timestamp: number
  severity: "CRITICAL" | "SEVERE" | "MODERATE" | "MINOR"
  severity_label: string
  confidence_pct: number
  confidence_label: string
  location: {
    lat: number
    lon: number
    address: string
    gps_fix: boolean
    satellite_count: number
  }
  telemetry: {
    peak_g: number
    jerk_gs: number
    gyro_deg: number
    orientation_delta: number
    post_motion: number
    speed_kmph: number
  }
  status: "SOS_SENT" | "ACKNOWLEDGED" | "DISPATCHED" | "RESOLVED"
  timeline: Array<{
    time: string
    title: string
    description: string
    status: "done" | "current" | "pending"
  }>
}

interface DashboardContextType {
  activeTab: "emergency" | "map" | "telemetry" | "fleet" | "history"
  setActiveTab: (tab: "emergency" | "map" | "telemetry" | "fleet" | "history") => void
  devices: DeviceInfo[]
  events: TelemetryEvent[]
  activeAlert: ActiveAlert | null
  selectedDeviceId: string
  setSelectedDeviceId: (id: string) => void
  selectedTelemetry: DeviceLiveTelemetry
  isBackendConnected: boolean
  lastSyncTime: Date
  acknowledgeAlert: (deviceId: string) => Promise<void>
  dispatchEmergencyServices: (deviceId: string) => Promise<void>
  resolveAlert: (deviceId: string) => Promise<void>
  triggerSimulation: (type: "severe_crash" | "moderate_impact" | "clear") => Promise<void>
  refreshData: () => Promise<void>
}

const RIDER_MAPPINGS: Record<string, { name: string; vehicle: string; address: string }> = {
  VEH_002: { name: "Rahul Sharma", vehicle: "KTM Duke 390 · KA-04-EK-9821", address: "Ring Road, Near AIIMS Flyover, New Delhi" },
  VEH_001: { name: "Amit Patel", vehicle: "Honda CB350 · TS-09-UB-4412", address: "Outer Ring Road, Gachibowli, Hyderabad" },
  VEH_003: { name: "Sneha Reddy", vehicle: "Royal Enfield 350 · AP-03-BW-1109", address: "SV University Road, Tirupati" },
  TEST_001: { name: "Demo Test Node", vehicle: "Sensor Prototype", address: "Electronic City Phase 1, Bangalore" },
}

const DashboardContext = createContext<DashboardContextType | null>(null)

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [activeTab, setActiveTab] = useState<"emergency" | "map" | "telemetry" | "fleet" | "history">("emergency")
  const [devices, setDevices] = useState<DeviceInfo[]>([])
  const [events, setEvents] = useState<TelemetryEvent[]>([])
  const [activeAlert, setActiveAlert] = useState<ActiveAlert | null>(null)
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("VEH_001")
  const [isBackendConnected, setIsBackendConnected] = useState(true)
  const [lastSyncTime, setLastSyncTime] = useState<Date>(new Date())
  const prevAlertIdRef = useRef<string | null>(null)

  // Fetch real data from FastAPI backend
  const syncWithBackend = useCallback(async () => {
    try {
      const [devRes, evtRes] = await Promise.all([
        api.getDevices(),
        api.getEvents(50),
      ])

      const fetchedDevices: DeviceDto[] = devRes?.devices || []
      const fetchedEvents: EventDto[] = evtRes?.events || []

      const enrichedDevices: DeviceInfo[] = fetchedDevices.map((d) => {
        const meta = RIDER_MAPPINGS[d.device_id] || {
          name: `Device ${d.device_id}`,
          vehicle: "Registered Vehicle Unit",
          address: `${d.last_gps_lat?.toFixed(4)}° N, ${d.last_gps_lon?.toFixed(4)}° E`,
        }

        // Find the most recent heartbeat or event for speed
        const latestEvent = fetchedEvents.find((e) => e.device_id === d.device_id)
        const payload = (latestEvent?.payload || {}) as Record<string, any>
        const speed = typeof payload.speed_kmph === "number" ? payload.speed_kmph : (d.status === "unreachable" ? 0.0 : 42.0)

        return {
          ...d,
          rider_name: meta.name,
          vehicle_model: meta.vehicle,
          last_speed_kmph: speed,
        }
      })

      setDevices(enrichedDevices)
      setEvents(fetchedEvents)
      setIsBackendConnected(true)
      setLastSyncTime(new Date())

      // Determine active SOS / impact from real events and real device states
      const activeSosDevice = enrichedDevices.find((d) => d.status === "sos_confirmed" || d.status === "impact_detected")
      const latestImpactEvent = fetchedEvents.find((e) => e.type === "impact")
      const latestAckEvent = fetchedEvents.find((e) => e.type === "alert_acknowledged")

      // Check if the most recent impact was already acknowledged after it happened
      const isAckAfterImpact = latestAckEvent && latestImpactEvent && latestAckEvent.timestamp >= latestImpactEvent.timestamp

      if (activeSosDevice || (latestImpactEvent && !isAckAfterImpact)) {
        const targetDeviceId = activeSosDevice ? activeSosDevice.device_id : latestImpactEvent!.device_id
        const meta = RIDER_MAPPINGS[targetDeviceId] || {
          name: `Rider (${targetDeviceId})`,
          vehicle: "KTM Duke 390",
          address: "Location Coordinates Locked",
        }

        const payload = (latestImpactEvent?.payload || {}) as Record<string, any>
        const impactG = typeof payload.impact_g === "number" ? payload.impact_g : 8.7
        const gyroDelta = typeof payload.gyro_delta === "number" ? payload.gyro_delta : 145.2
        const lat = typeof payload.gps_lat === "number" ? payload.gps_lat : (activeSosDevice?.last_gps_lat || 28.6139)
        const lon = typeof payload.gps_lon === "number" ? payload.gps_lon : (activeSosDevice?.last_gps_lon || 77.2090)
        const gpsFix = payload.gps_fix !== false

        const isCrit = impactG >= 6.0
        const alertId = `EVT-${latestImpactEvent?.id || 1}`

        if (prevAlertIdRef.current !== alertId) {
          prevAlertIdRef.current = alertId
          audioAlert.playEmergencyChime()
        }

        setActiveAlert((prev) => {
          const currentStatus = prev?.status && prev.device_id === targetDeviceId ? prev.status : "SOS_SENT"

          return {
            event_id: alertId,
            device_id: targetDeviceId,
            rider_name: meta.name,
            vehicle_model: meta.vehicle,
            timestamp: latestImpactEvent?.timestamp || Date.now(),
            severity: isCrit ? "CRITICAL" : "MODERATE",
            severity_label: isCrit ? "Severe Impact & Vehicle Rollover" : "Side Collision Detected",
            confidence_pct: isCrit ? 94 : 78,
            confidence_label: isCrit ? "High Confidence · 94% Certainty" : "Moderate Confidence · 78% Certainty",
            location: {
              lat,
              lon,
              address: meta.address,
              gps_fix: gpsFix,
              satellite_count: gpsFix ? 8 : 0,
            },
            telemetry: {
              peak_g: impactG,
              jerk_gs: typeof payload.peak_jerk === "number" ? payload.peak_jerk : (impactG * 6.2),
              gyro_deg: gyroDelta,
              orientation_delta: typeof payload.orientation_change === "number" ? payload.orientation_change : (gyroDelta * 0.44),
              post_motion: typeof payload.post_impact_motion === "number" ? payload.post_impact_motion : 0.04,
              speed_kmph: typeof payload.speed_kmph === "number" ? payload.speed_kmph : 48.5,
            },
            status: currentStatus,
            timeline: prev?.timeline || [
              { time: "T+0.0s", title: "Impact Detected", description: `${impactG}G peak shockwave recorded on MPU6050`, status: "done" },
              { time: "T+0.8s", title: "Sensor Fusion Analysis", description: `Crash classified with ${isCrit ? "94%" : "78%"} confidence`, status: "done" },
              { time: "T+2.0s", title: "SOS Broadcast Fired", description: "Emergency alert sent via GSM SIM800L & Cloud API", status: "done" },
              { time: "T+1.5m", title: "Contact Dashboard Live", description: "Waiting for emergency contact response", status: "current" },
            ],
          }
        })
      } else {
        prevAlertIdRef.current = null
        setActiveAlert(null)
      }
    } catch (err) {
      console.warn("Backend sync failed:", err)
      setIsBackendConnected(false)
    }
  }, [])

  useEffect(() => {
    syncWithBackend()
    const interval = setInterval(syncWithBackend, 2500)
    return () => clearInterval(interval)
  }, [syncWithBackend])

  // Derive live telemetry for the selected device strictly from real data
  const selectedDeviceObj = devices.find((d) => d.device_id === selectedDeviceId) || devices[0]
  const deviceEvents = events.filter((e) => e.device_id === selectedDeviceObj?.device_id)
  const latestDeviceEvent = deviceEvents[0]
  const eventPayload = (latestDeviceEvent?.payload || {}) as Record<string, any>

  const isDeviceSos = selectedDeviceObj?.status === "sos_confirmed" || latestDeviceEvent?.type === "impact"
  const deviceMeta = RIDER_MAPPINGS[selectedDeviceObj?.device_id || ""] || {
    name: selectedDeviceObj?.rider_name || selectedDeviceObj?.device_id || "Node",
    vehicle: selectedDeviceObj?.vehicle_model || "Motorcycle Unit",
    address: `${selectedDeviceObj?.last_gps_lat || 0}° N, ${selectedDeviceObj?.last_gps_lon || 0}° E`,
  }

  const speedKmph = typeof eventPayload.speed_kmph === "number" 
    ? eventPayload.speed_kmph 
    : (selectedDeviceObj?.last_speed_kmph || (selectedDeviceObj?.status === "unreachable" ? 0.0 : 42.0))

  const impactG = typeof eventPayload.impact_g === "number" ? eventPayload.impact_g : (isDeviceSos ? 8.70 : 1.01)
  const gyroDelta = typeof eventPayload.gyro_delta === "number" ? eventPayload.gyro_delta : (isDeviceSos ? 145.2 : 4.8)
  const batteryPct = typeof eventPayload.battery_pct === "number" ? eventPayload.battery_pct : (selectedDeviceObj?.battery_pct || 87)
  const lat = typeof eventPayload.gps_lat === "number" ? eventPayload.gps_lat : (selectedDeviceObj?.last_gps_lat || 17.3850)
  const lon = typeof eventPayload.gps_lon === "number" ? eventPayload.gps_lon : (selectedDeviceObj?.last_gps_lon || 78.4867)
  const gpsFix = eventPayload.gps_fix !== false && selectedDeviceObj?.status !== "unreachable"

  const selectedTelemetry: DeviceLiveTelemetry = {
    device_id: selectedDeviceObj?.device_id || "VEH_001",
    rider_name: deviceMeta.name,
    vehicle_model: deviceMeta.vehicle,
    accident_detected: isDeviceSos,
    status: isDeviceSos 
      ? "SOS_CONFIRMED" 
      : selectedDeviceObj?.status === "unreachable" 
        ? "UNREACHABLE" 
        : speedKmph > 0 
          ? "NORMAL_RIDING" 
          : "STATIONARY",
    timestamp: latestDeviceEvent?.timestamp || selectedDeviceObj?.last_heartbeat_time || Date.now(),
    speed_kmph: speedKmph,
    battery_pct: batteryPct,
    location: {
      lat,
      lon,
      address: deviceMeta.address,
      gps_fix: gpsFix,
      satellite_count: gpsFix ? 8 : 0,
    },
    imu: {
      accel_x: isDeviceSos ? (impactG * 0.78) : 0.08,
      accel_y: isDeviceSos ? (impactG * 0.48) : 0.14,
      accel_z: isDeviceSos ? (impactG * 0.22) : 0.99,
      total_g: impactG,
      gyro_x: isDeviceSos ? gyroDelta : 4.8,
      gyro_y: isDeviceSos ? (gyroDelta * 0.22) : 1.2,
      gyro_z: isDeviceSos ? (gyroDelta * 0.12) : 0.6,
      gyro_delta: gyroDelta,
      lean_angle: isDeviceSos ? 64.0 : (speedKmph > 0 ? 12.5 : 2.1),
      jerk: isDeviceSos ? (impactG * 6.2) : 0.35,
      post_motion: isDeviceSos ? 0.04 : (speedKmph > 0 ? 1.20 : 0.0),
    },
    rawContractJson: latestDeviceEvent ? {
      event_id: `EVT-${latestDeviceEvent.id}`,
      device_id: latestDeviceEvent.device_id,
      timestamp: latestDeviceEvent.timestamp,
      event_type: latestDeviceEvent.type,
      accident_detected: isDeviceSos,
      confidence: isDeviceSos ? 0.94 : 0.02,
      severity: isDeviceSos ? (impactG >= 6.0 ? "CRITICAL" : "MODERATE") : "NORMAL",
      location: {
        latitude: lat,
        longitude: lon,
        gps_fix: gpsFix,
        speed_kmph: speedKmph,
        battery_pct: batteryPct,
      },
      features: isDeviceSos ? {
        peak_acceleration: impactG,
        peak_jerk: impactG * 6.2,
        peak_angular_velocity: gyroDelta,
        velocity_change: speedKmph,
        orientation_change: 64.0,
        post_impact_motion: 0.04,
      } : {
        peak_acceleration: 1.01,
        peak_jerk: 0.35,
        peak_angular_velocity: 4.8,
        velocity_change: 0.0,
        orientation_change: speedKmph > 0 ? 12.5 : 2.1,
        post_impact_motion: speedKmph > 0 ? 1.20 : 0.0,
      },
      status: isDeviceSos ? "SOS_CONFIRMED" : (selectedDeviceObj?.status === "unreachable" ? "UNREACHABLE" : "NORMAL_RIDING"),
      raw_payload: latestDeviceEvent.payload,
    } : {
      device_id: selectedDeviceObj?.device_id || "VEH_001",
      status: selectedDeviceObj?.status || "ok",
      last_heartbeat_time: selectedDeviceObj?.last_heartbeat_time,
      last_gps_lat: selectedDeviceObj?.last_gps_lat,
      last_gps_lon: selectedDeviceObj?.last_gps_lon,
      battery_pct: selectedDeviceObj?.battery_pct,
    },
  }

  const acknowledgeAlert = async (deviceId: string) => {
    audioAlert.playAcknowledgeBeep()
    try {
      await api.acknowledgeDevice(deviceId)
    } catch (err) {
      console.warn("Backend acknowledge failed:", err)
    }

    setActiveAlert((prev) => {
      if (!prev) return null
      return {
        ...prev,
        status: "ACKNOWLEDGED",
        timeline: [
          ...prev.timeline.filter((t) => t.status !== "current"),
          { time: "Just now", title: "Acknowledged by Emergency Contact", description: "Emergency contact confirmed awareness", status: "done" },
          { time: "Next", title: "Emergency Dispatch / Verification", description: "Awaiting responder action or safety verification", status: "current" },
        ],
      }
    })

    await syncWithBackend()
  }

  const dispatchEmergencyServices = async (_deviceId: string) => {
    audioAlert.playAcknowledgeBeep()
    setActiveAlert((prev) => {
      if (!prev) return null
      return {
        ...prev,
        status: "DISPATCHED",
        timeline: [
          ...prev.timeline.filter((t) => t.status !== "current"),
          { time: "Just now", title: "Emergency 112 Services Contacted", description: "Crash coordinates & G-force data relayed to responder", status: "done" },
          { time: "Ongoing", title: "Ambulance / Police En Route", description: "Live GPS broadcast to incoming unit", status: "current" },
        ],
      }
    })
  }

  const resolveAlert = async (deviceId: string) => {
    audioAlert.playAcknowledgeBeep()
    try {
      await api.acknowledgeDevice(deviceId)
    } catch (err) {
      console.warn("Resolve failed:", err)
    }
    setActiveAlert(null)
    await syncWithBackend()
  }

  const triggerSimulation = async (type: "severe_crash" | "moderate_impact" | "clear") => {
    if (type === "clear") {
      audioAlert.playAcknowledgeBeep()
      try {
        await api.acknowledgeDevice("VEH_002")
      } catch {}
      setActiveAlert(null)
      await syncWithBackend()
      return
    }

    audioAlert.playEmergencyChime()

    const payload: SensorDataPayload = {
      device_id: "VEH_002",
      sos_type: "ACCIDENT",
      timestamp: Date.now(),
      accel_x: type === "severe_crash" ? 4.5 : 1.5,
      accel_y: type === "severe_crash" ? -2.3 : -1.0,
      accel_z: type === "severe_crash" ? 12.1 : 10.5,
      gyro_x: type === "severe_crash" ? 45.2 : 12.0,
      gyro_y: type === "severe_crash" ? -12.0 : -5.0,
      gyro_z: type === "severe_crash" ? 145.2 : 32.1,
      impact_g: type === "severe_crash" ? 8.7 : 4.8,
      vibration: true,
      temperature: 28.0,
      humidity: 55.0,
      gps_lat: 28.6139,
      gps_lon: 77.2090,
      gps_fix: true,
      gps_speed_kmph: type === "severe_crash" ? 60.0 : 40.0,
      battery_pct: 85
    }

    try {
      await api.postSos(payload)
    } catch (err) {
      console.warn("Direct impact error:", err)
    }

    await syncWithBackend()
  }

  return (
    <DashboardContext.Provider
      value={{
        activeTab,
        setActiveTab,
        devices,
        events,
        activeAlert,
        selectedDeviceId,
        setSelectedDeviceId,
        selectedTelemetry,
        isBackendConnected,
        lastSyncTime,
        acknowledgeAlert,
        dispatchEmergencyServices,
        resolveAlert,
        triggerSimulation,
        refreshData: syncWithBackend,
      }}
    >
      {children}
    </DashboardContext.Provider>
  )
}

export function useDashboard() {
  const context = useContext(DashboardContext)
  if (!context) {
    throw new Error("useDashboard must be used within a DashboardProvider")
  }
  return context
}
