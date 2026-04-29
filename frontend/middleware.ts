import { type NextRequest, NextResponse } from "next/server"

export function middleware(request: NextRequest) {
  const tieneTokenCliente = !!request.cookies.get("sgs-auth")?.value
  const tieneRefreshToken = !!request.cookies.get("refresh_token")?.value
  const tieneToken = tieneTokenCliente || tieneRefreshToken
  const pathname = request.nextUrl.pathname

  const estaEnLogin = pathname.startsWith("/login")

  if (!tieneToken && !estaEnLogin) {
    return NextResponse.redirect(new URL("/login", request.url))
  }

  // Autenticado en login → al inicio (el cliente decide overview o cuentas por rol)
  if (tieneToken && estaEnLogin) {
    return NextResponse.redirect(new URL("/", request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    "/",
    "/overview/:path*",
    "/pipeline/:path*",
    "/equipo/:path*",
    "/productos/:path*",
    "/copilot/:path*",
    "/voice/:path*",
    "/alertas/:path*",
    "/cuentas/:path*",
    "/clientes/:path*",
    "/perfil/:path*",
    "/notas/:path*",
    "/documentos/:path*",
    "/informes/:path*",
    "/deck/:path*",
    "/forecast/:path*",
    "/importacion/:path*",
    "/configuracion/:path*",
    "/admin/:path*",
    "/login",
  ],
}
