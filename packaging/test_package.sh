#!/bin/sh
# Run only inside a disposable Ubuntu26 container as root, never on production.
set -eu
test "$(id -u)" = 0
test -f /.dockerenv
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends systemd /work/xmqr/dist/*.deb /work/xmqr-client/dist/*.deb
mqtt-client --version
systemd-analyze verify /usr/lib/systemd/system/xmqr-broker.service /usr/lib/systemd/system/xmqr-client-sub@.service /usr/lib/systemd/system/xmqr-client-pub@.service
test ! -e /etc/systemd/system/multi-user.target.wants/xmqr-broker.service
printf '# operator edit\n' >> /etc/xmqr/broker.env
printf 'test-state' > /var/lib/xmqr/operator-data
mkdir -p /etc/xmqr-client/test
printf 'test-secret' > /etc/xmqr-client/test/password
apt-get install -y /work/xmqr/target/package-test/*.deb /work/xmqr-client/target/package-test/*.deb
test "$(tail -n 1 /etc/xmqr/broker.env)" = '# operator edit'
test -f /var/lib/xmqr/operator-data
apt-get remove -y xmqr-broker xmqr-client
test -f /etc/xmqr/broker.env
test -f /var/lib/xmqr/operator-data
test -f /etc/xmqr-client/test/password
apt-get purge -y xmqr-broker xmqr-client
test ! -f /etc/xmqr/broker.env
test -f /var/lib/xmqr/operator-data
test -f /etc/xmqr-client/test/password
echo PACKAGE_LIFECYCLE_PASS
