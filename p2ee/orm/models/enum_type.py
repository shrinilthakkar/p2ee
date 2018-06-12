from enum import Enum


class StringEnum(Enum):
    @classmethod
    def value_to_member_map(cls):
        return cls._value2member_map_

    @classmethod
    def member_to_value_map(cls):
        return {}

    def __str__(self):
        member_value_map = self.member_to_value_map()
        if self in member_value_map:
            return member_value_map[self]
        else:
            return str(self.value)

    @classmethod
    def fromStr(cls, value):
        return cls.value_to_member_map().get(value)

    @classmethod
    def all_enums(cls):
        return cls.value_to_member_map().values()

    @classmethod
    def all_strings(cls):
        return cls.value_to_member_map().keys()
