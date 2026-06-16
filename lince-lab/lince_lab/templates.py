"""Lima template builder + runtime egress lock-down (blueprint §3, §5; lima.md).

:func:`build_template` turns a config + a recipe's declared *needs* into a Lima
instance template, emitted as **JSON text** (which is valid YAML, so no external
YAML library is required — stdlib only).

The build is **policy-forced**: regardless of what a client asks for, the
generated template always sets the isolation invariants —

* ``plain: true``           — strip port-forwarding / mounts / guest-agent extras
* ``mounts: []``            — no host filesystem is exposed
* ``ssh.loadDotSSHPubKeys: false`` — host ``~/.ssh/*.pub`` keys are not injected

``cpus`` / ``memory`` / ``disk`` come from the recipe needs (falling back to
config defaults); the base image ``location`` + ``digest`` come from the config
image allowlist.

**Egress is NOT cut at boot.** Provisioning a guest (installing ``ht``, the node
toolchain, git/python, ...) is *trusted setup* and needs the network: a boot-time
egress cut would block it (``dnf install`` would fail, ``ht`` could never be
fetched). So the template boots a **normal networked VM**; the egress lock-down is
applied at *runtime* by the broker via :func:`egress_lockdown_argv`, AFTER the
recipe's ``[[provision]]`` scripts have run with network up and BEFORE the
agent-driven recipe steps execute. The thing we restrict is the agent-driven
steps, not the trusted provisioning.

The runtime lock-down (:func:`egress_lockdown_script`) carries the SAME
fail-closed nft logic the boot provision used to: it ensures ``nft`` is present,
creates table ``inet lince_lab`` with a default-DROP output chain, keeps loopback
and ``ct state established,related`` (CRITICAL: keeps Lima's management SSH
alive), and for each ``allow_ip`` × ``allow_port`` adds an
``ip daddr <ip> tcp dport <port> accept`` rule under that default-DROP policy.
There is never an any-host ``tcp dport <p> accept`` rule. Empty ``allow_ips`` ⇒
deny (drop-only). :func:`resolve_allow_ips` resolves ``allow_hosts`` to IPs
host-side and is now consumed by the runtime lock-down, not the template.
"""

from __future__ import annotations

import json
import socket
from typing import Any

from lince_lab.errors import DataError

# Marker comment lines emitted inside the runtime lock-down script so callers (and
# tests) can identify which egress posture was applied.
NET_CUT_MARKER = "lince-lab: egress cut (deny-by-default)"
NET_ALLOW_MARKER = "lince-lab: egress allowlist"


def resolve_allow_ips(allow_hosts: list[str]) -> list[str]:
    """Resolve ``allow_hosts`` to a de-duplicated list of literal IP addresses.

    Resolution happens **host-side** (in the broker process) at lock-down time
    via :func:`socket.getaddrinfo`, so the runtime nft rules pin concrete
    destination IPs rather than trusting in-guest DNS. A host that does not
    resolve is silently **omitted** (fail-closed: it never widens to any-host).

    Caveat: CDN / load-balanced hosts churn their IPs, so an allowlist pinned at
    lock-down time can drift from the host's live IP set during a long-lived VM;
    this is the intentional trade-off for a host-scoped, exfil-resistant
    allowlist. Order is preserved (first-seen) and both A (IPv4) and AAAA (IPv6)
    records are kept.
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


# Shell preamble shared by the deny + allow lock-downs. It is FAIL-CLOSED:
#   * ``set -e`` aborts on any unhandled command failure;
#   * ``nft`` is installed if missing, and the script ABORTS if it cannot be
#     obtained (a VM that can't enforce egress must not run agent steps);
#   * the default-DROP output policy is installed WITHOUT ``|| true`` so a failed
#     drop fails the lock-down rather than silently leaving egress open.
# The lock-down runs while the network is still UP (right after provisioning), so
# the nft install can still reach a package mirror; loopback stays up so in-guest
# tooling works.
_NFT_FAILCLOSED_PREAMBLE = (
    "set -e\n"
    "# Ensure nft is present; install it or ABORT (fail-closed).\n"
    "if ! command -v nft >/dev/null 2>&1; then\n"
    "  if command -v dnf >/dev/null 2>&1; then dnf install -y nftables\n"
    "  elif command -v apt-get >/dev/null 2>&1; then apt-get update && apt-get install -y nftables\n"
    "  elif command -v apk >/dev/null 2>&1; then apk add --no-cache nftables\n"
    "  else echo 'lince-lab: nft unavailable and no known package manager; aborting lock-down' >&2; exit 1\n"
    "  fi\n"
    "fi\n"
    'command -v nft >/dev/null 2>&1 || { echo \'lince-lab: nft install failed; aborting lock-down\' >&2; exit 1; }\n'
    "# Fresh table; default-DROP output policy is the critical fail-closed cut.\n"
    "nft delete table inet lince_lab 2>/dev/null || true\n"
    "nft add table inet lince_lab\n"
    "nft add chain inet lince_lab output '{ type filter hook output priority 0 ; policy drop ; }'\n"
    "nft add rule inet lince_lab output oif lo accept\n"
    # Allow replies to connections opened from OUTSIDE the guest — notably Lima's
    # management SSH (host -> guest). Without this the guest's SSH reply packets
    # are egress and get dropped, so Lima loses its connection. This does NOT let
    # the agent initiate egress: a NEW outbound connection still has no accept rule
    # and hits the default drop.
    "nft add rule inet lince_lab output ct state established,related accept\n"
)


def egress_lockdown_script(allow_ips: list[str], allow_ports: list[int]) -> str:
    """Return a ``/bin/sh`` script that applies the runtime egress lock-down.

    The script is FAIL-CLOSED and is meant to run inside the guest (via ``sudo``)
    AFTER provisioning, while the network is still up:

    * it ensures ``nft`` is present (install or ``exit 1``);
    * it creates table ``inet lince_lab`` with an ``output`` chain whose policy is
      DROP, accepting only ``oif lo`` and ``ct state established,related`` (the
      latter keeps Lima's management SSH alive);
    * for each ``allow_ip`` × ``allow_port`` it adds an
      ``ip daddr <ip> tcp dport <port> accept`` rule under that default-DROP
      policy. There is NEVER an any-host ``tcp dport <p> accept`` rule.

    Empty ``allow_ips`` ⇒ a deny (drop-only) posture: the default-DROP policy with
    no accept rules. ``allow_ports`` defaults to ``[443]`` when allow_ips are
    present but no ports were given.
    """
    if allow_ips:
        marker = NET_ALLOW_MARKER
    else:
        marker = NET_CUT_MARKER

    lines = [
        "#!/bin/sh",
        f"# {marker}",
        _NFT_FAILCLOSED_PREAMBLE.rstrip("\n"),
    ]
    if allow_ips:
        ports = [int(p) for p in allow_ports] or [443]
        for ip in allow_ips:
            for port in ports:
                # Host-scoped accept: pinned destination IP + port. NEVER any-host.
                lines.append(f"nft add rule inet lince_lab output ip daddr {ip} tcp dport {port} accept")
    return "\n".join(lines) + "\n"


def egress_lockdown_argv(allow_ips: list[str], allow_ports: list[int]) -> list[str]:
    """Build the ``backend.exec`` argv that applies the runtime egress lock-down.

    Returns ``['sudo', 'sh', '-c', egress_lockdown_script(allow_ips, allow_ports)]``
    so the broker / recipe runner / bisect builder can apply the lock-down through
    a single ``backend.exec(vm, egress_lockdown_argv(...))`` call. A nonzero exit
    means the VM could not enforce egress and the caller must fail the run.
    """
    return ["sudo", "sh", "-c", egress_lockdown_script(allow_ips, allow_ports)]


def build_template(config: dict[str, Any], recipe_needs: dict[str, Any]) -> str:
    """Build a policy-forced Lima template, returned as JSON text (valid YAML).

    The template boots a **normal networked VM** — there is NO egress boot
    provision. Provisioning (a trusted setup step) runs with network up; the
    egress lock-down is applied at runtime by the broker after provisioning and
    before the recipe steps (see :func:`egress_lockdown_argv`).

    ``recipe_needs`` keys (all optional except ``image``):

    * ``image``       — short name keyed into the config image allowlist.
    * ``cpus`` / ``memory`` / ``disk`` — resource caps (fall back to config).
    * ``provision``   — extra ``system`` / ``user`` provision scripts. These run
      with the network UP (they are the trusted toolchain installers).
    """
    image_name = recipe_needs.get("image")
    if not image_name:
        raise DataError("recipe needs must specify an 'image'")
    image = _resolve_image(config, str(image_name))

    provision: list[dict[str, str]] = []
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
    }
    # Only emit a provision key when the recipe carries provision scripts; a bare
    # template (e.g. a plain `vm up`) needs no provisioning at all.
    if provision:
        template["provision"] = provision
    # JSON with indentation is valid YAML and round-trips through any YAML parser.
    return json.dumps(template, indent=2, sort_keys=True) + "\n"
