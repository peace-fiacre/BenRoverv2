# Shared test helpers.
# Run from the workspace root:
# colcon test --packages-select benrover_sensors \
#   --python-testing pytest --event-handlers console_direct+

import time

import pytest
import rclpy


@pytest.fixture(autouse=True)
def rclpy_context():
    """Create an isolated ROS context for each test."""
    rclpy.init()
    yield
    rclpy.shutdown()


@pytest.fixture
def spin_for():
    """Return a helper that spins a node for a bounded duration."""
    def _spin_for(node_to_spin, seconds):
        end_time = time.time() + seconds
        while time.time() < end_time:
            rclpy.spin_once(node_to_spin, timeout_sec=0.05)

    return _spin_for
