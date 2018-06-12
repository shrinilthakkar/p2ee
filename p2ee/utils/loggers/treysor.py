import datetime
import logging.handlers
import os
import threading
import traceback
import sys
from threading import Lock

from p2ee.orm.models.enum_type import StringEnum
from p2ee.utils.package_utils import PackageUtils
from p2ee.orm.models.base.fields import IntField, EnumField, StringField
from p2ee.singleton import NamedInstanceMetaClass
from p2ee.utils.loggers.provider import LogConfigProvider
from p2ee.orm.models.base import SimpleSchemaDocument
from p2ee.utils.context.thread import ThreadContext
from p2ee.utils.context import GLOBAL_CONTEXT
from p2ee.utils.common_utils import CommonUtils


class LogFormat(StringEnum):
    TEXT = "text"
    JSON = "json"

    def get_formatter(self):
        return {
            LogFormat.TEXT: "%(threadName)s-%(asctime)s [%(levelname)s] - %(message)s",
            LogFormat.JSON: "%(message)s"
        }.get(self)


class LoggingConfig(SimpleSchemaDocument):
    file_path = StringField()
    log_level = IntField(min_value=logging.DEBUG, max_value=logging.CRITICAL,
                         choices=[logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL],
                         default=LogConfigProvider().get_log_level())
    log_format = EnumField(enum_class=LogFormat, default=LogFormat.JSON)
    log_type = StringField()
    domain = StringField(choices=set(LogConfigProvider().get_domains()),
                         default='unknown')

    @staticmethod
    def get_domain_from_log_type(domain):
        return domain.split('.')[0]

    def get_logging_base_path(self):
        if PackageUtils.isVirtualEnv():
            log_folder_path = sys.prefix
        elif PackageUtils.isLambdaEnv():
            log_folder_path = '/var/task'
        else:
            log_folder_path = '/var/log'
        return os.path.join(log_folder_path, 'treysor')

    def get_file_path(self):
        if self.file_path is None:
            self.file_path = "{base_path}/{domain}/{pid}.log".format(
                base_path=self.get_logging_base_path(),
                domain=str(self.domain),
                pid=str(GLOBAL_CONTEXT['pid'])
            )
        return self.file_path


class Treysor(object):
    __metaclass__ = NamedInstanceMetaClass
    INSTANCE_NAME_INIT_ARG = 'log_type'
    SETUP_LOCK = Lock()

    def __init__(self, log_type='commons', logging_config=None):
        domain = LoggingConfig.get_domain_from_log_type(log_type)
        self.logging_config = logging_config or LoggingConfig(log_type=log_type, domain=domain)
        self._context = ThreadContext(
            log_type=self.logging_config.log_type,
            log_domain=str(self.logging_config.domain),
            **GLOBAL_CONTEXT
        )
        self._logger = self.setup_logger(logging_config=self.logging_config)

    @classmethod
    def setup_logger(cls, logging_config):
        logger = logging.getLogger(str(logging_config.log_type))
        with cls.SETUP_LOCK:
            formatter = logging.Formatter(logging_config.log_format.get_formatter())
            logger.setLevel(logging_config.log_level)
            if not PackageUtils.isLambdaEnv():
                log_file_path = logging_config.get_file_path()
                CommonUtils.ensure_folder_path(log_file_path, 0o776, owner=LogConfigProvider().get_log_dir_owner(),
                                               group=LogConfigProvider().get_log_dir_group())

                for handler in logger.handlers:
                    logger.removeHandler(handler)

                file_handler = logging.handlers.WatchedFileHandler(filename=log_file_path)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)

            if CommonUtils.getEnv() != 'prod' or PackageUtils.isLambdaEnv():
                stream_handler = logging.StreamHandler()
                stream_handler.setFormatter(formatter)
                logger.addHandler(stream_handler)

        return logger

    def updateContext(self, **kwargs):
        """
        Update the context for the current thread for this domain's logger
        :param kwargs:
        :return:
        """
        self._context.updateContext(**kwargs)

    def setContext(self, **kwargs):
        """
        Set this as the new context for this thread
        :param kwargs:
        :return:
        """
        self.clearContext()
        self.updateContext(**kwargs)

    def getContext(self):
        """
        Get the current context for this thread
        :return: current context of the calling thread
        """
        return self._context.to_dict()

    def clearContext(self):
        """
        Clear the context set by the current thread
        :return:
        """
        self._context.clearContext()

    def removeContext(self, *keys):
        """
        Remove keys from context set by the current thread
        :return:
        """
        self._context.removeContext(*keys)

    def to_json(self, log_dict):
        try:
            return CommonUtils.to_json(log_dict)
        except Exception, e:
            return "Failed to serialize log line into json," \
                   "skipping treysor log - %r due to exception: %r" % (log_dict, e)

    def __get_log_message(self, **kwargs):
        """
        Construct a log message to be logged
        :param kwargs:
        :return:
        """
        message = ""
        # The parameter `3` to `getFunctionCallerInfo` indicates the nesting level of the _getframe call made.
        # _getframe returns the frame `n` levels above the current frame (from where _getframe is called)
        # In our case _getframe is called inside getFunctionCallerInfo. This call to _getframe is 3 levels nested
        # wrt to the point where the log statement was actually added.
        # The 3 nesting levels are -> treysor().info --> __get_log_message --> getFunctionCallerInfo --> _getframe
        if self.logging_config.log_format == LogFormat.TEXT:
            caller_info = CommonUtils.getFunctionCallerInfo(3)
            line_info = ""
            if 'func_call_info' in caller_info:
                file_info = caller_info['func_call_info'].split('@')
                if len(file_info) >= 2:
                    line_info = file_info[1]
            message += "[" + CommonUtils.convertCodePathToDotNotation(line_info) + ": " + \
                      threading.currentThread().name + "] " + kwargs.get('treysor_log_msg', "") + \
                      "\n" + kwargs.get("exception", "")
        else:
            # Get logging function's info
            if self._logger.getEffectiveLevel() > logging.INFO:
                log_dict = CommonUtils.getFunctionCallerInfo(3)
            else:
                log_dict = dict()
            # Add current context to log_message
            log_dict.update(self._context.to_dict())
            # Add log timestamp
            log_dict['log_timestamp'] = datetime.datetime.utcnow()
            # Add realtime log line params
            log_dict.update(kwargs)
            message += self.to_json(log_dict)
        return message

    def get_formatted_treysor_log_msg(self, treysor_log_msg, *args):
        if treysor_log_msg and len(args) > 0:
            treysor_log_msg = treysor_log_msg % args
        return treysor_log_msg

    def debug(self, treysor_log_msg=None, *args, **kwargs):
        kwargs.pop('log_level', None)
        if treysor_log_msg:
            kwargs['treysor_log_msg'] = self.get_formatted_treysor_log_msg(treysor_log_msg, *args)
        if self._logger.getEffectiveLevel() <= logging.DEBUG:
            self._logger.debug(self.__get_log_message(log_level='DEBUG', **kwargs))

    def info(self, treysor_log_msg=None, *args, **kwargs):
        kwargs.pop('log_level', None)
        if treysor_log_msg:
            kwargs['treysor_log_msg'] = self.get_formatted_treysor_log_msg(treysor_log_msg, *args)
        if self._logger.getEffectiveLevel() <= logging.INFO:
            self._logger.info(self.__get_log_message(log_level='INFO', **kwargs))

    def warning(self, treysor_log_msg=None, *args, **kwargs):
        kwargs.pop('log_level', None)
        if treysor_log_msg:
            kwargs['treysor_log_msg'] = self.get_formatted_treysor_log_msg(treysor_log_msg, *args)
        if self._logger.getEffectiveLevel() <= logging.WARNING:
            self._logger.warning(self.__get_log_message(log_level='WARNING', **kwargs))

    def warn(self, treysor_log_msg=None, *args, **kwargs):
        self.warning(treysor_log_msg=treysor_log_msg, *args, **kwargs)

    def error(self, treysor_log_msg=None, *args, **kwargs):
        kwargs.pop('log_level', None)
        if treysor_log_msg:
            kwargs['treysor_log_msg'] = self.get_formatted_treysor_log_msg(treysor_log_msg, *args)
        if self._logger.getEffectiveLevel() <= logging.ERROR:
            self._logger.error(self.__get_log_message(log_level='ERROR', **kwargs))

    def log(self, treysor_log_msg=None, *args, **kwargs):
        if treysor_log_msg:
            kwargs['treysor_log_msg'] = self.get_formatted_treysor_log_msg(treysor_log_msg, *args)
        self.info(**kwargs)

    def exception(self, treysor_log_msg=None, *args, **kwargs):
        if treysor_log_msg:
            kwargs['treysor_log_msg'] = self.get_formatted_treysor_log_msg(treysor_log_msg, *args)
        kwargs.pop('exception', None)
        kwargs.pop('log_level', None)
        self._logger.error(self.__get_log_message(log_level='EXCEPTION', exception=traceback.format_exc(), **kwargs))

    def critical(self, treysor_log_msg=None, *args, **kwargs):
        if treysor_log_msg:
            kwargs['treysor_log_msg'] = self.get_formatted_treysor_log_msg(treysor_log_msg, *args)
        kwargs.pop('exception', None)
        kwargs.pop('log_level', None)
        self._logger.error(self.__get_log_message(log_level='CRITICAL', exception=traceback.format_exc(), **kwargs))

    def fatal(self, treysor_log_msg=None, *args, **kwargs):
        self.critical(treysor_log_msg=treysor_log_msg, *args, **kwargs)

    @property
    def correlationId(self):
        return GLOBAL_CONTEXT.get('corr_id')

    @property
    def pid(self):
        return GLOBAL_CONTEXT.get('pid')

    @property
    def host(self):
        return GLOBAL_CONTEXT.get('host')

    @property
    def domain(self):
        return self.logging_config.domain

    def update_logging_config(self, logging_config):
        self._logger = self.setup_logger(logging_config)
