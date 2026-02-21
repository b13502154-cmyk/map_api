# Deploying this project to Render

This guide explains how to deploy this FastAPI project to Render (https://render.com). It covers both Docker-based and native Python deployments, environment variables, database setup, and verification steps.

**Prerequisites**
- A GitHub repository containing this project.
- A Render account and permissions to create services.
- If using a database: access to run SQL or use Render's Managed Postgres.

**Quick summary**
- Recommended: use Docker Web Service (uses `Dockerfile`).
- Alternative: use a Python Web Service and run with `gunicorn` + `uvicorn` worker.
- Health check: `/health` (returns `{ "status": "ok" }`).
- Data file: `data/build/places.json` is included by the Dockerfile; keep it in the repo.

**Files inspected**
- `app/main.py` — FastAPI app and endpoints.
- `Dockerfile` — builds image and currently runs Uvicorn on port 8000.
- `requirements.txt` — Python dependencies.
- `app/config.py` — environment variables used by the app.

**Environment variables used by the app**
- `API_KEY` — optional API key used to protect endpoints. If set, requests must include header `X-API-Key`.
- `DATABASE_URL` — Postgres connection string. Default points to a local DB; set this to a Render Managed Postgres URL if used.
- `HOST` — server host (default `0.0.0.0`).
- `PORT` — server port (default `8000`).

Note: The app reads `DATA_FILE` at `data/build/places.json`. Ensure this file is present in the deployed image or build output.

---

**Option A — Docker Web Service (recommended)**
1. In Render dashboard, create a new service: *Web Service*.
2. Connect your GitHub repo and pick the branch to deploy.
3. Select `Docker` as the environment (Render will build using your `Dockerfile`).
4. Build and Start settings:
   - No custom build command required (Render will run Docker build).
   - Port: Render provides `$PORT` at runtime. Two choices:
     - Quick: Set an environment variable `PORT=8000` in Render to match the current `Dockerfile` CMD.
     - Better: update the `Dockerfile` to use the runtime `$PORT` (recommended). See `Dockerfile` snippet below.
5. Add environment variables in Render's Environment section (`API_KEY`, `DATABASE_URL`, etc.).
6. Deploy and monitor the logs.

Recommended `Dockerfile` CMD change (use shell form so `$PORT` is expanded):

```dockerfile
# replace the existing CMD with this line
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

If you don't want to edit the `Dockerfile`, set Render env `PORT=8000`.

**Option B — Python Web Service (no Docker)**
1. Create a new *Web Service* and choose `Python` (or the native option Render provides).
2. Set the build command (optional): `pip install -r requirements.txt` (Render may do this automatically).
3. Set the Start Command to run Gunicorn with Uvicorn worker:

```bash
gunicorn -k uvicorn.workers.UvicornWorker "app.main:app" --bind 0.0.0.0:$PORT
```

4. Ensure `data/build/places.json` is present in the repository and included in the slug (it will be available at runtime).
5. Add environment variables (`API_KEY`, `DATABASE_URL`, etc.).

**Database (optional)**
If your usage requires Postgres / PostGIS:
- Create a Render Managed Postgres instance.
- In Render UI, copy the connection string and set it as `DATABASE_URL` for your web service.
- Run `schema.sql` to create tables. You can use either:
  - Local psql connecting to the managed DB, or
  - Render's Shell (one-off) to run SQL on the instance.

Example to run `schema.sql` from your machine:

```bash
psql "$DATABASE_URL" -f schema.sql
```

**Health check & readiness**
- Set Render's health check path to `/health`.
- Confirm the service responds with `{ "status": "ok" }`.

**Environment variables to add in Render**
- `API_KEY` (optional): protect endpoints if you want an API key.
- `DATABASE_URL` (optional): `postgresql://...` if using Postgres.
- `PORT` (only if you don't edit `Dockerfile`; otherwise Render provides it at runtime).

**Testing after deploy**
1. Open service logs in Render; watch build and startup logs for errors.
2. Visit `https://<your-service>.onrender.com/health`.
3. Test API endpoints, e.g. `/api/places`.
4. If protected by `API_KEY`, include header `X-API-Key: <your-key>`.

**Common issues & fixes**
- App fails to find `places.json`: ensure `data/build/places.json` is committed and copied in the `Dockerfile` (the current `Dockerfile` copies it).
- Port mismatch: either set `PORT=8000` in Render env or update `Dockerfile` to use `$PORT`.
- Missing Python dependencies: ensure `requirements.txt` lists FastAPI and `uvicorn[standard]` (this repo's `requirements.txt` already includes them).

**Optional: Patch suggestions (one-line edits you can make now)**
- Change `Dockerfile` to use `$PORT` (see snippet above).
- Use `gunicorn` for production when not using Docker.

---

If you'd like, I can:
- (A) Patch the `Dockerfile` now to use `$PORT` and commit the change, or
- (B) Produce a short Render dashboard checklist (copy/paste) for the UI.

