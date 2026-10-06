import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

ALLOWED_PORTS = {
    "http": {80},
    "https": {443},
}
DEFAULT_MAX_REDIRECTS = 5


class SafeRequestError(Exception):
    """Base error for a rejected or oversized outbound HTTP request."""


class UnsafeRequestURLError(SafeRequestError):
    pass


class ResponseTooLargeError(SafeRequestError):
    pass


def is_safe_http_url(url: str) -> bool:
    try:
        parsed_url = urlparse(url)
        port = parsed_url.port
    except ValueError:
        return False

    if parsed_url.scheme not in ALLOWED_PORTS or not parsed_url.hostname:
        return False

    if parsed_url.username or parsed_url.password:
        return False

    if port is not None and port not in ALLOWED_PORTS[parsed_url.scheme]:
        return False

    hostname = parsed_url.hostname.lower().rstrip(".")

    if (
        hostname == "localhost"
        or hostname.endswith((".localhost", ".local", ".internal"))
        or "%" in hostname
    ):
        return False

    try:
        return ipaddress.ip_address(hostname).is_global
    except ValueError:
        return True


async def is_safe_request_url(url: str) -> bool:
    if not is_safe_http_url(url):
        return False

    hostname = urlparse(url).hostname
    if hostname is None:
        return False

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            address_info = await asyncio.to_thread(
                socket.getaddrinfo,
                hostname,
                None,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror:
            return False

        addresses = {item[4][0] for item in address_info}
        return bool(addresses) and all(
            ipaddress.ip_address(resolved_address).is_global
            for resolved_address in addresses
        )

    return address.is_global


async def safe_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_response_bytes: int,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
) -> httpx.Response:
    """Fetch a public HTTP(S) URL with redirect and decoded-size limits."""
    current_url = url

    for redirect_count in range(max_redirects + 1):
        if not await is_safe_request_url(current_url):
            raise UnsafeRequestURLError("Outbound URL is not a public HTTP(S) address.")

        request = client.build_request("GET", current_url)
        response = await client.send(request, follow_redirects=False, stream=True)

        try:
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise UnsafeRequestURLError("Redirect response is missing a location.")

                if redirect_count >= max_redirects:
                    raise UnsafeRequestURLError("Too many outbound redirects.")

                current_url = urljoin(current_url, location)
                continue

            response.raise_for_status()
            content = bytearray()

            async for chunk in response.aiter_bytes():
                if len(content) + len(chunk) > max_response_bytes:
                    raise ResponseTooLargeError(
                        f"Outbound response exceeded {max_response_bytes} bytes."
                    )

                content.extend(chunk)

            buffered_headers = {
                name: value
                for name, value in response.headers.items()
                if name.lower() not in {"content-encoding", "content-length"}
            }
            return httpx.Response(
                status_code=response.status_code,
                headers=buffered_headers,
                content=bytes(content),
                request=request,
            )
        finally:
            await response.aclose()

    raise UnsafeRequestURLError("Too many outbound redirects.")
