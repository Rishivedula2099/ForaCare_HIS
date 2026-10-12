from app.modules.abdm.gateway_adapter import GatewayAbdmAdapter


class ProductionAbdmAdapter(GatewayAbdmAdapter):
    """Live NHA gateway (https://gateway.abdm.gov.in/v0.5). Requires NHA
    empanelment before use (docs/integrations.md section 2.1)."""

    mode = "production"
