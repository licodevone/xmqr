# Test-only Windows interoperability fixture

This independent helper hashes a stdin test password using the broker's bounded
Argon2id profile. Its fixed salt is reproducible and MUST NOT provision real users.
It is not included in the product installers. See the P242 validation runner.

Build with `cargo build --locked --manifest-path tools/windows-validation-fixture/Cargo.toml`
from the broker root. The stdin bytes are the complete password; no trailing
newline is removed. The helper prints only the PHC fixture hash.
