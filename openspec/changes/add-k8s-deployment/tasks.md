# Tasks

## Implementation Checklist

- [x] 1.1 创建 k8s/ base manifests (k8s/*.yaml)
- [x] 1.2 添加 api-gateway deployment (k8s/api-gateway-deployment.yaml)
- [x] 1.3 添加 chat-service deployment (k8s/chat-service-deployment.yaml)
- [x] 1.4 添加 admin-service deployment (k8s/admin-service-deployment.yaml)
- [x] 1.5 添加 knowledge-pipeline deployment (k8s/knowledge-pipeline-deployment.yaml)
- [x] 1.6 添加 ingress / service (k8s/ingress.yaml)
- [x] 1.7 添加 configmap / secret (k8s/pgbouncer-configmap.yaml, secrets.example.yaml)
- [x] 1.8 创建 Helm chart (k8s/Dockerfile)

## 已实现

### K8s Manifests (k8s/)
- api-gateway-deployment.yaml
- chat-service-deployment.yaml
- admin-service-deployment.yaml
- knowledge-pipeline-deployment.yaml
- ingress.yaml
- pgbouncer-configmap.yaml
- secrets.example.yaml
- prometheus-servicemonitor.yaml