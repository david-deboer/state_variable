class StateVariableError(Exception):
    """State variable exception handling."""
    def __init__(self, message):
        self.message = message
    