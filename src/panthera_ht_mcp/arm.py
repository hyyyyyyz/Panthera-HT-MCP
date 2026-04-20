"""Wrapper around the Panthera SDK.

Panthera_lib is shipped inside the SDK's scripts dir rather than as a
pip-installable package, so we prepend that dir to sys.path at import time.
Set PANTHERA_SDK_SCRIPTS_PATH to override the default location.
"""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path
from threading import Lock
from typing import Any

_DEFAULT_SDK_SCRIPTS = (
    Path.home() / "VLA" / "Panthera-HT_SDK" / "panthera_python" / "scripts"
)


def _sdk_scripts_path() -> Path:
    override = os.environ.get("PANTHERA_SDK_SCRIPTS_PATH")
    return Path(override).expanduser() if override else _DEFAULT_SDK_SCRIPTS


def _ensure_sdk_on_path() -> None:
    path = str(_sdk_scripts_path())
    if path not in sys.path:
        sys.path.insert(0, path)


@contextlib.contextmanager
def _silence_stdout():
    # Panthera SDK prints diagnostics to stdout; MCP stdio transport uses
    # stdout for JSON-RPC, so anything we emit there corrupts the stream.
    saved = sys.stdout
    sys.stdout = sys.stderr
    try:
        yield
    finally:
        sys.stdout = saved


_lock = Lock()
_robot: Any = None


def get_robot() -> Any:
    global _robot
    with _lock:
        if _robot is None:
            _ensure_sdk_on_path()
            with _silence_stdout():
                from Panthera_lib import Panthera

                _robot = Panthera()
        return _robot


def _refresh_state(robot: Any) -> None:
    # Example 0_robot_get_state.py issues 4 ping cycles before reading.
    for _ in range(4):
        robot.send_get_motor_state_cmd()
        robot.motor_send_cmd()


def read_state() -> dict[str, Any]:
    robot = get_robot()
    with _silence_stdout():
        _refresh_state(robot)
        positions = list(robot.get_current_pos())
        velocities = list(robot.get_current_vel())
        torques = list(robot.get_current_torque())
        gripper = robot.get_current_state_gripper()

        try:
            fk = robot.forward_kinematics()
            pose: dict[str, Any] = {
                "position_m": [float(x) for x in fk["position"]],
                "rotation": [[float(v) for v in row] for row in fk["rotation"]],
            }
        except Exception as exc:  # FK can fail if no recent state
            pose = {"error": f"FK failed: {exc}"}

    motor_count = int(robot.motor_count)
    return {
        "motor_count": motor_count,
        "joints": [
            {
                "index": i,
                "position_rad": float(positions[i]),
                "velocity_rad_s": float(velocities[i]),
                "torque_nm": float(torques[i]),
            }
            for i in range(motor_count)
        ],
        "gripper": {
            "position_rad": float(gripper.position),
            "velocity_rad_s": float(gripper.velocity),
        },
        "end_effector": pose,
    }
