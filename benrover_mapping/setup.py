import os
from glob import glob
from setuptools import setup

package_name = 'benrover_mapping'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml') + glob('config/*.rviz')),

    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='peace-fiacre',
    maintainer_email='fiacreegoudjobi@gmail.com',
    description='Intégration slam_toolbox pour la cartographie BenRover',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [],
    },
)