# UnifAI Shared Resources Deployment

This directory contains the ArgoCD Applications for deploying UnifAI shared infrastructure components using the App-of-Apps pattern.

## Components

The shared resources deployment includes the following components, deployed in order:

### Wave 1: Storage
- **storage-app.yaml** - Shared EFS storage for data persistence

### Wave 2: Core Services  
- **mongodb-app.yaml** - MongoDB database for application data
- **qdrant-app.yaml** - Qdrant vector database for embeddings
- **rabbitmq-app.yaml** - RabbitMQ message queue for async processing
- **docling-app.yaml** - Docling service for document processing

### Wave 3: Configuration
- **shared-config-app.yaml** - Shared configuration configmap with service endpoints

## Deployment Order

Components are deployed using ArgoCD sync waves:
1. Wave 1: Storage resources first
2. Wave 2: All core services in parallel 
3. Wave 3: Shared configuration after services are ready

## Usage

To deploy the shared resources:

1. Ensure ArgoCD is running in your `tag-ai--runtime-int` namespace
2. Apply the main shared resources application:
   ```bash
   kubectl apply -f ../shared-resources-tenant.yaml
   ```
3. ArgoCD will automatically deploy all components in the correct order

## Monitoring

Check deployment status with:
```bash
# Check main app
argocd app get unifai-shared-resources

# Check individual components  
argocd app list | grep unifai-
```

## Notes

- Database components (MongoDB, Qdrant, RabbitMQ) have `prune: false` to prevent accidental data loss
- Persistent volumes are configured to not auto-delete
- All components use the shared resource values from `helm/values/shared-resource-values.yaml`
