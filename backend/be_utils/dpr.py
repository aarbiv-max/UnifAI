from enum import Enum
from be_utils.utils import shell_exec,helm_response
import re
from config.configParams import config

class DPRCommands(Enum):
    # INSTALL         = "helm install -f {values}  {deployment_name} /home/cloud-user/AI-TC-s-Generator/pipelines/pre_training_helm --output json --namespace {namespace}"
    INSTALL         = "helm install -f {values} {deployment_name} /opt/app-root/src/pipelines/pre_training_helm --output json --namespace {namespace}"
    UNINSTALL       = "helm uninstall {deployment_name} --namespace {namespace}"
    STATUS          = "helm status {deployment_name} --namespace {namespace}"
    UPGRADE         = "helm upgrade {deployment_name} --reuse-values /opt/app-root/src/pipelines/pre_training_helm {helm_set_params} --output json --namespace {namespace}"
    RMQROUTE        = "oc get {option} {deployment_name}-rabbitmq-{option} -o jsonpath={spec} --namespace {namespace}"
    DBROUTE         = "oc get {option} {deployment_name}-mongodb-{option} -o jsonpath={spec} --namespace {namespace}"
    OC_WHOAMI       = "oc whoami"
    OC_SHOWSERVER   = "oc whoami --show-server"
    OC_LOGIN        = "oc login --token={cluster_access_token} --server={server} && oc project {namespace}"

class DPR:
    def __init__(self, api_url, token, namespace=None):
        self.api_url = api_url
        self.token = token
        self.namespace = namespace


    def run_dpr_command(self, command: DPRCommands, **kwargs):

        if not isinstance(command, DPRCommands):
            return helm_response(False, f"Error: Invalid Helm command {command}")

        if not self.is_oc_logged_in():
            if not self.oc_login():
                return helm_response(False, f"Error: Failed to log in to OpenShift cluster: {self.api_url}")          

        command_str = command.value.format(**kwargs).strip()
        rc, stdout = shell_exec(command_str)
        return helm_response(rc == 0, stdout.strip())

    def is_oc_logged_in(self):
        command_str = DPRCommands.OC_WHOAMI.value
        rc, stdout = shell_exec(command_str)
        command_str1 = DPRCommands.OC_SHOWSERVER.value
        rc1, stdout1 = shell_exec(command_str1)
        if rc == 0 and re.search(r"system:serviceaccount:tag-ai.*", stdout):
            if rc1 == 0 and self.api_url == stdout1:
                return True
        return False
        
    def oc_login(self):
        prod_cluster = config.get("dpr", "prod_cluster")
        cluster_access_token = config.get("dpr","prod_access_token") if self.api_url == prod_cluster else config.get("dpr","preprod_access_token")

        command_str = DPRCommands.OC_LOGIN.value.format(cluster_access_token=cluster_access_token, server=self.api_url, namespace=self.namespace)
        rc, stdout = shell_exec(command_str)
        if rc == 0 and re.search(r"Logged into*", stdout):
            return True
        return False