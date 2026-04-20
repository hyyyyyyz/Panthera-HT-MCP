# Panthera-HT MCP

MCP server exposing the Panthera-HT 6-axis robotic arm to Claude Code.

See [CLAUDE.md](CLAUDE.md) for architecture, remote server info, and the
dev/test workflow.

## Status

v0 — read-only. One tool: `arm_get_state`. Motion tools to follow once the
transport is validated end-to-end on real hardware.

## Install (on the remote)

```bash
cd ~/VLA/Panthera-HT-MCP
git pull
~/miniconda3/envs/panthera/bin/pip install -e .
```

## Run

```bash
~/miniconda3/envs/panthera/bin/python -m panthera_ht_mcp
```

The server speaks MCP over stdio.
