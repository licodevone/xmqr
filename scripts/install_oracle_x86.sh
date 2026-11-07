#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# P260: explicit operator execution only; new Ubuntu 26.04 amd64 host.
set -Eeuo pipefail
umask 077
INSTALLER_VERSION='0.1.0-rc.1'
if [[ ${1:-} == --version && $# == 1 ]]; then
    printf 'XMQR Oracle Installer %s\n' "$INSTALLER_VERSION"
    exit 0
fi

if [[ ${1:-} == --plan ]]; then
    printf '%s\n' 'New Ubuntu 26.04 amd64 only. Installs pinned official packages,' \
        'private mTLS credentials, broker, local observer and a test subscriber.' \
        'Checks hashes, readiness, QoS1, retained restart and authentication.' \
        'Does not modify SSH, firewall, OCI rules or billing.'
    exit 0
fi

die() { printf 'ERRO: %s\n' "$*" >&2; exit 1; }
resume_packages=false
resume_mqtt=false
if [[ ${1:-} == --resume-packages ]]; then
    resume_packages=true
    shift
elif [[ ${1:-} == --resume-mqtt ]]; then
    resume_mqtt=true
    shift
fi
[[ $EUID == 0 ]] || die 'Execute com sudo bash install_oracle_x86.sh IP_PUBLICO'
[[ $# == 1 ]] || die 'Informe somente o IPv4 publico da instancia.'
public_ip=$1
[[ -f /etc/os-release ]] || die 'Sistema operacional nao identificado.'
# shellcheck source=/dev/null
source /etc/os-release
[[ ${ID:-} == ubuntu && ${VERSION_ID:-} == 26.04 ]] || die 'Requer Ubuntu 26.04.'
[[ $(dpkg --print-architecture) == amd64 && $(uname -m) == x86_64 ]] || die 'Requer amd64/x86_64; ARM recusado.'
[[ -d /run/systemd/system ]] || die 'Requer systemd ativo.'
python3 - "$public_ip" <<'PY'
import ipaddress, sys
address = ipaddress.IPv4Address(sys.argv[1])
if not address.is_global:
    raise SystemExit('Informe o IPv4 publico real da instancia.')
PY

state=/var/lib/xmqr-oracle-install
packages=/var/cache/xmqr-oracle-install
if [[ $resume_mqtt == true ]]; then
    [[ -d $state && ! -L $state && $(stat -c '%u:%a' "$state") == 0:700 ]] || die 'Checkpoint ausente ou inseguro.'
    [[ -f $state/status && ! -L $state/status && $(stat -c '%u:%a' "$state/status") == 0:600 ]] || die 'Status ausente ou inseguro.'
    case $(cat "$state/status") in
        'FAILED stage=mqtt-smoke exit=1'|'FAILED stage=mqtt-smoke exit=2') ;;
        *) die 'Retomada MQTT exige checkpoint de falha em mqtt-smoke.' ;;
    esac
    [[ ! -e $state/resume-mqtt-0.1.0-rc.1 && ! -L $state/resume-mqtt-0.1.0-rc.1 ]] || die 'Esta retomada MQTT ja foi tentada; solicite revisao.'
    [[ -d $packages && ! -L $packages && $(stat -c '%u:%a' "$packages") == 0:755 ]] || die 'Cache ausente ou inseguro.'
    private_path() {
        local path=$1 owner=$2 mode=$3 kind=$4
        [[ ! -L $path ]] || die "Symlink recusado: $path"
        if [[ $kind == directory ]]; then [[ -d $path ]] || die "Diretorio ausente: $path"
        else [[ -f $path ]] || die "Arquivo ausente: $path"; fi
        [[ $(stat -c '%U:%a' "$path") == "$owner:$mode" ]] || die "Proprietario/modo divergente: $path"
    }
    private_path /etc/xmqr xmqr 700 directory
    private_path /var/lib/xmqr xmqr 700 directory
    private_path /etc/xmqr/broker.env root 600 file
    private_path /etc/xmqr/security.toml xmqr 600 file
    private_path /etc/xmqr/server.key xmqr 600 file
    private_path /etc/xmqr/server.crt xmqr 644 file
    private_path /etc/xmqr/clients-ca.crt xmqr 644 file
    private_path /etc/xmqr-client root 750 directory
    private_path /etc/xmqr-client/oracle xmqr-client 700 directory
    private_path /etc/xmqr-client/oracle.conf root 600 file
    for name in ca.crt client.crt client.key password password-invalid; do
        private_path "/etc/xmqr-client/oracle/$name" xmqr-client 600 file
    done
    private_path /etc/xmqr-admin xmqr-admin 700 directory
    private_path /etc/xmqr-admin/access.token xmqr-admin 600 file
    private_path /root/xmqr-oracle-pki root 700 directory
    private_path /etc/systemd/system/xmqr-admin.service root 644 file
    private_path /etc/systemd/system/xmqr-client-sub@oracle.service.d root 755 directory
    private_path /etc/systemd/system/xmqr-client-sub@oracle.service.d/10-broker.conf root 600 file
    for package in xmqr-broker xmqr-client xmqr-admin; do
        case "$package" in xmqr-admin) expected_version=0.11.0-1 ;; *) expected_version=0.43.0-1 ;; esac
        [[ $(dpkg-query -W -f='${Status} ${Version}' "$package") == "install ok installed $expected_version" ]] || die "Pacote divergente: $package"
    done
    for unit in xmqr-broker.service xmqr-client-sub@oracle.service xmqr-admin.service; do
        if systemctl is-active --quiet "$unit"; then die "Servico ativo: $unit. Revise antes da retomada."; fi
    done
    grep -Fxq 'MQTT_MODE=secure-mtls' /etc/xmqr/broker.env || die 'Modo mTLS divergente.'
    grep -Fxq 'MQTT_MONITOR_BIND=127.0.0.1:9090' /etc/xmqr/broker.env || die 'Monitor divergente.'
    grep -Fxq 'Environment=XMQR_ADMIN_BIND=127.0.0.1:19080' /etc/systemd/system/xmqr-admin.service || die 'Bind do admin divergente.'
elif [[ $resume_packages == true ]]; then
    [[ -d $state && ! -L $state && $(stat -c '%u:%a' "$state") == 0:700 ]] || die 'Checkpoint de instalacao ausente ou inseguro.'
    [[ -f $state/status && ! -L $state/status && $(stat -c '%u:%a' "$state/status") == 0:600 ]] || die 'Status de instalacao ausente ou inseguro.'
    [[ $(cat "$state/status") == 'FAILED stage=install-packages exit=1' ]] || die 'Retomada permitida somente apos falha em install-packages.'
    [[ ! -e $state/resume-packages-v1.7 && ! -L $state/resume-packages-v1.7 ]] || die 'Esta retomada ja foi tentada; preserve os arquivos e solicite revisao.'
    [[ -d $packages && ! -L $packages && $(stat -c '%u:%a' "$packages") == 0:755 ]] || die 'Cache de pacotes ausente ou inseguro.'
    for path in /etc/xmqr/security.toml /root/xmqr-oracle-pki \
        /etc/xmqr-admin /var/lib/xmqr-admin /etc/xmqr-client/oracle \
        /etc/xmqr-client/oracle.conf /etc/systemd/system/xmqr-admin.service \
        /etc/systemd/system/xmqr-client-sub@oracle.service.d; do
        [[ ! -e $path && ! -L $path ]] || die "Configuracao ja iniciada: $path. Retomada recusada."
    done
    [[ -d /etc/xmqr && ! -L /etc/xmqr ]] || die 'Diretorio broker invalido.'
    [[ -f /etc/xmqr/broker.env && ! -L /etc/xmqr/broker.env ]] || die 'Conffile broker invalido.'
    [[ -z $(find /etc/xmqr -mindepth 1 -maxdepth 1 ! -name broker.env -print -quit) ]] || die 'Arquivos broker externos ao pacote; retomada recusada.'
    for path in /var/lib/xmqr /etc/xmqr-client /var/lib/xmqr-client; do
        if [[ -e $path || -L $path ]]; then
            [[ -d $path && ! -L $path ]] || die "Diretorio invalido: $path"
            [[ -z $(find "$path" -mindepth 1 -maxdepth 1 -print -quit) ]] || die "Diretorio nao vazio: $path. Retomada recusada."
        fi
    done
    for package in xmqr-broker xmqr-client xmqr-admin; do
        case "$package" in xmqr-admin) expected_version=0.11.0-1 ;; *) expected_version=0.43.0-1 ;; esac
        [[ $(dpkg-query -W -f='${Status} ${Version}' "$package") == "install ok installed $expected_version" ]] || die "Pacote instalado divergente: $package"
        if ! verification=$(dpkg -V "$package" 2>&1); then die "Verificacao dpkg falhou: $package"; fi
        [[ -z $verification ]] || die "Arquivos de pacote alterados: $package. Retomada recusada."
    done
    getent passwd xmqr >/dev/null || die 'Usuario broker ausente.'
    getent passwd xmqr-client >/dev/null || die 'Usuario client ausente.'
    if getent passwd xmqr-admin >/dev/null; then die 'Conta do observador ja existe; retomada recusada.'; fi
    python3 -c 'from argon2 import PasswordHasher, Type'
else
for path in /etc/xmqr /var/lib/xmqr /etc/xmqr-client /var/lib/xmqr-client \
    /etc/xmqr-admin /var/lib/xmqr-admin /root/xmqr-oracle-pki \
    /var/lib/xmqr-oracle-install /var/cache/xmqr-oracle-install \
    /etc/systemd/system/xmqr-admin.service \
    /etc/systemd/system/xmqr-client-sub@oracle.service.d; do
    [[ ! -e $path && ! -L $path ]] || die "Instalacao existente/parcial: $path. Preserve os dados e solicite revisao."
done
for package in xmqr-broker xmqr-client xmqr-admin; do
    if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed'; then
        die "Pacote ja instalado: $package. Este script nao faz upgrade."
    fi
done
for account in xmqr xmqr-client xmqr-admin; do
    if getent passwd "$account" >/dev/null; then
        die "Conta preexistente: $account. Revise antes de instalar."
    fi
done
fi
for port in 8883 19080 9090; do
    if ss -H -lnt "sport = :$port" | grep -q .; then
        die "Porta $port ja ocupada."
    fi
done

if [[ $resume_mqtt == true ]]; then
    attempt_dir="$state/resume-mqtt-0.1.0-rc.1"
    mkdir -- "$attempt_dir"
    cp -p -- "$state/status" "$attempt_dir/status-before"
elif [[ $resume_packages == true ]]; then
    mkdir -- "$state/resume-packages-v1.7"
    cp -p -- "$state/status" "$state/resume-packages-v1.7/status-before"
    attempt_dir="$state/resume-packages-v1.7"
else
    install -d -m 0700 "$state"
    install -d -m 0755 "$packages"
    attempt_dir=$state
fi
created_units=()
stage=prerequisites
on_exit() {
    result=$?
    if (( result != 0 )); then
        printf 'FAILED stage=%s exit=%s\n' "$stage" "$result" > "$state/status"
        for unit in "${created_units[@]}"; do
            systemctl disable --now "$unit" >/dev/null 2>&1 || true
        done
        printf '\nFalha na etapa %s. Arquivos preservados; servicos desta execucao parados.\n' "$stage" >&2
        printf 'Envie a mensagem de erro, sem chaves, senhas ou tokens. Nao reexecute nem apague o estado.\n' >&2
    fi
    exit "$result"
}
trap on_exit EXIT
export DEBIAN_FRONTEND=noninteractive
if [[ $resume_packages == false && $resume_mqtt == false ]]; then
    apt-get update
    apt-get install -y --no-install-recommends ca-certificates curl openssl python3 python3-argon2
fi

stage=download-and-checksums
fetch_package() {
    local repo=$1 version=$2 file=$3 expected=$4
    if [[ $resume_packages == true || $resume_mqtt == true ]]; then
        [[ -f $packages/$file && ! -L $packages/$file ]] || die "Pacote cache ausente/invalido: $file"
    else
    curl --fail --show-error --location --retry 2 --connect-timeout 15 --max-time 180 \
        --proto '=https' --proto-redir '=https' --tlsv1.2 \
        "https://github.com/licodevone/$repo/releases/download/v$version/$file" \
        --output "$packages/$file"
    fi
    printf '%s  %s\n' "$expected" "$packages/$file" | sha256sum --check --strict
    [[ $(dpkg-deb -f "$packages/$file" Architecture) == amd64 ]] || die 'Arquitetura do pacote incorreta.'
    [[ $(dpkg-deb -f "$packages/$file" Version) == "$version-1" ]] || die 'Versao do pacote incorreta.'
    case "$repo" in xmqr) local name=xmqr-broker ;; *) local name=$repo ;; esac
    [[ $(dpkg-deb -f "$packages/$file" Package) == "$name" ]] || die 'Nome do pacote incorreto.'
    if [[ $resume_mqtt == true ]]; then
        local executables=() executable packed_hash installed_hash
        case "$repo" in
            xmqr) executables=(mqtt-broker mqtt-admin) ;;
            xmqr-client) executables=(mqtt-client mqtt-bridge) ;;
            xmqr-admin) executables=(xmqr-admin) ;;
        esac
        for executable in "${executables[@]}"; do
            [[ -f /usr/bin/$executable && ! -L /usr/bin/$executable ]] || die "Executavel ausente/invalido: $executable"
            packed_hash=$(dpkg-deb --fsys-tarfile "$packages/$file" | tar -xOf - "./usr/bin/$executable" | sha256sum | cut -d ' ' -f1)
            installed_hash=$(sha256sum "/usr/bin/$executable" | cut -d ' ' -f1)
            [[ $packed_hash == "$installed_hash" ]] || die "Executavel alterado: $executable"
        done
    fi
}
fetch_package xmqr 0.43.0 xmqr-broker_0.43.0-1_amd64.deb c2341ab3a341b1854e85ebb2f0bec9535968374b226a12a60cee58aa7cef3d4e
fetch_package xmqr-client 0.43.0 xmqr-client_0.43.0-1_amd64.deb e4d09cec660a0dba20790181727b17c44040913425a3340d3838e45113241f76
fetch_package xmqr-admin 0.11.0 xmqr-admin_0.11.0-1_amd64.deb fe03ffc858e7583e7d8ce6808b4f56495c688beb69d47870db7fe0c1b8b55469
chmod 0644 "$packages/"*.deb

stage=install-packages
if [[ $resume_packages == false && $resume_mqtt == false ]]; then
    apt-get install -y "$packages/xmqr-broker_0.43.0-1_amd64.deb" \
        "$packages/xmqr-client_0.43.0-1_amd64.deb" "$packages/xmqr-admin_0.11.0-1_amd64.deb"
fi
created_units+=(xmqr-broker.service)
[[ $(/usr/bin/mqtt-broker --version) == 'mqtt-broker 0.43.0' ]] || die 'Versao inesperada do broker.'
[[ $(/usr/bin/mqtt-client --version) == 'mqtt-client 0.43.0' ]] || die 'Versao inesperada do client.'
[[ $(/usr/bin/mqtt-bridge --version) == 'mqtt-bridge 0.5.0 (xmqr-client 0.43.0)' ]] || die 'Versao inesperada da bridge.'
[[ $(/usr/bin/xmqr-admin --version) == 'xmqr-admin 0.11.0' ]] || die 'Versao inesperada do admin.'

stage=cli-preflight
verifier="$(dirname -- "$(readlink -f -- "$0")")/verify_oracle_installer.py"
[[ -f $verifier && ! -L $verifier ]] || die 'Verificador ausente; utilize o pacote versionado completo.'
python3 "$verifier" --script "$(readlink -f -- "$0")"

if [[ $resume_mqtt == false ]]; then
stage=private-certificates
pki=/root/xmqr-oracle-pki
install -d -m 0700 "$pki"
openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 3650 \
    -subj '/CN=XMQR Oracle Private CA' \
    -addext 'basicConstraints=critical,CA:TRUE' \
    -addext 'keyUsage=critical,keyCertSign,cRLSign' \
    -keyout "$pki/ca.key" -out "$pki/ca.crt"
openssl req -new -newkey rsa:2048 -nodes -subj '/CN=xmqr' \
    -keyout "$pki/server.key" -out "$pki/server.csr"
cat > "$pki/server.ext" <<EOF
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=IP:$public_ip,IP:127.0.0.1,DNS:localhost,DNS:xmqr
EOF
openssl x509 -req -sha256 -days 365 -in "$pki/server.csr" \
    -CA "$pki/ca.crt" -CAkey "$pki/ca.key" -CAcreateserial \
    -extfile "$pki/server.ext" -out "$pki/server.crt"
openssl req -new -newkey rsa:2048 -nodes -subj '/CN=xmqr-oracle-client' \
    -keyout "$pki/client.key" -out "$pki/client.csr"
cat > "$pki/client.ext" <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature
extendedKeyUsage=clientAuth
EOF
openssl x509 -req -sha256 -days 365 -in "$pki/client.csr" \
    -CA "$pki/ca.crt" -CAkey "$pki/ca.key" -CAserial "$pki/ca.srl" \
    -extfile "$pki/client.ext" -out "$pki/client.crt"
openssl verify -CAfile "$pki/ca.crt" -purpose sslserver -verify_ip "$public_ip" "$pki/server.crt"
openssl verify -CAfile "$pki/ca.crt" -purpose sslclient "$pki/client.crt"

install -d -m 0700 -o xmqr -g xmqr /etc/xmqr
install -m 0600 -o xmqr -g xmqr "$pki/server.key" /etc/xmqr/server.key
install -m 0644 -o xmqr -g xmqr "$pki/server.crt" /etc/xmqr/server.crt
install -m 0644 -o xmqr -g xmqr "$pki/ca.crt" /etc/xmqr/clients-ca.crt
install -d -m 0750 -o root -g xmqr-client /etc/xmqr-client
install -d -m 0700 -o xmqr-client -g xmqr-client /etc/xmqr-client/oracle
for file in ca.crt client.crt client.key; do
    install -m 0600 -o xmqr-client -g xmqr-client "$pki/$file" "/etc/xmqr-client/oracle/$file"
done

stage=password-and-acl
python3 - <<'PY'
import hashlib, os, pathlib, pwd, secrets, ssl
from argon2 import PasswordHasher, Type
client = pathlib.Path('/etc/xmqr-client/oracle')
password = secrets.token_urlsafe(32)
hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1,
                        hash_len=32, salt_len=16, type=Type.ID)
password_hash = hasher.hash(password)
hasher.verify(password_hash, password)
certificate = ssl.PEM_cert_to_DER_cert((client/'client.crt').read_text())
fingerprint = hashlib.sha256(certificate).hexdigest()
def private_file(path, text, account):
    owner = pwd.getpwnam(account)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        os.fchown(stream.fileno(), owner.pw_uid, owner.pw_gid)
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
private_file(client/'password', password+'\n', 'xmqr-client')
private_file(client/'password-invalid', 'invalid-p260-password\n', 'xmqr-client')
bundle = ("version = 1\n\n[[users]]\nusername = 'oracle-client'\n"
          f"password_hash = '{password_hash}'\ncert_sha256 = 'sha256:{fingerprint}'\n"
          "publish = ['xmqr/health']\nsubscribe = ['xmqr/health']\n")
private_file('/etc/xmqr/security.toml', bundle, 'xmqr')
PY
runuser -u xmqr -- /usr/bin/xmqr-admin bundle validate --file /etc/xmqr/security.toml

stage=configure-services
cat > /etc/xmqr/broker.env <<'EOF'
MQTT_MODE=secure-mtls
MQTT_BIND=0.0.0.0:8883
MQTT_STATE_DIR=/var/lib/xmqr
MQTT_SERVER_CERT=/etc/xmqr/server.crt
MQTT_SERVER_KEY=/etc/xmqr/server.key
MQTT_CLIENT_CA=/etc/xmqr/clients-ca.crt
MQTT_SECURITY_BUNDLE=/etc/xmqr/security.toml
MQTT_MONITOR_ENABLED=true
MQTT_MONITOR_BIND=127.0.0.1:9090
RUST_LOG=info
EOF
chmod 0600 /etc/xmqr/broker.env
cat > /etc/xmqr-client/oracle.conf <<'EOF'
HOST=127.0.0.1
PORT=8883
TOPIC=xmqr/health
USERNAME=oracle-client
CLIENT_ID=xmqr-oracle-sub
QOS=1
EOF
chmod 0600 /etc/xmqr-client/oracle.conf
install -d -m 0755 /etc/systemd/system/xmqr-client-sub@oracle.service.d
cat > /etc/systemd/system/xmqr-client-sub@oracle.service.d/10-broker.conf <<'EOF'
[Unit]
After=xmqr-broker.service
Requires=xmqr-broker.service
PartOf=xmqr-broker.service
EOF
created_units+=(xmqr-client-sub@oracle.service)
useradd --system --user-group --home-dir /var/lib/xmqr-admin --shell /usr/sbin/nologin xmqr-admin
install -d -m 0700 -o xmqr-admin -g xmqr-admin /etc/xmqr-admin
runuser -u xmqr-admin -- /usr/bin/xmqr-admin token-init --file /etc/xmqr-admin/access.token
cat > /etc/systemd/system/xmqr-admin.service <<'EOF'
[Unit]
Description=XMQR local read-only observer
After=network.target xmqr-broker.service
Wants=xmqr-broker.service
StartLimitIntervalSec=120
StartLimitBurst=5

[Service]
Type=simple
User=xmqr-admin
Group=xmqr-admin
Environment=XMQR_ADMIN_BIND=127.0.0.1:19080
Environment=XMQR_ADMIN_MONITOR_BIND=127.0.0.1:9090
Environment=XMQR_ADMIN_TOKEN_FILE=/etc/xmqr-admin/access.token
ExecStart=/usr/bin/xmqr-admin serve
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
RestrictSUIDSGID=true

[Install]
WantedBy=multi-user.target
EOF
chmod 0644 /etc/systemd/system/xmqr-admin.service
created_units+=(xmqr-admin.service)
else
    stage=validate-existing-config
    created_units+=(xmqr-client-sub@oracle.service xmqr-admin.service)
    runuser -u xmqr -- /usr/bin/xmqr-admin bundle validate --file /etc/xmqr/security.toml
    cmp -s /etc/xmqr/clients-ca.crt /etc/xmqr-client/oracle/ca.crt || die 'CAs divergentes.'
    openssl verify -CAfile /etc/xmqr/clients-ca.crt -purpose sslserver -verify_ip "$public_ip" /etc/xmqr/server.crt
    openssl verify -CAfile /etc/xmqr/clients-ca.crt -purpose sslclient /etc/xmqr-client/oracle/client.crt
fi
systemd-analyze verify /usr/lib/systemd/system/xmqr-broker.service /etc/systemd/system/xmqr-admin.service
systemctl daemon-reload
systemctl start xmqr-broker.service
wait_ready() {
    local attempt
    for attempt in {1..30}; do
        if curl --noproxy '*' --fail --silent --max-time 2 http://127.0.0.1:9090/ready >/dev/null; then return 0; fi
        sleep 1
    done
    die 'Broker nao ficou pronto. Consulte journalctl -u xmqr-broker.service.'
}
wait_ready

stage=mqtt-smoke
client_args=(--host 127.0.0.1 --port 8883 --username oracle-client --qos 1
    --ca /etc/xmqr-client/oracle/ca.crt --cert /etc/xmqr-client/oracle/client.crt
    --key /etc/xmqr-client/oracle/client.key --password-file /etc/xmqr-client/oracle/password
    --timeout-seconds 8 --total-timeout-seconds 15)
run_client() { runuser -u xmqr-client -- /usr/bin/mqtt-client "$@"; }
run_client_checked() {
    local label=$1 result
    shift
    if run_client "$@" 2>"$attempt_dir/$label.stderr"; then
        return 0
    else
        result=$?
        printf 'Erro MQTT no teste %s (exit %s):\n' "$label" "$result" >&2
        head -n 1 "$attempt_dir/$label.stderr" >&2
        return "$result"
    fi
}
printf '%s\n' 'MQTT teste 1/4: publicar e receber retained.'
run_client_checked publish pub "${client_args[@]}" --client-id p260-check-pub \
    --topic xmqr/health --message XMQR-P260-READY --retain true
[[ $(run_client_checked subscribe sub "${client_args[@]}" --client-id p260-check-sub \
    --topic xmqr/health --count 1 --output raw) == XMQR-P260-READY ]] || die 'Pub/sub mTLS falhou.'
printf '%s\n' 'PASS: pub/sub mTLS QoS1.'
systemctl restart xmqr-broker.service
wait_ready
printf '%s\n' 'MQTT teste 2/4: retained apos restart.'
[[ $(run_client_checked restart sub "${client_args[@]}" --client-id p260-check-restart \
    --topic xmqr/health --count 1 --output raw) == XMQR-P260-READY ]] || die 'Retained apos restart falhou.'
printf '%s\n' 'PASS: retained apos restart.'
negative_args=("${client_args[@]}")
for ((index=0; index<${#negative_args[@]}; index++)); do
    if [[ ${negative_args[index]} == --password-file ]]; then
        negative_args[index+1]=/etc/xmqr-client/oracle/password-invalid
    fi
done
printf '%s\n' 'MQTT teste 3/4: recusar senha incorreta.'
if run_client pub "${negative_args[@]}" --client-id p260-invalid \
    --topic xmqr/health --message XMQR-P260-NEGATIVE >"$attempt_dir/rejected.log" 2>&1; then
    die 'Senha invalida foi aceita.'
fi
grep -Eq 'autenticacao MQTT recusada|acesso MQTT recusado' "$attempt_dir/rejected.log" || die 'Falha negativa sem recusa MQTT de autenticacao comprovada.'
printf '%s\n' 'MQTT teste 4/4: publicar com identidade valida.'
run_client_checked after-negative pub "${client_args[@]}" --client-id p260-valid-after \
    --topic xmqr/health --message XMQR-P260-READY --retain true
printf '%s\n' 'PASS: senha invalida recusada, conexao valida preservada.'

stage=admin-smoke
systemctl start xmqr-admin.service
for attempt in {1..20}; do
    if curl --noproxy '*' --fail --silent --max-time 2 http://127.0.0.1:19080/ >/dev/null; then break; fi
    sleep 1
done
python3 - <<'PY'
import pathlib, urllib.error, urllib.request
url = 'http://127.0.0.1:19080/api/status'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    opener.open(url, timeout=5)
except urllib.error.HTTPError as error:
    if error.code != 401:
        raise SystemExit(f'Esperava HTTP401 sem token; recebeu {error.code}')
else:
    raise SystemExit('API administrativa aceitou acesso sem token')
token = pathlib.Path('/etc/xmqr-admin/access.token').read_text().strip()
request = urllib.request.Request(url, headers={'Authorization': 'Bearer '+token})
with opener.open(request, timeout=5) as response:
    if response.status != 200:
        raise SystemExit('Falha no acesso administrativo autenticado')
print('PASS: admin autenticado; acesso sem token recusado.')
PY

stage=enable-services
systemctl enable --now xmqr-broker.service xmqr-admin.service xmqr-client-sub@oracle.service
sleep 2
for unit in xmqr-broker.service xmqr-admin.service xmqr-client-sub@oracle.service; do
    systemctl is-active --quiet "$unit" || die "Servico inativo: $unit"
done
wait_ready
printf 'PASS Ubuntu26 amd64 packages,mTLS,QoS1,retained,restart,authentication,admin,services\n' > "$state/status"
stage=complete
printf '\nXMQR_INSTALL_PASS\n'
/usr/bin/mqtt-broker --version
/usr/bin/mqtt-client --version
/usr/bin/mqtt-bridge --version
/usr/bin/xmqr-admin --version
printf '\nBroker TLS: %s:8883\nPainel por tunel SSH: http://127.0.0.1:19080\n' "$public_ip"
printf '%s\n' 'Token privado: sudo cat /etc/xmqr-admin/access.token (somente no seu terminal).' \
    'Firewall e regras OCI nao foram alterados. Nao publique 19080/9090.' \
    'Certificados folha: validade 365 dias; CA: 3650 dias. Planeje a renovacao.' \
    'Cliente de teste limitado ao topico xmqr/health. Dispositivos precisam de identidades/ACL proprias.'
