#!/usr/bin/env bash
#
# 09-packaging.sh — sub-issue #260 oracle (blueprint §11).
#
# Packaging + skill. SUBSTRATE-FREE: runs fully even without KVM and is
# deliberately NOT gated by skip_if_no_kvm. Installs the module into an isolated
# HOME, asserts `lince-lab --help` resolves on PATH and the skill landed, proves
# the install is idempotent (a second run is clean), then uninstalls and asserts
# every artifact is gone. This is the clean-clone third-party-installability gate.
#
# Exit 0 only on success → triggers 10-generic.sh.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00-lib.sh
source "$SCRIPT_DIR/00-lib.sh"

oracle_header "09 packaging (#260)"

# Locate the module root (where install.sh lives) from this script's position.
MODULE_DIR="$(cd "$SCRIPT_DIR/../../../lince-lab" && pwd)"
INSTALL_SH="$MODULE_DIR/install.sh"
UNINSTALL_SH="$MODULE_DIR/uninstall.sh"

assert_file "$INSTALL_SH" "install.sh present"
assert_file "$UNINSTALL_SH" "uninstall.sh present"

# Isolated HOME so the test never touches the real user's installed files. Every
# installed-layout path key in 00-lib.sh derives from $HOME / XDG_*, so pointing
# HOME (and XDG_CONFIG_HOME) at a scratch dir fully isolates the install.
FAKE_HOME="$(mktemp -d)"
cleanup() { rm -rf "$FAKE_HOME"; }
trap cleanup EXIT

export HOME="$FAKE_HOME"
export XDG_CONFIG_HOME="$FAKE_HOME/.config"
export PATH="$FAKE_HOME/.local/bin:$PATH"
# Re-derive the layout paths under the isolated HOME.
INST_BIN="$FAKE_HOME/.local/bin/lince-lab"
INST_SHARE="$FAKE_HOME/.local/share/lince/lince-lab"
INST_SKILL="$FAKE_HOME/.claude/skills/lince-lab"

log "install into the isolated HOME"
bash "$INSTALL_SH"

log "lince-lab resolves on PATH and --help works"
assert_file "$INST_BIN" "CLI installed to ~/.local/bin/lince-lab"
assert command -v lince-lab -- "lince-lab is on PATH"
assert_exit 0 "lince-lab --help -> 0" -- lince-lab --help
HELP="$(lince-lab --help)"
assert_contains "$HELP" "vm" "help lists the vm group"
assert_contains "$HELP" "run" "help lists the run group"

log "package data + skill landed"
assert_file "$INST_SHARE/lince_lab" "package installed to share"
assert_file "$INST_SKILL/SKILL.md" "skill installed to ~/.claude/skills/lince-lab"

log "install is idempotent (second run is clean)"
assert_exit 0 "re-run install.sh -> 0" -- bash "$INSTALL_SH"
assert_exit 0 "lince-lab --help still works after re-install" -- lince-lab --help

log "uninstall removes every artifact"
bash "$UNINSTALL_SH"
assert_no_file "$INST_BIN" "CLI removed"
assert_no_file "$INST_SHARE" "package data removed"
assert_no_file "$INST_SKILL" "skill removed"

ok "09 packaging oracle passed"
exit 0
