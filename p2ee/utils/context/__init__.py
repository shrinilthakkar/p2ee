from p2ee.utils.common_utils import CommonUtils
from p2ee.utils.package_utils import PackageUtils
import os
import socket


GLOBAL_CONTEXT = {
    'correlationId': CommonUtils.generateRandomString(6),
    'pid': str(os.getpid()),
    'host': socket.gethostbyname(socket.gethostname()),
    'env': PackageUtils.getExecutionEnv(),
    'region': PackageUtils.getInstanceMeta()['region']
}
