# Security policy

CheatCraft is a local, read-only diagnostic application for processes you own or are authorized to inspect. The preview is not independently security audited.

## Local access

The desktop selects the process. The MCP adapter cannot attach another process or write memory. Its authenticated named-pipe session secret is stored in `session.json` beside the app, using inherited directory permissions. Extract portable releases into a private, writable folder. Do not share live session files or add them to version control. Software running as your Windows user is outside this trust boundary.

A connected MCP client can read the attached process through the exposed tools. Only connect trusted clients. Exports may contain memory addresses, observed values, process names and diagnostic actions; review them before sharing.

## Reporting a vulnerability

Use the repository's **Security → Report a vulnerability** feature if private vulnerability reporting is available. Otherwise, open an issue requesting a private contact channel without posting secrets, memory dumps or exploit details. Do not submit vulnerabilities involving third-party software to this project's public issue tracker.

## Distribution

Preview binaries are unsigned. Verify the SHA-256 digest from the matching GitHub release. A checksum detects mismatches; it does not establish trust independently of the release publisher. The application does not install drivers or alter Windows protection settings.
