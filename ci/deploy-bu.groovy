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
    MainRepoURL        : "github.com",
    MainRepoProject    : "redhat-community-ai-tools/UnifAI",
    MainRepoBranch     : "${params.BRANCH}",
    CredentialsId      : "github-genie",
    CredMainRepoURL    : "gitlab.cee.redhat.com",
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
            if (params.deploy_location == 'STAGING') {
                echo "🛠 reduce resources in section: ${sectionName}"
                
                if (sectionName == "env") {
                    echo "⚠️ Skipping top-level 'env' section (no resources)"
                    return
                }
                sectionData.resources = sectionData.resources ?: [:]
                sectionData.resources.limits = sectionData.resources.limits ?: [:]
                sectionData.resources.requests = sectionData.resources.requests ?: [:]
                sectionData.resources.limits.cpu = 1
                sectionData.resources.limits.memory = "2Gi"
                sectionData.resources.requests.cpu = 1
                sectionData.resources.requests.memory = "2Gi"
            }
        }
    }

    echo "📝 Overwriting YAML file: ${filePath}"
    writeYaml file: filePath, data: values, overwrite: true
    echo "✅ Updated ${filePath} successfully"
}

def deployModules(module){
    echo "deploying modules: ${module}"
    sh("podman exec -t helmfile bash -lc 'helmfile -f ${module}.yaml.gotmpl apply'")
    echo("${module} successfully deployed")
    sh("sleep 10")
}

def deleteRunningApplication(){
    echo("Removing running UnifAI application")
    sh("podman exec -t helmfile bash -c 'helmfile destroy -f dataflow.yaml.gotmpl --deleteWait'")
    sh("podman exec -t helmfile bash -c 'helmfile destroy -f multiagent.yaml.gotmpl --deleteWait'")
    sh("podman exec -t helmfile bash -c 'helmfile destroy -f shared-resources.yaml.gotmpl --deleteWait'")
    echo("Wait for resource deletion...")
    sh("until ! oc get deployment,statefulset,svc | grep 'unifai\\|qdrant\\|mongo\\|rabbitmq'; do echo 'Waiting for deployment deletion...'; sleep 5; done")
    echo("UnifAi application successfully deleted")
    sh("sleep 10")
}

def cleanWorkspace() {
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
                            url: "https://${buildParams.CredMainRepoURL}/${buildParams.CredMainRepoProject}.git"
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
                                //ClusterAddress = 'https://api.stc-ai-e1-prod.rtc9.p1.openshiftapps.com:6443'
                                //NameSpace = "tag-ai--pipeline"
                                //ClusterAccessToken = 'tenantaccess-unifai-sa-prod'
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
                            if(params.deploy_type == 'FRESH_INSTALL') {
                                modules.add(0,'shared-resources')
                                deleteRunningApplication()
                            }
                            
                            for (mod in modules) {
                                switch(mod.trim()) {
                                    case 'shared-resources':
                                        updateValuesYaml("${buildParams.DevRoot}/${params.BRANCH}/helm/values/shared-resource-values.yaml", version)
                                        deployModules('shared-resources')
                                        break

                                    case 'dataflow':
                                        def version = params.DF_VERSION?.trim() ?: params.VERSION?.trim()
                                        updateChartVersions("${buildParams.DevRoot}/${params.BRANCH}/helm/dataflow/", version)
                                        updateValuesYaml("${buildParams.DevRoot}/${params.BRANCH}/helm/values/dataflow-resource-values.yaml", version)
                                        deployModules('dataflow')
                                        break

                                    case 'multiagent':
                                        def version = params.DF_VERSION?.trim() ?: params.VERSION?.trim()
                                        updateChartVersions("${buildParams.DevRoot}/${params.BRANCH}/helm/multiagent/", version)
                                        updateValuesYaml("${buildParams.DevRoot}/${params.BRANCH}/helm/values/multiagent-resource-values.yaml", version)
                                        deployModules('multiagent')
                                        break
                                }
                            }
                            echo("Deploy successfully completed")
                        }
                        cleanWorkspace()
                    }
                }
            }
        }
    }

}