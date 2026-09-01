"""
Tests unitaires du sensor_acquisition_node.

Principe : pas besoin de Gazebo. On lance le node normalement, et on
joue nous-memes le role de Gazebo/ros_gz_bridge en publiant directement
de faux messages sur /scan, /imu, /joint_states depuis le test - le node
ne fait aucune difference avec de vrais messages.
"""

import time

import pytest
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

from benrover_sensors.sensor_acquisition_node import (
    SensorAcquisitionNode,
    WHEEL_JOINT_NAMES,
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

    # Un node "faux Gazebo" independant, qui publie sur /joint_states
    # et ecoute /wheel_encoders - simule ce que fait ros_gz_bridge.
    helper = Node('test_helper')
    fake_joint_states_pub = helper.create_publisher(
        JointState, 'joint_states', 10)

    received = []
    helper.create_subscription(
        JointState, 'wheel_encoders', lambda msg: received.append(msg), 10)

    # Construit un faux message /joint_states avec les 14 joints,
    # chacun avec une position/vitesse arbitraire.
    fake_msg = JointState()
    fake_msg.name = ALL_JOINT_NAMES
    fake_msg.position = [0.1 * i for i in range(len(ALL_JOINT_NAMES))]
    fake_msg.velocity = [0.2 * i for i in range(len(ALL_JOINT_NAMES))]

    fake_joint_states_pub.publish(fake_msg)
    _spin_for(node_under_test, 0.5)
    _spin_for(helper, 0.2)

    assert len(received) >= 1, (
        "Aucun message recu sur /wheel_encoders"
    )
    last = received[-1]
    assert set(last.name) == set(WHEEL_JOINT_NAMES), (
        f"Attendu exactement les 6 joints de roue, recu : {last.name}"
    )

    node_under_test.destroy_node()
    helper.destroy_node()


def test_stale_sensor_is_reported_without_crashing():
    """Si /scan ne recoit jamais rien pendant plus que le seuil, le node
    doit le detecter (sans planter) - on verifie via son etat interne
    plutot que de parser les logs."""
    node_under_test = SensorAcquisitionNode()
    # Seuils reduits pour que le test soit rapide (pas besoin d'attendre
    # 1 vraie seconde comme en fonctionnement normal).
    node_under_test.stale_timeout_sec = 0.2

    # On ne publie jamais sur /scan : on attend juste plus longtemps
    # que le seuil, et on laisse le timer de surveillance s'executer.
    _spin_for(node_under_test, 0.5)

    assert node_under_test._already_reported_stale['scan'] is True, (
        "Le node n'a pas detecte le capteur scan comme muet"
    )
    # Le node doit toujours etre vivant et utilisable, pas plante :
    assert rclpy.ok()

    node_under_test.destroy_node()
