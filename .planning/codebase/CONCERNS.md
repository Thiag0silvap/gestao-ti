# Concerns

## Security
- **Hardcoded Defaults**: `SECRET_KEY` and `AGENT_API_KEY` have insecure defaults ("changeme") in `app/config.py`. These must be overridden in production via environment variables.
- **Trusted Connections**: The use of Windows Authentication (`DB_TRUSTED_CONNECTION="yes"`) for database access may limit deployment options to Windows-hosted environments and carries specific permission risks.
- **Sensitive Data in Logs**: Ensure that `backend.log` and `backend.err.log` do not contain PII or credentials.

## Technical Debt
- **No Automated Tests**: The lack of a test suite makes refactoring risky and increases the likelihood of regressions as the project grows.
- **Dynamic Schema Alterations**: The backend automatically alters database tables on startup (`ensure_computer_columns` in `main.py`). While convenient for development, this can be dangerous in production and should be replaced by a formal migration tool like **Alembic**.
- **Error Handling**: While `HTTPException` is used in routes, there is no global exception handler or centralized logging strategy for unhandled errors.

## Architecture & Scalability
- **Direct Agent Interaction**: The backend handles raw data submission from agents directly. As the number of managed computers grows, this could become a bottleneck. Consider a message queue (e.g., RabbitMQ, Redis) for asynchronous processing of telemetry.
- **SQL Server Dependency**: The project is heavily tied to SQL Server (via `pyodbc` and specific SQL syntax in schema checks). Migrating to another database (like PostgreSQL) would require significant changes.

## Maintainability
- **Mixed Languages**: UI strings are in Portuguese while code logic is in English. While acceptable for localized internal tools, it may pose challenges for international contributors or expansion.
- **Version Management**: Agent versioning and release management are handled via environment variables and static file paths, which could become hard to manage at scale.
