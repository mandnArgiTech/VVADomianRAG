"""Typed errors for programmatic use; CLI maps these to exit codes."""


class BookFactoryError(Exception):
    """Base class for recoverable book-factory failures."""

    exit_code: int = 1


class BookFactoryConfigError(BookFactoryError):
    """Invalid or missing configuration (YAML, paths, prompts schema, log level)."""

    exit_code = 2


class BookFactoryIOError(BookFactoryError):
    """Filesystem or parse errors when reading/writing inputs or outputs."""

    exit_code = 5
