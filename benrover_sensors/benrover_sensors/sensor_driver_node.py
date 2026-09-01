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

# Vrais noms de lien URDF, pour corriger le frame_id incoherent que
# Gazebo genere automatiquement (model/link/sensor).
LIDAR_LINK_FRAME_ID = 'lidar_link'
IMU_LINK_FRAME_ID = 'imu_link'


class SensorAcquisitionNode(Node):

    def __init__(self):
        super().__init__('sensor_driver_node')

        # Parametres ROS 2 : reglables au lancement sans recompiler, ex:
        #   ros2 run benrover_sensors sensor_driver_node \
        #       --ros-args -p stale_timeout_sec:=2.0
        self.declare_parameter('stale_timeout_sec', 1.0)
        self.declare_parameter('monitor_period_sec', 0.5)
        self.stale_timeout_sec = self.get_parameter(
            'stale_timeout_sec').get_parameter_value().double_value
        monitor_period_sec = self.get_parameter(
            'monitor_period_sec').get_parameter_value().double_value

        # Horodatage du dernier message recu pour chaque capteur.
        # Initialise a "maintenant" (pas None) pour eviter une fausse
        # alerte des la premiere seconde, avant que Gazebo ait eu le temps
        # de publier son premier message.
        now = self.get_clock().now()
        self._last_seen = {
            'scan': now,
            'imu': now,
            'joint_states': now,
        }
        # Evite de logguer la meme erreur en boucle a chaque tick du
        # timer tant que le capteur reste silencieux.
        self._already_reported_stale = {
            'scan': False,
            'imu': False,
            'joint_states': False,
        }

        # --- Abonnements aux topics bruts publies par ros_gz_bridge ---
        self.create_subscription(
            LaserScan, 'scan_raw', self._on_scan_raw, 10)
        self.create_subscription(
            Imu, 'imu_raw', self._on_imu_raw, 10)
        self.create_subscription(
            JointState, 'joint_states', self._on_joint_states, 10)

        # --- Publishers : les topics finaux, standards ---
        self._scan_pub = self.create_publisher(LaserScan, 'scan', 10)
        self._imu_pub = self.create_publisher(Imu, 'imu', 10)
        self._encoders_pub = self.create_publisher(
            JointState, 'wheel_encoders', 10)

        # --- Timer de surveillance de fraicheur ---
        self.create_timer(monitor_period_sec, self._check_staleness)

        self.get_logger().info(
            f'sensor_driver_node demarre '
            f'(seuil capteur muet: {self.stale_timeout_sec}s)'
        )

    # ------------------------------------------------------------------
    # Callbacks de reception
    # ------------------------------------------------------------------

    def _on_scan_raw(self, msg: LaserScan):
        self._mark_received('scan')
        # Corrige le frame_id (Gazebo genere un nom compose incoherent
        # avec l'URDF) puis republie sur le topic final /scan.
        msg.header.frame_id = LIDAR_LINK_FRAME_ID
        self._scan_pub.publish(msg)

    def _on_imu_raw(self, msg: Imu):
        self._mark_received('imu')
        msg.header.frame_id = IMU_LINK_FRAME_ID
        self._imu_pub.publish(msg)

    def _on_joint_states(self, msg: JointState):
        self._mark_received('joint_states')
        self._republish_wheel_encoders(msg)

    def _mark_received(self, sensor_key: str):
        self._last_seen[sensor_key] = self.get_clock().now()
        # Le capteur recommence a parler : on pourra re-logguer une
        # erreur si jamais il redevient muet plus tard.
        self._already_reported_stale[sensor_key] = False

    def _republish_wheel_encoders(self, msg: JointState):
        filtered = JointState()
        filtered.header = msg.header

        for name in WHEEL_JOINT_NAMES:
            if name not in msg.name:
                # Un joint attendu est absent du message recu : on le
                # signale (URDF incoherent avec ce node ?) mais on ne
                # plante pas, on republie juste ce qu'on a pu trouver.
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

    # ------------------------------------------------------------------
    # Surveillance periodique de fraicheur
    # ------------------------------------------------------------------

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
                # Sinon : deja signale, on ne repete pas le log a
                # chaque tick tant que le silence continue.


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