import random
import site
import string
import sys

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
