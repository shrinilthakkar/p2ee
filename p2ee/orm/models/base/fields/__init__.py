from abc import ABCMeta

from p2ee.orm.models.exceptions import InvalidFieldValueException, InvalidFieldDefinition


class BaseField(object):
    __metaclass__ = ABCMeta
    """A base class for all types of fields.

    Default value: None
    """

    def __init__(self, default=None, choices=None, required=False, field_name=None):
        """
        :param default: (optional) The default value for this field if
            no value has been set (or if the value has been unset).
            It can be a callable.
        :param choices: (optional) The valid choices
        """
        self._default = default
        self._choices = choices
        self._required = required
        self._field_name = field_name

    @property
    def default(self):
        """Default value for the field"""
        value = self._default if not callable(self._default) else self._default()
        if self.required and value is None:
            raise InvalidFieldValueException(message='Field is required but value is None')
        return value

    @property
    def choices(self):
        """Default value for the field"""
        return self._choices

    @property
    def required(self):
        return self._required

    @property
    def field_name(self):
        return self._field_name

    def validate(self, value, field=None):
        """Derived class should override this method and add extra validation logic."""
        if self.required and value is None:
            raise InvalidFieldValueException('Value cannot be None',
                                             field=field, value=value)
        if self.choices is not None and value not in self.choices:
            raise InvalidFieldValueException('Value must be one of the permitted values',
                                             field=field, value=value)

        return value

    @classmethod
    def _validate_validator(cls, validator):
        if validator and not isinstance(validator, BaseField):
            raise InvalidFieldDefinition("Element Validator should be an instance of BaseField: %r" % validator)
        return validator
