# Run from the workspace root:
# colcon test --packages-select benrover_sensors \
#   --python-testing pytest --event-handlers console_direct+

import rclpy

from benrover_sensors.sensor_driver_node import SensorAcquisitionNode


def test_stale_sensor_is_reported_without_crashing(spin_for):
    """A silent sensor must be marked stale while the node remains alive."""
    node_under_test = SensorAcquisitionNode(namespace='test_stale')
    node_under_test.stale_timeout_sec = 0.2

    spin_for(node_under_test, 0.5)

    assert node_under_test._already_reported_stale['scan'] is True
    assert rclpy.ok()

    node_under_test.destroy_node()
