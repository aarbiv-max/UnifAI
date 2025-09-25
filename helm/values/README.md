# Values Files Structure

This directory contains values files for both Helmfile and ArgoCD deployments:

## Master Configuration File
- **`shared-resource-values.yaml`** - Master configuration with grouped sections for Helmfile
  - Used by: `helm/helmfile1.yaml` 
  - Contains: `mongodb:`, `qdrant:`, `rabbitmq:`, `docling:`, `storage:` sections
  - ⚠️  **DO NOT MODIFY** - Used by Helmfile-based deployments

## ArgoCD Extract Files
These files are derived from the master configuration for individual ArgoCD applications:

- **`mongodb-extract.yaml`** - Complete MongoDB config (derived from `shared-resource-values.yaml` mongodb section)
- **`qdrant-extract.yaml`** - Complete Qdrant config (derived from `shared-resource-values.yaml` qdrant section)  
- **`rabbitmq-extract.yaml`** - Complete RabbitMQ config (derived from `shared-resource-values.yaml` rabbitmq section)
- **`docling-extract.yaml`** - Complete Docling config (derived from `shared-resource-values.yaml` docling section)

## Sync Process

When you modify `shared-resource-values.yaml`, update the corresponding extract files:

### Manual Sync
1. Copy values from `shared-resource-values.yaml` grouped section
2. Convert to root-level structure in the extract file
3. Add any additional fields required by the specific Helm chart

### Example
```yaml
# shared-resource-values.yaml
mongodb:
  image:
    registry: "example.com"
    
# mongodb-extract.yaml  
image:
  registry: "example.com"
```

### Automated Sync (if yq is available)
```bash
# Sync all extract files
bash helm/scripts/sync-all-values.sh
```

## Architecture
- **Helmfile**: Uses grouped `shared-resource-values.yaml` directly
- **ArgoCD**: Uses individual extract files (avoids Helm chart value structure conflicts)
- **Single Source of Truth**: `shared-resource-values.yaml` remains the master configuration
