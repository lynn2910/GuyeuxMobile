# 🗺️ Custom Map Format Guide (.smap)

This document explains how to create custom map files (`.smap`) for the traffic simulation. The format is text-based and
easy to edit manually.

## 📄 File Structure

A `.smap` file consists of several sections defined by keywords. The order of sections generally matters (define the
Graph first).

### 1. Graph Definition

The file **must** start with the `GRAPH` section. You must specify the simulation model in parentheses: `cellular` (
default) or `fluid`.

```text
GRAPH(cellular):
    NODE 1 (0, 0)
    NODE 2 (100, 0)
    
    # Unidirectional Edge (One-way street)
    UEDGE 1 2 distance=100 vmax=5 prob_slow=0.1
    
    # Bidirectional Edge (Two-way street)
    BEDGE 2 3 distance=50
```

> **Note:** comments (`#`) are not supported, it's there for documentation purposes

**Parameters:**

* **NODE:** `id (x, y)` - Defines an intersection or endpoint.
* **UEDGE / BEDGE:** `source_id dest_id [params]`
    * `distance`: Length of the road (meters or cells).
    * `vmax`: Maximum speed.
    * `prob_slow`: (Cellular only) Probability of random braking (0.0 - 1.0).
    * `density_max`: (Fluid only) Maximum density (vehicles/meter).

---

### 2. Intersections

Defines traffic control logic at specific nodes.

```text
INTERSECTIONS:
    TRAFFIC_LIGHT 2 duration=60
```

> `2` is the Node ID

**Types:**

* **TRAFFIC_LIGHT:** `node_id duration=ticks` - Cycles green light between incoming roads every `duration` ticks.

---

### 3. Spawners

Defines where vehicles enter the simulation automatically.

```text
SPAWNERS:
    SPAWNER 1 ratio=0.2
```

**Parameters:**

* `ratio`: Probability (0.0 - 1.0) of spawning a vehicle at each tick.

---

### 4. Vehicles (Optional)

Defines specific vehicles to exist at the start of the simulation.

```text
VEHICLES:
    CAR car_1 (1, 3)
```

**Format:**

* `CAR id (start_node, end_node)` - The simulation will calculate the shortest path.

---

## 📝 Example File

Here is a complete example of a simple map:

```text
GRAPH(cellular):
    # Define Nodes (x, y coordinates)
    NODE A (0, 100)
    NODE B (100, 100)
    NODE C (200, 100)
    NODE D (100, 0)
    NODE E (100, 200)

    # Define Roads
    # Horizontal road
    BEDGE A B distance=100 vmax=5
    BEDGE B C distance=100 vmax=5
    
    # Vertical road crossing at B
    BEDGE D B distance=100 vmax=3
    BEDGE B E distance=100 vmax=3

INTERSECTIONS:
    # Traffic light at the central intersection
    TRAFFIC_LIGHT B duration=40

SPAWNERS:
    # Cars enter from the edges
    SPAWNER A ratio=0.1
    SPAWNER C ratio=0.1
    SPAWNER D ratio=0.05
    SPAWNER E ratio=0.05
```

> ⚠️ Don't put the comments
