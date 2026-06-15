"""Recipe schema, validation, and run-flow orchestration (blueprint §5).

A *recipe* is a TOML file describing a disposable-VM test: which image to boot,
what network posture to allow, the one host workspace to stage, the provision
scripts baked into a base snapshot, the ordered steps to drive (plain ``exec``
steps and ``ht``-driven ``capture`` steps), and the mandatory ``[assert]`` block
that decides pass/fail.

This module is pure logic over the :class:`~lince_lab.backend.Backend` seam, so
the whole validate + run flow is exercisable against ``FakeBackend`` with no VM.

Three public entry points:

* :func:`load_recipe` — parse a TOML file into a :class:`Recipe` (records the
  recipe's source directory so ``[workspace].host_dir`` can be path-bounded).
* :func:`validate` — enforce the schema invariants, raising
  :class:`~lince_lab.errors.DataError` (exit 65) on any violation.
* :func:`run_recipe` — execute the section-5 flow and return the result exit
  code (0 if every assertion passes, else the failing code).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lince_lab.backend import Backend
from lince_lab.capture import Capture, Grid
from lince_lab.errors import DataError
from lince_lab.templates import build_template

# Snapshot tag baked after provisioning so retries / bisect can reset cheaply.
BASE_SNAPSHOT_TAG = "base-clean"


@dataclass
class Recipe:
    """A parsed recipe.

    ``source_dir`` is the directory the recipe TOML lives in; relative paths in
    the recipe (notably ``[workspace].host_dir``) resolve under it and must not
    escape it. The remaining fields mirror the TOML tables verbatim so the run
    flow and validation read them directly.
    """

    name: str
    description: str
    version: str
    vm: dict[str, Any]
    network: dict[str, Any]
    workspace: dict[str, Any]
    assertions: dict[str, Any]
    provision: list[dict[str, Any]] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    sync: dict[str, Any] = field(default_factory=dict)
    source_dir: Path = field(default_factory=Path.cwd)

    def has_capture_step(self) -> bool:
        """Return ``True`` iff any step drives a terminal via ``capture``."""
        return any(bool(step.get("capture")) for step in self.steps)


def load_recipe(path: str | Path) -> Recipe:
    """Parse the recipe TOML at ``path`` into a :class:`Recipe`.

    Records ``source_dir`` = the recipe file's parent so ``[workspace].host_dir``
    can be resolved and path-bounded during :func:`validate`. A malformed TOML
    file raises :class:`~lince_lab.errors.DataError` (exit 65).
    """
    recipe_path = Path(path).expanduser()
    try:
        raw = recipe_path.read_bytes()
    except (FileNotFoundError, NotADirectoryError, IsADirectoryError, PermissionError) as exc:
        raise DataError(f"cannot read recipe {recipe_path}: {exc}") from exc
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise DataError(f"malformed recipe TOML {recipe_path}: {exc}") from exc

    recipe_block = data.get("recipe") or {}
    return Recipe(
        name=str(recipe_block.get("name", "")),
        description=str(recipe_block.get("description", "")),
        version=str(recipe_block.get("version", "")),
        vm=dict(data.get("vm") or {}),
        network=dict(data.get("network") or {}),
        workspace=dict(data.get("workspace") or {}),
        assertions=dict(data.get("assert") or {}),
        provision=list(data.get("provision") or []),
        steps=list(data.get("step") or []),
        sync=dict(data.get("sync") or {}),
        source_dir=recipe_path.resolve().parent,
    )


# ── assertion keys that count toward "≥1 assertion present" ──────────────────
_ASSERTION_KEYS = ("exit_code", "grid_contains", "grid_absent", "file_exists")


def validate(recipe: Recipe, config: dict[str, Any] | None = None) -> None:
    """Validate ``recipe`` against the schema; raise on any violation.

    Raises :class:`~lince_lab.errors.DataError` (exit 65) on:

    * a missing ``[recipe]`` / ``[vm]`` / ``[workspace]`` / ``[assert]`` table;
    * an ``[assert]`` table containing zero assertions;
    * any ``capture`` step lacking a ``[sync]`` section;
    * ``[network] mode = "allow"`` with an empty allowlist;
    * a ``[workspace].host_dir`` that does not resolve under the recipe dir;
    * an image not present in ``config``'s allowed image set (when ``config`` is
      supplied — image-allowlist validation is skipped if no config is given).
    """
    # ── required tables ──
    if not recipe.name:
        raise DataError("recipe is missing a [recipe] table with a name")
    if not recipe.vm:
        raise DataError("recipe is missing the required [vm] table")
    if not recipe.workspace:
        raise DataError("recipe is missing the required [workspace] table")
    if not recipe.assertions:
        raise DataError("recipe is missing the required [assert] table")

    # ── at least one assertion ──
    if not any(key in recipe.assertions for key in _ASSERTION_KEYS):
        raise DataError(f"[assert] must contain at least one assertion (one of: {', '.join(_ASSERTION_KEYS)})")

    # ── every capture step needs [sync] ──
    if recipe.has_capture_step() and not recipe.sync:
        raise DataError("a capture step requires a [sync] section, but none is present")

    # ── network allow requires a non-empty allowlist ──
    if recipe.network.get("mode") == "allow":
        allow_hosts = recipe.network.get("allow_hosts") or []
        allow_ports = recipe.network.get("allow_ports") or []
        if not allow_hosts and not allow_ports:
            raise DataError("[network] mode = 'allow' requires a non-empty allow_hosts/allow_ports allowlist")

    # ── workspace host_dir must resolve under the recipe dir ──
    host_dir = recipe.workspace.get("host_dir")
    if not host_dir:
        raise DataError("[workspace] is missing a host_dir")
    if not _resolves_under(recipe.source_dir, str(host_dir)):
        raise DataError(
            f"[workspace] host_dir {host_dir!r} does not resolve under the recipe directory {recipe.source_dir}"
        )

    # ── image must be in the config allowlist (when a config is provided) ──
    if config is not None:
        image_name = recipe.vm.get("image")
        if not image_name:
            raise DataError("[vm] is missing an image")
        images = config.get("images") or {}
        if image_name not in images:
            known = ", ".join(sorted(images)) or "(none)"
            raise DataError(f"image {image_name!r} is not in the config allowlist; allowed: {known}")


def _resolves_under(base: Path, candidate: str) -> bool:
    """Return ``True`` iff ``candidate`` (relative to ``base``) stays under ``base``.

    An absolute ``candidate`` outside ``base`` or a relative one that climbs out
    via ``..`` is rejected. This is the recipe-level guard mirrored by the broker
    copy-in policy; it never touches the filesystem (pure path math).
    """
    base_resolved = base.resolve()
    target = Path(candidate)
    combined = target if target.is_absolute() else base_resolved / target
    resolved = combined.resolve()
    if resolved == base_resolved:
        return True
    return base_resolved in resolved.parents


# ── run flow (blueprint §5) ──────────────────────────────────────────────────


def run_recipe(
    backend: Backend,
    recipe: Recipe,
    config: dict[str, Any],
    keep: bool = False,
) -> int:
    """Execute ``recipe`` against ``backend`` and return the result exit code.

    The section-5 flow:

    1. :func:`validate` (fail-fast).
    2. Build the policy-forced template, ``create`` + ``start`` the VM.
    3. Run ``[[provision]]`` then ``snapshot_create(BASE_SNAPSHOT_TAG)``.
    4. ``copy_in`` the workspace ``host_dir`` → ``guest_dir`` (policy-bounded).
    5. For each ``[[step]]``: a ``capture`` step opens a channel and, for each key
       batch, waits for the configured substring, waits for the grid to settle,
       then ``send_keys``; an ``exec`` step runs its argv capturing the exit code.
    6. Evaluate ``[assert]`` (exit_code match; ``grid_contains`` / ``grid_absent``
       against the final settled grid; ``file_exists`` via ``test -f``).
    7. Return 0 if every assertion passes, else the failing exit code. The VM is
       deleted unless ``keep`` is set.

    Returns the recipe exit code:

    * the last step's nonzero exit code if a step fails, otherwise
    * 0 if all assertions pass, otherwise
    * 65 (``DATA_ERROR``) for an assertion mismatch (grid / file / exit_code).
    """
    validate(recipe, config)

    vm_name = _vm_name(recipe)
    needs = recipe_needs(recipe)
    template_yaml = build_template(config, needs)

    backend.create(vm_name, template_yaml)
    backend.start(vm_name)
    try:
        # 3. provision → base snapshot.
        for entry in recipe.provision:
            script = entry.get("script")
            if not script:
                continue
            backend.exec(vm_name, ["sh", "-c", str(script)])
        backend.snapshot_create(vm_name, BASE_SNAPSHOT_TAG)

        # 4. stage the single workspace dir (policy-bounded host_dir).
        host_dir = str(recipe.workspace["host_dir"])
        guest_dir = str(recipe.workspace.get("guest_dir", "/work"))
        if not _resolves_under(recipe.source_dir, host_dir):
            raise DataError(f"workspace host_dir {host_dir!r} escapes the recipe directory; refusing copy_in")
        backend.copy_in(vm_name, host_dir, guest_dir, recursive=True)

        # 5-6. run the ordered steps + evaluate the assertions. Shared verbatim
        # with the bisect loop via run_steps_and_assert (single-sourced oracle).
        exit_code, _step_failed = run_steps_and_assert(backend, recipe, vm_name)
        return exit_code
    finally:
        if not keep:
            backend.delete(vm_name, force=True)


def run_steps_and_assert(backend: Backend, recipe: Recipe, vm_name: str) -> tuple[int, str | None]:
    """Run a recipe's ordered steps then evaluate its ``[assert]`` block.

    This is steps 5-6 of :func:`run_recipe`, factored out so the bisect loop can
    reuse the exact same oracle against a persistent, snapshot-reset VM (without
    the create / provision / delete lifecycle). Returns ``(exit_code, step_failed)``:

    * a failing exec step short-circuits to ``(its_code, step_name)``;
    * otherwise the assertions are evaluated — an ``exit_code`` mismatch yields
      ``(65, None)``; a ``grid_contains`` / ``grid_absent`` / ``file_exists``
      mismatch raises :class:`~lince_lab.errors.DataError` (exit 65), which
      :func:`run_recipe` propagates and the bisect verdict runner turns into a
      "bad" verdict.

    The VM lifecycle (create / provision / snapshot / delete) is the caller's concern.
    """
    last_exit = 0
    final_grid: Grid | None = None
    for step in recipe.steps:
        if step.get("capture"):
            final_grid = _run_capture_step(backend, vm_name, recipe, step)
        else:
            last_exit = _run_exec_step(backend, vm_name, step)
            if last_exit != 0:
                # A failing step is the oracle/bisect signal — stop and report.
                return last_exit, str(step.get("name", "?"))
    return _evaluate_assertions(backend, vm_name, recipe, last_exit, final_grid), None


def _vm_name(recipe: Recipe) -> str:
    """Build the policy-prefixed VM name for ``recipe`` (``lince-lab-<recipe>``)."""
    safe = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in recipe.name) or "recipe"
    return f"lince-lab-{safe}"


def recipe_needs(recipe: Recipe) -> dict[str, Any]:
    """Project a recipe into the ``recipe_needs`` dict :func:`build_template` wants."""
    needs: dict[str, Any] = {
        "image": recipe.vm.get("image"),
        "cpus": recipe.vm.get("cpus"),
        "memory": recipe.vm.get("memory"),
        "disk": recipe.vm.get("disk"),
        "provision": list(recipe.provision),
    }
    if recipe.network.get("mode") == "allow":
        needs["allow_hosts"] = list(recipe.network.get("allow_hosts") or [])
        needs["allow_ports"] = list(recipe.network.get("allow_ports") or [])
    return needs


def _run_exec_step(backend: Backend, vm_name: str, step: dict[str, Any]) -> int:
    """Run a plain exec step's argv in the guest, returning its exit code."""
    run = step.get("run")
    if not run:
        raise DataError(f"exec step {step.get('name', '?')!r} is missing a 'run' argv")
    result = backend.exec(vm_name, [str(arg) for arg in run])
    return result.exit_code


def _run_capture_step(
    backend: Backend,
    vm_name: str,
    recipe: Recipe,
    step: dict[str, Any],
) -> Grid:
    """Drive a capture step via ``ht`` and return the final settled grid.

    For each key in ``step['keys']`` the runner first waits for the matching
    ``[sync].wait_for`` substring (when one is configured for that index), then
    waits for the grid to settle within ``[sync].stable_ms``, then injects the
    key. The grid after the last settle is returned for assertion evaluation.
    """
    program = step.get("program")
    if not program:
        raise DataError(f"capture step {step.get('name', '?')!r} is missing a 'program'")
    cols, rows = _parse_size(str(step.get("size", "80x24")))

    sync = recipe.sync
    wait_for = list(sync.get("wait_for") or [])
    stable_ms = int(sync.get("stable_ms", 150))
    timeout_s = float(sync.get("timeout_s", 60))

    channel = backend.open_capture(vm_name, [str(arg) for arg in program], cols, rows)
    capture = Capture(channel, cols, rows)
    try:
        grid = capture.snapshot(timeout_s=timeout_s)
        for index, key in enumerate(step.get("keys") or []):
            if index < len(wait_for):
                grid = capture.wait_for_substring(str(wait_for[index]), timeout_s=timeout_s)
            grid = capture.wait_for_stable(stable_ms, timeout_s=timeout_s)
            capture.send_keys([str(key)])
        # Settle one final time so the grid reflects the last keypress's effect.
        grid = capture.wait_for_stable(stable_ms, timeout_s=timeout_s)
        return grid
    finally:
        capture.close()


def _parse_size(size: str) -> tuple[int, int]:
    """Parse a ``"<cols>x<rows>"`` grid size into an ``(cols, rows)`` tuple."""
    try:
        cols_s, rows_s = size.lower().split("x", 1)
        return int(cols_s), int(rows_s)
    except (ValueError, AttributeError) as exc:
        raise DataError(f"invalid capture size {size!r}; expected '<cols>x<rows>'") from exc


def _evaluate_assertions(
    backend: Backend,
    vm_name: str,
    recipe: Recipe,
    last_exit: int,
    final_grid: Grid | None,
) -> int:
    """Evaluate ``[assert]`` and return 0 on pass or the failing exit code.

    A grid / file / exit_code mismatch is a data failure → exit 65. The
    ``exit_code`` assertion compares against the last exec step's code.
    """
    assertions = recipe.assertions

    if "exit_code" in assertions:
        expected = int(assertions["exit_code"])
        if last_exit != expected:
            # The recipe expected a specific code and the run produced another.
            return last_exit if last_exit != 0 else DataError.exit_code

    grid_text = final_grid.text if final_grid is not None else ""

    for needle in assertions.get("grid_contains") or []:
        if str(needle) not in grid_text:
            raise DataError(f"assertion failed: grid_contains {needle!r} not found on screen")

    for needle in assertions.get("grid_absent") or []:
        if str(needle) in grid_text:
            raise DataError(f"assertion failed: grid_absent {needle!r} appeared on screen")

    for path in assertions.get("file_exists") or []:
        result = backend.exec(vm_name, ["test", "-f", str(path)])
        if result.exit_code != 0:
            raise DataError(f"assertion failed: file_exists {path!r} not present in guest")

    return 0
