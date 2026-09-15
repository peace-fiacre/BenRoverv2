# Run from the workspace root:
# colcon test --packages-select benrover_sensors \
#   --python-testing pytest --event-handlers console_direct+

from benrover_sensors.sensor_driver_node import (
    SensorAcquisitionNode,
    WHEEL_JOINT_NAMES,
)
from rclpy.node import Node
from sensor_msgs.msg import JointState


ALL_JOINT_NAMES = [
    'rocker_left_joint', 'bogie_left_joint',
    'steer_front_left_joint', 'steer_rear_left_joint',
    'wheel_front_left_joint', 'wheel_middle_left_joint',
    'wheel_rear_left_joint',
    'rocker_right_joint', 'bogie_right_joint',
    'steer_front_right_joint', 'steer_rear_right_joint',
    'wheel_front_right_joint', 'wheel_middle_right_joint',
    'wheel_rear_right_joint',
]


def test_wheel_encoders_filter_to_six_wheel_joints(spin_for):
    """Only the six wheel joints must be republished as encoders."""
    node_under_test = SensorAcquisitionNode(namespace='test_encoders')
    helper = Node('test_helper_encoders', namespace='test_encoders')
    fake_joint_states_pub = helper.create_publisher(
        JointState, 'joint_states', 10)

    received = []
    helper.create_subscription(
        JointState, 'wheel_encoders', lambda msg: received.append(msg), 10)

    fake_msg = JointState()
    fake_msg.name = ALL_JOINT_NAMES
    fake_msg.position = [0.1 * i for i in range(len(ALL_JOINT_NAMES))]
    fake_msg.velocity = [0.2 * i for i in range(len(ALL_JOINT_NAMES))]

    fake_joint_states_pub.publish(fake_msg)
    spin_for(node_under_test, 0.5)
    spin_for(helper, 0.2)

    assert received, 'Aucun message recu sur /wheel_encoders'
    assert set(received[-1].name) == set(WHEEL_JOINT_NAMES)

    node_under_test.destroy_node()
    helper.destroy_node()
