import type { Metadata } from "next"
import Script from "next/script"
import { Providers } from "@/components/providers"
import "./globals.css"

export const metadata: Metadata = {
  title: "SGS España — Inteligencia Comercial",
  description: "Plataforma de análisis del pipeline comercial",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className="antialiased app-bg">
        <Script id="sgs-theme-init" strategy="beforeInteractive">
          {`
            (function() {
              try {
                var mode = localStorage.getItem('sgs-theme-mode') || 'dark';
                var isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                var resolved = mode === 'system' ? (isDark ? 'dark' : 'light') : mode;
                document.documentElement.setAttribute('data-theme', resolved);
              } catch (e) {
                document.documentElement.setAttribute('data-theme', 'dark');
              }
            })();
          `}
        </Script>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
