import { X } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { SensorTelemetryGrid } from "./SensorTelemetryGrid"
import { IncidentLifecycleTimeline } from "./IncidentLifecycleTimeline"

interface IncidentDetailModalProps {
  isOpen: boolean
  onClose: () => void
  deviceId: string | null
}

export function IncidentDetailModal({ isOpen, onClose, deviceId }: IncidentDetailModalProps) {
  if (!isOpen || !deviceId) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="relative w-full max-w-5xl max-h-[90vh] overflow-y-auto bg-card border border-border rounded-2xl shadow-xl flex flex-col"
        >
          <div className="sticky top-0 z-10 flex items-center justify-between p-4 sm:p-6 border-b border-border bg-card">
            <h2 className="text-lg font-bold text-foreground">Incident Details - {deviceId}</h2>
            <button
              onClick={onClose}
              className="p-2 rounded-full hover:bg-muted text-muted-foreground transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="p-4 sm:p-6 space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="space-y-6">
                <SensorTelemetryGrid />
              </div>
              <div className="space-y-6">
                <IncidentLifecycleTimeline />
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
