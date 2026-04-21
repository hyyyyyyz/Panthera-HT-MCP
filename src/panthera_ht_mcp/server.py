"""MCP server for the Panthera-HT 6-axis robotic arm."""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from panthera_ht_mcp import arm

mcp = FastMCP("panthera-ht")


@mcp.tool()
def arm_get_state() -> dict:
    """Read the current state of the Panthera-HT arm.

    Returns joint positions (rad), velocities (rad/s), torques (Nm), the
    gripper state, and the current end-effector pose from forward kinematics.
    """
    return arm.read_state()


@mcp.tool()
def arm_home(duration_s: float = 2.5) -> dict:
    """Move all joints to 0 rad. Duration clamped to at least 2.0 s."""
    return arm.home(duration_s)


@mcp.tool()
def arm_move_joint(positions_rad: list[float], duration_s: float = 2.0) -> dict:
    """Move to a joint-space target.

    positions_rad: list of joint angles in radians (one per motor,
      order matches motor indices 0..motor_count-1).
    duration_s: motion duration in seconds; clamped to at least 1.0 s.

    Targets are validated against the robot's joint_limits; out-of-range
    values raise before any motion is issued.
    """
    return arm.move_joint(positions_rad, duration_s)


@mcp.tool()
def arm_move_pose(
    position_m: list[float],
    quaternion_xyzw: Optional[list[float]] = None,
    duration_s: float = 2.0,
) -> dict:
    """Move the end-effector to a Cartesian pose (moveL, spline-smoothed).

    position_m: [x, y, z] in the base frame, meters.
    quaternion_xyzw: optional orientation as [x, y, z, w]. If omitted, the
      current end-effector orientation is retained.
    duration_s: motion duration in seconds; clamped to at least 1.0 s.
    """
    return arm.move_pose(
        position_m=position_m,
        quaternion_xyzw=quaternion_xyzw,
        duration_s=duration_s,
    )


@mcp.tool()
def gripper_open() -> dict:
    """Open the gripper."""
    return arm.gripper_open()


@mcp.tool()
def gripper_close() -> dict:
    """Close the gripper."""
    return arm.gripper_close()
