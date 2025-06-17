// pipeline-deploy.groovy

properties([
    parameters([
        choice(name: 'deployment_location', choices: ['STAGING', 'PRODUCTION'], description: 'Deployment environment'),
        choice(name: 'deployment_type', choices: ['FRESH_INSTALL', 'APPLICATION_UPGRADE'], description: 'Deployment type'),
        string(name: "namespace", defaultValue: "tag-ai--runtime-int", description: "K8s namespace"),
        string(name: "BRANCH", defaultValue: "main", description: "Branch to deploy from.")
    ])
])

def buildParams = [
    MainRepoURL        : "gitlab.cee.redhat.com",
    MainRepoProject    : "ai_tools/genie-ai",
    CredMainRepoProject: "ai_tools/genie-cred-data",
    CredMainRepoBranch : "main",
    CredentialsId      : "gitlab-genie",
    DevRoot            : "/root/workspace/${env.JOB_NAME}",
    NodeToRun          : "tag-slave",
]

pipeline {
    agent { node { label "${buildParams.NodeToRun}" } }

    stages {
        stage('Checkout Deployment Code') {
            steps {
                dir("${buildParams.DevRoot}/${params.BRANCH}/helm") {
                    checkout([$class: 'GitSCM',
                        branches: [[name: "${params.BRANCH}"]],
                        extensions: [[$class: 'RelativeTargetDirectory', relativeTargetDir: "${buildParams.DevRoot}/${params.BRANCH}/helm"]],
                        userRemoteConfigs: [[
                            credentialsId: buildParams.CredentialsId,
                            url: "https://${buildParams.MainRepoURL}/${buildParams.MainRepoProject}.git"
                        ]]
                    ])
                }
            }
        }

        stage('Checkout Credential Data') {
            steps {
                dir("${buildParams.DevRoot}/${params.BRANCH}/helm/genie-cred-data") {
                    checkout([$class: 'GitSCM',
                        branches: [[name: "${buildParams.CredMainRepoBranch}"]],
                        extensions: [[$class: 'RelativeTargetDirectory', relativeTargetDir: "${buildParams.DevRoot}/${params.BRANCH}/helm/genie-cred-data"]],
                        userRemoteConfigs: [[
                            credentialsId: buildParams.CredentialsId,
                            url: "https://${buildParams.MainRepoURL}/${buildParams.CredMainRepoProject}.git"
                        ]]
                    ])
                }
            }
        }

        stage('Deploy to Cluster') {
            when { expression { return params.deploy_genie } }
            steps {
                echo("Deploying Genie to ${params.deployment_location} with ${params.deployment_type}")
                echo("Namespace: ${params.namespace}")
                sh "helm upgrade --install genie ./genie --namespace ${params.namespace} --set deploymentType=${params.deployment_type}"
            }
        }
    }
}
