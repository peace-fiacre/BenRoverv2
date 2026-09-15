import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    gazebo_share = get_package_share_directory('benrover_gazebo')
    mapping_share = get_package_share_directory('benrover_mapping')
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Utiliser l horloge de simulation',
    )
    use_rviz_arg = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Lancer RViz avec la configuration de mapping',
    )

    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz = LaunchConfiguration('use_rviz')

    # Ce launch demarre deja sensor_driver_node et l EKF. Les relancer ici
    # creerait deux publishers concurrents sur les memes topics.
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            gazebo_share, 'launch', 'spawn_benrover.launch.py')),
        launch_arguments={
            'use_sim_time': use_sim_time,
        }.items(),
    )

    mapping_params = os.path.join(
        mapping_share, 'config', 'mapper_params_online_async.yaml')
    rviz_config = os.path.join(
        mapping_share, 'config', 'mapping.rviz')

    mapping_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='mapping_node',
        output='screen',
        parameters=[
            mapping_params,
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

    state_manager_node = Node(
        package='benrover_manager',
        executable='state_manager_node',
        name='state_manager_node',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
    )

    return LaunchDescription([
        use_sim_time_arg,
        use_rviz_arg,
        simulation,
        mapping_node,
        rviz_node,
        state_manager_node,
    ])
