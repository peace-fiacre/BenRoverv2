# Run from the workspace root:
# colcon test --packages-select benrover_sensors \
#   --python-testing pytest --event-handlers console_direct+

from benrover_sensors.sensor_driver_node import (
    LIDAR_LINK_FRAME_ID,
    SensorAcquisitionNode,
)
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


def test_scan_republished_with_corrected_frame_id(spin_for):
    """The simulated LIDAR frame must become the URDF lidar_link frame."""
    node_under_test = SensorAcquisitionNode(namespace='test_scan')
    helper = Node('test_helper_scan', namespace='test_scan')
    fake_scan_raw_pub = helper.create_publisher(LaserScan, 'scan_raw', 10)

    received = []
    helper.create_subscription(
        LaserScan, 'scan', lambda msg: received.append(msg), 10)

    fake_msg = LaserScan()
    fake_msg.header.frame_id = 'benrover/base_link/lidar_sensor'
    fake_msg.ranges = [1.0, 2.0, 3.0]

    fake_scan_raw_pub.publish(fake_msg)
    spin_for(node_under_test, 0.5)
    spin_for(helper, 0.2)

    assert received, 'Aucun message recu sur /scan'
    last = received[-1]
    assert last.header.frame_id == LIDAR_LINK_FRAME_ID
    assert list(last.ranges) == [1.0, 2.0, 3.0]

    node_under_test.destroy_node()
    helper.destroy_node()
