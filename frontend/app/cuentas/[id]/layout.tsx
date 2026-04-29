interface CuentaDetalleLayoutProps {
  children: React.ReactNode
}

/**
 * El shell global (sidebar + estructura) ya se aplica en /cuentas/layout.tsx.
 * En el detalle no debe volver a envolverse para evitar sidebar duplicado.
 */
export default function CuentaDetalleLayout({ children }: CuentaDetalleLayoutProps) {
  return <>{children}</>
}
