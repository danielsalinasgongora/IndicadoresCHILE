# Plan maestro: Dashboard macroeconómico Chile + OCDE

## 1) Objetivo del producto
Crear una plataforma web de análisis macroeconómico que:
- Consuma y actualice automáticamente indicadores del Banco Central de Chile, OCDE y fuentes globales.
- Permita análisis comparativo y exploratorio por año, evento y administración de gobierno.
- Muestre visualizaciones interactivas con comparaciones como:
  - Chile vs OCDE.
  - Inflación Chile vs inflación mundial.
  - Riesgo país por periodo presidencial.
  - Impacto de pandemia, retiros y ciclo del PIB.
- Añada contexto narrativo por año (hechos mundiales relevantes y posible impacto).

## 2) Casos de uso clave
1. **Filtrar por año/rango de años** y por tipo de indicador.
2. **Sumar 2 curvas** (ej: consumo + inversión) y compararlas contra una serie base.
3. **Comparar series entre geografías** (Chile, OCDE, mundo).
4. **Analizar por gobierno** (agrupación por presidencia y hitos nacionales).
5. **Ver timeline de eventos globales** para interpretar quiebres de tendencia.
6. **Exportar gráficos y datasets** (PNG/CSV) para informes.

## 3) Arquitectura recomendada

### Front-end
- **Next.js + TypeScript**.
- Librerías de gráficos: **Apache ECharts** o **Plotly** para series temporales y overlays.
- Diseño de filtros con estado global (Zustand/Redux Toolkit).

### Back-end API
- **FastAPI** o **NestJS** con endpoints para:
  - Catálogo de indicadores.
  - Series normalizadas.
  - Agregaciones (sumas, variaciones YoY/MoM, índices base 100).
  - Metadatos de eventos históricos.
- Cache de consultas frecuentes con Redis.

### Data pipeline (ETL/ELT)
- Orquestación con **Prefect** o **Airflow**.
- Tareas diarias:
  1. Extraer datos de Banco Central, OCDE y fuentes globales (IMF/World Bank/FRED según disponibilidad).
  2. Validar esquema y calidad.
  3. Cargar a modelo analítico en PostgreSQL.
  4. Recalcular agregados y métricas derivadas.

### Base de datos
- **PostgreSQL** con esquema:
  - `sources`
  - `indicators`
  - `series`
  - `observations`
  - `countries`
  - `events`
  - `governments`
  - `indicator_mappings` (equivalencias entre fuentes)

## 4) Modelo de datos mínimo

### Tabla `observations`
- `indicator_id`
- `country_code`
- `date`
- `value`
- `frequency` (M/Q/A)
- `unit`
- `source_id`
- `revision_tag`
- `ingested_at`

### Tabla `events`
- `event_date`
- `event_type` (global/local/policy/shock)
- `title`
- `description`
- `impact_tags` (inflation, rates, gdp, risk)
- `severity`

### Tabla `governments`
- `country_code`
- `president_name`
- `start_date`
- `end_date`
- `coalition`

## 5) Funcionalidades analíticas
1. **Operaciones entre curvas**
   - Suma/resta.
   - Rebase a 100.
   - Diferencias porcentuales.
2. **Comparadores predefinidos**
   - Inflación Chile vs inflación mundial.
   - Riesgo país vs gobierno de turno.
   - PIB real vs periodos pandemia/retiros.
3. **Capas de contexto (anotaciones)**
   - Línea de tiempo con hitos globales por año.
   - Tooltips explicativos y enlaces a fuentes.

## 6) Auto-actualización
- **Frecuencia diaria** para series de alta frecuencia y semanal para validaciones completas.
- Scheduler con reintentos y alertas (Slack/email).
- Detección de revisiones de series (versionado de dato).
- Dashboard de salud del pipeline:
  - Última ejecución.
  - Fuentes caídas.
  - Latencia de actualización.

## 7) Seguridad y control de acceso

### Autenticación y autorización
- SSO corporativo opcional (OIDC/SAML) + login local para administradores.
- Roles mínimos:
  - `viewer` (solo lectura)
  - `analyst` (dashboards personalizados, exportación)
  - `admin` (gestión de fuentes, eventos, usuarios)
- RBAC en API y front-end.

### Seguridad de aplicación
- OAuth2/JWT con expiración corta + refresh tokens rotativos.
- Protección CSRF/XSS/SQLi (ORM parametrizado, sanitización, CSP).
- Rate limiting por IP/usuario.
- WAF y protección anti-bot para endpoints públicos.

### Seguridad de datos
- Cifrado en tránsito (TLS 1.2+).
- Cifrado en reposo (volúmenes y backups).
- Secrets en gestor dedicado (Vault/AWS Secrets Manager/GCP Secret Manager).
- Backups automáticos y pruebas de restauración mensuales.

### Auditoría y cumplimiento
- Logs de acceso y cambios de configuración.
- Trazabilidad de cambios de datos (quién, cuándo, qué cambió).
- Políticas de retención y borrado según normativa aplicable.

## 8) Observabilidad y operación
- Métricas (Prometheus/Grafana): latencia API, tasa de errores, disponibilidad.
- Logging centralizado (ELK/OpenSearch).
- Alertas por caída de ETL, latencia alta, error de integración externa.
- SLO sugerido: 99.5% de disponibilidad mensual.

## 9) Roadmap por fases

### Fase 1 (4-6 semanas): MVP
- Ingesta Banco Central + OCDE.
- Dashboard con filtros por año, comparación Chile/OCDE e inflación global.
- Timeline de eventos anual básico.
- Seguridad base (JWT + RBAC + TLS).

### Fase 2 (4 semanas)
- Módulo de gobiernos + riesgo país.
- Operaciones avanzadas entre curvas.
- Exportación CSV/PNG y vistas guardadas.

### Fase 3 (4 semanas)
- Más fuentes internacionales y enriquecimiento de eventos.
- Alertas inteligentes de cambios atípicos.
- Hardening de seguridad y auditoría extendida.

## 10) Recomendaciones prácticas de implementación
1. Empezar con 10-15 indicadores críticos bien definidos antes de escalar catálogo.
2. Definir un diccionario único de unidades/frecuencias para evitar inconsistencias.
3. Versionar transformaciones de datos para reproducibilidad analítica.
4. Mantener datasets “raw”, “clean” y “serving” separados.
5. Diseñar desde el inicio el modelo de eventos para que el contexto histórico no sea manual y frágil.

## 11) Stack sugerido (concreto)
- Front-end: Next.js, TypeScript, Tailwind, ECharts.
- Back-end: FastAPI, SQLAlchemy, Pydantic.
- Data: PostgreSQL, Redis.
- ETL: Prefect.
- Infra: Docker + Terraform + Cloud Run/ECS/Kubernetes (según presupuesto).
- CI/CD: GitHub Actions con pruebas, lint y escaneo de seguridad.

## 12) Definición de éxito
- Datos actualizados automáticamente sin intervención manual diaria.
- Tiempo de respuesta de consultas < 2 segundos para filtros comunes.
- Capacidad de explicar variaciones anuales combinando series + eventos.
- Trazabilidad completa de cada dato a su fuente original.
