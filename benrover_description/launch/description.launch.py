import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_description = get_package_share_directory('benrover_description')

    # Chemin vers l'URDF. Il s'agit pour l'instant d'un fichier .urdf brut
    # (issu de l'export SolidWorks corrigé), pas encore d'un .xacro.
    # Le jour où il sera converti en Xacro, il suffira de remplacer ce bloc
    # par un appel à xacro.process_file() sans toucher au reste du launch.
    urdf_path = os.path.join(pkg_description, 'urdf', 'benrover.urdf')

    with open(urdf_path, 'r') as urdf_file:
        robot_description_content = urdf_file.read()

    # urdf_parser_py (utilisé par joint_state_publisher_gui) refuse une
    # chaîne Python contenant la déclaration XML "<?xml ...?>" en tête
    # (erreur lxml : "Unicode strings with encoding declaration are not
    # supported"). robot_state_publisher (parseur C++/KDL) la tolère,
    # mais on la retire pour que les deux nodes acceptent le même contenu.
    if robot_description_content.lstrip().startswith('<?xml'):
        robot_description_content = robot_description_content.split('?>', 1)[1].lstrip()

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_content}],
    )

    # joint_state_publisher_gui : sliders manuels pour bouger chaque joint.
    # Utile UNIQUEMENT pour ce test de validation TF/géométrie en RViz.
    # Sera retiré une fois qu'on passera par Gazebo + ros2_control, qui
    # publieront /joint_states automatiquement.
    joint_state_publisher_gui_node = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        output='screen',
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
    )

    return LaunchDescription([
        robot_state_publisher_node,
        joint_state_publisher_gui_node,
        rviz_node,
    ])