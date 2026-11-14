"""Check the page in a real browser against a throwaway Home Assistant.

Starts Home Assistant in a temporary directory, reachable from this machine
only, with the integration talking to a made-up cloud (see run_hass.py and
demo_cloud.py): one household, a Toniebox 2 that plays, a classic box, bought
and creative figures and a disc, made-up listening times and battery cycles.
Playwright then drives the page and checks what it shows and what reaches the
integration. Home Assistant is stopped through its own stop action at the
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
    return {"days": days, "chapters": chapters, "hours": hours, "placements": placements}


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
            env={**os.environ, "STORYBOX_DEMO_BASE": self.base},
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
            "favourites": {"tonies": {"fig-fox": {"active": True, "chapters": [0, 2, 4]}}},
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
    tab: str = "boxes",
    path: str | None = None,
    **options: Any,
) -> Page:
    """A new page, logged in, on a tab of the Storybox Plus page or at another path."""
    target = f"{instance.base}{path}" if path else f"{instance.base}/storybox-plus#{tab}"
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


async def _ready(page: Page, what: str) -> None:
    """The tab shows its content and Home Assistant's loading screen has faded out."""
    # The first load of the frontend takes a while on a slow CI machine
    await page.locator(f"{PANEL} {what}").first.wait_for(timeout=90000)
    await page.locator("#ha-launch-screen").wait_for(state="detached")


async def _schedules(api: Api, instance: Instance) -> dict[str, dict[str, Any]]:
    """The bedtime schedules of the Toniebox 2 as the integration has them, by name."""
    reply = await api.ws(instance.token, {"type": "storybox_plus/overview"})
    box = next(b for b in reply["result"]["boxes"] if b["bedtime"])
    return {s["name"]: s for s in box["bedtime"]["schedules"]}


async def _library(api: Api, instance: Instance) -> dict[str, dict[str, Any]]:
    """The figures as the integration has them, by ID."""
    reply = await api.ws(instance.token, {"type": "storybox_plus/library"})
    return {figure["id"]: figure for figure in reply["result"]["tonies"]}


def _version() -> str:
    return str(json.loads((INTEGRATION / "manifest.json").read_text())["version"])


async def _brand_loaded(page: Page) -> bool:
    return bool(
        await page.locator(PANEL).evaluate(
            "el => (el.shadowRoot.querySelector('img.brand')?.naturalWidth || 0) > 0"
        )
    )


async def _header_row(page: Page, *, tabs: bool) -> None:
    """One header row: the integration's icon, the name, the tabs right after it."""
    await _until(lambda: _brand_loaded(page), "the integration icon in the header", seconds=10)
    row = await page.locator(PANEL).evaluate(
        """el => {
          const root = el.shadowRoot;
          const box = (x) => x.getBoundingClientRect();
          const img = root.querySelector('[slot=title] img.brand');
          const name = box(root.querySelector('[slot=title] .name'));
          const nav = root.querySelector('[slot=title] nav.tabs');
          return {
            brand: { shown: box(img).width, top: box(img).top, bottom: box(img).bottom,
              right: box(img).right },
            name: { top: name.top, bottom: name.bottom, left: name.left, right: name.right },
            tabs: nav ? { top: box(nav).top, bottom: box(nav).bottom, left: box(nav).left,
              count: nav.querySelectorAll('a.tab').length,
              active: nav.querySelectorAll('a.tab.active').length } : null,
            second: !!root.querySelector('.app > nav.tabs'),
          };
        }"""
    )
    middle = (row["name"]["top"] + row["name"]["bottom"]) / 2
    icon = row["brand"]
    expect(icon["shown"] == 24, f"icon {icon['shown']} px wide")
    expect(icon["right"] <= row["name"]["left"], "the icon is not left of the name")
    expect(abs((icon["top"] + icon["bottom"]) / 2 - middle) <= 2, "icon and name not in one row")
    expect(not row["second"], "a second header row for the tabs")
    if tabs:
        nav = row["tabs"]
        expect(nav is not None, "no tabs in the header row")
        expect(
            nav["count"] == 4 and nav["active"] == 1, f"{nav['count']} tabs, {nav['active']} active"
        )
        expect(nav["left"] >= row["name"]["right"], "the tabs are not right of the name")
        expect(
            abs((nav["top"] + nav["bottom"]) / 2 - middle) <= 2,
            f"tabs {nav['top']}-{nav['bottom']} not in the name's row {row['name']}",
        )
    else:
        expect(row["tabs"] is None, "tabs in the header")


async def check_page(browser: Browser, instance: Instance, api: Api, shots: Path | None) -> Checks:
    page = await _open(browser, instance, ADMIN)

    async def go(tab: str, what: str) -> None:
        await page.goto(f"{instance.base}/storybox-plus#{tab}")
        await page.reload()
        await _ready(page, what)

    checks = Checks()

    async def boxes() -> None:
        await _ready(page, ".fact-btn")
        cards = page.locator(f"{PANEL} .grid > ha-card:not(.mini-box)")
        expect(await cards.count() == 1, f"1 Toniebox 2 card expected, got {await cards.count()}")
        kids = await cards.nth(0).inner_text()
        for part in ("Kids room", "The Clever Fox", "Chapter 3 / 8"):
            expect(part in kids, f"{part!r} missing on the box: {kids}")
        # No generation chip and no status word: a dot with a tooltip, the battery in the head
        for part in ("Toniebox 2", "Online"):
            expect(part not in kids, f"{part!r} on the box: {kids}")
        head = cards.nth(0).locator(".card-header")
        dot = await head.locator(".dot.ok").get_attribute("title")
        expect(dot == "Online", f"the dot's tooltip: {dot}")
        expect(await head.locator(".fact-btn").count() == 1, "the battery not in the head")
        expect("The Frozen River" in kids and "Playing" in kids, kids)
        # The card names the battery's level only, and two sleep timers; no firmware
        expect("64 %" in kids and "per full charge" not in kids, f"battery on the card: {kids}")
        expect("Firmware" not in kids, "the firmware on the card")
        # While an alarm is due the timers stay away; otherwise there are two
        timers = await cards.nth(0).locator(".sleep-pick button").all_inner_texts()
        expect(timers in ([], ["30 min", "60 min"]), f"sleep timers: {timers}")
        free = await page.evaluate(
            """() => {
              const panel = document.querySelector("home-assistant").shadowRoot
                .querySelector("home-assistant-main").shadowRoot
                .querySelector("partial-panel-resolver").querySelector("ha-panel-custom")
                .querySelector("storybox-plus-panel");
              const html = panel._controls({ id: "x", online: true, volume: 5, playback: null });
              const box = document.createElement("div");
              box.innerHTML = html;
              return [...box.querySelectorAll(".sleep-pick button")].map((b) => b.textContent);
            }"""
        )
        expect(free == ["30 min", "60 min"], f"sleep timers without an alarm: {free}")
        # The Toniebox 1 is a small card of its own, without heading and connection state
        minis = page.locator(f"{PANEL} .grid > ha-card.mini-box")
        expect(await minis.count() == 1, f"{await minis.count()} small cards")
        expect(
            await minis.locator(".card-header, .dot").count() == 0,
            "heading or dot on the small card",
        )
        living = await minis.inner_text()
        for part in ("Living room", "Last seen", "Max. 100 %", "headphones 75 %", "LED Dimmed"):
            expect(part in living, f"{part!r} missing in the Toniebox 1 card: {living}")
        for part in ("live data", "Unknown", "Toniebox 1"):
            expect(part not in living, f"{part!r} on the Toniebox 1 card: {living}")
        about = await page.locator(f"{PANEL} .about").inner_text()
        expect(about.startswith(f"Storybox Plus {_version()} · commit "), about)
        title = await page.locator(f"{PANEL} ha-top-app-bar-fixed [slot=title] .name").inner_text()
        expect(title == "Storybox Plus", title)
        await _header_row(page, tabs=True)

    await checks.run(
        "boxes with live state, battery, version and one header row: icon, name, tabs", boxes
    )

    async def built_from_home_assistant() -> None:
        defined = await page.evaluate(
            """() => ["ha-top-app-bar-fixed", "ha-menu-button", "ha-card", "ha-button",
                     "ha-icon-button", "ha-alert", "ha-switch", "ha-form", "ha-svg-icon"]
                     .filter((name) => !customElements.get(name))"""
        )
        expect(defined == [], f"not defined without loading: {defined}")
        own = await page.locator(
            f"{PANEL} .card, {PANEL} .btn, {PANEL} .alert, {PANEL} button.icon-button, "
            f"{PANEL} .toolbar"
        ).count()
        expect(own == 0, f"{own} hand-made cards, buttons, alerts or toolbars left")
        header = await page.evaluate(
            """() => {
              const root = document.querySelector("home-assistant").shadowRoot
                .querySelector("home-assistant-main").shadowRoot
                .querySelector("partial-panel-resolver").querySelector("ha-panel-custom")
                .querySelector("storybox-plus-panel").shadowRoot;
              const bar = root.querySelector("ha-top-app-bar-fixed");
              const style = getComputedStyle(bar);
              return {
                same: style.getPropertyValue("--app-header-background-color").trim() ===
                  style.getPropertyValue("--sidebar-background-color").trim(),
                height: root.host.getBoundingClientRect().height,
              };
            }"""
        )
        expect(header["same"], "the header is not in the sidebar's colour")
        expect(header["height"] > 400, f"the page has no height: {header}")

    await checks.run(
        "only Home Assistant's elements, header in the sidebar's colour", built_from_home_assistant
    )

    async def bedtimes() -> None:
        # The card names the next alarm; the bedtimes sit behind the box's cog
        card = page.locator(f"{PANEL} .grid > ha-card:not(.mini-box)").nth(0)
        await _until(
            lambda: _has_text(card, "Next alarm"), "the next alarm on the card", seconds=10
        )
        expect(await card.locator(".tile").count() == 0, "no sections left on the card")
        overlay = await _box_overlay(page)
        tile = overlay.locator(".tile", has_text="Bedtimes")
        await tile.wait_for()
        text = await tile.inner_text()
        for part in ("Bedtime", "every day", "Weekend lie-in", "Next alarm"):
            expect(part in text, f"{part!r} missing in the bedtimes: {text}")
        # The integration arms the alarm half a minute after the box came online
        await _until(
            lambda: _has_text(tile.locator(".alarm-next"), "set on the box"),
            "the alarm armed on the box",
            seconds=90,
        )
        rows = tile.locator(".schedules > li")
        expect(await rows.count() == 2, f"2 bedtimes expected, got {await rows.count()}")
        weekend = rows.filter(has_text="Weekend lie-in")
        await weekend.locator("ha-switch").click()

        async def switched(on: bool) -> bool:
            return (await _schedules(api, instance))["Weekend lie-in"]["enabled"] is on

        await _until(lambda: switched(True), "the bedtime switched on", seconds=5)
        await page.wait_for_timeout(300)
        await weekend.locator("ha-switch").click()
        await _until(lambda: switched(False), "the bedtime switched off", seconds=5)
        await _close_overlay(page)

    await checks.run("bedtimes: next alarm armed on the box, a switch per bedtime", bedtimes)

    async def bedtime_form() -> None:
        overlay = await _box_overlay(page)
        tile = overlay.locator(".tile", has_text="Bedtimes")
        await tile.locator("ha-button[data-act^='sadd:']").click()
        form = tile.locator("ha-form[data-form=schedule]")
        await form.wait_for()
        await form.locator("input").first.fill("Nap")
        await page.wait_for_timeout(300)
        if shots is not None:
            await page.set_viewport_size({"width": 1200, "height": 2000})
            await page.wait_for_timeout(400)
            await tile.screenshot(path=str(shots / "bedtime.png"))
            await page.set_viewport_size({"width": 1200, "height": 820})
        await tile.locator("ha-button[data-act=ssave]").click()
        await _until(
            lambda: _has_schedule(api, instance, "Nap", True), "the new bedtime", seconds=5
        )
        await form.wait_for(state="detached")
        nap = await _schedules(api, instance)
        expect(nap["Nap"]["days"] == ["monday", "tuesday", "wednesday", "thursday", "friday"], nap)
        row = tile.locator(".schedules > li", has_text="Nap")
        await row.locator("ha-icon-button[data-act^='sedit:']").click()
        await form.wait_for()
        delete = tile.locator("ha-button[data-act=sdel]")
        await delete.click()
        await _until(lambda: _has_text(delete, "Really delete"), "the delete to ask", seconds=5)
        await delete.click()
        await _until(
            lambda: _has_schedule(api, instance, "Nap", False), "the bedtime deleted", seconds=5
        )
        await _close_overlay(page)

    await checks.run(
        "bedtimes: a new one through the form, deleted after a second click", bedtime_form
    )

    async def box_settings() -> None:
        kids = page.locator(f"{PANEL} .grid > ha-card:not(.mini-box)").nth(0)
        # The row of the Toniebox 1 opens the same overlay with its own settings
        living = page.locator(f"{PANEL} ha-card.mini-box").first
        overlay = await _open_overlay(page, living.locator("ha-icon-button[data-act^='boxset:']"))
        text = await overlay.inner_text()
        expect("Living room" in text and "LED Dimmed" in text, text)
        expect("Bedtimes" not in text, "a Toniebox 1 has no bedtimes")
        await _close_overlay(page)
        # Escape closes the overlay too
        await _box_overlay(page)
        await page.keyboard.press("Escape")
        await page.locator(OVERLAY).wait_for(state="detached")
        overlay = await _box_overlay(page)
        tile = overlay.locator(".tile", has_text="Settings")
        text = await tile.inner_text()
        for part in ("Max. 75 %", "light ring 60 %", "skipping on"):
            expect(part in text, f"{part!r} missing in the settings: {text}")

        async def rename(name: str) -> None:
            await tile.locator("ha-icon-button[data-act^='bedit:']").click()
            form = tile.locator("ha-form[data-form=settings]")
            await form.wait_for()
            await form.locator("input").first.fill(name)
            await page.wait_for_timeout(300)
            if shots is not None and name != "Kids room":
                await page.set_viewport_size({"width": 1200, "height": 2000})
                await page.wait_for_timeout(400)
                await tile.screenshot(path=str(shots / "settings.png"))
                await page.set_viewport_size({"width": 1200, "height": 820})
            await tile.locator("ha-button[data-act=bsave]").click()
            await form.wait_for(state="detached")

            async def named() -> bool:
                reply = await api.ws(instance.token, {"type": "storybox_plus/overview"})
                return any(b["name"] == name for b in reply["result"]["boxes"])

            await _until(named, f"the box named {name}", seconds=5)

        await rename("Nursery")
        expect("Nursery" in await kids.locator(".box-name").inner_text(), "new name not shown")
        await rename("Kids room")
        await _close_overlay(page)

    await checks.run("box settings: summary per generation, renamed through the form", box_settings)

    async def night_mode() -> None:
        overlay = await _box_overlay(page)
        tile = overlay.locator(".tile", has_text="Settings")
        await tile.locator("ha-button[data-act^='nedit:']").click()
        form = tile.locator("ha-form[data-form=night]")
        await form.wait_for()
        if shots is not None:
            await page.set_viewport_size({"width": 1200, "height": 1400})
            await page.wait_for_timeout(400)
            await tile.screenshot(path=str(shots / "night.png"))
            await page.set_viewport_size({"width": 1200, "height": 820})
        await tile.locator("ha-button[data-act=nsave]").click()
        await form.wait_for(state="detached")

        async def kids_box() -> dict[str, Any]:
            reply = await api.ws(instance.token, {"type": "storybox_plus/overview"})
            return next(b for b in reply["result"]["boxes"] if b["night"])

        async def ring_follows() -> bool:
            box = await kids_box()
            night = box["night"]
            if not night["mode"] or night["mode"]["applied"] != night["phase"]:
                return False
            wanted = night["mode"]["night" if night["phase"] == "night" else "day"]
            return box["settings"]["values"]["lightring_brightness"] == wanted

        await _until(ring_follows, "the light ring set for the phase", seconds=10)
        expect("Night mode of the light ring" in await tile.inner_text(), "night mode row missing")
        await tile.locator("ha-switch[data-act^='non:']").click()

        async def switched_off() -> bool:
            return (await kids_box())["night"]["mode"]["enabled"] is False

        await _until(switched_off, "the night mode switched off", seconds=5)
        await _close_overlay(page)

    await checks.run("night mode: set up through the form, the light ring follows", night_mode)

    async def charge_history() -> None:
        if shots is not None:
            await page.set_viewport_size({"width": 1200, "height": 900})
            await page.wait_for_timeout(400)
            await page.screenshot(path=str(shots / "boxes.png"))
            await page.set_viewport_size({"width": 1200, "height": 820})
        # The level on the card opens the battery with its charge history
        level = page.locator(f"{PANEL} .fact-btn[data-act^='battset:']")
        overlay = await _open_overlay(page, level)
        rows = overlay.locator("table.cycles tbody tr")
        await rows.first.wait_for()
        expect(await rows.count() == 7, f"7 charges expected, got {await rows.count()}")
        text = await overlay.inner_text()
        expect("per full charge" in text and "Lasts about" in text, text)
        if shots is not None:
            await page.wait_for_timeout(400)
            await overlay.screenshot(path=str(shots / "battery.png"))
        await page.keyboard.press("Escape")
        await page.locator(OVERLAY).wait_for(state="detached")
        # Keyboard: Enter on the level opens it too
        await level.focus()
        await page.keyboard.press("Enter")
        await page.locator(OVERLAY).wait_for()
        await _close_overlay(page)
        # The firmware is noted in the box's settings
        settings = await _box_overlay(page)
        expect("Firmware 1.6.30" in await settings.inner_text(), "the firmware in the settings")
        await _close_overlay(page)

    await checks.run(
        "the battery's level opens its charge history, also by keyboard; firmware in the settings",
        charge_history,
    )

    async def figures_filter() -> None:
        await go("figures", ".figure")
        count = page.locator(f"{PANEL} .count")
        expect((await count.inner_text()).strip() == "8 figures", await count.inner_text())
        await page.locator(f"{PANEL} ha-form.search input").fill("dragon")
        await _until(lambda: _text_is(count, "1 of 8 figures"), "the search to filter", seconds=5)
        await page.locator(f"{PANEL} ha-form.search input").fill("")
        await page.locator(f"{PANEL} [data-kind=creative]").click()
        await _until(lambda: _text_is(count, "2 of 8 figures"), "the kind to filter", seconds=5)
        await page.locator(f"{PANEL} [data-kind=all]").click()

    await checks.run("figures: search over chapters and the kind filter", figures_filter)

    async def favourites() -> None:
        await go("figures", ".figure")
        fox = page.locator(f"{PANEL} .figure", has_text="The Clever Fox")
        await fox.locator("[data-fold]").click()
        stars = fox.locator("ha-icon-button.star")
        await stars.first.wait_for()
        expect(await stars.count() == 8, f"8 stars expected, got {await stars.count()}")
        expect(await fox.locator("ha-icon-button.star.on").count() == 3, "3 favourites expected")
        await stars.nth(1).click()

        async def set_star() -> bool:
            fav = (await _library(api, instance))["fig-fox"]["favourites"]
            return fav == {"active": True, "chapters": [0, 1, 2, 4]}

        await _until(set_star, "the new favourite in the integration")
        await fox.locator("ha-icon-button.star.on").nth(3).wait_for()
        if shots is not None:
            await page.set_viewport_size({"width": 1200, "height": 900})
            await page.wait_for_timeout(400)
            await page.screenshot(path=str(shots / "figures.png"))
            await page.set_viewport_size({"width": 1200, "height": 820})
        await fox.locator("ha-switch[data-act^='favon:']").click()

        async def switched_off() -> bool:
            fav = (await _library(api, instance))["fig-fox"]["favourites"]
            return fav is not None and fav["active"] is False

        await _until(switched_off, "the favourites switched off")

    await checks.run("favourite chapters and their switch reach the integration", favourites)

    async def rearrange() -> None:
        await go("figures", ".figure")
        grandma = page.locator(f"{PANEL} .figure", has_text="Grandma's Stories")
        await grandma.locator("[data-fold]").click()
        await grandma.get_by_role("button", name="Edit").click()
        await grandma.locator("ha-icon-button[data-act='down:0']").click()
        await grandma.locator("ha-icon-button[data-act='remove:3']").click()
        if shots is not None:
            await grandma.scroll_into_view_if_needed()
            await page.wait_for_timeout(400)
            await grandma.screenshot(path=str(shots / "creative.png"))
        await grandma.get_by_role("button", name="Save").click()

        async def saved() -> bool:
            titles = [
                c["title"] for c in (await _library(api, instance))["fig-grandma"]["chapters"]
            ]
            return titles == ["When I Was Little", "The Red Bicycle", "Songs from the Kitchen"]

        await _until(saved, "the new order in the integration")
        await grandma.get_by_role("button", name="Edit").wait_for()

    await checks.run("chapters of a creative figure rearranged and removed", rearrange)

    async def upload() -> None:
        await go("figures", ".figure")
        empty = page.locator(f"{PANEL} .figure", has_text="Creative figure")
        await empty.locator("[data-fold]").click()
        # Without chapters there is nothing to edit
        await empty.get_by_role("button", name="Upload").wait_for()
        expect(await empty.locator("ha-button[data-act^='edit:']").count() == 0, "edit on empty")
        async with page.expect_file_chooser() as chooser:
            await empty.get_by_role("button", name="Upload").click()
        await (await chooser.value).set_files(
            {"name": "Morning song.mp3", "mimeType": "audio/mpeg", "buffer": b"ID3" + bytes(256)}
        )

        async def added() -> bool:
            chapters = (await _library(api, instance))["fig-empty"]["chapters"]
            return [c["title"] for c in chapters] == ["Morning song"]

        await _until(added, "the uploaded chapter in the integration")
        await empty.get_by_text("Morning song").wait_for()
        await empty.locator("ha-button[data-act^='edit:']").wait_for()
        # Without the Media Fetcher app the link button stays off and says why
        link = empty.get_by_role("button", name="From YouTube")
        expect(await link.is_disabled(), "the link button works without the app")
        hint = await empty.locator(".tip:has(ha-button[data-act^='link:'])").get_attribute("title")
        expect(hint is not None and "Media Fetcher" in hint, str(hint))

    await checks.run("an uploaded file becomes a chapter; links need the app", upload)

    async def figure_tools() -> None:
        await go("figures", ".figure")
        lib = await _library(api, instance)
        creative = next(
            f for f in lib.values() if f["kind"] == "creative" and len(f["chapters"]) > 2
        )
        # By its ID: the name changes on the way
        figure = page.locator(f"{PANEL} .figure:has([data-fold='{creative['id']}'])")
        await figure.locator("[data-fold]").click()
        # A volume of its own, chosen from Home Assistant's dropdown behind the figure's cog
        expect(await figure.locator("ha-form[data-form^='vol:']").count() == 0, "volume inline")
        overlay = await _figure_overlay(page, figure)
        volume = overlay.locator("ha-form[data-form^='vol:']")
        await volume.wait_for()
        await volume.evaluate(
            """(form) => form.dispatchEvent(new CustomEvent("value-changed",
                 { detail: { value: { level: "5" } }, bubbles: true, composed: true }))"""
        )

        async def has_volume() -> bool:
            return (await _library(api, instance))[creative["id"]]["volume"] == 5

        await _until(has_volume, "the figure's volume", seconds=5)
        await _until(
            lambda: _has_text(figure.locator(".badges"), "volume 5 / 13"),
            "the volume chip",
            seconds=5,
        )
        # The name in the settings, saved by its own button; live mode by its switch
        name = overlay.locator("ha-form[data-form=figname] input[name=name]")
        await name.wait_for()
        await name.fill("Renamed figure")
        await page.wait_for_timeout(300)
        await overlay.locator("ha-button[data-act^='figrename:']").click()

        async def named() -> bool:
            return (await _library(api, instance))[creative["id"]]["name"] == "Renamed figure"

        await _until(named, "the new name", seconds=5)
        await overlay.locator("ha-switch[data-act^='figlive:']").click()

        async def is_live() -> bool:
            return (await _library(api, instance))[creative["id"]]["live"] is True

        await _until(is_live, "the live mode saved", seconds=5)
        await _close_overlay(page)
        # The edit mode holds the chapters only
        await figure.locator("ha-button[data-act^='edit:']").click()
        await figure.locator("ha-button[data-act=sorttitle]").wait_for()
        expect(
            await figure.locator("ha-form[data-form=figname]").count() == 0, "name in the edit mode"
        )
        await figure.locator("ha-button[data-act=sorttitle]").click()
        await figure.locator("ha-button[data-act=save]").click()

        async def saved() -> bool:
            f = (await _library(api, instance))[creative["id"]]
            titles = [c["title"] for c in f["chapters"]]
            return titles == sorted(titles, key=str.lower)

        await _until(saved, "the new order", seconds=5)
        # A chapter renamed in the edit mode
        await figure.locator("ha-button[data-act^='edit:']").click()
        await figure.locator("ha-icon-button[data-act='chrename:0']").click()
        chapter_name = figure.locator("ha-form[data-form=chname] input")
        await chapter_name.wait_for()
        await chapter_name.fill("Renamed chapter")
        await page.wait_for_timeout(300)
        await figure.locator("ha-button[data-act=chrenameok]").click()
        await figure.locator("ha-button[data-act=save]").click()

        async def chapter_renamed() -> bool:
            f = (await _library(api, instance))[creative["id"]]
            return any(c["title"] == "Renamed chapter" for c in f["chapters"])

        await _until(chapter_renamed, "the chapter renamed", seconds=5)
        # Back to its name, for the pictures
        renamed = (await _library(api, instance))[creative["id"]]["chapters"]
        original = next(c for c in creative["chapters"] if c["id"] == renamed[0]["id"])
        await api.ws(
            instance.token,
            {
                "type": "storybox_plus/chapters/arrange",
                "tonie_id": creative["id"],
                "chapters": [c["id"] for c in renamed],
                "titles": {original["id"]: original["title"]},
            },
        )
        # Without Piper the text button is grey and says why
        text_button = figure.locator("ha-button[data-act^='text:']")
        expect(await text_button.get_attribute("disabled") is not None, "text button not grey")
        tip = await figure.locator(".tip:has(ha-button[data-act^='text:'])").get_attribute("title")
        expect("Piper" in (tip or ""), f"no hint at Piper: {tip}")
        # Shuffling on swap in the settings too
        overlay = await _figure_overlay(page, figure)
        swap = overlay.locator("ha-switch[data-act^='swapshuffle:']")
        await swap.wait_for()
        await swap.click()

        async def shuffles() -> bool:
            return (await _library(api, instance))[creative["id"]]["shuffle_on_swap"] is True

        await _until(shuffles, "shuffling on swap switched on", seconds=5)
        await _close_overlay(page)
        # Later checks know the figure by its old name
        await api.ws(
            instance.token,
            {
                "type": "storybox_plus/figure/update",
                "tonie_id": creative["id"],
                "name": creative["name"],
            },
        )

    await checks.run(
        "figures: a volume per figure, renamed and sorted in the edit mode", figure_tools
    )

    async def preferences() -> None:
        await go("preferences", ".pref-head")
        text = await page.locator(f"{PANEL} .sheet").inner_text()
        for part in (
            "Lock new figures",
            "Mark notifications as read",
            "Backend version",
            "tested",
            "Members (3)",
            "Alex Muster",
            "alex@example.com",
            "Owner",
            "Limited access",
        ):
            expect(part in text, f"{part!r} missing in the settings: {text}")
        expect(
            await page.locator(f"{PANEL} .member").count() == 3, "three members of the household"
        )
        # Another commit of the tested release counts as tested
        expect("tested with" not in text, "the demo cloud runs the tested release")
        expect(
            await page.locator(f"{PANEL} ha-alert[alert-type=warning]").count() == 0, "a cloud note"
        )
        if shots is not None:
            await page.wait_for_timeout(400)
            await page.locator(f"{PANEL} ha-card").first.screenshot(
                path=str(shots / "preferences.png")
            )
        await page.locator(f"{PANEL} ha-switch[data-act^='pmarkread:']").click()

        async def marks() -> bool:
            reply = await api.ws(instance.token, {"type": "storybox_plus/overview"})
            return bool(reply["result"]["entries"][0]["preferences"]["mark_read"])

        await _until(marks, "the preference saved", seconds=5)
        await page.locator(f"{PANEL} ha-switch[data-act^='pmarkread:']").click()
        await _until(lambda: _negate(marks), "the preference saved back", seconds=5)
        # The household renamed and back
        home = page.locator(f"{PANEL} ha-form[data-form^='home:'] input")
        await home.fill("Our flat")
        await page.wait_for_timeout(300)
        await page.locator(f"{PANEL} ha-button[data-act^='homesave:']").click()

        async def renamed(name: str) -> bool:
            reply = await api.ws(instance.token, {"type": "storybox_plus/overview"})
            return reply["result"]["entries"][0]["households"][0]["name"] == name

        await _until(lambda: renamed("Our flat"), "the household renamed", seconds=5)
        await api.ws(
            instance.token,
            {"type": "storybox_plus/household/rename", "household_id": "home", "name": "Home"},
        )
        # A bought figure can be unlocked on its page
        await go("figures", ".figure")
        fox = page.locator(f"{PANEL} .figure", has_text="The Clever Fox")
        await fox.locator("[data-fold]").click()
        overlay = await _figure_overlay(page, fox)
        lock = overlay.locator("ha-switch[data-act^='lock:']")
        await lock.wait_for()
        await lock.click()

        async def unlocked() -> bool:
            return (await _library(api, instance))["fig-fox"]["locked"] is False

        await _until(unlocked, "the figure unlocked", seconds=5)
        await lock.click()
        await _until(lambda: _negate(unlocked), "the figure locked again", seconds=5)
        await _close_overlay(page)
        # The box card shows the box's picture
        await go("boxes", ".fact-btn")
        expect(await page.locator(f"{PANEL} img.box-pic").count() == 1, "box picture missing")

    await checks.run(
        "settings tab with the members, a figure unlocked and locked, the box's picture",
        preferences,
    )

    async def clear_all() -> None:
        await go("figures", ".figure")
        empty = page.locator(f"{PANEL} .figure:has([data-fold='fig-empty'])")
        await empty.locator("[data-fold]").click()
        await empty.locator("ha-button[data-act^='edit:']").click()
        rows = empty.locator("ol.chapters li")
        before = await rows.count()
        expect(before > 0, "the figure has no chapter to remove")
        ask = empty.locator(".clear-ask")
        # Asked twice; keeping them at the second question changes nothing
        await empty.locator("ha-button[data-act=clearall]").click()
        await _until(lambda: _has_text(ask, "Really remove all"), "the first question", seconds=5)
        await empty.locator("ha-button[data-act=clearyes]").click()
        await _until(lambda: _has_text(ask, "keeps no copy"), "the second question", seconds=5)
        if shots is not None:
            await empty.scroll_into_view_if_needed()
            await page.wait_for_timeout(400)
            await empty.screenshot(path=str(shots / "clear.png"))
        await empty.locator("ha-button[data-act=clearno]").click()
        await ask.wait_for(state="detached")
        expect(await rows.count() == before, "chapters removed without both answers")
        await empty.locator("ha-button[data-act=clearall]").click()
        await empty.locator("ha-button[data-act=clearyes]").click()
        await _until(
            lambda: _has_text(ask, "keeps no copy"), "the second question again", seconds=5
        )
        await empty.locator("ha-button[data-act=clearyes]").click()
        await _until(lambda: _count_is(rows, 0), "the list emptied", seconds=5)
        # Nothing is sent before saving: cancelled, the figure keeps its chapters
        await empty.locator("ha-button[data-act=cancel]").click()
        chapters = (await _library(api, instance))["fig-empty"]["chapters"]
        expect(len(chapters) == before, f"chapters changed without saving: {chapters}")

    await checks.run("removing all chapters asks twice and waits for saving", clear_all)

    async def tunes() -> None:
        await go("figures", ".figure")
        empty = page.locator(f"{PANEL} .figure", has_text="Creative figure")
        await empty.locator("[data-fold]").click()
        # The Tune has an overlay of its own, not in the settings
        settings = await _figure_overlay(page, empty)
        expect(await settings.locator(".tune-row").count() == 0, "the Tune in the settings")
        await _close_overlay(page)
        overlay = await _open_overlay(page, empty.locator("ha-icon-button[data-act^='tuneset:']"))
        await overlay.locator("ha-form[data-form^='tune:']").wait_for()
        await overlay.locator("ha-button[data-act^='tuneon:']").click()

        async def laid_on() -> bool:
            lib = await api.ws(instance.token, {"type": "storybox_plus/library"})
            return any("fig-empty" in t["assigned"] for t in lib["result"]["tunes"])

        await _until(laid_on, "the Tune laid on", seconds=5)
        await _until(
            lambda: _has_text(overlay.locator(".tune-row"), "Tune on it:"),
            "the Tune shown",
            seconds=5,
        )
        await _until(
            lambda: _has_text(empty.locator(".badges"), "Tune"), "the Tune chip", seconds=5
        )
        if shots is not None:
            await page.wait_for_timeout(400)
            await overlay.screenshot(path=str(shots / "tune.png"))
        await overlay.locator("ha-button[data-act^='tuneoff:']").click()
        await _until(lambda: _negate(laid_on), "the Tune taken off", seconds=5)
        await _close_overlay(page)

    await checks.run("Tunes: one laid on a creative figure and taken off again", tunes)

    async def listening() -> None:
        await go("listening", ".chart")
        text = await page.locator(f"{PANEL} #sheet").inner_text()
        for part in (
            "Listening time",
            "Most played",
            "Most played chapters",
            "Placed most often",
            "When it is listened to",
            "Per day",
            "Per box",
        ):
            expect(part in text, f"{part!r} missing")
        note = page.locator(f"{PANEL} ha-alert[alert-type='info'][title='Counted locally']")
        expect(await note.count() == 1, "the note on where the numbers come from is missing")
        expect("The Clever Fox" in text, "the most played figure is missing")
        placed = page.locator(f"{PANEL} ol.placed li")
        expect(await placed.count() >= 3, f"{await placed.count()} figures placed")
        first = await placed.first.inner_text()
        expect("Moon" in first and "\u00d7" in first, f"most placed: {first}")
        compare = await page.locator(f"{PANEL} .compare").inner_text()
        expect("compared with the 30 days before" in compare, f"no comparison: {compare}")
        cells = await page.locator(f"{PANEL} .heatmap .hm-cell").count()
        expect(cells == 7 * 24, f"the heatmap has {cells} cells")
        bars = await page.locator(f"{PANEL} .chart rect.fill").count()
        expect(bars > 15, f"too few bars: {bars}")
        await page.locator(f"{PANEL} [data-range='all']").click()
        await page.get_by_text("Since", exact=False).first.wait_for()
        await page.locator(f"{PANEL} [data-range='30']").click()
        if shots is not None:
            await page.set_viewport_size({"width": 1200, "height": 2300})
            await page.wait_for_timeout(400)
            await page.screenshot(path=str(shots / "listening.png"))
            await page.set_viewport_size({"width": 1200, "height": 820})

    await checks.run("listening times with the note, rankings, chart and heatmap", listening)

    async def extras() -> None:
        # Headphones and the player's buttons on the card of the Toniebox 2
        await go("boxes", ".fact-btn")
        kids = page.locator(f"{PANEL} .grid > ha-card").nth(0)
        card = await kids.inner_text()
        expect("Headphones 80 %" in card, "headphones missing on the card")
        expect("asts about" not in card, f"battery remaining on the card: {card}")
        controls = kids.locator(".controls")
        for act in ("previous", "pause", "next", "volume:8", "volume:10"):
            expect(
                await controls.locator(f"[data-act$=':{act}']").count() == 1,
                f"button {act} missing",
            )
        # The demo's bedtime alarm is due: the sleep timer stays out of its way
        sleep = await controls.locator("[data-act*=':sleep']").count()
        expect(sleep == 0, f"{sleep} sleep timer buttons while an alarm is due")
        await controls.locator("[data-act$=':pause']").click()
        await page.wait_for_timeout(600)
        expect(await kids.locator("ha-alert[alert-type=error]").count() == 0, "the command failed")
        # The volume shows in the box's percent; two quick presses go up two levels,
        # though the box answers only later
        expect("70 %" in card, f"volume not in percent: {card}")
        await controls.locator("[data-act$=':volume:10']").click()
        await controls.locator("[data-act$=':volume:11']").wait_for(timeout=3000)
        await controls.locator("[data-act$=':volume:11']").click()
        await controls.locator("[data-act$=':volume:12']").wait_for(timeout=3000)
        await _until(
            lambda: _has_text(kids.locator(".facts"), "90 %"),
            "the volume the box reports after two presses",
            seconds=10,
        )
        # A voucher on the settings tab: a wrong one is refused, the right one adds a Tune
        await go("preferences", ".pref-head")
        code = page.locator(f"{PANEL} ha-form[data-form^='voucher:'] input")
        await code.fill("WRONG")
        await page.wait_for_timeout(300)
        await page.locator(f"{PANEL} ha-button[data-act^='voucher:']").click()
        await page.locator(f"{PANEL} ha-alert[alert-type=error]").first.wait_for()
        await code.fill("DEMO-VOUCHER")
        await page.wait_for_timeout(300)
        await page.locator(f"{PANEL} ha-button[data-act^='voucher:']").click()
        await page.locator(f"{PANEL} ha-alert[alert-type=success]").first.wait_for()

        async def new_tune() -> bool:
            lib = await api.ws(instance.token, {"type": "storybox_plus/library"})
            return any(t["title"] == "Moon Lullabies" for t in lib["result"]["tunes"])

        await _until(new_tune, "the voucher's Tune", seconds=5)
        # Content from a code on a creative figure
        await go("figures", ".figure")
        empty = page.locator(f"{PANEL} .figure:has([data-fold='fig-empty'])")
        await empty.locator("[data-fold]").click()
        overlay = await _open_overlay(page, empty.locator("ha-button[data-act^='code:']"))
        token = overlay.locator("ha-form[data-form=code] input")
        await token.wait_for()
        await token.fill("CARD-123")
        await page.wait_for_timeout(300)
        await overlay.locator("ha-button[data-act=codeadd]").click()

        async def from_card() -> bool:
            chapters = (await _library(api, instance))["fig-empty"]["chapters"]
            return any(c["title"] == "Song from a card" for c in chapters)

        await _until(from_card, "the content from the code", seconds=5)
        # Done, the overlay closes on its own
        await page.locator(OVERLAY).wait_for(state="detached")

    await checks.run("player buttons, headphones, a voucher and content from a code", extras)

    async def escape() -> None:
        # Escape closes every overlay, wherever the focus is: in a field, on the page, nowhere
        async def closes(opener: Any, field: str | None = None, blur: bool = False) -> None:
            overlay = await _open_overlay(page, opener)
            if field is not None:
                box = overlay.locator(field).first
                await box.wait_for()
                await box.click()
            if blur:
                await page.evaluate("document.activeElement?.blur()")
            await page.keyboard.press("Escape")
            try:
                await page.locator(OVERLAY).wait_for(state="detached", timeout=3000)
            except Exception as err:
                raise AssertionError(
                    f"Escape left the overlay open ({field}, blur={blur})"
                ) from err

        await go("boxes", ".fact-btn")
        kids = page.locator(f"{PANEL} .grid > ha-card:not(.mini-box)").nth(0)
        await closes(kids.locator(".fact-btn"))
        await closes(kids.locator(".fact-btn"), blur=True)
        await closes(kids.locator("ha-icon-button[data-act^='boxset:']"))
        # With the settings form open and a field in it focused
        overlay = await _open_overlay(page, kids.locator("ha-icon-button[data-act^='boxset:']"))
        await overlay.locator("ha-icon-button[data-act^='bedit:']").first.click()
        name = overlay.locator("ha-form[data-form=settings] input").first
        await name.wait_for()
        await name.click()
        await page.keyboard.press("Escape")
        await page.locator(OVERLAY).wait_for(state="detached", timeout=3000)
        await closes(page.locator(f"{PANEL} ha-card.mini-box ha-icon-button[data-act^='boxset:']"))
        await go("figures", ".figure")
        creative = page.locator(f"{PANEL} .figure:has([data-fold='fig-grandma'])")
        await closes(
            creative.locator("ha-icon-button[data-act^='figset:']"),
            "ha-form[data-form=figname] input",
        )
        await closes(creative.locator("ha-icon-button[data-act^='figset:']"), blur=True)
        empty = page.locator(f"{PANEL} .figure:has([data-fold='fig-empty'])")
        await empty.locator("[data-fold]").click()
        await closes(empty.locator("ha-icon-button[data-act^='tuneset:']"))
        await closes(empty.locator("ha-button[data-act^='code:']"), "ha-form[data-form=code] input")

    await checks.run("escape closes every overlay, wherever the focus is", escape)

    async def header() -> None:
        # Every message the page sends is noted and the integration's answers are held
        # back a little, so the spinning refresh button can be seen
        await page.evaluate(
            """() => {
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
        )
        bar = page.locator(f"{PANEL} ha-top-app-bar-fixed")
        stamp = bar.locator("#stamp")
        refresh = bar.locator("ha-icon-button#refresh")
        for tab, what, message in (
            ("boxes", ".fact-btn", "storybox_plus/overview"),
            ("figures", ".figure", "storybox_plus/library"),
            ("listening", ".chart", "storybox_plus/analytics"),
        ):
            await page.locator(f"{PANEL} nav.tabs a[data-tab={tab}]").click()
            await _ready(page, what)
            await _header_row(page, tabs=True)
            items = await bar.evaluate(
                """(bar) => [...bar.querySelectorAll(":scope > [slot=actionItems]")].map((el) =>
                     el.id === "stamp" ? "stamp" : el.getAttribute("path"))"""
            )
            icons = {_mdi("refresh"): "refresh", _mdi("cog"): "cog"}
            order = [icons.get(item, item[:24]) for item in items]
            expect(
                order == ["stamp", "refresh", "cog"],
                f"{tab}: the header is not stamp, refresh, settings: {order}",
            )
            await _until(lambda: _stamped(stamp), f"{tab}: the stamp", seconds=10)
            before = (await stamp.inner_text()).strip()
            # The stamp shows seconds; a second later a new one differs
            await page.wait_for_timeout(1100)
            await page.evaluate("window.__sent = []")
            await refresh.click()
            await _until(
                lambda: refresh.evaluate("(el) => el.classList.contains('spin')"),
                f"{tab}: the refresh button to spin",
                seconds=2,
            )
            await _until(
                lambda before=before: _stamp_after(stamp, before),
                f"{tab}: a new stamp after the refresh",
            )
            sent = await page.evaluate("window.__sent")
            expect(message in sent, f"{tab}: {message} not asked again: {sent}")
            # The boxes' own poll may spin it once more; it stops when that is in too
            await _until(
                lambda: refresh.evaluate("(el) => !el.classList.contains('spin')"),
                f"{tab}: the refresh button to stop spinning",
                seconds=5,
            )
        # Settings: Home Assistant's page of the integration, in the app without a reload
        await page.evaluate("window.__kept = true")
        await bar.locator("ha-icon-button[data-act=settings]").click()
        await page.wait_for_url("**/config/integrations/integration/storybox_plus")
        await page.locator("ha-config-integration-page").wait_for(timeout=20000)
        expect(await page.evaluate("window.__kept === true"), "the settings button reloaded")

    await checks.run("header: stamp, refresh on every tab, settings opens the integration", header)

    async def counting() -> None:
        # Last: switching counting off deletes the listening times the other checks use
        await go("preferences", ".pref-head")
        # Counting switched off and on again: the account reloads in between
        counting = page.locator(f"{PANEL} ha-switch[data-act^='panalytics:']")
        await counting.click()

        async def counts(on: bool) -> bool:
            reply = await api.ws(instance.token, {"type": "storybox_plus/overview"})
            entry = reply["result"]["entries"][0]
            return entry.get("preferences", {}).get("analytics") is on

        await _until(lambda: counts(False), "counting switched off", seconds=15)
        await page.wait_for_timeout(5000)
        await counting.click()
        await _until(lambda: counts(True), "counting switched on", seconds=15)
        await page.wait_for_timeout(5000)

    await checks.run("counting switched off and on again on the settings tab", counting)

    async def no_page_for_users() -> None:
        token = await api.login(*USER)
        for message in (
            {"type": "storybox_plus/overview"},
            {"type": "storybox_plus/library"},
            {
                "type": "storybox_plus/favourites/set",
                "tonie_id": "fig-fox",
                "chapters": [],
                "active": False,
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
        # The card on a dashboard, seen by a user without administrator rights
        registry = await api.ws(instance.token, {"type": "config/entity_registry/list"})
        player = next(
            e["entity_id"]
            for e in registry["result"]
            if e["platform"] == "storybox_plus" and e["entity_id"].startswith("media_player.")
        )
        card_config = {"type": "custom:storybox-plus-box-card", "entity": player}
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
                "config": {"views": [{"title": "Kids", "path": "kids", "cards": [card_config]}]},
            },
        )
        expect(saved["success"], str(saved))
        user = await _open(browser, instance, USER, path="/storybox-test/kids")
        try:
            card = user.locator("storybox-plus-box-card ha-card")
            await card.locator(".card-header").wait_for(timeout=90000)
            text = await card.inner_text()
            for part in ("Kids room", "The Clever Fox", "Headphones 80 %", "Next alarm"):
                expect(part in text, f"{part!r} missing on the card: {text}")
            # Neither the settings nor the charge history: no cog, the battery is no button
            expect(await card.locator("[data-act^='boxset:'], .fact-btn").count() == 0, text)
            expect(await card.locator(".card-header .batt").count() == 1, "battery not in the head")
            # The buttons are the media player's actions, which a user may call
            volume = card.locator(".fact[title^='level']")
            before = await volume.inner_text()
            plus = card.locator("[data-act*=':volume:']").nth(1)
            await plus.click()

            async def answered() -> bool:
                now = await volume.inner_text()
                pending = await card.locator(".fact.pending").count()
                return now != before and "%" in now and not pending

            await _until(answered, "the volume the box reports after a press", seconds=10)
            await card.locator("[data-act$=':pause'], [data-act$=':play']").first.click()
            await user.wait_for_timeout(600)
            alerts = await card.locator("ha-alert[alert-type=error]").count()
            expect(alerts == 0, "a button failed for the user")
            offered = await user.evaluate("(window.customCards || []).map((c) => c.type)")
            expect("storybox-plus-box-card" in offered, f"not in the card picker: {offered}")
            if shots is not None:
                await card.screenshot(path=str(shots / "card.png"))
        finally:
            await user.context.close()

    await checks.run("the dashboard card for a user without administrator rights", dashboard_card)
    await page.context.close()

    phone = await _open(
        browser,
        instance,
        ADMIN,
        viewport={"width": 390, "height": 844},
        color_scheme="dark",
    )

    async def phone_dark() -> None:
        await _ready(phone, ".fact-btn")
        expect(
            await phone.locator(f"{PANEL} .bottom-tabs .tab").count() == 4, "no tabs at the bottom"
        )
        expect(await phone.locator(f"{PANEL} nav.tabs").count() == 0, "tabs at the top on a phone")
        await _header_row(phone, tabs=False)
        await phone.locator(f"{PANEL} ha-menu-button[slot=navigationIcon]").wait_for()
        wide = await phone.evaluate(
            """() => {
              const root = document.querySelector("home-assistant").shadowRoot
                .querySelector("home-assistant-main").shadowRoot
                .querySelector("partial-panel-resolver").querySelector("ha-panel-custom")
                .querySelector("storybox-plus-panel").shadowRoot;
              const content = root.querySelector(".content");
              return [document.documentElement.scrollWidth > window.innerWidth,
                      content.scrollWidth > content.clientWidth];
            }"""
        )
        expect(wide == [False, False], f"the page scrolls sideways: {wide}")
        bar = phone.locator(f"{PANEL} ha-top-app-bar-fixed")
        expect(not await bar.locator("#stamp").is_visible(), "the stamp shows on a phone")
        for button in ("#refresh", "[data-act=settings]"):
            expect(await bar.locator(f"ha-icon-button{button}").is_visible(), f"{button} hidden")
        background = await phone.evaluate(
            "() => getComputedStyle(document.documentElement).getPropertyValue('--primary-background-color').trim()"
        )
        expect(background.lower() not in ("#fafafa", "#ffffff", ""), f"not dark: {background}")
        if shots is not None:
            await phone.wait_for_timeout(400)
            await phone.screenshot(path=str(shots / "boxes-phone-dark.png"))

    await checks.run("phone width in dark mode: tabs at the bottom, nothing sideways", phone_dark)
    await phone.context.close()
    return checks


def _mdi(name: str) -> str:
    """An icon path as the page has it."""
    script = (INTEGRATION / "frontend" / "storybox-plus-common.js").read_text()
    start = script.index(f'  {name}: "') + len(f'  {name}: "')
    return script[start : script.index('"', start)]


OVERLAY = f"{PANEL} #overlay .ov-card"


async def _open_overlay(page: Any, opener: Any) -> Any:
    """Click a cog (or another opener) and return the overlay it opens."""
    await opener.click()
    overlay = page.locator(OVERLAY)
    await overlay.wait_for()
    return overlay


async def _close_overlay(page: Any) -> None:
    await page.locator(f"{OVERLAY} ha-icon-button[data-act=dlgclose]").click()
    await page.locator(OVERLAY).wait_for(state="detached")


async def _box_overlay(page: Any) -> Any:
    """The overlay of the Toniebox 2's settings, night mode and bedtimes."""
    card = page.locator(f"{PANEL} .grid > ha-card:not(.mini-box)").nth(0)
    return await _open_overlay(page, card.locator("ha-icon-button[data-act^='boxset:']"))


async def _figure_overlay(page: Any, figure: Any) -> Any:
    """The overlay of a figure's settings, opened by its cog."""
    return await _open_overlay(page, figure.locator("ha-icon-button[data-act^='figset:']"))


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
