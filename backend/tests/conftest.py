"""Run the Reboot test harness without its local Envoy proxy.

`reboot.aio.tests.Reboot.up` boots Envoy (a PATH executable or the
envoyproxy Docker image) whenever the application has HTTP routes or
mounts. These tests never touch the HTTP surface — they speak gRPC through
external contexts — and Envoy has proven a pure liability in every
environment this suite runs in: Routine sandboxes have no Docker and no
network route to an Envoy binary, and Envoy-in-Docker on GitHub CI runners
races on port allocation ("address already in use"; actions run
29357037307). `servers=1` matches the configuration proven green in the
sandbox (loop session of 2026-07-14); multi-server consensus adds processes
without covering more of this app.

The wrapper only fills in defaults: a test that genuinely exercises the
HTTP surface opts back in by passing `local_envoy=True` to its own `up()`
call.
"""

from reboot.aio.tests import Reboot

_reboot_up_with_defaults = Reboot.up


async def _reboot_up_envoy_free(self, *args, **kwargs):
    kwargs.setdefault("local_envoy", False)
    kwargs.setdefault("servers", 1)
    return await _reboot_up_with_defaults(self, *args, **kwargs)


# The method assignment is the point of this guard; silence only that.
Reboot.up = _reboot_up_envoy_free  # type: ignore[method-assign]
