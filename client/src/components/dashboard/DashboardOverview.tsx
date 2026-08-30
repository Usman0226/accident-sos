import { useDashboard } from "@/context/DashboardContext"
import { EmergencyHeroAlert } from "./EmergencyHeroAlert"
import { SensorDataTable } from "./SensorDataTable"
import { SensorTelemetryGrid } from "./SensorTelemetryGrid"
import { LiveLocationRadar } from "./LiveLocationRadar"
import { IncidentLifecycleTimeline } from "./IncidentLifecycleTimeline"
import { HardwareFleetMonitor } from "./HardwareFleetMonitor"
import { IncidentHistoryList } from "./IncidentHistoryList"
import { SimulationControlBar } from "./SimulationControlBar"
import { IncidentDetailModal } from "./IncidentDetailModal"
import { useState } from "react"
import { MapView } from "./views/MapView"
import { SensorTelemetryView } from "./views/SensorTelemetryView"
import { FleetView } from "./views/FleetView"
import { HistoryView } from "./views/HistoryView"

export function DashboardOverview() {
  const { activeTab, selectedDeviceId, setSelectedDeviceId } = useDashboard()
  const [isModalOpen, setIsModalOpen] = useState(false)

  const handleIncidentSelect = (deviceId: string) => {
    setSelectedDeviceId(deviceId)
    setIsModalOpen(true)
  }

  // Render dedicated view if selected in sidebar
  if (activeTab === "map") {
    return <MapView />
  }

  if (activeTab === "telemetry") {
    return <SensorTelemetryView />
  }

  if (activeTab === "fleet") {
    return <FleetView />
  }

  if (activeTab === "history") {
    return <HistoryView />
  }

  // Default: Unified Emergency Command Center & Continuous Live Sensor Telemetry Table
  return (
    <div className="w-full max-w-[1440px] mx-auto p-4 sm:p-6 space-y-5">
      {/* Simulation Controls for Quick Testing */}
      <SimulationControlBar />

      {/* Primary Emergency Alert Bar / Safe Status Banner */}
      <EmergencyHeroAlert />

      {/* Live Ingested Sensor & Telemetry Data Table (BeUI Table Component) */}
      <SensorDataTable />

      {/* Main High-Density Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Column (7 cols): Incident History & Active Incidents */}
        <div className="lg:col-span-7 space-y-5">
          <IncidentHistoryList onSelect={handleIncidentSelect} />
          <LiveLocationRadar />
        </div>

        {/* Right Column (5 cols): Fleet Status */}
        <div className="lg:col-span-5 space-y-5">
          <HardwareFleetMonitor />
        </div>
      </div>

      <IncidentDetailModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        deviceId={selectedDeviceId} 
      />
    </div>
  )
}
