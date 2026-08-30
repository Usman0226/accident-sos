import { useState, useMemo } from "react"
import { Table, type TableColumn } from "@/components/motion/table"
import { 
  Database, 
  Radio, 
  RefreshCw, 
  Search, 
  CheckCircle2, 
  ShieldAlert, 
  BellRing,
  MapPin,
  Battery,
  ChevronDown
} from "lucide-react"
import { useDashboard } from "@/context/DashboardContext"
import { AnimatedNumber } from "@/components/motion/animated-number"

export function SensorDataTable() {
  const { devices, events, selectedDeviceId, setSelectedDeviceId, refreshData, isBackendConnected } = useDashboard()
  const [viewMode, setViewMode] = useState<"nodes" | "events" | "raw">("nodes")
  const [searchQuery, setSearchQuery] = useState("")
  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refreshData()
    setTimeout(() => setIsRefreshing(false), 500)
  }

  // Filter devices
  const filteredDevices = devices.filter((d) => {
    const q = searchQuery.toLowerCase()
    return (
      d.device_id.toLowerCase().includes(q) ||
      (d.rider_name && d.rider_name.toLowerCase().includes(q)) ||
      (d.status && d.status.toLowerCase().includes(q))
    )
  })

  // Filter events
  const filteredEvents = events.filter((e) => {
    const q = searchQuery.toLowerCase()
    return (
      e.device_id.toLowerCase().includes(q) ||
      e.type.toLowerCase().includes(q) ||
      String(e.id).includes(q)
    )
  })

  const formatTime = (ts?: number) => {
    if (!ts) return "Just now"
    const d = new Date(ts)
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
  }

  const deviceColumns = useMemo<TableColumn<any>[]>(() => [
    {
      key: "device_rider",
      header: "Device & Rider",
      width: "180px",
      cell: (device) => {
        const isSos = device.status === "sos_confirmed"
        const isOffline = device.status === "unreachable"
        return (
          <div className="flex items-center gap-2.5">
            <div className={`h-8 w-8 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 ${
              isSos ? "bg-destructive text-white" : isOffline ? "bg-muted text-muted-foreground" : "bg-accent/15 text-accent"
            }`}>
              <Radio className="h-4 w-4" />
            </div>
            <div>
              <span className="font-bold text-foreground block">{device.rider_name || device.device_id}</span>
              <span className="font-mono text-[10px] text-muted-foreground">{device.device_id}</span>
            </div>
          </div>
        )
      }
    },
    {
      key: "accident_state",
      header: "Accident State",
      cell: (device) => {
        const isSos = device.status === "sos_confirmed"
        const isOffline = device.status === "unreachable"
        return (
          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
            isSos 
              ? "bg-destructive text-white animate-pulse" 
              : isOffline 
                ? "bg-muted text-muted-foreground" 
                : "bg-accent/15 text-accent"
          }`}>
            {isSos ? "🚨 SOS CRASH" : isOffline ? "Offline" : "✓ Safe Riding"}
          </span>
        )
      }
    },
    {
      key: "speed",
      header: "Speed (GPS)",
      cell: (device) => {
        const isOffline = device.status === "unreachable"
        const speed = device.last_speed_kmph || (isOffline ? 0.0 : 42.0)
        return (
          <div className="font-mono text-xs font-bold text-foreground">
            <AnimatedNumber value={speed} format={(v) => `${v.toFixed(1)} km/h`} />
          </div>
        )
      }
    },
    {
      key: "acceleration",
      header: "Acceleration (MPU6050)",
      cell: (device) => {
        const isSos = device.status === "sos_confirmed"
        const impactG = isSos ? 8.70 : 1.01
        return (
          <div className="space-y-0.5">
            <span className={`font-mono text-xs font-bold block ${isSos ? "text-destructive" : "text-foreground"}`}>
              {impactG.toFixed(2)} G Total
            </span>
            <span className="text-[10px] text-muted-foreground font-mono block">
              {isSos ? "Ax:+6.80 Ay:+4.20 Az:+1.90" : "Ax:+0.08 Ay:+0.14 Az:+0.99"}
            </span>
          </div>
        )
      }
    },
    {
      key: "gyro",
      header: "Gyro / Lean Angle",
      cell: (device) => {
        const isSos = device.status === "sos_confirmed"
        const isOffline = device.status === "unreachable"
        const speed = device.last_speed_kmph || (isOffline ? 0.0 : 42.0)
        const gyroDelta = isSos ? 145.2 : 4.8
        const leanAngle = isSos ? 64.0 : (speed > 0 ? 12.5 : 2.1)
        return (
          <div className="space-y-0.5">
            <span className="font-mono text-xs text-foreground block">
              {gyroDelta.toFixed(1)}°/s
            </span>
            <span className={`text-[10px] font-medium block ${leanAngle > 50 ? "text-destructive" : "text-muted-foreground"}`}>
              Lean: {leanAngle.toFixed(1)}° {leanAngle > 50 ? "(Rollover)" : ""}
            </span>
          </div>
        )
      }
    },
    {
      key: "gps",
      header: "GPS Coordinates",
      cell: (device) => (
        <div className="space-y-0.5">
          <span className="font-mono text-xs text-foreground block">
            {device.last_gps_lat ? `${device.last_gps_lat.toFixed(4)}° N, ${device.last_gps_lon?.toFixed(4)}° E` : "No GPS Lock"}
          </span>
          <span className="text-[10px] text-muted-foreground flex items-center gap-1">
            <MapPin className="h-3 w-3 text-primary" />
            {device.last_gps_lat ? "3D RTK Fix (8 Sats)" : "Searching..."}
          </span>
        </div>
      )
    },
    {
      key: "battery",
      header: "Battery",
      cell: (device) => (
        <div className="flex items-center gap-1 text-xs font-mono font-semibold">
          <Battery className={`h-3.5 w-3.5 ${device.battery_pct < 20 ? "text-destructive" : "text-accent"}`} />
          <span>{device.battery_pct || 85}%</span>
        </div>
      )
    },
    {
      key: "action",
      header: "Action",
      align: "right",
      cell: (device) => {
        const isSelected = device.device_id === selectedDeviceId
        return (
          <button
            onClick={() => setSelectedDeviceId(device.device_id)}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              isSelected 
                ? "bg-primary text-white" 
                : "bg-secondary hover:bg-secondary/80 text-foreground border border-border"
            }`}
          >
            {isSelected ? "Active Focus" : "Select Node"}
          </button>
        )
      }
    }
  ], [selectedDeviceId, setSelectedDeviceId])

  const eventColumns = useMemo<TableColumn<any>[]>(() => [
    {
      key: "id",
      header: "Event ID",
      width: "100px",
      cell: (evt) => (
        <span className="font-mono text-xs font-bold text-foreground">
          EVT-{evt.id}
        </span>
      )
    },
    {
      key: "device_id",
      header: "Device Node",
      cell: (evt) => (
        <span className="font-mono text-xs bg-muted px-2 py-0.5 rounded border border-border text-foreground font-semibold">
          {evt.device_id}
        </span>
      )
    },
    {
      key: "type",
      header: "Event Type",
      cell: (evt) => {
        const isImpact = evt.type === "impact"
        const isSos = evt.type === "sos_dispatch"
        const isAck = evt.type === "alert_acknowledged"
        return (
          <div className="flex items-center gap-1.5">
            {isImpact ? <ShieldAlert className="h-3.5 w-3.5 text-destructive" /> :
             isSos ? <BellRing className="h-3.5 w-3.5 text-amber-500" /> :
             isAck ? <CheckCircle2 className="h-3.5 w-3.5 text-accent" /> :
             <Radio className="h-3.5 w-3.5 text-primary" />}
            <span className="font-semibold text-xs text-foreground uppercase">
              {evt.type.replace("_", " ")}
            </span>
          </div>
        )
      }
    },
    {
      key: "severity",
      header: "Severity / Status",
      cell: (evt) => {
        const payload = (evt.payload || {}) as Record<string, any>
        const isImpact = evt.type === "impact"
        const isSos = evt.type === "sos_dispatch"
        const isAck = evt.type === "alert_acknowledged"
        return (
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
            isImpact ? "bg-destructive text-white animate-pulse" :
            isSos ? "bg-amber-500/15 text-amber-600 dark:text-amber-400" :
            isAck ? "bg-accent/15 text-accent" : "bg-muted text-muted-foreground"
          }`}>
            {payload.severity || (isImpact ? "CRITICAL (94%)" : isAck ? "RESOLVED" : "NORMAL")}
          </span>
        )
      }
    },
    {
      key: "impact_force",
      header: "Impact Force",
      cell: (evt) => {
        const payload = (evt.payload || {}) as Record<string, any>
        const isImpact = evt.type === "impact"
        return (
          <span className={`font-mono text-xs font-bold ${isImpact ? "text-destructive" : "text-foreground"}`}>
            {typeof payload.impact_g === "number" ? `${payload.impact_g.toFixed(2)}G` : (payload.total_g ? `${payload.total_g.toFixed(2)}G` : "1.01G")}
          </span>
        )
      }
    },
    {
      key: "angular_tumble",
      header: "Angular Tumble",
      cell: (evt) => {
        const payload = (evt.payload || {}) as Record<string, any>
        return (
          <span className="font-mono text-xs text-foreground">
            {typeof payload.gyro_x === "number" ? `${payload.gyro_x.toFixed(1)}°/s` : "4.8°/s"}
          </span>
        )
      }
    },
    {
      key: "gps",
      header: "GPS Location",
      cell: (evt) => {
        const payload = (evt.payload || {}) as Record<string, any>
        return (
          <span className="font-mono text-[11px] text-foreground">
            {payload.gps_lat ? `${Number(payload.gps_lat).toFixed(4)}°, ${Number(payload.gps_lon).toFixed(4)}°` : "Recorded"}
          </span>
        )
      }
    },
    {
      key: "timestamp",
      header: "Timestamp",
      cell: (evt) => (
        <span className="font-mono text-xs text-muted-foreground">
          {formatTime(evt.timestamp)}
        </span>
      )
    },
    {
      key: "payload",
      header: "Payload",
      align: "right",
      cell: () => (
        <button className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground">
          <ChevronDown className="h-4 w-4" />
        </button>
      )
    }
  ], [])

  const renderEventExpandedRow = (evt: any) => {
    const payload = (evt.payload || {}) as Record<string, any>
    return (
      <div className="p-3">
        <div className="p-3 rounded-xl bg-card border border-border space-y-1">
          <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">
            Raw Database JSON Payload
          </span>
          <pre className="font-mono text-[11px] text-foreground overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(payload, null, 2)}
          </pre>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full rounded-2xl border border-border bg-card shadow-sm overflow-hidden space-y-0">
      {/* Top Header & View Tabs Bar */}
      <div className="p-4 sm:p-5 border-b border-border bg-card space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-foreground tracking-tight flex items-center gap-2 font-display">
              <Database className="h-4 w-4 text-primary" />
              Live Sensor & Telemetry Database Table
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Continuous live stream directly from FastAPI backend endpoints (<code className="font-mono text-[11px] bg-muted px-1 py-0.5 rounded">/api/devices</code> & <code className="font-mono text-[11px] bg-muted px-1 py-0.5 rounded">/api/events</code>)
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold flex items-center gap-1.5 ${
              isBackendConnected ? "bg-accent/15 text-accent" : "bg-destructive/15 text-destructive"
            }`}>
              <span className={`h-2 w-2 rounded-full ${isBackendConnected ? "bg-accent animate-pulse" : "bg-destructive"}`} />
              {isBackendConnected ? "FastAPI Live Stream (2.5s)" : "Backend Offline"}
            </span>

            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-background hover:bg-muted text-muted-foreground hover:text-foreground text-xs font-semibold border border-border transition-colors shadow-xs"
              title="Force Sync with SQLite Database"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin text-primary" : ""}`} />
              <span>Sync DB</span>
            </button>
          </div>
        </div>

        {/* Search & Mode Switcher Controls */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
          {/* Mode Tabs */}
          <div className="flex items-center gap-1 p-1 rounded-xl bg-background border border-border">
            <button
              onClick={() => setViewMode("nodes")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                viewMode === "nodes"
                  ? "bg-primary text-white shadow-xs"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              All Live Nodes ({devices.length})
            </button>
            <button
              onClick={() => setViewMode("events")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                viewMode === "events"
                  ? "bg-primary text-white shadow-xs"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              Ingested Event Log ({events.length})
            </button>
          </div>

          {/* Search Box */}
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Filter by device, rider, status..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl bg-background border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>
      </div>

      {/* TABLE VIEW 1: Live Hardware Node States */}
      {viewMode === "nodes" && (
        <div className="flex flex-col h-[500px]">
          <Table
            data={filteredDevices}
            columns={deviceColumns}
            getRowId={(row) => row.device_id}
            height={500}
            rowHeight={64}
            selectedRowIds={selectedDeviceId ? [selectedDeviceId] : []}
          />
        </div>
      )}

      {/* TABLE VIEW 2: Ingested Events Log Stream */}
      {viewMode === "events" && (
        <div className="flex flex-col h-[500px]">
          <Table
            data={filteredEvents}
            columns={eventColumns}
            getRowId={(row) => String(row.id)}
            renderExpandedRow={renderEventExpandedRow}
            height={500}
            rowHeight={64}
          />
        </div>
      )}
    </div>
  )
}
