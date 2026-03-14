# Canvas Assignment Agent Frontend

React frontend for the Canvas Assignment Agent.

## Local Development

1. Install dependencies:

```bash
npm ci
```

1. Configure frontend environment:

```bash
cp .env.example .env
```

By default, the frontend points to the backend on port 8010:

```env
VITE_API_URL=http://127.0.0.1:8010
```

1. Start backend (from repository root):

```bash
.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8010
```

1. Start frontend (from this folder):

```bash
npm run dev -- --host 127.0.0.1 --port 5173
```

1. Open:

```text
http://127.0.0.1:5173
```

## Build

```bash
npm run build
```

## Lint

```bash
npm run lint
```
