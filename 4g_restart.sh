#!/bin/sh
qmi-network /dev/cdc-wdm0 start
udhcpc -q -f -i wwan0
cat <<EOF >/etc/resolv.conf
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF
