import { 
  AlertTriangle, 
  MapPin, 
  Activity, 
  Cpu, 
  History,
  Zap
} from "lucide-react"
import {
  AnimatedSidebar,
  AnimatedSidebarContent,
  AnimatedSidebarFooter,
  AnimatedSidebarGroup,
  AnimatedSidebarGroupLabel,
  AnimatedSidebarGroupContent,
  AnimatedSidebarHeader,
  AnimatedSidebarMenu,
  AnimatedSidebarMenuButton,
  AnimatedSidebarMenuItem,
  useAnimatedSidebar,
} from "@/components/motion/animated-sidebar"
import { useDashboard } from "@/context/DashboardContext"

export function Sidebar() {
  const { state } = useAnimatedSidebar()
  const { activeTab, setActiveTab, activeAlert, devices } = useDashboard()

  const navItems = [
    { 
      id: "emergency" as const, 
      icon: AlertTriangle, 
      label: "Live Emergency", 
      badge: activeAlert ? "1 ACTIVE" : undefined,
      badgeColor: "bg-destructive text-white" 
    },
    { 
      id: "map" as const, 
      icon: MapPin, 
      label: "GPS Navigation",
      badge: "3D Fix",
      badgeColor: "bg-accent/15 text-accent"
    },
    { 
      id: "telemetry" as const, 
      icon: Activity, 
      label: "Sensor Fusion",
      badge: "100 Hz",
      badgeColor: "bg-muted text-muted-foreground"
    },
    { 
      id: "fleet" as const, 
      icon: Cpu, 
      label: "Hardware Fleet",
      badge: `${devices.length} Nodes`,
      badgeColor: "bg-muted text-muted-foreground"
    },
    { 
      id: "history" as const, 
      icon: History, 
      label: "Incident Logs" 
    },
  ]

  return (
    <AnimatedSidebar variant="sidebar" collapsible="icon">
      <AnimatedSidebarHeader className="h-14 flex justify-center border-b border-border">
        <div className="flex items-center gap-3 overflow-hidden px-2">
          <div className="h-8 w-8 rounded-lg bg-primary/15 text-primary flex shrink-0 items-center justify-center">
            <Zap className="h-5 w-5 stroke-[2.5]" />
          </div>
          {state === "expanded" && (
            <div className="flex flex-col">
              <span className="whitespace-nowrap text-base font-bold text-foreground tracking-tight font-display">
                Accident SOS
              </span>
              <span className="text-[10px] text-muted-foreground -mt-1 font-mono uppercase tracking-wider">
                Emergency Hub
              </span>
            </div>
          )}
        </div>
      </AnimatedSidebarHeader>

      <AnimatedSidebarContent>
        <AnimatedSidebarGroup>
          <AnimatedSidebarGroupLabel>Responder Console</AnimatedSidebarGroupLabel>
          <AnimatedSidebarGroupContent>
            <AnimatedSidebarMenu>
              {navItems.map((item) => {
                const Icon = item.icon
                const isActive = activeTab === item.id

                return (
                  <AnimatedSidebarMenuItem key={item.id}>
                    <AnimatedSidebarMenuButton 
                      isActive={isActive}
                      icon={<Icon className={`h-4 w-4 stroke-[2px] ${isActive ? "text-primary" : "text-muted-foreground/70"}`} />}
                      badge={
                        item.badge ? (
                          <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded-full font-bold ${item.badgeColor}`}>
                            {item.badge}
                          </span>
                        ) : null
                      }
                      onSelect={() => setActiveTab(item.id)}
                    >
                      <span className={isActive ? "font-semibold text-foreground" : "font-medium text-muted-foreground/80"}>
                        {item.label}
                      </span>
                    </AnimatedSidebarMenuButton>
                  </AnimatedSidebarMenuItem>
                )
              })}
            </AnimatedSidebarMenu>
          </AnimatedSidebarGroupContent>
        </AnimatedSidebarGroup>
      </AnimatedSidebarContent>

      <AnimatedSidebarFooter>
        <AnimatedSidebarMenu>
          <AnimatedSidebarMenuItem>
            <div className="px-2 py-1.5 flex items-center justify-between text-[11px] text-muted-foreground bg-muted/50 rounded-lg border border-border">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
                <span>ESP32 Telemetry</span>
              </div>
              <span className="font-mono text-[10px] text-accent font-semibold">ONLINE</span>
            </div>
          </AnimatedSidebarMenuItem>
        </AnimatedSidebarMenu>
      </AnimatedSidebarFooter>
    </AnimatedSidebar>
  )
}
