import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_dir = get_package_share_directory('benrover_mapping')
    default_params_file = os.path.join(
        package_dir, 'config', 'mapper_params_online_async.yaml'
    )
    default_rviz_config = os.path.join(
        package_dir, 'config', 'mapping.rviz'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description="Utiliser l'horloge de simulation Gazebo (/clock)",
    )
    slam_params_file_arg = DeclareLaunchArgument(
        'slam_params_file',
        default_value=default_params_file,
        description='Chemin vers le fichier de paramètres slam_toolbox',
    )
    use_rviz_arg = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Ouvrir automatiquement RViz avec la config de mapping',
    )
    rviz_config_arg = DeclareLaunchArgument(
        'rviz_config',
        default_value=default_rviz_config,
        description='Chemin vers le fichier de config RViz (.rviz)',
    )

    use_sim_time = LaunchConfiguration('use_sim_time')
    slam_params_file = LaunchConfiguration('slam_params_file')
    use_rviz = LaunchConfiguration('use_rviz')
    rviz_config = LaunchConfiguration('rviz_config')

    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='mapping_node',
        output='screen',
        parameters=[
            slam_params_file,
            {'use_sim_time': use_sim_time},
        ],
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription([
        use_sim_time_arg,
        slam_params_file_arg,
        use_rviz_arg,
        rviz_config_arg,
        slam_toolbox_node,
        rviz_node,
    ])