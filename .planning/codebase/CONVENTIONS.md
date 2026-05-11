# Coding Conventions

## General
- **Language**: Source code (logic) is in English, but UI text and some database identifiers/comments are in **Portuguese (pt-BR)**.
- **Project Structure**: Mono-repo style with clear separation between `frontend` and `backend`.

## Backend (Python/FastAPI)
- **Naming**:
  - Functions/Variables: `snake_case`.
  - Classes (Models, Schemas): `PascalCase`.
- **Architecture**:
  - Routes: Defined in `app/routes/<domain>.py`.
  - Models: SQLAlchemy models in `app/models/`.
  - Validation: Pydantic schemas in `app/schemas/`.
- **Best Practices**:
  - Use FastAPI's Dependency Injection for DB sessions and Auth.
  - Schema validation for all incoming/outgoing data.
  - Use `typing` for function signatures.

## Frontend (React/Vite)
- **Naming**:
  - Components: `PascalCase` (e.g., `Dashboard.jsx`).
  - Variables/Functions: `camelCase`.
- **State Management**:
  - Local state with `useState`.
  - Context API for global UI state (`UIContext`).
- **Hooks**:
  - Prefer `useMemo` and `useCallback` for performance optimization in complex pages.
  - Custom hooks for reusable logic (e.g., `useAutoRefresh`).
- **Styling**:
  - Utility-first CSS using **Tailwind CSS**.
  - Consistent layout using a `Layout` component.
- **Linting**:
  - Strict linting via ESLint 9.
