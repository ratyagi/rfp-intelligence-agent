"""Microsoft Graph API wrapper — SharePoint, Teams, and Mail search."""
import logging
import os

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _stub_mode() -> bool:
    return os.getenv("STUB_MODE", "false").lower() == "true"


class GraphClient:
    """Wraps Microsoft Graph API for SharePoint, Teams, and Mail search."""

    def __init__(self):
        if not _stub_mode():
            self._client = self._build_client()
        else:
            self._client = None

    def _build_client(self):
        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET")

        if not all([tenant_id, client_id, client_secret]):
            raise EnvironmentError(
                "AZURE_TENANT_ID, AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET must be set in .env"
            )

        try:
            from azure.identity import ClientSecretCredential
            from msgraph import GraphServiceClient
        except ImportError as e:
            raise ImportError(
                "azure-identity and msgraph-sdk-python are required. "
                "Run: pip install azure-identity msgraph-sdk-python"
            ) from e

        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
        return GraphServiceClient(credentials=credential)

    def search_sharepoint(self, query: str, site_id: str, top: int = 5) -> list[dict]:
        """Search SharePoint for documents matching query.

        Returns list of {"title", "url", "excerpt", "last_modified"}.
        Returns empty list on error.
        """
        if _stub_mode():
            return [
                {
                    "title": "Azure Migration Case Study — HealthGov 2024",
                    "url": "https://sharepoint.example.com/sites/proposals/azure-migration-healthgov.pdf",
                    "excerpt": (
                        "Completed migration of 620 VMs from on-premises Windows Server 2016 to Azure IaaS "
                        "with zero unplanned downtime. Achieved 99.97% uptime post-migration."
                    ),
                    "last_modified": "2024-11-15",
                },
                {
                    "title": "ISO 27001 Certification — Current",
                    "url": "https://sharepoint.example.com/sites/compliance/iso27001-cert-2025.pdf",
                    "excerpt": (
                        "Current ISO 27001:2022 certification valid through March 2027. "
                        "Scope covers all cloud delivery operations and data handling practices."
                    ),
                    "last_modified": "2025-03-01",
                },
                {
                    "title": "RFP Response Template — Government Cloud",
                    "url": "https://sharepoint.example.com/sites/proposals/templates/gov-cloud-template.docx",
                    "excerpt": (
                        "Standard response template for government cloud procurement RFPs. "
                        "Includes pre-approved commercial terms and compliance attestations."
                    ),
                    "last_modified": "2025-08-20",
                },
            ][:top]

        try:
            import asyncio
            from msgraph.generated.search.query.query_post_request_body import QueryPostRequestBody
            from msgraph.generated.models.search_request import SearchRequest
            from msgraph.generated.models.entity_type import EntityType

            search_request = SearchRequest()
            search_request.query = type("q", (), {"query_string": query})()
            search_request.entity_types = [EntityType.DriveItem]
            search_request.size = top
            if site_id:
                search_request.content_sources = [f"/sites/{site_id}"]

            body = QueryPostRequestBody()
            body.requests = [search_request]

            result = asyncio.get_event_loop().run_until_complete(
                self._client.search.query.post(body)
            )

            items = []
            for hit_container in (result.value or []):
                for hit in (hit_container.hits or []):
                    resource = hit.resource
                    items.append({
                        "title": getattr(resource, "name", "Untitled"),
                        "url": getattr(resource, "web_url", ""),
                        "excerpt": hit.summary or "",
                        "last_modified": str(getattr(resource, "last_modified_date_time", "")),
                    })
            return items[:top]

        except Exception as e:
            logger.error(f"GraphClient.search_sharepoint error: {e}")
            return []

    def search_teams(self, query: str, top: int = 5) -> list[dict]:
        """Search Teams channel messages matching query.

        Returns list of {"message", "channel", "url", "timestamp"}.
        Returns empty list on error.
        """
        if _stub_mode():
            return [
                {
                    "message": (
                        "We achieved 99.96% uptime on the StateGov migration last quarter — "
                        "MTTR was 18 minutes average. Good reference for SLA questions."
                    ),
                    "channel": "delivery-updates",
                    "url": "https://teams.microsoft.com/l/message/example/123",
                    "timestamp": "2025-09-10T14:32:00Z",
                },
                {
                    "message": (
                        "Azure Site Recovery cutover for FinanceDept was 2.5 hours, well under the 4-hour "
                        "window they required. Zero data loss confirmed by their ops team."
                    ),
                    "channel": "project-financedept",
                    "url": "https://teams.microsoft.com/l/message/example/456",
                    "timestamp": "2025-11-03T09:15:00Z",
                },
            ][:top]

        try:
            import asyncio
            from msgraph.generated.search.query.query_post_request_body import QueryPostRequestBody
            from msgraph.generated.models.search_request import SearchRequest
            from msgraph.generated.models.entity_type import EntityType

            search_request = SearchRequest()
            search_request.query = type("q", (), {"query_string": query})()
            search_request.entity_types = [EntityType.ChatMessage]
            search_request.size = top

            body = QueryPostRequestBody()
            body.requests = [search_request]

            result = asyncio.get_event_loop().run_until_complete(
                self._client.search.query.post(body)
            )

            items = []
            for hit_container in (result.value or []):
                for hit in (hit_container.hits or []):
                    resource = hit.resource
                    items.append({
                        "message": getattr(resource, "body", {}).get("content", hit.summary or ""),
                        "channel": getattr(resource, "channel_identity", {}).get("channel_id", ""),
                        "url": getattr(resource, "web_url", ""),
                        "timestamp": str(getattr(resource, "created_date_time", "")),
                    })
            return items[:top]

        except Exception as e:
            logger.error(f"GraphClient.search_teams error: {e}")
            return []

    def search_mail(self, query: str, top: int = 5) -> list[dict]:
        """Search Outlook mail matching query.

        Returns list of {"subject", "from", "excerpt", "date"}.
        Returns empty list on error.
        """
        if _stub_mode():
            return [
                {
                    "subject": "RE: Fixed-price proposal — cloud migration engagement",
                    "from": "procurement@clientco.com",
                    "excerpt": (
                        "We accepted the fixed-price Year 1–3 schedule. The CPI+2% escalation cap "
                        "was agreed and documented in the signed SOW."
                    ),
                    "date": "2025-07-22",
                },
                {
                    "subject": "Privacy Act compliance confirmation — project Aurora",
                    "from": "legal@internalco.com",
                    "excerpt": (
                        "Legal confirms full Privacy Act 1988 compliance for project Aurora data handling. "
                        "NDB scheme notification procedures documented in the DPIA."
                    ),
                    "date": "2025-05-14",
                },
            ][:top]

        try:
            import asyncio

            result = asyncio.get_event_loop().run_until_complete(
                self._client.me.messages.get(
                    request_configuration=lambda rc: setattr(
                        rc.query_parameters, "filter", f"contains(subject,'{query}')"
                    ) or setattr(rc.query_parameters, "top", top)
                )
            )

            items = []
            for msg in (result.value or []):
                items.append({
                    "subject": msg.subject or "",
                    "from": (msg.from_.email_address.address if msg.from_ else ""),
                    "excerpt": (msg.body_preview or "")[:300],
                    "date": str(msg.received_date_time or ""),
                })
            return items[:top]

        except Exception as e:
            logger.error(f"GraphClient.search_mail error: {e}")
            return []
