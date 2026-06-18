#!/usr/bin/env python3
"""Recipe schema + validate + run-flow tests (blueprint §5).

Validation cases assert each rule raises :class:`DataError` (exit 65). Run-flow
cases drive the section-5 orchestration against ``FakeBackend`` — scripting step
exec results with ``fake.on(...)`` and capture steps with an answering channel
over a fake monotonic clock — so the whole flow runs with no VM and no real
sleeping.

Covered:

* every validation rule → correct raise / exit code;
* run-flow step ordering (provision → snapshot → copy_in → steps → assert);
* assert-pass and assert-fail paths (exit_code, grid_contains, grid_absent);
* copy_in path-bounds rejection (host_dir escaping the recipe dir);
* file_exists assertion evaluated via the backend ``test -f`` builtin.

Run with:
    python3 lince-lab/tests/test_recipe.py
"""

import pathlib
import sys
import tempfile
import unittest

# Put the package dir (lince-lab/) on sys.path so absolute imports resolve.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from lince_lab import capture as capture_mod  # noqa: E402
from lince_lab import recipe as recipe_mod  # noqa: E402
from lince_lab.backend import CaptureChannel, ExecResult  # noqa: E402
from lince_lab.errors import DATA_ERROR, DataError  # noqa: E402
from lince_lab.fake_backend import FakeBackend  # noqa: E402
from lince_lab.recipe import (  # noqa: E402
    BASE_SNAPSHOT_TAG,
    Recipe,
    load_recipe,
    run_recipe,
    validate,
)
from lince_lab.templates import egress_lockdown_argv  # noqa: E402


def _register_lockdown(backend: FakeBackend, vm_name: str, allow_ips=None, allow_ports=None) -> None:
    """Register the runtime egress lock-down exec to succeed on the Fake.

    FakeBackend.exec returns 127 for an unregistered argv, which would make the
    lock-down (applied after provision, before the steps/snapshot) fail and abort
    the run. Real run-flow tests register it to return 0 so the lock-down is a
    no-op success and the rest of the flow proceeds.
    """
    backend.on(vm_name, egress_lockdown_argv(allow_ips or [], allow_ports or []), ExecResult(0, "", ""))

# A minimal config with an image allowlist that recipes may reference.
CONFIG = {
    "vm": {"cpus": 2, "memory": "2GiB", "disk": "20GiB"},
    "images": {
        "fedora": {"location": "https://example/Fedora.qcow2", "arch": "x86_64", "digest": ""},
    },
}


def make_recipe(source_dir: pathlib.Path, **overrides) -> Recipe:
    """Build a valid baseline :class:`Recipe`; ``overrides`` replace fields."""
    base = {
        "name": "demo",
        "description": "demo recipe",
        "version": "1",
        "vm": {"image": "fedora", "cpus": 2, "memory": "2GiB", "disk": "20GiB"},
        "network": {"mode": "deny", "allow_hosts": [], "allow_ports": []},
        "workspace": {"host_dir": ".", "guest_dir": "/work"},
        "assertions": {"exit_code": 0},
        "provision": [],
        "steps": [],
        "sync": {},
        "source_dir": source_dir,
    }
    base.update(overrides)
    return Recipe(**base)


# ── a clock + answering capture channel for capture-step tests ───────────────


class FakeClock:
    """A monotonic clock advanced explicitly by the answering channel."""

    def __init__(self) -> None:
        self.t = 1000.0

    def monotonic(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


class AnsweringChannel(CaptureChannel):
    """Answers ``takeSnapshot`` from a current text; silent otherwise.

    On a ``takeSnapshot`` command the next ``read_line`` returns a ``snapshot``
    event carrying ``text``. When no answer is pending, ``read_line`` advances
    the clock to the deadline (event silence) and returns ``None`` — exactly the
    condition ``wait_for_stable`` settles on. ``text`` may be updated to model the
    screen changing between key batches.
    """

    def __init__(self, clock: FakeClock, text: str = "") -> None:
        self._clock = clock
        self.text = text
        self._pending: list[dict] = []
        self.sent: list[dict] = []
        self.closed = False

    def send_line(self, obj: dict) -> None:
        self.sent.append(dict(obj))
        if obj.get("type") == "takeSnapshot":
            self._pending.append({"type": "snapshot", "data": {"cols": 80, "rows": 24, "text": self.text}})

    def read_line(self, deadline: float):
        if self._pending:
            return self._pending.pop(0)
        if self._clock.monotonic() < deadline:
            self._clock.t = deadline
        return None

    def close(self) -> None:
        self.closed = True


class ValidateTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _assert_data_error(self, recipe: Recipe) -> None:
        with self.assertRaises(DataError) as ctx:
            validate(recipe, CONFIG)
        self.assertEqual(ctx.exception.exit_code, DATA_ERROR)

    def test_valid_recipe_passes(self) -> None:
        validate(make_recipe(self.dir), CONFIG)  # no raise

    def test_missing_recipe_table(self) -> None:
        self._assert_data_error(make_recipe(self.dir, name=""))

    def test_missing_vm_table(self) -> None:
        self._assert_data_error(make_recipe(self.dir, vm={}))

    def test_missing_workspace_table(self) -> None:
        self._assert_data_error(make_recipe(self.dir, workspace={}))

    def test_missing_assert_table(self) -> None:
        self._assert_data_error(make_recipe(self.dir, assertions={}))

    def test_assert_with_zero_assertions(self) -> None:
        # An [assert] table that carries no recognized assertion key is invalid.
        self._assert_data_error(make_recipe(self.dir, assertions={"comment": "noop"}))

    def test_capture_step_without_sync(self) -> None:
        recipe = make_recipe(
            self.dir,
            steps=[{"name": "drive", "capture": True, "program": ["app"], "keys": ["Enter"]}],
            sync={},
        )
        self._assert_data_error(recipe)

    def test_capture_step_with_sync_ok(self) -> None:
        recipe = make_recipe(
            self.dir,
            steps=[{"name": "drive", "capture": True, "program": ["app"], "keys": ["Enter"]}],
            sync={"wait_for": ["Ready"], "stable_ms": 100, "timeout_s": 5},
        )
        validate(recipe, CONFIG)  # no raise

    def test_network_allow_with_empty_allowlist(self) -> None:
        recipe = make_recipe(self.dir, network={"mode": "allow", "allow_hosts": [], "allow_ports": []})
        self._assert_data_error(recipe)

    def test_network_allow_with_allowlist_ok(self) -> None:
        recipe = make_recipe(
            self.dir,
            network={"mode": "allow", "allow_hosts": ["registry.npmjs.org"], "allow_ports": [443]},
        )
        validate(recipe, CONFIG)  # no raise

    def test_host_dir_escaping_recipe_dir(self) -> None:
        recipe = make_recipe(self.dir, workspace={"host_dir": "../escape", "guest_dir": "/work"})
        self._assert_data_error(recipe)

    def test_host_dir_absolute_outside_rejected(self) -> None:
        recipe = make_recipe(self.dir, workspace={"host_dir": "/etc", "guest_dir": "/work"})
        self._assert_data_error(recipe)

    def test_host_dir_subdir_ok(self) -> None:
        recipe = make_recipe(self.dir, workspace={"host_dir": "./fixtures/clone", "guest_dir": "/work"})
        validate(recipe, CONFIG)  # subdir under the recipe dir is allowed

    def test_image_not_in_allowlist(self) -> None:
        recipe = make_recipe(self.dir, vm={"image": "no-such-image", "cpus": 1})
        self._assert_data_error(recipe)

    def test_image_check_skipped_without_config(self) -> None:
        # With no config the image allowlist cannot be checked; validation passes.
        recipe = make_recipe(self.dir, vm={"image": "anything", "cpus": 1})
        validate(recipe, config=None)  # no raise


class LoadRecipeTest(unittest.TestCase):
    def test_load_records_source_dir_and_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "r.toml"
            path.write_text(
                "[recipe]\nname='x'\ndescription='d'\nversion='1'\n"
                "[vm]\nimage='fedora'\ncpus=2\n"
                "[network]\nmode='deny'\n"
                "[workspace]\nhost_dir='.'\nguest_dir='/work'\n"
                "[[provision]]\nmode='system'\nscript='echo hi'\n"
                "[[step]]\nname='s1'\nrun=['true']\n"
                "[assert]\nexit_code=0\n",
                encoding="utf-8",
            )
            recipe = load_recipe(path)
            self.assertEqual(recipe.name, "x")
            self.assertEqual(recipe.vm["image"], "fedora")
            self.assertEqual(recipe.source_dir, path.resolve().parent)
            self.assertEqual(len(recipe.provision), 1)
            self.assertEqual(recipe.steps[0]["run"], ["true"])
            self.assertFalse(recipe.has_capture_step())

    def test_load_missing_file_raises_data_error(self) -> None:
        with self.assertRaises(DataError):
            load_recipe(pathlib.Path("/nonexistent/recipe.toml"))

    def test_load_malformed_toml_raises_data_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "bad.toml"
            path.write_text("this = = not toml ][", encoding="utf-8")
            with self.assertRaises(DataError):
                load_recipe(path)


class RunFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)
        self.backend = FakeBackend()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_run_flow_order_and_pass(self) -> None:
        # Track the sequence of backend operations to assert ordering.
        calls: list[str] = []
        orig_exec = self.backend.exec
        orig_snap = self.backend.snapshot_create
        orig_copy = self.backend.copy_in

        lockdown_argv = egress_lockdown_argv([], [])

        def rec_exec(name, argv, **kw):
            tag = "lockdown" if list(argv) == lockdown_argv else " ".join(argv)
            calls.append(f"exec:{tag}")
            return orig_exec(name, argv, **kw)

        def rec_snap(name, tag):
            calls.append(f"snapshot:{tag}")
            return orig_snap(name, tag)

        def rec_copy(name, host, guest, recursive=False):
            calls.append(f"copy_in:{host}->{guest}")
            return orig_copy(name, host, guest, recursive)

        self.backend.exec = rec_exec  # type: ignore[method-assign]
        self.backend.snapshot_create = rec_snap  # type: ignore[method-assign]
        self.backend.copy_in = rec_copy  # type: ignore[method-assign]

        recipe = make_recipe(
            self.dir,
            provision=[{"mode": "system", "script": "install deps"}],
            steps=[{"name": "run-test", "run": ["make", "test"]}],
            assertions={"exit_code": 0},
        )
        vm_name = recipe_mod._vm_name(recipe)
        self.backend.on(vm_name, ["sh", "-c", "install deps"], ExecResult(0, "", ""))
        self.backend.on(vm_name, ["make", "test"], ExecResult(0, "passed", ""))
        _register_lockdown(self.backend, vm_name)

        rc = run_recipe(self.backend, recipe, CONFIG, keep=True)
        self.assertEqual(rc, 0)

        # Ordering: provision exec → egress lock-down → base snapshot → copy_in →
        # step exec. The lock-down runs with network up (after provision) and
        # before the first step + the base snapshot, so the steps and every reset
        # candidate run restricted.
        i_prov = calls.index("exec:sh -c install deps")
        i_lock = calls.index("exec:lockdown")
        i_snap = calls.index(f"snapshot:{BASE_SNAPSHOT_TAG}")
        i_copy = next(i for i, c in enumerate(calls) if c.startswith("copy_in:"))
        i_step = calls.index("exec:make test")
        self.assertLess(i_prov, i_lock)
        self.assertLess(i_lock, i_snap)
        self.assertLess(i_snap, i_copy)
        self.assertLess(i_copy, i_step)
        self.assertLess(i_lock, i_step)

    def test_run_flow_deletes_vm_when_not_kept(self) -> None:
        recipe = make_recipe(
            self.dir,
            steps=[{"name": "ok", "run": ["true"]}],
            assertions={"exit_code": 0},
        )
        vm_name = recipe_mod._vm_name(recipe)
        self.backend.on(vm_name, ["true"], ExecResult(0, "", ""))
        _register_lockdown(self.backend, vm_name)
        rc = run_recipe(self.backend, recipe, CONFIG, keep=False)
        self.assertEqual(rc, 0)
        # The VM is gone after a non-kept run.
        from lince_lab.backend import VmStatus

        self.assertEqual(self.backend.status(vm_name).status, VmStatus.ABSENT)

    def test_failing_step_returns_its_exit_code(self) -> None:
        recipe = make_recipe(
            self.dir,
            steps=[{"name": "boom", "run": ["make", "test"]}],
            assertions={"exit_code": 0},
        )
        vm_name = recipe_mod._vm_name(recipe)
        self.backend.on(vm_name, ["make", "test"], ExecResult(7, "", "fail"))
        _register_lockdown(self.backend, vm_name)
        rc = run_recipe(self.backend, recipe, CONFIG, keep=True)
        self.assertEqual(rc, 7)

    def test_exit_code_assert_mismatch_is_data_error(self) -> None:
        # Step succeeds (exit 0) but the recipe asserts a nonzero code → 65.
        recipe = make_recipe(
            self.dir,
            steps=[{"name": "ok", "run": ["true"]}],
            assertions={"exit_code": 3},
        )
        vm_name = recipe_mod._vm_name(recipe)
        self.backend.on(vm_name, ["true"], ExecResult(0, "", ""))
        _register_lockdown(self.backend, vm_name)
        rc = run_recipe(self.backend, recipe, CONFIG, keep=True)
        self.assertEqual(rc, DATA_ERROR)

    def test_file_exists_assertion_pass(self) -> None:
        # A step "installs" a file; the file_exists assertion then finds it.
        def installer(fs, argv):
            fs["/work/.config/lince/lince.toml"] = b"written"
            return ExecResult(0, "", "")

        recipe = make_recipe(
            self.dir,
            steps=[{"name": "install", "run": ["./install.sh"]}],
            assertions={"exit_code": 0, "file_exists": ["/work/.config/lince/lince.toml"]},
        )
        vm_name = recipe_mod._vm_name(recipe)
        self.backend.on(vm_name, ["./install.sh"], installer)
        _register_lockdown(self.backend, vm_name)
        rc = run_recipe(self.backend, recipe, CONFIG, keep=True)
        self.assertEqual(rc, 0)

    def test_file_exists_assertion_fail(self) -> None:
        recipe = make_recipe(
            self.dir,
            steps=[{"name": "noop", "run": ["true"]}],
            assertions={"exit_code": 0, "file_exists": ["/work/never-created"]},
        )
        vm_name = recipe_mod._vm_name(recipe)
        self.backend.on(vm_name, ["true"], ExecResult(0, "", ""))
        _register_lockdown(self.backend, vm_name)
        with self.assertRaises(DataError):
            run_recipe(self.backend, recipe, CONFIG, keep=True)

    def test_copy_in_path_bounds_rejected_at_runtime(self) -> None:
        # A recipe whose host_dir escapes the recipe dir is refused before copy_in.
        # validate() also catches this; here we bypass validate by asserting on a
        # workspace whose host_dir is valid for validate but the run guard still
        # re-checks — use an absolute escaping path which both layers reject.
        recipe = make_recipe(
            self.dir,
            workspace={"host_dir": "/etc/passwd", "guest_dir": "/work"},
            steps=[{"name": "noop", "run": ["true"]}],
            assertions={"exit_code": 0},
        )
        with self.assertRaises(DataError):
            run_recipe(self.backend, recipe, CONFIG, keep=True)

    def test_lockdown_failure_fails_the_run_before_steps(self) -> None:
        # If the egress lock-down exec returns nonzero, the run must fail (a VM
        # that can't enforce egress must not run the steps) and the step must
        # never execute.
        from lince_lab.errors import BackendError

        step_ran = {"v": False}

        def step_handler(fs, argv):
            step_ran["v"] = True
            return ExecResult(0, "", "")

        recipe = make_recipe(
            self.dir,
            provision=[{"mode": "system", "script": "install deps"}],
            steps=[{"name": "run-test", "run": ["make", "test"]}],
            assertions={"exit_code": 0},
        )
        vm_name = recipe_mod._vm_name(recipe)
        self.backend.on(vm_name, ["sh", "-c", "install deps"], ExecResult(0, "", ""))
        self.backend.on(vm_name, ["make", "test"], step_handler)
        # Lock-down exec fails (nonzero) — left unregistered so the Fake returns 127.
        with self.assertRaises(BackendError):
            run_recipe(self.backend, recipe, CONFIG, keep=True)
        self.assertFalse(step_ran["v"], "the step must not run when the lock-down failed")

    def test_allow_recipe_locks_down_with_resolved_ips(self) -> None:
        # An allow recipe resolves its hosts host-side and applies a host-scoped
        # lock-down (ip daddr accept rules), not the deny drop-only one.
        recipe = make_recipe(
            self.dir,
            network={"mode": "allow", "allow_hosts": ["registry.npmjs.org"], "allow_ports": [443]},
            steps=[{"name": "fetch", "run": ["npm", "install"]}],
            assertions={"exit_code": 0},
        )
        vm_name = recipe_mod._vm_name(recipe)
        self.backend.on(vm_name, ["npm", "install"], ExecResult(0, "", ""))
        # Resolve deterministically (no real DNS) and register the resulting
        # allow-posture lock-down argv to succeed. apply_egress_lockdown resolves
        # the host→IP MAP once (feeding both the nft rules and the /etc/hosts pin),
        # so patch that single source.
        orig = recipe_mod.resolve_allow_map
        recipe_mod.resolve_allow_map = lambda hosts: {"registry.npmjs.org": ["104.16.11.34"]} if hosts else {}
        try:
            _register_lockdown(self.backend, vm_name, allow_ips=["104.16.11.34"], allow_ports=[443])
            rc = run_recipe(self.backend, recipe, CONFIG, keep=True)
        finally:
            recipe_mod.resolve_allow_map = orig
        self.assertEqual(rc, 0)

    def test_pin_guest_etc_hosts_appends_resolved_ip(self) -> None:
        # The /etc/hosts pin makes the guest connect to exactly the allow-listed
        # IP without DNS. Capture the issued exec and assert its content.
        self.backend.create("pinvm", "")
        seen: list[list[str]] = []

        def capture(_fs: dict, argv: list[str]) -> ExecResult:
            seen.append(list(argv))
            return ExecResult(0, "", "")

        self.backend.on("pinvm", None, capture)
        recipe_mod._pin_guest_etc_hosts(self.backend, "pinvm", {"registry.npmjs.org": ["104.16.11.34", "1.2.3.4"]})
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][:2], ["sh", "-c"])
        script = seen[0][-1]
        # Pins the FIRST resolved IP (also nft-allowed) and writes /etc/hosts.
        self.assertIn("104.16.11.34 registry.npmjs.org", script)
        self.assertIn("/etc/hosts", script)
        self.assertNotIn("1.2.3.4", script)  # only the first IP is pinned

    def test_grid_contains_and_absent_pass(self) -> None:
        clock = FakeClock()
        orig_monotonic = capture_mod.time.monotonic
        capture_mod.time.monotonic = clock.monotonic
        try:
            channel = AnsweringChannel(clock, text="Configuration written\nenabled_agents")
            recipe = make_recipe(
                self.dir,
                steps=[
                    {
                        "name": "drive",
                        "capture": True,
                        "program": ["lince-config", "quickstart"],
                        "size": "80x24",
                        "keys": ["Enter"],
                    }
                ],
                sync={"wait_for": ["Configuration written"], "stable_ms": 50, "timeout_s": 5},
                assertions={
                    "grid_contains": ["Configuration written", "enabled_agents"],
                    "grid_absent": ["Traceback"],
                },
            )
            vm_name = recipe_mod._vm_name(recipe)
            self.backend.script_capture(vm_name, channel)
            _register_lockdown(self.backend, vm_name)
            rc = run_recipe(self.backend, recipe, CONFIG, keep=True)
            self.assertEqual(rc, 0)
            # The Enter key was injected through the capture channel.
            self.assertIn({"type": "sendKeys", "keys": ["Enter"]}, channel.sent)
        finally:
            capture_mod.time.monotonic = orig_monotonic

    def test_grid_absent_violation_fails(self) -> None:
        clock = FakeClock()
        orig_monotonic = capture_mod.time.monotonic
        capture_mod.time.monotonic = clock.monotonic
        try:
            channel = AnsweringChannel(clock, text="Traceback (most recent call last)")
            recipe = make_recipe(
                self.dir,
                steps=[
                    {
                        "name": "drive",
                        "capture": True,
                        "program": ["app"],
                        "size": "80x24",
                        "keys": [],
                    }
                ],
                sync={"wait_for": [], "stable_ms": 50, "timeout_s": 5},
                assertions={"grid_absent": ["Traceback"]},
            )
            vm_name = recipe_mod._vm_name(recipe)
            self.backend.script_capture(vm_name, channel)
            _register_lockdown(self.backend, vm_name)
            with self.assertRaises(DataError):
                run_recipe(self.backend, recipe, CONFIG, keep=True)
        finally:
            capture_mod.time.monotonic = orig_monotonic


class PresetWiringTest(unittest.TestCase):
    """The preset-tunable knobs (step_timeout_s, retain_base_snapshot) are consumed.

    Wired in stage 4: the effective config (a preset overlaid on the base config)
    flows into run_recipe and changes observable run behavior.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)
        self.backend = FakeBackend()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _recipe(self) -> Recipe:
        recipe = make_recipe(
            self.dir,
            steps=[{"name": "ok", "run": ["true"]}],
            assertions={"exit_code": 0},
        )
        vm_name = recipe_mod._vm_name(recipe)
        self.backend.on(vm_name, ["true"], ExecResult(0, "", ""))
        _register_lockdown(self.backend, vm_name)
        return recipe

    def test_step_timeout_s_reaches_exec(self) -> None:
        # The effective config's step_timeout_s is passed through to backend.exec.
        seen: list[float | None] = []
        orig_exec = self.backend.exec

        def rec_exec(name, argv, workdir=None, env=None, timeout=None):
            seen.append(timeout)
            return orig_exec(name, argv, workdir=workdir, env=env, timeout=timeout)

        self.backend.exec = rec_exec  # type: ignore[method-assign]
        recipe = self._recipe()
        cfg = dict(CONFIG, step_timeout_s=600)
        rc = run_recipe(self.backend, recipe, cfg, keep=True)
        self.assertEqual(rc, 0)
        # The step exec saw the 600s timeout (default behavior would be None).
        self.assertIn(600.0, seen)

    def test_retain_base_snapshot_keeps_snapshot(self) -> None:
        # With retain_base_snapshot the base-clean snapshot survives the run; the
        # default drops it. This proves the preset knob changes effective behavior.
        recipe = self._recipe()
        vm_name = recipe_mod._vm_name(recipe)

        run_recipe(self.backend, recipe, dict(CONFIG, retain_base_snapshot=True), keep=True)
        self.assertIn(BASE_SNAPSHOT_TAG, self.backend.snapshot_list(vm_name))

    def test_default_drops_base_snapshot(self) -> None:
        recipe = self._recipe()
        vm_name = recipe_mod._vm_name(recipe)
        run_recipe(self.backend, recipe, CONFIG, keep=True)
        self.assertNotIn(BASE_SNAPSHOT_TAG, self.backend.snapshot_list(vm_name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
