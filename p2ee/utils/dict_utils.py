import json
from datetime import datetime, timedelta
from enum import Enum
from bson.objectid import ObjectId


class DictUtils(object):

    @classmethod
    def deepMergeDictionaries(cls, dict_source, dict_to_merge):
        for key in dict_to_merge:
            if key in dict_source:
                if isinstance(dict_source[key], dict) and isinstance(dict_to_merge[key], dict):
                    dict_source[key] = cls.deepMergeDictionaries(dict_source[key], dict_to_merge[key])
                else:
                    dict_source[key] = dict_to_merge[key]
            else:
                dict_source[key] = dict_to_merge[key]
        return dict_source

    @classmethod
    def to_json(cls, dictionary, **kwargs):
        try:
            return json.dumps(dictionary, default=cls.orm_serialize, **kwargs)
        except TypeError:
            return cls.to_json(cls.to_serializable_dict(dictionary), **kwargs)

    @classmethod
    def to_serializable_dict(cls, dictionary, serializer=None):
        serializer = serializer or cls.orm_serialize
        return {
            serializer(k, serializer=serializer): serializer(v, serializer=serializer)
            for k, v in dictionary.items()
        }

    @classmethod
    def json_serialize(cls, o, serializer=None):
        serializer = serializer or cls.json_serialize
        if isinstance(o, (Enum, ObjectId, timedelta)):
            return str(o)
        elif isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, dict):
            return {
                serializer(key, serializer=serializer): serializer(value, serializer=serializer)
                for key, value in o.items()
            }
        elif isinstance(o, (list, set)):
            return map(lambda item: serializer(item, serializer=serializer), o)
        else:
            return o

    @classmethod
    def orm_serialize(cls, o):
        from p2ee.orm.models.base import SimpleDocument
        from p2ee.orm.models.base.fields import BaseField
        if isinstance(o, SimpleDocument):
            return o.to_dict()
        elif isinstance(o, BaseField):
            return o.default
        elif isinstance(o, (datetime, ObjectId, Enum)):
            return o
        else:
            return cls.json_serialize(o)
