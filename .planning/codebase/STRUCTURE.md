# Project Structure

## Root
- `backend/`: FastAPI backend source code.
- `frontend/`: React frontend source code.
- `agent/`: Likely source for the inventory agent (source/binary).
- `.agent/`: GSD/Agent specific configuration.
- `.planning/`: Project planning and codebase mapping (this directory).

## Backend (`/backend`)
- `app/`: Core application logic.
  - `routes/`: API endpoint definitions organized by domain.
  - `models/`: SQLAlchemy database models.
  - `schemas/`: Pydantic models for validation.
  - `core/`: Core utilities and configurations.
  - `database.py`: DB engine and session setup.
  - `main.py`: Entry point and app configuration.
- `requirements.txt`: Python dependencies.
- `run_api.py`: Helper script to run the API.

## Frontend (`/frontend`)
- `src/`: React source code.
  - `pages/`: Page-level components.
  - `components/`: Reusable UI components.
  - `api/`: API client configurations.
  - `services/`: Business logic and API call wrappers.
  - `hooks/`: Custom React hooks.
  - `utils/`: Helper functions.
  - `assets/`: Static assets (images, etc.).
- `package.json`: Node.js dependencies and scripts.
- `vite.config.js`: Vite configuration.
- `tailwind.config.js`: Tailwind CSS configuration.
