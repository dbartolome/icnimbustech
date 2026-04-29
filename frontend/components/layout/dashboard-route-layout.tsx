import { DashboardShell } from "@/components/layout/dashboard-shell"

interface DashboardRouteLayoutProps {
  children: React.ReactNode
}

/**
 * Layout base para todas las secciones privadas del dashboard.
 * Centraliza la composición shell (sidebar + contenido) en un único punto.
 */
export default function DashboardRouteLayout({ children }: DashboardRouteLayoutProps) {
  return <DashboardShell>{children}</DashboardShell>
}
