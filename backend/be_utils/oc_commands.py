from enum import Enum
from be_utils.utils import shell_exec,helm_response
import re
from config.configParams import config

class OCCommands(Enum):
    OC_WHOAMI       = "oc whoami"
    OC_SHOWSERVER   = "oc whoami --show-server"
    OC_LOGIN        = "oc login --token={cluster_access_token} --server={server} && oc project {namespace}"

class OC:
    def __init__(self, api_url, namespace=None):
        self.api_url = api_url
        self.namespace = namespace

    def is_oc_logged_in(self):
        prod_cluster = config.get("dpr", "prod_cluster")
        tenant_name = config.get("dpr","prod_tenant_name") if self.api_url == prod_cluster else config.get("dpr","preprod_tenant_name")
        command_str = OCCommands.OC_WHOAMI.value
        rc, stdout = shell_exec(command_str)
        command_str1 = OCCommands.OC_SHOWSERVER.value
        rc1, stdout1 = shell_exec(command_str1)
        logged_user_expression = r"system:serviceaccount:{}.*".format(re.escape(tenant_name))
        if rc == 0 and re.search(logged_user_expression, stdout):
            if rc1 == 0 and self.api_url == stdout1:
                return True
        return False
        
    def oc_login(self):
        prod_cluster = config.get("dpr", "prod_cluster")
        cluster_access_token = config.get("dpr","prod_access_token") if self.api_url == prod_cluster else config.get("dpr","preprod_access_token")

        command_str = OCCommands.OC_LOGIN.value.format(cluster_access_token=cluster_access_token, server=self.api_url, namespace=self.namespace)
        rc, stdout = shell_exec(command_str)
        logged_user_expression = r".*{}.*".format(re.escape(self.api_url))
        if rc == 0 and re.search(logged_user_expression, stdout):
            return True
        return False