# Frontend

React + Vite dashboard for the regression detector backend.

## Setup

```bash
cd frontend
npm install
```

## Development

```bash
npm run dev
```

The dev server runs on `http://localhost:5173` and proxies API requests to the FastAPI backend at `http://localhost:8000`.

## Build

```bash
npm run build
```

Output lands in `frontend/dist/` and can be served statically or via the FastAPI app.
