# Architecture

## System Overview
The project is an IT Asset Management system consisting of a React frontend and a FastAPI backend, communicating via REST.

## Backend Architecture
- **Framework**: FastAPI (Python).
- **Domain-Driven Routing**: Routes are organized by domain (auth, computers, assets, tickets, etc.) in `app/routes`.
- **Data Layer**: SQLAlchemy ORM with Pydantic schemas for request/response validation.
- **Dynamic Schema Management**: The backend performs schema checks and `ALTER TABLE` statements on startup to ensure the database matches expected columns (see `app/main.py`).
- **Agent Integration**: A dedicated set of routes handles communication with external inventory agents.

## Frontend Architecture
- **Framework**: React (Vite).
- **Routing**: Single Page Application (SPA) using `react-router-dom` v7.
- **Security**: 
  - Token-based authentication.
  - Client-side route protection via `ProtectedRoute`.
  - Role-based access control (RBAC) via `RoleProtectedRoute` (Roles: admin, technician, operator).
- **UI Structure**: Centralized `Layout` component with sidebar/header, wrapping various domain pages.

## Data Flow
1. **Inventory Collection**: Agents send data to backend `/agent` endpoints.
2. **Persistence**: Backend validates and stores data in SQL Server.
3. **Visualization**: Frontend fetches data from backend APIs and displays it to authenticated users based on their roles.
4. **Action**: Users can trigger remote actions from the frontend, which are queued/sent to agents via the backend.
