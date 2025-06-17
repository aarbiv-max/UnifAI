properties([
    parameters([
        // 🌐 Global Parameters
        string(name: "BRANCH", defaultValue: "main", description: "Git branch to build images from."),
        string(name: "VERSION", defaultValue: new Date().format('yyyy.MM.dd'), description: "Image version tag"),
        
        // 🛠️ Image Build Parameters
        booleanParam(name: 'build_gui', defaultValue: false, description: 'Create image for UI'),
        booleanParam(name: 'build_dataflow_backend', defaultValue: false, description: 'Create image for dataflow backend'),
        booleanParam(name: 'build_multiagent_backend', defaultValue: false, description: 'Create image for multiagent backend'),
        booleanParam(name: 'set_image_canidate', defaultValue: false, description: 'Set images with latest tag'),
        
        // 🚀 Deployment Parameters
        booleanParam(name: 'deploy_unifai', defaultValue: false, description: 'True - Deploy UnifAI, False - Only build images and upload to image-paas'),
        choice(name: 'deploy_type', choices: ['FRESH_INSTALL', 'APPLICATION_UPGRADE'], description: 'Deployment type'),
        choice(name: 'deploy_location', choices: ['STAGING', 'PRODUCTION'], description: 'Deployment environment'),
        string(name: "deploy_namespace", defaultValue: "tag-ai--runtime-int", description: "K8s namespace"),
    ])
])

def buildParams = [
    MainRepoURL        : "gitlab.cee.redhat.com",
    MainRepoProject    : "ai_tools/unifai",
    CredentialsId      : "gitlab-genie",
    NodeToRun          : "tag-slave",
    DevRoot            : "/root/workspace/${env.JOB_NAME}",
    ImageRegistry      : "images.paas.redhat.com",
    ImageRegistryPath  : "genie",
    ImageRegistryCreds : "images.paas.registry",
]

def buildDockerImage(String module, String component) {
    String dockerfile = "Dockerfile"
    String logFile = "/tmp/${module}_build.log"

    echo("---====  buildDockerImage ${module}  ====---")

    def status = sh(script: "podman build -t ${module}:${VERSION} -t ${component}/${module}:latest -f ${dockerfile} > ${logFile} 2>&1", returnStatus: true)

    if (status != 0) {
        echo("Build failed for module: ${component}/${module}. Check ${logFile} for details.")
        sh "cat ${logFile}"
        return false
    } else {
        echo("Build completed successfully for module: ${module}.")
        return true
    }
}

def tagAndPushImageToRegistry(module, buildParams,component) {
    echo("Tagging and pushing image for ${module}.")

    withCredentials([usernamePassword(
        credentialsId: "${buildParams.ImageRegistryCreds}",
        usernameVariable: 'REGISTRY_USER',
        passwordVariable: 'REGISTRY_PASS'
    )]) {
        sh """
            podman login -u ${REGISTRY_USER} -p ${REGISTRY_PASS} ${buildParams.ImageRegistry}
            podman push ${module}:${VERSION} ${buildParams.ImageRegistry}/${buildParams.ImageRegistryPath}/${component}/${module}:${VERSION}
        """
        if (params.set_image_canidate) {
            sh """
                podman push --quiet ${module}:${VERSION} ${buildParams.ImageRegistry}/${buildParams.ImageRegistryPath}/${component}/${module}:latest
            """
        }
        echo("Image for ${module} has been tagged and pushed to ${buildParams.ImageRegistry}/${buildParams.ImageRegistryPath}/${component}/${module}:${VERSION}")
    }
}

def cleanWorkspace(module,component) {
    sh """
        podman rm -f  ${component}/${module} || true
        podman rmi -f ${component}/${module}:${VERSION} || true
        podman rmi -f ${component}/${module}:latest || true
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

pipeline {
    agent { node { label "${buildParams.NodeToRun}" } }

    stages {
        stage('Checkout') {
            steps {
                dir("${buildParams.DevRoot}/${params.BRANCH}/") {
                    checkout([$class: 'GitSCM',
                        branches: [[name: "${params.BRANCH}"]],
                        extensions: [[$class: 'RelativeTargetDirectory', relativeTargetDir: "${buildParams.DevRoot}/${params.BRANCH}"]],
                        userRemoteConfigs: [[
                            credentialsId: buildParams.CredentialsId,
                            url: "https://${buildParams.MainRepoURL}/${buildParams.MainRepoProject}.git"
                        ]]
                    ])
                }
            }
        }
        stage('Debug Parameters') {
            steps {
                script {
                    echo "build_gui: ${params.build_gui}"
                    echo "build_dataflow_backend: ${params.build_dataflow_backend}"
                    echo "build_multiagent_backend: ${params.build_multiagent_backend}"
                }
            }
        }

        stage('Build and Push Images') {
            parallel {
                stage('build_gui_image') {
                    when { expression { params.build_gui } }
                    steps {
                        script {
                            def component = "DataPipelineHub"
                            def module = "ui"
                            def componentLower = component.toLowerCase()
                            dir("${buildParams.DevRoot}/${params.BRANCH}/${component}/${module}/") {
                                //cleanWorkspace(module)
                                if (buildDockerImage(module, componentLower)) {
                                    tagAndPushImageToRegistry(module, buildParams, componentLower)
                                    cleanWorkspace(module, componentLower)
                                } else {
                                    error("Terminating process for ${module}: Build failed")
                                }
                            }
                        }
                    }
                }

                stage('build_dataflow_image') {
                    when { expression { params.build_dataflow_backend } }
                    steps {
                        script {
                            def component = "DataPipelineHub"
                            def module = "backend"
                            def componentLower = component.toLowerCase()
                            dir("${buildParams.DevRoot}/${params.BRANCH}/${component}/${module}") {
                                //cleanWorkspace(module)
                                if (buildDockerImage(module, componentLower)) {
                                    tagAndPushImageToRegistry(module, buildParams,componentLower)
                                    cleanWorkspace(module,componentLower)
                                } else {
                                    error("Terminating process for ${module}: Build failed")
                                }
                            }
                        }
                    }
                }

                // Uncomment if needed
                // stage('build_multiagent_image') {
                //     when { expression { params.build_multiagent_backend } }
                //     steps {
                //         script {
                //             def module = "multi-agent/backend"
                //             dir("${buildParams.DevRoot}/${params.BRANCH}/${module}") {
                //                 cleanWorkspace(module)
                //                 if (buildDockerImage(module)) {
                //                     tagAndPushImageToRegistry(module, buildParams)
                //                     cleanWorkspace(module)
                //                 } else {
                //                     error("Terminating process for ${module}: Build failed")
                //                 }
                //             }
                //         }
                //     }
                // }
            }
        }

        stage('Deploy Application') {
            when {
                expression { return params.deploy_unifai }
            }
            steps {
                script {
                    echo "Triggering deployment pipeline..."
                    build job: 'pipeline-deploy',
                    parameters: [
                        string(name: 'BRANCH', value: params.BRANCH),
                        string(name: 'VERSION', value: params.VERSION),
                        string(name: 'deploy_type', value: params.deploy_type),
                        string(name: 'deploy_location', value: params.deploy_location),
                        string(name: 'namespace', value: params.deploy_namespace)
                    ]
                }
            }
        }
    }

    // post {
    //     always {
    //         script {
    //             echo "Running cleanup..."
    //             cleanPodmanSystem()
    //         }
    //     }
    // }
}

