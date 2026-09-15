# Run from the workspace root:
# colcon test --packages-select benrover_sensors \
#   --python-testing pytest --event-handlers console_direct+

from benrover_sensors.sensor_driver_node import (
    IMU_LINK_FRAME_ID,
    SensorAcquisitionNode,
)
from rclpy.node import Node
from sensor_msgs.msg import Imu


def test_imu_republished_with_corrected_frame_id(spin_for):
    """The simulated IMU frame must become the URDF imu_link frame."""
    node_under_test = SensorAcquisitionNode(namespace='test_imu')
    helper = Node('test_helper_imu', namespace='test_imu')
    fake_imu_raw_pub = helper.create_publisher(Imu, 'imu_raw', 10)

    received = []
    helper.create_subscription(Imu, 'imu', lambda msg: received.append(msg), 10)

    fake_msg = Imu()
    fake_msg.header.frame_id = 'benrover/base_link/imu_sensor'
    fake_msg.linear_acceleration.z = 9.8

    fake_imu_raw_pub.publish(fake_msg)
    spin_for(node_under_test, 0.5)
    spin_for(helper, 0.2)

    assert received, 'Aucun message recu sur /imu'
    last = received[-1]
    assert last.header.frame_id == IMU_LINK_FRAME_ID
    assert last.linear_acceleration.z == 9.8

    node_under_test.destroy_node()
    helper.destroy_node()
