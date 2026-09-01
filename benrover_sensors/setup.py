from setuptools import find_packages, setup

package_name = 'benrover_sensors'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='peace-fiacre',
    maintainer_email='fiacreegoudjobi@gmail.com',
    description=(
        "Node d'acquisition capteur BenRover (encodeurs filtres depuis "
        "joint_states, surveillance de fraicheur scan/imu/joint_states)"
    ),
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'sensor_acquisition_node = '
            'benrover_sensors.sensor_acquisition_node:main',
        ],
    },
)