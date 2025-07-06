properties([
    parameters([
        choice(name: 'deploy_location', choices: ['STAGING', 'PRODUCTION'], description: 'Deployment environment'),
        choice(name: 'deploy_type', choices: ['FRESH_INSTALL', 'APPLICATION_UPGRADE'], description: 'Deployment type'),
        string(name: "BRANCH", defaultValue: "main", description: "Branch to deploy from."),
        string(name: "VERSION", defaultValue: "", description: "DONT SET THIS VALUE!"),
        string(name: "DF_VERSION", defaultValue: "", description: "Image tag for dataflow"),
        string(name: "MA_VERSION", defaultValue: "", description: "Image tag for multi-agent"),
        string(name: "GUI_VERSION", defaultValue: "", description: "Image tag for UI"),
        string(name: "MODULES_TO_DEPLOY", defaultValue: "", description: "Comma-separated list of modules to update (e.g. dataflow,multiagent,gui)"),
        booleanParam(name: 'debug_mode', defaultValue: false, description: 'debug the pods'),
    ])
])

def buildParams = [
    LogLevel           : "ALL",
    MainRepoURL        : "gitlab.cee.redhat.com",
    MainRepoProject    : "ai_tools/unifai",
    MainRepoBranch     : "${params.BRANCH}",
    CredentialsId      : "gitlab-genie",
    CredMainRepoProject: "ai_tools/genie-cred-data", 
    CredMainRepoBranch : "main",
    CredCredentialsId  : "gitlab-genie",

    NodeToRun          : "tag-slave",
    DevRoot            : "/root/workspace/${env.JOB_NAME}",
    ImageRegistry      : "images.paas.redhat.com",
    ImageRegistryPath  : "unifai",
    ImageRegistryCreds : "images.paas.registry-unifai",
]

def updateChartVersions(rootPath, version) {
    echo "Looking for Chart.yaml files under: ${rootPath}"

    def chartFiles = sh(
        script: "find ${rootPath} -name 'Chart.yaml'",
        returnStdout: true
    ).trim().split('\n')

    chartFiles.each { file ->
        echo "Updating: ${file}"
        def chart = readYaml file: file
        //chart.version = params.VERSION
        chart.appVersion = version
        echo "📝 Overwriting YAML file: ${file}"
        writeYaml file: file, data: chart, overwrite: true
    }
}

def updateValuesYaml(String filePath , String version) {
    echo "🔄 Loading values from: ${filePath}"

    def values = readYaml file: filePath

    values.each { sectionName, sectionData ->
        if (sectionData instanceof Map) {
            if (params.debug_mode) {
                echo "🛠 Setting debug mode in section: ${sectionName}"
                sectionData.debug = true
                sectionData.env = sectionData.env ?: [:]
                sectionData.env.ROLE = "debug"
            }

            if (sectionData.image?.tag == 'latest') {
                echo "🏷 Updating image tag in section: ${sectionName} to VERSION: ${version}"
                sectionData.image.tag = version
            }
        }
    }

    echo "📝 Overwriting YAML file: ${filePath}"
    writeYaml file: filePath, data: values, overwrite: true
    echo "✅ Updated ${filePath} successfully"
}

def cleanWorkspace(module) {
    sh """
        podman rm -f helmfile
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
                    echo "Branch            : ${params.BRANCH}"
                    echo "Version           : ${params.VERSION}"
                    echo "Deployment Type   : ${params.deploy_type}"
                    echo "Deployment Target : ${params.deploy_location}"
                    echo "Debug mode        : ${params.debug_mode}"
                    echo "Modules to deploy : ${params.MODULES_TO_DEPLOY}"
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
                dir("${buildParams.DevRoot}/${params.BRANCH}/helm/") {
                    checkout([$class: 'GitSCM',
                        branches: [[name: "${buildParams.CredMainRepoBranch}"]],
                        doGenerateSubmoduleConfigurations: false,
                        //extensions: [[$class: 'RelativeTargetDirectory', relativeTargetDir: "${buildParams.DevRoot}/${params.BRANCH}"]],
                        extensions: [[$class: 'RelativeTargetDirectory', relativeTargetDir: "${buildParams.DevRoot}/${params.BRANCH}/helm/genie-cred-data/"]],
                        submoduleCfg: [],
                        userRemoteConfigs: [[
                            credentialsId: "${buildParams.CredCredentialsId}",
                            url: "https://${buildParams.MainRepoURL}/${buildParams.CredMainRepoProject}.git"
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
                        
                        withCredentials([
                            string(credentialsId: "${ClusterAccessToken}", variable: 'token'),
                        ]){
                            echo("Creating helm deployment pod")
                            sh("oc login --token=${token} --server=${ClusterAddress}")
                            sh("oc project ${NameSpace}")
                            echo("Deploy Helm container")
                            sh("podman run --replace -dt --env-file=./genie-cred-data/.env --workdir /helm/charts -v .:/helm/charts:Z -v ~/.kube/:/helm/.kube:Z --name helmfile ghcr.io/helmfile/helmfile:latest bash")
                            
                            def modules = params.MODULES_TO_DEPLOY.tokenize(',')
                            for (mod in modules) {
                                echo "Processing module: ${mod}"

                                switch(mod.trim()) {
                                    case 'dataflow':
                                        def dfVersion = params.DF_VERSION?.trim()
                                        if (!dfVersion && params.VERSION?.trim()) {
                                            dfVersion = params.VERSION.trim()
                                        }
                                        updateChartVersions("${buildParams.DevRoot}/${params.BRANCH}/helm/dataflow/", dfVersion)
                                        updateValuesYaml("${buildParams.DevRoot}/${params.BRANCH}/helm/values/dataflow-resource-values.yaml", dfVersion)
                                        break

                                    // case 'multiagent':
                                    //     updateChartVersions("${buildParams.DevRoot}/${params.BRANCH}/helm/multiagent/")
                                    //     updateValuesYaml("${buildParams.DevRoot}/${params.BRANCH}/helm/values/multiagent-resource-values.yaml")
                                    //     break

                                    // case 'gui':
                                    //     updateChartVersions("${buildParams.DevRoot}/${params.BRANCH}/helm/gui/")
                                    //     updateValuesYaml("${buildParams.DevRoot}/${params.BRANCH}/helm/values/gui-resource-values.yaml")
                                    //     break

                                    default:
                                        echo "Unknown module: ${mod}, skipping."
                                }
                            }


                            if(params.deploy_type == 'FRESH_INSTALL') {
                                echo("Removing previous helms")
                                sh("podman exec -t helmfile bash -c 'helmfile destroy -f helmfile2.yaml.gotmpl --deleteWait'")
                                sh("podman exec -t helmfile bash -c 'helmfile destroy -f helmfile1.yaml.gotmpl --deleteWait'")
                                echo("Wait for the key resource is deleted")
                                sh("until ! oc get deployment,statefulset,svc | grep 'unifai\\|qdrant\\|mongo\\|rabbitmq'; do echo 'Waiting for deployment deletion...'; sleep 5; done")
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