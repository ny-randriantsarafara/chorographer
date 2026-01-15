"""Base domain exceptions."""


class DomainError(Exception):
    """Base exception for all domain errors."""

    pass


class ExtractionError(DomainError):
    """Failed to read/extract OSM data."""

    pass


class TransformationError(DomainError):
    """Failed to convert OSM data to domain entity."""

    pass


class ValidationError(DomainError):
    """Entity failed business rule validation."""

    pass


class PenaltyCalculationError(DomainError):
    """Failed to compute road penalty."""

    pass
