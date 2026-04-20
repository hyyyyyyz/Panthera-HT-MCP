"""MCP server for the Panthera-HT 6-axis robotic arm.

v0 is read-only by design: we ship only `arm_get_state` first to validate
the MCP transport and SDK bring-up end-to-end before exposing motion.
"""

from __future__ import annotations

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
