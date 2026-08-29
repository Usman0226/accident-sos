import { MapContainer, TileLayer, Marker, Popup, Circle } from "react-leaflet"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import { MapPin, Navigation, Compass, ExternalLink, Radio, Building2 } from "lucide-react"
import { useDashboard } from "@/context/DashboardContext"

// Custom marker icons
const createCustomIcon = (color: string, label: string) => {
  return L.divIcon({
    className: "custom-leaflet-marker",
    html: `
      <div style="
        background: ${color};
        color: white;
        border: 2px solid white;
        border-radius: 50%;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        font-weight: bold;
        font-size: 11px;
      ">
        ${label}
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  })
}

export function MapView() {
  const { activeAlert, devices } = useDashboard()

  const activeLat = activeAlert?.location.lat || 28.6139
  const activeLon = activeAlert?.location.lon || 77.2090
  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${activeLat},${activeLon}`

  return (
    <div className="w-full max-w-[1440px] mx-auto p-4 sm:p-6 space-y-5">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-2xl border border-border bg-card shadow-sm">
        <div>
          <h2 className="text-lg font-bold text-foreground tracking-tight font-display flex items-center gap-2">
            <MapPin className="h-5 w-5 text-primary" />
            Tactical GPS Navigation & Fleet Map
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Real-time geospatial tracking with u-blox Neo-6M GPS sensor feeds and emergency routing
          </p>
        </div>

        <div className="flex items-center gap-2">
          <a
            href={mapsUrl}
            target="_blank"
            rel="noreferrer noopener"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-primary hover:bg-primary/90 text-white text-xs font-semibold shadow-sm transition-all"
          >
            <Navigation className="h-3.5 w-3.5" />
            <span>Open in Google Maps</span>
            <ExternalLink className="h-3 w-3 opacity-70" />
          </a>
        </div>
      </div>

      {/* Main Map Container & Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Interactive Leaflet Map (8 cols) */}
        <div className="lg:col-span-8 rounded-2xl border border-border bg-card overflow-hidden shadow-sm relative h-[520px]">
          <MapContainer
            center={[activeLat, activeLon]}
            zoom={13}
            scrollWheelZoom={true}
            style={{ height: "100%", width: "100%", zIndex: 1 }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {/* Impact Zone Danger Radius */}
            {activeAlert && (
              <Circle
                center={[activeLat, activeLon]}
                radius={250}
                pathOptions={{ color: "#c64545", fillColor: "#c64545", fillOpacity: 0.2 }}
              />
            )}

            {/* Active SOS Pin */}
            <Marker
              position={[activeLat, activeLon]}
              icon={createCustomIcon("#c64545", "SOS")}
            >
              <Popup>
                <div className="p-1 space-y-1 text-xs">
                  <div className="font-bold text-red-600">🚨 Severe Impact Incident</div>
                  <div className="font-medium text-black">Rahul Sharma · KTM Duke 390</div>
                  <div className="text-gray-600 text-[11px]">{activeAlert?.location.address}</div>
                  <div className="text-gray-500 font-mono text-[10px]">{activeLat.toFixed(4)}° N, {activeLon.toFixed(4)}° E</div>
                </div>
              </Popup>
            </Marker>

            {/* Other Devices */}
            {devices
              .filter((d) => d.device_id !== "VEH_002" && d.last_gps_lat && d.last_gps_lon)
              .map((d) => (
                <Marker
                  key={d.device_id}
                  position={[d.last_gps_lat, d.last_gps_lon]}
                  icon={createCustomIcon(d.status === "unreachable" ? "#888888" : "#5db8a6", d.device_id.replace("VEH_", ""))}
                >
                  <Popup>
                    <div className="p-1 text-xs space-y-0.5 text-black">
                      <div className="font-bold">{d.rider_name || d.device_id}</div>
                      <div className="text-[11px] text-gray-600">Status: {d.status}</div>
                      <div className="text-[11px] text-gray-600">Battery: {d.battery_pct}%</div>
                    </div>
                  </Popup>
                </Marker>
              ))}
          </MapContainer>

          {/* Floating Map Overlay Badge */}
          <div className="absolute top-3 right-3 z-[1000] bg-background/90 backdrop-blur-sm px-3 py-1.5 rounded-xl border border-border shadow-md text-xs font-mono flex items-center gap-2">
            <Radio className="h-3.5 w-3.5 text-primary animate-pulse" />
            <span>GPS Fix: 8 Sats · RTK Lock</span>
          </div>
        </div>

        {/* Location Intelligence Panel (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          {/* Target Location Card */}
          <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground tracking-tight flex items-center gap-2">
                <Compass className="h-4 w-4 text-primary" />
                Coordinates & Geofence
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-destructive/15 text-destructive font-bold uppercase">
                Active Crash Pin
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="p-3 rounded-xl bg-background/80 border border-border space-y-1">
                <span className="text-muted-foreground text-[11px]">Exact Incident Landmark:</span>
                <p className="font-semibold text-foreground text-xs leading-snug">
                  {activeAlert?.location.address || "Ring Road, Near AIIMS Flyover, New Delhi"}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 rounded-xl bg-background/60 border border-border">
                  <span className="text-[10px] text-muted-foreground block">Latitude</span>
                  <span className="font-mono text-xs font-bold text-foreground">{activeLat.toFixed(5)}° N</span>
                </div>
                <div className="p-2.5 rounded-xl bg-background/60 border border-border">
                  <span className="text-[10px] text-muted-foreground block">Longitude</span>
                  <span className="font-mono text-xs font-bold text-foreground">{activeLon.toFixed(5)}° E</span>
                </div>
              </div>
            </div>
          </div>

          {/* Nearest Emergency Facilities */}
          <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-3">
            <h3 className="text-sm font-semibold text-foreground tracking-tight flex items-center gap-2">
              <Building2 className="h-4 w-4 text-accent" />
              Nearest Trauma Centers & Services
            </h3>

            <div className="space-y-2 text-xs">
              <div className="p-2.5 rounded-xl bg-background/80 border border-border flex items-center justify-between">
                <div>
                  <span className="font-semibold text-foreground block">AIIMS Trauma Centre</span>
                  <span className="text-[11px] text-muted-foreground">Emergency Ward · 1.2 km away</span>
                </div>
                <a
                  href="tel:112"
                  className="px-2.5 py-1 rounded-lg bg-primary/10 text-primary text-[11px] font-medium hover:bg-primary/20 transition-colors"
                >
                  Dial Unit
                </a>
              </div>

              <div className="p-2.5 rounded-xl bg-background/80 border border-border flex items-center justify-between">
                <div>
                  <span className="font-semibold text-foreground block">Safdarjung Hospital</span>
                  <span className="text-[11px] text-muted-foreground">Level 1 Emergency · 2.4 km away</span>
                </div>
                <a
                  href="tel:112"
                  className="px-2.5 py-1 rounded-lg bg-primary/10 text-primary text-[11px] font-medium hover:bg-primary/20 transition-colors"
                >
                  Dial Unit
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
