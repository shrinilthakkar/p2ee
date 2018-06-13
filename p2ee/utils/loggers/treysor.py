import datetime
import grp
import logging.handlers
import os
import pwd
import threading
import traceback

from enum import Enum

from p2ee.threadsafe import ThreadContext, GLOBAL_CONTEXT
from p2ee.utils.common_utils import CommonUtils
from p2ee.models.base import SimpleSchemaDocument


class LogFormat(Enum):
    TEXT = 1
    JSON = 2

    def __str__(self):
        return {
            LogFormat.TEXT: "text",
            LogFormat.JSON: "json"
        }.get(self)

    @staticmethod
    def fromStr(value):
        return {
            "text": LogFormat.TEXT,
            "json": LogFormat.JSON
        }.get(value)


class LoggingConfig(SimpleSchemaDocument):
    def __init__(self, **kwargs):
        """
            Structure for treysor logging
            log_levels = [logging.ERROR,logging.WARNING,logging.INFO,logging.DEBUG]
            log_level is index of log level from this string
            EXCEPTION = ERROR
        """
        self._log_level = 2
        self._filename = self.get_default_filename()
        self.when = "D"
        self.interval = 1
        self.backup_count = 7
        self.log_format = LogFormat.JSON
        super(LoggingConfig, self).__init__(**kwargs)

    @classmethod
    def get_default_filename(cls):
        pid = str(os.getpid())
        log_file_path = '/var/log/treysor/treysor_pid.log'
        return log_file_path.replace("pid", pid)

    @property
    def log_level(self):
        return self._log_level

    @log_level.setter
    def log_level(self, log_level_index):
        log_levels = [
            logging.ERROR,
            logging.WARNING,
            logging.INFO,
            logging.DEBUG
        ]
        self._log_level = log_levels[log_level_index]

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, filename):
        if filename is None:
            filename = self.get_default_filename()
        self._filename = filename

    @classmethod
    def required_fields(cls):
        return ['log_level', 'filename', 'when', 'interval', 'backup_count']

    def validate_schema_document(self, invalid_fields=None):
        invalid_fields = invalid_fields or []
        for key in self.required_fields():
            if not self[key]:
                invalid_fields.append(key)
        super(LoggingConfig, self).validate_schema_document(invalid_fields=invalid_fields)


class TreysorMeta(type):
    def __init__(cls, name, bases, dictionary):
        super(TreysorMeta, cls).__init__(cls, bases, dictionary)
        cls._loggers = {}
        cls._lock = threading.Lock()
        # create global context - doesnt change for a single running process
        cls._default_context = GLOBAL_CONTEXT

    def __call__(cls, *args, **kwargs):
        """
        Called before each logger instance creation
        :param args:
        :param kwargs:
        :return:
        """
        # Get domain name from logger constructor - defaults to commons
        domain = kwargs.get('domain', args[0] if args else 'moengage_commons')
        # try to get any existing logger for this domain
        logger = cls._loggers.get(domain)
        if not logger:
            with cls._lock:
                if not cls._loggers.get(domain):
                    # If logger not found, create one
                    logger = super(TreysorMeta, cls).__call__(*args, **kwargs)
                    cls._loggers[domain] = logger
                else:
                    logger = cls._loggers.get(domain)
        return logger

    @classmethod
    def setup_logger(mcs, logger, logging_config):
        log_file_path = logging_config['filename']
        log_directory = os.path.dirname(log_file_path)
        if not os.path.exists(log_directory):
            os.makedirs(log_directory)
            os.chmod(log_directory, 0o764)
            os.chown(log_directory, pwd.getpwnam("ubuntu").pw_uid, grp.getgrnam("syslog").gr_gid)
        if logging_config.get('log_format') == str(LogFormat.TEXT):
            formatter = logging.Formatter('%(threadName)s-%(asctime)s [%(levelname)s] - %(message)s')
        else:
            formatter = logging.Formatter("%(message)s")
        file_handler = logging.handlers.WatchedFileHandler(filename=log_file_path)
        # file_handler = logging.handlers.TimedRotatingFileHandler(log_file_path, when=logging_config['when'],
        #                                                          interval=logging_config['interval'],
        #                                                          backupCount=logging_config['backup_count'])
        stream_handler = logging.StreamHandler()
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        if CommonUtils.getEnv() != 'prod':
            logger.addHandler(stream_handler)
        return logger

    @classmethod
    def setup_logging(mcs, logger_name, logging_config):
        # configure root logger
        log_level = logging_config['log_level']
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        return mcs.setup_logger(logger, logging_config)


class Treysor(object):
    __metaclass__ = TreysorMeta

    def __init__(self, domain='moengage_commons', logging_config=None):
        """
        Initialized only once per domain - handled in metaclass
        :param domain: MoEngage internal domains eg - segmentation, commons, inapps etc
        """
        self._logger = logging.getLogger(domain)
        self._domain = domain
        self._log_format = LogFormat.JSON
        # Each thread maintains a separate context (A context per thread per domain).
        # _context is a dictionary that maintains all those contexts
        # when reading context, current thread which is trying to read context is checked, and context for only that
        # thread is returned - Check ThreadContext class
        self._context = ThreadContext(LogType=self._domain, domain=self._domain, **self._default_context)
        treysor_logging_conf = LoggingConfig().to_dict()
        if logging_config and isinstance(logging_config, LoggingConfig):
            self._log_format = logging_config.log_format
            treysor_logging_conf = CommonUtils.deepMergeDictionaries(LoggingConfig().to_dict(),
                                                                     logging_config.to_dict())
        TreysorMeta.setup_logging(domain, treysor_logging_conf)

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
        if self._log_format == LogFormat.TEXT:
            caller_info = CommonUtils.getFunctionCallerInfo(3)
            line_info = ""
            if 'func_call_info' in caller_info:
                file_info = caller_info['func_call_info'].split('@')
                if len(file_info) >= 2:
                    line_info = file_info[1]
            message = "[" + CommonUtils.convertCodePathToDotNotation(line_info) + ": " + \
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
            message = self.to_json(log_dict)
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
        return self._default_context.get('correlationId')

    @property
    def pid(self):
        return self._default_context.get('pid')

    @property
    def host(self):
        return self._default_context.get('host')

    @property
    def domain(self):
        return self._domain

    def update_logging_config(self, logging_config):
        with self._lock:
            self._log_format = logging_config.log_format
            logger = logging.getLogger(self._domain)
            for handler in logger.handlers:
                logger.removeHandler(handler)
            treysor_logging_conf = LoggingConfig().to_dict()
            if logging_config and isinstance(logging_config, LoggingConfig):
                treysor_logging_conf = CommonUtils.deepMergeDictionaries(LoggingConfig().to_dict(),
                                                                         logging_config.to_dict())
            TreysorMeta.setup_logger(logger, treysor_logging_conf)
