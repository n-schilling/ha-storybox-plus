"""Check the page in a real browser against a throwaway Home Assistant.

Starts Home Assistant in a temporary directory, reachable from this machine
only, with the integration talking to a made-up cloud (see run_hass.py and
demo_cloud.py): one household, a Toniebox 2 that plays, a classic box, bought
and creative figures and a disc, made-up listening times and battery cycles.
Playwright then drives the page and checks what STANDARD.md section 7 asks of
it (Home Assistant's frame with the areas, the pages and subpages, the header's
stamp, refresh and integration button, old addresses, settings rows with their
(i) and the one save button, errors as one line, numbers in the language's
format, phone width and dark mode) and what reaches the integration. Home Assistant is stopped through its own stop action at the
end, also after a failure.

Usage (from the repository root, with the packages of requirements_panel.txt):

    python -I scripts/panel/check_panel.py [--screenshots DIR] [--keep]
        [--browser chrome|chromium] [--headed]

--screenshots writes the pictures of the README into DIR (docs/screenshots).
--keep leaves the temporary directory for a look at the log.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import random
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any
from zoneinfo import ZoneInfo

import aiohttp
from playwright.async_api import Browser, Page, async_playwright

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = ROOT / "custom_components" / "storybox_plus"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import demo_cloud

TIME_ZONE = ZoneInfo("Europe/Berlin")
# Accounts of the throwaway instance; it listens on 127.0.0.1 only and is deleted afterwards
ADMIN = ("admin", "panel-check-admin")
USER = ("user", "panel-check-user")
PANEL = "storybox-plus-panel"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _configuration(port: int) -> str:
    return f"""homeassistant:
  name: Home
  time_zone: {TIME_ZONE.key}
  unit_system: metric
  country: DE
  language: en
http:
  server_host: 127.0.0.1
  server_port: {port}
frontend:
config:
# Home Assistant's frontend asks recorder/info on every page; without a recorder the
# answer is unknown_command, which it sometimes leaves unhandled in the console. The
# database lies in the throwaway configuration folder (in memory is not supported)
recorder:
  purge_keep_days: 1
logger:
  default: warning
"""


def _stored(key: str, data: dict[str, Any]) -> str:
    return json.dumps({"version": 1, "minor_version": 1, "key": key, "data": data})


def _analytics(today: date) -> dict[str, Any]:
    """Made-up listening times of the last 75 days: evenings, more at weekends."""
    rng = random.Random(4)
    weights = {"fig-fox": 5, "fig-dragon": 4, "fig-moon": 3, "fig-grandma": 2, "fig-sea": 1}
    days: dict[str, Any] = {}
    chapters: dict[str, Any] = {}
    hours: dict[str, Any] = {}
    placements: dict[str, Any] = {}
    counts = {"fig-fox": 8, "fig-dragon": 3, "fig-moon": 12, "fig-grandma": 4, "fig-sea": 5}
    for back in range(75):
        day = today - timedelta(days=back)
        if rng.random() < 0.15:
            continue
        weekend = day.weekday() >= 5
        sums: dict[str, int] = {}
        per_chapter: dict[str, dict[str, int]] = {}
        per_hour: dict[str, int] = {}
        placed: dict[str, int] = {}
        for _ in range(rng.randint(2, 5 if weekend else 3)):
            figure = rng.choices(list(weights), weights=list(weights.values()))[0]
            seconds = rng.randint(4, 22) * 60
            sums[figure] = sums.get(figure, 0) + seconds
            # The moon is placed often but for short
            placed[figure] = placed.get(figure, 0) + (3 if figure == "fig-moon" else 1)
            # Early chapters more often than late ones
            index = str(min(int(rng.expovariate(0.6)), counts[figure] - 1))
            per_chapter.setdefault(figure, {})[index] = (
                per_chapter.get(figure, {}).get(index, 0) + seconds
            )
            # Mornings at the weekend, evenings always
            hour = str(
                rng.choice([8, 9, 10, 17, 18, 19, 19, 20] if weekend else [7, 18, 19, 19, 20])
            )
            per_hour[hour] = per_hour.get(hour, 0) + seconds
        key = day.isoformat()
        days[key] = {demo_cloud.KIDS_BOX: sums}
        chapters[key] = per_chapter
        hours[key] = {demo_cloud.KIDS_BOX: per_hour}
        placements[key] = {demo_cloud.KIDS_BOX: placed}
    # The Toniebox 1 was in the network on some evenings (its presence entity told so)
    active = {
        (today - timedelta(days=back)).isoformat(): {demo_cloud.LIVING_BOX: {"18": 2400, "19": 900}}
        for back in range(1, 20, 3)
    }
    return {
        "days": days,
        "chapters": chapters,
        "hours": hours,
        "placements": placements,
        "active": active,
    }


def _battery(today: date) -> dict[str, Any]:
    """Made-up charges of the Toniebox 2, and the one running now."""
    rng = random.Random(9)
    cycles = []
    for n in range(7, 0, -1):
        hours = round(rng.uniform(9.5, 13.5), 2)
        start, end = 100, rng.randint(6, 22)
        cycles.append(
            {
                "day": (today - timedelta(days=3 * n)).isoformat(),
                "hours": hours,
                "from": start,
                "to": end,
                "per_full": round(hours * 100 / (start - end), 1),
            }
        )
    return {
        "cycles": {demo_cloud.KIDS_BOX: cycles},
        "open": {demo_cloud.KIDS_BOX: {"from": 100, "to": 64, "seconds": 4 * 3600 + 20 * 60}},
    }


class Api:
    """REST and WebSocket access to the throwaway instance."""

    def __init__(self, session: aiohttp.ClientSession, base: str) -> None:
        self.session = session
        self.base = base
        self.client_id = f"{base}/"

    async def login(self, username: str, password: str) -> str:
        """An access token for a user, through the login flow the page uses."""
        flow = await self._json(
            "post",
            "/auth/login_flow",
            json={
                "client_id": self.client_id,
                "handler": ["homeassistant", None],
                "redirect_uri": self.client_id,
            },
        )
        step = await self._json(
            "post",
            f"/auth/login_flow/{flow['flow_id']}",
            json={"client_id": self.client_id, "username": username, "password": password},
        )
        token = await self._json(
            "post",
            "/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": step["result"],
                "client_id": self.client_id,
            },
        )
        return str(token["access_token"])

    async def _json(self, method: str, path: str, **kwargs: Any) -> Any:
        async with self.session.request(method, self.base + path, **kwargs) as response:
            response.raise_for_status()
            return await response.json()

    async def post(self, token: str, path: str, body: dict[str, Any] | None = None) -> Any:
        """A REST call as the user of the token."""
        headers = {"Authorization": f"Bearer {token}"}
        return await self._json("post", path, headers=headers, json=body or {})

    async def ws(self, token: str, message: dict[str, Any]) -> dict[str, Any]:
        """One WebSocket command; the whole result message, success or not."""
        async with self.session.ws_connect(self.base + "/api/websocket") as ws:
            await ws.receive_json()
            await ws.send_json({"type": "auth", "access_token": token})
            if (await ws.receive_json())["type"] != "auth_ok":
                raise RuntimeError("WebSocket login failed")
            await ws.send_json({"id": 1, **message})
            while True:
                reply = await ws.receive_json()
                if reply.get("id") == 1 and reply.get("type") == "result":
                    return dict(reply)


class Instance:
    """A throwaway Home Assistant with the integration on a made-up cloud."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.config = directory / "config"
        # What happens in the room of the made-up box (see demo_cloud.DemoPush)
        self.world = directory / "world"
        self.port = _free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.process: subprocess.Popen[bytes] | None = None
        self.token = ""
        self.entry_id = ""

    def _launch(self) -> None:
        """Copy the integration, write the pictures and start Home Assistant in the background."""
        (self.config / "custom_components").mkdir(parents=True)
        shutil.copytree(
            INTEGRATION,
            self.config / "custom_components" / "storybox_plus",
            ignore=shutil.ignore_patterns("__pycache__", "BUILD"),
        )
        commit = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        (self.config / "custom_components" / "storybox_plus" / "BUILD").write_text(
            commit or "panel-check"
        )
        pictures = self.config / "www" / "storybox-demo"
        pictures.mkdir(parents=True)
        for figure_id in demo_cloud.COLOURS:
            (pictures / f"{figure_id}.svg").write_text(demo_cloud.picture_svg(figure_id))
        (pictures / "box-red.svg").write_text(demo_cloud.box_svg())
        (self.config / "configuration.yaml").write_text(_configuration(self.port))
        log = (self.directory / "hass.log").open("wb")
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-I",
                str(Path(__file__).with_name("run_hass.py")),
                "-c",
                str(self.config),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            env={
                **os.environ,
                "STORYBOX_DEMO_BASE": self.base,
                "STORYBOX_DEMO_WORLD": str(self.world),
            },
        )

    async def start(self, session: aiohttp.ClientSession) -> Api:
        """Start, onboard and set up the account with its made-up history."""
        await asyncio.to_thread(self._launch)
        api = Api(session, self.base)
        await self._wait_ready(session)
        self.token = await self._onboard(api)
        await self._seed(api)
        return api

    async def _wait_ready(self, session: aiohttp.ClientSession) -> None:
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError(f"Home Assistant ended, see {self.directory / 'hass.log'}")
            try:
                async with session.get(self.base + "/api/onboarding") as response:
                    if response.status == 200:
                        return
            except aiohttp.ClientError:
                pass
            await asyncio.sleep(1)
        raise RuntimeError("Home Assistant did not start within 3 minutes")

    async def _onboard(self, api: Api) -> str:
        user = await api._json(
            "post",
            "/api/onboarding/users",
            json={
                "client_id": api.client_id,
                "name": "Sam",
                "username": ADMIN[0],
                "password": ADMIN[1],
                "language": "en",
            },
        )
        token = await api._json(
            "post",
            "/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": user["auth_code"],
                "client_id": api.client_id,
            },
        )
        access = str(token["access_token"])
        await api.post(access, "/api/onboarding/core_config")
        await api.post(access, "/api/onboarding/analytics")
        await api.post(
            access,
            "/api/onboarding/integration",
            {"client_id": api.client_id, "redirect_uri": api.client_id},
        )
        # The HTTP settings of configuration.yaml start as a trial that the page
        # asks to confirm and that reverts after five minutes; keep them
        promoted = await api.ws(access, {"type": "http/config/promote"})
        if not promoted["success"]:
            raise RuntimeError(f"HTTP settings not kept: {promoted}")
        return access

    async def _entry(self, api: Api, disabled_by: str | None) -> None:
        reply = await api.ws(
            self.token,
            {
                "type": "config_entries/disable",
                "entry_id": self.entry_id,
                "disabled_by": disabled_by,
            },
        )
        if not reply["success"]:
            raise RuntimeError(f"Entry not switched: {reply}")

    async def _seed(self, api: Api) -> None:
        flow = await api.post(
            self.token, "/api/config/config_entries/flow", {"handler": "storybox_plus"}
        )
        result = await api.post(
            self.token,
            f"/api/config/config_entries/flow/{flow['flow_id']}",
            {"email": "sam@example.com", "password": "made-up"},
        )
        if result.get("type") != "create_entry" or result["result"]["state"] != "loaded":
            raise RuntimeError(f"Storybox Plus did not load: {result}")
        self.entry_id = result["result"]["entry_id"]
        # The history goes into the stores while the entry is off, so its own
        # write at the unload does not cover it
        await self._entry(api, "user")
        today = datetime.now(TIME_ZONE).date()
        storage = self.config / ".storage"
        stores = {
            "analytics": _analytics(today),
            "battery": _battery(today),
            "favourites": {"tonies": {"fig-fox": {"mode": "only", "chapters": [0, 2, 4]}}},
        }
        for name, data in stores.items():
            key = f"storybox_plus.{self.entry_id}.{name}"
            (storage / key).write_text(_stored(key, data))
        await self._entry(api, None)
        # A user without administrator rights, for the access check
        created = await api.ws(
            self.token,
            {"type": "config/auth/create", "name": "Visitor", "group_ids": ["system-users"]},
        )
        await api.ws(
            self.token,
            {
                "type": "config/auth_provider/homeassistant/create",
                "user_id": created["result"]["user"]["id"],
                "username": USER[0],
                "password": USER[1],
            },
        )

    async def stop(self, session: aiohttp.ClientSession) -> None:
        """Stop through Home Assistant's own stop action; force only if that fails."""
        if self.process is None or self.process.poll() is not None:
            return
        try:
            if self.token:
                async with session.post(
                    self.base + "/api/services/homeassistant/stop",
                    headers={"Authorization": f"Bearer {self.token}"},
                ):
                    pass
        except aiohttp.ClientError:
            pass
        try:
            self.process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=30)


@dataclass
class Checks:
    """The checks that ran and the ones that failed."""

    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    before: Callable[[], Awaitable[None]] | None = None

    async def run(self, name: str, check: Callable[[], Awaitable[None]]) -> None:
        try:
            if self.before is not None:
                await self.before()
            await check()
        except Exception as err:
            self.failed.append(f"{name}: {err!r}")
            print(f"FAIL {name}: {err!r}")
        else:
            self.passed.append(name)
            print(f"ok   {name}")


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


async def _until(check: Callable[[], Awaitable[bool]], what: str, seconds: float = 10) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if await check():
            return
        await asyncio.sleep(0.2)
    raise AssertionError(f"timed out waiting for {what}")


async def _open(
    browser: Browser,
    instance: Instance,
    user: tuple[str, str],
    path: str = "/storybox-plus/boxes/overview",
    **options: Any,
) -> Page:
    """A new page, logged in, at the path."""
    target = f"{instance.base}{path}"
    context = await browser.new_context(
        viewport=options.pop("viewport", {"width": 1200, "height": 820}),
        device_scale_factor=2,
        locale="en-US",
        timezone_id=TIME_ZONE.key,
        color_scheme=options.pop("color_scheme", "light"),
    )
    # A rejected promise nobody handles shows with what it carried, not as "Object"
    await context.add_init_script(
        "window.addEventListener('unhandledrejection', (e) => console.error("
        "'unhandled rejection: ' + JSON.stringify(e.reason) + ' ' + (e.reason?.stack || '')));"
    )
    page = await context.new_page()
    # Errors of the page's scripts show in the output, where a failed check needs them
    page.on("pageerror", lambda err: print(f"     page error: {err}", flush=True))
    page.on(
        "console",
        lambda m: print(f"     console: {m.text}", flush=True) if m.type == "error" else None,
    )
    await page.goto(target)
    await page.get_by_label("Username").fill(user[0])
    await page.get_by_label("Password", exact=True).fill(user[1])
    await page.keyboard.press("Enter")
    await page.wait_for_load_state("networkidle")
    # Keep the sidebar out of the pictures
    await page.evaluate("localStorage.setItem('dockedSidebar', JSON.stringify('always_hidden'))")
    await page.goto(target)
    await page.reload()
    await page.wait_for_load_state("networkidle")
    return page


async def _goto(page: Page, instance: Instance, path: str, what: str = "ha-card") -> None:
    """A page of the panel, with its content drawn and Home Assistant's loading screen gone."""
    await page.goto(f"{instance.base}/storybox-plus/{path}")
    await _ready(page, what)


async def _ready(page: Page, what: str) -> None:
    """The page shows its content and Home Assistant's loading screen has faded out."""
    # The first load of the frontend takes a while on a slow CI machine
    await page.locator(f"{PANEL} hass-tabs-subpage").first.wait_for(timeout=90000)
    await page.locator(f"{PANEL} #sheet {what}").first.wait_for(timeout=30000)
    await page.locator("#ha-launch-screen").wait_for(state="detached")


async def _schedules(api: Api, instance: Instance) -> dict[str, dict[str, Any]]:
    """The bedtime schedules of the Toniebox 2 as the integration has them, by name."""
    reply = await api.ws(instance.token, {"type": "storybox_plus/overview"})
    box = next(b for b in reply["result"]["boxes"] if b["bedtime"])
    return {s["name"]: s for s in box["bedtime"]["schedules"]}


async def _kids_box(api: Api, instance: Instance) -> dict[str, Any]:
    reply = await api.ws(instance.token, {"type": "storybox_plus/overview"})
    return dict(next(b for b in reply["result"]["boxes"] if b["id"] == demo_cloud.KIDS_BOX))


async def _library(api: Api, instance: Instance) -> dict[str, dict[str, Any]]:
    """The figures as the integration has them, by ID."""
    reply = await api.ws(instance.token, {"type": "storybox_plus/library"})
    return {figure["id"]: figure for figure in reply["result"]["tonies"]}


async def _entry(api: Api, instance: Instance) -> dict[str, Any]:
    reply = await api.ws(instance.token, {"type": "storybox_plus/overview"})
    return dict(reply["result"]["entries"][0])


def _version() -> str:
    return str(json.loads((INTEGRATION / "manifest.json").read_text())["version"])


async def _frame(page: Page, *, sub: bool, page_id: str | None = None) -> None:
    """Home Assistant's frame: the four areas as tabs and the menu, or a back arrow and a name."""
    info = await page.locator(PANEL).evaluate(
        """el => {
          const frame = el.shadowRoot.getElementById('frame');
          const bar = frame.shadowRoot.getElementById('tabbar');
          const tabs = bar ? [...bar.querySelectorAll('ha-tab')] : [];
          const active = el.shadowRoot.querySelector('#subtabs ha-tab-group-tab[active]');
          return {
            tabs: tabs.length,
            active: tabs.filter((t) => t.active).length,
            back: !!frame.shadowRoot.querySelector('ha-icon-button-arrow-prev'),
            menu: !!frame.shadowRoot.querySelector('ha-menu-button'),
            name: el.shadowRoot.querySelector('.subname')?.textContent.trim() || null,
            page: active ? active.getAttribute('panel') : null,
            pages: el.shadowRoot.querySelectorAll('#subtabs ha-tab-group-tab').length,
          };
        }"""
    )
    if sub:
        expect(info["tabs"] == 0 and info["back"] and not info["menu"], f"subpage frame {info}")
        expect(bool(info["name"]), f"no name in the header {info}")
    else:
        expect(
            info["tabs"] == 4 and info["active"] == 1 and info["menu"] and not info["back"],
            f"frame {info}",
        )
        if page_id is not None and info["pages"]:
            expect(info["page"] == page_id, f"tab of the page: {info['page']} for {page_id}")


async def _header(page: Page) -> None:
    """The header's actions on every page and subpage: stamp, refresh, integration."""
    order = await page.locator(PANEL).evaluate(
        "el => [...el.shadowRoot.querySelector('[slot=toolbar-icon]').children].map(e => e.id)"
    )
    expect(order == ["stamp", "refresh", "integration"], f"header actions {order}")
    stamp = page.locator(f"{PANEL} #stamp")
    await _until(lambda: _stamped(stamp), "the stamp 'As of HH:MM:SS' in the header", seconds=10)
    for button, name, label in (
        ("refresh", "refresh", "Refresh"),
        ("integration", "cog", "Integration in Home Assistant"),
    ):
        el = page.locator(f"{PANEL} ha-icon-button#{button}")
        expect(await el.is_visible(), f"{button} button not visible")
        expect(await el.get_attribute("path") == _mdi(name), f"{button}: wrong icon")
        expect(await el.get_attribute("label") == label, f"{button}: label")


async def _subname(page: Page) -> str:
    return (await page.locator(f"{PANEL} .subname").inner_text()).strip()


async def _named(page: Page, name: str) -> bool:
    return bool(await page.locator(f"{PANEL} .subname").count()) and await _subname(page) == name


async def _save(page: Page) -> None:
    """The one save button of the settings, shown while something is changed."""
    button = page.locator(f"{PANEL} ha-button#save:not([hidden])")
    await button.wait_for(timeout=5000)
    await button.click()
    await page.locator(f"{PANEL} ha-button#save").wait_for(state="hidden", timeout=10000)


async def _attr(locator: Any, name: str, value: str) -> bool:
    return bool(await locator.get_attribute(name) == value)


async def _gone(locator: Any) -> bool:
    return bool(await locator.count() == 0)


async def _count_is(locator: Any, count: int) -> bool:
    return bool(await locator.count() == count)


async def _rows_have_help(page: Page) -> None:
    rows = page.locator(f"{PANEL} ha-settings-row")
    helps = page.locator(f"{PANEL} ha-settings-row [slot=heading] ha-icon-button.help")
    n = await rows.count()
    expect(n > 0 and n == await helps.count(), f"{n} rows, {await helps.count()} with an (i)")


async def check_page(browser: Browser, instance: Instance, api: Api, shots: Path | None) -> Checks:
    page = await _open(browser, instance, ADMIN)
    checks = Checks()

    async def every_page() -> None:
        for path in PAGES:
            await _goto(page, instance, path, "ha-card, ha-alert")
            try:
                await _header(page)
                await _frame(page, sub=False, page_id=path.split("/")[1])
                # The version only at the bottom of the setup overview
                about = page.locator(f"{PANEL} .about")
                if path == "setup/overview":
                    text = await about.inner_text()
                    expect(text.startswith(f"Storybox Plus {_version()} · commit "), text)
                else:
                    expect(await about.count() == 0, "a version line")
            except AssertionError as err:
                raise AssertionError(f"{path}: {err}") from err

    await checks.run(
        "every page: the four areas as Home Assistant's tabs, its own tab, stamp, refresh, "
        "integration; the version on the setup overview",
        every_page,
    )

    async def built_from_home_assistant() -> None:
        defined = await page.evaluate(
            """() => ["hass-tabs-subpage", "ha-tab-group", "ha-card", "ha-button", "ha-icon-button",
                     "ha-alert", "ha-switch", "ha-form", "ha-svg-icon", "ha-settings-row",
                     "ha-tooltip", "ha-filter-chip", "ha-control-select", "ha-badge"]
                     .filter((name) => !customElements.get(name))"""
        )
        expect(defined == [], f"not defined without loading: {defined}")
        own = await page.locator(PANEL).evaluate(
            """el => [...el.shadowRoot.querySelectorAll(
                 "button, select, ha-icon, ha-menu-button, ha-top-app-bar-fixed, .ov-card")].length"""
        )
        expect(own == 0, f"{own} home-made elements left")
        height = await page.locator(PANEL).evaluate("el => el.getBoundingClientRect().height")
        expect(height > 400, f"the page has no height: {height}")

    await checks.run(
        "only Home Assistant's elements, a page with a height", built_from_home_assistant
    )

    async def old_addresses() -> None:
        # Bookmarks and links of before: to the page that took the place
        for old, new in (
            ("#figures", "/storybox-plus/figures/list"),
            ("#listening", "/storybox-plus/listening/summary"),
            ("#preferences", "/storybox-plus/setup/preferences"),
            ("#boxes", "/storybox-plus/boxes/overview"),
            ("", "/storybox-plus/boxes/overview"),
            ("/figures", "/storybox-plus/figures/list"),
        ):
            await page.goto(f"{instance.base}/storybox-plus{old}")
            await page.wait_for_url(f"**{new}")
        # A change of the query alone: another view of the same box
        await _goto(page, instance, f"boxes/overview?key={demo_cloud.KIDS_BOX}", "ha-settings-row")
        await page.evaluate(
            """() => {
              history.pushState(null, "", location.pathname + location.search + "&view=battery");
              window.dispatchEvent(new CustomEvent("location-changed"));
            }"""
        )
        await page.locator(f"{PANEL} table.cycles").wait_for()
        await page.go_back()
        await page.locator(f"{PANEL} ha-settings-row").first.wait_for()

    await checks.run(
        "old addresses and a change of the query alone lead to the right page", old_addresses
    )

    async def boxes() -> None:
        await _goto(page, instance, "boxes/overview", ".batt-btn")
        cards = page.locator(f"{PANEL} .grid > ha-card:not(.mini-box)")
        expect(await cards.count() == 1, f"1 Toniebox 2 card expected, got {await cards.count()}")
        kids = await cards.nth(0).inner_text()
        for part in ("Kids room", "The Clever Fox", "Chapter 3 / 8", "64 %"):
            expect(part in kids, f"{part!r} missing on the box: {kids}")
        for part in ("Toniebox 2", "Online", "per full charge", "Firmware"):
            expect(part not in kids, f"{part!r} on the box: {kids}")
        head = cards.nth(0).locator(".card-header")
        dot = await head.locator(".dot.ok").get_attribute("aria-label")
        expect(dot == "Online", f"the dot's words: {dot}")
        # While an alarm is due the timers stay away; otherwise there are two
        timers = await cards.nth(0).locator(".sleep-pick ha-button").all_inner_texts()
        expect(timers in ([], ["30 min", "60 min"]), f"sleep timers: {timers}")
        minis = page.locator(f"{PANEL} .grid > ha-card.mini-box")
        expect(await minis.count() == 1, f"{await minis.count()} small cards")
        expect(await minis.locator(".card-header, .dot").count() == 0, "heading or dot")
        living = await minis.inner_text()
        for part in ("Living room", "Last seen", "Max. 100 %", "headphones 75 %", "LED Dimmed"):
            expect(part in living, f"{part!r} missing in the Toniebox 1 card: {living}")
        expect(await page.locator(f"{PANEL} img.box-pic").count() == 1, "box picture missing")
        if shots is not None:
            await page.set_viewport_size({"width": 1200, "height": 900})
            await page.wait_for_timeout(400)
            await page.screenshot(path=str(shots / "boxes.png"))
            await page.set_viewport_size({"width": 1200, "height": 820})

    await checks.run("boxes with live state, battery and a small Toniebox 1", boxes)

    async def box_settings() -> None:
        await _goto(page, instance, "boxes/overview", ".batt-btn")
        kids = page.locator(f"{PANEL} .grid > ha-card:not(.mini-box)").nth(0)
        await kids.locator("ha-icon-button[data-act^='boxset:']").click()
        await page.wait_for_url(f"**/boxes/overview?key={demo_cloud.KIDS_BOX}&view=settings")
        await page.locator(f"{PANEL} ha-settings-row").first.wait_for()
        await _until(lambda: _named(page, "Kids room"), "the box's name in the header")
        await _frame(page, sub=True)
        await _header(page)
        views = await page.locator(f"{PANEL} #views ha-tab-group-tab").all_inner_texts()
        expect(
            [v.strip() for v in views] == ["Settings", "Night mode", "Bedtimes", "Battery"],
            str(views),
        )
        await _rows_have_help(page)
        expect("Firmware" in await page.locator(f"{PANEL} #sheet").inner_text(), "no firmware")
        save = page.locator(f"{PANEL} ha-button#save")
        expect(await save.is_hidden(), "a save button with nothing changed")
        # The (i) beside a setting: a tap shows its explanation in Home Assistant's tooltip
        row = page.locator(f"{PANEL} ha-settings-row", has_text="Light ring brightness")
        await row.locator("ha-icon-button.help").click()
        tip = row.locator("ha-tooltip")
        await _until(lambda: tip.evaluate("el => el.open === true"), "the explanation")
        expect("0 % is off" in await tip.evaluate("el => el.textContent"), "wrong explanation")
        name = page.get_by_role("textbox", name="Name", exact=True)
        await name.fill("Nursery")
        await save.wait_for(state="visible")
        # Back to the saved value: nothing differs, the button goes
        await name.fill("Kids room")
        await save.wait_for(state="hidden")
        await name.fill("Nursery")
        ring = page.get_by_role("textbox", name="Light ring brightness")
        expect(await ring.input_value() == "60", await ring.input_value())
        await ring.fill("55")
        if shots is not None:
            await page.set_viewport_size({"width": 1200, "height": 1500})
            await page.wait_for_timeout(400)
            await page.screenshot(path=str(shots / "settings.png"))
            await page.set_viewport_size({"width": 1200, "height": 820})
        await _save(page)

        async def saved() -> bool:
            box = await _kids_box(api, instance)
            values = box["settings"]["values"]
            return bool(box["name"] == "Nursery" and values["lightring_brightness"] == 55)

        await _until(saved, "the name and the light ring saved")
        await _until(lambda: _named(page, "Nursery"), "the new name in the header")
        reply = await api.ws(
            instance.token,
            {
                "type": "storybox_plus/box/settings",
                "box_id": demo_cloud.KIDS_BOX,
                "name": "Kids room",
                "lightring_brightness": 60,
            },
        )
        expect(reply["success"], str(reply))
        # The Toniebox 1 has its settings only; the back arrow leads to the overview
        await page.locator(PANEL).evaluate(
            "el => el.shadowRoot.getElementById('frame').shadowRoot"
            ".querySelector('ha-icon-button-arrow-prev').click()"
        )
        await page.wait_for_url("**/storybox-plus/boxes/overview")
        living = page.locator(f"{PANEL} ha-card.mini-box ha-icon-button[data-act^='boxset:']")
        await living.click()
        await _until(lambda: _named(page, "Living room"), "the Toniebox 1's page")
        expect(await page.locator(f"{PANEL} #views").count() == 0, "views of a Toniebox 1")
        # Only a Toniebox 1 takes an entity that tells whether it is in the network
        presence = page.locator(f"{PANEL} ha-settings-row", has_text="Presence entity")
        await _until(
            lambda: presence.locator("ha-selector-entity").count(),
            "the presence entity's field",
        )
        await _until(
            lambda: page.get_by_role("textbox", name="Lag taken off the active time").count(),
            "the lag's field",
        )
        await _rows_have_help(page)

    await checks.run(
        "a box as a subpage: rows with their (i), one save button while changed, back arrow",
        box_settings,
    )

    async def night_mode() -> None:
        await _goto(
            page,
            instance,
            f"boxes/overview?key={demo_cloud.KIDS_BOX}&view=night",
            "ha-settings-row",
        )
        await _rows_have_help(page)
        await page.get_by_role("switch", name="Active").evaluate("el => el.click()")
        await page.get_by_role("textbox", name="Light ring at night").fill("12")
        if shots is not None:
            await page.set_viewport_size({"width": 1200, "height": 1000})
            await page.wait_for_timeout(400)
            await page.locator(f"{PANEL} ha-card").first.screenshot(path=str(shots / "night.png"))
            await page.set_viewport_size({"width": 1200, "height": 820})
        await _save(page)

        async def ring_follows() -> bool:
            night = (await _kids_box(api, instance))["night"]
            mode = night["mode"]
            return bool(
                mode
                and mode["enabled"]
                and mode["night"] == 12
                and mode["applied"] == night["phase"]
            )

        await _until(ring_follows, "the night mode saved and applied")
        await page.get_by_role("switch", name="Active").evaluate("el => el.click()")
        await _save(page)

        async def off() -> bool:
            return (await _kids_box(api, instance))["night"]["mode"]["enabled"] is False

        await _until(off, "the night mode switched off")

    await checks.run(
        "night mode: rows saved with the one button, the light ring follows", night_mode
    )

    async def bedtimes() -> None:
        await _goto(
            page, instance, f"boxes/overview?key={demo_cloud.KIDS_BOX}&view=bedtimes", ".item"
        )
        card = page.locator(f"{PANEL} ha-card", has_text="Bedtimes")
        text = await card.inner_text()
        for part in ("Bedtime", "every day", "Weekend lie-in"):
            expect(part in text, f"{part!r} missing in the bedtimes: {text}")
        # The integration arms the alarm half a minute after the box came online
        await _until(
            lambda: _has_text(page.locator(f"{PANEL} ha-alert.alarm-next"), "set on the box"),
            "the alarm armed on the box",
            seconds=90,
        )
        weekend = card.locator(".item", has_text="Weekend lie-in")
        await weekend.locator("ha-switch").click()

        async def switched(on: bool) -> bool:
            return (await _schedules(api, instance))["Weekend lie-in"]["enabled"] is on

        await _until(lambda: switched(True), "the bedtime switched on")
        await page.wait_for_timeout(300)
        await weekend.locator("ha-switch").click()
        await _until(lambda: switched(False), "the bedtime switched off")
        # A new one through the form
        await card.locator("ha-button[data-act^='sadd:']").click()
        form = page.locator(f"{PANEL} [data-form=schedule] > ha-form")
        await form.wait_for()
        await form.get_by_role("textbox", name="Name").fill("Nap")
        volume = form.get_by_role("textbox", name="Alarm volume")
        expect(await volume.input_value() == "50", await volume.input_value())
        await volume.fill("40")
        await page.wait_for_timeout(300)
        if shots is not None:
            await page.set_viewport_size({"width": 1200, "height": 2000})
            await page.wait_for_timeout(400)
            await card.screenshot(path=str(shots / "bedtime.png"))
            await page.set_viewport_size({"width": 1200, "height": 820})
        await page.locator(f"{PANEL} ha-button[data-act=ssave]").click()
        await _until(lambda: _has_schedule(api, instance, "Nap", True), "the new bedtime")
        nap = (await _schedules(api, instance))["Nap"]
        expect(nap["alarm_volume"] == 40 and len(nap["days"]) == 5, str(nap))
        # A row opens its form by keyboard; deleting asks first
        row = card.locator(".item .main", has_text="Nap")
        await row.focus()
        await page.keyboard.press("Enter")
        await page.locator(f"{PANEL} ha-button[data-act=sdel]").click()
        ask = page.locator(
            f"{PANEL} ha-alert[alert-type=warning]", has_text="Delete the bedtime Nap?"
        )
        await ask.wait_for()
        await ask.locator("ha-button[data-act=sdelok]").click()
        await _until(lambda: _has_schedule(api, instance, "Nap", False), "the bedtime deleted")

    await checks.run("bedtimes: next alarm, a switch per row, added and deleted", bedtimes)

    async def battery() -> None:
        await _goto(page, instance, "boxes/overview", ".batt-btn")
        level = page.locator(f"{PANEL} ha-button.batt-btn")
        # Keyboard: Enter on the level opens the box's battery
        await level.focus()
        await page.keyboard.press("Enter")
        await page.wait_for_url("**&view=battery")
        rows = page.locator(f"{PANEL} table.cycles tbody tr")
        await rows.first.wait_for()
        expect(await rows.count() == 7, f"7 charges expected, got {await rows.count()}")
        text = await page.locator(f"{PANEL} #sheet").inner_text()
        expect("per full charge" in text and "Lasts about" in text, text)

    await checks.run("the battery's level opens its charge history, also by keyboard", battery)

    async def figures_filter() -> None:
        await _goto(page, instance, "figures/list", ".item")
        count = page.locator(f"{PANEL} .count")
        expect((await count.inner_text()).strip() == "8 figures", await count.inner_text())
        await page.get_by_role("searchbox", name="Search figures and chapters").fill("dragon")
        await _until(lambda: _text_is(count, "1 of 8 figures"), "the search to filter")
        await page.get_by_role("searchbox", name="Search figures and chapters").fill("")
        await page.locator(f"{PANEL} ha-filter-chip[data-key=creative]").click()
        await _until(lambda: _text_is(count, "2 of 8 figures"), "the kind to filter")
        selected = await page.locator(f"{PANEL} ha-filter-chip[data-key=creative]").evaluate(
            "el => el.selected"
        )
        expect(selected, "the chip is not shown as chosen")
        await page.locator(f"{PANEL} ha-filter-chip[data-key=all]").click()
        await _until(lambda: _text_is(count, "8 figures"), "all figures again")

    await checks.run("figures: search over chapters and the kind filter", figures_filter)

    async def favourites() -> None:
        await _goto(page, instance, "figures/list", ".item")
        fox = page.locator(f"{PANEL} .item[data-key='fig-fox']")
        await fox.focus()
        await page.keyboard.press("Enter")
        await page.wait_for_url("**/figures/list?key=fig-fox")
        await _until(lambda: _named(page, "The Clever Fox"), "the figure's page")
        await _frame(page, sub=True)
        stars = page.locator(f"{PANEL} ha-icon-button.star")
        await stars.first.wait_for()
        expect(await stars.count() == 8, f"8 stars expected, got {await stars.count()}")
        expect(await page.locator(f"{PANEL} ha-icon-button.star.on").count() == 3, "3 favourites")
        await stars.nth(1).click()

        async def set_star() -> bool:
            fav = (await _library(api, instance))["fig-fox"]["favourites"]
            return bool(fav == {"mode": "only", "chapters": [0, 1, 2, 4]})

        await _until(set_star, "the new favourite in the integration")
        await page.locator(f"{PANEL} ha-icon-button.star.on").nth(3).wait_for()
        if shots is not None:
            await page.set_viewport_size({"width": 1200, "height": 900})
            await page.wait_for_timeout(400)
            await page.screenshot(path=str(shots / "figures.png"))
            await page.set_viewport_size({"width": 1200, "height": 820})
        # How the favourites play and the lock are settings of the figure
        await page.locator(f"{PANEL} #views ha-tab-group-tab[panel=settings]").click()
        await page.wait_for_url("**view=settings")
        await page.locator(f"{PANEL} ha-settings-row").first.wait_for()
        await _rows_have_help(page)
        settings = await page.locator(f"{PANEL} #sheet").inner_text()
        expect("How its favourites play" in settings, f"no mode of the favourites: {settings}")
        await page.get_by_role("switch", name="Locked to the household").evaluate(
            "el => el.click()"
        )
        await _save(page)

        async def saved() -> bool:
            fox = (await _library(api, instance))["fig-fox"]
            return bool(fox["favourites"]["mode"] == "only" and fox["locked"] is False)

        await _until(saved, "the figure unlocked, its favourites as they were")
        await page.get_by_role("switch", name="Locked to the household").evaluate(
            "el => el.click()"
        )
        await _save(page)

        async def locked() -> bool:
            return (await _library(api, instance))["fig-fox"]["locked"] is True

        await _until(locked, "the figure locked again")

    await checks.run(
        "a figure as a subpage: stars at once, its settings with the one save button", favourites
    )

    async def favourites_page() -> None:
        # Every chapter with a star on one page; a star taken off there is gone at once
        await _goto(page, instance, "figures/favourites", ".fav-fig")
        text = await page.locator(f"{PANEL} #sheet").inner_text()
        expect("The Clever Fox" in text and "Play on Kids room" in text, text)
        rows = page.locator(f"{PANEL} ol.chapters li")
        expect(await rows.count() == 4, f"4 favourites expected, got {await rows.count()}")
        expect(await page.locator(f"{PANEL} ol.chapters li.playable").count() == 4, "not playable")
        await rows.first.locator("ha-icon-button.star").click()

        async def taken_off() -> bool:
            fav = (await _library(api, instance))["fig-fox"]["favourites"]
            return bool(fav == {"mode": "only", "chapters": [1, 2, 4]})

        await _until(taken_off, "the star taken off in the integration")
        await _until(lambda: _count_is(rows, 3), "the row gone from the page")
        # A creative figure takes stars too
        await _goto(page, instance, "figures/list?key=fig-grandma&view=chapters", "ol.chapters")
        stars = page.locator(f"{PANEL} ha-icon-button.star")
        expect(await stars.count() > 0, "no stars on a creative figure")

    await checks.run("the favourites of all figures on one page", favourites_page)

    async def creative_settings() -> None:
        await _goto(page, instance, "figures/list?key=fig-grandma&view=settings", "ha-settings-row")
        name = page.get_by_role("textbox", name="Name of the figure")
        await name.fill("Renamed figure")
        await page.get_by_role("switch", name="Live mode").evaluate("el => el.click()")
        await page.get_by_role("switch", name="Shuffle when another figure replaces it").evaluate(
            "el => el.click()"
        )
        await _save(page)

        async def saved() -> bool:
            f = (await _library(api, instance))["fig-grandma"]
            return bool(f["name"] == "Renamed figure" and f["live"] and f["shuffle_on_swap"])

        await _until(saved, "name, live mode and shuffling saved")
        await _until(lambda: _named(page, "Renamed figure"), "the new name in the header")
        for message in (
            {
                "type": "storybox_plus/figure/update",
                "tonie_id": "fig-grandma",
                "name": "Grandma's Stories",
                "live": False,
            },
            {
                "type": "storybox_plus/figure/shuffle_on_swap",
                "tonie_id": "fig-grandma",
                "enabled": False,
            },
        ):
            reply = await api.ws(instance.token, message)
            expect(reply["success"], str(reply))

    await checks.run(
        "a creative figure: name, live mode and shuffling as settings", creative_settings
    )

    async def rearrange() -> None:
        await _goto(page, instance, "figures/list?key=fig-grandma&view=chapters", "ol.chapters")
        await page.locator(f"{PANEL} ha-button[data-act='edit:fig-grandma']").click()
        await page.locator(f"{PANEL} ha-icon-button[data-act='down:0']").click()
        await page.locator(f"{PANEL} ha-icon-button[data-act='remove:3']").click()
        if shots is not None:
            await page.wait_for_timeout(400)
            await page.locator(f"{PANEL} ha-card", has_text="Remove all chapters").screenshot(
                path=str(shots / "creative.png")
            )
        await page.locator(f"{PANEL} ha-button[data-act=chsave]").click()

        async def saved() -> bool:
            titles = [
                c["title"] for c in (await _library(api, instance))["fig-grandma"]["chapters"]
            ]
            return titles == ["When I Was Little", "The Red Bicycle", "Songs from the Kitchen"]

        await _until(saved, "the new order in the integration")
        await page.locator(f"{PANEL} ha-button[data-act='edit:fig-grandma']").wait_for()

    await checks.run("chapters of a creative figure rearranged and removed", rearrange)

    async def upload() -> None:
        await _goto(page, instance, "figures/list?key=fig-empty&view=add", "ha-card")
        text = await page.locator(f"{PANEL} #sheet").inner_text()
        # Without the Media Fetcher app and Piper their cards say what is needed
        expect("Needs the Media Fetcher app." in text and "Needs a voice." in text, text)
        async with page.expect_file_chooser() as chooser:
            await page.locator(f"{PANEL} ha-button[data-act='upload:fig-empty']").click()
        await (await chooser.value).set_files(
            {"name": "Morning song.mp3", "mimeType": "audio/mpeg", "buffer": b"ID3" + bytes(256)}
        )

        async def added() -> bool:
            chapters = (await _library(api, instance))["fig-empty"]["chapters"]
            return [c["title"] for c in chapters] == ["Morning song"]

        await _until(added, "the uploaded chapter in the integration")
        await _goto(page, instance, "figures/list?key=fig-empty", "ol.chapters")
        await page.get_by_text("Morning song").wait_for()

    await checks.run(
        "an uploaded file becomes a chapter; links and texts say what they need", upload
    )

    async def clear_all() -> None:
        await _goto(page, instance, "figures/list?key=fig-empty", "ol.chapters")
        await page.locator(f"{PANEL} ha-button[data-act='edit:fig-empty']").click()
        rows = page.locator(f"{PANEL} ol.chapters li")
        before = await rows.count()
        expect(before > 0, "the figure has no chapter to remove")
        ask = page.locator(f"{PANEL} .clear-ask")
        await page.locator(f"{PANEL} ha-button[data-act=clearall]").click()
        await _until(lambda: _has_text(ask, "Really remove all"), "the first question")
        await page.locator(f"{PANEL} ha-button[data-act=clearyes]").click()
        await _until(lambda: _has_text(ask, "keeps no copy"), "the second question")
        await page.locator(f"{PANEL} ha-button[data-act=clearno]").click()
        await ask.wait_for(state="detached")
        expect(await rows.count() == before, "chapters removed without both answers")
        await page.locator(f"{PANEL} ha-button[data-act=clearall]").click()
        await page.locator(f"{PANEL} ha-button[data-act=clearyes]").click()
        await _until(lambda: _has_text(ask, "keeps no copy"), "the second question again")
        await page.locator(f"{PANEL} ha-button[data-act=clearyes]").click()
        await _until(lambda: _count_is(rows, 0), "the list emptied")
        # Nothing is sent before saving: cancelled, the figure keeps its chapters
        await page.locator(f"{PANEL} ha-button[data-act=chcancel]").click()
        chapters = (await _library(api, instance))["fig-empty"]["chapters"]
        expect(len(chapters) == before, f"chapters changed without saving: {chapters}")

    await checks.run("removing all chapters asks twice and waits for saving", clear_all)

    async def tunes() -> None:
        await _goto(page, instance, "figures/list?key=fig-empty&view=tune", "ha-card")
        await page.locator(f"{PANEL} ha-button[data-act='tuneon:fig-empty']").click()

        async def laid_on() -> bool:
            lib = await api.ws(instance.token, {"type": "storybox_plus/library"})
            return any("fig-empty" in t["assigned"] for t in lib["result"]["tunes"])

        await _until(laid_on, "the Tune laid on")
        await page.get_by_text("Tune on it:").wait_for()
        await page.locator(f"{PANEL} ha-button[data-act='tuneoff:fig-empty']").click()
        await _until(lambda: _negate(laid_on), "the Tune taken off")
        # The page of the Tunes lists them
        await _goto(page, instance, "figures/tunes", ".item")
        expect("Bought Tunes" in await page.locator(f"{PANEL} #sheet").inner_text(), "no list")

    await checks.run("Tunes: one laid on a creative figure and taken off again", tunes)

    async def voucher_and_code() -> None:
        await _goto(page, instance, "figures/tunes", ".item")
        code = page.get_by_role("textbox", name="Voucher code")
        await code.fill("WRONG")
        await page.locator(f"{PANEL} ha-button[data-act^='voucher:']").click()
        # An error reads one line by its kind, what Home Assistant said behind its (i)
        alert = page.locator(f"{PANEL} ha-alert[alert-type=error]")
        await alert.wait_for()
        line = await alert.evaluate("el => el.firstChild.textContent")
        expect(line == "The Tonie cloud did not answer or refused it.", line)
        said = await alert.locator("ha-tooltip").evaluate("el => el.textContent")
        expect(said.startswith("Message:") and "voucher_not_found" in said, said)
        await code.fill("DEMO-VOUCHER")
        await page.locator(f"{PANEL} ha-button[data-act^='voucher:']").click()
        await page.locator(f"{PANEL} ha-alert[alert-type=success]").first.wait_for()

        async def new_tune() -> bool:
            lib = await api.ws(instance.token, {"type": "storybox_plus/library"})
            return any(t["title"] == "Moon Lullabies" for t in lib["result"]["tunes"])

        await _until(new_tune, "the voucher's Tune")
        await page.get_by_role("textbox", name="Content code").fill("CARD-123")
        await page.locator(f"{PANEL} ha-button[data-act=codeadd]").click()

        async def from_card() -> bool:
            lib = await _library(api, instance)
            return any(
                c["title"] == "Song from a card" for f in lib.values() for c in f["chapters"]
            )

        await _until(from_card, "the content from the code")

    await checks.run(
        "a wrong voucher reads one line with the message behind the (i); a voucher and a code",
        voucher_and_code,
    )

    async def listening() -> None:
        await _goto(page, instance, "listening/summary", ".total")
        text = await page.locator(f"{PANEL} #sheet").inner_text()
        for part in (
            "Listening time",
            "Most played",
            "Most played chapters",
            "Favourites",
            "of the listening time went to favourite chapters",
            "Heard a lot, no star yet",
            "Placed most often",
            "Listening time of the Toniebox 2",
            "Active time of the Toniebox 1",
        ):
            expect(part in text, f"{part!r} missing")
        expect("The Clever Fox" in text, "the most played figure is missing")
        # Where the numbers come from is behind the (i) of the total
        note = page.locator(f"{PANEL} ha-card", has_text="Listening time").first.locator(
            "ha-tooltip"
        )
        expect(
            "counts the listening time itself" in await note.evaluate("el => el.textContent"),
            "note",
        )
        # The active time stands apart, with why it is no listening time behind its (i)
        active = page.locator(f"{PANEL} ha-card", has_text="Active time of the Toniebox 1")
        expect("Living room" in await active.inner_text(), "the Toniebox 1's active time")
        expect(
            "not listening time"
            in await active.locator("ha-tooltip").evaluate("el => el.textContent"),
            "the active time's note",
        )
        placed = page.locator(f"{PANEL} ol.placed li")
        first = await placed.first.inner_text()
        expect("Moon" in first and "\u00d7" in first, f"most placed: {first}")
        compare = await page.locator(f"{PANEL} .compare").inner_text()
        expect("compared with the 30 days before" in compare, f"no comparison: {compare}")
        # The period: Home Assistant's segmented control
        await (
            page.locator(f"{PANEL} ha-control-select#range")
            .get_by_role("radio", name="All")
            .click()
        )
        await page.get_by_text("since", exact=False).first.wait_for()
        await (
            page.locator(f"{PANEL} ha-control-select#range")
            .get_by_role("radio", name="30 days")
            .click()
        )
        await page.locator(f"{PANEL} .compare").wait_for()
        if shots is not None:
            await page.set_viewport_size({"width": 1200, "height": 2900})
            await page.wait_for_timeout(400)
            await page.screenshot(path=str(shots / "listening.png"))
            await page.set_viewport_size({"width": 1200, "height": 820})
        await _goto(page, instance, "listening/times", ".chart")
        label = await page.locator(f"{PANEL} svg.chart").get_attribute("aria-label")
        expect(label is not None and label.startswith("Listening time on 30 days"), str(label))
        cells = page.locator(f"{PANEL} .heatmap .hm-cell[aria-label]")
        expect(await cells.count() == 7 * 24, f"the heatmap has {await cells.count()} cells")
        expect(await page.locator(f"{PANEL} .chart rect.fill").count() > 15, "too few bars")

    await checks.run("listening: summary with the note behind its (i), times with words", listening)

    async def refresh_and_integration() -> None:
        # Every message the page sends is noted and the integration's answers are held
        # back a little, so the spinning refresh button can be seen
        wrap = """() => {
              const conn = document.querySelector("home-assistant").hass.connection;
              window.__sent = [];
              if (conn.__wrapped) return;
              conn.__wrapped = true;
              const send = conn.sendMessagePromise.bind(conn);
              conn.sendMessagePromise = async (msg) => {
                window.__sent.push(msg.type);
                if (String(msg.type).startsWith("storybox_plus/")) {
                  await new Promise((r) => setTimeout(r, 700));
                }
                return send(msg);
              };
            }"""
        stamp = page.locator(f"{PANEL} #stamp")
        refresh = page.locator(f"{PANEL} ha-icon-button#refresh")
        for path, what, message in (
            ("boxes/overview", ".batt-btn", "storybox_plus/overview"),
            ("figures/list", ".item", "storybox_plus/library"),
            ("listening/summary", ".total", "storybox_plus/analytics"),
        ):
            await _goto(page, instance, path, what)
            await page.evaluate(wrap)
            await page.evaluate("window.__kept = true")
            await _until(lambda: _stamped(stamp), f"{path}: the stamp")
            before = (await stamp.inner_text()).strip()
            await page.wait_for_timeout(1100)
            await page.evaluate("window.__sent = []")
            await refresh.click()
            await _until(
                lambda: refresh.evaluate("(el) => el.classList.contains('spin')"),
                f"{path}: the refresh button to spin",
                seconds=2,
            )
            await _until(lambda before=before: _stamp_after(stamp, before), f"{path}: a new stamp")
            sent = await page.evaluate("window.__sent")
            expect(message in sent, f"{path}: {message} not asked again: {sent}")
            expect(await page.evaluate("window.__kept === true"), "refresh reloaded the page")
        await page.locator(f"{PANEL} ha-icon-button#integration").click()
        await page.wait_for_url("**/config/integrations/integration/storybox_plus")
        await page.locator("ha-config-integration-page").wait_for(timeout=20000)
        expect(await page.evaluate("window.__kept === true"), "the integration button reloaded")

    await checks.run(
        "refresh fetches again, spins and moves the stamp; the integration button opens its page",
        refresh_and_integration,
    )

    async def setup() -> None:
        await _goto(page, instance, "setup/overview", ".item")
        steps = page.locator(f"{PANEL} ha-card .item[role=button]")
        expect(await steps.count() == 3, f"{await steps.count()} steps")
        done = await page.locator(f"{PANEL} .step.done[aria-label=Done]").count()
        expect(done == 3, f"{done} steps done")
        await steps.nth(1).click()
        await page.wait_for_url("**/storybox-plus/setup/household")
        # The household renamed through its row
        await page.locator(f"{PANEL} ha-settings-row").first.wait_for()
        await _rows_have_help(page)
        text = await page.locator(f"{PANEL} #sheet").inner_text()
        for part in ("Members (3)", "Alex Muster", "alex@example.com", "Owner", "Limited access"):
            expect(part in text, f"{part!r} missing on the household: {text}")
        await page.get_by_role("textbox", name="Name of the household").fill("Our flat")
        await _save(page)

        async def renamed() -> bool:
            return (await _entry(api, instance))["households"][0]["name"] == "Our flat"

        await _until(renamed, "the household renamed")
        await api.ws(
            instance.token,
            {"type": "storybox_plus/household/rename", "household_id": "home", "name": "Home"},
        )
        # Preferences: rows with their (i), saved with the one button
        await _goto(page, instance, "setup/preferences", "ha-settings-row")
        await _rows_have_help(page)
        text = await page.locator(f"{PANEL} #sheet").inner_text()
        expect("Backend version" in text and "tested" in text and "tested with" not in text, text)
        expect("How favourites play" in text, text)
        if shots is not None:
            await page.set_viewport_size({"width": 1200, "height": 1000})
            await page.wait_for_timeout(400)
            await page.screenshot(path=str(shots / "preferences.png"))
            await page.set_viewport_size({"width": 1200, "height": 820})
        mark = page.get_by_role(
            "switch", name="Mark notifications as read in the cloud once passed on"
        )
        await mark.evaluate("el => el.click()")
        await _save(page)

        async def marks() -> bool:
            return bool((await _entry(api, instance))["preferences"]["mark_read"])

        await _until(marks, "the preference saved")
        await mark.evaluate("el => el.click()")
        await _save(page)
        await _until(lambda: _negate(marks), "the preference saved back")

    await checks.run("setup: three steps done, the household renamed, a preference saved", setup)

    async def numbers_in_german() -> None:
        # A German page writes numbers as German does and takes a comma back
        await page.evaluate("localStorage.setItem('selectedLanguage', JSON.stringify('de'))")
        try:
            await _goto(
                page,
                instance,
                f"boxes/overview?key={demo_cloud.KIDS_BOX}&view=battery",
                "table.cycles",
            )
            text = await page.locator(f"{PANEL} #sheet").inner_text()
            expect(" h pro Ladung" in text, text)
            per_full = re.search(r"etwa (\S+) h pro Ladung", text)
            expect(per_full is not None and "," in per_full[1], f"not German: {text}")
            await _goto(page, instance, "boxes/overview", ".batt-btn")
            area = await page.locator(PANEL).evaluate(
                "el => el.shadowRoot.getElementById('frame').tabs.map((t) => t.name)"
            )
            expect(area == ["Boxen", "Figuren", "Hörzeit", "Einrichtung"], str(area))
            await _goto(
                page,
                instance,
                f"boxes/overview?key={demo_cloud.KIDS_BOX}&view=settings",
                "ha-settings-row",
            )
            ring = page.get_by_role("textbox", name="Helligkeit des Lichtrings")
            await ring.fill("57,0")
            await _save(page)

            async def saved() -> bool:
                values = (await _kids_box(api, instance))["settings"]["values"]
                return bool(values["lightring_brightness"] == 57)

            await _until(saved, "57,0 saved as 57")
        finally:
            await page.evaluate("localStorage.setItem('selectedLanguage', JSON.stringify('en'))")
            await api.ws(
                instance.token,
                {
                    "type": "storybox_plus/box/settings",
                    "box_id": demo_cloud.KIDS_BOX,
                    "lightring_brightness": 60,
                },
            )
            await page.reload()

    await checks.run(
        "numbers in German on the page and in the fields, a comma typed back", numbers_in_german
    )

    async def extras() -> None:
        await _goto(page, instance, "boxes/overview", ".batt-btn")
        kids = page.locator(f"{PANEL} .grid > ha-card").nth(0)
        card = await kids.inner_text()
        expect("Headphones, battery 80 %" in card, "headphones missing on the card")
        controls = kids.locator(".controls")
        for act in ("previous", "pause", "next", "volume:8", "volume:10"):
            expect(await controls.locator(f"[data-act$=':{act}']").count() == 1, f"button {act}")
        # The demo's bedtime alarm is due: the sleep timer stays out of its way
        expect(await controls.locator("[data-act*=':sleep']").count() == 0, "sleep timer buttons")
        await controls.locator("[data-act$=':pause']").click()
        await page.wait_for_timeout(600)
        expect(await kids.locator("ha-alert[alert-type=error]").count() == 0, "the command failed")
        # Repeat: one button through off, the whole figure, one chapter
        again = controls.locator("ha-icon-button.repeat")
        for pressed, label in (
            ("false", "Repeat: off"),
            ("true", "Repeat: the whole figure"),
            ("true", "Repeat: this chapter"),
            ("false", "Repeat: off"),
        ):
            await _until(
                lambda label=label: _attr(again, "label", label), f"the repeat button says {label}"
            )
            expect(await again.get_attribute("aria-pressed") == pressed, f"pressed at {label}")
            await again.click()
        await _until(lambda: _attr(again, "label", "Repeat: the whole figure"), "repeat set")
        await again.click()
        await again.click()
        await _until(lambda: _attr(again, "label", "Repeat: off"), "repeat off again")
        # The chapter list opens in Home Assistant's dialog; Escape closes it, a chapter
        # chosen there closes it too and plays
        await controls.locator("[data-act^='tracks:']").click()
        rows = page.locator(f"{PANEL} #overlay ha-dialog ol.tracks li")
        await rows.first.wait_for(timeout=3000)
        expect(await rows.count() > 1, "chapters in the list")
        expect(await page.locator(f"{PANEL} #overlay li.current").count() == 1, "current chapter")
        await page.keyboard.press("Escape")
        await _until(lambda: _gone(page.locator(f"{PANEL} #overlay ha-dialog")), "Escape")
        await controls.locator("[data-act^='tracks:']").click()
        await rows.last.wait_for(timeout=3000)
        # A star in the list marks the chapter; the list stays open
        star = rows.nth(5).locator("ha-icon-button.star")
        expect(await star.get_attribute("aria-pressed") == "false", "chapter 6 has a star")
        await star.click()
        await _until(
            lambda: _attr(rows.nth(5).locator("ha-icon-button.star"), "aria-pressed", "true"),
            "the star in the list",
        )
        expect(await page.locator(f"{PANEL} #overlay ha-dialog").count() == 1, "the list closed")
        await rows.nth(5).locator("ha-icon-button.star").click()
        await _until(
            lambda: _attr(rows.nth(5).locator("ha-icon-button.star"), "aria-pressed", "false"),
            "the star taken off in the list",
        )
        await rows.last.click()
        await _until(lambda: _gone(page.locator(f"{PANEL} #overlay ha-dialog")), "a chapter chosen")
        # The chapter that plays shows its star beside its title; the favourites steer
        # the figure, and a button lets it play everything until it is taken off
        now_star = kids.locator("ha-icon-button.now-star")
        expect(await now_star.get_attribute("aria-pressed") == "true", "the playing chapter's star")
        expect("Only favourites" in await kids.inner_text(), "the mode at work is not shown")
        everything = kids.locator("ha-icon-button.fav-all")
        await everything.click()
        await _until(
            lambda: _attr(kids.locator("ha-icon-button.fav-all"), "aria-pressed", "true"),
            "everything today",
        )
        expect("Everything today" in await kids.inner_text(), "everything today is not shown")
        await kids.locator("ha-icon-button.fav-all").click()
        await _until(
            lambda: _attr(kids.locator("ha-icon-button.fav-all"), "aria-pressed", "false"),
            "the favourites steer again",
        )
        await page.wait_for_timeout(600)
        expect(await kids.locator("ha-alert[alert-type=error]").count() == 0, "the jump failed")
        expect("70 %" in card, f"volume not in percent: {card}")
        await controls.locator("[data-act$=':volume:10']").click()
        await controls.locator("[data-act$=':volume:11']").wait_for(timeout=3000)
        await controls.locator("[data-act$=':volume:11']").click()
        await controls.locator("[data-act$=':volume:12']").wait_for(timeout=3000)
        await _until(
            lambda: _has_text(kids.locator(".facts"), "90 %"),
            "the volume the box reports after two presses",
        )

    await checks.run("player buttons and headphones on the box's card", extras)

    async def counting() -> None:
        # Late: switching counting off deletes the listening times the other checks use
        await _goto(page, instance, "setup/preferences", "ha-settings-row")
        switch = page.get_by_role("switch", name="Count listening time")
        await switch.evaluate("el => el.click()")
        await _save(page)

        async def counts(on: bool) -> bool:
            return (await _entry(api, instance)).get("preferences", {}).get("analytics") is on

        await _until(lambda: counts(False), "counting switched off", seconds=15)
        await page.wait_for_timeout(5000)
        await _goto(page, instance, "setup/preferences", "ha-settings-row")
        await page.get_by_role("switch", name="Count listening time").evaluate("el => el.click()")
        await _save(page)
        await _until(lambda: counts(True), "counting switched on", seconds=15)
        await page.wait_for_timeout(5000)

    await checks.run("counting switched off and on again with the save button", counting)

    async def no_page_for_users() -> None:
        token = await api.login(*USER)
        for message in (
            {"type": "storybox_plus/overview"},
            {"type": "storybox_plus/library"},
            {
                "type": "storybox_plus/favourites/set",
                "tonie_id": "fig-fox",
                "chapters": [],
                "mode": None,
            },
            {"type": "storybox_plus/favourites/star", "tonie_id": "fig-fox", "chapter": 0},
            {
                "type": "storybox_plus/box/favourites",
                "box_id": demo_cloud.KIDS_BOX,
                "suspended": True,
            },
        ):
            reply = await api.ws(token, message)
            expect(not reply["success"] and reply["error"]["code"] == "unauthorized", str(reply))
        panels = await api.ws(token, {"type": "get_panels"})
        expect("storybox-plus" not in panels["result"], "the page is offered to a user")

    await checks.run(
        "users without administrator rights get neither page nor commands", no_page_for_users
    )

    async def dashboard_card() -> None:
        # The card on a dashboard, seen by a user without administrator rights: as it
        # comes (no configuration: every Toniebox 2), with parts left out, and in a
        # sections view with one, three and six rows, where it shows what fits
        registry = await api.ws(instance.token, {"type": "config/entity_registry/list"})
        player = next(
            e["entity_id"]
            for e in registry["result"]
            if e["platform"] == "storybox_plus" and e["entity_id"].startswith("media_player.")
        )
        plain = {"type": "custom:storybox-plus-card"}
        slim_config = {
            **plain,
            "entity": player,
            "show_battery": False,
            "show_picture": False,
            "show_next_alarm": False,
            "show_controls": False,
        }
        created = await api.ws(
            instance.token,
            {
                "type": "lovelace/dashboards/create",
                "url_path": "storybox-test",
                "title": "Storybox test",
                "mode": "storage",
            },
        )
        expect(created["success"], str(created))
        saved = await api.ws(
            instance.token,
            {
                "type": "lovelace/config/save",
                "url_path": "storybox-test",
                "config": {
                    "views": [
                        {"title": "Kids", "path": "kids", "cards": [plain, slim_config]},
                        {
                            "title": "Sizes",
                            "path": "sizes",
                            "type": "sections",
                            "sections": [
                                {
                                    "type": "grid",
                                    "cards": [
                                        {**plain, "grid_options": {"columns": 12, "rows": rows}}
                                        for rows in (1, 3, 6)
                                    ]
                                    + [plain, {**plain, "grid_options": {"columns": 6, "rows": 1}}],
                                }
                            ],
                        },
                    ]
                },
            },
        )
        expect(saved["success"], str(saved))
        # The card is a dashboard resource, once
        resources = await api.ws(instance.token, {"type": "lovelace/resources"})
        ours = [r for r in resources["result"] if "storybox-plus-card.js?v=" in r["url"]]
        expect(len(ours) == 1 and ours[0]["type"] == "module", f"resources: {resources['result']}")
        user = await _open(browser, instance, USER, path="/storybox-test/kids")
        try:
            card = user.locator("storybox-plus-card ha-card").first
            await card.locator(".card-header").wait_for(timeout=90000)
            text = await card.inner_text()
            for part in ("Kids room", "The Clever Fox", "Headphones, battery 80 %", "Next alarm"):
                expect(part in text, f"{part!r} missing on the card: {text}")
            # Home Assistant's own word for the state
            expect("Playing" in text or "Paused" in text, f"no state on the card: {text}")
            # Neither the settings nor the charge history: no cog, the battery is no button
            expect(await card.locator("[data-act^='boxset:'], .batt-btn").count() == 0, text)
            expect(await card.locator(".card-header .batt").count() == 1, "battery not in the head")
            # Exactly its controls, each an action of the media player, and they work
            acts = await card.locator("[data-act]").evaluate_all(
                """els => els.map((el) => {
                  const parts = el.getAttribute('data-act').split(':');
                  return ['star', 'tracks'].includes(parts[0]) ? parts[0] : parts[2];
                })"""
            )
            expect(
                set(acts)
                <= {
                    "previous",
                    "play",
                    "pause",
                    "next",
                    "volume_down",
                    "volume_up",
                    "sleep",
                    "sleep_clear",
                    "star",
                    "tracks",
                },
                f"other buttons on the card: {acts}",
            )
            # The star of the chapter that plays: every user may set it and take it off
            star = card.locator("ha-icon-button.now-star")
            expect(await star.get_attribute("aria-pressed") == "true", "no star on the card")
            await star.click()
            await _until(
                lambda: _attr(card.locator("ha-icon-button.now-star"), "aria-pressed", "false"),
                "the star taken off on the card",
            )
            await card.locator("ha-icon-button.now-star").click()
            await _until(
                lambda: _attr(card.locator("ha-icon-button.now-star"), "aria-pressed", "true"),
                "the star set on the card",
            )
            # The list of chapters opens in Home Assistant's dialog above the dashboard: a
            # star there marks a chapter, a chapter chosen plays and closes the list
            await card.locator("[data-act^='tracks:']").click()
            rows = user.locator("storybox-plus-card #overlay ha-dialog ol.tracks li")
            await rows.first.wait_for(timeout=5000)
            expect(await rows.count() == 8, f"8 chapters expected, got {await rows.count()}")
            expect(
                await user.locator("storybox-plus-card #overlay li.current").count() == 1,
                "the chapter that plays is not marked",
            )
            row_star = rows.nth(6).locator("ha-icon-button.star")
            expect(await row_star.get_attribute("aria-pressed") == "false", "chapter 7 has a star")
            await row_star.click()
            await _until(
                lambda: _attr(rows.nth(6).locator("ha-icon-button.star"), "aria-pressed", "true"),
                "the star in the card's list",
            )
            await rows.nth(6).locator("ha-icon-button.star").click()
            await _until(
                lambda: _attr(rows.nth(6).locator("ha-icon-button.star"), "aria-pressed", "false"),
                "the star taken off in the card's list",
            )
            if shots is not None:
                await user.wait_for_timeout(400)
                await user.screenshot(path=str(shots / "card-chapters.png"))
            await rows.nth(3).click()
            await _until(
                lambda: _gone(user.locator("storybox-plus-card #overlay ha-dialog")),
                "a chapter chosen on the card",
            )
            await user.wait_for_timeout(600)
            expect(await card.locator("ha-alert[alert-type=error]").count() == 0, "the jump failed")
            volume = card.locator(".fact.vol")
            before = await volume.inner_text()
            await card.locator("[data-act$=':volume_up']").click()

            async def answered() -> bool:
                now = await volume.inner_text()
                return now != before and "%" in now

            await _until(answered, "the volume the box reports after a press")
            await card.locator("[data-act$=':pause'], [data-act$=':play']").first.click()
            await user.wait_for_timeout(600)
            expect(await card.locator("ha-alert[alert-type=error]").count() == 0, "a button failed")
            slim = user.locator("storybox-plus-card ha-card").nth(1)
            await slim.locator(".card-header").wait_for()
            slim_text = await slim.inner_text()
            expect("Next alarm" not in slim_text and "The Clever Fox" in slim_text, slim_text)
            for left_out in (".batt", ".box-pic", ".controls"):
                expect(await slim.locator(left_out).count() == 0, f"{left_out} on the slim card")
            # A failed call reads the line only, without Home Assistant's message
            line = await user.evaluate(
                """() => {
                  const card = document.createElement("storybox-plus-card");
                  const box = document.createElement("div");
                  box.innerHTML = card._errHtml(card._error({ code: "alarm_due", message: "boom" }));
                  return box.textContent;
                }"""
            )
            expect(line == "An alarm of a bedtime is set; a sleep timer would cancel it.", line)
            # The card picker knows the card once, it needs no configuration, and its
            # editor has a text for every field
            offered = await user.evaluate(
                """() => {
                  const element = customElements.get("storybox-plus-card");
                  const form = element.getConfigForm();
                  const names = (schema) => schema.flatMap((f) => f.schema ? names(f.schema) : [f.name]);
                  return {
                    picker: (window.customCards || []).filter((c) => c.type === "storybox-plus-card").length,
                    stub: element.getStubConfig(),
                    fields: names(form.schema),
                    labels: names(form.schema).map((name) => form.computeLabel({ name })),
                  };
                }"""
            )
            expect(offered["picker"] == 1, "the card is not in the card picker once")
            expect(offered["stub"] == {}, f"the card needs a configuration: {offered['stub']}")
            expect(len(offered["fields"]) == 12, f"editor fields: {offered['fields']}")
            expect(
                not set(offered["fields"]) & set(offered["labels"]),
                f"an editor field without its text: {offered['labels']}",
            )
            # The editor shows what the card does (a part not in the configuration is
            # on, the night mode off) and writes only what differs from that
            edited = await user.evaluate(
                """async () => {
                  const editor = customElements.get("storybox-plus-card").getConfigElement();
                  editor.hass = document.querySelector("home-assistant").hass;
                  editor.setConfig({ type: "custom:storybox-plus-card" });
                  const form = editor.querySelector("ha-form");
                  const shown = { ...form.data };
                  let config = null;
                  editor.addEventListener("config-changed", (e) => { config = e.detail.config; });
                  form.dispatchEvent(new CustomEvent("value-changed", {
                    detail: { value: { ...shown, show_battery: false, show_night_mode: true, title: "" } },
                  }));
                  return { shown, config, fields: form.schema.length };
                }"""
            )
            expect(
                edited["shown"]["show_playback"] is True
                and edited["shown"]["show_controls"] is True
                and edited["shown"]["show_night_mode"] is False
                and edited["shown"]["size"] == "auto",
                f"the editor does not show the defaults: {edited['shown']}",
            )
            expect(
                edited["config"]
                == {
                    "type": "custom:storybox-plus-card",
                    "show_battery": False,
                    "show_night_mode": True,
                },
                f"the editor wrote {edited['config']}",
            )
            # A title names the one box; a box that is none of ours says so
            odd = await user.evaluate(
                """async (player) => {
                  const hass = document.querySelector("home-assistant").hass;
                  const make = async (config) => {
                    const card = document.createElement("storybox-plus-card");
                    card.setConfig({ type: "custom:storybox-plus-card", ...config });
                    document.body.appendChild(card);
                    card.hass = hass;
                    await new Promise((r) => setTimeout(r, 300));
                    const text = card.shadowRoot.textContent;
                    card.remove();
                    return text;
                  };
                  return [await make({ entity: player, title: "Bedtime story" }), await make({ entity: "sun.sun" })];
                }""",
                player,
            )
            expect("Bedtime story" in odd[0] and "Kids room" not in odd[0], odd[0])
            expect("This is no Toniebox 2 of Storybox Plus." in odd[1], odd[1])
            # Laid out by its width: side by side in half of a wall display (748 x 262 px),
            # stacked and still whole in a third of it (370 x 262 px), compact in a quarter
            for width, height, columns in ((748, 262, 2), (370, 262, 1), (200, 0, 1)):
                size = await user.evaluate(
                    """async ([player, w, h]) => {
                      const box = document.createElement("div");
                      box.id = "card-size";
                      box.style.cssText = `position:fixed;left:0;top:0;width:${w}px;` +
                        (h ? `height:${h}px;` : "") + "z-index:99";
                      const card = document.createElement("storybox-plus-card");
                      card.setConfig({ type: "custom:storybox-plus-card", entity: player });
                      box.appendChild(card);
                      document.body.appendChild(box);
                      card.hass = document.querySelector("home-assistant").hass;
                      await new Promise((r) => setTimeout(r, 1500));
                      const root = card.shadowRoot;
                      return {
                        content: root.querySelector(".content").scrollHeight,
                        columns: getComputedStyle(root.querySelector(".box-body"))
                          .gridTemplateColumns.split(" ").length,
                        buttons: root.querySelectorAll(".controls ha-icon-button").length,
                      };
                    }""",
                    [player, width, height],
                )
                if shots is not None and width == 748:
                    await user.locator("#card-size").screenshot(path=str(shots / "card-wide.png"))
                await user.evaluate("document.getElementById('card-size').remove()")
                expect(size["columns"] == columns, f"{width} px: {size}")
                expect(size["buttons"] == 6, f"{width} px without its buttons: {size}")
                if height:
                    expect(size["content"] <= height, f"{width} x {height} px overflows: {size}")
            if shots is not None:
                # Without the mark of the button pressed last
                await user.mouse.move(0, 0)
                await user.evaluate("document.activeElement?.blur?.()")
                await user.wait_for_timeout(400)
                await card.screenshot(path=str(shots / "card.png"))
            # What does not fit is left out: one row, three rows, six rows; no rows; half as wide
            await user.goto(f"{instance.base}/storybox-test/sizes")
            cards = user.locator("storybox-plus-card")
            await cards.nth(2).locator(".card-header").wait_for(timeout=30000)
            await cards.nth(4).locator(".compact").wait_for()
            await user.wait_for_timeout(500)
            forms = await cards.evaluate_all(
                """els => els.map((el) => {
                  const root = el.shadowRoot;
                  const card = root.querySelector("ha-card");
                  const content = root.querySelector(".content");
                  const sub = root.querySelector(".compact .sub");
                  let cut = null;
                  if (sub) {
                    const probe = document.createElement("span");
                    probe.className = sub.className;
                    probe.style.cssText = "position:absolute;visibility:hidden;overflow:visible;width:auto;display:inline-block";
                    probe.textContent = sub.textContent;
                    sub.parentElement.appendChild(probe);
                    cut = probe.getBoundingClientRect().width > sub.getBoundingClientRect().width;
                    probe.remove();
                  }
                  return {
                    form: root.querySelector(".compact") ? "small" : root.querySelector(".controls") ? "large" : "medium",
                    fits: content.getBoundingClientRect().bottom <= card.getBoundingClientRect().bottom + 1,
                    spare: card.clientHeight - content.scrollHeight,
                    playback: !!root.querySelector(".play"),
                    cut,
                    text: sub ? sub.textContent : "",
                  };
                })"""
            )
            expect(
                [f["form"] for f in forms] == ["small", "medium", "large", "large", "small"],
                f"the forms by their rows: {forms}",
            )
            expect(all(f["fits"] for f in forms), f"a card that cuts off what it shows: {forms}")
            expect(forms[1]["playback"], "the medium card does not say what plays")
            expect(
                abs(forms[3]["spare"]) <= 2, f"a card without rows is off its content: {forms[3]}"
            )
            for index in (0, 4):
                expect(
                    forms[index]["cut"] is False, f"a second line that is cut off: {forms[index]}"
                )
                expect("The Clever Fox" in forms[index]["text"], f"the small card: {forms[index]}")

            # What the card is there for, brought about for real: somebody takes the
            # figure off the box, the box reports it, and every size says so and still
            # fits; then the figure is put back
            async def says(words: str) -> list[dict[str, Any]]:
                found: list[dict[str, Any]] = []

                async def all_say() -> bool:
                    found[:] = await cards.evaluate_all(
                        """els => els.map((el) => {
                          const root = el.shadowRoot;
                          const card = root.querySelector("ha-card");
                          const content = root.querySelector(".content");
                          const line = root.querySelector(".compact .sub, .play .headline");
                          return {
                            text: line ? line.textContent : "",
                            fits: content.getBoundingClientRect().bottom <= card.getBoundingClientRect().bottom + 1,
                          };
                        })"""
                    )
                    return len(found) == 5 and all(words in f["text"] for f in found)

                await _until(all_say, f"{words!r} on the card in every size")
                return found

            instance.world.write_text("removed")
            gone = await says("Nothing on the box")
            expect(all(f["fits"] for f in gone), f"cut off without a figure: {gone}")
            instance.world.write_text("placed")
            back = await says("The Clever Fox")
            expect(all(f["fits"] for f in back), f"cut off with the figure back: {back}")
            # Somebody switches the box off: Home Assistant's word for it in every size,
            # and no button left; then on again
            instance.world.write_text("off")
            off = await says("Off")
            expect(all(f["fits"] for f in off), f"cut off while the box is off: {off}")
            buttons = await cards.evaluate_all(
                "els => els.map((el) => el.shadowRoot.querySelectorAll('[data-act]').length)"
            )
            expect(not any(buttons), f"buttons on a box that is off: {buttons}")
            instance.world.write_text("placed")
            await says("The Clever Fox")
            if shots is not None:
                # High enough for the whole section, so Home Assistant's header covers nothing
                await user.set_viewport_size({"width": 1200, "height": 2200})
                await user.wait_for_timeout(500)
                await user.locator("hui-grid-section").first.screenshot(
                    path=str(shots / "card-sizes.png")
                )
        finally:
            await user.context.close()

    await checks.run("the dashboard card for a user without administrator rights", dashboard_card)
    await page.context.close()

    async def phone_dark() -> None:
        phone = await _open(
            browser, instance, ADMIN, viewport={"width": 390, "height": 844}, color_scheme="dark"
        )
        try:
            await _ready(phone, ".batt-btn")
            await _frame(phone, sub=False)
            bottom = await phone.locator(PANEL).evaluate(
                "el => !!el.shadowRoot.getElementById('frame').shadowRoot.querySelector('#tabbar.bottom-bar')"
            )
            expect(bottom, "the areas are not at the bottom")
            expect(not await phone.locator(f"{PANEL} #stamp").is_visible(), "the stamp shows")
            for button in ("#refresh", "#integration"):
                expect(await phone.locator(f"{PANEL} ha-icon-button{button}").is_visible(), button)
            for path in (
                "boxes/overview",
                "figures/list",
                f"boxes/overview?key={demo_cloud.KIDS_BOX}",
                "setup/preferences",
            ):
                await _goto(phone, instance, path, "ha-card")
                overflow = await phone.evaluate(
                    "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
                )
                expect(overflow <= 0, f"{path}: the page scrolls sideways by {overflow} px")
            background = await phone.locator(PANEL).evaluate(
                "el => getComputedStyle(el).backgroundColor"
            )
            channels = [
                int(part) for part in background[background.index("(") + 1 : -1].split(",")[:3]
            ]
            expect(sum(channels) < 200, f"dark mode background is {background}")
            if shots is not None:
                await _goto(phone, instance, "boxes/overview", ".batt-btn")
                await phone.wait_for_timeout(600)
                await phone.screenshot(path=str(shots / "boxes-phone-dark.png"))
        finally:
            await phone.context.close()

    await checks.run("phone width in dark mode: areas at the bottom, nothing sideways", phone_dark)

    async def phone_safe_area() -> None:
        phone = await _open(
            browser, instance, ADMIN, viewport={"width": 390, "height": 844}, color_scheme="dark"
        )
        try:
            measured: dict[str, Any] = {}
            for name, path in (
                ("the page", "/storybox-plus/boxes/overview"),
                ("Home Assistant's automations", "/config/automation/dashboard"),
            ):
                await phone.goto(f"{instance.base}{path}")
                await phone.wait_for_load_state("networkidle")
                await phone.locator("#ha-launch-screen").wait_for(state="detached")
                await phone.wait_for_timeout(1500)
                # As Home Assistant's own debug setting simulates an iPhone's safe area
                await phone.evaluate(SAFE_AREA)
                await phone.wait_for_timeout(800)
                frame = await phone.evaluate(MEASURE_FRAME)
                expect(isinstance(frame, dict), f"{name}: {frame}")
                height = frame["viewport"]
                expect(frame["frame"] == [0, height], f"{name}: the frame spans {frame['frame']}")
                expect(
                    frame["toolbar"] == 56 + SAFE_TOP,
                    f"{name}: the header is {frame['toolbar']} px high",
                )
                tabbar = frame["tabbar"]
                expect(tabbar is not None, f"{name}: no tab bar at the bottom")
                expect(
                    tabbar[1] == height and 0 <= tabbar[0] < tabbar[1],
                    f"{name}: the tab bar spans {tabbar} in a viewport of {height} px",
                )
                print(f"     {name}: {frame}")
                measured[name] = frame
            ours, theirs = measured.values()
            expect(ours == theirs, f"the page {ours} differs from Home Assistant's {theirs}")
        finally:
            await phone.context.close()

    await checks.run(
        "phone with a safe area: header and tab bar as on Home Assistant's own pages",
        phone_safe_area,
    )
    return checks


SAFE_TOP = 47
# An iPhone's safe area, set the way Home Assistant's debug setting does it
SAFE_AREA = f"""() => {{
    const style = document.createElement('style');
    style.textContent = ':root{{--app-safe-area-inset-top:{SAFE_TOP}px !important;'
        + '--app-safe-area-inset-bottom:34px !important;}}';
    document.head.append(style);
}}"""
# Where the first hass-tabs-subpage and its bottom tab bar sit ([top, bottom]), and its header's height
MEASURE_FRAME = """() => {
    const find = (root) => {
        for (const el of root.querySelectorAll('*')) {
            if (el.localName === 'hass-tabs-subpage') return el;
            const inner = el.shadowRoot && find(el.shadowRoot);
            if (inner) return inner;
        }
        return null;
    };
    const frame = find(document);
    if (!frame) return 'no hass-tabs-subpage';
    const span = (el) => {
        if (!el) return null;
        const box = el.getBoundingClientRect();
        return [Math.round(box.top), Math.round(box.bottom)];
    };
    const root = frame.shadowRoot;
    const toolbar = root.querySelector('.toolbar');
    return {
        viewport: innerHeight,
        frame: span(frame),
        toolbar: toolbar ? Math.round(toolbar.getBoundingClientRect().height) : null,
        tabbar: span(root.querySelector('#tabbar.bottom-bar')),
    };
}"""


# Every page of the panel, by its address
PAGES = (
    "boxes/overview",
    "figures/list",
    "figures/tunes",
    "listening/summary",
    "listening/times",
    "setup/overview",
    "setup/household",
    "setup/preferences",
)


def _mdi(name: str) -> str:
    """An icon path as the page has it."""
    script = (INTEGRATION / "frontend" / "storybox-plus-common.js").read_text()
    start = script.index(f'  {name}: "') + len(f'  {name}: "')
    return script[start : script.index('"', start)]


async def _negate(check: Callable[[], Awaitable[bool]]) -> bool:
    return not await check()


async def _count_is(locator: Any, count: int) -> bool:
    return bool(await locator.count() == count)


async def _has_text(locator: Any, text: str) -> bool:
    return text in await locator.inner_text()


async def _has_schedule(api: Api, instance: Instance, name: str, present: bool) -> bool:
    return (name in await _schedules(api, instance)) is present


async def _stamped(locator: Any) -> bool:
    text = (await locator.inner_text()).strip()
    return text.startswith("As of ") and len(text) == len("As of 00:00:00")


async def _stamp_after(locator: Any, before: str) -> bool:
    return await _stamped(locator) and (await locator.inner_text()).strip() != before


async def _text_is(locator: Any, text: str) -> bool:
    return (await locator.inner_text()).strip() == text


async def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--screenshots", type=Path, help="write the README pictures into this directory"
    )
    parser.add_argument("--keep", action="store_true", help="keep the temporary directory")
    parser.add_argument("--browser", choices=["chrome", "chromium"], default="chromium")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    if args.screenshots is not None:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="storybox-plus-panel-"))
    instance = Instance(directory)
    checks = Checks()
    async with aiohttp.ClientSession() as session:
        try:
            api = await instance.start(session)
            print(f"Home Assistant on {instance.base}, files in {directory}")
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    channel="chrome" if args.browser == "chrome" else None,
                    headless=not args.headed,
                )
                try:
                    checks = await check_page(browser, instance, api, args.screenshots)
                finally:
                    await browser.close()
        except Exception as err:
            checks.failed.append(f"setup: {err!r}")
            print(f"FAIL setup: {err!r}")
            log = directory / "hass.log"
            if log.exists():
                print("".join(log.read_text(errors="replace").splitlines(keepends=True)[-60:]))
        finally:
            await instance.stop(session)
    errors = (
        [
            line
            for line in (directory / "config" / "home-assistant.log")
            .read_text(errors="replace")
            .splitlines()
            if " ERROR " in line and "storybox_plus" in line
        ]
        if (directory / "config" / "home-assistant.log").exists()
        else []
    )
    for line in errors:
        checks.failed.append(f"log: {line}")
        print(f"FAIL log: {line}")
    print(f"\n{len(checks.passed)} passed, {len(checks.failed)} failed")
    if args.keep or checks.failed:
        print(f"Files kept in {directory}")
    else:
        shutil.rmtree(directory, ignore_errors=True)
    return 1 if checks.failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
