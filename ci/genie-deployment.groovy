package main.groovy

properties([ 
    parameters([
        string(name: "PIPELINE_BRANCH", defaultValue: "main", description: "Git branch to take the pipeline from, for testing purpose"),
        string(name: "BRANCH", defaultValue: "main", description: "Git branch to build images from."),        
        booleanParam(name: 'gui', defaultValue: true, description: 'Create image for ui'),
        booleanParam(name: 'backend', defaultValue: true, description: 'Create image for BACKEND'),
        booleanParam(name: 'data_pre', defaultValue: true, description: 'Create image for data-pre'),
        booleanParam(name: 'llm_backend', defaultValue: true, description: 'Create image for llm-backend'),
        booleanParam(name: 'prompt_lab', defaultValue: false, description: 'Create image for prompt_lab'),
        booleanParam(name: 'reviewer', defaultValue: false, description: 'Create image for reviewer'),
        booleanParam(name: 'DB', defaultValue: false, description: 'Create image for DB'),
        booleanParam(name: 'CELERY', defaultValue: false, description: 'Create image for CELERY'),
        booleanParam(name: 'vllm_openai', defaultValue: false, description: 'Create vllm-openai image for Prompt/Reviewer cycle'),
        booleanParam(name: 'rabbitmq', defaultValue: false, description: 'Create image for RabbitMQ'),
        booleanParam(name: 'deploy_genie', defaultValue: false, description: 'True - Deploy Genie, False - Only build images and upload to image-paas'),
        choice(name: 'deployment_location', choices: ['STAGING', 'PRODUCTION'], description: 'Where to deploy Genie?'),
        string(name: "namespace", defaultValue: "tag-ai--runtime-int", description: "The namespace to use for deployment.")
    ]) 
])

Map buildParams = [
    LogLevel           : "ALL",
    MainRepoURL        : "github.com",
    MainRepoProject    : "Nirsisr/Genie-AI",
    MainRepoBranch     : "main",
    CredentialsId      : "tag-github-creds",
    NodeToRun          : "tag-slave",
    DevRoot            : "/root/workspace/${env.JOB_NAME}", //${env.JOB_NAME}/${env.BUILD_ID}",
    ImageRegistry      : "images.paas.redhat.com",
    ImageRegistryPath  : "genie",
    ImageRegistryCreds : "images.paas.registry",
] as HashMap


def checkContainerAndAPI(module, apiUrl = null) {

    // args:
    // module = is the built  image  module
    // apiUrl = not mandatory, call function with apiUrl will check the exposed endpoint. 
    //          if not mantioned it means that there is no exposed endpoint and it will only check that container is running.


    echo("Checking if container for ${module} can be created and exposed API is responsive.")
    echo("module : ${module}")
    echo("apiUrl : ${apiUrl}")

    if (apiUrl) {
        
        sh """
            podman run -d -p 8080:80  --name ${module} ${module}:${VERSION}
        """
        sleep 5

        def response = sh(script: "curl -s -o /dev/null -w '%{http_code}' ${apiUrl}", returnStdout: true).trim()

        if (response == "200") {
            echo("API is responsive for ${module}.")
        } else {
                error "API health check failed for ${module}."
        }

    } else {
        sh """
            podman run -d --name ${module} ${module}:${VERSION}
        """
        sleep 5
        def containerStatus = sh(script: "podman ps -q -f name=${module}", returnStdout: true).trim()
        def containerLogs = sh(script: "podman logs ${module}", returnStdout: true).trim()

        if (containerStatus) {
            echo("Container ${module} is up & running.")
        } else {
            echo("Container ${module} logs")
            echo("${containerLogs}")
            error "Container ${module} failed to start."
        }
    }

}



def cleanWorkspace(module) {
    sh """
        podman rm -f ${module}
        podman rmi -f ${module}:${VERSION}
        podman rmi -f ${module}:latest
        sleep 10        
    """
}

def cleanPodmanSystem() {
    sh """
        for container in \$(podman ps --external |awk '{ print \$1 }'); do podman rm -f \$container ;done
        for image in \$(podman images |grep none | awk '{print \$3}') ;do  podman rmi -f \$image ; done
        podman system prune --force
        podman system prune --force --external
    """
}

def buildDockerImage(String module) {
    String dockerfile = "Dockerfile" //"Dockerfile.${module}"
    String logFile = "/tmp/${module}_build.log"
    
    echo("---====  buildDockerImage ${module}  ====---")

    def status = sh(script: "podman build -t ${module}:${VERSION} -t ${module}:latest -f ${dockerfile} > ${logFile} 2>&1", returnStatus: true)

    if (status != 0) {
        echo("Build failed for module: ${module}. Check ${logFile} for details.")
        sh "cat ${logFile}"
        return false
    } else {
        echo("Build completed successfully for module: ${module}.")
        return true
    }
}

def tagAndPushImageToRegistry(module, buildParams) {
    
    // Tag the image with the version tag
    // Push the image to the registry
    echo("Tagging and pushing image for ${buildParams.ImageRegistryCreds}.")

    withCredentials([usernamePassword(
                                    credentialsId: "${buildParams.ImageRegistryCreds}", 
                                    usernameVariable: 'REGISTRY_USER',
                                    passwordVariable: 'REGISTRY_PASS')
                    ]) {

        echo("Tagging and pushing image for ${module}.")
        
        sh """
            podman login -u ${REGISTRY_USER} -p ${REGISTRY_PASS} ${buildParams.ImageRegistry}
            podman push ${module}:${VERSION} ${buildParams.ImageRegistry}/${buildParams.ImageRegistryPath}/${module}:${VERSION}
            #podman push --quiet ${module}:${VERSION} ${buildParams.ImageRegistry}/${buildParams.ImageRegistryPath}/${module}:latest
        """
        if (params.deploy_genie) {
            sh """
                podman push --quiet ${module}:${VERSION} ${buildParams.ImageRegistry}/${buildParams.ImageRegistryPath}/${module}:latest
            """
        }
        echo("Image for ${module} has been tagged and pushed to ${buildParams.ImageRegistry}/${buildParams.ImageRegistryPath}/${module}:${VERSION}")

    }
}

def updateChartfile(module) {
    echo("Updating helm chart file for ${module} to version ${VERSION}.")
    dir("${buildParams.DevRoot}/${params.BRANCH}/helm/${module}/")
    script{
        def yamlFile = 'Chart.yaml'
        def chart = readYaml file: yamlFile
        chart.version = ${VERSION}
        chart.appVersion = ${VERSION}
        writeYaml file: yamlFile, data: chart
    }
}

pipeline {
    agent {
        node {
            label "${buildParams.NodeToRun}"
        }
    }
    environment {
        VERSION = new Date().format('yyyy.MM.dd') 
    }
    stages {
        stage("Prepare Workspace") {
            steps {
                script{
                    switch(params.deployment_location){
                        case 'STAGING':
                          ClusterAddress='https://api.stc-ai-e1-pp.imap.p1.openshiftapps.com:6443'
                          //namespace='tag-ai--runtime-int'
                        case 'PRODUCTION':
                          ClusterAddress='https://api.stc-ai-e1-pp.imap.p1.openshiftapps.com:6443'
                          //namespace='tag-ai--runtime-int'
                    }
                }
                echo("CheckOut ${buildParams.MainRepoProject}/${params.BRANCH}")
                checkout([$class: 'GitSCM',
                    branches: [[name: "${params.BRANCH}"]],
                    doGenerateSubmoduleConfigurations: false,
                    //extensions: [[$class: 'RelativeTargetDirectory', relativeTargetDir: "${buildParams.DevRoot}/${params.BRANCH}"]],
                    extensions: [[$class: 'RelativeTargetDirectory', relativeTargetDir: "${buildParams.DevRoot}/${params.BRANCH}"]],
                    submoduleCfg: [],
                    userRemoteConfigs: [[
                        credentialsId: "${buildParams.CredentialsId}",
                        url: "https://${buildParams.MainRepoURL}/${buildParams.MainRepoProject}.git"
                    ]]
                ])
            }
        }
        
        stage('Build Module Images') {
            parallel {
                stage('gui') {
                    when { expression { params.gui } }
                    steps {
                        script{
                            def module = "ui"
                            dir("${buildParams.DevRoot}/${params.BRANCH}/${module}/"){
                                cleanWorkspace(module)
                                if(buildDockerImage(module)) {
                                    //checkContainerAndAPI(module, 'http://localhost:8080/')
                                    tagAndPushImageToRegistry(module,buildParams)
                                    // if(deploy_genie) {
                                    //     updateChartfile(module)
                                    // }                                    
                                    cleanWorkspace(module)
                                    } 
                                    else {
                                        error("Terminating process for ${module} : Build failed")
                                }
                            }
                        }
                    }
                }
                stage('backend') {
                    when { expression { params.backend } }
                    steps {
                        script{
                            def module = "backend"
                            dir("${buildParams.DevRoot}/${params.BRANCH}/${module}/"){
                                cleanWorkspace(module)
                                if(buildDockerImage(module)) {
                                    //checkContainerAndAPI(module)
                                    tagAndPushImageToRegistry(module,buildParams)
                                    // if(deploy_genie) {
                                    //     updateChartfile(module)
                                    // }                                     
                                    cleanWorkspace(module)
                                    } 
                                    else {
                                        error("Terminating process for ${module} : Build failed")
                                }
                            }
                        }
                    }
                }
                stage('data_pre') {
                    when { expression { params.data_pre } }
                    steps {
                        script{
                            def module = "data_pre"
                            dir("${buildParams.DevRoot}/${params.BRANCH}/${module}/"){
                                cleanWorkspace(module)
                                if(buildDockerImage(module)) {
                                    //checkContainerAndAPI(module)
                                    tagAndPushImageToRegistry(module,buildParams)
                                    // if(deploy_genie) {
                                    //     updateChartfile(module)
                                    // }                                     
                                    cleanWorkspace(module)
                                    } 
                                    else {
                                        error("Terminating process for ${module} : Build failed")
                                }
                            }
                        }
                    }
                }
                stage('llm_backend') {
                    when { expression { params.llm_backend } }
                    steps {
                        script{
                            def module = "llm-backend"
                            dir("${buildParams.DevRoot}/${params.BRANCH}/${module}/"){
                                cleanWorkspace(module)
                                if(buildDockerImage(module)) {
                                    //checkContainerAndAPI(module)
                                    tagAndPushImageToRegistry(module,buildParams)
                                    // if(deploy_genie) {
                                    //     updateChartfile(module)
                                    // }                                     
                                    cleanWorkspace(module)
                                    } 
                                    else {
                                        error("Terminating process for ${module} : Build failed")
                                }
                            }
                        }
                    }
                }
                stage('prompt_lab') {
                    when { expression { params.prompt_lab } }
                    steps {
                            script{
                                def module = "prompt_lab"
                                dir("${buildParams.DevRoot}/${params.BRANCH}/${module}/"){
                                    cleanWorkspace(module)
                                    if(buildDockerImage(module)) {
                                        //checkContainerAndAPI(module)
                                        tagAndPushImageToRegistry(module,buildParams)
                                        // if(deploy_genie) {
                                        //     updateChartfile(module)
                                        // }                                         
                                        cleanWorkspace(module)
                                        } 
                                        else {
                                            error("Terminating process for ${module} : Build failed")
                                    }
                                }
                            }
                    }
                }
                stage('reviewer') {
                    when { expression { params.reviewer } }
                    steps {
                            script{
                                def module = "reviewer"
                                dir("${buildParams.DevRoot}/${params.BRANCH}/${module}/"){
                                    cleanWorkspace(module)
                                    if(buildDockerImage(module)) {
                                        //checkContainerAndAPI(module)
                                        tagAndPushImageToRegistry(module,buildParams)
                                        // if(deploy_genie) {
                                        //     updateChartfile(module)
                                        // }                                         
                                        cleanWorkspace(module)
                                        } 
                                        else {
                                            error("Terminating process for ${module} : Build failed")
                                    }
                                }
                            }
                    }
                }
                stage('DB') {
                    when { expression { params.DB } }
                    steps {
                        echo("Building image for DB")
                    }
                }
                stage('CELERY') {
                    when { expression { params.CELERY } }
                    steps {
                        echo("Building image for CELERY")
                    }
                }
                stage('vllm_openai') {
                    when { expression { params.vllm_openai} }
                    steps {
                            script{
                                def module = "vllm-openai"
                                dir("${buildParams.DevRoot}/${params.BRANCH}/${module}/"){
                                    cleanWorkspace(module)
                                    if(buildDockerImage(module)) {
                                        //checkContainerAndAPI(module)
                                        tagAndPushImageToRegistry(module,buildParams)
                                        // if(deploy_genie) {
                                        //     updateChartfile(module)
                                        // }                                         
                                        cleanWorkspace(module)
                                        } 
                                        else {
                                            error("Terminating process for ${module} : Build failed")
                                    }
                                }
                            }
                    }
                }
                stage('rabbitmq') {
                    when { expression { params.rabbitmq } }
                    steps {
                            script{
                                def module = "rabbitmq"
                                dir("${buildParams.DevRoot}/${params.BRANCH}/${module}/"){
                                    cleanWorkspace(module)
                                    if(buildDockerImage(module)) {
                                        //checkContainerAndAPI(module)
                                        tagAndPushImageToRegistry(module,buildParams)
                                        // if(deploy_genie) {
                                        //     updateChartfile(module)
                                        // }                                         
                                        cleanWorkspace(module)
                                        } 
                                        else {
                                            error("Terminating process for ${module} : Build failed")
                                    }
                                }
                            }
                    }
                }
            }
        }
        
        stage('Deploy Genie') {
            when { 
                allOf {
                    expression { params.deploy_genie }
                    expression { currentBuild.result == null || currentBuild.result == 'SUCCESS' }                    
                }
            }
            steps {
                dir("${buildParams.DevRoot}/${params.BRANCH}/helm/") {
                    script {
                      module = "helmfile"
                    } 
                    cleanWorkspace(module) 
                    withCredentials([string(credentialsId: 'RHOI-service-token', variable: 'token')]){
                        echo("Creating helm deployment pod")
                        sh("oc login --token=${token} --server=${ClusterAddress}")
                        sh("oc project ${params.namespace}")
                        echo("Deploy Helm container")
                        sh("podman run -dt --workdir /helm/charts -v .:/helm/charts:Z -v ~/.kube/:/helm/.kube:Z --name helmfile ghcr.io/helmfile/helmfile:latest bash")
                        echo("Removing previous helms")
                        sh("podman exec -t helmfile bash -c 'helmfile destroy -f helmfile2.yaml --deleteWait'")
                        sh("podman exec -t helmfile bash -c 'helmfile destroy -f helmfile1.yaml --deleteWait'")
                        echo("Wait for the key resourc is deleted")
                        sh("until ! oc get deployment,statefulset,svc | grep 'genie\|mongo\|rabbitmq'; do echo 'Waiting for deployment deletion...'; sleep 5; done")
                        sh("sleep 10") 

                        echo("Deploy/update Helmfile1 for mongodb and rabbitmq")
                        sh("podman exec -t helmfile helmfile -f helmfile1.yaml apply")
                        sh("sleep 10") 
                        echo("Deploy/update Helmfile2 for everything else")
                        sh("podman exec -t helmfile helmfile -f helmfile2.yaml apply")
                        script{
                            GUI_EP = sh(
                                script: 'oc get route genie-ui -n tag-ai--runtime-int -o jsonpath="{.spec.host}"',
                                returnStdout: true
                                ).trim()
                        }
                        echo("Deploy completed successfuly")
                        echo("Genie UI is available at ${GUI_EP}")
                        

                    }
                    cleanWorkspace(module)
                }

            }
        }


    }
    post { 
            success { 
                echo('Build finished successfully')
                cleanPodmanSystem()
                script {
                    if( params.deploy_genie && GUI_EP ) {
                        echo("Deployment completed successfuly")
                        echo("Genie UI is available at http://${GUI_EP}")
                    }
                    else if ( params.deploy_genie && !GUI_EP ) {
                        echo("Unexpected error: GUI_EP is empty or invalid.")
                    }
                }
             }
        }
}
