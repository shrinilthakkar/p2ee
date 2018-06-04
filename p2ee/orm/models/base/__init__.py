from threading import Lock

from p2ee.utils.dict_utils import DictUtils
from p2ee.orm.models.base.fields import BaseField, ObjectIdField
from p2ee.orm.models.exceptions import InvalidFieldValueException, InvalidFieldException

__all__ = ('SimpleDocument', 'SimpleSchemaDocument', 'SchemalessDocument', 'SchemaDocument')


class DocumentMetaClass(type):
    def __init__(cls, name, bases, dictionary):
        # Read from class variables to see if schema flexible is defined
        schema_flexible = dictionary.get('_schema_flexible', True)
        # Load the class
        super(DocumentMetaClass, cls).__init__(cls, bases, dictionary)
        # Set schema on class from class variables - Only BaseField allowed
        # cls._schema = {k: v for k, v in dictionary.items() if isinstance(v, BaseField)}
        cls._schema = {}
        for k, v in dictionary.items():
            if isinstance(v, BaseField):
                v.field_name = k
                cls._schema[k] = v
        # All class schemas are default flexible unless explicitly disabled
        cls._schema_flexible = schema_flexible
        cls._schema_lock = Lock()
        if len(cls.__mro__) > 1:
            # Merge values from super class
            try:
                cls._schema.update({k: v for k, v in cls.__mro__[1]._schema.items() if k not in cls._schema})
            except AttributeError:
                pass
            try:
                cls._schema_flexible = cls.__mro__[1]._schema_flexible and cls._schema_flexible
            except AttributeError:
                pass


class SimpleDocument(object):
    __metaclass__ = DocumentMetaClass

    def __new__(cls, *args, **kwargs):
        obj = super(SimpleDocument, cls).__new__(cls, *args, **kwargs)
        obj.__dict__['__object_initializing'] = True
        return obj

    def __init__(self, **kwargs):
        super(SimpleDocument, self).__init__()
        # __object_initializing should not be set on the class instance __dict__
        # Fields from subclass init have already been added to the schema, so __object_initializing from
        # object dict can safely be popped now
        self.__dict__.pop('__object_initializing', None)
        # Initialize the object with passed values
        self.__update(**kwargs)

    def __update(self, **kwargs):
        for key, schema in self._schema.items():
            # Remove underscore for models defining python properties (only _id is allowed and nothing else)
            # `self._name` should be checked as `name` in schema
            key_final = self.__get_key(key, schema=schema)
            # Check if value for the key has been passed in kwargs
            val = kwargs.pop(key_final, None)
            if val is None:
                # If value for a key isn't passed, use the schema to get the value to be set
                val = self.__unpack_schema(schema)
            if val is None:
                # Set None value in object without validating it
                super(SimpleDocument, self).__setattr__(key, val)
            else:
                # Try to call custom setter from SimpleDocument to set the value against the key in class dict
                self.__setattr__(key, val)
        # Handle fields not specified in schema
        if kwargs and not self._schema_flexible:
            # If something is left in kwargs and schema is not flexible, then we should raise an exception
            raise InvalidFieldException('Missing fields in document schema for class %s: %s' %
                                        (self.__class__.__name__, str(kwargs.keys())))
        else:
            # If something is left in kwargs and schema is flexible, then those attributes are added to object
            for extra_key, extra_value in kwargs.items():
                self.__setattr__(extra_key, extra_value)
        self.validate_schema_document()

    def get_schema(self, key):
        return self._schema.get(key)

    def __unpack_schema(self, schema):
        return schema.default if isinstance(schema, BaseField) else schema

    def __check_and_set_schema(self, key, schema=None):
        _key = '_' + key
        if key not in self._schema and _key not in self._schema:
            with self._schema_lock:
                if key not in self._schema and _key not in self._schema:
                    if '__object_initializing' in self.__dict__:
                        # Add keys to schema only when fields from __init__ in class definition are being
                        # initialized. While updating the values for those keys, schema shouldnt be updated
                        self._schema[key] = schema
                    elif not self._schema_flexible:
                        raise InvalidFieldException("Field: %s missing in Document Schema for %s" %
                                                    (key, self.__class__.__name__), field=key, missing=True)

    def get(self, key, default=None):
        try:
            return self.__getattribute__(key)
        except AttributeError:
            return default

    def pop(self, key, default=None):
        try:
            val = self.get(key, default=default)
            if val:
                super(SimpleDocument, self).__setattr__(key, None)
            return val
        except AttributeError:
            return default

    def update(self, model_update_spec=None, **kwargs):
        if not model_update_spec:
            model_update_spec = {}
        model_update_spec.update(kwargs)
        for key, value in model_update_spec.items():
            self[key] = value

    def __get_key(self, key, schema=None):
        if schema and isinstance(schema, BaseField) and schema.field_name:
            return schema.field_name
        return key[1:] if key.startswith('_') and key != '_id' else key

    def __eq__(self, other):
        if isinstance(other, SimpleDocument):
            return self.to_dict() == other.to_dict()
        return False

    def __contains__(self, item):
        try:
            self.__getattribute__(item)
            return True
        except AttributeError:
            return False

    def __getattribute__(self, item):
        value = super(SimpleDocument, self).__getattribute__(item)
        if value and isinstance(value, BaseField):
            value = value.default
        return value

    def __getitem__(self, item):
        # To enable dictionary like access to the document
        try:
            return self.__getattribute__(item)
        except AttributeError:
            return None

    def __setitem__(self, key, value):
        # To enable dictionary like access to the document
        self.__setattr__(key, value)

    def __setattr__(self, key, value):
        schema_key = self.__get_key(key)
        self.__check_and_set_schema(schema_key, schema=value)
        schema = self.get_schema(schema_key)
        if schema and isinstance(schema, BaseField):
            value = schema.validate(value)
        try:
            super(SimpleDocument, self).__setattr__(key, value)
        except UnicodeEncodeError:
            super(SimpleDocument, self).__setattr__(key.encode("utf-8"), value)

    def to_dict(self):
        """ Convert the document into a dictionary which can be saved
        :return: Dictionary with filtered fields to be saved in mongo
        """
        ret_dict = {}
        for key, val in self.__dict__.items():
            set_value = DictUtils.orm_serialize(val)
            if set_value is None:
                continue
            schema_key = self.__get_key(key)
            schema = self.get_schema(schema_key)
            key_final = self.__get_key(key, schema=schema)
            ret_dict[key_final] = set_value
        return ret_dict

    def to_json(self):
        """ JSON serialize the to_dict representation of the document
        :return: JSON String
        """
        return DictUtils.to_json(self.to_dict())

    def copy(self, **kwargs):
        class_dict = self.to_dict()
        class_dict.update(kwargs)
        return self.__class__(**class_dict)

    def __repr__(self):
        return self.to_json()

    def __deepcopy__(self, memodict=None):
        return self.copy()

    def __copy__(self):
        return self.copy()

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__ = state

    def validate_schema_document(self, invalid_fields=None):
        if invalid_fields:
            invalid_fields_str = ", ".join(invalid_fields)
            raise InvalidFieldValueException(
                'Some of the required field values are missing: {0}'.format(invalid_fields_str),
                field=invalid_fields_str)


class SimpleSchemaDocument(SimpleDocument):
    _schema_flexible = False


class SchemalessDocument(SimpleDocument):
    _id = ObjectIdField()

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value


class SchemaDocument(SimpleSchemaDocument):
    _id = ObjectIdField()

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value
