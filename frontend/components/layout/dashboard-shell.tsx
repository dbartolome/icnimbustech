"use client"

import { Sidebar } from "@/components/layout/sidebar"
import { MobileNavbar } from "@/components/layout/mobile-navbar"
import { PageTransition } from "@/components/page-transition"

export function DashboardShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-shell min-h-screen">
      {/* Barra superior mobile: logo + hamburguesa */}
      <MobileNavbar />

      {/* Sidebar: fixed siempre, overlay en mobile */}
      <Sidebar />

      {/* Contenido: margen izquierdo solo en desktop */}
      <div className="pt-12 lg:pt-0 lg:ml-56 min-h-screen flex flex-col">
        <PageTransition>{children}</PageTransition>
      </div>
    </div>
  )
}
