import { motion } from "framer-motion"
import { MapPin, Navigation, Compass, ExternalLink, Radio } from "lucide-react"
import { useDashboard } from "@/context/DashboardContext"

export function LiveLocationRadar() {
  const { activeAlert, selectedTelemetry } = useDashboard()

  const location = activeAlert?.location || selectedTelemetry.location
  const isAccident = activeAlert !== null || selectedTelemetry.accident_detected

  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${location.lat},${location.lon}`

  return (
    <div className="w-full rounded-2xl border border-border bg-card p-5 shadow-sm flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold text-foreground tracking-tight">
              Live GPS Location ({selectedTelemetry.device_id})
            </h3>
          </div>
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium ${
            location.gps_fix 
              ? "bg-accent/10 text-accent border border-accent/20" 
              : "bg-amber-500/10 text-amber-600 border border-amber-500/20"
          }`}>
            <Radio className="h-3 w-3 animate-pulse" />
            {location.gps_fix ? `3D Fix (${location.satellite_count} Sats)` : "Cell Approximate"}
          </span>
        </div>

        {/* Interactive GPS Visualizer */}
        <div className="relative w-full h-44 rounded-xl bg-gradient-to-br from-muted/80 to-muted border border-border overflow-hidden flex items-center justify-center group mb-3">
          {/* Radar Circles */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="w-48 h-48 rounded-full border border-primary/10 animate-ping opacity-20"></div>
            <div className="absolute w-36 h-36 rounded-full border border-primary/20"></div>
            <div className="absolute w-24 h-24 rounded-full border border-primary/30"></div>
            <div className="absolute w-12 h-12 rounded-full border border-primary/40"></div>
            <div className="absolute w-full h-[1px] bg-primary/10"></div>
            <div className="absolute h-full w-[1px] bg-primary/10"></div>
          </div>

          {/* Location Pin */}
          <motion.div 
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            className="relative z-10 flex flex-col items-center"
          >
            <div className="relative flex items-center justify-center">
              {isAccident && <span className="animate-ping absolute h-8 w-8 rounded-full bg-destructive opacity-75"></span>}
              <div className={`h-10 w-10 rounded-full text-white flex items-center justify-center shadow-lg border-2 border-background ${
                isAccident ? "bg-destructive" : "bg-primary"
              }`}>
                <Navigation className="h-5 w-5 rotate-45" />
              </div>
            </div>
            <div className="mt-2 px-2.5 py-1 rounded-md bg-background/90 backdrop-blur-sm border border-border text-[11px] font-semibold text-foreground shadow-sm">
              {isAccident ? "Impact Point (±2.5m)" : "Live Node Position (±1.5m)"}
            </div>
          </motion.div>

          {/* Compass Rose */}
          <div className="absolute top-2 right-2 flex items-center gap-1 text-[10px] font-mono text-muted-foreground bg-background/80 px-2 py-0.5 rounded border border-border">
            <Compass className="h-3 w-3 text-primary" />
            <span>N {location.lat.toFixed(2)}°</span>
          </div>

          {/* Road Tag */}
          <div className="absolute bottom-2 left-2 text-[11px] font-medium text-foreground bg-background/80 px-2.5 py-1 rounded border border-border">
            📍 {location.address.split(",")[0]}
          </div>
        </div>

        {/* Address and details */}
        <div className="space-y-1.5 text-xs">
          <div className="flex items-start justify-between gap-2">
            <span className="text-muted-foreground shrink-0 font-medium">Exact Coordinates:</span>
            <span className="font-mono text-foreground text-right">{location.lat.toFixed(5)}° N, {location.lon.toFixed(5)}° E</span>
          </div>
          <div className="flex items-start justify-between gap-2">
            <span className="text-muted-foreground shrink-0 font-medium">Geocoded Landmark:</span>
            <span className="text-foreground text-right font-medium">{location.address}</span>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-border flex items-center gap-2">
        <a
          href={mapsUrl}
          target="_blank"
          rel="noreferrer noopener"
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-primary hover:bg-primary/90 text-white text-xs font-semibold shadow-sm transition-all"
        >
          <Navigation className="h-3.5 w-3.5" />
          <span>Open Google Maps Directions</span>
          <ExternalLink className="h-3 w-3 opacity-70" />
        </a>
      </div>
    </div>
  )
}
