import random
import site
import string
import sys
import pkg_resources
import json
import os
import pwd
import grp

from p2ee.utils.package_utils import PackageUtils
from p2ee.utils.dict_utils import DictUtils


class CommonUtils(DictUtils):

    @staticmethod
    def getEnv():
        return PackageUtils.getExecutionEnv()

    @staticmethod
    def getFunctionCallerInfo(function_call_level):
        func = sys._getframe(function_call_level).f_code
        return {'func_call_info': func.co_name + '@' + func.co_filename + ':' + str(func.co_firstlineno)}

    @classmethod
    def create_path(cls, path, permissions, owner=None, group=None):
        os.makedirs(path, permissions)
        os.chmod(path, permissions)
        path_stat = os.stat(path)
        owner = owner or pwd.getpwuid(path_stat.st_uid)[0]
        group = group or grp.getgrgid(path_stat.st_gid)[0]
        os.chown(path, pwd.getpwnam(owner).pw_uid, grp.getgrnam(group).gr_gid)

    @classmethod
    def ensure_path(cls, path, permissions, owner=None, group=None):
        path_components = list(os.path.split(path))
        current_path = '/'
        created = False
        for path_component in path_components:
            current_path = os.path.join(current_path, path_component)
            if not os.path.exists(current_path):
                cls.create_path(current_path, permissions, owner=owner, group=group)
                created = True
        return created

    @staticmethod
    def convertCodePathToDotNotation(code_path):
        try:
            dist_packages = site.getsitepackages()
            module_path = code_path
            for location in dist_packages:
                module_path = code_path.replace(location, '', 1)
                if module_path != code_path:
                    break
            module_components = module_path.split("/")
            module_path_dot_notation = map(lambda x: x[:1], module_components[:-1])
            return ".".join(module_path_dot_notation + module_components[-1:]).strip(".")
        except Exception:
            return code_path

    @staticmethod
    def generateRandomString(string_length):
        return ''.join(random.sample(string.letters * 5, string_length))

    @classmethod
    def readResourceString(cls, module, path):
        return pkg_resources.resource_string(module, path)

    @classmethod
    def ensure_folder_path(cls, file_path, permissions, owner=None, group=None):
        return cls.ensure_path(os.path.dirname(file_path), permissions, owner=owner, group=group)

    @classmethod
    def readPackageResourceJson(cls, module, path):
        return json.loads(cls.readResourceString(module, path))