"""Client for the Aruba Instant (IAP) virtual-controller web API.

Talks to ``/swarm.cgi`` on port 4343 — the same endpoint the Instant WebUI
uses — so it works without enabling the separate ``allow-rest-api`` feature.

Protocol (observed from the WebUI's app.js and a live AP):
  * Login:  POST /swarm.cgi  opcode=login&user=..&passwd=..
            -> <re><data name="sid">..</data>..</re>   (bad creds -> <re></re>)
  * Show:   GET  /swarm.cgi?opcode=show&cmd=<cli cmd>&ip=127.0.0.1&sid=..
            -> <re><t tn="Client List" nc=".." nr=".."><th><h>..</h></th>
                   <r><c>..</c>..</r>..</t></re>
  * Expired session -> <re><error>Invalid Session ID</error></re>
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
import xml.etree.ElementTree as ET

import aiohttp
from defusedxml import ElementTree as SafeET

_LOGGER = logging.getLogger(__name__)

INVALID_SESSION = "invalid session id"
TIMEOUT = aiohttp.ClientTimeout(total=15)


class ArubaApiError(Exception):
    """Generic communication / parsing failure."""


class ArubaAuthError(ArubaApiError):
    """Credentials rejected."""


@dataclass
class ArubaTable:
    """A parsed ``<t>`` table from a show command."""

    name: str
    headers: list[str] = field(default_factory=list)
    rows: list[dict[str, str]] = field(default_factory=list)


def _parse_xml(text: str) -> ET.Element:
    try:
        return SafeET.fromstring(text)
    except (ET.ParseError, SafeET.DefusedXmlException) as err:
        raise ArubaApiError(f"Invalid XML from AP: {err}") from err


def parse_tables(root: ET.Element) -> list[ArubaTable]:
    """Extract every ``<t>`` table under the response root."""
    tables: list[ArubaTable] = []
    for t in root.iter("t"):
        headers = [(h.text or "").strip() for h in t.findall("./th/h")]
        rows = [
            dict(zip(headers, [(c.text or "").strip() for c in r.findall("c")]))
            for r in t.findall("r")
        ]
        tables.append(ArubaTable(name=(t.get("tn") or "").strip(), headers=headers, rows=rows))
    return tables


def parse_client_count(root: ET.Element) -> int:
    """Count wireless clients in a ``show clients`` response."""
    for table in parse_tables(root):
        if table.name.lower() == "client list":
            return len(table.rows)
    # Some firmwares also emit a summary data item; use it if present.
    for data in root.iter("data"):
        if (data.get("name") or "").strip().lower() == "number of clients":
            try:
                return int((data.text or "").strip())
            except ValueError:
                break
    raise ArubaApiError("No 'Client List' table in 'show clients' response")


class ArubaInstantClient:
    """Minimal async client for an Aruba Instant virtual controller."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        username: str,
        password: str,
        verify_ssl: bool = False,
    ) -> None:
        self._session = session
        self._url = f"https://{host}:{port}/swarm.cgi"
        self._username = username
        self._password = password
        self._ssl = None if verify_ssl else False
        self._sid: str | None = None
        self._lock = asyncio.Lock()

    async def _request(self, method: str, **kwargs) -> ET.Element:
        try:
            async with self._session.request(
                method, self._url, ssl=self._ssl, timeout=TIMEOUT, **kwargs
            ) as resp:
                resp.raise_for_status()
                text = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise ArubaApiError(f"Error talking to {self._url}: {err}") from err
        return _parse_xml(text)

    async def login(self) -> None:
        root = await self._request(
            "POST",
            data={
                "opcode": "login",
                "user": self._username,
                "passwd": self._password,
                "refresh": "false",
                "ip": "127.0.0.1",
            },
        )
        error = root.findtext("error")
        if error:
            raise ArubaAuthError(error.strip())
        for data in root.iter("data"):
            if data.get("name") == "sid" and data.text:
                self._sid = data.text.strip()
                return
        raise ArubaAuthError("Login rejected (no session id returned)")

    async def logout(self) -> None:
        if not self._sid:
            return
        try:
            await self._request("POST", data={"opcode": "logout", "sid": self._sid})
        except ArubaApiError:
            pass
        self._sid = None

    async def show(self, cmd: str) -> ET.Element:
        """Run a ``show`` CLI command, re-logging in once if the session expired."""
        async with self._lock:
            for attempt in range(2):
                if not self._sid:
                    await self.login()
                root = await self._request(
                    "GET",
                    params={
                        "opcode": "show",
                        "cmd": cmd,
                        "ip": "127.0.0.1",
                        "refresh": "false",
                        "sid": self._sid,
                    },
                )
                error = (root.findtext("error") or "").strip()
                if not error:
                    return root
                if error.lower() == INVALID_SESSION and attempt == 0:
                    _LOGGER.debug("Aruba session expired, logging in again")
                    self._sid = None
                    continue
                raise ArubaApiError(f"'{cmd}' failed: {error}")
        raise ArubaApiError(f"'{cmd}' failed after re-login")

    async def get_client_count(self) -> int:
        return parse_client_count(await self.show("show clients"))
