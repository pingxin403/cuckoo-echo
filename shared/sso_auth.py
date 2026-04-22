"""SSO/SAML/OIDC authentication."""

from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime
import hashlib
import base64
import xml.etree.ElementTree as ET


class SAMLConfig(BaseModel):
    tenant_id: str
    idp_entity_id: str
    idp_sso_url: str
    idp_certificate: str
    sp_entity_id: str
    attribute_mapping: dict[str, str] = {}
    enabled: bool = False


class OIDCConfig(BaseModel):
    tenant_id: str
    client_id: str
    client_secret: str
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    scope: str = "openid email profile"
    enabled: bool = False


class SSOManager:
    def __init__(self, db_pool=None):
        self.db = db_pool
        self._saml_configs: dict[str, SAMLConfig] = {}
        self._oidc_configs: dict[str, OIDCConfig] = {}

    async def configure_saml(
        self,
        tenant_id: str,
        idp_entity_id: str,
        idp_sso_url: str,
        idp_certificate: str,
        sp_entity_id: str,
    ) -> SAMLConfig:
        config = SAMLConfig(
            tenant_id=tenant_id,
            idp_entity_id=idp_entity_id,
            idp_sso_url=idp_sso_url,
            idp_certificate=idp_certificate,
            sp_entity_id=sp_entity_id,
        )
        self._saml_configs[tenant_id] = config
        return config

    async def configure_oidc(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        issuer: str,
    ) -> OIDCConfig:
        config = OIDCConfig(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            issuer=issuer,
            authorization_endpoint=f"{issuer}/authorize",
            token_endpoint=f"{issuer}/oauth/token",
            userinfo_endpoint=f"{issuer}/userinfo",
        )
        self._oidc_configs[tenant_id] = config
        return config

    def get_saml_config(self, tenant_id: str) -> Optional[SAMLConfig]:
        return self._saml_configs.get(tenant_id)

    def get_oidc_config(self, tenant_id: str) -> Optional[OIDCConfig]:
        return self._oidc_configs.get(tenant_id)

    def generate_saml_request(self, tenant_id: str, acs_url: str) -> str:
        config = self._saml_configs.get(tenant_id)
        if not config:
            raise ValueError(f"No SAML config for tenant: {tenant_id}")

        request_id = f"__{hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:16]}"

        saml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{datetime.now().isoformat()}"
    AssertionConsumerServiceURL="{acs_url}">
    <saml:Issuer xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">{config.sp_entity_id}</saml:Issuer>
</samlp:AuthnRequest>"""

        return base64.b64encode(saml_request.encode()).decode()

    def parse_saml_response(self, saml_response: str) -> dict[str, Any]:
        decoded = base64.b64decode(saml_response).decode()

        try:
            root = ET.fromstring(decoded)
        except ET.ParseError:
            return {"error": "Invalid SAML response"}

        ns = {"saml": "urn:oasis:names:tc:SAML:2.0:assertion"}

        name_id = root.find(".//saml:NameID", ns)
        attributes = {}

        for attr in root.findall(".//saml:Attribute", ns):
            attr_name = attr.get("Name")
            attr_value = attr.find(".//saml:AttributeValue", ns)
            if attr_name and attr_value is not None:
                attributes[attr_name] = attr_value.text

        return {
            "name_id": name_id.text if name_id is not None else None,
            "attributes": attributes,
        }

    def map_idp_roles(self, idp_claims: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
        mapped = {}
        for local_attr, idp_attr in mapping.items():
            mapped[local_attr] = idp_claims.get(idp_attr)
        return mapped


def get_sso_manager() -> SSOManager:
    global _sso_manager
    if _sso_manager is None:
        _sso_manager = SSOManager()
    return _sso_manager


_sso_manager: Optional[SSOManager] = None