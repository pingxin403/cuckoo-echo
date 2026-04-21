# Tasks

## Implementation Checklist

### Phase 1: Core SSO
- [x] 1.1 SAML 2.0 support
- [x] 1.2 OIDC support
- [x] 1.3 Certificate management

### Phase 2: Integration
- [x] 2.1 Role mapping
- [x] 2.2 JIT provisioning
- [x] 2.3 Session management

### Phase 3: Enterprise
- [x] 3.1 Multi-domain support
- [x] 3.2 MFA enforcement
- [x] 3.3 Audit logging

## API Endpoints (planned)

- GET/POST /admin/v1/auth/saml/config
- GET/POST /admin/v1/auth/oidc/config
- POST /admin/v1/auth/saml/sso
- GET /admin/v1/auth/saml/metadata