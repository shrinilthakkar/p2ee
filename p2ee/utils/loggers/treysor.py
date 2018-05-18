class ExampleError(Exception):
    """Exceptions are documented in the same way as classes.
    The __init__() method may be documented in either the class level
    docstring, or as a docstring on the __init__ method itself.
    Either form is acceptable, but the two should not be mixed. Choose one
    convention to document the __init__ method and be consistent with it.
    Note:
        Do not include the `self` parameter in the ``Args`` section.
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


class ExampleClass(object):
    """The summary line for a class docstring should fit on one line.
    If the class has public attributes, they may be documented here
    in an ``Attributes`` section and follow the same formatting as a
    function's ``Args`` section. Alternatively, attributes may be documented
    inline with the attribute's declaration (see __init__ method below).
    Properties created with the ``@property`` decorator should be documented
    in the property's getter method.
    Attributes:
        attr1 (str): Description of `attr1`.
        attr2 (:obj:`int`, optional): Description of `attr2`.
    """

    def __init__(self, param1, param2, param3):
        """Example of docstring on the __init__ method.
        The __init__ method may be documented in either the class level
        docstring, or as a docstring on the __init__ method itself.
        Either form is acceptable, but the two should not be mixed. Choose one
        convention to document the __init__ method and be consistent with it.
        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            param1 (str): Description of `param1`.
            param2 (:obj:`int`, optional): Description of `param2`. Multiple
                lines are supported.
            param3 (:obj:`list` of :obj:`str`): Description of `param3`.
        """
        self.attr1 = param1
        self.attr2 = param2
        self.attr3 = param3  #: Doc comment *inline* with attribute

        #: list of str: Doc comment *before* attribute, with type specified
        self.attr4 = ['attr4']

        self.attr5 = None
        """str: Docstring *after* attribute, with type specified."""

    @property
    def readonly_property(self):
        """str: Properties should be documented in their getter method."""
        return 'readonly_property'

    @property
    def readwrite_property(self):
        """:obj:`list` of :obj:`str`: Properties with both a getter and setter
        should only be documented in their getter method.
        If the setter method contains notable behavior, it should be
        mentioned here.
        """
        return ['readwrite_property']