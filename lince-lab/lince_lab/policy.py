"""Policy gate — the broker's single, client-untrusted enforcement point (blueprint §3).

Every dispatch in :mod:`lince_lab.broker` calls :func:`check` before touching the
backend or the recipe/bisect runners. The function is **pure**: given a verb, its
decoded args, and the broker's policy context it either returns a (possibly
rewritten) args dict that is safe to act on, or raises
:class:`~lince_lab.errors.PolicyDenied` (exit 13). No I/O, no sockets — so every
rule is exhaustively unit-testable with no VM.

Enforced points (blueprint §3, items 1–5):

1. **Server-side template forcing** — a ``vm.create`` template supplied by the
   client is *never* trusted. :func:`check` strips any client-provided
   ``template_yaml`` so the broker rebuilds it from the recipe's declared needs.
2. **Network deny-by-default** — ``recipe.run`` / ``bisect.run`` with a network
   mode other than ``deny`` is refused unless the recipe carries a non-empty
   ``allow_hosts`` / ``allow_ports`` allowlist.
3. **copy_in path bounding** — a ``vm.copy_in`` host path must resolve *under* the
   recipe's declared workspace directory; ``..`` escapes, absolute-outside paths,
   and host secret directories (``~/.ssh``, ``~/.config/lince``, ``~/.aws``) are
   refused.
4. **Credential stripping** — ``vm.exec`` ``env`` keys matching the secret pattern
   (``*_TOKEN`` / ``*_KEY`` and a small denylist) are removed before the command
   is forwarded; host credentials never enter the VM.
5. **Name-prefix guard** — every VM name the broker is asked to operate on must
   carry the ``lince-lab-`` prefix, so a user's pre-existing VMs are untouchable.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from lince_lab.errors import PolicyDenied

# ── VM name namespace (blueprint §3.5) ───────────────────────────────────────
# Every VM the broker may touch must carry this prefix; anything else is a user
# instance the broker must never operate on.
VM_NAME_PREFIX = "lince-lab-"

# ── host secret locations the broker must never stage (blueprint §3.3) ───────
# Resolved against the caller's home; a copy_in source under any of these (or an
# exact match) is refused even if it would otherwise resolve under the workspace.
SECRET_DIR_NAMES: tuple[str, ...] = (
    ".ssh",
    ".aws",
    ".gnupg",
)
# Secret subpaths under the config dir (kept separate so the check is explicit).
SECRET_CONFIG_SUBDIRS: tuple[str, ...] = (
    ".config/lince",
    ".config/gh",
)

# ── secret env key patterns (blueprint §3.4) ─────────────────────────────────
# Suffix patterns: any env key ending in one of these is stripped from vm.exec.
SECRET_ENV_SUFFIXES: tuple[str, ...] = (
    "_TOKEN",
    "_KEY",
    "_SECRET",
    "_PASSWORD",
    "_PASSWD",
    "_CREDENTIALS",
)
# Exact-match secret env keys (no recognizable suffix).
SECRET_ENV_NAMES: frozenset[str] = frozenset(
    {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
    }
)

# Verbs that name a VM the broker acts on; all require the name-prefix guard.
_VM_NAMED_VERBS: frozenset[str] = frozenset(
    {
        "vm.create",
        "vm.start",
        "vm.stop",
        "vm.delete",
        "vm.status",
        "vm.exec",
        "vm.copy_in",
        "vm.copy_out",
        "snap.create",
        "snap.apply",
        "snap.delete",
        "snap.list",
        "capture.open",
        "capture.snapshot",
    }
)


def is_secret_env_key(key: str) -> bool:
    """Return ``True`` iff ``key`` names a credential that must never reach the VM."""
    upper = key.upper()
    if upper in SECRET_ENV_NAMES:
        return True
    return any(upper.endswith(suffix) for suffix in SECRET_ENV_SUFFIXES)


def strip_secret_env(env: dict[str, str]) -> dict[str, str]:
    """Return a copy of ``env`` with every secret-pattern key removed."""
    return {k: v for k, v in env.items() if not is_secret_env_key(k)}


def _require_vm_name_prefix(args: dict[str, Any]) -> None:
    """Raise :class:`PolicyDenied` unless ``args['name']`` carries the lab prefix."""
    name = args.get("name")
    if not isinstance(name, str) or not name:
        raise PolicyDenied("request is missing a VM name")
    if not name.startswith(VM_NAME_PREFIX):
        raise PolicyDenied(f"refusing to operate on VM {name!r}: lab VMs must be prefixed {VM_NAME_PREFIX!r}")


def _resolves_under(base: Path, candidate: str) -> bool:
    """Return ``True`` iff ``candidate`` (relative to ``base``) stays under ``base``.

    Pure path math — never touches the filesystem. An absolute ``candidate``
    outside ``base`` or a relative one that climbs out via ``..`` is rejected.
    Mirrors the recipe-level guard so the broker enforces the same bound on the
    wire that validation enforces in the recipe.
    """
    base_resolved = base.resolve()
    target = Path(candidate).expanduser()
    combined = target if target.is_absolute() else base_resolved / target
    resolved = combined.resolve()
    if resolved == base_resolved:
        return True
    return base_resolved in resolved.parents


def _is_secret_host_path(candidate: str, home: Path) -> bool:
    """Return ``True`` iff ``candidate`` is, or lives under, a host secret dir."""
    resolved = Path(candidate).expanduser()
    resolved = resolved if resolved.is_absolute() else (home / resolved)
    resolved = resolved.resolve()
    home_resolved = home.resolve()
    secret_dirs = [home_resolved / name for name in SECRET_DIR_NAMES]
    secret_dirs += [home_resolved / sub for sub in SECRET_CONFIG_SUBDIRS]
    for secret in secret_dirs:
        if resolved == secret or secret in resolved.parents:
            return True
    return False


def _check_copy_in(args: dict[str, Any], recipe_ctx: dict[str, Any], home: Path) -> None:
    """Enforce blueprint §3.3: copy_in host path must stay under the workspace.

    The workspace directory is taken from ``recipe_ctx['workspace_dir']`` (the one
    host dir the recipe declared it may stage). A host path that escapes it, is
    absolute-outside, or lands in a secret location is refused.
    """
    host_path = args.get("host_path")
    if not isinstance(host_path, str) or not host_path:
        raise PolicyDenied("vm.copy_in is missing a host_path")

    if _is_secret_host_path(host_path, home):
        raise PolicyDenied(f"refusing to copy a host secret location: {host_path!r}")

    workspace = recipe_ctx.get("workspace_dir")
    if not workspace:
        raise PolicyDenied("vm.copy_in requires a recipe workspace context; none was supplied")
    if not _resolves_under(Path(str(workspace)), host_path):
        raise PolicyDenied(
            f"vm.copy_in host_path {host_path!r} does not resolve under the recipe workspace {workspace!r}"
        )


def _check_network(args: dict[str, Any], recipe_ctx: dict[str, Any]) -> None:
    """Enforce blueprint §3.2: a non-deny network mode needs a non-empty allowlist.

    The network posture is read from the recipe context (server-side trusted)
    when present, else from the request args. ``mode`` defaults to ``deny``; any
    other value requires at least one ``allow_hosts`` or ``allow_ports`` entry.
    """
    network = recipe_ctx.get("network")
    if not isinstance(network, dict):
        network = args.get("network") if isinstance(args.get("network"), dict) else {}
    mode = str(network.get("mode", "deny"))
    if mode == "deny":
        return
    allow_hosts = network.get("allow_hosts") or []
    allow_ports = network.get("allow_ports") or []
    if not allow_hosts and not allow_ports:
        raise PolicyDenied(f"network mode {mode!r} requires a non-empty allow_hosts/allow_ports allowlist")


def check(
    verb: str,
    args: dict[str, Any],
    recipe_ctx: dict[str, Any] | None = None,
    *,
    home: Path | None = None,
) -> dict[str, Any]:
    """Enforce every section-3 policy point and return safe-to-act-on args.

    The returned dict is a *copy* of ``args`` with policy rewrites applied:

    * ``vm.create`` — any client ``template_yaml`` is dropped (the broker rebuilds
      it server-side; never trust the client's template);
    * ``vm.exec`` — secret-pattern ``env`` keys are stripped.

    ``recipe_ctx`` carries the broker-side trusted recipe facts a verb needs
    (``workspace_dir`` for copy_in bounding, ``network`` for the allowlist gate).
    ``home`` defaults to the real home and is overridable for tests.

    Raises :class:`~lince_lab.errors.PolicyDenied` (exit 13) on any violation.
    """
    ctx = dict(recipe_ctx or {})
    home_dir = home if home is not None else Path.home()
    safe_args = copy.deepcopy(args)

    # §3.5 — name-prefix guard for every verb that names a VM.
    if verb in _VM_NAMED_VERBS:
        _require_vm_name_prefix(safe_args)

    # §3.1 — server-side template forcing: drop any client-supplied template.
    if verb == "vm.create":
        safe_args.pop("template_yaml", None)

    # §3.4 — credential stripping on exec.
    if verb == "vm.exec":
        env = safe_args.get("env")
        if isinstance(env, dict):
            safe_args["env"] = strip_secret_env(env)

    # §3.3 — copy_in host path must stay under the recipe workspace.
    if verb == "vm.copy_in":
        _check_copy_in(safe_args, ctx, home_dir)

    # §3.2 — deny-by-default network; allow needs a non-empty allowlist.
    if verb in ("recipe.run", "bisect.run"):
        _check_network(safe_args, ctx)

    return safe_args
