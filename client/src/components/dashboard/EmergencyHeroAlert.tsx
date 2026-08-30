import { useState } from "react"
import { motion } from "framer-motion"
import { 
  PhoneCall, 
  Phone, 
  MapPin, 
  ExternalLink, 
  CheckCircle2, 
  Copy, 
  ShieldCheck,
  Clock,
  Radio,
  AlertTriangle,
  Eye,
  Ambulance
} from "lucide-react"
import { useDashboard } from "@/context/DashboardContext"
import { ActionSwapButton } from "@/components/motion/action-swap"
import { Magnetic } from "@/components/motion/magnetic"
import { AnimatedNumber } from "@/components/motion/animated-number"

export function EmergencyHeroAlert() {
  const { activeAlert, acknowledgeAlert, dispatchEmergencyServices, resolveAlert } = useDashboard()
  const [copied, setCopied] = useState(false)

  if (!activeAlert) {
    return null
  }

  const isSevere = activeAlert.severity === "CRITICAL" || activeAlert.severity === "SEVERE"
  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${activeAlert.location.lat},${activeAlert.location.lon}`

  const copyEmergencyScript = () => {
    const text = `EMERGENCY DISPATCH: Accident detected at ${activeAlert.location.address} (Lat: ${activeAlert.location.lat}, Lon: ${activeAlert.location.lon}). Rider: ${activeAlert.rider_name}. Severity: ${activeAlert.severity_label}. Impact force: ${activeAlert.telemetry.peak_g}G.`
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`w-full rounded-2xl border shadow-md transition-all overflow-hidden ${
        isSevere 
          ? "border-destructive/40 bg-gradient-to-b from-destructive/10 via-card to-card" 
          : "border-amber-500/40 bg-gradient-to-b from-amber-500/10 via-card to-card"
      }`}
    >
      {/* Top Banner Alert Bar */}
      <div className={`px-5 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs font-medium border-b ${
        isSevere ? "bg-destructive/15 text-destructive border-destructive/20" : "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/20"
      }`}>
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isSevere ? "bg-destructive" : "bg-amber-500"}`}></span>
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${isSevere ? "bg-destructive" : "bg-amber-500"}`}></span>
          </span>
          <span className="font-bold tracking-wide uppercase flex items-center gap-1.5">
            {activeAlert.status === "SOS_SENT" ? (
              <><AlertTriangle className="h-4 w-4" /> Active SOS Triggered</>
            ) : activeAlert.status === "ACKNOWLEDGED" ? (
              <><Eye className="h-4 w-4" /> Alert Acknowledged</>
            ) : (
              <><Ambulance className="h-4 w-4" /> Emergency Services Dispatched</>
            )}
          </span>
          <span className="opacity-40">|</span>
          <span>Event {activeAlert.event_id}</span>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1">
            <Clock className="h-3.5 w-3.5 opacity-70" />
            Triggered 2 mins ago
          </span>
          <span className="px-2 py-0.5 rounded-full bg-background/60 font-semibold">
            <AnimatedNumber value={activeAlert.confidence_pct} />% Confidence
          </span>
        </div>
      </div>

      {/* Main Alert Body */}
      <div className="p-5 sm:p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
          {/* Left info column */}
          <div className="space-y-3 flex-1 min-w-0">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className={`px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wider ${
                isSevere ? "bg-destructive text-white" : "bg-amber-500 text-white"
              }`}>
                {activeAlert.severity}
              </span>
              <h2 className="text-xl sm:text-2xl font-bold text-foreground tracking-tight font-display">
                {activeAlert.severity_label}
              </h2>
            </div>

            <div className="grid sm:grid-cols-2 gap-2 text-xs text-muted-foreground">
              <div className="flex items-center gap-2">
                <span className="font-medium text-foreground">Rider:</span>
                <span className="font-semibold text-foreground">{activeAlert.rider_name}</span>
                <span className="text-muted-foreground">({activeAlert.vehicle_model})</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-medium text-foreground">Sensor Node:</span>
                <span className="font-mono bg-muted px-1.5 py-0.5 rounded text-foreground">{activeAlert.device_id}</span>
                <span className="text-accent flex items-center gap-1 font-medium">
                  <Radio className="h-3 w-3" /> GSM / GPS Linked
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2 text-xs bg-muted/60 p-2.5 rounded-lg border border-border">
              <MapPin className="h-4 w-4 text-primary shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <span className="font-medium text-foreground">{activeAlert.location.address}</span>
                <span className="text-muted-foreground block text-[11px] mt-0.5">
                  Coordinates: {activeAlert.location.lat.toFixed(4)}° N, {activeAlert.location.lon.toFixed(4)}° E (GPS 3D Fix: 8 Sats Lock)
                </span>
              </div>
              <button 
                onClick={copyEmergencyScript}
                title="Copy emergency dispatch address"
                className="shrink-0 flex items-center gap-1 px-2 py-1 rounded bg-background text-[11px] font-medium text-muted-foreground hover:text-foreground border border-border transition-colors"
              >
                <Copy className="h-3 w-3" />
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
          </div>

          {/* Right Action Suite */}
          <div className="flex flex-col sm:flex-row lg:flex-col gap-2.5 shrink-0 justify-center">
            {/* Primary Action 1: Call 112 */}
            <div className="flex gap-2">
              <Magnetic strength={0.2} className="w-full">
                <a
                  href="tel:112"
                  onClick={() => dispatchEmergencyServices(activeAlert.device_id)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-destructive hover:bg-destructive/90 text-white font-medium text-xs shadow-sm transition-all text-center"
                >
                  <PhoneCall className="h-4 w-4" />
                  <span>Call Emergency (112)</span>
                </a>
              </Magnetic>

              <Magnetic strength={0.2} className="w-full">
                <a
                  href="tel:+919876543210"
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary hover:bg-primary/90 text-white font-medium text-xs shadow-sm transition-all text-center"
                >
                  <Phone className="h-4 w-4" />
                  <span>Call Rahul</span>
                </a>
              </Magnetic>
            </div>

            {/* Secondary Actions */}
            <div className="flex gap-2">
              <a
                href={mapsUrl}
                target="_blank"
                rel="noreferrer noopener"
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-secondary hover:bg-secondary/80 text-foreground font-medium text-xs border border-border transition-colors"
              >
                <MapPin className="h-3.5 w-3.5 text-primary" />
                <span>Navigate</span>
                <ExternalLink className="h-3 w-3 opacity-60" />
              </a>

              {/* beUI ActionSwapButton for Acknowledge lifecycle */}
              <ActionSwapButton
                items={[
                  {
                    id: "ack_pending",
                    label: "I've Seen This",
                    icon: <CheckCircle2 className="h-3.5 w-3.5" />,
                  },
                  {
                    id: "ack_done",
                    label: "Acknowledged ✓",
                    icon: <ShieldCheck className="h-3.5 w-3.5 text-accent" />,
                  },
                ]}
                value={activeAlert.status !== "SOS_SENT" ? "ack_done" : "ack_pending"}
                onValueChange={(val) => {
                  if (val === "ack_done") {
                    acknowledgeAlert(activeAlert.device_id)
                  }
                }}
                variant="secondary"
                size="sm"
                className="flex-1 rounded-xl text-xs h-auto py-2 font-medium"
              />

              <button
                onClick={() => resolveAlert(activeAlert.device_id)}
                className="px-3 py-2 rounded-xl bg-background hover:bg-muted text-muted-foreground hover:text-foreground text-xs font-medium border border-border transition-colors"
              >
                Resolve
              </button>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
