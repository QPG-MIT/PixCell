"""
Synchronous entry points for MCP servers.

pyproject.toml [project.scripts] requires synchronous callables.
Each MCP server's main() is async, so we wrap with asyncio.run().
"""

import asyncio


def mj():
    from gg.servers.mj_server import main
    asyncio.run(main())


def michaelangelo():
    from gg.servers.michaelangelo_server import main
    asyncio.run(main())


def jee():
    from gg.servers.jee_server import main
    asyncio.run(main())


def weber():
    from gg.servers.weber_server import main
    asyncio.run(main())


def flex():
    from gg.servers.flex_server import main
    asyncio.run(main())


def pdk():
    from gg.servers.pdk_server import main
    asyncio.run(main())


def raphael():
    from gg.servers.raphael_server import main
    asyncio.run(main())
