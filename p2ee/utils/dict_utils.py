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
            return json.dumps(dictionary, default=cls.serializable, **kwargs)
        except TypeError:
            return cls.to_json(cls.to_serializable_dict(dictionary), **kwargs)

    @classmethod
    def to_serializable_dict(cls, dictionary, serializer=None):
        serializer = serializer or cls.serializable
        return {
            serializer(k, serializer=serializer): serializer(v, serializer=serializer)
            for k, v in dictionary.items()
        }

    @classmethod
    def serializable(cls, o, serializer=None):
        from p2ee.serializable import SerializableObject
        serializer = serializer or cls.serializable
        if isinstance(o, (Enum, ObjectId, timedelta)):
            return str(o)
        elif isinstance(o, datetime):
            return o.isoformat()
        # Check if o is an instance of a python class
        elif hasattr(o, '__name__'):
            return {k[1:] if k.startswith('_') else k: v for k, v in o.__dict__.items() if v}
        elif isinstance(o, dict):
            return {
                serializer(key, serializer=serializer): serializer(value, serializer=serializer)
                for key, value in o.items()
            }
        elif isinstance(o, (list, set)):
            serialized = list()
            for item in o:
                serialized.append(serializer(item, serializer=serializer))
            return serialized
        elif isinstance(o, SerializableObject):
            return o.to_dict()
        else:
            return o
