# LoadFlow — Freight Brokerage Operations Suite

A take-home hackathon build for RB DesignTech. LoadFlow connects **Brokers**,
**Carriers**, and **Shippers** around a load lifecycle, enforced by a real
(not hardcoded) role-based permission system.

## Stack + one-line reason

- **Backend: FastAPI + SQLite (SQLAlchemy ORM)** — fastest path to a
  server-enforced permission layer with clear, typed request/response
  contracts (Pydantic), and SQLite needs zero infra for a 24h build.
- **Frontend: React + Vite** — fast dev loop, small bundle, no
  framework ceremony for a UI this size.
- **Auth: JWT (python-jose) + bcrypt (passlib)** — stateless auth that's
  trivial to attach to both server-side dependency checks and the frontend.

## Architecture

```
backend/
  app/
    main.py           FastAPI app, CORS, router registration
    database.py        SQLite engine/session
    models.py           SQLAlchemy models + PERMISSION_CATALOG (source of truth)
    schemas.py           Pydantic request/response models
    auth.py                Password hashing, JWT issue/verify
    permissions.py           require_permission() / require_org_type() / assert_load_visible()
    routers/
      auth_router.py          bootstrap org (broker/carrier admin), shipper signup, login
      roles_router.py         create custom roles, invite staff (org-admin only)
      loads_router.py         load CRUD, state machine, assign carrier, search/filter
      compliance_router.py    carrier compliance record CRUD
      rates_router.py         versioned rate confirmations
      pod_router.py           POD upload/viewer
      dashboard_router.py     per-account-type summaries, carrier directory, audit log
frontend/
  src/
    api.js                     axios client, attaches JWT
    context/AuthContext.jsx    current-user state
    components/Layout.jsx      topbar + role-aware sidebar
    pages/                     Auth, Dashboard, LoadBoard, LoadDetail, RolesAdmin, Compliance, AuditLog
```

## RBAC design (the core of this assignment)

- **Permissions are the only thing code checks.** The fixed catalog lives in
  `models.PERMISSION_CATALOG` (`load.create`, `load.assign_carrier`,
  `load.override_compliance_flag`, `rate.confirm`, `load.update_status`,
  `staff.manage`, `pod.upload`). Every protected endpoint depends on
  `require_permission("...")`, which reads permission strings off the
  user's role — never a role name.
- **Roles are just labels an org admin puts on a bundle of permissions**,
  created at runtime via `POST /roles`, not hardcoded in the backend.
  Org admins implicitly get every permission in their org; staff only get
  what their assigned role grants.
- **Enforcement is server-side**, in the FastAPI dependency layer, not just
  hidden in the UI. A staff account hitting a restricted endpoint directly
  (e.g. with curl) is blocked the same as if they'd clicked a hidden button.
  Verified in `backend/test_flow.py` — a Dispatcher role without
  `load.create` gets a 403 even calling the API directly.
- **Org scoping**: Broker staff only ever see their broker org's loads;
  carrier staff only their carrier org's; enforced in every `loads`
  query filter, not just the UI list.
- **Object-level scoping**: shippers only see their own loads;
  `permissions.assert_load_visible()` is called on every single-load
  endpoint (`GET /loads/{id}`, assign-carrier, status update, rate
  confirmation, POD).
- **Denied attempts are logged** to `permission_denied_log` (and console),
  visible to org admins via the Audit log page.

## Load state machine

```
Posted → Carrier Assigned → Rate Confirmed → Dispatched → In Transit
       → Delivered → POD Verified → Invoiced/Closed
```

- Transitions are **forward-only, one step at a time** (`loads_router.update_status`).
- **Compliance auto-flag**: assigning a carrier with expired insurance or a
  non-active MC/DOT authority sets `compliance_flag=True` on the load and
  blocks any transition past "Carrier Assigned" — unless the acting user
  holds `load.override_compliance_flag`.
- Every transition is written to `load_status_history` with actor + timestamp
  (audit trail), shown as a timeline on the load detail page.
- "Rate Confirmed" additionally requires at least one current rate
  confirmation to exist before the transition is allowed.

## Setup & run locally

### Backend
```bash
cd backend
pip install -r requirements.txt --break-system-packages   # or use a venv
uvicorn app.main:app --reload --port 8000
```
API docs at `http://localhost:8000/docs`.

### Frontend
```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev
```

### Automated RBAC test
```bash
cd backend
python test_flow.py   # requires the backend server running on :8000
```
This script exercises the full flow end-to-end: bootstrapping a broker and
carrier org, creating a custom "Dispatcher" role with a deliberately
restricted permission set, confirming a 403 on a missing permission,
compliance auto-flagging blocking progression, object-level scope
enforcement (a stranger can't view someone else's load), and the
forward-only state machine.

## Deployment

- **Backend → Render**: New Web Service, root `backend/`, build command
  `pip install -r requirements.txt`, start command
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `LOADFLOW_SECRET_KEY`
  to a random value in the environment tab.
- **Frontend → Vercel/Netlify**: root `frontend/`, build command
  `npm run build`, publish directory `dist`. Set `VITE_API_URL` to the
  deployed Render URL.
- Update `allow_origins` in `backend/app/main.py` from `"*"` to the deployed
  frontend origin before considering this production-ready.

## Assumptions made

- A broker's first-posted load attaches the posting user as
  shipper-of-record (no separate shipper-intake flow was built — see below).
- "Confirm rate" is a broker-side action; carriers view but don't confirm,
  matching the brief's account-type split.
- Org bootstrap (`POST /auth/bootstrap-org`) is how the *first* Broker/Carrier
  Admin account is created; every other org member is invited by that admin.

## What's incomplete / stretch not built

- Compliance expiry renewal alerts (stretch #9) — the data model supports it
  (`insurance_expiry` is queryable) but no scheduled/notification job exists.
- POD upload is a URL field, not real file storage — fine for this scope,
  would swap for S3/GCS presigned uploads in a real build.
- No password reset / email delivery — staff invites return credentials
  directly in the API response rather than emailing them.
- Frontend has no automated tests (backend RBAC logic does, via `test_flow.py`).

## What I'd do with more time

- Move the RBAC permission checks into a single declarative policy table
  instead of per-route dependencies, so a new endpoint can't forget to
  guard itself.
- Add a proper shipper-intake flow so loads aren't shipper-of-record'd to
  the posting broker.
- Real file storage for POD + a background job for compliance expiry alerts.
- Integration tests for the frontend (Playwright) alongside the existing
  backend RBAC test suite.

## AI tool usage note

Built with Claude (Anthropic) as a pair-programming/code-generation partner:
architecture and schema design, endpoint implementation, the RBAC
enforcement layer, and the end-to-end test script were all generated
through iterative prompting, with the RBAC/state-machine logic verified by
running `test_flow.py` against a live server before moving on to the
frontend. See commit history for the incremental build order.
