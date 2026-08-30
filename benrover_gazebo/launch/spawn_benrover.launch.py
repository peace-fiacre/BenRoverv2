import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg_description = get_package_share_directory('benrover_description')
    pkg_gazebo = get_package_share_directory('benrover_gazebo')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    urdf_path = os.path.join(pkg_description, 'urdf', 'benrover.urdf')
    bridge_config_path = os.path.join(pkg_gazebo, 'config', 'ros_gz_bridge.yaml')

    with open(urdf_path, 'r') as urdf_file:
        robot_description_content = urdf_file.read()

    # urdf_parser_py (utilise par certains outils/nodes ROS 2) refuse une
    # chaine Python contenant la declaration XML "<?xml ...?>" en tete
    # (meme souci deja rencontre avec joint_state_publisher_gui).
    if robot_description_content.lstrip().startswith('<?xml'):
        robot_description_content = robot_description_content.split('?>', 1)[1].lstrip()

    # Lance Gazebo Garden avec un monde vide (-r = demarre la simulation
    # directement, sans attendre un clic sur "play").
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': '-r empty.sdf'}.items(),
    )

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_content}],
    )

    # Spawn du robot dans Gazebo, en lisant directement le topic
    # /robot_description (publie par robot_state_publisher ci-dessus)
    # plutot qu'un chemin de fichier -> pas de duplication de source.
    spawn_node = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'benrover',
            '-topic', 'robot_description',
            '-z', '0.3',
        ],
        output='screen',
    )

    # Pont ROS 2 <-> Gazebo Transport, configure via le fichier YAML
    # (cmd_vel, odom, tf, joint_states, scan, imu, clock).
    bridge_node = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        output='screen',
        parameters=[{'config_file': bridge_config_path}],
    )

    return LaunchDescription([
        gazebo,
        robot_state_publisher_node,
        spawn_node,
        bridge_node,
    ])
