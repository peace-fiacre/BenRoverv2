import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, Imu, JointState


# Les 6 joints de roue du rover (voir benrover.urdf) : ce sont les seuls
# qui nous interessent pour un topic "encodeurs" - on ignore les joints
# de rocker/bogie/direction, qui ne sont pas des encodeurs de roue.
WHEEL_JOINT_NAMES = [
    'wheel_front_left_joint',
    'wheel_middle_left_joint',
    'wheel_rear_left_joint',
    'wheel_front_right_joint',
    'wheel_middle_right_joint',
    'wheel_rear_right_joint',
]


class SensorAcquisitionNode(Node):

    def __init__(self):
        super().__init__('sensor_acquisition_node')

    
        self.declare_parameter('stale_timeout_sec', 1.0)
        self.declare_parameter('monitor_period_sec', 0.5)
        self.stale_timeout_sec = self.get_parameter(
            'stale_timeout_sec').get_parameter_value().double_value
        monitor_period_sec = self.get_parameter(
            'monitor_period_sec').get_parameter_value().double_value
        
        now = self.get_clock().now()
        self._last_seen = {
            'scan': now,
            'imu': now,
            'joint_states': now,
        }
      
        self._already_reported_stale = {
            'scan': False,
            'imu': False,
            'joint_states': False,
        }

        self.create_subscription(LaserScan, 'scan', self._on_scan, 10)
        self.create_subscription(Imu, 'imu', self._on_imu, 10)
        self.create_subscription(
            JointState, 'joint_states', self._on_joint_states, 10)

        self._encoders_pub = self.create_publisher(
            JointState, 'wheel_encoders', 10)

        self.create_timer(monitor_period_sec, self._check_staleness)

        self.get_logger().info(
            f'sensor_acquisition_node demarre '
            f'(seuil capteur muet: {self.stale_timeout_sec}s)'
        )


    def _on_scan(self, msg: LaserScan):
        self._mark_received('scan')

    def _on_imu(self, msg: Imu):
        self._mark_received('imu')

    def _on_joint_states(self, msg: JointState):
        self._mark_received('joint_states')
        self._republish_wheel_encoders(msg)

    def _mark_received(self, sensor_key: str):
        self._last_seen[sensor_key] = self.get_clock().now()
        self._already_reported_stale[sensor_key] = False

    def _republish_wheel_encoders(self, msg: JointState):
        filtered = JointState()
        filtered.header = msg.header

        for name in WHEEL_JOINT_NAMES:
            if name not in msg.name:
                self.get_logger().warning(
                    f"Joint de roue attendu introuvable dans "
                    f"/joint_states : {name}"
                )
                continue

            i = msg.name.index(name)
            filtered.name.append(name)
            if i < len(msg.position):
                filtered.position.append(msg.position[i])
            if i < len(msg.velocity):
                filtered.velocity.append(msg.velocity[i])
            if i < len(msg.effort):
                filtered.effort.append(msg.effort[i])

        self._encoders_pub.publish(filtered)


    def _check_staleness(self):
        now = self.get_clock().now()
        threshold = rclpy.duration.Duration(
            seconds=self.stale_timeout_sec)

        for sensor_key, last_time in self._last_seen.items():
            elapsed = now - last_time
            if elapsed > threshold:
                if not self._already_reported_stale[sensor_key]:
                    elapsed_sec = elapsed.nanoseconds / 1e9
                    self.get_logger().error(
                        f"Capteur '{sensor_key}' muet depuis "
                        f"{elapsed_sec:.1f}s (seuil: "
                        f"{self.stale_timeout_sec}s)"
                    )
                    self._already_reported_stale[sensor_key] = True
            


def main(args=None):
    rclpy.init(args=args)
    node = SensorAcquisitionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
