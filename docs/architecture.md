# Architecture

The project follows a light clean architecture split into domain, application, infrastructure, and interface layers.

- **Domain** holds pure models and value objects without framework dependencies.
- **Application** contains use cases and ports (repositories, unit of work) that orchestrate behaviour.
- **Infrastructure** implements the ports using SQLAlchemy, async database sessions, and OIDC helpers.
- **Interfaces** exposes HTTP endpoints, middleware, and DTOs via FastAPI.

Unit of work boundaries ensure all write operations pass through transactional contexts, while repositories enforce tenant filters and optimistic locking.

Authentication combines external OIDC validation and locally issued JWTs that reference users stored in the database; a password hasher service and JWT service live in the infrastructure layer.
