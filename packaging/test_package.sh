#!/bin/sh
# SPDX-License-Identifier: MIT
# Run only in a fresh disposable Ubuntu 26.04 amd64 container, never on the host.
set -eu
blocked() { echo "BLOCKED: $*" >&2; exit 2; }
[ "$#" = 4 ] || blocked "usage: test_package.sh OLD_BROKER.deb OLD_CLIENT.deb NEW_BROKER.deb NEW_CLIENT.deb"
[ "${XMQR_DISPOSABLE_PACKAGE_TEST:-}" = 1 ] || blocked "set XMQR_DISPOSABLE_PACKAGE_TEST=1 in a disposable container"
[ "$(id -u)" = 0 ] || blocked "root required inside the disposable container"
[ -f /.dockerenv ] || blocked "Docker container marker required; do not run on the host"
[ -f /etc/os-release ] || blocked "Ubuntu release metadata missing"
. /etc/os-release
[ "$ID" = ubuntu ] && [ "$VERSION_ID" = 26.04 ] || blocked "Ubuntu 26.04 required"
for command in dpkg dpkg-deb dpkg-query apt-get sha256sum getent stat mktemp cmp; do
    command -v "$command" >/dev/null || blocked "missing prerequisite: $command"
done
[ "$(dpkg --print-architecture)" = amd64 ] || blocked "native amd64 required"
old_broker=$1
old_client=$2
new_broker=$3
new_client=$4
check_deb() {
    case "$1" in /*) ;; *) blocked "package paths must be absolute: $1" ;; esac
    [ -f "$1" ] || blocked "package missing: $1"
    [ "$(dpkg-deb -f "$1" Package)" = "$2" ] || blocked "unexpected package name: $1"
    [ "$(dpkg-deb -f "$1" Architecture)" = amd64 ] || blocked "unexpected package architecture: $1"
}
check_deb "$old_broker" xmqr-broker
check_deb "$old_client" xmqr-client
check_deb "$new_broker" xmqr-broker
check_deb "$new_client" xmqr-client
old_broker_version=$(dpkg-deb -f "$old_broker" Version)
old_client_version=$(dpkg-deb -f "$old_client" Version)
new_broker_version=$(dpkg-deb -f "$new_broker" Version)
new_client_version=$(dpkg-deb -f "$new_client" Version)
dpkg --compare-versions "$new_broker_version" gt "$old_broker_version" || blocked "broker upgrade must increase Debian version"
dpkg --compare-versions "$new_client_version" gt "$old_client_version" || blocked "client upgrade must increase Debian version"
for package in xmqr-broker xmqr-client; do
    if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed'; then
        blocked "$package already installed; use a fresh container"
    fi
done
snapshot=$(mktemp)
package_extract=$(mktemp -d)
trap 'rm -f "$snapshot"; rm -rf "$package_extract"' EXIT HUP INT TERM
dpkg-deb --extract "$old_broker" "$package_extract/old"
dpkg-deb --extract "$new_broker" "$package_extract/new"
for file in broker.toml.example configuration.md; do
    [ -s "$package_extract/new/usr/share/doc/xmqr-broker/$file" ]
done
check_config_docs() {
    for file in broker.toml.example configuration.md; do
        expected="$package_extract/$1/usr/share/doc/xmqr-broker/$file"
        installed="/usr/share/doc/xmqr-broker/$file"
        if [ -f "$expected" ]; then
            cmp "$expected" "$installed"
        else
            [ ! -e "$installed" ]
        fi
    done
}
sha256sum "$old_broker" "$old_client" "$new_broker" "$new_client"
export DEBIAN_FRONTEND=noninteractive
# The minimal Ubuntu Docker image excludes documentation by default. Preserve
# only our package docs so installation/rollback can exercise the real files.
printf '%s\n' 'path-include=/usr/share/doc/xmqr-broker' 'path-include=/usr/share/doc/xmqr-broker/*' 'path-include=/usr/share/doc/xmqr-client' 'path-include=/usr/share/doc/xmqr-client/*' > /etc/dpkg/dpkg.cfg.d/zz-xmqr-test-docs
apt-get update -qq
apt-get install -y --no-install-recommends systemd "$old_broker" "$old_client"
check_versions() {
    [ "$(dpkg-query -W -f='${Version}' xmqr-broker)" = "$1" ]
    [ "$(dpkg-query -W -f='${Version}' xmqr-client)" = "$2" ]
    dpkg-query -W -f='${Package} ${Version} ${Status}\n' xmqr-broker xmqr-client
}
check_units() {
    systemd-analyze verify /usr/lib/systemd/system/xmqr-broker.service /usr/lib/systemd/system/xmqr-client-sub@.service /usr/lib/systemd/system/xmqr-client-pub@.service
    [ ! -e /etc/systemd/system/multi-user.target.wants/xmqr-broker.service ]
    [ "$(stat -c '%U:%G:%a' /var/lib/xmqr)" = xmqr:xmqr:700 ]
    getent passwd xmqr >/dev/null
    getent passwd xmqr-client >/dev/null
}
check_versions "$old_broker_version" "$old_client_version"
check_units
printf '# operator edit\n' >> /etc/xmqr/broker.env
printf 'test-state' > /var/lib/xmqr/operator-data
mkdir -p /etc/xmqr-client/test
printf 'test-secret' > /etc/xmqr-client/test/password
chmod 600 /etc/xmqr-client/test/password
sha256sum /etc/xmqr/broker.env /var/lib/xmqr/operator-data /etc/xmqr-client/test/password > "$snapshot"
check_preserved() {
    sha256sum --check "$snapshot"
    [ "$(stat -c '%a' /etc/xmqr-client/test/password)" = 600 ]
}
apt-get install -y -o Dpkg::Options::=--force-confold "$new_broker" "$new_client"
check_versions "$new_broker_version" "$new_client_version"
check_config_docs new
check_units
check_preserved
# Rollback tests the packages and operator files; real MQTT replay is a separate gate.
apt-get install -y --allow-downgrades -o Dpkg::Options::=--force-confold "$old_broker" "$old_client"
check_versions "$old_broker_version" "$old_client_version"
check_config_docs old
check_units
check_preserved
apt-get remove -y xmqr-broker xmqr-client
check_preserved
[ ! -e /usr/bin/mqtt-broker ]
[ ! -e /usr/bin/mqtt-admin ]
[ ! -e /usr/bin/mqtt-client ]
apt-get purge -y xmqr-broker xmqr-client
[ ! -f /etc/xmqr/broker.env ]
[ "$(cat /var/lib/xmqr/operator-data)" = test-state ]
[ "$(cat /etc/xmqr-client/test/password)" = test-secret ]
getent passwd xmqr >/dev/null
getent passwd xmqr-client >/dev/null
echo PACKAGE_LIFECYCLE_PASS
