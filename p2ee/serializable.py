from datetime import timedelta

from enum import Enum


class SerializableObject(object):
    @classmethod
    def serialize(cls, value):
        if isinstance(value, list):
            if len(value) > 0:
                item = value[0]
                if isinstance(item, SerializableObject):
                    return map(lambda x: x.to_dict(), value)
        elif isinstance(value, dict):
            return {str(k): cls.serialize(v) for k, v in value.items()}
        elif isinstance(value, SerializableObject):
            return value.to_dict()
        elif isinstance(value, Enum):
            return str(value)
        elif isinstance(value, timedelta):
            return value.total_seconds()
        return value

    def to_dict(self):
        return self.to_dict_object(self.__dict__)

    def to_json(self):
        from p2ee.utils.common_utils import CommonUtils
        return CommonUtils.to_json(self.to_dict())

    @classmethod
    def to_dict_object(cls, object_dict):
        return {k[1:] if k.startswith('_') and k != '_id' else k: cls.serialize(v)
                for k, v in object_dict.items() if v is not None}
