class ExampleError(Exception):
    """
    Exceptions are documented in the same way as classes.
    Args:
        msg (str): Human readable string describing the exception.
        code (:obj:`int`, optional): Error code.
    Attributes:
        msg (str): Human readable string describing the exception.
        code (int): Exception error code.
    """

    def __init__(self, msg, code):
        self.msg = msg
        self.code = code
