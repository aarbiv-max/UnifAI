# UnifAI Platform GitOps Deployment

This directory contains the complete GitOps deployment structure for the UnifAI platform using a **single ArgoCD application** with Helmfile.

## Single Application Structure

### One Application to Rule Them All
- **`unifai-platform.yaml`** - Single ArgoCD application that deploys the complete platform
- **Two Implementation Options:**
  - **Option A**: `helm/unifai-platform.yaml.gotmpl` - Master Helmfile (requires Helmfile plugin)  
  - **Option B**: `helm/unifai-platform-chart/` - Helm chart with dependencies (no plugin required)

### Platform Components (All Managed Internally)
All components are deployed as Helm releases within the single ArgoCD application:
- **Storage Infrastructure**: Shared EFS storage
- **Infrastructure Services**: MongoDB, RabbitMQ, Qdrant, Docling  
- **Platform Services**: Shared configuration, SSO authentication
- **Application Services**: Dataflow backend, MultiAgent backend  
- **User Interface**: Frontend UI

## Deployment Architecture

The platform uses Helmfile dependencies for ordered deployment within a **single ArgoCD application**:

1. **Wave 1**: Storage resources
2. **Wave 2**: Infrastructure services (MongoDB, RabbitMQ, Qdrant, Docling) 
3. **Wave 3**: Platform services (shared config, SSO authentication)
4. **Wave 4**: Application services (Dataflow, MultiAgent backends)
5. **Wave 5**: User interface (UI frontend)

## Deployment

### Simple Single Command Deployment
Deploy the entire UnifAI platform with one command:
```bash
kubectl apply -f gitops/unifai-platform.yaml
```

This single application uses Helmfile to automatically deploy all infrastructure and application components in the correct order.

## Application Architecture

### Single Application with Multiple Helm Releases
- **Single ArgoCD Application**: `unifai-platform` is the only application visible in ArgoCD UI
- **Master Helmfile**: `helm/unifai-platform.yaml.gotmpl` manages all components internally
- **Helm Releases**: All components deploy as individual Helm releases within the single application
- **Dependency Management**: Uses Helmfile `needs` declarations for proper ordering
- **Dynamic Configuration**: Helmfile hooks create dynamic configurations after services are ready

### Component Types
- **Infrastructure**: Individual Helm charts from `helm/shared-resources/`
- **Applications**: Individual Helm charts from `helm/dataflow/`, `helm/multiagent/`, `helm/ui/`
- **Values**: Component-specific value files from `helm/values/`
- **Hooks**: Post-deployment hooks for service discovery and dynamic configuration

## Monitoring

### ArgoCD UI Experience
- **Root Level**: You will see only **1 application** (`unifai-platform`) in the ArgoCD root page
- **Application Details**: Click into `unifai-platform` to see all Helm releases (components)
- **Component Status**: Each component appears as a Helm release within the main application

### CLI Monitoring
```bash
# Check the single platform application
argocd app get unifai-platform

# List all applications (should see only unifai-platform)
argocd app list

# Check Helm releases within the application (from within the cluster)
helm list -n tag-ai--runtime-int
```

## File Organization

```
gitops/
├── unifai-platform.yaml          # Single ArgoCD application
├── argocd.install.tenant.yaml    # ArgoCD installation (if needed)
└── README.md                     # This documentation

helm/
├── unifai-platform.yaml.gotmpl   # Master Helmfile managing all components
├── dataflow.yaml.gotmpl           # Individual component helmfiles (for reference)
├── multiagent.yaml.gotmpl
├── shared-resources.yaml.gotmpl
├── sso.yaml.gotmpl
├── ui.yaml.gotmpl
└── values/                       # All component value files
```

## Prerequisites

1. ArgoCD installed and running in `tag-ai--runtime-int` namespace
2. GitLab repository access configured  
3. Helm charts and values files present in the repository
4. **Choose one approach:**
   - **Option A**: Helmfile plugin installed in ArgoCD (see Solution 1 below)
   - **Option B**: Use the Helm chart with dependencies approach (no plugin required)

## Key Benefits

- **Simplified ArgoCD UI**: Only 1 application visible at the root level
- **Hierarchical Management**: All components nested under the main application
- **Proper Dependencies**: Helmfile `needs` ensures correct deployment order
- **Single Source of Truth**: One master helmfile controls the entire platform
- **Dynamic Configuration**: Post-deployment hooks handle service discovery
- **Easier Debugging**: All components visible within a single application context

## Implementation Solutions

### **If you get "helmfile plugin not found" error:**

#### **Solution 1: Install Helmfile Plugin (Recommended)**
1. Apply the updated ArgoCD configuration:
   ```bash
   kubectl apply -f gitops/argocd.install.tenant.yaml
   kubectl apply -f gitops/helmfile-plugin-config.yaml
   ```
2. Restart ArgoCD pods to load the plugin:
   ```bash
   kubectl rollout restart deployment argocd-repo-server -n tag-ai--runtime-int
   ```

#### **Solution 2: Use Helm Chart Dependencies (No Plugin Required)**
The platform is pre-configured to use this approach:
- Uses `helm/unifai-platform-chart/` with all components as dependencies
- Works with standard ArgoCD installation
- Just deploy: `kubectl apply -f gitops/unifai-platform.yaml`

## Notes

- **ArgoCD Experience**: You'll see only `unifai-platform` on the root page, with all components nested inside it
- **Dependency Management**: Handled by either Helmfile or Helm chart dependencies
- **Values Management**: Uses existing component-specific value files from `helm/values/`
- **No Plugin Required**: Solution 2 works with any standard ArgoCD installation
