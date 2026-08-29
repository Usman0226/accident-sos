import type { ReactNode } from "react"
import { Sidebar } from "./Sidebar"
import { TopNavbar } from "./TopNavbar"
import { AnimatedSidebarProvider, AnimatedSidebarInset, AnimatedSidebarTrigger } from "@/components/motion/animated-sidebar"
import { Menu } from "lucide-react"

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <AnimatedSidebarProvider>
      <Sidebar />
      <AnimatedSidebarInset>
        {/* Main Content Area */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden bg-background">
          {/* Top Navbar */}
          <TopNavbar trigger={
            <AnimatedSidebarTrigger className="md:hidden">
              <Menu className="h-5 w-5" />
            </AnimatedSidebarTrigger>
          } />

          {/* Page Content */}
          <main className="flex-1 overflow-y-auto">
            <div className="w-full">
              {children}
            </div>
          </main>
        </div>
      </AnimatedSidebarInset>
    </AnimatedSidebarProvider>
  )
}
