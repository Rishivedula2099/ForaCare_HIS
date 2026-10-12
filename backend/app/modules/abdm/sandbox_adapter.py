from app.modules.abdm.gateway_adapter import GatewayAbdmAdapter


class SandboxAbdmAdapter(GatewayAbdmAdapter):
    """NHA sandbox gateway (https://dev.abdm.gov.in/gateway/v0.5)."""

    mode = "sandbox"
