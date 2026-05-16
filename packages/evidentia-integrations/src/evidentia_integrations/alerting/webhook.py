"""Generic HTTP webhook alert channel (v0.9.3 P1.2).

POSTs a JSON payload with an HMAC-SHA256 signature header so
downstream receivers can verify the message came from this
daemon (vs a spoofed source) using a shared secret.

Payload shape:

    {
      "cadence_slug": "nist-800-53-rev5-ca7",
      "framework":    "nist-800-53-rev5",
      "activity":     "continuous-monitoring",
      "state":        "overdue",
      "days_until_due": -45,
      "last_completed": "2026-01-01",
      "next_due":      "2026-02-01"
    }

Signature header:

    X-Evidentia-Signature: sha256=<hex digest>

Receivers compute ``HMAC-SHA256(shared_secret, raw_body_bytes)``
and compare to the header value.

Secrets per the v0.9.3 cycle-open sign-off:

- ``WebhookConfig.secret`` MUST already be resolved via
  :func:`evidentia_core.conmon.alerting.resolve_secret`.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import urllib.request
from dataclasses import dataclass
from urllib.error import HTTPError, URLError

from evidentia_core.conmon.daemon import CycleObservation


@dataclass(frozen=True)
class WebhookConfig:
    """Operator-supplied webhook channel configuration. Immutable."""

    url: str
    secret: str
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not self.url:
            raise ValueError("webhook URL required")
        if not self.url.startswith(("https://", "http://")):
            raise ValueError(
                f"webhook URL must be http:// or https://; "
                f"got {self.url!r}"
            )
        if not self.secret:
            raise ValueError(
                "webhook secret required (resolve via "
                "evidentia_core.conmon.alerting.resolve_secret)"
            )


class WebhookAlertChannel:
    """:class:`AlertChannel` impl that POSTs to a single webhook
    endpoint per observation. Uses stdlib urllib to avoid taking on
    requests/httpx as a runtime dep for a single POST.
    """

    name = "webhook"

    def __init__(self, config: WebhookConfig) -> None:
        self._config = config

    def dispatch(self, obs: CycleObservation) -> None:
        payload = {
            "cadence_slug": obs.cadence.slug,
            "framework": obs.cadence.framework,
            "activity": obs.cadence.activity,
            "state": obs.state.value,
            "days_until_due": obs.days_until_due,
            "last_completed": obs.last_completed.isoformat(),
            "next_due": obs.next_due.isoformat(),
        }
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature = hmac.new(
            self._config.secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        request = urllib.request.Request(
            url=self._config.url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": "evidentia-conmon-daemon/v0.9.3",
                "X-Evidentia-Signature": f"sha256={signature}",
            },
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self._config.timeout_seconds,
            ) as response:
                if response.status >= 400:
                    raise RuntimeError(
                        f"webhook POST returned status "
                        f"{response.status}"
                    )
        except HTTPError as exc:
            raise RuntimeError(
                f"webhook POST failed with HTTP {exc.code}: "
                f"{exc.reason}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"webhook POST failed (transport): {exc.reason}"
            ) from exc
