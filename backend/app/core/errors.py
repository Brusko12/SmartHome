"""Domain errors; HTTP mapping belongs to the API layer."""


class DomainError(Exception):
    code = "domain_error"


class NotFound(DomainError):
    code = "not_found"


class Conflict(DomainError):
    code = "conflict"


class InvalidCommand(DomainError):
    code = "invalid_command"


class Unavailable(DomainError):
    code = "unavailable"
