"""Policy gate — the broker's single, client-untrusted enforcement point (blueprint §3).

Every dispatch in :mod:`lince_lab.broker` calls :func:`check` before touching the
backend or the recipe/bisect runners. The function is **pure**: given a verb, its
decoded args, and the broker's policy context it either returns a (possibly
rewritten) args dict that is safe to act on, or raises
:class:`~lince_lab.errors.PolicyDenied` (exit 13). No I/O, no sockets — so every
rule is exhaustively unit-testable with no VM.

Enforced points (blueprint §3, items 1–6):

1. **Server-side template forcing** — a ``vm.create`` template supplied by the
   client is *never* trusted. :func:`check` strips any client-provided
   ``template_yaml`` so the broker rebuilds it from the recipe's declared needs.
2. **Network deny-by-default** — ``recipe.run`` / ``bisect.run`` with a network
   mode other than ``deny`` is refused unless the recipe carries a non-empty
   ``allow_hosts`` / ``allow_ports`` allowlist.
3. **copy_in path bounding** — a ``vm.copy_in`` host path must resolve *under* a
   **server-trusted** workspace directory; ``..`` escapes, absolute-outside
   paths, and host secret directories (``~/.ssh``, ``~/.config/lince``,
   ``~/.aws``, ...) are refused. The workspace is never taken from the client: a
   bare ``vm.copy_in`` with no server-side recipe context is **denied**
   (fail-closed), and a workspace that is itself the filesystem root or a host
   secret location is rejected so a forged ``workspace_dir='/'`` cannot turn
   copy_in into ``/etc/shadow`` exfiltration.
4. **copy_out path bounding** — a ``vm.copy_out`` host *destination* must resolve
   under a **server-derived** artifacts root (never a client value); ``..``
   escapes, absolute-outside, and secret-location destinations are refused so the
   guest cannot be used to clobber arbitrary host files.
5. **Credential stripping** — ``vm.exec`` ``env`` keys matching the secret pattern
   (``*_TOKEN`` / ``*_KEY`` / ``*_DSN`` and a denylist incl. ``KUBECONFIG`` /
   ``DATABASE_URL`` / ``AWS_PROFILE`` / ``SSH_AUTH_SOCK`` / ``CLOUDSDK_*``) are
   removed before the command is forwarded; host credentials never enter the VM.
6. **Name-prefix guard** — every VM name the broker is asked to operate on must
   carry the ``lince-lab-`` prefix, so a user's pre-existing VMs are untouchable.

The capture-stream verbs (``capture.send`` / ``capture.snapshot``) are gated by
:func:`check_capture` so an upgraded capture connection cannot bypass the gate.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from lince_lab.errors import PolicyDenied

# VM_NAME_PREFIX and the path-bounding guard live once in lince_lab.paths;
# importing them here keeps ``from lince_lab.policy import VM_NAME_PREFIX`` working
# (blueprint §3.6) and lets the copy_in/out checks reuse the single guard.
from lince_lab.paths import VM_NAME_PREFIX, resolves_under

# ── server-derived artifacts root (blueprint §3.4) ───────────────────────────
# The ONLY host tree a vm.copy_out destination may land under. Server-chosen,
# never client-supplied; resolved under the caller's home.
ARTIFACTS_SUBPATH = ".local/share/lince/lince-lab/artifacts"

# ── host secret locations the broker must never stage / clobber (blueprint §3.3)
# Each is resolved against the caller's home; a copy_in source or copy_out
# destination that *is* one of these, or lives *under* it, is refused even if it
# would otherwise resolve under the workspace. Comparison is per path-segment
# (not string-prefix), so a sibling like ``~/.ssh-backup`` cannot escape the
# ``~/.ssh`` rule.
SECRET_DIR_NAMES: tuple[str, ...] = (
    ".ssh",
    ".aws",
    ".gnupg",
    ".kube",
    ".netrc",
    ".git-credentials",
)
# Secret subpaths under the config dir (kept separate so the check is explicit).
SECRET_CONFIG_SUBDIRS: tuple[str, ...] = (
    ".config/lince",
    ".config/gh",
    ".docker/config.json",
)
# Absolute secret locations independent of the caller's home.
SECRET_ABS_PATHS: tuple[str, ...] = (
    "/etc/ssh",
    "/etc/shadow",
    "/etc/gshadow",
)

# ── secret env key patterns (blueprint §3.5) ─────────────────────────────────
# Suffix patterns: any env key ending in one of these is stripped from vm.exec.
SECRET_ENV_SUFFIXES: tuple[str, ...] = (
    "_TOKEN",
    "_KEY",
    "_SECRET",
    "_PASSWORD",
    "_PASSWD",
    "_CREDENTIALS",
    "_DSN",
)
# Prefix patterns: any env key starting with one of these is stripped.
SECRET_ENV_PREFIXES: tuple[str, ...] = ("CLOUDSDK_",)
# Exact-match secret env keys (no recognizable suffix/prefix).
SECRET_ENV_NAMES: frozenset[str] = frozenset(
    {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "KUBECONFIG",
        "DATABASE_URL",
        "SSH_AUTH_SOCK",
    }
)

# Capture-stream verbs gated by :func:`check_capture`.
_CAPTURE_STREAM_VERBS: frozenset[str] = frozenset({"capture.send", "capture.snapshot"})

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
    if any(upper.startswith(prefix) for prefix in SECRET_ENV_PREFIXES):
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


def _is_secret_host_path(candidate: str, home: Path) -> bool:
    """Return ``True`` iff ``candidate`` is, or lives under, a host secret dir.

    Matching is per path-segment via :class:`~pathlib.Path` equality / ``parents``
    (never string-prefix), so a sibling such as ``~/.ssh-backup`` does **not**
    match the ``~/.ssh`` rule and is judged on its own merits.
    """
    resolved = Path(candidate).expanduser()
    resolved = resolved if resolved.is_absolute() else (home / resolved)
    resolved = resolved.resolve()
    home_resolved = home.resolve()
    secret_dirs = [home_resolved / name for name in SECRET_DIR_NAMES]
    secret_dirs += [home_resolved / sub for sub in SECRET_CONFIG_SUBDIRS]
    secret_dirs += [Path(abs_path) for abs_path in SECRET_ABS_PATHS]
    for secret in secret_dirs:
        if resolved == secret or secret in resolved.parents:
            return True
    return False


def artifacts_root(home: Path) -> Path:
    """Return the server-derived artifacts root (the only copy_out destination tree).

    Always under the caller's home — never a client value — so a guest can only
    write back into a fixed, lab-owned tree.
    """
    return (home / ARTIFACTS_SUBPATH).resolve()


def _is_unsafe_workspace(workspace: Path, home: Path) -> bool:
    """Return ``True`` iff ``workspace`` is too broad to be a legitimate workspace.

    A workspace that is the filesystem root, the caller's bare home, or that *is*
    (or lives under) a host secret location can never be a recipe-declared stage
    dir — trusting one would let a forged ``workspace_dir`` (e.g. ``/``) turn
    copy_in into arbitrary host-file exfiltration. Fail-closed: reject it.
    """
    resolved = workspace.resolve()
    if resolved == Path(resolved.anchor):  # filesystem root, e.g. "/"
        return True
    if resolved == home.resolve():  # the bare home dir spans every secret
        return True
    return _is_secret_host_path(str(resolved), home)


def _check_copy_in(args: dict[str, Any], recipe_ctx: dict[str, Any], home: Path) -> None:
    """Enforce blueprint §3.3: copy_in host path must stay under the workspace.

    The workspace directory is taken from ``recipe_ctx['workspace_dir']`` — a
    **server-trusted** fact (the broker derives it from a loaded recipe and never
    passes a client value). A bare ``vm.copy_in`` arrives with no recipe context
    and is denied. A workspace that is itself the filesystem root / bare home / a
    secret location is rejected, and any host path that escapes the workspace, is
    absolute-outside, or lands in a secret location is refused.
    """
    host_path = args.get("host_path")
    if not isinstance(host_path, str) or not host_path:
        raise PolicyDenied("vm.copy_in is missing a host_path")

    workspace = recipe_ctx.get("workspace_dir")
    if not workspace:
        raise PolicyDenied("vm.copy_in requires a server-side recipe workspace context; none was supplied")
    if _is_unsafe_workspace(Path(str(workspace)), home):
        raise PolicyDenied(f"refusing copy_in: workspace {workspace!r} is too broad / a secret location")

    if _is_secret_host_path(host_path, home):
        raise PolicyDenied(f"refusing to copy a host secret location: {host_path!r}")

    if not resolves_under(Path(str(workspace)), host_path):
        raise PolicyDenied(
            f"vm.copy_in host_path {host_path!r} does not resolve under the recipe workspace {workspace!r}"
        )


def _check_copy_out(args: dict[str, Any], recipe_ctx: dict[str, Any], home: Path) -> None:
    """Enforce blueprint §3.4: copy_out host destination must stay under artifacts.

    The destination tree is **server-derived**: by default the fixed lab
    artifacts root (:func:`artifacts_root`), or a recipe's own artifacts dir when
    the broker supplies one via ``recipe_ctx['artifacts_dir']`` (still never a
    client value). A destination that escapes it, is absolute-outside, or lands in
    a secret location is refused so a guest cannot clobber arbitrary host files.
    """
    host_path = args.get("host_path")
    if not isinstance(host_path, str) or not host_path:
        raise PolicyDenied("vm.copy_out is missing a host_path destination")

    declared = recipe_ctx.get("artifacts_dir")
    out_root = Path(str(declared)).expanduser().resolve() if declared else artifacts_root(home)

    if _is_secret_host_path(host_path, home):
        raise PolicyDenied(f"refusing to write a host secret location: {host_path!r}")

    if not resolves_under(out_root, host_path):
        raise PolicyDenied(
            f"vm.copy_out host_path {host_path!r} does not resolve under the artifacts root {str(out_root)!r}"
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

    # §3.4 — copy_out host destination must stay under the artifacts root.
    if verb == "vm.copy_out":
        _check_copy_out(safe_args, ctx, home_dir)

    # §3.2 — deny-by-default network; allow needs a non-empty allowlist.
    if verb in ("recipe.run", "bisect.run"):
        _check_network(safe_args, ctx)

    return safe_args


def check_capture(
    verb: str,
    args: dict[str, Any],
    *,
    home: Path | None = None,
) -> dict[str, Any]:
    """Gate a capture-stream verb (blueprint §3) before it drives the channel.

    The capture connection is upgraded to a line stream after ``capture.open``;
    every subsequent ``capture.send`` / ``capture.snapshot`` must still pass a
    policy check rather than reaching the live :class:`~lince_lab.capture.Capture`
    unmediated. The capture verbs carry no host path or VM name (the target was
    fixed and name-prefix-checked at ``capture.open`` time), so the gate's job is
    to refuse any verb that is *not* a recognized capture-stream verb — closing
    the bypass where an arbitrary verb could be smuggled onto the upgraded stream.

    Returns a safe copy of ``args``; raises :class:`PolicyDenied` (exit 13) for a
    non-capture verb on the stream.
    """
    _ = home  # reserved for symmetry with check(); capture verbs take no host path
    if verb not in _CAPTURE_STREAM_VERBS:
        raise PolicyDenied(f"verb {verb!r} is not permitted on a capture stream")
    return copy.deepcopy(args)
