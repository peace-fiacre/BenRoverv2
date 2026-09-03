"""
Test d'intégration pour benrover_mapping.

Vérifie la Definition of Done :
  "Un test unitaire couvre la publication et le format du message
   nav_msgs/OccupancyGrid"

Stratégie : plutôt que de dépendre de Gazebo (lourd, non déterministe
en CI), on lance réellement slam_toolbox (async) et on lui fournit :
  - une TF statique odom -> base_link -> lidar_link
  - quelques sensor_msgs/LaserScan publiés à la main sur /scan

... puis on vérifie que /map est bien publié en nav_msgs/OccupancyGrid
avec des champs cohérents (resolution > 0, largeur/hauteur > 0, header
correctement rempli).

Ce test ne valide PAS la qualité de la carte (dérive, cohérence
géométrique) : ça reste du ressort de la validation manuelle en RViz
prévue dans la DoD ("carte cohérente sur un parcours simple").
"""

import math
import os
import unittest

import launch
import launch_ros.actions
import launch_testing.actions
import launch_testing.markers
import pytest
import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from tf2_ros import StaticTransformBroadcaster


@pytest.mark.launch_test
@launch_testing.markers.keep_alive
def generate_test_description():
    package_dir = get_package_share_directory('benrover_mapping')
    params_file = os.path.join(
        package_dir, 'config', 'mapper_params_online_async.yaml'
    )

    slam_toolbox_node = launch_ros.actions.Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='mapping_node',
        output='screen',
        parameters=[params_file, {'use_sim_time': False}],
    )

    return (
        launch.LaunchDescription([
            slam_toolbox_node,
            launch_testing.actions.ReadyToTest(),
        ]),
        {'slam_toolbox_node': slam_toolbox_node},
    )


class TestMapPublication(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = Node('test_map_published')

        # TF statique : odom -> base_link -> lidar_link
        # (en simulation réelle, odom->base_link vient de
        # gz-sim-diff-drive-system ; ici on la fige pour isoler le test
        # de slam_toolbox lui-même)
        self.tf_broadcaster = StaticTransformBroadcaster(self.node)
        now = self.node.get_clock().now().to_msg()

        odom_to_base = TransformStamped()
        odom_to_base.header.stamp = now
        odom_to_base.header.frame_id = 'odom'
        odom_to_base.child_frame_id = 'base_link'
        odom_to_base.transform.rotation.w = 1.0

        base_to_lidar = TransformStamped()
        base_to_lidar.header.stamp = now
        base_to_lidar.header.frame_id = 'base_link'
        base_to_lidar.child_frame_id = 'lidar_link'
        base_to_lidar.transform.rotation.w = 1.0

        self.tf_broadcaster.sendTransform([odom_to_base, base_to_lidar])

        self.scan_pub = self.node.create_publisher(LaserScan, '/scan', 10)

        self.received_maps = []
        self.map_sub = self.node.create_subscription(
            OccupancyGrid, '/map', self.received_maps.append, 10
        )

    def tearDown(self):
        self.node.destroy_node()

    def _publish_fake_scan(self):
        scan = LaserScan()
        scan.header.stamp = self.node.get_clock().now().to_msg()
        scan.header.frame_id = 'lidar_link'
        scan.angle_min = -math.pi
        scan.angle_max = math.pi
        scan.angle_increment = math.pi / 180.0
        scan.range_min = 0.1
        scan.range_max = 12.0
        num_readings = int(
            (scan.angle_max - scan.angle_min) / scan.angle_increment
        )
        # Un mur fictif à 3m tout autour pour donner de la matière au SLAM.
        scan.ranges = [3.0] * num_readings
        self.scan_pub.publish(scan)

    def test_map_is_published_as_occupancy_grid(self):
        # On publie des scans à intervalle régulier jusqu'à recevoir /map,
        # avec un budget temps généreux (slam_toolbox + démarrage node).
        timeout_sec = 20.0
        elapsed = 0.0
        step = 0.5

        while elapsed < timeout_sec and not self.received_maps:
            self._publish_fake_scan()
            rclpy.spin_once(self.node, timeout_sec=step)
            elapsed += step

        self.assertTrue(
            len(self.received_maps) > 0,
            "Aucun message reçu sur /map après {}s".format(timeout_sec),
        )

        latest_map = self.received_maps[-1]

        # -- Format du message --
        self.assertIsInstance(latest_map, OccupancyGrid)
        self.assertEqual(latest_map.header.frame_id, 'map')
        self.assertGreater(latest_map.info.resolution, 0.0)
        self.assertGreater(latest_map.info.width, 0)
        self.assertGreater(latest_map.info.height, 0)
        self.assertEqual(
            len(latest_map.data),
            latest_map.info.width * latest_map.info.height,
            "La taille de 'data' doit correspondre à width*height",
        )
