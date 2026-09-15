from glob import glob
import os

from setuptools import find_packages, setup


package_name = 'benrover_manager'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='peace-fiacre',
    maintainer_email='fiacreegoudjobi@gmail.com',
    description='Supervision informative de l etat des capteurs et du mapping',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'state_manager_node = '
            'benrover_manager.state_manager_node:main',
        ],
    },
)
