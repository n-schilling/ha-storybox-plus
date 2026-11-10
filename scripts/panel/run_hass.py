"""Start Home Assistant for the page tests, reachable from this machine only.

Home Assistant resolves names with an mDNS resolver that listens on every
network interface (UDP 5353). The page tests need no name resolution, so this
starter swaps it for the plain resolver of aiohttp; together with
`server_host: 127.0.0.1` nothing listens beyond the loopback interface, and the
desktop firewall has nothing to ask about.

Before Home Assistant starts, the integration's cloud is replaced by the
made-up one of demo_cloud.py, so no request goes to the manufacturer.

Usage: python -I run_hass.py -c <config dir>
"""

from pathlib import Path
import sys

import aiohttp

import homeassistant.helpers.aiohttp_client as aiohttp_client


class _LocalResolver(aiohttp.ThreadedResolver):
    """The resolver of aiohttp, closed the way Home Assistant closes its own."""

    async def real_close(self) -> None:
        await self.close()


aiohttp_client._async_make_resolver = lambda hass: _LocalResolver()

# The config folder holds custom_components; Home Assistant imports the
# integration from there and finds it already patched
sys.path.insert(0, str(Path(sys.argv[sys.argv.index("-c") + 1]).resolve()))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import demo_cloud

demo_cloud.install()

from homeassistant.__main__ import main

sys.exit(main())
