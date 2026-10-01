# Controlled Security Operations

The scan API accepts a strict JSON authorization document. The executor never invokes a shell and never accepts arbitrary command arguments.

## Scope document

```json
{
  "version": "1",
  "mode": "safe",
  "targets": [
    {
      "host": "example.com",
      "ports": [80, 443],
      "paths": ["/health"]
    }
  ],
  "tool_allowlist": ["nmap", "curl"],
  "max_runtime_seconds": 120
}
```

The requested API `target` must appear in `targets`. Hosts, ports, and paths are validated before a scan is queued.

## Operating modes

- `safe`: Nmap TCP connect reconnaissance and HTTP header checks only.
- `guarded`: Explicitly allowlisted reconnaissance with tighter timeouts; packet capture can be requested where the OS supports it.
- `full_access`: A label for an explicitly approved scope, not unrestricted command execution. Only implemented allowlisted tools can run.
- `human_review`: The scan pauses in `awaiting_review` until `POST /api/scan/{id}/approve` receives a reviewer token.

## Implemented tools

- `nmap`: bounded TCP-connect scan with a fixed top-port limit or explicit ports.
- `curl`: bounded HTTP/HTTPS `HEAD` request with protocol restriction and timeout.
- `tcpdump`: optional bounded capture on POSIX systems; skipped in safe mode and unavailable on Windows.

Metasploit, Hydra, Hashcat, John, SQLMap, Burp automation, enum4linux, and code-generation attack execution are intentionally not enabled by this implementation. They require a separate authorization and review design, OS-specific privilege handling, audit storage, and stronger containment before they should be exposed to a remote API.

## Live telemetry

`GET /api/scan/{id}/events?after=0` returns recent stage and tool events. Events are currently held in process memory; persistent audit storage should be added before production deployment.
