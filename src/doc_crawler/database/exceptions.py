"""Database-related exceptions."""

class DatabaseError(Exception):
    """Base exception for database errors."""
    pass

class DuplicateResourceError(DatabaseError):
    """Error resource already exists"""
    pass

class ResourceNotFoundError(DatabaseError):
    """Error resource not found"""
    pass

class DatabaseConnectionError(DatabaseError):
    """Error resource not found"""
    pass