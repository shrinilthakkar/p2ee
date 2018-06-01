import json
from nose_parameterized import parameterized
import six
from unittest import TestCase

from p2ee.orm.models.base import SimpleDocument
from p2ee.orm.models.base.fields import IntField, EmailField, DictField, ListField, StringField
from p2ee.orm.models.exceptions import InvalidFieldValueException


class TestSimpleDocument(TestCase):

    @parameterized.expand([
        #
        # Parameters:
        #   <FieldType>
        #   <FieldKwargs>
        #   <ObjectKwargs>
        #   <ExpectedToDict>
        #   <ExpectedFieldValue>
        #   <ExpectedFieldTypeInToDict>
        #
        # Valid cases IntField
        (
            IntField, {'default': 5}, {}, {'my_field': 5}, 5, int
        ), (
            IntField, {'default': 5}, {'my_field': 10}, {'my_field': 10}, 10, int
        ), (
            IntField, {'default': 5, 'min_value': 2, 'max_value': 10, 'choices': [2, 5, 7, 10]},
            {'my_field': 7}, {'my_field': 7}, 7, int
        ), (
            IntField, {'min_value': 2, 'max_value': 10, 'choices': [2, 5, 7, 10]},
            {'my_field': 7}, {'my_field': 7}, 7, int
        ), (
            IntField, {'choices': [2, 5, 7, 10]}, {'my_field': 7}, {'my_field': 7}, 7, int
        ),

        # Valid cases StringField
        (
            StringField, {'default': 'STRING'}, {}, {'my_field': 'STRING'}, 'STRING',
            six.string_types
        ), (
            StringField, {'default': 'STRING1'}, {'my_field': 'STRING'}, {'my_field': 'STRING'},
            'STRING', six.string_types
        ), (
            StringField, {'default': 'STRING1', 'min_length': 2, 'max_length': 15},
            {'my_field': 'STRING'}, {'my_field': 'STRING'}, 'STRING', six.string_types
        ), (
            StringField, {'choices': ['STR1', 'STR2', 'STR3']}, {'my_field': 'STR2'},
            {'my_field': 'STR2'}, 'STR2', six.string_types
        ), (
            StringField, {'choices': ['STR1', 'STR2', 'STR3'], 'regex': 'STR[0-9]'},
            {'my_field': 'STR2'}, {'my_field': 'STR2'}, 'STR2', six.string_types
        ),

        # Valid cases EmailField
        (
            EmailField, {'default': 'abc@abc.com'}, {}, {'my_field': 'abc@abc.com'},
            'abc@abc.com', six.string_types
        ), (
            EmailField, {'default': 'def@def.com'}, {'my_field': 'abc@abc.com'},
            {'my_field': 'abc@abc.com'}, 'abc@abc.com', six.string_types
        ), (
            EmailField, {'default': 'def@def.com', 'min_length': 5, 'max_length': 25},
            {'my_field': 'abc@abc.com'}, {'my_field': 'abc@abc.com'}, 'abc@abc.com',
            six.string_types
        ), (
            EmailField, {'choices': ['abc@abc.com', 'def@def.com']}, {'my_field': 'abc@abc.com'},
            {'my_field': 'abc@abc.com'}, 'abc@abc.com', six.string_types
        ),

        # Valid cases ListField
        (
            ListField, {'default': ['1']}, {}, {'my_field': ['1']}, ['1'], (list, tuple, set)
        ), (
            ListField, {'default': ['2']}, {'my_field': ['1']}, {'my_field': ['1']}, ['1'],
            (list, tuple)
        ), (
            ListField, {'default': ['2'], 'element_validator': StringField()}, {'my_field': ['1']},
            {'my_field': ['1']}, ['1'], (list, tuple)
        ), (
            ListField, {'default': [2], 'element_validator': IntField()}, {'my_field': [1, 2, 3]},
            {'my_field': [1, 2, 3]}, [1, 2, 3], (list, tuple)
        ), (
            ListField, {'default': [[2]], 'element_validator': ListField(element_validator=IntField())},
            {'my_field': [[1], [2]]}, {'my_field': [[1], [2]]}, [[1], [2]], (list, tuple)
        ),

        # Valid cases DictField
        (
            DictField, {'default': {1: 1}}, {}, {'my_field': {1: 1}}, {1: 1}, dict
        ), (
            DictField, {'default': {2: 2}}, {'my_field': {1: 1}}, {'my_field': {1: 1}}, {1: 1}, dict
        ), (
            DictField, {'default': {'2': 2}, 'key_validator': StringField()}, {'my_field': {'1': 1}},
            {'my_field': {'1': 1}}, {'1': 1}, dict
        ), (
            DictField, {'default': {'2': 2}, 'key_validator': StringField()}, {'my_field': {'1': '1'}},
            {'my_field': {'1': '1'}}, {'1': '1'}, dict
        ), (
            DictField, {'default': {2: '2'}, 'key_validator': IntField(),
                        'value_validator': StringField()}, {'my_field': {1: '1'}},
            {'my_field': {1: '1'}}, {1: '1'}, dict
        ), (
            DictField, {'default': {2: ['2']}, 'key_validator': IntField(),
                        'value_validator': ListField(element_validator=StringField())},
            {'my_field': {1: ['1']}}, {'my_field': {1: ['1']}}, {1: ['1']}, dict
        ),
    ])
    def test_unit_valid_field_and_value(self, field_type, field_kwargs, obj_kwargs, to_dict,
                                        field_value, to_dict_field_type):
        class Dummy(SimpleDocument):
            my_field = field_type(**field_kwargs)

            def __init__(self, **kwargs):
                super(Dummy, self).__init__(**kwargs)

        obj = Dummy(**obj_kwargs)
        print obj.to_dict(), to_dict
        self.assertDictEqual(obj.to_dict(), to_dict, msg="to_dict should return correct dict")
        self.assertEqual(obj.to_json(), json.dumps(to_dict),
                         msg="to_json should return correct json")
        self.assertEqual(obj.my_field, field_value)
        self.assertEqual(obj['my_field'], field_value)
        self.assertIsInstance(obj.get_schema('my_field'), field_type,
                              msg="my_field should be %s instance in schema dict"
                                  % str(field_type))
        self.assertIsInstance(obj.__dict__.get('my_field'), to_dict_field_type,
                              msg="my_field in __dict__ should be of %s type"
                                  % str(to_dict_field_type))

    @parameterized.expand([
        #
        # Parameters:
        #   <FieldType>
        #   <FieldKwargs>
        #   <ObjectKwargs>
        #   <InvalidMessage>

        # Invalid validations for IntField
        #
        # Enforce choices
        (
            IntField, {'choices': [1, 2, 3, 5]}, {'my_field': 4}, 'Value not in allowed list'
        ), (
            IntField, {'choices': [1, 2, 3, 5]}, {'my_field': 6}, 'Value not in allowed list'
        ),

        # Invalid validations for StringField
        #
        # Enforce min_length
        (StringField, {'min_length': 3, 'max_length': 4}, {'my_field': 'ST'}, 'Value too short'),
        # Enforce max_length
        (StringField, {'min_length': 3, 'max_length': 4}, {'my_field': 'STR12'}, 'Value too long'),
        # Enforce choice
        (
            StringField, {'choices': ['STR1', 'STR2', 'STR3']}, {'my_field': 'STR4'},
            'Value not in allowed list'
        ),

    ])
    def test_unit_invalid_field_and_value(self, field_type, field_kwargs, obj_kwargs, msg):
        class Dummy(SimpleDocument):
            my_field = field_type(**field_kwargs)

            def __init__(self, **kwargs):
                super(Dummy, self).__init__(**kwargs)

        try:
            Dummy(**obj_kwargs)
            self.assertTrue(False, msg="Validation should fail: %s" % msg)
        except InvalidFieldValueException:
            self.assertTrue(True)
