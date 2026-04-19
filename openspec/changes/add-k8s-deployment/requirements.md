# Requirements: K8s Deployment

## Functional

1. **Deployments**
   - api-gateway: 2+ replicas
   - chat-service: 3+ replicas
   - admin-service: 1+ replica
   - knowledge-pipeline: 1+ replica

2. **Services**
   - ClusterIP for internal
   - Ingress for external

3. **Config**
   - ConfigMap for config
   - Secret for secrets

## Non-Functional

- Health checks: /health
- Readiness: /ready
- Resource limits defined

## Out of Scope

- Auto-scaling HPA (future)
- Service mesh (future)