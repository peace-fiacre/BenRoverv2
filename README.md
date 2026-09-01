# BenRover — Jumeau numérique (ROS 2 / Gazebo)

Jumeau numérique du rover martien BenRover, développé pour permettre à
l'équipe software de développer et tester ses nodes ROS 2 (perception,
planification, contrôle) en simulation, sans dépendre de la disponibilité
du rover physique.

## Structure du projet

```
BenRover/
├── src/
│   ├── benrover_description/   # Géométrie du robot (URDF, meshes)
│   │   ├── urdf/
│   │   ├── meshes/
│   │   ├── config/
│   │   └── launch/
│   └── benrover_gazebo/        # Simulation (monde, spawn, bridge)
│       ├── worlds/
│       ├── config/
│       └── launch/
└── README.md                   # Ce fichier
```

## État actuel

### Fait et validé

- Squelette du workspace ROS 2 et des deux packages (`benrover_description`,
  `benrover_gazebo`), build propre avec `colcon build`.
- URDF fonctionnel d'un rover 6 roues à suspension rocker-bogie, avec
  direction avant et arrière (`steer_front_*` / `steer_rear_*`) et roue
  centrale sans direction — architecture cohérente avec le BOM SolidWorks
  reçu de l'équipe mécanique.
  - **Géométrie actuelle : primitives (box/cylinder), pas les vraies
    meshes STL.** But de cette version : valider la chaîne technique, pas
    représenter fidèlement BenRover visuellement.
- Chaîne TF (`robot_state_publisher` + joints) validée dans RViz sur une
  version antérieure du fichier (URDF legacy issu d'un export SolidWorks) :
  arbre complet, sans frame orpheline.
- Simulation sous **Gazebo (`gz-sim7`)** :
  - Le rover se lance dans Gazebo via un unique launch file
    (`spawn_benrover.launch.py`).
  - Contrôle différentiel 6 roues via le plugin `gz-sim-diff-drive-system`.
  - Pont `ros_gz_bridge` configuré (`cmd_vel`, `odom`, `tf`, `joint_states`,
    `scan`, `imu`, `clock`).
  - Le rover répond à une commande de vitesse sur `/cmd_vel` (testé et
    confirmé — penser à démarrer/`play` la simulation dans Gazebo, sinon
    aucune commande n'a d'effet).

### À vérifier / à faire

- [ ] Confirmer que `/joint_states` publie bien **en continu** (pas
      juste une fois) pendant que la simulation tourne.
- [ ] Confirmer l'absence de frame orpheline dans le TF tree **sur la
      version actuelle** du fichier (validé précédemment sur une version
      antérieure, à reconfirmer sur le fichier en place aujourd'hui) via
      `ros2 run tf2_tools view_frames`.
- [ ] Récupérer les vraies données CAO définitives : définir les
      **mates/joints dans SolidWorks** à partir du fichier STEP reçu de
      l'équipe mécanique, puis exporter via le plugin SW2URDF (meshes STL
      + URDF avec les vraies dimensions).
- [ ] Remplacer les primitives par les vraies meshes STL une fois
      l'export SolidWorks obtenu.
- [ ] Piloter les joints de direction avant/arrière (`steer_front_*` /
      `steer_rear_*`) — pour l'instant ils restent figés, seul le
      déplacement en ligne droite/rotation (skid-style) est fonctionnel.
- [ ] La barre différentielle mécanique reliant les deux rockers n'est pas
      modélisée (limitation connue d'URDF, qui ne supporte pas les
      boucles fermées) — les deux côtés restent cinématiquement
      indépendants pour l'instant.
- [ ] Choix d'architecture de contrôle à trancher pour la suite : rester
      sur le plugin `diff_drive` direct (actuel, plus simple) ou migrer
      vers `ros2_control` (plus standard ROS 2, envisagé initialement).
- [ ] Capturer une courte démo (vidéo ou live) à présenter à l'équipe.


## Comment lancer et tester

### 1. Build

```bash
cd ~/Projects/BenRover
colcon build
source install/setup.bash
```

### 2. Lancer la simulation complète

```bash
ros2 launch benrover_gazebo spawn_benrover.launch.py
```

Ce launch file démarre Gazebo (monde vide), spawn le rover, lance
`robot_state_publisher` et le pont `ros_gz_bridge`.

**Important** : la simulation démarre parfois **en pause** dans Gazebo —
vérifier que le bouton play est bien activé (sinon aucune commande
n'aura d'effet, même si tout est correctement configuré).

### 3. Vérifier les topics disponibles

```bash
ros2 topic list
```

Doivent apparaître : `/cmd_vel`, `/odom`, `/tf`, `/joint_states`,
`/scan`, `/imu`, `/clock`.

### 4. Tester une commande de vitesse

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}}" --once
```

Les roues doivent tourner visuellement dans Gazebo.

### 5. Vérifier la publication continue de `/joint_states`

```bash
ros2 topic echo /joint_states
```

### 6. Vérifier le TF tree (absence de frame orpheline)

Avec la simulation en cours, dans un autre terminal :

```bash
ros2 run tf2_tools view_frames
xdg-open frames.pdf
```

Ou visuellement dans RViz (`rviz2`) : ajouter les displays `RobotModel`
(Description Topic = `/robot_description`) et `TF`, régler
**Fixed Frame** sur `base_link`.

