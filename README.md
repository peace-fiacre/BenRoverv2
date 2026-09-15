# BenRover - Simulation et cartographie

Ce workspace ROS 2 permet de simuler le rover BenRover, de tester ses
capteurs et de construire une carte de son environnement.

## Principe de fonctionnement

La simulation fournit les commandes, l'odométrie, l'IMU et les scans du
LIDAR. Les données sont utilisées de la façon suivante :

```text
Simulation
   |
   +--> odométrie
   +--> IMU ------------+
   +--> scan LIDAR      |
                        v
                     EKF
                        |
                        +--> odom -> base_link

scan + TF + odométrie
          |
          v
     SLAM Toolbox
          |
          +--> /map
          +--> map -> odom
```

L'EKF utilise la vitesse d'avancement issue de l'odométrie et l'orientation
de l'IMU. Cette combinaison évite de dépendre directement du yaw estimé par
les roues pendant les rotations.

SLAM Toolbox associe les scans LIDAR à la chaîne TF :

```text
map -> odom -> base_link -> lidar_link
```

RViz affiche ensuite la carte, le robot et les scans reçus.

## État actuel

- Simulation du rover avec commande de vitesse sur `/cmd_vel`.
- Publication de l'odométrie sur `/odom`.
- Fusion de l'odométrie et de l'IMU sur `/odometry/filtered`.
- Publication des scans corrigés sur `/scan`.
- Cartographie avec SLAM Toolbox.
- Monde de test contenant un parcours de type labyrinthe.
- Sauvegarde et rechargement d'une carte validés.
- Test automatisé vérifiant la publication correcte de `/map`.

## Préparer le workspace

```bash
cd ~/Projects/BenRover
source /opt/ros/humble/setup.bash
colcon build
source install/setup.bash
```

## Lancer la simulation

```bash
ros2 launch benrover_gazebo spawn_benrover.launch.py
```

La simulation démarre le robot, ses capteurs, le pont de communication et
l'EKF. Si le monde est en pause, appuyer sur le bouton de lecture avant de
tester les commandes.

## Lancer l'intégration complète

Le launch d'intégration démarre en une seule commande la simulation, les
capteurs, l'EKF, SLAM Toolbox, RViz et la supervision.

```bash
ros2 launch benrover_manager integration.launch.py
```

Pour lancer la chaîne sans RViz :

```bash
ros2 launch benrover_manager integration.launch.py use_rviz:=false
```

Le launch de la simulation démarre déjà `sensor_driver_node` et l'EKF. Ils ne
doivent pas être relancés séparément, afin d'éviter des publishers en double.

## Vérifier les topics

```bash
ros2 topic list
```

Topics principaux :

```text
/cmd_vel
/odom
/odometry/filtered
/imu
/scan
/tf
/tf_static
/clock
```

Vérifier les fréquences :

```bash
ros2 topic hz /scan
ros2 topic hz /imu
ros2 topic hz /odometry/filtered
ros2 topic hz /tf
```

## Tester les mouvements

Avancer :

```bash
ros2 topic pub --rate 20 /cmd_vel \
  geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.0}}"
```

Tourner :

```bash
ros2 topic pub --rate 20 /cmd_vel \
  geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.3}}"
```

Arrêter le robot :

```bash
ros2 topic pub --once /cmd_vel \
  geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

## Vérifier l'odométrie et le TF

```bash
ros2 topic echo /odometry/filtered --once
ros2 run tf2_ros tf2_echo odom base_link
```

Générer l'arbre TF :

```bash
ros2 run tf2_tools view_frames
xdg-open frames.pdf
```

Pendant une rotation, comparer l'orientation de Gazebo avec celle de
`/odometry/filtered` et de `odom -> base_link`.

## Lancer la cartographie

```bash
ros2 launch benrover_mapping mapping.launch.py
```

Dans RViz, utiliser :

```text
Fixed Frame : map
Map         : /map
LaserScan   : /scan
```

Pendant le parcours, les scans doivent rester alignés avec les murs et la
position du robot doit rester cohérente avec la carte, y compris pendant les
rotations.

## Tester automatiquement la cartographie

```bash
cd ~/Projects/BenRover
source /opt/ros/humble/setup.bash
source install/setup.bash

ROS_LOG_DIR=/tmp/benrover-ros-log \
colcon test \
  --packages-select benrover_mapping \
  --python-testing pytest \
  --event-handlers console_direct+
```

Le test démarre SLAM Toolbox avec des TF et des scans artificiels, puis
vérifie que `/map` est publié avec un format valide.

Résultat attendu :

```text
3 passed, 1 skipped
```

## Sauvegarder une carte

Créer le dossier de stockage :

```bash
mkdir -p ~/Projects/BenRover/src/benrover_mapping/maps
```

Se placer dans ce dossier :

```bash
cd ~/Projects/BenRover/src/benrover_mapping/maps
```

Sauvegarder la carte :

```bash
ros2 run nav2_map_server map_saver_cli -f ./benrover_map
```

Les fichiers suivants sont créés :

```text
benrover_map.yaml
benrover_map.pgm
```

## Recharger une carte

Lancer le serveur de carte :

```bash
ros2 run nav2_map_server map_server \
  --ros-args \
  -p yaml_filename:=$HOME/Projects/BenRover/src/benrover_mapping/maps/benrover_map.yaml
```

Dans un autre terminal, configurer puis activer le node lifecycle :

```bash
ros2 lifecycle set /map_server configure
ros2 lifecycle set /map_server activate
```

Vérifier la publication :

```bash
ros2 topic echo /map --once
```

## Ouvrir RViz avec la carte sauvegardée

Sans horloge de simulation :

```bash
ros2 run rviz2 rviz2 \
  -d "$HOME/Projects/BenRover/src/benrover_mapping/config/mapping.rviz" \
  --ros-args -p use_sim_time:=false
```

Avec la simulation active et `/clock` disponible :

```bash
ros2 run rviz2 rviz2 \
  -d "$HOME/Projects/BenRover/src/benrover_mapping/config/mapping.rviz" \
  --ros-args -p use_sim_time:=true
```

## Validation d'intégration

Pendant la démonstration, vérifier simultanément le déplacement du rover dans
la simulation, l'affichage de la carte dans RViz et le statut :

```bash
ros2 topic echo /reactive/status
```

Pour tester la supervision, arrêter uniquement `sensor_driver_node` ou
`mapping_node` avec `Ctrl+C`. Le composant concerné et le statut global doivent
passer à `ERROR`, sans que le node de supervision arrête le rover.

## CI

Le workflow GitHub Actions se trouve dans `.github/workflows/ci.yml`. Il
construit le workspace et exécute les tests de `benrover_sensors`,
`benrover_mapping` et `benrover_manager` avec `pytest`.

```bash
colcon test \
  --packages-select \
  benrover_sensors benrover_mapping benrover_manager \
  --python-testing pytest \
  --event-handlers console_direct+

colcon test-result --verbose
```
