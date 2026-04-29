"use client"

import { useEffect, useState } from "react"
import { usePathname } from "next/navigation"
import { HelpCircle, X } from "lucide-react"
import { cn } from "@/lib/utils"

// =============================================================================
// Contenido de ayuda por ruta
// =============================================================================

interface SeccionAyuda {
  titulo: string
  subtitulo: string
  secciones: Array<{
    icono: string
    titulo: string
    texto: string
  }>
  consejos?: string[]
}

const AYUDA: Record<string, SeccionAyuda> = {
  "/overview": {
    titulo: "Dashboard",
    subtitulo: "Vista general del pipeline comercial de SGS España",
    secciones: [
      {
        icono: "▦",
        titulo: "KPIs principales",
        texto: "Los 4 indicadores clave: Pipeline activo (€ en oportunidades abiertas), Win Rate global (% de cierre), Importe ganado e Importe perdido. Se calculan en tiempo real desde la base de datos.",
      },
      {
        icono: "📈",
        titulo: "Evolución mensual",
        texto: "Gráfico de barras con las oportunidades creadas y ganadas por mes. Permite identificar tendencias estacionales y picos de actividad comercial.",
      },
      {
        icono: "◈",
        titulo: "Breakdown por SBU",
        texto: "Tabla comparativa de rendimiento por Strategic Business Unit. Muestra pipeline activo, importe ganado y win rate de cada unidad de negocio.",
      },
      {
        icono: "⚠",
        titulo: "Toggle 'Incluyendo ops fantasma'",
        texto: "Filtra las 293 oportunidades con importe 0€ que distorsionan los KPIs. Actívalo para ver los datos reales del negocio sin ruido estadístico.",
      },
    ],
    consejos: [
      "Usa el toggle 'Solo datos reales' para un análisis más preciso del rendimiento",
      "El win rate global incluye todas las oportunidades cerradas (ganadas + perdidas)",
    ],
  },

  "/pipeline": {
    titulo: "Pipeline",
    subtitulo: "Gestión y seguimiento de oportunidades comerciales",
    secciones: [
      {
        icono: "◈",
        titulo: "Funnel de etapas",
        texto: "Visualización del embudo de ventas con el número de oportunidades y el importe total en cada etapa: Discover → Propose → Negotiate → Closed. Permite identificar cuellos de botella.",
      },
      {
        icono: "📋",
        titulo: "Tabla de oportunidades",
        texto: "Listado completo de oportunidades con filtros por etapa, SBU y búsqueda por nombre. Cada fila muestra nombre, cuenta, importe, etapa y fecha de decisión.",
      },
      {
        icono: "✦",
        titulo: "Nueva oportunidad con IC",
        texto: "El botón '+ Nueva oportunidad' abre un modal con autocompletado de IC. Escribe el nombre de la oportunidad y IC sugiere automáticamente la Business Line y el Canal de Venta más probables, con un índice de confianza.",
      },
    ],
    consejos: [
      "La sugerencia de IC se activa automáticamente 800ms después de escribir el nombre",
      "El badge de confianza: verde ≥80%, naranja 60-79%, gris <60% (revisar manualmente)",
      "Puedes ignorar la sugerencia y rellenar los campos manualmente",
    ],
  },

  "/equipo": {
    titulo: "Equipo",
    subtitulo: "Ranking y rendimiento del equipo comercial",
    secciones: [
      {
        icono: "◫",
        titulo: "Ranking de comerciales",
        texto: "Tabla ordenada por importe ganado. Muestra para cada comercial: número de oportunidades, tasa de cierre (win rate), pipeline activo y comparativa con la media del equipo.",
      },
      {
        icono: "📊",
        titulo: "Métricas individuales",
        texto: "Win rate individual, oportunidades abiertas, cerradas ganadas y perdidas. Permite identificar los mejores performers y los que necesitan soporte.",
      },
    ],
    consejos: [
      "El win rate se calcula sobre oportunidades cerradas (won + lost), no las abiertas",
      "Un comercial con 100% WR pero pocas oportunidades puede indicar baja actividad prospectora",
    ],
  },

  "/productos": {
    titulo: "Productos",
    subtitulo: "Análisis de rendimiento por producto y certificación",
    secciones: [
      {
        icono: "◆",
        titulo: "Tabla de productos",
        texto: "Análisis de cada producto/certificación: número de oportunidades totales y ganadas, importe total ganado, ticket medio y win rate. Ordenado por importe ganado descendente.",
      },
      {
        icono: "📈",
        titulo: "Gráfico de comparativa",
        texto: "Visualización comparativa de win rate y volumen entre productos. Permite identificar los productos más rentables y los que tienen mayor potencial de mejora.",
      },
    ],
    consejos: [
      "IDI Proyectos tiene el win rate más alto (98,1%) — analiza qué lo diferencia",
      "ISO 9001:2015 tiene el mayor volumen — priorizar cross-selling con clientes existentes",
    ],
  },

  "/copilot": {
    titulo: "IC Copilot",
    subtitulo: "Asistente de inteligencia comercial con contexto del pipeline",
    secciones: [
      {
        icono: "✦",
        titulo: "Chat con contexto real",
        texto: "El Copilot tiene acceso a todos los KPIs del pipeline, el catálogo de servicios SGS y la matriz sectorial. Puedes preguntarle sobre oportunidades, rendimiento, recomendaciones comerciales o estrategia.",
      },
      {
        icono: "◎",
        titulo: "Sugerencias rápidas",
        texto: "Los botones de sugerencia en la pantalla inicial te permiten hacer preguntas frecuentes con un solo clic. Son un buen punto de partida si no sabes por dónde empezar.",
      },
      {
        icono: "⚙",
        titulo: "Proveedor IC",
        texto: "Por defecto usa Anthropic Claude. Si tienes Ollama instalado localmente, puedes cambiarlo en Configuración → Proveedor. El copilot usa streaming para mostrar la respuesta en tiempo real.",
      },
    ],
    consejos: [
      "Pregunta: '¿Cuáles son los productos con mejor win rate?' o 'Analiza el pipeline de Q1'",
      "El contexto se reconstruye en cada conversación — no recuerda chats anteriores",
      "Cambia el proveedor IC en /configuracion para usar tu instancia de Ollama local",
    ],
  },

  "/voice": {
    titulo: "Voice Studio",
    subtitulo: "Generación de briefings de audio para el equipo directivo",
    secciones: [
      {
        icono: "◎",
        titulo: "Briefing de voz",
        texto: "Genera un script de 300-450 palabras (2-3 minutos de lectura) con los datos clave del pipeline: KPIs, top productos, top comerciales y estado del funnel.",
      },
      {
        icono: "▶",
        titulo: "Reproducción TTS",
        texto: "El script generado se puede reproducir directamente con la voz del sistema (Web Speech API). Puedes pausar, reanudar y detener la reproducción en cualquier momento.",
      },
      {
        icono: "🎯",
        titulo: "Focos temáticos",
        texto: "Elige el foco del briefing: General (visión completa), Productos (análisis por certificación), Equipo (rendimiento comercial) o Pipeline (estado del funnel y riesgos).",
      },
    ],
    consejos: [
      "El briefing no usa markdown ni símbolos — está optimizado para lectura en voz alta",
      "Cambia el proveedor IC en /configuracion para generar con Ollama local",
      "Ideal para escuchar en el coche o durante el desplazamiento a una reunión",
    ],
  },

  "/alertas": {
    titulo: "Alertas",
    subtitulo: "Centro de notificaciones y alertas del pipeline",
    secciones: [
      {
        icono: "◬",
        titulo: "Tipos de alerta",
        texto: "Tres niveles: Crítico (rojo, acción inmediata), Seguimiento (naranja, monitorizar) y Oportunidad (verde, acción proactiva). Las alertas pueden ser generadas por el sistema o manualmente.",
      },
      {
        icono: "✓",
        titulo: "Resolver alertas",
        texto: "Marca una alerta como resuelta cuando se haya tomado la acción correspondiente. Las alertas resueltas se mantienen en el historial para trazabilidad.",
      },
    ],
    consejos: [
      "Las alertas críticas indican oportunidades con fecha de decisión próxima sin avance",
      "Revisa el centro de alertas al inicio de cada jornada",
    ],
  },

  "/perfil": {
    titulo: "Mi Perfil",
    subtitulo: "Información personal, objetivos y configuración de notificaciones",
    secciones: [
      {
        icono: "◯",
        titulo: "Datos personales",
        texto: "Nombre, email, teléfono, zona geográfica y SBU principal. El nombre en el campo 'Nombre en CSV' es clave — debe coincidir exactamente con 'Opportunity Owner' en los exports de Salesforce para que las oportunidades se asignen correctamente.",
      },
      {
        icono: "🎯",
        titulo: "Objetivos comerciales",
        texto: "Define y sigue tus objetivos de pipeline, win rate y oportunidades ganadas. El progreso se actualiza automáticamente con los datos reales del pipeline.",
      },
      {
        icono: "🔔",
        titulo: "Notificaciones",
        texto: "Configura el briefing diario (hora de envío), el umbral de alerta para win rate y las preferencias de voz TTS para el Voice Studio.",
      },
    ],
    consejos: [
      "El 'Nombre en CSV' es crítico para la importación — escríbelo exactamente como aparece en Salesforce",
      "El win rate personal se calcula solo con tus oportunidades cerradas",
    ],
  },

  "/cuentas": {
    titulo: "Mis Cuentas",
    subtitulo: "Portfolio de cuentas cliente con inteligencia comercial",
    secciones: [
      {
        icono: "◉",
        titulo: "Lista de cuentas",
        texto: "Todas las cuentas con oportunidades en el pipeline, ordenadas por pipeline activo. Busca por nombre con el campo de búsqueda. Cada cuenta muestra: oportunidades activas, pipeline total e importe ganado.",
      },
      {
        icono: "📋",
        titulo: "Tab Oportunidades",
        texto: "Al seleccionar una cuenta, el panel lateral muestra el detalle de todas sus oportunidades con etapa, importe y fecha de decisión.",
      },
      {
        icono: "✦",
        titulo: "Tab Cross-Selling",
        texto: "Inteligencia de cross-selling para las 77 cuentas más estratégicas. Muestra: servicio actual, oportunidades de venta cruzada, mensaje comercial personalizado y preguntas de discovery para la próxima reunión.",
      },
    ],
    consejos: [
      "El badge de confianza en Cross-Selling indica la probabilidad de éxito de la recomendación",
      "Las preguntas de discovery están diseñadas para detectar necesidades no cubiertas",
      "Solo las 77 cuentas del ranking tienen inteligencia de cross-selling disponible",
    ],
  },

  "/notas": {
    titulo: "Notas de Voz",
    subtitulo: "Grabación y transcripción de notas comerciales",
    secciones: [
      {
        icono: "◐",
        titulo: "Grabar nota",
        texto: "Graba notas de voz directamente desde el navegador (requiere permiso de micrófono). La nota se transcribe automáticamente y se puede asociar a una oportunidad del pipeline.",
      },
      {
        icono: "📝",
        titulo: "Gestión de notas",
        texto: "Lista de todas tus notas con transcripción completa, duración y la oportunidad asociada. Puedes buscar por contenido y eliminar las que ya no necesites.",
      },
    ],
    consejos: [
      "Ideal para capturar ideas después de una reunión sin interrumpir el flujo",
      "La transcripción es automática — revísala si el audio tenía ruido de fondo",
    ],
  },

  "/documentos": {
    titulo: "Documentos",
    subtitulo: "Repositorio de documentos comerciales por oportunidad",
    secciones: [
      {
        icono: "◧",
        titulo: "Subir documentos",
        texto: "Sube cualquier documento (PDF, Word, Excel, imágenes) asociándolo a una oportunidad del pipeline. Límite: 20MB por archivo.",
      },
      {
        icono: "🔍",
        titulo: "Buscar y descargar",
        texto: "Filtra documentos por oportunidad o busca por nombre. Descarga los documentos directamente desde el listado.",
      },
    ],
    consejos: [
      "Asociar documentos a oportunidades facilita el traspaso entre comerciales",
      "Sube las propuestas enviadas para tener un histórico completo",
    ],
  },

  "/informes": {
    titulo: "Informes PDF",
    subtitulo: "Generación automática de informes ejecutivos con IC",
    secciones: [
      {
        icono: "📊",
        titulo: "Tipos de informe",
        texto: "Cuatro tipos disponibles: Ejecutivo mensual (KPIs globales), Análisis de comercial (rendimiento individual), Propuesta para cliente (orientado a cuenta específica) y Revisión de pipeline (funnel completo).",
      },
      {
        icono: "🏢",
        titulo: "Empresa destinataria",
        texto: "Selecciona la empresa cliente del listado de cuentas. El informe incluirá el nombre de la empresa en la portada y contextualizará el análisis.",
      },
      {
        icono: "✦",
        titulo: "Generación con IC",
        texto: "IC genera el índice de secciones y el contenido analítico de cada una basándose en los datos reales de tu pipeline. El proceso tarda 30-60 segundos y puedes seguir el progreso en tiempo real.",
      },
      {
        icono: "📄",
        titulo: "Descarga PDF",
        texto: "Una vez completado, descarga el informe como PDF listo para enviar. Los informes se guardan en tu historial y puedes descargarlo de nuevo en cualquier momento.",
      },
    ],
    consejos: [
      "Añade contexto adicional para que IC personalice mejor el informe",
      "El informe ejecutivo mensual es el más completo para presentaciones a dirección",
      "Cambia el proveedor IC en /configuracion para generar con Ollama local",
    ],
  },

  "/deck": {
    titulo: "Deck de Visita",
    subtitulo: "Presentaciones comerciales personalizadas generadas con IC",
    secciones: [
      {
        icono: "⬡",
        titulo: "Personalización",
        texto: "Introduce la empresa cliente, sector, norma/certificación objetivo y tipo de visita (primera visita, seguimiento, upselling o propuesta técnica). IC adapta el contenido a estos parámetros.",
      },
      {
        icono: "✦",
        titulo: "Generación con IC",
        texto: "IC genera el contenido de cada slide: puntos clave concisos y nota del presentador (guía para el comercial). Usa el catálogo real de SGS y los pain points del sector para enriquecer el contenido.",
      },
      {
        icono: "⬇",
        titulo: "Descarga PPTX",
        texto: "El resultado es un archivo PowerPoint (.pptx) con diseño corporativo SGS (rojo #C0001A, tipografía Calibri). Descárgalo y edita los slides antes de la reunión.",
      },
    ],
    consejos: [
      "Sé específico en 'Objetivo de la visita' — cuanto más contexto, mejor el contenido",
      "La nota del presentador en cada slide te guía sobre qué decir sin leer el slide",
      "El deck está en formato 16:9 widescreen — compatible con cualquier proyector",
    ],
  },

  "/admin/usuarios": {
    titulo: "Gestión de Usuarios",
    subtitulo: "Administración de cuentas, roles y permisos",
    secciones: [
      {
        icono: "◈",
        titulo: "Roles de usuario",
        texto: "Tres roles: Admin (acceso total), Manager (puede ver todo el equipo e importar datos) y Comercial (solo ve sus propios datos). Los permisos se asignan automáticamente según el rol.",
      },
      {
        icono: "👤",
        titulo: "Crear y editar usuarios",
        texto: "Crea nuevos usuarios con email, nombre completo y rol. El campo 'Nombre CSV' debe coincidir exactamente con el campo 'Opportunity Owner' en los exports de Salesforce.",
      },
      {
        icono: "🔒",
        titulo: "Permisos granulares",
        texto: "Además del rol base, puedes configurar permisos individuales: ver equipo, ver todos el pipeline, gestionar alertas, importar datos y ver informes ejecutivos.",
      },
    ],
    consejos: [
      "El 'Nombre CSV' es crítico — error aquí significa que las oportunidades no se asignarán al usuario",
      "Un Manager solo ve los comerciales de sus SBUs asignados",
    ],
  },

  "/admin/importacion": {
    titulo: "Importación CSV",
    subtitulo: "Carga masiva de oportunidades desde Salesforce",
    secciones: [
      {
        icono: "📂",
        titulo: "Formato del CSV",
        texto: "El archivo debe ser un export de Salesforce con las columnas: Opportunity Name, Strategic Business Unit, Business Line, Product Name, Account Name, Canal de Venta, Opportunity Owner, Amount, Created Date, Stage, Opportunity ID.",
      },
      {
        icono: "🔄",
        titulo: "Modo Upsert vs Append",
        texto: "Upsert: crea oportunidades nuevas Y actualiza las existentes (mismo Opportunity ID). Append: solo inserta las nuevas, ignora las existentes. Usa Upsert para actualizaciones periódicas.",
      },
      {
        icono: "✓",
        titulo: "Validación automática",
        texto: "El sistema valida Business Lines (13 valores oficiales) y Canales de Venta (4 valores) antes de insertar. Los errores se muestran fila por fila para que puedas corregir el CSV.",
      },
    ],
    consejos: [
      "Exporta desde Salesforce en UTF-8 para evitar problemas con caracteres especiales",
      "Las 293 oportunidades con importe 0€ se importan pero se filtran en el modo 'Solo datos reales'",
      "El historial guarda las últimas 20 importaciones con estadísticas detalladas",
    ],
  },

  "/configuracion": {
    titulo: "Configuración IC",
    subtitulo: "Selección del motor de Inteligencia Comercial",
    secciones: [
      {
        icono: "✦",
        titulo: "Anthropic Claude",
        texto: "El modelo por defecto (claude-sonnet-4-20250514). Requiere conexión a internet y la API key configurada en el servidor. Es el más capaz para generación de JSON estructurado (Informes, Decks).",
      },
      {
        icono: "◎",
        titulo: "Ollama local",
        texto: "Ejecuta modelos IC en tu propia máquina sin coste y sin internet. Requiere tener Ollama instalado y corriendo en tu equipo. Usa 'Conectar' para ver los modelos disponibles.",
      },
      {
        icono: "⚡",
        titulo: "Botón 'Probar IC'",
        texto: "Lanza un test real con la configuración actual (la que ves en pantalla, aunque no la hayas guardado). Pregunta el win rate global del pipeline y muestra la respuesta en streaming para verificar que funciona.",
      },
    ],
    consejos: [
      "Guarda la configuración antes de ir a otras páginas — se persiste en localStorage",
      "Para Informes y Decks con Ollama, usa modelos con buen seguimiento de instrucciones: llama3.2, qwen2.5, mistral",
      "Modelos pequeños (<3B) pueden fallar en la generación de JSON estructurado de los Informes",
    ],
  },
}

const AYUDA_DEFECTO: SeccionAyuda = {
  titulo: "Ayuda",
  subtitulo: "SGS España — Inteligencia Comercial",
  secciones: [
    {
      icono: "ℹ",
      titulo: "Navegación",
      texto: "Usa el menú lateral para moverte entre las secciones de la plataforma. El sidebar filtra automáticamente las secciones según tu rol.",
    },
  ],
}

// =============================================================================
// Componente modal
// =============================================================================

interface HelpModalProps {
  abierto: boolean
  onCerrar: () => void
}

function HelpModal({ abierto, onCerrar }: HelpModalProps) {
  const pathname = usePathname()
  const ayuda = AYUDA[pathname] ?? AYUDA_DEFECTO

  useEffect(() => {
    if (!abierto) return
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onCerrar() }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [abierto, onCerrar])

  if (!abierto) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-end"
      onClick={onCerrar}
    >
      {/* Overlay semitransparente */}
      <div className="absolute inset-0 overlay-strong backdrop-blur-sm" />

      {/* Panel */}
      <div
        className="relative mt-3 sm:mt-14 mr-2 sm:mr-4 w-[calc(100vw-1rem)] sm:w-[420px] max-h-[calc(100vh-1.5rem)] sm:max-h-[calc(100vh-5rem)] overflow-y-auto bg-white rounded-2xl shadow-2xl border border-zinc-200 flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Cabecera */}
        <div className="sticky top-0 bg-white px-5 pt-5 pb-3 border-b border-zinc-100 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-zinc-900">{ayuda.titulo}</h2>
            <p className="text-xs text-zinc-500 mt-0.5">{ayuda.subtitulo}</p>
          </div>
          <button
            onClick={onCerrar}
            className="shrink-0 w-7 h-7 flex items-center justify-center rounded-full hover:bg-zinc-100 text-zinc-400 hover:text-zinc-700 transition-colors"
          >
            <X size={14} />
          </button>
        </div>

        {/* Secciones */}
        <div className="px-5 py-4 space-y-4">
          {ayuda.secciones.map((s) => (
            <div key={s.titulo} className="flex gap-3">
              <span className="shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-red-50 text-sgs-rojo text-sm">
                {s.icono}
              </span>
              <div>
                <p className="text-sm font-semibold text-zinc-800">{s.titulo}</p>
                <p className="text-xs text-zinc-600 leading-relaxed mt-0.5">{s.texto}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Consejos */}
        {ayuda.consejos && ayuda.consejos.length > 0 && (
          <div className="mx-5 mb-5 bg-amber-50 rounded-xl p-4">
            <p className="text-xs font-semibold text-amber-800 mb-2">💡 Consejos</p>
            <ul className="space-y-1.5">
              {ayuda.consejos.map((c, i) => (
                <li key={i} className="text-xs text-amber-700 flex gap-2">
                  <span className="shrink-0 mt-0.5 text-amber-500">•</span>
                  {c}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Botón de ayuda (se usa en el Topbar)
// =============================================================================

export function HelpButton() {
  const [abierto, setAbierto] = useState(false)

  return (
    <>
      <button
        onClick={() => setAbierto(true)}
        className={cn(
          "w-7 h-7 flex items-center justify-center rounded-full transition-colors",
          "bg-zinc-100 text-zinc-500 hover:bg-sgs-rojo hover:text-white",
        )}
        title="Ayuda sobre esta página"
      >
        <HelpCircle size={14} />
      </button>
      <HelpModal abierto={abierto} onCerrar={() => setAbierto(false)} />
    </>
  )
}
