"""Run the harness Envoy-free where Envoy can't exist.

This app mounts MCP/HTTP routes, so `reboot.aio.tests.Reboot.up` boots a
local Envoy proxy by default (auto-enabled whenever the application has HTTP
routes or mounts). Envoy arrives as a PATH executable or the envoyproxy
Docker image — a Claude Code Routine sandbox has neither, and its network
policy blocks downloading one. These tests never touch the HTTP surface
(they speak gRPC through external contexts), so where no Envoy source
exists, force the harness to skip the proxy rather than skipping the tests:
the full suite runs everywhere, and CI (which has Docker) also exercises the
Envoy-fronted path. `servers=1` matches the configuration proven green in
the sandbox (loop session of 2026-07-14, 21/21 per app); multi-server
consensus spawns processes a constrained sandbox may not afford.
"""

import os
import shutil

from reboot.aio.tests import Reboot


def _envoy_available() -> bool:
    return shutil.which("envoy") is not None or os.path.exists(
        "/var/run/docker.sock"
    )


if not _envoy_available():
    _reboot_up_with_envoy = Reboot.up

    async def _reboot_up_without_envoy(self, *args, **kwargs):
        kwargs.setdefault("local_envoy", False)
        kwargs.setdefault("servers", 1)
        return await _reboot_up_with_envoy(self, *args, **kwargs)

    Reboot.up = _reboot_up_without_envoy
