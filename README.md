# AquaCascade AI MVP

Monorepo structure:

- `frontend/` - Next.js + Tailwind + Leaflet dashboard
- `backend/` - FastAPI processing API

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

## Supported inputs

- CSV and GeoJSON only.
- Best-effort column matching:
  - Terrain: `lat/lon/elevation` aliases
  - Groundwater: `lat/lon/suitability` aliases
- If parsing fails, API returns warnings and falls back to mock-compatible data.
