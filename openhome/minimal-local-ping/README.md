# Minimal Local Ping

Clean-room diagnostic Local Ability. It sends one `ping_devkit` action to the physical OpenHome DevKit, writes one safe DevKit log entry, and returns a bounded `pong` JSON payload.

Trigger: `devkit ping`

No network calls, credentials, BLE access, filesystem access, or third-party dependencies.
