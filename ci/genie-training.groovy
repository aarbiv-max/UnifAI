package main.groovy

properties([ 
    parameters([
        string(name: "PIPELINE_BRANCH", defaultValue: "main", description: "Git branch to take the pipeline from, for testing purpose"),
        string(name: "BRANCH", defaultValue: "main", description: "Git branch to build images from."),        
        booleanParam(name: 'build_image', defaultValue: false, description: 'Create image for ui'),
        booleanParam(name: 'deploy_training', defaultValue: false, description: 'True - Deploy Genie, False - Only build images and upload to image-paas'),
        choice(name: 'deployment_location', choices: ['staging', 'production'], description: 'Where to deploy Genie?'),
        string(name: "namespace", defaultValue: "tag-ai--pipeline", description: "The namespace to use for deployment."),
        string(name: "PROJECT", defaultValue: "mpc_training", description: "The name of the project for which we train the model"),
        string(name: "MODEL_NAME_OR_PATH", defaultValue: "Qwen/Qwen2.5-Coder-14B-Instruct", description: "what model to use (from huggingface)"),
        string(name: "TEMPLATE", defaultValue: "qwen", description: "The template to use (should match the model)"),
        string(name: "DATASET", defaultValue: "mpc_training", description: "The dataset to use for the fine tuning"), 
        string(name: "LORA_RANK", defaultValue: "16", description: ""),
        string(name: "LORA_ALPHA", defaultValue: "16", description: ""),
        string(name: "LORA_DROPOUT", defaultValue: "0.1", description: ""),               
        string(name: "MAX_SAMPLES", defaultValue: "500000", description: "Max samples to use for the fine tuning"),
        string(name: "NUM_TRAIN_EPOCHS", defaultValue: "1", description: "How many epochs to run in the fine tuning"),
        string(name: "GRADIENT_ACCUMULATION_STEPS", defaultValue: "16", description: "The gradient accumulation to use for the fine tuning"),
        string(name: "PER_DEVICE_TRAIN_BATCH_SIZE", defaultValue: "1", description: "The per device batch size to use for the fine tuning"),
        string(name: "LEARNING_RATE", defaultValue: "5e-5", description: "The learning rate to use for the fine tuning"),
        booleanParam(name: "QUANTIZATION", defaultValue: true, description: "Use quantization in fine tuning")
    ]) 
])

// namespaces: tag-ai--runtime-int / tag-ai--pipeline
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
    HelmValueFile      : "automated_values_file.yaml"
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

        //removed the pushing of lates as to not overwrite the existing one
        sh """
            podman login -u ${REGISTRY_USER} -p ${REGISTRY_PASS} ${buildParams.ImageRegistry}
            podman push ${module}:${VERSION} ${buildParams.ImageRegistry}/${buildParams.ImageRegistryPath}/${module}:${VERSION}
            podman push --quiet ${module}:${VERSION} ${buildParams.ImageRegistry}/${buildParams.ImageRegistryPath}/${module}:latest
        """
        // sh """
        //     podman login -u ${REGISTRY_USER} -p ${REGISTRY_PASS} ${buildParams.ImageRegistry}
        //     podman push ${module}:${VERSION} ${buildParams.ImageRegistry}/${buildParams.ImageRegistryPath}/${module}:${VERSION}
        //     podman push --quiet ${module}:${VERSION} ${buildParams.ImageRegistry}/${buildParams.ImageRegistryPath}/${module}:latest
        // """
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

//for updating the values file with the user input
def createValueFile(params, buildParams) {
    def binding = [
        NAMESPACE                   : params.namespace,
        PROJECT                     : params.PROJECT,
        MODEL_NAME_OR_PATH          : params.MODEL_NAME_OR_PATH,
        TEMPLATE                    : params.TEMPLATE,
        DATASET                     : params.DATASET,
        DATASET_NAME                : params.DATASET.split("/")[-1],
        LORA_RANK                   : params.LORA_RANK,
        LORA_ALPHA                  : params.LORA_ALPHA,
        LORA_DROPOUT                : params.LORA_DROPOUT,
        MAX_SAMPLES                 : params.MAX_SAMPLES,
        NUM_TRAIN_EPOCHS            : params.NUM_TRAIN_EPOCHS,
        GRADIENT_ACCUMULATION_STEPS : params.GRADIENT_ACCUMULATION_STEPS,
        PER_DEVICE_TRAIN_BATCH_SIZE : params.PER_DEVICE_TRAIN_BATCH_SIZE,
        LEARNING_RATE               : new BigDecimal(params.LEARNING_RATE),
        QUANTIZATION                : params.QUANTIZATION
    ]

    def text='''
ConfigMap: 
  data: 
    MODE: "training" #debug | training
    PROJECT: ${PROJECT}
    DATASET_REPO: "${DATASET}"
    DATASET_NAME: "${DATASET_NAME}"

ConfigMapTrainerArgs:
    metadata:
        name: trainer-configmap-trainer-args
        namespace: "${NAMESPACE}"
    data: 
        MODEL_NAME_OR_PATH: "${MODEL_NAME_OR_PATH}"
        LORA_RANK: "${LORA_RANK}"
        LORA_ALPHA: "${LORA_ALPHA}"
        LORA_DROPOUT: "${LORA_DROPOUT}"
        DATASET: "${DATASET_NAME}"
        TEMPLATE: "${TEMPLATE}"
        MAX_SAMPLES: "${MAX_SAMPLES}"
        NUM_TRAIN_EPOCHS: "${NUM_TRAIN_EPOCHS}"
        GRADIENT_ACCUMULATION_STEPS: "${GRADIENT_ACCUMULATION_STEPS}"
        PER_DEVICE_TRAIN_BATCH_SIZE: "${PER_DEVICE_TRAIN_BATCH_SIZE}"
        LEARNING_RATE: "${LEARNING_RATE}"
        QUANTIZATION: "${QUANTIZATION}"
'''
    //println(binding)
    println(buildParams.HelmValueFile)
    def engine = new groovy.text.SimpleTemplateEngine()
    def template = engine.createTemplate(text).make(binding)
    //println template.toString()
    writeFile(file: buildParams.HelmValueFile, text: template.toString())  // , encoding: "UTF-8"
}

def checkTrainingStatus(String POD) {
            boolean done = false
            String output = ""
            while (!done) {
                output = sh(script: " oc logs ${POD} | tail -5", returnStdout: true).trim()
                echo "Last line: ${output}"
                if (output.contains("training process is done, logs are at /app/screen.log")) {
                    echo("training is done")
                    done = true
                } else if (output.contains("training didn't finish successfuly")) {
                    echo("training process has failed")
                    error "Training failed. Stopping pipeline execution."
                } else if (output.contains("training still in progress")) {
                    echo("training is still in progress")
                    sleep 60  // Wait for 1 minute before checking again
                }
            }
            return output  // Return the final log message when done
}

def helmOperation(action) {
    sh("oc login --token=${token} --server=${ClusterAddress}")
    sh("oc project ${params.namespace}")
    if (action == 'install') {
        echo("Creating helm training deployment ")
        script{
            createValueFile(params,buildParams)
        }
        // sh("oc login --token=${token} --server=${ClusterAddress}")
        // sh("oc project ${params.namespace}")
        echo("Deploying Helm chart")
        sh("helm install training-${currentBuild.number} training/ -f ${buildParams.HelmValueFile} --wait --timeout 10m0s")
        //sh("helm install training-${currentBuild.number} training/ --wait --set Deployment.spec.template.spec.containers.image=images.paas.redhat.com/genie/training:test --set ConfigMap.data.MODE=debug --set Global.cluster=${deployment_location}")
        echo("Deployment completed successfuly, training in progress")
        script{
            API_EP = sh(
                script: "oc get route genie-training-api -n ${params.namespace} -o jsonpath='{.spec.host}'",
                returnStdout: true
                ).trim()
            POD_NAME = sh(
                script: 'oc get pods -o jsonpath="{.items[?(@.metadata.name contains "genie-training")].metadata.name}"',
                returnStdout: true
                ).trim()                                
        }
        return [API_EP , POD_NAME]
    }
    else if (action == 'uninstall') {
        // sh("oc login --token=${token} --server=${ClusterAddress}")
        // sh("oc project ${params.namespace}")
        sh("helm uninstall training-${currentBuild.number}")
    }
    else {
        echo("unknown action provided")
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
        ClusterAddress = "${params.deployment_location == 'staging' ? 'https://api.stc-ai-e1-pp.imap.p1.openshiftapps.com:6443' : 'https://api.stc-ai-e1-prod.rtc9.p1.openshiftapps.com:6443'}"
        ClusterCreds = "${params.deployment_location == 'staging' ? 'RHOI-service-token' : 'openshift-production-token'}"
        // ClusterAddress = (params.deployment_location == 'staging') 
        //             ? 'https://api.stc-ai-e1-pp.imap.p1.openshiftapps.com:6443' 
        //             : 'https://api.stc-ai-e1-pp.imap.p1.openshiftapps.com:6443'
    }
    stages {
        stage("Prepare Workspace") {
            steps {
                // script{
                //     switch(params.deployment_location){
                //         case 'STAGING':
                //           ClusterAddress='https://api.stc-ai-e1-pp.imap.p1.openshiftapps.com:6443'
                //           //namespace='tag-ai--runtime-int'
                //         case 'PRODUCTION':
                //           ClusterAddress='https://api.stc-ai-e1-pp.imap.p1.openshiftapps.com:6443'
                //           //namespace='tag-ai--runtime-int'
                //     }
                // }
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
        
        stage('Build training image') {
            when { expression { params.build_image } }
            steps {
                    script{
                        def module = "training"
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

        stage('Run Training') {
            when { 
                allOf {
                    expression { params.deploy_training }
                    expression { currentBuild.result == null || currentBuild.result == 'SUCCESS' }                    
                }
            }
            steps {
                dir("${buildParams.DevRoot}/${params.BRANCH}/pipelines/") {

                    // script {
                    //   module = "helmfile"
                    // } 
                    //cleanWorkspace(module) 
                    withCredentials([string(credentialsId: ClusterCreds, variable: 'token')]){
                        // script{
                        //    def (API_EP, POD_NAME) = helmOperation('install')
                        // }                        
                        echo("Creating helm training deployment ")
                        script{
                          createValueFile(params,buildParams)
                        }
                        sh("oc login --token=${token} --server=${ClusterAddress}")
                        sh("oc project ${params.namespace}")
                        echo("Deploying Helm chart")
                        sh("helm install training-${currentBuild.number} training/ -f ${buildParams.HelmValueFile} --wait --timeout 10m0s")
                        //sh("helm install training-${currentBuild.number} training/ --wait --set Deployment.spec.template.spec.containers.image=images.paas.redhat.com/genie/training:test --set ConfigMap.data.MODE=debug --set Global.cluster=${deployment_location}")
                        echo("Deployment completed successfuly, training in progress")
                        script{
                            API_EP = sh(
                                script: "oc get route genie-training-api -n ${params.namespace} -o jsonpath='{.spec.host}'",
                                returnStdout: true
                                ).trim()
                            POD_NAME = sh(
                                script: 'oc get pods -o jsonpath="{.items[?(@.metadata.name contains "genie-training")].metadata.name}"',
                                returnStdout: true
                                ).trim()                                
                        }  
                        //sh("curl http://${API_EP}/api/training/status")
                        //sh("oc logs genie-training-7d4bfd64cd-vqjqp |tail -1")  
                        script{
                            def finalLog = checkTrainingStatus(POD_NAME)
                            echo(finalLog)
                        }
                        sh("helm uninstall training-${currentBuild.number}")

                    }
                    //cleanWorkspace(module)
                }

            }
        }

        // stage('debug file') {
        //     steps {
        //         script{
        //             createValueFile(params)
        //         }
                
        //     }
        // }
            }
        
        
    post { 
            success { 
                echo('Build finished successfully')
                cleanPodmanSystem()
             }
        }
}
