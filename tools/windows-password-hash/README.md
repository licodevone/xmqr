# XMQR Windows password hash helper - P247

Standalone initial-setup helper, using the broker's exact bounded Argon2id
profile: v19, m=19456 KiB, t=2, p=1, 32-byte output. Each invocation obtains
a fresh 16-byte salt from the operating system CSPRNG. Entropy errors fail
closed. It is independent from the fixed-salt test fixture.

The helper accepts **no command-line arguments**. Pass 32..1024 raw password
bytes through standard input, without BOM or appended newline. This interface
is intended for the setup script's generated high-entropy credential; it does
not prompt, generate a default password, or create credential files.

Successful stdout is exactly one PHC hash line. Errors use generic messages
on stderr and exit code 2. Neither passwords nor rejected arguments are echoed.
The input buffer and the returned PHC string are zeroized on drop. The setup
script must capture stdout privately and must not log it or the input.

The setup script owns private stdin delivery, file/ACL creation and certificate
fingerprint binding. This executable performs no installation, service control,
network access or certificate-store changes.

Build and validate from this directory:

```text
cargo fmt --all -- --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
cargo build --locked --release
```

Use a writable `CARGO_HOME` where the environment requires it. This crate's
lockfile and target directory are independent of the broker and other tools.
