## Overview

This readme refers to the procedure of deploying the multi-agent part of UnifAi.

**NOTE: this readme file refers ONLY to the multiagent deployment. and assume existing deployment of shared resources.**


## Deployment procedure

### Pre-requisites
1. this deployment is being deployed on the same cluster of the shared-resources deployment.
this necessarily means that the mongodb and rabbit are all accessible withing this cluster by unsing thes values below.
2. all actions are being done from this current folder (unifai/helm/multiagent)


in order to deploy the helm please use the procedure below:

1. Login to the cluster you want to deploy the multiagent on.

2. If the shared resources are on the same cluster just run the command 
```
helm install <deployment name> ./be
```

3. If the shared resources are on a different cluster

- If the shared resources are NOT on the same cluster please *create a new yaml file with this content:

```
env:
  MONGODB_IP: <mongo db address> 
  MONGODB_PORT: <mongo db port>
  RABBITMQ_IP: <rabbitmq address>
  RABBITMQ_PORT: <rabbitmq port>
```

- now the command will be (assuming the new file was called new_values.yaml):

```
helm install <deployment name> -f new_values.yaml ./be
```