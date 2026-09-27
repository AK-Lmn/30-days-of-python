# Day 12 — WardenAuth: Identity & Authentication Service

A production-grade, asynchronous authentication, token lifecycle, and session governance service built with FastAPI, Argon2id, PyJWT, SQLAlchemy 2.0 (asyncio), and Python 3.13.

**Date:** Sep 23, 2026  
**Status:** ✅ Completed

---

## Overview

WardenAuth is a secure identity management engine providing end-to-end authentication, session isolation, role-based access control (RBAC), API key management, and tamper-evident security audit logging.

### Key Highlights

- **Cryptographic Security**:
  - Passwords hashed using **Argon2id** (memory-hard, resistant to GPU/ASIC cracking).
  - High-entropy cryptographic secrets generated via Python's `secrets` module.
  - API keys hashed with SHA-256 before persistence with prefix identification (`wauth_live_...`).
- **Token & Session Governance**:
  - JWT Access Tokens (short-lived, 15 minutes) with role and permission scopes.
  - Refresh Tokens (7 days) tied to database-backed session entities.
  - **Refresh Token Rotation**: Automatic token renewal with immediate invalidation of prior refresh tokens.
  - **Compromise Detection**: Immediate termination of the entire session if an already-rotated or reused token is presented.
  - Granular session revocation (revoke single active session or terminate all user sessions).
- **Role-Based Access Control (RBAC) & Scopes**:
  - Hierarchical roles: `Admin` > `Manager` > `User`.
  - Fine-grained permission scopes (`*`, `users:read`, `sessions:read`, `audit:read`, `profile:read`, etc.).
  - Route-level security guards and dependency injection.
- **Account Protection & Anti-Abuse**:
  - In-memory rate limiting and sliding window lockout after repeated failed login attempts.
  - Account suspension support preventing authentication and invalidating active sessions.
  - Secure password reset flow using time-bounded cryptographic tokens.
- **Audit Logging & System Telemetry**:
  - Structured event tracking for all authentication lifecycle events (`user.registered`, `auth.login.success`, `auth.login.failed`, `auth.token.refreshed`, `session.revoked`, `password.changed`).
  - Admin inspection endpoints and system metrics.
- **Developer & Operator Experience**:
  - Interactive OpenAPI / Swagger UI at `/docs` and ReDoc at `/redoc`.
  - Full-featured command-line interface (`wardenauth`) with Rich terminal tables for user management, token issuance, debugging, and inspection.
  - Complete automated test suite using `pytest` and `pytest-asyncio` with 100% pass rate.

---

## Repository Structure

```text
12-auth-service/
├── pyproject.toml              # Project metadata, scripts, and dependencies
├── requirements.txt            # Locked requirements
├── README.md                   # Project documentation
├── .gitignore
├── wardenauth/
│   ├── __init__.py
│   ├── config.py               # Pydantic Settings configuration
│   ├── database.py             # Async SQLAlchemy engine and session dependency
│   ├── main.py                 # FastAPI application factory and error handlers
│   ├── cli.py                  # Click and Rich terminal management CLI
│   ├── core/
│   │   ├── __init__.py
│   │   ├── errors.py           # Domain exception classes and HTTP mapping
│   │   ├── hashing.py          # Argon2id and SHA-256 hashing utilities
│   │   ├── tokens.py           # JWT generation, validation, and decoding
│   │   ├── permissions.py      # RBAC roles, hierarchy, and scope validation
│   │   ├── rate_limiter.py     # Sliding window rate limiter and lockout manager
│   │   └── middleware.py       # Security headers, Request ID, and latency tracking
│   ├── models/
│   │   ├── __init__.py
│   │   ├── entities.py         # SQLAlchemy ORM database models
│   │   └── schemas.py          # Pydantic request and response schemas
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── user_repo.py        # User and reset token database queries
│   │   ├── session_repo.py     # Session persistence and revocation queries
│   │   ├── api_key_repo.py     # API key persistence and lookup
│   │   └── audit_repo.py       # Audit trail query engine
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py     # Authentication, login, rotation, and reset workflows
│   │   ├── user_service.py     # User profile, role, and status management
│   │   ├── session_service.py  # Session tracking and invalidation
│   │   ├── api_key_service.py  # Service key generation and verification
│   │   └── audit_service.py    # Structured security event logging
│   └── routers/
│       ├── __init__.py
│       ├── dependencies.py     # Bearer and API key auth guards
│       ├── auth_router.py      # /api/v1/auth routes
│       ├── users_router.py     # /api/v1/users routes
│       ├── sessions_router.py  # /api/v1/sessions routes
│       ├── keys_router.py      # /api/v1/keys routes
│       └── admin_router.py     # /api/v1/admin routes
└── tests/
    ├── __init__.py
    ├── conftest.py             # In-memory async SQLite engine and fixtures
    ├── test_hashing.py         # Password and hash verification tests
    ├── test_tokens.py          # JWT issuance, expiry, and decode tests
    ├── test_auth.py            # Registration, login, lockout, and password flows
    ├── test_sessions.py        # Multi-session tracking and revocation tests
    ├── test_rbac.py            # Role hierarchy and permission tests
    ├── test_api_keys.py        # API key authentication tests
    ├── test_audit.py           # Audit logging and telemetry tests
    └── test_cli.py             # CLI command verification tests
```

---

## Architecture & Authentication Flow

```
                      +---------------------------------------+
                      |           Client Request              |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |      SecurityHeadersMiddleware        |
                      | (X-Request-ID, X-Process-Time-Ms, CSP)|
                      +---------------------------------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
                [Bearer JWT Token]                   [X-API-Key Header]
                        |                                   |
                        v                                   v
             +--------------------+               +--------------------+
             |   Decode JWT &     |               |    SHA-256 Hash    |
             |   Verify Signature |               |   Lookup in DB     |
             +--------------------+               +--------------------+
                        |                                   |
                        v                                   v
             +--------------------+                         |
             | Validate Session   |                         |
             |  (Not Revoked)     |                         |
             +--------------------+                         |
                        |                                   |
                        +-----------------+-----------------+
                                          |
                                          v
                      +---------------------------------------+
                      |         RBAC & Scope Verification     |
                      |  (Role Hierarchy / Required Scopes)   |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |       Protected Route Execution       |
                      +---------------------------------------+
```

---

## API Endpoints

### 1. Authentication (`/api/v1/auth`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Register new user account | Public |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT access & refresh tokens | Public |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token and obtain new token pair | Public |
| `POST` | `/api/v1/auth/logout` | Revoke current active session | Bearer Token |
| `POST` | `/api/v1/auth/logout-all` | Terminate all active sessions for the user | Bearer Token |
| `POST` | `/api/v1/auth/change-password`| Change password and invalidate all sessions | Bearer Token |
| `POST` | `/api/v1/auth/forgot-password`| Request cryptographic password reset token | Public |
| `POST` | `/api/v1/auth/reset-password` | Confirm password reset using valid reset token | Public |
| `GET`  | `/api/v1/auth/me` | Fetch authenticated user information | Bearer Token |

### 2. User Profiles (`/api/v1/users`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET`  | `/api/v1/users/me` | Retrieve profile information | Bearer or API Key |
| `PATCH`| `/api/v1/users/me` | Update personal profile details | Bearer Token |

### 3. Session Governance (`/api/v1/sessions`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET`  | `/api/v1/sessions` | List all active sessions for current user | Bearer Token |
| `DELETE` | `/api/v1/sessions/{id}` | Revoke a specific active session | Bearer Token |

### 4. API Keys (`/api/v1/keys`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/keys` | Generate new API key with custom scopes | Bearer Token |
| `GET`  | `/api/v1/keys` | List active API keys (hashes hidden) | Bearer Token |
| `DELETE` | `/api/v1/keys/{id}` | Revoke an API key | Bearer Token |

### 5. Administration & Audit (`/api/v1/admin`)

| Method | Endpoint | Description | Required Role |
|---|---|---|---|
| `GET`  | `/api/v1/admin/users` | List registered users with pagination & search | `Manager` |
| `GET`  | `/api/v1/admin/users/{id}` | Retrieve comprehensive user details | `Manager` |
| `PATCH`| `/api/v1/admin/users/{id}/role` | Update user authorization role | `Admin` |
| `PATCH`| `/api/v1/admin/users/{id}/status` | Suspend or reactivate user account | `Admin` |
| `DELETE` | `/api/v1/admin/users/{id}` | Delete user account and associated resources | `Admin` |
| `GET`  | `/api/v1/admin/sessions` | List active sessions across the entire system | `Manager` |
| `DELETE` | `/api/v1/admin/sessions/{id}` | Forcefully revoke any session | `Admin` |
| `GET`  | `/api/v1/admin/audit-logs` | Filter and query audit log events | `Manager` |
| `GET`  | `/api/v1/admin/stats` | View real-time security and user metrics | `Manager` |

---

## Command Line Interface (CLI)

The `wardenauth` CLI provides direct administrative access:

```bash
# Display help and commands
uv run wardenauth --help

# Provision an administrator account
uv run wardenauth create-user --role admin

# List registered users in formatted table
uv run wardenauth list-users

# Issue a direct access token for testing
uv run wardenauth issue-token <username>

# Inspect and decode JWT token payload in terminal
uv run wardenauth inspect-token <jwt_token>

# View security audit logs
uv run wardenauth audit-logs --limit 25

# Display system telemetry stats
uv run wardenauth stats

# Launch the FastAPI application server
uv run wardenauth serve --host 127.0.0.1 --port 8000
```

---

## Testing & Verification

The test suite covers unit and integration scenarios across all service layers:

```bash
uv run pytest -v
```

### Test Coverage Highlights

- **Hashing & Cryptography**: Verification of Argon2id password hashing, salt variations, and mismatch rejections.
- **Token Security**: Claims validation, signature verification, expiration enforcement, and secret tampering rejection.
- **Authentication Flows**: Account registration, duplicate prevention, password complexity validation, login, account lockout on brute-force attempts.
- **Token Lifecycle**: Refresh token rotation, token reuse detection, and single/all session terminations.
- **Role-Based Access Control**: Route protections for Admin, Manager, and User roles, with permission escalation barriers.
- **Machine-to-Machine Auth**: API key generation, header authentication, and revocation lifecycle.
- **Audit Logs & Telemetry**: Event emission tracking and metrics reporting.
- **CLI Commands**: End-to-end command execution and output validation via Click's `CliRunner`.
