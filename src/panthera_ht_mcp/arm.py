"""Wrapper around the Panthera SDK.

Panthera_lib is shipped inside the SDK's scripts dir rather than as a
pip-installable package, so we prepend that dir to sys.path at import time.
Set PANTHERA_SDK_SCRIPTS_PATH to override the default location.
"""

from __future__ import annotations

import contextlib
import os
import sys
import time
from pathlib import Path
from threading import Lock
from typing import Any, Optional, Sequence

import numpy as np

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
                # CAN bus settle time; without it the first state read
                # returns 999.0 sentinels for joint positions.
                time.sleep(1.0)
        return _robot


def _refresh_state(robot: Any) -> None:
    # Ping several times with a small pause so get_current_pos() returns
    # fresh values instead of the SDK's 999.0 not-yet-initialized sentinel.
    for _ in range(8):
        robot.send_get_motor_state_cmd()
        robot.motor_send_cmd()
        time.sleep(0.01)


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


_MIN_JOINT_DURATION_S = 1.0
_MIN_HOME_DURATION_S = 2.0
_MIN_POSE_DURATION_S = 1.0


def _max_torque(robot: Any) -> Optional[list[float]]:
    mt = getattr(robot, "max_torque", None)
    return [float(x) for x in mt] if mt is not None else None


def _validate_joint_target(robot: Any, positions: Sequence[float]) -> None:
    count = int(robot.motor_count)
    if len(positions) != count:
        raise ValueError(
            f"expected {count} joint positions, got {len(positions)}"
        )
    limits = getattr(robot, "joint_limits", None)
    if not limits:
        return
    lower = limits["lower"]
    upper = limits["upper"]
    for i, p in enumerate(positions):
        if p < lower[i] or p > upper[i]:
            raise ValueError(
                f"joint {i} target {p:.4f} rad outside limits "
                f"[{float(lower[i]):.4f}, {float(upper[i]):.4f}]"
            )


def move_joint(positions_rad: Sequence[float], duration_s: float) -> dict[str, Any]:
    robot = get_robot()
    positions = [float(x) for x in positions_rad]
    duration = max(float(duration_s), _MIN_JOINT_DURATION_S)
    _validate_joint_target(robot, positions)
    with _silence_stdout():
        _refresh_state(robot)
        ok = robot.moveJ(
            positions,
            duration=duration,
            max_tqu=_max_torque(robot),
            iswait=True,
        )
    return {
        "success": bool(ok),
        "target_rad": positions,
        "duration_s": duration,
    }


def home(duration_s: float = 2.5) -> dict[str, Any]:
    robot = get_robot()
    duration = max(float(duration_s), _MIN_HOME_DURATION_S)
    zero = [0.0] * int(robot.motor_count)
    with _silence_stdout():
        _refresh_state(robot)
        ok = robot.moveJ(
            zero,
            duration=duration,
            max_tqu=_max_torque(robot),
            iswait=True,
        )
    return {"success": bool(ok), "target_rad": zero, "duration_s": duration}


def move_pose(
    position_m: Sequence[float],
    quaternion_xyzw: Optional[Sequence[float]] = None,
    duration_s: float = 2.0,
    use_spline: bool = True,
) -> dict[str, Any]:
    from scipy.spatial.transform import Rotation as R

    robot = get_robot()
    pos = [float(x) for x in position_m]
    if len(pos) != 3:
        raise ValueError("position_m must have 3 elements")
    duration = max(float(duration_s), _MIN_POSE_DURATION_S)
    with _silence_stdout():
        _refresh_state(robot)
        if quaternion_xyzw is not None:
            q = [float(x) for x in quaternion_xyzw]
            if len(q) != 4:
                raise ValueError("quaternion_xyzw must have 4 elements")
            rotation = R.from_quat(q).as_matrix()
        else:
            fk = robot.forward_kinematics()
            rotation = np.array(fk["rotation"], dtype=float)
        ok = robot.moveL(
            target_position=np.array(pos, dtype=float),
            target_rotation=rotation,
            duration=duration,
            use_spline=bool(use_spline),
        )
    return {
        "success": bool(ok),
        "target_position_m": pos,
        "duration_s": duration,
        "kept_current_orientation": quaternion_xyzw is None,
    }


def gripper_open() -> dict[str, Any]:
    robot = get_robot()
    with _silence_stdout():
        robot.gripper_open()
    return {"success": True, "action": "open"}


def gripper_close() -> dict[str, Any]:
    robot = get_robot()
    with _silence_stdout():
        robot.gripper_close()
    return {"success": True, "action": "close"}
