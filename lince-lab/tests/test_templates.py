#!/usr/bin/env python3
"""Template network-isolation tests (blueprint §3, §5; STAGE 2).

Focused coverage of the host-scoped, fail-closed egress posture baked into the
Lima boot provision:

* :func:`resolve_allow_ips` resolves ``allow_hosts`` to IPs host-side, dropping
  unresolvable hosts (fail-closed, never any-host) and de-duplicating;
* the deny-by-default template carries a default-DROP egress policy, detects the
  default-route interface dynamically (no hardcoded ``eth0``), and has no
  any-host accept rule;
* an allow template with a resolvable host emits ``ip daddr <ip> ... dport
  <port> accept`` under the default DROP and NO bare any-host ``dport <p>
  accept`` rule;
* an unresolvable allow host yields the drop-only cut posture (fail-closed).

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


def _boot_script(text: str) -> str:
    tmpl = json.loads(text)
    boot = [p for p in tmpl["provision"] if p["mode"] == "boot"]
    assert len(boot) == 1
    return boot[0]["script"]


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


class DenyTemplateTestCase(unittest.TestCase):
    def test_deny_template_is_failclosed_default_drop(self) -> None:
        script = _boot_script(build_template(_config(), {"image": "fedora"}))
        self.assertIn(NET_CUT_MARKER, script)
        self.assertNotIn(NET_ALLOW_MARKER, script)
        # Fail-closed default-DROP egress policy.
        self.assertIn("policy drop", script)
        # set -e is on and the critical drop is NOT swallowed by `|| true`.
        self.assertIn("set -e", script)
        self.assertNotIn("policy drop ; }' 2>/dev/null || true", script)
        # No hardcoded NIC-down; interface is detected dynamically instead.
        self.assertNotIn("ip link set", script)
        self.assertNotIn("eth0 down", script)
        self.assertIn("ip route show default", script)
        # nft is installed-or-abort (fail-closed), not best-effort `|| true`.
        self.assertIn("aborting boot", script)
        # NO any-host accept rule of any kind.
        self.assertNotIn("tcp dport", script)
        self.assertNotIn("ip daddr", script)


class AllowTemplateTestCase(unittest.TestCase):
    def test_resolvable_host_emits_host_scoped_accept(self) -> None:
        needs = {"image": "fedora", "allow_hosts": ["registry.npmjs.org"], "allow_ports": [443]}
        resolver = _fake_getaddrinfo({"registry.npmjs.org": ["104.16.11.34"]})
        with mock.patch.object(templates_mod.socket, "getaddrinfo", resolver):
            script = _boot_script(build_template(_config(), needs))
        self.assertIn(NET_ALLOW_MARKER, script)
        self.assertNotIn(NET_CUT_MARKER, script)
        # Host-scoped accept rule: pinned destination IP + port.
        self.assertIn("ip daddr 104.16.11.34 tcp dport 443 accept", script)
        # Underlying default-DROP policy remains (allowlist is additive to drop).
        self.assertIn("policy drop", script)
        # NO bare any-host `output tcp dport <p> accept` rule.
        self.assertNotIn("output tcp dport 443 accept", script)
        self.assertNotIn("ip link set", script)

    def test_multiple_hosts_and_ports_cross_product(self) -> None:
        needs = {
            "image": "fedora",
            "allow_hosts": ["a.example", "b.example"],
            "allow_ports": [443, 80],
        }
        resolver = _fake_getaddrinfo({"a.example": ["1.0.0.1"], "b.example": ["2.0.0.2"]})
        with mock.patch.object(templates_mod.socket, "getaddrinfo", resolver):
            script = _boot_script(build_template(_config(), needs))
        for ip in ("1.0.0.1", "2.0.0.2"):
            for port in (443, 80):
                self.assertIn(f"ip daddr {ip} tcp dport {port} accept", script)
        self.assertNotIn("output tcp dport 443 accept", script)
        self.assertNotIn("output tcp dport 80 accept", script)

    def test_unresolvable_allow_host_falls_back_to_cut(self) -> None:
        needs = {"image": "fedora", "allow_hosts": ["nope.invalid"], "allow_ports": [443]}
        resolver = _fake_getaddrinfo({})  # nothing resolves
        with mock.patch.object(templates_mod.socket, "getaddrinfo", resolver):
            script = _boot_script(build_template(_config(), needs))
        # Fail-closed: the drop-only cut, never any-host.
        self.assertIn(NET_CUT_MARKER, script)
        self.assertNotIn(NET_ALLOW_MARKER, script)
        self.assertNotIn("ip daddr", script)
        self.assertNotIn("tcp dport", script)
        self.assertIn("policy drop", script)

    def test_pre_resolved_allow_ips_used_without_dns(self) -> None:
        # When the broker has already resolved (allow_ips), build_template must NOT
        # call getaddrinfo again.
        needs = {"image": "fedora", "allow_ips": ["9.9.9.9"], "allow_ports": [443]}
        boom = mock.Mock(side_effect=AssertionError("getaddrinfo must not be called"))
        with mock.patch.object(templates_mod.socket, "getaddrinfo", boom):
            script = _boot_script(build_template(_config(), needs))
        self.assertIn(NET_ALLOW_MARKER, script)
        self.assertIn("ip daddr 9.9.9.9 tcp dport 443 accept", script)
        boom.assert_not_called()

    def test_empty_pre_resolved_allow_ips_falls_back_to_cut(self) -> None:
        needs = {"image": "fedora", "allow_ips": [], "allow_ports": [443]}
        with mock.patch.object(templates_mod.socket, "getaddrinfo", _fake_getaddrinfo({})):
            script = _boot_script(build_template(_config(), needs))
        self.assertIn(NET_CUT_MARKER, script)
        self.assertNotIn("ip daddr", script)


if __name__ == "__main__":
    unittest.main(verbosity=2)
