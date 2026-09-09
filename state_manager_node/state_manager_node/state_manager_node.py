from dataclasses import dataclass
from typing import Optional

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from sensor_msgs.msg import Imu, JointState, LaserScan


@dataclass
class TopicHealth:
    """Etat local d'un topic surveille."""

    name: str
    last_message_ns: Optional[int] = None
    valid: bool = True
    error: str = ''

    def mark_received(self, now_ns: int, valid: bool = True, error: str = ''):
        self.last_message_ns = now_ns
        self.valid = valid
        self.error = error

    def is_stale(self, now_ns: int, timeout_sec: float) -> bool:
        if self.last_message_ns is None:
            return True
        return (now_ns - self.last_message_ns) / 1e9 > timeout_sec


def _status_for_topic(topic: TopicHealth, now_ns: int, timeout_sec: float):
    if not topic.valid:
        return DiagnosticStatus.ERROR, topic.error or 'format invalide'
    if topic.is_stale(now_ns, timeout_sec):
        if topic.last_message_ns is None:
            return DiagnosticStatus.ERROR, 'aucun message recu'
        return DiagnosticStatus.ERROR, 'aucun message recent'
    return DiagnosticStatus.OK, 'messages recus normalement'


class StateManagerNode(Node):
    """Publie l'etat consolide des capteurs et du mapping."""

    def __init__(self):
        super().__init__('state_manager_node')

        self.declare_parameter('sensor_timeout_sec', 1.0)
        self.declare_parameter('map_timeout_sec', 2.0)
        self.declare_parameter('publish_period_sec', 0.5)

        self.sensor_timeout_sec = self.get_parameter(
            'sensor_timeout_sec').value
        self.map_timeout_sec = self.get_parameter(
            'map_timeout_sec').value
        publish_period_sec = self.get_parameter(
            'publish_period_sec').value

        self._topics = {
            'scan': TopicHealth('/scan'),
            'imu': TopicHealth('/imu'),
            'wheel_encoders': TopicHealth('/wheel_encoders'),
            'map': TopicHealth('/map'),
        }

        self.create_subscription(
            LaserScan, '/scan', self._on_scan, 10)
        self.create_subscription(
            Imu, '/imu', self._on_imu, 10)
        self.create_subscription(
            JointState, '/wheel_encoders', self._on_wheel_encoders, 10)
        self.create_subscription(
            OccupancyGrid, '/map', self._on_map, 10)

        self._status_pub = self.create_publisher(
            DiagnosticArray, '/reactive/status', 10)
        self.create_timer(publish_period_sec, self._publish_status)

        self.get_logger().info(
            'state_manager_node demarre: publication sur /reactive/status')

    def _now_ns(self):
        return self.get_clock().now().nanoseconds

    def _on_scan(self, msg: LaserScan):
        valid = bool(msg.header.frame_id) and bool(msg.ranges)
        error = '' if valid else 'frame_id ou ranges manquant'
        self._topics['scan'].mark_received(self._now_ns(), valid, error)

    def _on_imu(self, msg: Imu):
        valid = bool(msg.header.frame_id)
        error = '' if valid else 'frame_id manquant'
        self._topics['imu'].mark_received(self._now_ns(), valid, error)

    def _on_wheel_encoders(self, msg: JointState):
        valid = bool(msg.name)
        error = '' if valid else 'aucun joint dans le message'
        self._topics['wheel_encoders'].mark_received(
            self._now_ns(), valid, error)

    def _on_map(self, msg: OccupancyGrid):
        expected_size = msg.info.width * msg.info.height
        valid = (
            msg.header.frame_id == 'map'
            and msg.info.width > 0
            and msg.info.height > 0
            and len(msg.data) == expected_size
        )
        error = '' if valid else 'OccupancyGrid invalide'
        self._topics['map'].mark_received(self._now_ns(), valid, error)

    def _make_status(self, name, level, message, values):
        status = DiagnosticStatus()
        status.name = name
        status.level = level
        status.message = message
        status.values = [
            KeyValue(key=key, value=value) for key, value in values.items()
        ]
        return status

    def _publish_status(self):
        now_ns = self._now_ns()
        sensor_statuses = []
        for key in ('scan', 'imu', 'wheel_encoders'):
            topic = self._topics[key]
            level, message = _status_for_topic(
                topic, now_ns, self.sensor_timeout_sec)
            sensor_statuses.append((key, level, message))

        map_level, map_message = _status_for_topic(
            self._topics['map'], now_ns, self.map_timeout_sec)

        sensor_level = max(item[1] for item in sensor_statuses)
        sensor_message = 'capteurs operationnels'
        if sensor_level != DiagnosticStatus.OK:
            sensor_message = 'au moins un capteur est indisponible'

        overall_level = max(sensor_level, map_level)
        overall_message = 'supervision operationnelle'
        if overall_level != DiagnosticStatus.OK:
            overall_message = 'une anomalie a ete detectee'

        diagnostic = DiagnosticArray()
        diagnostic.header.stamp = self.get_clock().now().to_msg()
        diagnostic.status = [
            self._make_status(
                'sensor_driver_node',
                sensor_level,
                sensor_message,
                {key: message for key, _, message in sensor_statuses},
            ),
            self._make_status(
                'mapping_node',
                map_level,
                map_message,
                {'/map': map_message},
            ),
            self._make_status(
                'state_manager_node',
                overall_level,
                overall_message,
                {'sensor_driver_node': sensor_message,
                 'mapping_node': map_message},
            ),
        ]
        self._status_pub.publish(diagnostic)


def main(args=None):
    rclpy.init(args=args)
    node = StateManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
