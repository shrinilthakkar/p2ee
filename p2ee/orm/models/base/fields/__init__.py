import datetime
import re
from abc import ABCMeta

import six
from bson import ObjectId
from bson.errors import InvalidId
from dateutil import parser
from enum import Enum

from p2ee.orm.models.exceptions import InvalidFieldValueException, InvalidFieldDefinition, InvalidFieldException


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


class StringField(BaseField):
    """A unicode string field.

    Default value:
    """

    def __init__(self, regex=None, min_length=None, max_length=None, **kwargs):
        self.regex = regex
        self.min_length = min_length
        self.max_length = max_length

        try:
            self.regex = re.compile(self.regex) if regex is not None else None
        except Exception:
            raise InvalidFieldValueException('Invalid regex pattern')

        super(StringField, self).__init__(**kwargs)

    def validate(self, value, field=None):
        if not isinstance(value, six.string_types):
            raise InvalidFieldValueException('Value must be a string',
                                             field=field, value=value)

        if self.max_length is not None and len(value) > self.max_length:
            raise InvalidFieldValueException('String value too long', field=field, value=value)

        if self.min_length is not None and len(value) < self.min_length:
            raise InvalidFieldValueException('String value too short', field=field, value=value)

        if self.regex is not None and self.regex.match(value) is None:
            raise InvalidFieldValueException('String value did not match validation regex',
                                             field=field, value=value)

        return super(StringField, self).validate(value, field=field)


class ObjectIdField(BaseField):
    def __init__(self, default=ObjectId, **kwargs):
        super(ObjectIdField, self).__init__(default=default, **kwargs)

    def validate(self, value, field=None):
        if not isinstance(value, ObjectId):
            if isinstance(value, basestring) and len(value) == 24:
                try:
                    value = ObjectId(value)
                except InvalidId:
                    raise InvalidFieldValueException('Value must be a valid ObjectId', field=field, value=value)
            else:
                raise InvalidFieldValueException('Value must be a valid ObjectId', field=field, value=value)
        return super(ObjectIdField, self).validate(value, field=field)


class DBNameField(StringField):
    def __init__(self, **kwargs):
        super(DBNameField, self).__init__(max_length=50, min_length=1, **kwargs)


class EnumField(BaseField):
    def __init__(self, enum_class=Enum, **kwargs):
        self.enum_class = enum_class
        if not hasattr(self.enum_class, 'fromStr'):
            raise InvalidFieldException("Enum class %r must implement `fromStr` method" % self.enum_class)
        super(EnumField, self).__init__(choices=list(self.enum_class), **kwargs)

    def validate(self, value, field=None):
        if not isinstance(value, self.enum_class):
            value_enum = self.enum_class.fromStr(value)
            if not value_enum:
                raise InvalidFieldValueException("Enum doesnt allow value: %r, "
                                                 "allowed values: %r" % (value_enum,
                                                                         map(lambda x: str(x), self.enum_class)))
        else:
            value_enum = value

        return super(EnumField, self).validate(value=value_enum, field=field)


class IntField(BaseField):
    """32-bit integer field.

    Default value: 0
    """

    def __init__(self, min_value=None, max_value=None, **kwargs):
        self.min_value = min_value
        self.max_value = max_value

        super(IntField, self).__init__(**kwargs)

    def _instance_check(self, value, field=None):
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        if not isinstance(value, (int, long)):
            raise InvalidFieldValueException('Value must be an integer', field=field, value=value)
        return value

    def _min_check(self, value, field=None):
        if self.min_value is not None and value < self.min_value:
            raise InvalidFieldValueException('Value is too small', field=field, value=value)

    def _max_check(self, value, field=None):
        if self.max_value is not None and value > self.max_value:
            raise InvalidFieldValueException('Value is too large', field=field, value=value)

    def validate(self, value, field=None):
        value_int = self._instance_check(value, field=field)
        self._min_check(value_int, field=field)
        self._max_check(value_int, field=field)
        return super(IntField, self).validate(value_int, field=field)


class EmailField(StringField):
    """A field that validates input as an email address.

    Default value: ''
    """
    EMAIL_REGEX = re.compile(
        # dot-atom
        r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"
        # quoted-string
        r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"'
        # domain
        r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,253}[A-Z0-9])?\.)+[A-Z]{2,6}$', re.IGNORECASE
    )

    def validate(self, value, field=None):
        if not EmailField.EMAIL_REGEX.match(value):
            raise InvalidFieldValueException('Invalid email address', field=field, value=value)

        return super(EmailField, self).validate(value, field=field)


class ListField(BaseField):
    """A list field that wraps a standard field.
    `items` are converted to validator type if validator is passed

    Default value: []
    """

    def __init__(self, element_validator=None, choices=None, max_items=None, **kwargs):
        self.element_validator = self._validate_validator(element_validator)
        self.max_items = max_items
        self.container_type = kwargs.pop('container_type', list)
        super(ListField, self).__init__(**kwargs)

    def add_value(self, container, value):
        if self.container_type is list:
            container.append(value)
        elif self.container_type is set:
            container.add(value)

    def validate(self, value, field=None):
        """Make sure that a list of valid fields is being used."""
        if not isinstance(value, (list, tuple, set)):
            raise InvalidFieldValueException('Only lists and tuples may be used in a list field',
                                             field=field, value=value)

        container = self.container_type()
        if self.element_validator is not None:
            for val in value:
                self.add_value(container, self.element_validator.validate(val, field=field))
        else:
            if not isinstance(value, self.container_type):
                container = self.container_type(value)
            else:
                container = value

        if self.max_items and len(container) > self.max_items:
            raise InvalidFieldValueException("Too many items in list, "
                                             "max allowed: %d, passed: %r" % (self.max_items, len(container)))
        return super(ListField, self).validate(container, field=field)


class DictField(BaseField):
    """A dictionary field that parses a standard Python dictionary.
    `keys` and `values` are converted to validator types if validators are passed

    Default value: {}
    """

    def __init__(self, key_validator=None, value_validator=None, choices=None, **kwargs):
        self.key_validator = self._validate_validator(key_validator)
        self.value_validator = self._validate_validator(value_validator)

        super(DictField, self).__init__(**kwargs)

    def validate(self, value, field=None):
        """Make sure that a list of valid fields is being used."""
        if not isinstance(value, dict):
            raise InvalidFieldValueException('Only dictionaries may be used in a dict field',
                                             field=field, value=value)
        value_dict = {}

        if self.key_validator is not None or self.value_validator is not None:
            for key, val in value.iteritems():
                if self.key_validator is not None:
                    validated_key = self.key_validator.validate(key, field=field)
                else:
                    validated_key = key

                if self.value_validator is not None:
                    validated_value = self.value_validator.validate(val, field=field)
                else:
                    validated_value = val
                value_dict[validated_key] = validated_value
        else:
            value_dict = value

        return super(DictField, self).validate(value_dict, field=field)


class EmbeddedField(BaseField):
    """A SimpleDocument field that wraps a Simple document object."""

    def __init__(self, document, **kwargs):
        from p2ee.orm.models.base import SimpleDocument
        if not issubclass(document, SimpleDocument):
            raise InvalidFieldValueException('Invalid document')

        self.document = document
        super(EmbeddedField, self).__init__(**kwargs)

    def validate(self, value, field=None):
        doc = self.document(**value) if not isinstance(value, self.document) else value
        return super(EmbeddedField, self).validate(doc, field=field)


class BooleanField(BaseField):
    def __init__(self, **kwargs):
        kwargs.setdefault('default', False)
        super(BooleanField, self).__init__(**kwargs)

    def validate(self, value, field=None):
        if not isinstance(value, bool):
            raise InvalidFieldValueException('Only boolean field is accepted', field=field,
                                             value=value)

        return super(BooleanField, self).validate(value, field=field)


class DateTimeField(BaseField):
    def __init__(self, **kwargs):
        kwargs.setdefault('default', datetime.datetime.utcnow)
        super(DateTimeField, self).__init__(**kwargs)

    def validate(self, value, field=None):
        if not isinstance(value, datetime.datetime):
            try:
                value = parser.parse(value, ignoretz=True)
            except ValueError:
                raise InvalidFieldValueException('Not a valid datetime value', field=field, value=value)
        return super(DateTimeField, self).validate(value, field=field)


class FloatField(IntField):
    def _instance_check(self, value, field=None):
        if isinstance(value, (long, int)):
            value = float(value)
        if not isinstance(value, float):
            raise InvalidFieldValueException('Value must be a valid float', field=field, value=value)
        return value
