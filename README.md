# IndicadoresCHILE

Proyecto web para analizar indicadores macroeconómicos de Chile con comparación OCDE/mundo, contexto histórico anual y actualización automática.

## Funcionalidades implementadas
- Dashboard web con:
  - Filtros por indicador y rango de años.
  - Gráfico comparativo Chile vs OCDE vs Mundo.
  - Módulo para **sumar 2 curvas** (`indicador:pais + indicador:pais`).
  - Visualización de **riesgo país vs gobierno**.
  - Timeline de eventos relevantes (pandemia, retiros, shocks globales).
  - Tarjetas de insights (brechas inflación/PIB y cantidad de eventos del período).
- API FastAPI con endpoints de consulta, agregación y metadatos de actualización.
- Actualización automática de datos desde World Bank API con reintentos.
- Endpoint administrativo protegido por API key para forzar refresh.
- Testing automatizado + CI con GitHub Actions.

## Endpoints principales
- `GET /api/health`
- `GET /api/indicators`
- `GET /api/series?indicator=inflation&countries=CHL,OED,WLD&start_year=2010&end_year=2024`
- `GET /api/curve/sum?left=inflation:CHL&right=gdp_growth:CHL&start_year=2010&end_year=2024`
- `GET /api/context/events?start_year=2018&end_year=2024`
- `GET /api/risk/governments?start_year=2015&end_year=2024`
- `GET /api/insights/overview?start_year=2018&end_year=2024`
- `GET /api/metadata/last-update`
- `POST /api/admin/refresh` (header `X-API-Key`)

## Ejecutar local
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/update_data.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Abrir: `http://localhost:8000`

## Ejecutar con Docker
```bash
docker compose up --build
```

## Tests
```bash
pytest -q
```

## Seguridad y acceso
- CORS configurable por `ALLOWED_ORIGINS` (por defecto sólo localhost).
- Endpoint admin protegido con `ADMIN_API_KEY`.
- Cabeceras de seguridad HTTP activas (CSP, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`).
- Recomendado para producción:
  - Reverse proxy con TLS.
  - Rotación de `ADMIN_API_KEY` y gestión en Secret Manager.
  - Rate limiting/WAF en capa de borde.

## Auto-actualización
- Programar cron diario para refrescar series:
```bash
0 6 * * * cd /ruta/IndicadoresCHILE && /ruta/.venv/bin/python scripts/update_data.py
```
- También puedes forzar actualización con `POST /api/admin/refresh`.

## CI/CD
El workflow `.github/workflows/ci.yml` instala dependencias y ejecuta pruebas en cada push/PR.


## Publicar en GitHub
Si aún no tienes remoto configurado:
```bash
git remote add origin <URL_DEL_REPO>
```

Subir cambios:
```bash
git push -u origin <tu-rama>
```

Crear PR desde GitHub usando la rama subida.
