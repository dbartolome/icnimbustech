"use client"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useState } from "react"
import { Toaster } from "sonner"
import { CommandPalette } from "@/components/command-palette"

export function Providers({ children }: { children: React.ReactNode }) {
  // QueryClient único por sesión de navegador para reutilizar caché entre rutas.
  const [queryClient] = useState(
    () => new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 5 * 60 * 1000,
          retry: 1,
        },
      },
    })
  )

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <CommandPalette />
      <Toaster
        position="bottom-right"
        richColors
        closeButton
        toastOptions={{
          duration: 4000,
          classNames: {
            toast: "font-sans text-sm",
          },
        }}
      />
    </QueryClientProvider>
  )
}
