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
    for back in range(75):
        day = today - timedelta(days=back)
        if rng.random() < 0.15:
            continue
        weekend = day.weekday() >= 5
        sums: dict[str, int] = {}
        for _ in range(rng.randint(2, 5 if weekend else 3)):
            figure = rng.choices(list(weights), weights=list(weights.values()))[0]
            sums[figure] = sums.get(figure, 0) + rng.randint(4, 22) * 60
        days[day.isoformat()] = {demo_cloud.KIDS_BOX: sums}
    return {"days": days}


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
    browser: Browser, instance: Instance, user: tuple[str, str], tab: str = "boxes", **options: Any
) -> Page:
    """A new page, logged in, on a tab of the Storybox Plus page."""
    context = await browser.new_context(
        viewport=options.pop("viewport", {"width": 1200, "height": 820}),
        device_scale_factor=2,
        locale="en-US",
        timezone_id=TIME_ZONE.key,
        color_scheme=options.pop("color_scheme", "light"),
    )
    page = await context.new_page()
    await page.goto(f"{instance.base}/storybox-plus#{tab}")
    await page.get_by_label("Username").fill(user[0])
    await page.get_by_label("Password", exact=True).fill(user[1])
    await page.keyboard.press("Enter")
    await page.wait_for_load_state("networkidle")
    # Keep the sidebar out of the pictures
    await page.evaluate("localStorage.setItem('dockedSidebar', JSON.stringify('always_hidden'))")
    await page.goto(f"{instance.base}/storybox-plus#{tab}")
    await page.reload()
    await page.wait_for_load_state("networkidle")
    return page


async def _ready(page: Page, what: str) -> None:
    """The tab shows its content and Home Assistant's loading screen has faded out."""
    # The first load of the frontend takes a while on a slow CI machine
    await page.locator(f"{PANEL} {what}").first.wait_for(timeout=90000)
    await page.locator("#ha-launch-screen").wait_for(state="detached")


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
            nav["count"] == 3 and nav["active"] == 1, f"{nav['count']} tabs, {nav['active']} active"
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
        await _ready(page, ".tile")
        cards = page.locator(f"{PANEL} .grid > ha-card")
        expect(await cards.count() == 2, f"2 boxes expected, got {await cards.count()}")
        kids = await cards.nth(0).inner_text()
        for part in ("Kids room", "Toniebox 2", "Online", "The Clever Fox", "Chapter 3 / 8"):
            expect(part in kids, f"{part!r} missing on the box: {kids}")
        expect("The Frozen River" in kids and "Playing" in kids, kids)
        expect("64 %" in kids and "per full charge" in kids, "battery missing")
        expect("Sleep timer until" in kids, "sleep timer missing")
        living = await cards.nth(1).inner_text()
        expect("Living room" in living and "Last seen" in living, living)
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

    async def charge_history() -> None:
        await page.locator(f"{PANEL} .tile [data-fold]").click()
        rows = page.locator(f"{PANEL} table.cycles tbody tr")
        await rows.first.wait_for()
        expect(await rows.count() == 7, f"7 charges expected, got {await rows.count()}")
        # Keyboard: Enter on the head closes it again
        await page.locator(f"{PANEL} .tile [data-fold]").press("Enter")
        await rows.first.wait_for(state="hidden")
        if shots is not None:
            await page.locator(f"{PANEL} .tile [data-fold]").click()
            await rows.first.wait_for()
            await page.set_viewport_size({"width": 1200, "height": 560})
            await page.wait_for_timeout(400)
            await page.screenshot(path=str(shots / "boxes.png"))
            await page.set_viewport_size({"width": 1200, "height": 820})

    await checks.run("the charge history opens and closes, also by keyboard", charge_history)

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
        await fox.locator("ha-switch").click()

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
        # Without the Media Fetcher app the link button stays off and says why
        link = empty.get_by_role("button", name="From YouTube")
        expect(await link.is_disabled(), "the link button works without the app")
        hint = await empty.locator(".tip").get_attribute("title")
        expect(hint is not None and "Media Fetcher" in hint, str(hint))

    await checks.run("an uploaded file becomes a chapter; links need the app", upload)

    async def listening() -> None:
        await go("listening", ".chart")
        text = await page.locator(f"{PANEL} #sheet").inner_text()
        for part in ("Listening time", "Most played", "Per day", "Per box"):
            expect(part in text, f"{part!r} missing")
        note = page.locator(f"{PANEL} ha-alert[alert-type='info'][title='Counted locally']")
        expect(await note.count() == 1, "the note on where the numbers come from is missing")
        expect("The Clever Fox" in text, "the most played figure is missing")
        bars = await page.locator(f"{PANEL} .chart rect.fill").count()
        expect(bars > 15, f"too few bars: {bars}")
        await page.locator(f"{PANEL} [data-range='all']").click()
        await page.get_by_text("Since", exact=False).first.wait_for()
        await page.locator(f"{PANEL} [data-range='30']").click()
        if shots is not None:
            await page.set_viewport_size({"width": 1200, "height": 1500})
            await page.wait_for_timeout(400)
            await page.screenshot(path=str(shots / "listening.png"))
            await page.set_viewport_size({"width": 1200, "height": 820})

    await checks.run("listening times with the note, ranking and chart", listening)

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
            ("boxes", ".tile", "storybox_plus/overview"),
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
    await page.context.close()

    phone = await _open(
        browser,
        instance,
        ADMIN,
        viewport={"width": 390, "height": 844},
        color_scheme="dark",
    )

    async def phone_dark() -> None:
        await _ready(phone, ".tile")
        expect(
            await phone.locator(f"{PANEL} .bottom-tabs .tab").count() == 3, "no tabs at the bottom"
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
    script = (INTEGRATION / "frontend" / "storybox-plus-panel.js").read_text()
    start = script.index(f'    {name}: "') + len(f'    {name}: "')
    return script[start : script.index('"', start)]


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
