# Security Policy

PBX Admin sits on an authentication and reverse-proxy boundary. Security reports are taken seriously, especially those involving authentication bypass, authorization bypass, server-side request forgery, credential exposure, unsafe proxy behavior, or access to another user's PBX server.

## Supported Versions

Security fixes are applied to the latest release and the default branch. Older releases are not maintained unless explicitly stated in their release notes.

## Reporting a Vulnerability

Do not report vulnerabilities in a public issue, pull request, discussion, log excerpt, or test fixture.

Use [GitHub private vulnerability reporting](https://github.com/mennotech/pbx-admin/security/advisories/new) to contact the maintainers privately. Include:

- the affected version or commit;
- a clear description of the impact;
- reproducible steps or a minimal proof of concept;
- relevant configuration with all secrets and private identifiers removed;
- any known mitigations or suggested fixes.

If private vulnerability reporting is unavailable, contact the repository owner through the contact methods on the [Mennotech GitHub profile](https://github.com/mennotech) and request a private reporting channel. Do not include vulnerability details in the initial public message.

The maintainers will make a best-effort attempt to acknowledge a complete report within seven days. Investigation and release timing depend on severity, reproducibility, and maintainer availability. Please allow time for a fix before public disclosure.

## Deployment Security

Operators are responsible for securely configuring Cloudflare Access, Fly.io, secrets, private networking, TLS verification, and PBX access controls. Example configuration and seed data are placeholders and must be reviewed before deployment.

Reports about vulnerabilities in Cloudflare, Fly.io, Flask, or another dependency should also be sent to the affected upstream project. Reports about an insecure local deployment configuration may be handled as support requests rather than product vulnerabilities.
