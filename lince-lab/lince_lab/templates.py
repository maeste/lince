"""Lima template builder (blueprint §3, §5; lima.md).

:func:`build_template` turns a config + a recipe's declared *needs* into a Lima
instance template, emitted as **JSON text** (which is valid YAML, so no external
YAML library is required — stdlib only).

The build is **policy-forced**: regardless of what a client asks for, the
generated template always sets the isolation invariants —

* ``plain: true``           — strip port-forwarding / mounts / guest-agent extras
* ``mounts: []``            — no host filesystem is exposed
* ``ssh.loadDotSSHPubKeys: false`` — host ``~/.ssh/*.pub`` keys are not injected

and a ``boot`` provision script that **cuts egress by default**. Only when the
recipe carries a non-empty network allowlist does the boot script install an
allow-listed egress rule instead of a hard cut. ``cpus`` / ``memory`` / ``disk``
come from the recipe needs (falling back to config defaults); the base image
``location`` + ``digest`` come from the config image allowlist.

**Network isolation is fail-closed.** The deny-by-default boot script runs under
``set -e``, detects the real default-route interface dynamically (never assumes
``eth0``), installs ``nft`` or aborts the boot, and sets an nft default-DROP
egress policy with the critical drop NOT swallowed by ``|| true``. The allowlist
posture is **host-scoped**: ``allow_hosts`` are resolved to IP addresses
*host-side at template-build time* (:func:`resolve_allow_ips`) and emitted as
``ip daddr <ip> tcp dport <port> accept`` rules under the same default-DROP
policy — there is never an any-host ``tcp dport <p> accept`` rule. A host that
fails to resolve is dropped (fail-closed, never widened to any-host).
"""

from __future__ import annotations

import json
import socket
from typing import Any

from lince_lab.errors import DataError

# Marker comment lines emitted inside the boot provision script so callers (and
# tests) can identify which egress posture was baked in.
NET_CUT_MARKER = "lince-lab: egress cut (deny-by-default)"
NET_ALLOW_MARKER = "lince-lab: egress allowlist"


def resolve_allow_ips(allow_hosts: list[str]) -> list[str]:
    """Resolve ``allow_hosts`` to a de-duplicated list of literal IP addresses.

    Resolution happens **host-side** (in the broker process) at template-build
    time via :func:`socket.getaddrinfo`, so the baked nft rules pin concrete
    destination IPs rather than trusting in-guest DNS. A host that does not
    resolve is silently **omitted** (fail-closed: it never widens to any-host).

    Caveat: CDN / load-balanced hosts churn their IPs, so an allowlist pinned at
    build time can drift from the host's live IP set during a long-lived VM; this
    is the intentional trade-off for a host-scoped, exfil-resistant allowlist.
    Order is preserved (first-seen) and both A (IPv4) and AAAA (IPv6) records are
    kept.
    """
    ips: list[str] = []
    seen: set[str] = set()
    for host in allow_hosts:
        host_s = str(host).strip()
        if not host_s:
            continue
        try:
            infos = socket.getaddrinfo(host_s, None, proto=socket.IPPROTO_TCP)
        except OSError:
            # Unresolvable → omit (fail-closed). Never fall back to any-host.
            continue
        for info in infos:
            ip = info[4][0]
            if ip and ip not in seen:
                seen.add(ip)
                ips.append(ip)
    return ips


def _resolve_image(config: dict[str, Any], image_name: str) -> dict[str, str]:
    """Return the ``{location, arch, digest}`` for ``image_name`` from config.

    Raises :class:`~lince_lab.errors.DataError` if the image is not in the
    config allowlist — a recipe may only ask for a known, pinned image.
    """
    images = config.get("images", {})
    entry = images.get(image_name)
    if not isinstance(entry, dict) or not entry.get("location"):
        known = ", ".join(sorted(images)) or "(none)"
        raise DataError(f"unknown image {image_name!r}; allowed images: {known}")
    return {
        "location": str(entry["location"]),
        "arch": str(entry.get("arch", "x86_64")),
        "digest": str(entry.get("digest", "")),
    }


def _need(needs: dict[str, Any], config: dict[str, Any], key: str) -> Any:
    """Resolve a resource ``key`` from recipe needs, falling back to config ``vm``."""
    if key in needs and needs[key] is not None:
        return needs[key]
    return config.get("vm", {}).get(key)


# Shell preamble shared by the cut + allow scripts. It is FAIL-CLOSED:
#   * ``set -e`` aborts the boot on any unhandled command failure;
#   * ``nft`` is installed if missing, and the boot ABORTS if it cannot be
#     obtained (a VM that can't enforce egress must not come up networked);
#   * the default-DROP output policy is installed WITHOUT ``|| true`` so a failed
#     drop fails the boot rather than silently leaving egress open.
# Loopback stays up so in-guest tooling works; the default route interface is
# detected dynamically (never the hardcoded ``eth0``).
_NFT_FAILCLOSED_PREAMBLE = (
    "set -e\n"
    "# Detect the real default-route interface (do NOT assume 'eth0').\n"
    "DEFAULT_IF=$(ip route show default 2>/dev/null | sed -n 's/.* dev \\([^ ]*\\).*/\\1/p' | head -n1)\n"
    'echo "lince-lab: default-route interface: ${DEFAULT_IF:-<none>}" >&2\n'
    "# Ensure nft is present; install it or ABORT the boot (fail-closed).\n"
    "if ! command -v nft >/dev/null 2>&1; then\n"
    "  if command -v dnf >/dev/null 2>&1; then dnf install -y nftables\n"
    "  elif command -v apt-get >/dev/null 2>&1; then apt-get update && apt-get install -y nftables\n"
    "  elif command -v apk >/dev/null 2>&1; then apk add --no-cache nftables\n"
    "  else echo 'lince-lab: nft unavailable and no known package manager; aborting boot' >&2; exit 1\n"
    "  fi\n"
    "fi\n"
    'command -v nft >/dev/null 2>&1 || { echo \'lince-lab: nft install failed; aborting boot\' >&2; exit 1; }\n'
    "# Fresh table; default-DROP output policy is the critical fail-closed cut.\n"
    "nft delete table inet lince_lab 2>/dev/null || true\n"
    "nft add table inet lince_lab\n"
    "nft add chain inet lince_lab output '{ type filter hook output priority 0 ; policy drop ; }'\n"
    "nft add rule inet lince_lab output oif lo accept\n"
    # Allow replies to connections opened from OUTSIDE the guest — notably Lima's
    # management SSH (host -> guest). Without this the guest's SSH reply packets
    # are egress and get dropped, so Lima never connects ("waiting for ssh" -> the
    # VM never reaches 'running'). This does NOT let the agent initiate egress: a
    # NEW outbound connection still has no accept rule and hits the default drop.
    "nft add rule inet lince_lab output ct state established,related accept\n"
)


def _net_cut_script() -> str:
    """A FAIL-CLOSED boot provision that severs outbound networking (deny-by-default).

    Runs under ``set -e``; installs ``nft`` or aborts; sets a default-DROP egress
    policy (only loopback survives). The interface is detected dynamically — there
    is no hardcoded ``eth0`` — so the cut never depends on a guessed NIC name.
    """
    return f"#!/bin/sh\n# {NET_CUT_MARKER}\n{_NFT_FAILCLOSED_PREAMBLE}"


def _net_allow_script(allow_ips: list[str], allow_ports: list[int]) -> str:
    """A FAIL-CLOSED boot provision: default-DROP egress + a host-scoped allowlist.

    ``allow_ips`` are concrete IP addresses already resolved host-side (see
    :func:`resolve_allow_ips`); each is paired with every allow port to emit an
    ``ip daddr <ip> tcp dport <port> accept`` rule under the default-DROP policy.
    There is NO any-host ``tcp dport <p> accept`` rule — egress is pinned to the
    resolved hosts only. Built only when at least one ``ip daddr ... accept`` rule
    exists (the caller fail-closes to the cut script otherwise).
    """
    lines = [
        "#!/bin/sh",
        f"# {NET_ALLOW_MARKER}",
        # The preamble already permits established/related replies (Lima SSH).
        _NFT_FAILCLOSED_PREAMBLE.rstrip("\n"),
    ]
    ports = [int(p) for p in allow_ports] or [443]
    for ip in allow_ips:
        for port in ports:
            # Host-scoped accept: pinned destination IP + port. NEVER any-host.
            lines.append(f"nft add rule inet lince_lab output ip daddr {ip} tcp dport {port} accept")
    return "\n".join(lines) + "\n"


def build_template(config: dict[str, Any], recipe_needs: dict[str, Any]) -> str:
    """Build a policy-forced Lima template, returned as JSON text (valid YAML).

    ``recipe_needs`` keys (all optional except ``image``):

    * ``image``       — short name keyed into the config image allowlist.
    * ``cpus`` / ``memory`` / ``disk`` — resource caps (fall back to config).
    * ``allow_hosts`` / ``allow_ports`` — network allowlist. ``allow_hosts`` are
      resolved to IP addresses **host-side at build time** (or taken pre-resolved
      from ``allow_ips`` if the caller already did so). The boot script installs
      ``ip daddr <ip> tcp dport <port> accept`` rules under a default-DROP policy
      only when at least one host resolves; otherwise it FAILS CLOSED to the hard
      egress cut (never an any-host rule).
    * ``allow_ips``   — optional pre-resolved IP list (overrides ``allow_hosts``
      resolution); used by the broker so resolution happens exactly once.
    * ``provision``   — extra ``system`` / ``user`` provision scripts to append
      after the forced ``boot`` egress script.
    """
    image_name = recipe_needs.get("image")
    if not image_name:
        raise DataError("recipe needs must specify an 'image'")
    image = _resolve_image(config, str(image_name))

    allow_hosts = list(recipe_needs.get("allow_hosts") or [])
    allow_ports = list(recipe_needs.get("allow_ports") or [])
    # Prefer a pre-resolved IP list (broker resolved once); else resolve host-side
    # now. An empty resolved set ⇒ fail-closed to the hard cut (never any-host).
    if recipe_needs.get("allow_ips") is not None:
        allow_ips = [str(ip) for ip in recipe_needs["allow_ips"]]
    else:
        allow_ips = resolve_allow_ips(allow_hosts)

    if allow_ips:
        boot_script = _net_allow_script(allow_ips, allow_ports)
    else:
        boot_script = _net_cut_script()

    provision: list[dict[str, str]] = [{"mode": "boot", "script": boot_script}]
    for extra in recipe_needs.get("provision") or []:
        if not isinstance(extra, dict) or "script" not in extra:
            raise DataError("each extra provision entry needs a 'script'")
        provision.append(
            {
                "mode": str(extra.get("mode", "system")),
                "script": str(extra["script"]),
            }
        )

    image_entry: dict[str, str] = {"location": image["location"], "arch": image["arch"]}
    if image["digest"]:
        image_entry["digest"] = image["digest"]

    template: dict[str, Any] = {
        # ── policy-forced isolation invariants (non-overridable) ──
        "plain": True,
        "mounts": [],
        "ssh": {"loadDotSSHPubKeys": False, "forwardAgent": False},
        # ── image + resources ──
        "images": [image_entry],
        "cpus": int(_need(recipe_needs, config, "cpus")),
        "memory": str(_need(recipe_needs, config, "memory")),
        "disk": str(_need(recipe_needs, config, "disk")),
        # ── provisioning (forced egress posture first) ──
        "provision": provision,
    }
    # JSON with indentation is valid YAML and round-trips through any YAML parser.
    return json.dumps(template, indent=2, sort_keys=True) + "\n"
