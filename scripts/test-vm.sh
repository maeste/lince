#!/usr/bin/env bash
#
# test-vm.sh — Disposable GUI VM launcher for LINCE testing
#
# Downloads Fedora/Ubuntu desktop ISOs once, then creates throwaway VMs
# with GNOME desktop, virt-viewer window, and copy-on-write overlays.
# Delete the overlay = back to zero.
#
# Usage:
#   ./scripts/test-vm.sh fedora          # Launch a fresh Fedora 43 Workstation VM with GNOME
#   ./scripts/test-vm.sh ubuntu          # Launch a fresh Ubuntu 24.04 Desktop VM with GNOME
#   ./scripts/test-vm.sh list            # Show running test VMs
#   ./scripts/test-vm.sh destroy <name>  # Destroy a specific VM
#   ./scripts/test-vm.sh destroy-all     # Destroy all test VMs
#   ./scripts/test-vm.sh download        # Download ISOs only
#
# Prerequisites:
#   sudo dnf install qemu-kvm libvirt virt-install virt-viewer genisoimage
#   sudo systemctl enable --now libvirtd
#   sudo usermod -aG libvirt $USER  (then re-login)
#
# First run per distro:
#   1. Downloads the ISO (~2-6 GB)
#   2. Opens graphical installer — you install GNOME normally (~15 min)
#   3. Creates a base snapshot
#
# Subsequent runs:
#   1. Creates a COW overlay of the base (instant, few KB)
#   2. Opens virt-viewer with GNOME desktop
#   3. Destroy when done → back to zero
#

set -e

# ── Config ───────────────────────────────────────────────────────────
IMAGE_DIR="$HOME/.local/share/lince-test-vms"

FEDORA_ISO_URL="https://download.fedoraproject.org/pub/fedora/linux/releases/43/Workstation/x86_64/iso/Fedora-Workstation-Live-x86_64-43-1.1.iso"
FEDORA_ISO="$IMAGE_DIR/Fedora-Workstation-43.iso"
FEDORA_BASE="$IMAGE_DIR/fedora-43-desktop-base.qcow2"

UBUNTU_ISO_URL="https://releases.ubuntu.com/24.04.2/ubuntu-24.04.2-desktop-amd64.iso"
UBUNTU_ISO="$IMAGE_DIR/Ubuntu-24.04-Desktop.iso"
UBUNTU_BASE="$IMAGE_DIR/ubuntu-2404-desktop-base.qcow2"

VM_CPUS=4
VM_RAM=16384      # 16GB
VM_DISK=40        # GB

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

# ── Functions ────────────────────────────────────────────────────────
download_iso() {
    local distro="$1"
    mkdir -p "$IMAGE_DIR"
    case "$distro" in
        fedora)
            if [ ! -f "$FEDORA_ISO" ]; then
                echo -e "${CYAN}Downloading Fedora 43 Workstation ISO (~2.3 GB)...${NC}"
                curl -L -o "$FEDORA_ISO" "$FEDORA_ISO_URL"
                echo -e "${GREEN}✓ Downloaded${NC}"
            else
                echo -e "${GREEN}✓ Fedora ISO exists${NC}"
            fi ;;
        ubuntu)
            if [ ! -f "$UBUNTU_ISO" ]; then
                echo -e "${CYAN}Downloading Ubuntu 24.04 Desktop ISO (~5.8 GB)...${NC}"
                curl -L -o "$UBUNTU_ISO" "$UBUNTU_ISO_URL"
                echo -e "${GREEN}✓ Downloaded${NC}"
            else
                echo -e "${GREEN}✓ Ubuntu ISO exists${NC}"
            fi ;;
    esac
}

create_base_image() {
    local distro="$1"
    local base_image iso_path os_variant vm_name="lince-base-${distro}"

    case "$distro" in
        fedora) base_image="$FEDORA_BASE"; iso_path="$FEDORA_ISO"; os_variant="fedora-unknown" ;;
        ubuntu) base_image="$UBUNTU_BASE"; iso_path="$UBUNTU_ISO"; os_variant="ubuntu-unknown" ;;
    esac

    if [ -f "$base_image" ]; then
        echo -e "${GREEN}✓ Base image exists: $base_image${NC}"
        return 0
    fi

    download_iso "$distro"

    echo ""
    echo -e "${YELLOW}${BOLD}═══════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}${BOLD}  First-time setup: Installing $distro desktop${NC}"
    echo -e "${YELLOW}${BOLD}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  A graphical installer will open. Complete the installation."
    echo -e "  Create user: ${BOLD}tester${NC} / password: ${BOLD}tester${NC}"
    echo -e "  After reboot + login, ${BOLD}shut down the VM${NC} from GNOME menu."
    echo ""
    read -p "  Press ENTER to start the installer..."

    qemu-img create -f qcow2 "$base_image" "${VM_DISK}G" >/dev/null

    virt-install \
        --name "$vm_name" \
        --memory $VM_RAM \
        --vcpus $VM_CPUS \
        --disk "path=$base_image,format=qcow2" \
        --cdrom "$iso_path" \
        --os-variant "$os_variant" \
        --network default \
        --graphics spice,listen=none \
        --video qxl \
        --channel spicevmc \
        --boot cdrom,hd \
        --wait -1

    virsh undefine "$vm_name" 2>/dev/null || true

    echo -e "${GREEN}${BOLD}✓ Base image created: $base_image ($(du -h "$base_image" | cut -f1))${NC}"
}

launch_vm() {
    local distro="$1"
    local ts=$(date +%H%M%S)
    local vm_name="lince-test-${distro}-${ts}"
    local overlay="$IMAGE_DIR/${vm_name}.qcow2"
    local base_image os_variant

    case "$distro" in
        fedora) base_image="$FEDORA_BASE"; os_variant="fedora-unknown" ;;
        ubuntu) base_image="$UBUNTU_BASE"; os_variant="ubuntu-unknown" ;;
        *) echo -e "${RED}Use 'fedora' or 'ubuntu'.${NC}"; exit 1 ;;
    esac

    [ ! -f "$base_image" ] && create_base_image "$distro"

    echo -e "${CYAN}Creating overlay (base untouched)...${NC}"
    qemu-img create -f qcow2 -b "$base_image" -F qcow2 "$overlay" "${VM_DISK}G" >/dev/null

    echo -e "${CYAN}Launching ${distro} VM: ${vm_name}...${NC}"
    virt-install \
        --name "$vm_name" \
        --memory $VM_RAM \
        --vcpus $VM_CPUS \
        --disk "path=$overlay,format=qcow2" \
        --os-variant "$os_variant" \
        --network default \
        --graphics spice,listen=none \
        --video qxl \
        --channel spicevmc \
        --import \
        --noautoconsole

    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  VM: ${BOLD}${vm_name}${NC}"
    echo -e "${GREEN}║  Login: tester / tester${NC}"
    echo -e "${GREEN}║  Display: virt-viewer ${vm_name}${NC}"
    echo -e "${GREEN}║  Destroy: $0 destroy ${vm_name}${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""

    sleep 2
    virt-viewer "$vm_name" 2>/dev/null &
    disown
    echo -e "${GREEN}✓ virt-viewer opened.${NC}"
}

list_vms() {
    echo -e "${CYAN}LINCE test VMs:${NC}"
    local found=false
    for vm in $(virsh list --all --name 2>/dev/null | grep "^lince-test-"); do
        found=true
        local state=$(virsh domstate "$vm" 2>/dev/null)
        [ "$state" = "running" ] && echo -e "  ${GREEN}$vm${NC} ($state)" || echo -e "  ${YELLOW}$vm${NC} ($state)"
    done
    [ "$found" = false ] && echo "  No test VMs."
    echo ""
    echo -e "${CYAN}Base images:${NC}"
    [ -f "$FEDORA_BASE" ] && echo -e "  ${GREEN}✓${NC} Fedora: $(du -h "$FEDORA_BASE" | cut -f1)" || echo -e "  ${YELLOW}✗${NC} Fedora: not created"
    [ -f "$UBUNTU_BASE" ] && echo -e "  ${GREEN}✓${NC} Ubuntu: $(du -h "$UBUNTU_BASE" | cut -f1)" || echo -e "  ${YELLOW}✗${NC} Ubuntu: not created"
}

destroy_vm() {
    local vm="$1"
    [ -z "$vm" ] && { echo -e "${RED}Usage: $0 destroy <name>${NC}"; exit 1; }
    echo -e "${CYAN}Destroying ${vm}...${NC}"
    virsh destroy "$vm" 2>/dev/null || true
    virsh undefine "$vm" --remove-all-storage 2>/dev/null || true
    echo -e "${GREEN}✓ Destroyed${NC}"
}

destroy_all() {
    for vm in $(virsh list --all --name 2>/dev/null | grep "^lince-test-"); do
        destroy_vm "$vm"
    done
    echo -e "${GREEN}✓ All test VMs destroyed. Base images preserved.${NC}"
}

case "${1:-}" in
    fedora|ubuntu) launch_vm "$1" ;;
    download) download_iso fedora; download_iso ubuntu ;;
    list) list_vms ;;
    destroy) destroy_vm "$2" ;;
    destroy-all) destroy_all ;;
    *)
        echo "test-vm.sh — Disposable GUI VMs for LINCE testing"
        echo ""
        echo "  $0 fedora         Launch Fedora 43 GNOME VM"
        echo "  $0 ubuntu         Launch Ubuntu 24.04 GNOME VM"
        echo "  $0 list           Show VMs"
        echo "  $0 destroy <name> Destroy a VM"
        echo "  $0 destroy-all    Destroy all test VMs"
        echo "  $0 download       Download ISOs only"
        echo ""
        echo "Login: tester / tester | Images: $IMAGE_DIR"
        ;;
esac
