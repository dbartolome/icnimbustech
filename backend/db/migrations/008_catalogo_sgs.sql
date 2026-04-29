-- Módulo B: Catálogo de servicios SGS + Matriz sectorial
-- Estas tablas enriquecen el Copilot y el Deck con portfolio real de SGS España

-- =============================================================================
-- 1. Catálogo de servicios
-- =============================================================================

CREATE TABLE IF NOT EXISTS catalogo_servicios (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    linea            VARCHAR(100) NOT NULL,
    servicio         TEXT NOT NULL,
    entregables      TEXT,
    normas_clave     TEXT,
    sectores_objetivo TEXT,
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_catalogo_linea ON catalogo_servicios (linea);
CREATE INDEX IF NOT EXISTS idx_catalogo_normas ON catalogo_servicios USING gin (to_tsvector('spanish', normas_clave));

-- =============================================================================
-- 2. Matriz sectorial
-- =============================================================================

CREATE TABLE IF NOT EXISTS matriz_sectorial (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sector               VARCHAR(100) NOT NULL,
    certificaciones_tipo TEXT NOT NULL,
    pain_points          TEXT NOT NULL,
    servicios_sgs_tipo   TEXT NOT NULL,
    creado_en            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matriz_sector ON matriz_sectorial (sector);

-- =============================================================================
-- 3. Seed: 8 líneas de servicio reales del catálogo SGS España
-- =============================================================================

INSERT INTO catalogo_servicios (linea, servicio, entregables, normas_clave, sectores_objetivo) VALUES
(
    'Certificación y auditoría',
    'Certificación de sistemas de gestión: calidad, medioambiente, seguridad, energía, seguridad de la información y continuidad de negocio. Auditorías de primera, segunda y tercera parte.',
    'Certificado acreditado ENAC · Informe de auditoría detallado · Plan de acciones correctoras (CAPA) · Alcance de certificación',
    'ISO 9001, ISO 14001, ISO 45001, ISO 27001, ISO 50001, ISO 22301, ISO 13485, ISO 22000',
    'Industria, alimentación, farma, construcción, servicios, energía, logística, sanitario'
),
(
    'Inspección y ensayos técnicos',
    'Inspecciones reglamentarias, control de calidad en origen y destino, ensayos no destructivos (NDT), integridad de activos e instalaciones, RIPCI, CPR (marcado CE).',
    'Informe de inspección acreditado · Registro de no conformidades · Actas de verificación · Certificados de conformidad',
    'RIPCI, NDT (ISO 9712), ISO 55001, CPR (Reglamento UE 305/2011), ISO 17020',
    'Petroquímica, construcción, energía, obra pública, industria, puertos'
),
(
    'Ensayos de laboratorio',
    'Ensayos mecánicos, metalúrgicos, microbiológicos, químicos y físicos. Calibración de equipos. Ensayos de contacto alimentario, residuos, shelf life y estabilidad.',
    'Informe de ensayo acreditado ENAC · Certificado de calibración · Resultados analíticos trazables',
    'ISO 17025, ISO 14001, ISO 22000, Reglamento (CE) 1907/2006 (REACH)',
    'Alimentación, farma, cosmética, packaging, automoción, química'
),
(
    'Formación SGS Academy',
    'Formación técnica y profesional: cursos de auditor interno/líder, normas ISO, NDT, sostenibilidad, ciberseguridad, seguridad alimentaria y gestión de riesgos. Presencial y online.',
    'Diploma SGS Academy · Material didáctico · Plan de capacitación personalizado · Evaluación de competencias',
    'ISO 9001, ISO 14001, ISO 45001, ISO 27001, ISO 22000, ISO 14064, NDT (ISO 9712)',
    'Todos los sectores — especialmente industria, alimentación, energía, farma, construcción'
),
(
    'Sostenibilidad y ESG',
    'Cálculo y verificación de huella de carbono (alcance 1, 2 y 3), verificación de reporting ESG y CSRD, declaraciones ambientales de producto (DAP/EPD), PFAS, ISO 14064/14067.',
    'Declaración de verificación de tercera parte · Informe de huella de carbono · DAP/EPD verificada · Informe CSRD',
    'ISO 14064, ISO 14067, GHG Protocol, CSRD (Directiva UE), ESRS, GRI, TCFD',
    'Todos los sectores — especialmente energía, construcción, industria, retail, alimentación'
),
(
    'Supply Chain y auditorías de proveedores',
    'Gestión de la cadena de suministro: auditorías de segunda parte (RBS social, ética, SMETA), programas supplier management, SCRM, inspecciones en origen, CAPA management.',
    'Scorecard de proveedor · Informe de auditoría con CAPA · Plan de mejora de proveedores · Clasificación de riesgo',
    'ISO 28000, SA8000, SMETA (Sedex), ISO 20400, IATF 16949',
    'Alimentación, retail, moda, automoción, electrónica, logística'
),
(
    'Ciberseguridad y Digital Trust',
    'Certificación y consultoría en seguridad de la información, privacidad, continuidad de negocio, inteligencia artificial e infraestructuras críticas. Pentesting y evaluaciones técnicas.',
    'Gap assessment · Informe de pentest · Certificado ISO 27001 · Evaluación técnica ENS · Informe de vulnerabilidades',
    'ISO 27001, ISO 27701, ISO 22301, ISO 42001, TISAX, ENS (Esquema Nacional de Seguridad), NIS2, DORA',
    'Servicios financieros, seguros, administración pública, sanidad, industria 4.0, telecomunicaciones'
),
(
    'Verificación y aseguramiento de declaraciones',
    'Verificación independiente de información no financiera, claims de sostenibilidad, aseguramiento de informes ESG, verificaciones para licitaciones y memorias corporativas.',
    'Informe de verificación independiente · Declaración de aseguramiento · Carta de verificación para terceros',
    'ISAE 3000, AA1000AS, GRI, CSRD, ISO 14064-3',
    'Empresas cotizadas, utilities, alimentación, industria, entidades financieras'
)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- 4. Seed: Matriz sectorial con pain points reales por sector
-- =============================================================================

INSERT INTO matriz_sectorial (sector, certificaciones_tipo, pain_points, servicios_sgs_tipo) VALUES
(
    'Alimentación y bebidas',
    'ISO 22000, FSSC 22000, BRCGS, IFS, HACCP, FSC/PEFC CoC, RD 993/2014',
    'Seguridad alimentaria y gestión de alérgenos, trazabilidad de ingredientes, gestión de recalls, presión de grandes retailers (auditorías BRCGS/IFS), fraude alimentario, residuos/contaminantes, cumplimiento HACCP, auditorías de proveedores de materias primas',
    'Auditorías de certificación FSSC/BRCGS/IFS, ensayos microbiológicos y químicos, trazabilidad y shelf life, auditorías de proveedores, verificación de huella de carbono'
),
(
    'Automoción e industria de componentes',
    'IATF 16949, ISO 9001, ISO 14001, ISO 45001, TISAX, ISO 50001',
    'Calidad de proveedor (PPM, no conformidades), ciberseguridad del vehículo conectado, trazabilidad de componentes, cumplimiento ESG en supply chain, descarbonización de operaciones, gestión de residuos y economía circular',
    'Auditorías de proveedores IATF/ISO, TISAX (ciberseguridad automoción), certificación ISO 14001/50001, NDT e inspección de piezas, formación de auditores internos'
),
(
    'Farma, cosmética y productos sanitarios',
    'GxP, GMP, ISO 13485, MDR/IVDR Annex IX, ISO 22716, ISO 14001',
    'Cumplimiento regulatorio GxP/MDR, data integrity, validación de procesos de limpieza, gestión de proveedores críticos, cualificación de equipos, auditorías regulatorias FDA/EMA, trazabilidad de lotes',
    'Auditorías GxP/ISO 13485, ensayos microbiológicos y de esterilidad, auditorías de proveedores, verificación MDR, formación GMP/GxP'
),
(
    'Energía, petróleo y gas',
    'ISO 9001, ISO 14001, ISO 45001, ISO 50001, ISO 14064, EMAS',
    'Integridad de activos y paradas no planificadas, reporting ESG y huella de carbono, cumplimiento regulatorio ambiental, gestión de riesgos HSE, inspección de instalaciones críticas, transición energética y descarbonización',
    'NDT e inspección de integridad, certificación ISO 50001/14001, verificación GHG/ISO 14064, auditorías HSE, EMAS'
),
(
    'Construcción e infraestructuras',
    'ISO 9001, ISO 14001, ISO 45001, Marcado CE (CPR), RIPCI, ISO 14064',
    'Calidad de materiales y ensayos in situ, plazos y gestión de no conformidades, cumplimiento reglamentario (RIPCI, CTE, CPR), gestión de residuos de obra, seguridad y salud laboral, huella de carbono en licitaciones públicas',
    'Ensayos de materiales (hormigón, acero, suelos), inspección RIPCI, marcado CE/CPR, certificación ISO sistemas de gestión, verificación de huella para licitaciones'
),
(
    'Logística, puertos y supply chain',
    'ISO 28000, ISO 9001, ISO 27001, TAPA, ISO 22301',
    'Daños en tránsito y pérdidas de carga, cumplimiento aduanero y OEA, ciberseguridad de sistemas logísticos, continuidad operacional, trazabilidad de mercancías peligrosas, auditorías de proveedores de transporte',
    'Inspección de carga en origen/destino, certificación ISO 28000, Digital Trust (ISO 27001), auditorías de proveedores, formación operadores logísticos'
),
(
    'Seguros y servicios financieros',
    'ISO 27001, ISO 27701, ISO 22301, DORA, NIS2, ISO 42001',
    'Riesgo cibernético y protección de datos, cumplimiento regulatorio (DORA, NIS2, GDPR), continuidad de negocio, gestión de riesgos de IA, auditorías internas de controles, reporting ESG para inversores',
    'Certificación ISO 27001/27701, pentest y evaluaciones técnicas, ISO 22301 (continuidad), ISO 42001 (IA), gap assessment DORA/NIS2, aseguramiento ESG'
),
(
    'Retail y distribución',
    'ISO 9001, ISO 27001, RBS Social, SA8000, FSC/PEFC CoC',
    'ESG en cadena de suministro (presión inversores y consumidores), riesgo reputacional en proveedores (condiciones laborales), ciberseguridad y protección de datos de clientes, trazabilidad de producto, cumplimiento CSRD para grandes grupos',
    'Auditorías RBS social y ética de proveedores, certificación ISO 27001, aseguramiento ESG/CSRD, FSC/PEFC cadena de custodia, verificación de huella de carbono'
)
ON CONFLICT DO NOTHING;
