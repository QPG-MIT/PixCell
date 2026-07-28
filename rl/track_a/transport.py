"""Local kill-switch for the Tinker SDK's pyqwest transport.

The SDK (0.22.7) defaults to a reqwest/rustls HTTP backend (``pyqwest``)
whose bundled trust store rejects the certificate chain this host currently
receives for ``tinker.thinkingmachines.dev`` (``invalid peer certificate:
UnknownIssuer`` against the Google Trust Services WE1 chain), while httpx's
certifi-based verification accepts it. The SDK's own kill-switch for this
transport is server-side only (``ClientConfigResponse.use_pyqwest_transport``),
so a client whose auth bootstrap dies on pyqwest can never be told to stop
using it. Verified empirically: the same auth POST succeeds through httpx
and curl in ~0.2s and fails through pyqwest with UnknownIssuer.

``disable_pyqwest_transport()`` swaps the transport factory for one that
returns ``None`` — httpx then builds its default (working) transport. Call
it before any ``tinker.ServiceClient`` is constructed. Remove when the SDK
grows a client-side override or pyqwest validates this chain.
"""

from __future__ import annotations


def disable_pyqwest_transport() -> None:
    import tinker._base_client as base_client

    base_client._default_pyqwest_transport = lambda: None
