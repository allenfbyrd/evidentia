"""Power BI REST API client (v0.7.8 P1.2).

Pure-Python client over httpx (already a base dep) + MSAL Python
for the Azure AD service-principal OAuth2 flow.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx

from evidentia_integrations.powerbi.config import PowerBIConfig

if TYPE_CHECKING:
    # Type-only import; msal is in the [powerbi] optional extra.
    import msal  # noqa: F401


class PowerBIApiError(Exception):
    """Base class for all Power BI integration failures."""


class PowerBIAuthError(PowerBIApiError):
    """OAuth2 client-credentials flow failed (bad client secret,
    wrong tenant, missing service-principal permission, etc.)."""


class PowerBIPublishError(PowerBIApiError):
    """A specific publish step failed (dataset creation, row push,
    workspace ID lookup, etc.)."""


class PowerBIClient:
    """Power BI client.

    Args:
        config: typed :class:`PowerBIConfig`. Holds workspace +
            tenant + client identifiers + the env-var name where
            the client secret lives.
        http_timeout: httpx request timeout in seconds. Power BI
            REST endpoints are usually fast (< 1s) but row-push
            can take longer for large batches.

    Usage::

        with PowerBIClient(config) as client:
            dataset_id = client.ensure_dataset(
                dataset_name="evidentia-gaps",
                schema=GAP_DATASET_SCHEMA,
            )
            client.push_rows(
                dataset_id=dataset_id,
                table_name="gaps",
                rows=row_list,
            )
    """

    def __init__(
        self,
        config: PowerBIConfig,
        *,
        http_timeout: float = 30.0,
    ) -> None:
        self._config = config
        self._timeout = http_timeout
        self._access_token: str | None = None
        self._http: httpx.Client | None = None

    def __enter__(self) -> PowerBIClient:
        self._signin()
        return self

    def __exit__(self, *_: object) -> None:
        self._close()

    # ── Internal lifecycle ──────────────────────────────────────────

    def _ensure_msal(self) -> Any:
        try:
            import msal
        except ImportError as e:
            raise PowerBIApiError(
                "msal is not installed. Install via the [powerbi] "
                "extra: "
                'pip install "evidentia-integrations[powerbi]"'
            ) from e
        return msal

    def _signin(self) -> None:
        if self._access_token is not None:
            return

        client_secret = os.environ.get(self._config.client_secret_env)
        if not client_secret:
            raise PowerBIAuthError(
                f"Env var '{self._config.client_secret_env}' is "
                f"not set or is empty. Set it to the Azure AD "
                f"service-principal client secret."
            )

        msal = self._ensure_msal()
        try:
            authority = (
                f"{self._config.authority_url.rstrip('/')}/"
                f"{self._config.tenant_id}"
            )
            app = msal.ConfidentialClientApplication(
                client_id=self._config.client_id,
                client_credential=client_secret,
                authority=authority,
            )
            result = app.acquire_token_for_client(
                scopes=[self._config.api_scope]
            )
        except Exception as e:
            raise PowerBIAuthError(
                f"MSAL token acquisition failed "
                f"(driver: {type(e).__name__})"
            ) from e

        if not isinstance(result, dict) or "access_token" not in result:
            err = (
                result.get("error_description")
                if isinstance(result, dict)
                else "unknown"
            )
            raise PowerBIAuthError(
                f"Power BI access token not granted. "
                f"Verify the service principal has "
                f"Dataset.ReadWrite.All on the workspace. "
                f"Detail: {err}"
            )
        self._access_token = str(result["access_token"])
        self._http = httpx.Client(
            base_url=self._config.api_base_url.rstrip("/"),
            timeout=self._timeout,
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            },
        )

    def _close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None
        self._access_token = None

    # ── Public surface ──────────────────────────────────────────────

    def list_datasets(self) -> list[dict[str, Any]]:
        """Enumerate all datasets in the configured workspace."""
        if self._http is None:
            self._signin()
        assert self._http is not None
        try:
            r = self._http.get(
                f"/groups/{self._config.workspace_id}/datasets"
            )
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise PowerBIPublishError(
                f"List datasets failed: {type(e).__name__}: {e}"
            ) from e
        result = r.json()
        value = result.get("value", [])
        if not isinstance(value, list):
            return []
        return list(value)

    def find_dataset_by_name(self, name: str) -> dict[str, Any] | None:
        """Return the first dataset matching `name` exactly, or None."""
        for ds in self.list_datasets():
            if ds.get("name") == name:
                return ds
        return None

    def create_dataset(
        self,
        *,
        dataset_name: str,
        table_name: str,
        schema: list[dict[str, str]],
    ) -> str:
        """Create a Push Dataset with a single table.

        Args:
            dataset_name: human-readable name (Power BI lookup
                key).
            table_name: name for the single table within the
                dataset (Power BI Push Datasets typically have
                one table per dataset).
            schema: list of {name, dataType} dicts per column.

        Returns the new dataset ID.
        """
        if self._http is None:
            self._signin()
        assert self._http is not None
        body = {
            "name": dataset_name,
            "defaultMode": "Push",
            "tables": [
                {"name": table_name, "columns": schema}
            ],
        }
        try:
            r = self._http.post(
                f"/groups/{self._config.workspace_id}/datasets",
                json=body,
            )
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise PowerBIPublishError(
                f"Create dataset '{dataset_name}' failed: "
                f"{type(e).__name__}: {e}"
            ) from e
        result = r.json()
        ds_id = result.get("id")
        if not ds_id:
            raise PowerBIPublishError(
                f"Power BI did not return a dataset ID for "
                f"'{dataset_name}'."
            )
        return str(ds_id)

    def ensure_dataset(
        self,
        *,
        dataset_name: str,
        table_name: str,
        schema: list[dict[str, str]],
    ) -> str:
        """Look up an existing Push Dataset by name; create if missing."""
        existing = self.find_dataset_by_name(dataset_name)
        if existing is not None and "id" in existing:
            return str(existing["id"])
        return self.create_dataset(
            dataset_name=dataset_name,
            table_name=table_name,
            schema=schema,
        )

    def clear_table(
        self, *, dataset_id: str, table_name: str
    ) -> None:
        """Delete all rows from a Push Dataset table.

        Power BI Push Datasets retain rows until explicitly cleared
        (or until the FIFO row limit is hit). For periodic full-
        refresh use cases (the typical compliance-dashboard
        pattern) we clear before pushing.

        F-V08-CR-H3 — first-publish flows on a freshly-created Push
        Dataset can return 404 (table doesn't yet contain rows the
        endpoint can identify) or other 4xx variants from some
        Power BI deployment regions. These are benign — the desired
        post-condition (no rows in the table) is already true. We
        swallow 4xx and let the caller proceed to push_rows. Real
        problems (5xx, network errors) still surface as
        PowerBIPublishError.
        """
        if self._http is None:
            self._signin()
        assert self._http is not None
        try:
            r = self._http.delete(
                f"/groups/{self._config.workspace_id}/datasets/"
                f"{dataset_id}/tables/{table_name}/rows"
            )
        except httpx.HTTPError as e:
            # Network-level failure (timeout, connection refused, etc.)
            raise PowerBIPublishError(
                f"Clear table '{table_name}' failed: "
                f"{type(e).__name__}: {e}"
            ) from e
        if r.status_code == 404 or 400 <= r.status_code < 500:
            # Benign — see docstring. Proceed silently; the caller's
            # subsequent push_rows call will validate the table is
            # actually pushable.
            return
        if r.status_code >= 500:
            raise PowerBIPublishError(
                f"Clear table '{table_name}' failed: "
                f"HTTP {r.status_code} {r.reason_phrase}"
            )

    def push_rows(
        self,
        *,
        dataset_id: str,
        table_name: str,
        rows: list[dict[str, Any]],
    ) -> None:
        """Push rows to a Push Dataset table.

        Power BI's documented limit for a single push request is
        10,000 rows; this method splits into batches of 10,000.
        """
        if self._http is None:
            self._signin()
        assert self._http is not None

        if not rows:
            return

        batch_size = 10_000
        for batch_start in range(0, len(rows), batch_size):
            batch = rows[batch_start : batch_start + batch_size]
            try:
                r = self._http.post(
                    f"/groups/{self._config.workspace_id}/datasets/"
                    f"{dataset_id}/tables/{table_name}/rows",
                    json={"rows": batch},
                )
                r.raise_for_status()
            except httpx.HTTPError as e:
                raise PowerBIPublishError(
                    f"Push rows to '{table_name}' failed "
                    f"(batch starting at row {batch_start}): "
                    f"{type(e).__name__}: {e}"
                ) from e
