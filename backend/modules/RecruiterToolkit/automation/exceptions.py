class AutomationException(Exception):
    """Base exception for the automation framework."""
    pass


class ElementNotFoundException(AutomationException):
    """Raised when an element cannot be located."""
    pass


class ElementNotVisibleException(AutomationException):
    """Raised when an element exists but is not visible."""
    pass


class ElementNotEnabledException(AutomationException):
    """Raised when an element is disabled."""
    pass


class NavigationException(AutomationException):
    """Raised when page navigation fails."""
    pass


class ValidationException(AutomationException):
    """Raised when a validation or assertion fails."""
    pass


class ExportException(AutomationException):
    """Raised when export operations fail."""
    pass
