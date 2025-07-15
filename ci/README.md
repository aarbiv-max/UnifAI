# 🚀 UnifAI CI/CD Pipelines

Welcome! This guide explains our two-step Jenkins pipeline process for building and deploying the **UnifAI** application.

---

## 📦 Overview

Our CI/CD process consists of two main pipelines:

1. **Image Builder** – Builds new container images from our code.
2. **Application Deployer** – Deploys those images to our OpenShift clusters using Helm.

---

## 🏗️ Pipeline 1: Image Builder

This pipeline performs the following tasks:
- Compiles the source code
- Builds container images using **Podman**
- Pushes the images to our internal image registry
- Optionally triggers the deployment pipeline

### ▶️ How to Use

1. Go to the Jenkins job for **Image Builder**:  
   👉 [Jenkins Image Builder Job](https://jenkins-csb-ant-main.dno.corp.redhat.com/job/UnifAI/job/image-builder/)  
2. Click **"Build with Parameters"**.
3. Fill in the parameters as needed (see below).
4. To also deploy the UnifAI after built image, check the `deploy_unifai` box. ( this will trigger the second pipeline.)

### 🔧 Key Parameters

| Parameter             | Description                                                                 | Default Value               |
|-----------------------|-----------------------------------------------------------------------------|------------------------------|
| `BRANCH`              | The Git branch to build the images from.                                    | `main`                      |
| `VERSION`             | A unique tag for the new images. ( use as it is )                                           | Today's date (`yyyy.MM.dd`) |
| `build_...`           | Check the boxes for the components you want to build (e.g., `build_dataflow_backend`). | `false`                     |
| `set_image_canidate`  | If checked, the new image will also be tagged as `latest` in the registry.  | `false`                     |
| `deploy_unifai`       | **Most Important!** Triggers the Application Deployer pipeline after build. | `false`                     |
| `deploy_location`     | Target cluster for deployment.                                          | `STAGING` `PRODUCTION`                  |
| `deploy_type`         | Deployment type: `FRESH_INSTALL`  wipes the environment before deploying or `APPLICATION_UPGRADE` upgrades the modules with the created image.   | `FRESH_INSTALL` `APPLICATION_UPGRADE`         |

---

## 🚀 Pipeline 2: Application Deployer

This pipeline takes the images built by the first pipeline and deploys them to an environment using **Helm**.

> **Note:** You typically won't run this pipeline manually. It's designed to be triggered automatically by the Image Builder pipeline. Manual runs are for special cases like rollbacks or redeploying an existing version.
***if that was the case, please make sure to set the proper Versions (DF_VERSION, MA_VERSION) and avoid VERSION***

### ⚙️ How It Works

1. Checks out the application's Helm charts.
2. Determines the deployment type:
   - `FRESH_INSTALL`: Deletes the existing application from the environment. Deploys shared resources (e.g., databases) first, then application modules.
   - `APPLICATION_UPGRADE`: Performs a rolling update for selected application modules.
3. Updates configuration files (`values.yaml`, `Chart.yaml`) with:
   - Correct image versions
   - Environment settings (e.g., debug mode, resource limits)
4. Executes `helmfile apply` to apply the changes on the OpenShift cluster.

### ▶️ How to Use (Manual Runs Only)

1. Go to the Jenkins job for **Application Deployer**:  
   👉 [Jenkins Application Deployer Job](https://jenkins-csb-ant-main.dno.corp.redhat.com/job/UnifAI/job/app-deployer/)  
2. Click **"Build with Parameters"**.
3. Fill in the relevant parameters described below.

### 🔧 Key Parameters

| Parameter           | Description                                                                  |
|---------------------|------------------------------------------------------------------------------|
| `MODULES_TO_DEPLOY` | Comma-separated list of components to deploy (e.g., `dataflow,multiagent`). |
| `VERSION`           | DONT set this value when Manual Runs.                                     |
| `DF_VERSION`, `MA_VERSION` | (Optional) Use to specify a different version per module.         |
| `deploy_location`   | Target environment (`STAGING` or `PRODUCTION`).                              |
| `deploy_type`       | Deployment strategy: `FRESH_INSTALL` or `APPLICATION_UPGRADE`.               |
| `debug_mode`        | If `true`, pods will run with debug settings enabled.                        |

---

Have Fun.