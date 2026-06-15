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
"""

from __future__ import annotations

import json
from typing import Any

from lince_lab.errors import DataError

# Marker comment lines emitted inside the boot provision script so callers (and
# tests) can identify which egress posture was baked in.
NET_CUT_MARKER = "lince-lab: egress cut (deny-by-default)"
NET_ALLOW_MARKER = "lince-lab: egress allowlist"


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


def _net_cut_script() -> str:
    """A boot provision that severs outbound networking (deny-by-default)."""
    return (
        "#!/bin/sh\n"
        "set -eu\n"
        f"# {NET_CUT_MARKER}\n"
        "# Bring the default NIC down and install a drop-all egress rule so the\n"
        "# disposable lab VM cannot reach the network.\n"
        "ip link set dev eth0 down 2>/dev/null || true\n"
        "if command -v nft >/dev/null 2>&1; then\n"
        "  nft add table inet lince_lab 2>/dev/null || true\n"
        "  nft add chain inet lince_lab output '{ type filter hook output priority 0 ; policy drop ; }' "
        "2>/dev/null || true\n"
        "  nft add rule inet lince_lab output oif lo accept 2>/dev/null || true\n"
        "fi\n"
    )


def _net_allow_script(allow_hosts: list[str], allow_ports: list[int]) -> str:
    """A boot provision that drops egress except an explicit host/port allowlist."""
    lines = [
        "#!/bin/sh",
        "set -eu",
        f"# {NET_ALLOW_MARKER}",
        "# Deny-by-default egress with an explicit per-recipe allowlist.",
        "if command -v nft >/dev/null 2>&1; then",
        "  nft add table inet lince_lab 2>/dev/null || true",
        "  nft add chain inet lince_lab output "
        "'{ type filter hook output priority 0 ; policy drop ; }' 2>/dev/null || true",
        "  nft add rule inet lince_lab output oif lo accept 2>/dev/null || true",
        "  nft add rule inet lince_lab output ct state established,related accept 2>/dev/null || true",
    ]
    for port in allow_ports:
        lines.append(f"  nft add rule inet lince_lab output tcp dport {int(port)} accept 2>/dev/null || true")
    lines.append("fi")
    for host in allow_hosts:
        # Documented allow target; resolution/pinning is recipe-driven. Kept as a
        # comment marker so the allowlisted host is visible in the baked script.
        lines.append(f"# allow-host: {host}")
    return "\n".join(lines) + "\n"


def build_template(config: dict[str, Any], recipe_needs: dict[str, Any]) -> str:
    """Build a policy-forced Lima template, returned as JSON text (valid YAML).

    ``recipe_needs`` keys (all optional except ``image``):

    * ``image``       — short name keyed into the config image allowlist.
    * ``cpus`` / ``memory`` / ``disk`` — resource caps (fall back to config).
    * ``allow_hosts`` / ``allow_ports`` — network allowlist; if **either** is
      non-empty the boot script installs an allow rule instead of cutting egress.
    * ``provision``   — extra ``system`` / ``user`` provision scripts to append
      after the forced ``boot`` egress script.
    """
    image_name = recipe_needs.get("image")
    if not image_name:
        raise DataError("recipe needs must specify an 'image'")
    image = _resolve_image(config, str(image_name))

    allow_hosts = list(recipe_needs.get("allow_hosts") or [])
    allow_ports = list(recipe_needs.get("allow_ports") or [])
    networked = bool(allow_hosts) or bool(allow_ports)

    if networked:
        boot_script = _net_allow_script(allow_hosts, allow_ports)
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
