import time

import pytest
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState, LaserScan, Imu

from benrover_sensors.sensor_driver_node import (
    SensorAcquisitionNode,
    WHEEL_JOINT_NAMES,
    LIDAR_LINK_FRAME_ID,
    IMU_LINK_FRAME_ID,
)

# Tous les joints mobiles du rover, pas seulement les roues - pour
# verifier que le node filtre bien et ne garde QUE les 6 attendus.
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

# Frame_id compose que Gazebo genere reellement (incoherent avec l'URDF)
FAKE_GAZEBO_LIDAR_FRAME = 'benrover/base_link/lidar_sensor'
FAKE_GAZEBO_IMU_FRAME = 'benrover/base_link/imu_sensor'


@pytest.fixture(autouse=True)
def rclpy_context():
    rclpy.init()
    yield
    rclpy.shutdown()


def _spin_for(node_to_spin, seconds):
    """Fait tourner le node pendant une courte duree pour laisser le
    temps aux callbacks de s'executer (equivalent d'une pause 'active')."""
    end_time = time.time() + seconds
    while time.time() < end_time:
        rclpy.spin_once(node_to_spin, timeout_sec=0.05)


def test_wheel_encoders_filters_to_six_wheel_joints():
    """/wheel_encoders ne doit contenir QUE les 6 joints de roue, pas
    les 14 joints (rockers/bogies/direction inclus) de /joint_states."""
    node_under_test = SensorAcquisitionNode()

    helper = Node('test_helper_encoders')
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
    _spin_for(node_under_test, 0.5)
    _spin_for(helper, 0.2)

    assert len(received) >= 1, "Aucun message recu sur /wheel_encoders"
    last = received[-1]
    assert set(last.name) == set(WHEEL_JOINT_NAMES), (
        f"Attendu exactement les 6 joints de roue, recu : {last.name}"
    )

    node_under_test.destroy_node()
    helper.destroy_node()


def test_scan_republished_with_corrected_frame_id():
    """/scan doit exister, etre du bon type, et avoir un frame_id
    corrige (lidar_link) meme si le message brut de Gazebo arrive avec
    un frame_id compose incoherent (benrover/base_link/lidar_sensor)."""
    node_under_test = SensorAcquisitionNode()

    helper = Node('test_helper_scan')
    fake_scan_raw_pub = helper.create_publisher(LaserScan, 'scan_raw', 10)

    received = []
    helper.create_subscription(
        LaserScan, 'scan', lambda msg: received.append(msg), 10)

    fake_msg = LaserScan()
    fake_msg.header.frame_id = FAKE_GAZEBO_LIDAR_FRAME
    fake_msg.ranges = [1.0, 2.0, 3.0]

    fake_scan_raw_pub.publish(fake_msg)
    _spin_for(node_under_test, 0.5)
    _spin_for(helper, 0.2)

    assert len(received) >= 1, "Aucun message recu sur /scan"
    last = received[-1]
    assert last.header.frame_id == LIDAR_LINK_FRAME_ID, (
        f"frame_id attendu '{LIDAR_LINK_FRAME_ID}', recu "
        f"'{last.header.frame_id}'"
    )
    assert list(last.ranges) == [1.0, 2.0, 3.0], (
        "Les donnees du scan n'ont pas ete preservees pendant la "
        "republication"
    )

    node_under_test.destroy_node()
    helper.destroy_node()


def test_imu_republished_with_corrected_frame_id():
    """Meme verification que pour /scan, mais pour /imu."""
    node_under_test = SensorAcquisitionNode()

    helper = Node('test_helper_imu')
    fake_imu_raw_pub = helper.create_publisher(Imu, 'imu_raw', 10)

    received = []
    helper.create_subscription(
        Imu, 'imu', lambda msg: received.append(msg), 10)

    fake_msg = Imu()
    fake_msg.header.frame_id = FAKE_GAZEBO_IMU_FRAME
    fake_msg.linear_acceleration.z = 9.8

    fake_imu_raw_pub.publish(fake_msg)
    _spin_for(node_under_test, 0.5)
    _spin_for(helper, 0.2)

    assert len(received) >= 1, "Aucun message recu sur /imu"
    last = received[-1]
    assert last.header.frame_id == IMU_LINK_FRAME_ID, (
        f"frame_id attendu '{IMU_LINK_FRAME_ID}', recu "
        f"'{last.header.frame_id}'"
    )
    assert last.linear_acceleration.z == 9.8, (
        "Les donnees IMU n'ont pas ete preservees pendant la "
        "republication"
    )

    node_under_test.destroy_node()
    helper.destroy_node()


def test_stale_sensor_is_reported_without_crashing():
    """Si /scan_raw ne recoit jamais rien pendant plus que le seuil, le
    node doit le detecter (sans planter) - on verifie via son etat
    interne plutot que de parser les logs."""
    node_under_test = SensorAcquisitionNode()
    # Seuil reduit pour que le test soit rapide.
    node_under_test.stale_timeout_sec = 0.2

    _spin_for(node_under_test, 0.5)

    assert node_under_test._already_reported_stale['scan'] is True, (
        "Le node n'a pas detecte le capteur scan comme muet"
    )
    assert rclpy.ok()

    node_under_test.destroy_node()