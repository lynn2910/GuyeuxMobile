# 🚦 Traffic Flow Simulation

### Mathematical Modeling Project

![Python](https://img.shields.io/badge/Python-3.14%2B-blue)
![Status](https://img.shields.io/badge/Status-Active-orange)

## 📖 Overview

This project was developed as part of the **"Modélisation Mathématique" (Mathematical Modeling)** curriculum at the
University/IUT. The primary objective is to bridge the gap between theoretical mathematics and computer science by
implementing and visualizing complex traffic flow models.

We simulate urban traffic using graph theory and two distinct mathematical approaches: microscopic (Cellular Automata)
and macroscopic (Fluid Dynamics). This allows for the analysis of traffic congestion, bottleneck formation, and the
efficiency of road networks.

**Team Members:**

* Cédric COLIN
* Marvyn LEVIN
* Alexandre VILLANI

---

## 🧮 Mathematical Models

This simulation implements three core mathematical concepts:

### 1. Graph Theory (Network Topology)

The road network is modeled as a directed graph $G = (V, E)$, where:

* **Nodes ($V$):** Represent intersections and spawners.
* **Edges ($E$):** Represent road segments with properties like length, max speed, and capacity.
* **Pathfinding:** We utilize the **A* (A-Star) algorithm** with a dynamic heuristic function. The edge weights are
  updated in real-time based on traffic density, allowing vehicles to reroute around congestion dynamically.

### 2. Microscopic Model: Cellular Automata

Based on the **Nagel-Schreckenberg model**, this approach simulates individual driver behaviors.

* **Discretization:** Roads are divided into cells of fixed size ($7.5m$). Time is discrete.
* **State Update:** For each vehicle, position $x$ and velocity $v$ are updated using:
    1. **Acceleration:** $v \leftarrow \min(v + 1, v_{max})$
    2. **Braking (Safety):** $v \leftarrow \min(v, gap)$ (where $gap$ is distance to next vehicle)
    3. **Randomization:** With probability $p$, $v \leftarrow \max(v - 1, 0)$ (simulates human reaction/distraction)
    4. **Movement:** $x \leftarrow x + v$

### 3. Macroscopic Model: Fluid Dynamics (LWR)

Based on the **Lighthill-Whitham-Richards (LWR)** model, treating traffic as a continuous fluid.

* **Conservation Law:** Traffic flow is governed by the continuity equation:
  $$ \frac{\partial \rho}{\partial t} + \frac{\partial q}{\partial x} = 0 $$
  Where $\rho$ is density and $q$ is flow ($q = \rho v$).
* **Fundamental Diagram:** We use a quadratic speed-density relationship:
  $$ v(\rho) = v_{max} \cdot \left(1 - \left(\frac{\rho}{\rho_{max}}\right)^2\right) $$
  This model is computationally efficient for large-scale simulations.

---

## 🚀 Features

* **Real-World Map Import:** Integration with **OpenStreetMap (OSM)** via `osmnx` to download and simulate traffic on
  real cities (e.g., Belfort, Paris).
* **Dual Simulation Engine:** Switch seamlessly between Cellular and Fluid models.
* **Dynamic Visualization:** High-performance rendering using `pygame` with zoom, pan, and real-time inspection.
* **Traffic Control:** Implementation of traffic light cycles at intersections.
* **Spatial Indexing:** Optimized rendering and collision detection using spatial hashing.
* **Multithreading:** Simulation logic runs in a separate thread to ensure UI responsiveness.

> ⚠️ The performances with big maps are insanely slow, you should prefer to use smaller maps.

---

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/lynn2910/GuyeuxMobile.git
   cd GuyeuxMobile
   ```

2. **Install dependencies:**<br>
   It is recommended to use a virtual environment.
   ```bash
   pip install -r requirements.txt
   ```
   *Key libraries: `pygame`, `networkx`, `osmnx`, `matplotlib`, `numpy`.*

---

## 🎮 Usage

### 1. Running a Simulation

To run the simulation on an existing map file:

```bash
python src/main.py --map data/maps/belfort.smap --tps 20 --visualizer
```

**Arguments:**

* `--map`: Path to the `.smap` file.
* `--tps`: Ticks Per Second (simulation speed).
* `--visualizer`: Enables the graphical interface.
* `--debug`: Enables verbose logging.

### 2. Importing Real Maps (OSM)

You can download and convert real-world data using the importer tool:

```bash
# Download by city name
python src/osm_importer.py --city "Belfort, France" --output data/maps/belfort.smap --model cellular

# Download by bounding box (North, South, East, West)
python src/osm_importer.py --bbox 47.64 47.63 6.86 6.85 --output data/maps/custom.smap --model fluid
```

### 3. Creating Custom Maps

You can create your own maps manually by editing `.smap` files.
See the [Map Format Guide](MAP_FORMAT.md) for detailed instructions on the syntax.

### 4. Controls (Visualizer)

* **Left Click + Drag:** Pan the camera.
* **Mouse Wheel:** Zoom in/out.
* **R:** Reset camera view.
* **L:** Toggle legend.
* **Hover:** Inspect node/edge details.

---

## 📂 Project Structure

```
src/
├── core/               # Core simulation logic
│   ├── graph.py        # Graph data structure & A* algo
│   ├── simulation.py   # Main loop & threading
│   └── fs/             # File parsing (.smap)
├── models/             # Mathematical models
│   ├── edges/          # Cellular & Fluid edge logic
│   └── intersections/  # Traffic light logic
├── entities/           # Vehicles & Spawners
├── ui/                 # Visualization engine (Pygame)
├── osm_importer.py     # OpenStreetMap -> .smap converter
└── main.py             # Entry point
```

---

## 📜 License

This project is for educational purposes.
