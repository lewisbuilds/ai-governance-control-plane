# AIBOM Verification and Key Management

This project can optionally enforce verification of AI Bill of Materials (AIBOM) signatures for policy operations.

## Enabling Verification

- Set environment variables (already wired in Compose):
  - `AIBOM_REQUIRED=true`
  - `AIBOM_PUBLIC_KEY_PATH=/app/keys/aibom_public_key.pem`
- Provide an Ed25519 public key file at `infra/keys/aibom_public_key.pem` (or mount your path).
- The `mcp-policy` service will reject operations that do not include a valid AIBOM signature when `AIBOM_REQUIRED=true`.

## Key Rotation Procedure

1. Generate a new Ed25519 key pair in a secure workstation or HSM:
   - Public key (PEM) to distribute.
   - Private key stays in your signer system/tooling.
2. Publish the new public key into `infra/keys/aibom_public_key.pem` (or your secret store) and roll out the updated config.
3. During a rotation window, you may support two keys by placing a multi-key file and updating the service to load both. After cutover, remove the old key.
4. Record the rotation in your change log and update any CI pipelines that sign artifacts.

## CI Integration (optional)

If you sign AIBOMs/SBOMs during builds, add a CI step to verify signatures using the same public key path. Gate deployments when verification fails.

## Notes

- Keep keys out of source control unless they are public.
- Ensure secure permissions on mounted key files in production.
- All verification should use modern, constant‑time Ed25519 libraries.