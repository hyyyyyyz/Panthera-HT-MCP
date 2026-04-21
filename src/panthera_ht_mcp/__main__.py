"""Entry point for the Panthera-HT MCP server.

The Panthera SDK has C/C++ code that writes directly to file descriptor 1
(e.g. "motor brake" on shutdown). Python-level stdout redirection does not
catch those, and they corrupt the MCP stdio JSON-RPC stream. We remap fds
at startup: duplicate the original stdout to a fresh fd and hand it to the
Python-level `sys.stdout` wrapper (which MCP uses), then point fd 1 at
stderr so native writes to fd 1 are harmless.
"""

from __future__ import annotations

import os
import sys


def _isolate_stdout_fd() -> None:
    mcp_fd = os.dup(1)
    os.dup2(2, 1)
    sys.stdout = os.fdopen(mcp_fd, "w", buffering=1, encoding="utf-8")


_isolate_stdout_fd()

from panthera_ht_mcp.server import mcp  # noqa: E402


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
