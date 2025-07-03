properties([
    parameters([
        choice(name: 'deploy_location', choices: ['STAGING', 'PRODUCTION'], description: 'Deployment environment'),
        choice(name: 'deploy_type', choices: ['FRESH_INSTALL', 'APPLICATION_UPGRADE'], description: 'Deployment type'),
        string(name: "BRANCH", defaultValue: "main", description: "Branch to deploy from."),
        string(name: "VERSION", defaultValue: new Date().format('yyyy.MM.dd'), description: "Image version tag"),
    ])
])

def buildParams = [
    LogLevel           : "ALL",
    MainRepoURL        : "gitlab.cee.redhat.com",
    MainRepoProject    : "ai_tools/unifai",
    MainRepoBranch     : "${params.BRANCH}",
    CredentialsId      : "gitlab-genie",
    NodeToRun          : "tag-slave",
    DevRoot            : "/root/workspace/${env.JOB_NAME}",
    ImageRegistry      : "images.paas.redhat.com",
    ImageRegistryPath  : "unifai",
    ImageRegistryCreds : "images.paas.registry-unifai",
]

def cleanWorkspace(module) {
    sh """
        podman rm -f ${module}
        podman rmi -f ${module}:${VERSION}
        podman rmi -f ${module}:latest 
        sleep 10        
    """
}

pipeline {
    agent { node { label "${buildParams.NodeToRun}" } }

    stages {

        stage('Checkout') {
            steps {
                script {
                    echo "================ Deployment Configuration ================="
                    echo "Branch           : ${params.BRANCH}"
                    echo "Version          : ${params.VERSION}"
                    echo "Deployment Type  : ${params.deploy_type}"
                    echo "Deployment Target: ${params.deploy_location}"
                    echo "----------------------------------------------"
                    echo "Workspace Path:    ${buildParams.DevRoot}/${params.BRANCH}/"
                    echo "==========================================================="
                }
                echo("CheckOut ${buildParams.MainRepoProject}/${params.BRANCH}")
                dir("${buildParams.DevRoot}/${params.BRANCH}/") {
                    checkout([$class: 'GitSCM',
                        branches: [[name: "${params.BRANCH}"]],
                        // 🛠️ Removed RelativeTargetDirectory to avoid nesting loop
                        submoduleCfg: [],
                        userRemoteConfigs: [[
                            credentialsId: "${buildParams.CredentialsId}",
                            url: "https://${buildParams.MainRepoURL}/${buildParams.MainRepoProject}.git"
                        ]]
                    ])
                }
                
            }
        }
        
        stage('Deploy UnifAI') {
            steps {
                dir("${buildParams.DevRoot}/${params.BRANCH}/helm/") {
                    script {
                        // Declare variables outside the switch statement
                        def ClusterAddress = ''
                        def NameSpace = ''
                        def ClusterAccessToken = ''
                        
                        // Fixed parameter name and added break statements
                        switch(params.deploy_location) {
                            case 'STAGING':
                                ClusterAddress = 'https://api.stc-ai-e1-pp.imap.p1.openshiftapps.com:6443'
                                NameSpace = "tag-ai--pipeline"
                                ClusterAccessToken = 'tenantaccess-unifai-sa-pp'
                                break
                            case 'PRODUCTION':
                                ClusterAddress = 'https://api.stc-ai-e1-prod.rtc9.p1.openshiftapps.com:6443'
                                NameSpace = "tag-ai--pipeline"
                                ClusterAccessToken = 'tenantaccess-unifai-sa-prod'
                                break
                            default:
                                error("Invalid deployment location: ${params.deploy_location}")
                        }
                        
                        def module = "helmfile"
                        cleanWorkspace(module) 
                        
                        withCredentials([
                            string(credentialsId: "${ClusterAccessToken}", variable: 'token'),
                        ]){
                            echo("Creating helm deployment pod")
                            sh("oc login --token=${token} --server=${ClusterAddress}")
                            sh("oc project ${NameSpace}")
                            echo("Deploy Helm container")
                            sh("podman run -dt --env-file=./genie-cred-data/.env --workdir /helm/charts -v .:/helm/charts:Z -v ~/.kube/:/helm/.kube:Z --name helmfile ghcr.io/helmfile/helmfile:latest bash")

                            if(params.deploy_location == "STAGING"){
                                sh 'sed -i \'s/^\\([[:space:]]*tag:[[:space:]]*\\).*$/\\1"' + params.VERSION + '"/\' values/dataflow-resource-values.yaml'
                            }

                            if(params.deploy_type == 'FRESH_INSTALL') {
                                echo("Removing previous helms")
                                sh("podman exec -t helmfile bash -c 'helmfile destroy -f helmfile2.yaml.gotmpl --deleteWait'")
                                sh("podman exec -t helmfile bash -c 'helmfile destroy -f helmfile1.yaml.gotmpl --deleteWait'")
                                echo("Wait for the key resource is deleted")
                                sh("""
                                    until ! oc get deployment,statefulset,svc | grep 'unifai'; do echo 'Waiting for deployment deletion...'; sleep 5; done
                                """)
                                sh("sleep 10")

                                echo("Deploy/update Helmfile1 for mongodb ,qdrant and rabbitmq")
                                sh("podman exec -t helmfile bash -lc 'helmfile -f helmfile1.yaml.gotmpl apply'")
                                sh("sleep 10")
                            }
                            else {
                                echo("Removing previous app helms")
                                sh("podman exec -t helmfile bash -c 'helmfile destroy -f helmfile2.yaml.gotmpl --deleteWait'")
                                echo("Wait for the key genie resource is deleted")
                                sh("""
                                    until ! oc get deployment,statefulset,svc | grep 'unifai'; do echo 'Waiting for deployment deletion...'; sleep 5; done
                                """)
                                sh("sleep 10")
                            }

                            echo("Deploy/update Helmfile2 for everything else")
                            sh("podman exec -t helmfile bash -lc 'helmfile -f helmfile2.yaml.gotmpl apply'")
                            
                            echo("Deploy completed successfully")
                        }
                        cleanWorkspace(module)
                    }
                }
            }
        }
    }

    // Optional cleanup
    // post {
    //     always {
    //         script {
    //             echo "Running cleanup..."
    //             cleanPodmanSystem()
    //             cleanWs()
    //         }
    //     }
    // }
}