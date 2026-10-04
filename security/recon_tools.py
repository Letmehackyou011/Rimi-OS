"""
Native Reconnaissance Tools for OSINT, Subdomain Enumeration, DNS, and Port Scanning.
Combines system curl (when present) with Python network primitives for maximum Windows/Linux compatibility.
"""

from __future__ import annotations

import asyncio
import shutil
import socket
import subprocess
from typing import Any, Dict, List
from urllib.parse import urlparse

COMMON_SUBDOMAINS = [
    "api", "dev", "staging", "admin", "mail", "app", "test",
    "portal", "auth", "login", "vpn", "beta", "webmail", "shop"
]

COMMON_PORTS = [21, 22, 25, 53, 80, 110, 143, 443, 465, 587, 993, 995, 3306, 5432, 8080, 8443, 8000, 8888]

SECURITY_HEADERS = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "X-XSS-Protection",
]


def extract_domain(target: str) -> str:
    """Extract host/domain from target URL or host string."""
    target = target.strip()
    if "://" in target:
        parsed = urlparse(target)
        return parsed.hostname or target
    return target.split("/")[0].split(":")[0]


async def resolve_dns_records(domain: str) -> Dict[str, Any]:
    """Resolve A and IP addresses for a host asynchronously."""
    loop = asyncio.get_event_loop()
    results: Dict[str, Any] = {"domain": domain, "ip_addresses": [], "status": "pending"}

    def _resolve():
        try:
            addr_info = socket.getaddrinfo(domain, None)
            ips = sorted(list({item[4][0] for item in addr_info if item[4]}))
            return ips
        except Exception as e:
            return str(e)

    res = await loop.run_in_executor(None, _resolve)
    if isinstance(res, list):
        results["ip_addresses"] = res
        results["status"] = "resolved"
    else:
        results["status"] = "failed"
        results["error"] = str(res)
    return results


async def enumerate_subdomains(domain: str, max_check: int = 14) -> List[Dict[str, Any]]:
    """Enumerate common subdomains asynchronously using native DNS resolution."""
    loop = asyncio.get_event_loop()
    found: List[Dict[str, Any]] = []

    def _check_sub(sub: str):
        full_host = f"{sub}.{domain}"
        try:
            addr = socket.gethostbyname(full_host)
            return {"subdomain": full_host, "ip": addr}
        except Exception:
            return None

    tasks = [
        loop.run_in_executor(None, _check_sub, sub)
        for sub in COMMON_SUBDOMAINS[:max_check]
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, dict) and r:
            found.append(r)
    return found


async def scan_common_ports(host: str, ports: List[int] | None = None, timeout: float = 1.0) -> List[Dict[str, Any]]:
    """Safe, timeout-bounded TCP port scanner for common services."""
    check_ports = ports or COMMON_PORTS
    open_ports = []

    async def _check_port(port: int):
        try:
            conn = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(conn, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            try:
                service = socket.getservbyport(port, "tcp")
            except OSError:
                service = "http" if port in (80, 8080, 8000) else "https" if port in (443, 8443) else "custom"
            return {"port": port, "state": "open", "service": service}
        except Exception:
            return None

    semaphore = asyncio.Semaphore(10)

    async def _bounded_check(port: int):
        async with semaphore:
            return await _check_port(port)

    tasks = [_bounded_check(p) for p in check_ports]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, dict) and r:
            open_ports.append(r)

    return open_ports


def _curl_headers_sync(url: str) -> Dict[str, str]:
    """Fetch HTTP headers using system curl with standard timeouts."""
    if not shutil.which("curl"):
        return {}
    try:
        proc = subprocess.run(
            ["curl", "-s", "-I", "-k", "--max-time", "10", url],
            capture_output=True,
            text=True,
            timeout=12,
        )
        headers = {}
        for line in proc.stdout.splitlines():
            line = line.strip()
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
            elif line.startswith("HTTP/"):
                headers["_status_line"] = line
        return headers
    except Exception:
        return {}


async def inspect_http_security(url: str, timeout: float = 8.0) -> Dict[str, Any]:
    """Inspect HTTP response headers, tech fingerprint, and missing security headers."""
    if not url.startswith("http://") and not url.startswith("https://"):
        target_url = f"https://{url}"
    else:
        target_url = url

    result: Dict[str, Any] = {
        "url": target_url,
        "status_code": None,
        "server": None,
        "technologies": [],
        "present_security_headers": {},
        "missing_security_headers": [],
        "insecure_transport": target_url.startswith("http://"),
    }

    loop = asyncio.get_event_loop()
    headers = await loop.run_in_executor(None, _curl_headers_sync, target_url)

    # If curl didn't produce headers, try urllib as backup
    if not headers:
        import urllib.request
        import ssl
        def _urllib_fetch():
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(target_url, headers={"User-Agent": "Rimi-OS/1.0"})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return {k.lower(): v for k, v in r.headers.items()}
        try:
            headers = await loop.run_in_executor(None, _urllib_fetch)
        except Exception as e:
            result["error"] = str(e)
            headers = {}

    if headers:
        result["server"] = headers.get("server") or headers.get("x-powered-by")
        status_line = headers.get("_status_line", "")
        if status_line:
            parts = status_line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                result["status_code"] = int(parts[1])

        # Technologies
        for k, v in headers.items():
            if k in ("server", "x-powered-by", "x-generator"):
                result["technologies"].append(f"{k}: {v}")
            if "hostinger" in v.lower() or "hpanel" in v.lower():
                result["technologies"].append("Hostinger")
            if "cloudflare" in v.lower():
                result["technologies"].append("Cloudflare")

        # Check security headers
        for sec_header in SECURITY_HEADERS:
            key_lower = sec_header.lower()
            if key_lower in headers:
                result["present_security_headers"][sec_header] = headers[key_lower]
            else:
                result["missing_security_headers"].append(sec_header)

    return result


async def run_full_reconnaissance_native(target: str) -> Dict[str, Any]:
    """Execute complete native OSINT, DNS, subdomain, port scan, and HTTP security inspection."""
    domain = extract_domain(target)

    dns_task = resolve_dns_records(domain)
    subdomains_task = enumerate_subdomains(domain)
    ports_task = scan_common_ports(domain)
    http_task = inspect_http_security(target)

    dns_res, sub_res, ports_res, http_res = await asyncio.gather(
        dns_task, subdomains_task, ports_task, http_task, return_exceptions=True
    )

    return {
        "domain": domain,
        "dns": dns_res if isinstance(dns_res, dict) else {"error": str(dns_res)},
        "subdomains": sub_res if isinstance(sub_res, list) else [],
        "open_ports": ports_res if isinstance(ports_res, list) else [],
        "http_security": http_res if isinstance(http_res, dict) else {"error": str(http_res)},
    }
