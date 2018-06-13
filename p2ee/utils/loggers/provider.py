from p2ee.singleton import SingletonMetaClass


class LogConfigProvider(object):
    __metaclass__ = SingletonMetaClass

    def __init__(self):
        from p2ee.utils.common_utils import CommonUtils
        self.config = CommonUtils.readPackageResourceJson(__name__, 'config.json')

    def __str__(self):
        return "MoEngage - Log Config Provider"

    def get_logging_config(self):
        return self.config.get('logging', {})

    def get_log_level(self):
        return self.get_logging_config().get('log_level', 20)

    def get_domains(self):
        return self.get_logging_config().get('allowed_domains', [])

    def get_log_dir_config(self):
        return self.get_logging_config().get('log_directory', {})

    def get_log_dir_owner(self):
        return self.get_log_dir_config().get('owner', 'ubuntu')

    def get_log_dir_group(self):
        return self.get_log_dir_config().get('group', 'ubuntu')
