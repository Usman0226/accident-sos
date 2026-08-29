import { useState, useMemo } from "react"
import { Table, TableColumn } from "@/components/motion/table"
import { History, Filter, Download, AlertTriangle, Radio, ShieldCheck, CheckCircle2, ChevronDown } from "lucide-react"
import { useDashboard } from "@/context/DashboardContext"

export function HistoryView() {
  const { events } = useDashboard()
  const [filterType, setFilterType] = useState<string>("all")

  const filteredEvents = events.filter((e) => {
    if (filterType === "all") return true
    return e.type === filterType
  })

  const exportJson = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(events, null, 2))
    const downloadAnchor = document.createElement("a")
    downloadAnchor.setAttribute("href", dataStr)
    downloadAnchor.setAttribute("download", `accident_sos_audit_events_${Date.now()}.json`)
    document.body.appendChild(downloadAnchor)
    downloadAnchor.click()
    downloadAnchor.remove()
  }

  const columns = useMemo<TableColumn<any>[]>(() => [
    {
      key: "id",
      header: "ID",
      width: "100px",
      cell: (row) => (
        <span className="font-mono text-xs font-bold text-foreground">
          #{row.id}
        </span>
      ),
    },
    {
      key: "type",
      header: "Type",
      cell: (row) => {
        const isImpact = row.type === "impact"
        const isSos = row.type === "sos_dispatch"
        const isAck = row.type === "alert_acknowledged"
        return (
          <div className="flex items-center gap-2">
            <div className={`h-6 w-6 rounded-md flex items-center justify-center shrink-0 ${
              isImpact ? "bg-destructive text-white" :
              isSos ? "bg-amber-500 text-white" :
              isAck ? "bg-accent text-white" :
              "bg-muted text-muted-foreground"
            }`}>
              {isImpact ? <AlertTriangle className="h-3.5 w-3.5" /> :
               isSos ? <Radio className="h-3.5 w-3.5" /> :
               isAck ? <CheckCircle2 className="h-3.5 w-3.5" /> :
               <ShieldCheck className="h-3.5 w-3.5 text-foreground" />}
            </div>
            <span className="font-bold text-xs capitalize text-foreground">
              {row.type.replace("_", " ")}
            </span>
          </div>
        )
      },
    },
    {
      key: "device_id",
      header: "Device Node",
      cell: (row) => (
        <span className="font-mono text-xs bg-muted px-2 py-0.5 rounded text-foreground border border-border font-semibold">
          {row.device_id}
        </span>
      ),
    },
    {
      key: "summary",
      header: "Summary / Metrics",
      cell: (row) => {
        const isImpact = row.type === "impact"
        const isSos = row.type === "sos_dispatch"
        const isAck = row.type === "alert_acknowledged"
        const payload = (row.payload || {}) as Record<string, any>
        return (
          <span className="font-mono text-xs text-muted-foreground">
            {isImpact 
              ? `Impact: ${payload.impact_g || 0}G · Gyro X: ${payload.gyro_x || 0}°/s · Lat: ${payload.gps_lat}`
              : isSos 
                ? `Dispatched via ${payload.method || "SMS"} · Success: ${String(payload.success)}`
                : isAck 
                  ? `Operator: ${payload.actor || "human_operator"}`
                  : `Speed: ${payload.gps_speed_kmph || 0} km/h · Batt: ${payload.battery_pct || 0}% · Lat: ${payload.gps_lat}`}
          </span>
        )
      },
    },
    {
      key: "timestamp",
      header: "Timestamp",
      cell: (row) => (
        <span className="font-mono text-xs text-muted-foreground">
          {new Date(row.timestamp).toLocaleString()}
        </span>
      ),
    },
    {
      key: "action",
      header: "Payload",
      align: "right",
      cell: () => (
        <button className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground">
          <ChevronDown className="h-4 w-4" />
        </button>
      ),
    },
  ], [])

  const renderExpandedRow = (row: any) => (
    <div className="p-4 space-y-1">
      <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">
        Raw Database Payload JSON
      </span>
      <pre className="p-3 rounded-xl bg-card border border-border font-mono text-[11px] text-foreground overflow-x-auto">
        {JSON.stringify(row.payload, null, 2)}
      </pre>
    </div>
  )

  return (
    <div className="w-full max-w-[1440px] mx-auto p-4 sm:p-6 space-y-5">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-2xl border border-border bg-card shadow-sm">
        <div>
          <h2 className="text-lg font-bold text-foreground tracking-tight font-display flex items-center gap-2">
            <History className="h-5 w-5 text-primary" />
            Incident Audit Logs & Event Trail Table
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Immutable database records of impacts, dispatches, heartbeats, and operator acknowledgments
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Filter Dropdown */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-background border border-border text-xs">
            <Filter className="h-3.5 w-3.5 text-muted-foreground" />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="bg-transparent text-foreground focus:outline-none cursor-pointer"
            >
              <option value="all">All Events ({events.length})</option>
              <option value="impact">Impact Events</option>
              <option value="sos_dispatch">SOS Dispatches</option>
              <option value="heartbeat">Heartbeats</option>
              <option value="alert_acknowledged">Operator Acknowledged</option>
            </select>
          </div>

          <button
            onClick={exportJson}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-secondary hover:bg-secondary/80 text-foreground font-semibold text-xs border border-border transition-colors shadow-sm"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Export Audit JSON</span>
          </button>
        </div>
      </div>

      {/* Events Table Container using BeUI Table */}
      <div className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden flex flex-col h-[500px]">
        <Table 
          data={filteredEvents} 
          columns={columns} 
          getRowId={(row) => String(row.id)}
          renderExpandedRow={renderExpandedRow}
          height={500}
          rowHeight={64}
        />
      </div>
    </div>
  )
}
