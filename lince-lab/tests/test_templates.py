#!/usr/bin/env python3
"""Template + runtime egress lock-down tests (blueprint §3, §5; STAGE 2).

Two surfaces:

* :func:`build_template` boots a **normal networked VM** — it carries the forced
  isolation invariants (``plain`` / ``mounts: []`` / ssh keys off) and the image
  + resources, but NO egress boot provision. Egress is restricted at runtime, not
  at boot, so provisioning can install tooling with the network up.
* :func:`resolve_allow_ips` resolves ``allow_hosts`` to IPs host-side (fail-closed
  on unresolvable hosts, de-duplicating), and the runtime
  :func:`egress_lockdown_script` carries the fail-closed nft logic: a default-DROP
  output chain keeping loopback + established/related (Lima SSH), with host-scoped
  ``ip daddr <ip> ... dport <port> accept`` rules for resolved allow IPs and NO
  any-host accept. Empty allow IPs ⇒ drop-only deny.

All DNS is mocked — no real ``getaddrinfo`` is ever called.

Run with:
    python3 lince-lab/tests/test_templates.py
"""

import json
import pathlib
import sys
import unittest
from unittest import mock

# Put the package dir (lince-lab/) on sys.path so absolute imports resolve.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from lince_lab import templates as templates_mod  # noqa: E402
from lince_lab.templates import (  # noqa: E402
    NET_ALLOW_MARKER,
    NET_CUT_MARKER,
    build_template,
    egress_lockdown_argv,
    egress_lockdown_script,
    resolve_allow_ips,
)


def _fake_getaddrinfo(mapping: dict[str, list[str]]):
    """A ``socket.getaddrinfo`` stand-in resolving only ``mapping`` hosts.

    A host present in ``mapping`` returns its listed IPs as getaddrinfo tuples;
    anything else raises ``OSError`` (models NXDOMAIN). No real DNS is touched.
    """

    def _resolver(host, *_args, **_kwargs):
        ips = mapping.get(host)
        if not ips:
            raise OSError(f"name resolution failed for {host!r}")
        return [(2, 1, 6, "", (ip, 0)) for ip in ips]

    return _resolver


def _config() -> dict:
    return {
        "vm": {"cpus": 2, "memory": "2GiB", "disk": "20GiB"},
        "images": {
            "fedora": {
                "location": "https://example/Fedora-Cloud.qcow2",
                "arch": "x86_64",
                "digest": "sha256:deadbeef",
            }
        },
    }


class ResolveAllowIpsTestCase(unittest.TestCase):
    def test_resolves_and_dedups(self) -> None:
        resolver = _fake_getaddrinfo({"a.example": ["1.1.1.1", "1.1.1.1", "2.2.2.2"]})
        with mock.patch.object(templates_mod.socket, "getaddrinfo", resolver):
            ips = resolve_allow_ips(["a.example"])
        # First-seen order preserved, duplicates collapsed.
        self.assertEqual(ips, ["1.1.1.1", "2.2.2.2"])

    def test_unresolvable_host_is_omitted(self) -> None:
        resolver = _fake_getaddrinfo({"good.example": ["3.3.3.3"]})
        with mock.patch.object(templates_mod.socket, "getaddrinfo", resolver):
            ips = resolve_allow_ips(["bad.invalid", "good.example"])
        # The unresolvable host is dropped (fail-closed), the good one kept.
        self.assertEqual(ips, ["3.3.3.3"])

    def test_all_unresolvable_yields_empty(self) -> None:
        resolver = _fake_getaddrinfo({})
        with mock.patch.object(templates_mod.socket, "getaddrinfo", resolver):
            self.assertEqual(resolve_allow_ips(["x.invalid", "y.invalid"]), [])

    def test_blank_hosts_skipped(self) -> None:
        resolver = _fake_getaddrinfo({"h.example": ["4.4.4.4"]})
        with mock.patch.object(templates_mod.socket, "getaddrinfo", resolver):
            self.assertEqual(resolve_allow_ips(["", "  ", "h.example"]), ["4.4.4.4"])


class TemplateBootsNetworkedTestCase(unittest.TestCase):
    """build_template boots a normal networked VM — no egress boot provision."""

    def test_isolation_invariants_and_image_present(self) -> None:
        tmpl = json.loads(build_template(_config(), {"image": "fedora"}))
        # Forced isolation invariants survive.
        self.assertIs(tmpl["plain"], True)
        self.assertEqual(tmpl["mounts"], [])
        self.assertIs(tmpl["ssh"]["loadDotSSHPubKeys"], False)
        self.assertIs(tmpl["ssh"]["forwardAgent"], False)
        # Image entry + resources are present.
        self.assertEqual(tmpl["images"][0]["location"], "https://example/Fedora-Cloud.qcow2")
        self.assertEqual(tmpl["images"][0]["digest"], "sha256:deadbeef")
        self.assertEqual(tmpl["cpus"], 2)
        self.assertEqual(tmpl["memory"], "2GiB")
        self.assertEqual(tmpl["disk"], "20GiB")

    def test_no_boot_egress_provision(self) -> None:
        tmpl = json.loads(build_template(_config(), {"image": "fedora"}))
        # No provision at all for a needs dict with no provision scripts...
        provisions = tmpl.get("provision", [])
        # ...and certainly no boot-mode egress provision.
        self.assertEqual([p for p in provisions if p.get("mode") == "boot"], [])
        # The egress markers / nft logic are NOT baked into any template text.
        text = build_template(_config(), {"image": "fedora"})
        self.assertNotIn(NET_CUT_MARKER, text)
        self.assertNotIn(NET_ALLOW_MARKER, text)
        self.assertNotIn("policy drop", text)
        self.assertNotIn("nft add table", text)

    def test_allow_hosts_do_not_add_boot_provision(self) -> None:
        # Even an allow recipe's needs do not bake egress into the template now;
        # the lock-down is applied at runtime, so getaddrinfo must not be called.
        needs = {"image": "fedora", "allow_hosts": ["registry.npmjs.org"], "allow_ports": [443]}
        boom = mock.Mock(side_effect=AssertionError("build_template must not resolve DNS"))
        with mock.patch.object(templates_mod.socket, "getaddrinfo", boom):
            tmpl = json.loads(build_template(_config(), needs))
        self.assertEqual([p for p in tmpl.get("provision", []) if p.get("mode") == "boot"], [])
        boom.assert_not_called()

    def test_extra_provision_scripts_are_emitted(self) -> None:
        needs = {
            "image": "fedora",
            "provision": [{"mode": "system", "script": "dnf install -y nodejs"}],
        }
        tmpl = json.loads(build_template(_config(), needs))
        scripts = [p["script"] for p in tmpl["provision"]]
        self.assertIn("dnf install -y nodejs", scripts)
        # The provision is system-mode trusted setup, never boot egress.
        self.assertEqual([p for p in tmpl["provision"] if p.get("mode") == "boot"], [])


class EgressLockdownDenyTestCase(unittest.TestCase):
    """The deny (drop-only) runtime lock-down."""

    def test_deny_is_failclosed_default_drop(self) -> None:
        script = egress_lockdown_script([], [])
        self.assertIn(NET_CUT_MARKER, script)
        self.assertNotIn(NET_ALLOW_MARKER, script)
        # Fail-closed default-DROP egress policy under set -e.
        self.assertIn("policy drop", script)
        self.assertIn("set -e", script)
        # nft is installed-or-abort (fail-closed), not best-effort `|| true`.
        self.assertIn("aborting lock-down", script)
        # CRITICAL: established/related + the default-gateway daddr are kept so
        # Lima's management SSH survives (the gateway rule is conntrack-independent).
        self.assertIn("ct state established,related accept", script)
        self.assertIn("oif lo accept", script)
        self.assertIn('ip daddr "$LL_GW" accept', script)
        # NO host-scoped/any-host EGRESS allow: the only daddr rule is the gateway
        # control-plane exception above; there is no port-scoped accept.
        self.assertNotIn("tcp dport", script)

    def test_argv_wraps_script_in_sudo_sh_c(self) -> None:
        argv = egress_lockdown_argv([], [])
        self.assertEqual(argv[:3], ["sudo", "sh", "-c"])
        self.assertEqual(argv[3], egress_lockdown_script([], []))


class EgressLockdownAllowTestCase(unittest.TestCase):
    """The allow runtime lock-down with host-scoped accept rules."""

    def test_resolved_ip_emits_host_scoped_accept(self) -> None:
        script = egress_lockdown_script(["104.16.11.34"], [443])
        self.assertIn(NET_ALLOW_MARKER, script)
        self.assertNotIn(NET_CUT_MARKER, script)
        # Host-scoped accept rule: pinned destination IP + port.
        self.assertIn("ip daddr 104.16.11.34 tcp dport 443 accept", script)
        # Underlying default-DROP policy remains (allowlist is additive to drop).
        self.assertIn("policy drop", script)
        # established/related still kept (Lima SSH).
        self.assertIn("ct state established,related accept", script)
        # NO bare any-host `output tcp dport <p> accept` rule.
        self.assertNotIn("output tcp dport 443 accept", script)

    def test_multiple_ips_and_ports_cross_product(self) -> None:
        script = egress_lockdown_script(["1.0.0.1", "2.0.0.2"], [443, 80])
        for ip in ("1.0.0.1", "2.0.0.2"):
            for port in (443, 80):
                self.assertIn(f"ip daddr {ip} tcp dport {port} accept", script)
        self.assertNotIn("output tcp dport 443 accept", script)
        self.assertNotIn("output tcp dport 80 accept", script)

    def test_allow_ips_without_ports_default_to_443(self) -> None:
        script = egress_lockdown_script(["9.9.9.9"], [])
        self.assertIn("ip daddr 9.9.9.9 tcp dport 443 accept", script)

    def test_empty_allow_ips_is_drop_only(self) -> None:
        # Empty allow_ips ⇒ deny (drop-only), never any accept rule — even if ports
        # were given. This is the unresolvable/empty fail-closed posture.
        script = egress_lockdown_script([], [443])
        self.assertIn(NET_CUT_MARKER, script)
        self.assertNotIn(NET_ALLOW_MARKER, script)
        # No port-scoped/external-host egress allow; the only daddr rule is the
        # gateway control-plane exception that keeps Lima SSH alive.
        self.assertNotIn("tcp dport", script)
        self.assertNotIn("203.", script)  # no resolved external IP leaked in
        self.assertIn('ip daddr "$LL_GW" accept', script)
        self.assertIn("policy drop", script)


if __name__ == "__main__":
    unittest.main(verbosity=2)
