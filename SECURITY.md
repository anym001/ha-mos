# Security Policy

## Supported versions

Only the latest release receives fixes. Backporting is not practical, and HACS updates in place anyway.

| Version        | Supported |
| -------------- | --------- |
| Latest release | ✅        |
| Anything older | ❌        |

## Reporting a vulnerability

**Please do not open a public issue.** Use GitHub's private vulnerability reporting instead:

[**Report a vulnerability**](../../security/advisories/new)

That opens a private advisory only you and the maintainers can see, so a fix can be prepared before anything is public.

Helpful in a report:

- What an attacker can do, and what they need in order to do it — network position, a valid API token, access to Home Assistant, and so on
- Which version of the integration and of MOS you saw it on
- Steps to reproduce, ideally against a test server
- Log output or a diagnostics download, with the token and anything identifying removed

Expect an acknowledgement within about a week. There is no guaranteed response time and no bug bounty. Credit in the release notes is offered by default and gladly withheld on request.

## What belongs here, and what doesn't

**In scope** — anything in `custom_components/mos/`: how the API token is stored, transmitted or logged, what ends up in a diagnostics download, how request paths are built, and how the token's permission scope is honoured.

**Out of scope** — vulnerabilities in the MOS server, its REST API or its web UI. This integration is only a client. Report those to the [MOS project](https://mos-official.net/), not here.

Also out of scope, because they are documented behaviour rather than defects — see the [Security section of the README](README.md#security) for the reasoning:

- The connection defaults to plain HTTP, so the API token is sent in clear text unless HTTPS is enabled
- **Verify TLS certificate** can be turned off
- A diagnostics download deliberately keeps container, VM and pool names readable

If you think one of those defaults is wrong, an ordinary issue is the right place to argue it.
