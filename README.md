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

## Instalación pública (recomendada)
Requisitos: Docker Engine + Docker Compose plugin (+ curl en el host).

```bash
git clone <URL_DE_TU_REPO>
cd IndicadoresCHILE
./deployment/install_public.sh
```

Esto hace automáticamente:
- pre-check de Docker/Compose/curl,
- creación de `.env` desde `.env.example`,
- generación automática de `ADMIN_API_KEY` segura (sin depender de python del host),
- build + `up -d`,
- validación de salud del servicio.
- detección de puerto ocupado y solicitud de nuevo puerto antes del despliegue.

Abre: `http://IP_DEL_SERVIDOR:8000` (o puerto definido en `APP_PORT`).

## Alternativa con Makefile (más simple)
```bash
make install-public
```

## Instalación manual con Docker
```bash
cp .env.example .env
# opcional: editar .env
./deployment/deploy.sh
```

### Comandos operativos útiles
```bash
# levantar/actualizar
./deployment/deploy.sh
# o
make deploy

# logs en vivo
docker compose logs -f dashboard
# o
make logs

# estado
docker compose ps
# o
make status

# detener
docker compose down
# o
make down
```


## Despliegue detrás de proxy (Nginx Proxy Manager)
Si expones la app públicamente detrás de Nginx Proxy Manager:

1. Configura el proxy host apuntando al servidor/puerto donde corre Docker (`APP_PORT`, por defecto 8000).
2. En `.env`, ajusta:
```bash
ALLOWED_ORIGINS=https://tu-dominio.com
FORWARDED_ALLOW_IPS=*
PROXY_HEADERS=1
```
3. Si publicas en subruta (ej: `https://tu-dominio.com/indicadores`), usa:
```bash
ROOT_PATH=/indicadores
```
4. Reaplica despliegue:
```bash
./deployment/deploy.sh
```

Notas:
- `PROXY_HEADERS=1` habilita lectura de `X-Forwarded-*` en Uvicorn.
- `FORWARDED_ALLOW_IPS` puede restringirse a la IP de tu proxy en lugar de `*` para mayor seguridad.

## Resolver conflictos de merge (rápido)
Si tu PR marca conflictos con `main`, puedes usar:

```bash
./deployment/resolve_merge_conflicts.sh main
```

El script hace `fetch + rebase` y te deja instrucciones para continuar en caso de conflicto.

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

## Ejecutar local sin Docker
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/update_data.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Abrir: `http://localhost:8000`

## Tests
```bash
pytest -q
# o
make test
```

## Seguridad y acceso
- CORS configurable por `ALLOWED_ORIGINS`.
- Endpoint admin protegido con `ADMIN_API_KEY`.
- `deployment/deploy.sh` genera automáticamente una API key segura si detecta valor por defecto.
- Cabeceras de seguridad HTTP activas (CSP, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`).
- Recomendado para producción:
  - Reverse proxy con TLS (Nginx/Traefik/Caddy).
  - Rotación de `ADMIN_API_KEY` y gestión en Secret Manager.
  - Rate limiting/WAF en capa de borde.

## Auto-actualización
- `RUN_UPDATE_ON_STARTUP=1` hace actualización inicial al iniciar contenedor.
- Para refresco periódico, mantener cron/job externo que invoque:
```bash
docker compose exec dashboard python scripts/update_data.py
```

## Troubleshooting rápido

- Si ves `port is already allocated`, vuelve a ejecutar `./deployment/deploy.sh` y el script te pedirá otro puerto libre.
- Verifica salud:
```bash
curl -sS http://127.0.0.1:8000/api/health
```
- Si no responde:
```bash
docker compose ps
docker compose logs -f dashboard
```

## CI/CD
El workflow `.github/workflows/ci.yml` instala dependencias y ejecuta pruebas en cada push/PR.
