// pipeline-deploy.groovy

properties([
    parameters([
        choice(name: 'deploy_location', choices: ['STAGING', 'PRODUCTION'], description: 'Deployment environment'),
        choice(name: 'deploy_type', choices: ['FRESH_INSTALL', 'APPLICATION_UPGRADE'], description: 'Deployment type'),
        string(name: "namespace", defaultValue: "tag-ai--runtime-int", description: "K8s namespace"),
        string(name: "BRANCH", defaultValue: "main", description: "Branch to deploy from."),
        string(name: "VERSION", defaultValue: new Date().format('yyyy.MM.dd'), description: "Image version tag"),
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
        stage('Debug Parameters') {
            steps {
                script {
                    echo "BRANCH: ${params.BRANCH}"
                    echo "VERSION: ${params.VERSION}"
                    echo "deploy_type: ${params.deploy_type}"
                    echo "deploy_location: ${params.deploy_location}"
                    echo "namespace: ${params.namespace}"
                }
            }
        }

    }
}
