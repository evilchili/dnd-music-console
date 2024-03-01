class APIHandlingException(Exception):
    """
    An API reqeust could not be encoded or decoded.
    """


class ConfigurationError(Exception):
    """
    An error was discovered with the Groove on Demand configuration.
    """


class InvalidPathError(Exception):
    """
    The specified path was invalid -- either it was not the expected type or wasn't accessible.
    """
