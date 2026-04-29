"use client"

import { Menu } from "lucide-react"
import { useAppStore } from "@/store/use-app-store"

export function MobileNavbar() {
  const toggleSidebar = useAppStore((s) => s.toggleSidebar)

  return (
    <div className="lg:hidden fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-4 h-12 bg-white border-b border-zinc-200">
      <span className="text-base font-bold tracking-tight text-sgs-rojo">SGS</span>
      <button
        onClick={toggleSidebar}
        className="p-1.5 rounded-md text-zinc-600 hover:bg-zinc-100 transition-colors"
        aria-label="Abrir menú"
      >
        <Menu size={20} />
      </button>
    </div>
  )
}
