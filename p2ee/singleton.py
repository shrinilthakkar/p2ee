import inspect
import threading

def get_default_args(func):
    """
    returns a dictionary of arg_name:default_values for the input function
    """
    if func:
        args, _, _, defaults = inspect.getargspec(func)
        if defaults:
            return dict(zip(args[-len(defaults):], defaults))
    return dict()


DEFAULT_INSTANCE_NAME_KEY = 'MOE_DEFAULT_INSTANCE_NAME'


class NamedInstanceMetaClass(type):
    def __init__(cls, name, bases, dictionary):
        instance_name_arg = dictionary.pop('INSTANCE_NAME_INIT_ARG', None)
        super(NamedInstanceMetaClass, cls).__init__(cls, bases, dictionary)
        cls._instances = {}
        cls._instance_lock = threading.Lock()
        cls._default_init_args = get_default_args(dictionary.get('__init__'))
        cls._instance_name_init_arg = instance_name_arg
        if len(cls.__mro__) > 1:
            # Merge values from super class
            try:
                super_instance_name_arg = cls.__mro__[1]._instance_name_init_arg
                cls._instance_name_init_arg = cls._instance_name_init_arg or super_instance_name_arg
            except AttributeError:
                pass

    def __call__(cls, *args, **kwargs):
        # Access instance_name from kwargs if passed. If missing in kwargs,
        # access it from default values specified in __init__. If not found in default values, use arg[0],
        # if everything else fails, call it default_instance
        instance_name_key = cls._instance_name_init_arg or DEFAULT_INSTANCE_NAME_KEY
        # instance name is popped from the kwargs, so that it will not get passed down to implemented classes.
        instance_name = kwargs.pop(DEFAULT_INSTANCE_NAME_KEY, None) or kwargs.get(cls._instance_name_init_arg) or\
                        cls._default_init_args.get(instance_name_key, args[0] if args else 'default_instance')
        if instance_name not in cls._instances:
            with cls._instance_lock:
                if instance_name not in cls._instances:
                    instance = super(NamedInstanceMetaClass, cls).__call__(*args, **kwargs)
                    cls._instances[instance_name] = instance
        return cls._instances[instance_name]


class SingletonMetaClass(NamedInstanceMetaClass):
    def __init__(cls, name, bases, dictionary):
        dictionary['INSTANCE_NAME_INIT_ARG'] = DEFAULT_INSTANCE_NAME_KEY
        super(SingletonMetaClass, cls).__init__(cls, bases, dictionary)

    def __call__(cls, *args, **kwargs):
        # if kwargs also contain instance_name key word, it will get popped here.
        # kwargs.pop(DEFAULT_INSTANCE_NAME_KEY, None)
        kwargs[DEFAULT_INSTANCE_NAME_KEY] = 'singleton_instance'
        return super(SingletonMetaClass, cls).__call__(*args, **kwargs)
