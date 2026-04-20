# Panthera-HT MCP

MCP server exposing the Panthera-HT 6-axis robotic arm to Claude Code.

## Goal

Let Claude Code drive a real Panthera-HT arm through natural language — read
state, move joints, move Cartesian, gripper — via MCP tools.

## Stack

- **Language:** Python 3.10 (conda env `panthera` on the remote)
- **MCP SDK:** `mcp` Python package, `FastMCP` high-level API
- **Backend:** Direct Panthera Python SDK (`hightorque_robot` + `Panthera_lib`),
  not ROS2. ROS2 is available as a future backend if we need standard
  interfaces; the direct SDK is simpler to deploy (no ROS2 daemon) and lower
  latency.

## Workflow

Dev happens **locally**; hardware tests happen **on the remote**.

1. Edit locally at `/Users/jacksonhuang/project/Panthera-HT-MCP`
2. `git commit && git push`
3. On remote: `cd ~/VLA/Panthera-HT-MCP && git pull`
4. On remote: install once with `~/miniconda3/envs/panthera/bin/pip install -e .`
5. Run / test

## Remote server

- SSH: `ssh -p 3333 jackson@10.109.70.55` (key at `~/.ssh/id_ed25519`)
- Repo path: `~/VLA/Panthera-HT-MCP`
- SDK (Python): `~/VLA/Panthera-HT_SDK/panthera_python`
  - Scripts dir (holds `Panthera_lib/Panthera.py`):
    `~/VLA/Panthera-HT_SDK/panthera_python/scripts`
  - Default robot config: `…/panthera_python/robot_param/Follower.yaml`
- SDK (C++): `~/VLA/Panthera-HT_SDK/panthera_cpp` (unused)
- ROS2 workspace: `~/VLA/Panthera-HT_ROS2` (unused for now)
- Conda env: `~/miniconda3/envs/panthera/bin/python` (Python 3.10,
  `hightorque_robot` whl already installed)
- OS: Ubuntu 22.04, ROS2 Humble (installed, unused)

## SDK integration notes

- `Panthera_lib` is **not** a pip package — it lives inside the SDK's scripts
  dir. We prepend that dir to `sys.path` at runtime. Path is overridable via
  env var `PANTHERA_SDK_SCRIPTS_PATH`.
- `Panthera()` prints diagnostics to stdout. MCP stdio transport uses stdout
  for JSON-RPC, so SDK prints must be redirected to stderr (see
  `arm._silence_stdout`). Never `print()` from tool handlers.
- State reads need several `send_get_motor_state_cmd()` + `motor_send_cmd()`
  ping cycles before the values are fresh (see example `0_robot_get_state.py`).

## Tool surface

v0 (shipped, read-only):
- `arm_get_state` — joint pos/vel/torque, gripper state, end-effector pose

Planned (motion — add only after v0 validated end-to-end):
- `arm_move_joint` — joint-space goal with duration
- `arm_move_pose` — Cartesian goal via `moveL`
- `arm_home` — go to zero
- `gripper_open` / `gripper_close`
- `arm_stop` / emergency

## Running the server

On the remote:
```bash
~/miniconda3/envs/panthera/bin/python -m panthera_ht_mcp
```

To connect Claude Code to it, add to `~/.claude/mcp.json` (or
`.mcp.json` in a project):
```json
{
  "mcpServers": {
    "panthera-ht": {
      "command": "ssh",
      "args": ["-p", "3333", "jackson@10.109.70.55",
               "/home/jackson/miniconda3/envs/panthera/bin/python",
               "-m", "panthera_ht_mcp"]
    }
  }
}
```

## Safety

Real hardware. When power is removed the motors drop — keep the arm
supported. When adding motion tools, default durations should be
conservative (≥2 s for joint moves), and every motion tool must validate
joint limits (available via `robot.joint_limits`) before issuing the command.
