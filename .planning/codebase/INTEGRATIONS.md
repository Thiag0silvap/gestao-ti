# Integrations

## Database
- **SQL Server**: Primary data store. Accessed via SQLAlchemy with PyODBC driver.
- **Connection**: Supports trusted connections (Windows Authentication) or standard connection strings.

## Agent System
- **Inventory Agent**: The system integrates with a custom "Inventory Agent" (likely a client-side executable).
- **Communication**: Backend provides endpoints for agent registration, heartbeat, and data submission.
- **Remote Actions**: System supports sending remote commands/actions to managed computers via agents.

## External APIs
- No clear evidence of 3rd-party SaaS integrations (like Stripe, SendGrid, etc.) in the core configuration, but the system appears to be an internal IT management tool.

## Internal Components
- **Frontend-Backend**: Communication via REST API (Vite/React frontend → FastAPI backend).
- **CORS**: Configured in backend to allow specific origins (defaulting to localhost/127.0.0.1 for development).
