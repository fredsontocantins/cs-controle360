"""Custom exceptions for CS-Controle 360."""

class AppError(Exception):
    """Base class for all application errors."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class EntityNotFoundError(AppError):
    """Raised when an entity is not found in the database."""
    def __init__(self, entity_name: str, entity_id: int | str):
        self.entity_name = entity_name
        self.entity_id = entity_id
        super().__init__(f"{entity_name} with ID {entity_id} not found.")

class DatabaseOperationError(AppError):
    """Raised when a database operation fails."""
    pass

class AuthenticationError(AppError):
    """Raised when authentication fails."""
    pass
