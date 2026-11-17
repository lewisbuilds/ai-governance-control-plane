# AIBOM Verification and Key Management

An AIBOM is an AI bill of materials. This project can require a valid signature on an AIBOM before it accepts a policy request.

## Turn verification on

- Set these environment variables. Compose already wires them up.
  - `AIBOM_REQUIRED=true`
  - `AIBOM_PUBLIC_KEY_PATH=/app/keys/aibom_public_key.pem`
- Provide an Ed25519 public key at `infra/keys/aibom_public_key.pem`, or mount a key from another path.
- With `AIBOM_REQUIRED=true`, the `mcp-policy` service rejects any request that does not include a valid AIBOM signature.

## Rotate the key

1. Generate a new Ed25519 key pair on a secure workstation or in a hardware security module (HSM). Share the public key (PEM). Keep the private key inside your signing system.
2. Put the new public key at `infra/keys/aibom_public_key.pem`, or in your secret store, and roll out the change.
3. If you need a changeover period, you can support two keys. Use a file that holds both keys and update the service to load both. Remove the old key after the cutover.
4. Write the rotation in your change log. Update any CI pipeline that signs artifacts.

## Use it in CI (optional)

If you sign AIBOMs or SBOMs during builds, add a CI step that checks the signature with the same public key. Block the deployment if the check fails.

## Good habits

- Keep keys out of source control. The only exception is a public key.
- Set strict permissions on key files in production.
- Use a modern Ed25519 library that compares values in constant time.
