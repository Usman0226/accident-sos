import { ThemeProvider } from "@/components/theme-provider"
import { AppShell } from "@/components/layouts/AppShell"
import { DashboardOverview } from "@/components/dashboard/DashboardOverview"
import { DashboardProvider } from "@/context/DashboardContext"
import './index.css'

function App() {
  return (
    <ThemeProvider defaultTheme="light" storageKey="accident-sos-theme">
      <DashboardProvider>
        <AppShell>
          <DashboardOverview />
        </AppShell>
      </DashboardProvider>
    </ThemeProvider>
  )
}

export default App
