from enum import Enum
from be_utils.utils import shell_exec,helm_response
from be_utils.oc_commands import OC
import re
from config.configParams import config


class HELMCommands(Enum):
    # INSTALL         = "helm install -f {values} {deployment_name} /home/cloud-user/genie-ai/pipelines/{pipeline} --output json --namespace {namespace}"
    INSTALL         = "helm install -f {values} {deployment_name} /opt/app-root/src/pipelines/{pipeline} --output json --namespace {namespace}"
    UNINSTALL       = "helm uninstall {deployment_name} --namespace {namespace}"
    # STATUS          = "helm status {deployment_name} --namespace {namespace}"
    # UPGRADE         = "helm upgrade {deployment_name} --reuse-values /opt/app-root/src/pipelines/pre_training_helm {helm_set_params} --output json --namespace {namespace}"
    # RMQROUTE        = "oc get {option} {deployment_name}-rabbitmq-{option} -o jsonpath={spec} --namespace {namespace}"
    # DBROUTE         = "oc get {option} {deployment_name}-mongodb-{option} -o jsonpath={spec} --namespace {namespace}"

class HELM:
    def __init__(self, api_url, namespace=None):
        self.api_url = api_url
        self.namespace = namespace


    def run_helm_command(self, command: HELMCommands, **kwargs):
        if not isinstance(command, HELMCommands):
            return helm_response(False, f"Error: Invalid Helm command {command}")

        oc = OC(api_url=self.api_url, namespace=self.namespace)
        if not oc.is_oc_logged_in():
            if not oc.oc_login():
                return helm_response(False, f"Error: Failed to log in to OpenShift cluster: {self.api_url}")          

        command_str = command.value.format(**kwargs).strip()
        rc, stdout = shell_exec(command_str)
        return helm_response(rc == 0, stdout.strip())