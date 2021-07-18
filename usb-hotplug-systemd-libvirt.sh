#!/bin/bash

# Libvirt & qemu don't automatically deal well with passing through hot plugged USB devices.
# VM won't start if the passed USB device is not plugged in.
# Device won't go to VM if it's plugged in after VM start.
#
# However we can programmatically add & remove devices,
# so this is hacking our own hotplugging in using udev/systemd hooks.


set -eEu -o pipefail
shopt -s failglob
trap 'echo >&2 "${BASH_SOURCE:-$0}:${LINENO}: unknown error"' ERR

CMD="$1"
VM_USB_ID="$2"
IFS='_:' read VM_NAME VENDOR_ID MODEL_ID <<< "$VM_USB_ID"

declare -A valid_cmds=(
  [attach-device]=1 [detach-device]=1
)
if [[ -z "${valid_cmds[$CMD]:-}" ]] ; then
    echo "ERROR: Invalid command $CMD"
    exit 2
fi

# FIXME: Add some checks for whether the VM even exists

virsh $CMD $VM_NAME --persistent /dev/stdin  << EOF
    <hostdev mode='subsystem' type='usb' managed='yes'>
        <source startupPolicy='optional'>
            <vendor id='0x${VENDOR_ID}' />
            <product id='0x${MODEL_ID}' />
        </source>
    </hostdev>
EOF


# NOTES
# =====
# udev rules file /etc/udev/rules.d/99-newhall-hotplug.rules:
#    # FIXME: Can I do this entirely in systemd?
#    SUBSYSTEM=="usb", ENV{PRODUCT}=="d8c/13c/*", SYMLINK+="Newhall_0d8c:013c" TAG+="systemd", ENV{SYSTEMD_WANTS}="usb-vm-hotplug@Newhall_0d8c:013c.service"
# systemd unit  usb-vm-hotplug@.service:
#    [Unit]
#    Description=Hotplug USB to libvirt VM
#    After=libvirtd.service
#    BindsTo=dev-%i.device
#    After=dev-%i.device
#    Requisite=dev-%i.device
#
#    [Service]
#    Type=oneshot
#    RemainAfterExit=yes
#    ExecStart=/home/mike/vcs/misc-scripts/usb-hotplug-systemd-libvirt.sh attach-device %I
#    ExecStop=/home/mike/vcs/misc-scripts/usb-hotplug-systemd-libvirt.sh detach-device %I
#
#    [Install]
#    WantedBy=dev-%i.device
