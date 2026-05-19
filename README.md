# NexHost Custom Automation API

Backend automation engine for NexHost, built with FastAPI, PostgreSQL, SQLAlchemy, Alembic, and JWT authentication.

## Features

- FastAPI application with interactive API docs
- PostgreSQL database connection through SQLAlchemy
- Alembic migration setup
- User signup and login
- Password hashing with Passlib bcrypt
- JWT access token generation
- User model with email and optional phone number

## Project Structure

```txt
app/
  api/v1/          API route handlers
  core/            App config and security helpers
  database/        Database engine and session setup
  models/          SQLAlchemy database models
  schemas/         Pydantic request/response schemas
migrations/        Alembic migration files
alembic.ini        Alembic configuration
requirements.txt   Python dependencies
```

## Requirements

- Python 3.11+
- PostgreSQL
- Virtual environment recommended

## Setup

Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://postgres:your_password@127.0.0.1:5432/nexhost_db
JWT_SECRET=replace_with_a_strong_secret_key
REDIS_URL=redis://127.0.0.1:6379/0
CORS_ORIGINS=http://127.0.0.1:3000,http://localhost:3000
```

Make sure the PostgreSQL database exists:

```sql
CREATE DATABASE nexhost_db;
```

## Database Migrations

Run migrations:

```powershell
alembic upgrade head
```

Create a new migration after model changes:

```powershell
alembic revision --autogenerate -m "your migration message"
```

## Run The API

Start the development server:

```powershell
uvicorn app.main:app --reload
```

Open:

- API root: `http://127.0.0.1:8000/`
- Swagger docs: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Auth Endpoints

Signup:

```http
POST /api/v1/auth/signup
```

Example body:

```json
{
  "full_name": "Hasan",
  "email": "hasan@example.com",
  "phone_number": "01700000000",
  "password": "strongpassword"
}
```

Login:

```http
POST /api/v1/auth/login
```

Example body:

```json
{
  "email": "hasan@example.com",
  "password": "strongpassword"
}
```

Both endpoints return:

```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "full_name": "Hasan",
    "email": "hasan@example.com",
    "phone_number": "01700000000",
    "is_active": true,
    "is_admin": false,
    "created_at": "2026-05-19T00:00:00Z"
  }
}
```

## Notes

- Keep `.env` private and never commit real secrets.
- Alembic migrations are the source of truth for database schema changes.
- Run `alembic upgrade head` before starting the API on a fresh database.
