from time import sleep, time
import config
from cli import debug_log


class Simulation:
    def __init__(self, graph, tps: float, visualizer=None):
        self.graph = graph
        self.vehicles = []
        self.spawners = []
        self.tps = tps
        self.tick_duration = 1.0 / tps
        self.t = 0
        self.running = False
        self.since_last_update = 0
        self.visualizer = visualizer

    def add_vehicle(self, vehicle, start_edge):
        vehicle.current_edge = start_edge
        start_edge.insert_vehicle(vehicle)
        self.vehicles.append(vehicle)

    def add_spawner(self, spawner):
        self.spawners.append(spawner)

    def remove_vehicle_safely(self, vehicle):
        try:
            self.vehicles.remove(vehicle)
        except ValueError:
            pass

    def tick(self):
        start_time = time()
        if self.since_last_update >= self.tick_duration:
            self.t += 1
            self.internal_step()
            self.since_last_update -= self.tick_duration

        if self.visualizer:
            self.visualizer.update(self.t)
            if not self.visualizer.handle_events():
                self.running = False
                return
        elapsed = time() - start_time
        self.since_last_update += elapsed

    def internal_step(self):
        # 0. Mise à jour des feux
        self.graph.update_intersections()

        # 1. Spawners
        for spawner in self.spawners:
            new_vehicle = spawner.update(self.graph)
            if new_vehicle:
                self.vehicles.append(new_vehicle)
                if config.DEBUG:
                    print(f"Spawned vehicle {new_vehicle.id} at {spawner.node}")

        # 2. Edges Update & Transfer Logic
        # On parcourt toutes les edges du graphe
        for src, dst, data in self.graph.get_edges():
            edge = data['object']

            # A. On fait avancer les voitures DANS la route
            # Elles vont s'accumuler au bout si elles ne peuvent pas sortir
            edge.update()

            # B. Logique de transfert (Spillback handling)
            # Y a-t-il un véhicule prêt à sortir ?
            if hasattr(edge, 'peek_last_vehicle') and edge.peek_last_vehicle():
                vehicle = edge.peek_last_vehicle()

                # 1. Vérification du Feu / Intersection
                can_pass = True
                intersection = self.graph.get_intersection(dst)
                if intersection:
                    can_pass = intersection.can_pass(src)

                if not can_pass:
                    # Feu Rouge : Le véhicule reste bloqué sur l'edge actuel.
                    # Comme on ne l'enlève pas (pop), il bloquera les suivants au prochain update.
                    continue

                    # 2. Vérification de la destination suivante
                vehicle.pop_next_target()  # On regarde la prochaine cible temporairement
                next_node = vehicle.next_target()

                # Remettre la cible si échec ? Non, pop_next_target modifie la liste interne
                # Si échec, il faudra gérer le cas où le path est corrompu, 
                # MAIS vehicle.next_target() ne fait que lire le chemin[0].

                transfer_success = False

                if next_node is None:
                    # Arrivé à destination finale : Il sort du système
                    edge.pop_last_vehicle()  # On l'enlève de la route
                    self.remove_vehicle_safely(vehicle)  # On l'enlève de la simu
                    transfer_success = True
                else:
                    # Tente d'entrer sur la route suivante
                    try:
                        next_edge = self.graph.get_edge(dst, next_node)

                        # C'EST ICI QUE LA MAGIE OPERE :
                        # Si next_edge.insert_vehicle renvoie False (Pleine), 
                        # alors transfer_success reste False.
                        if next_edge.insert_vehicle(vehicle):
                            # Succès ! On l'enlève de l'ancienne route
                            edge.pop_last_vehicle()
                            vehicle.current_edge = next_edge
                            transfer_success = True
                        else:
                            # Echec (Bouchon devant) : 
                            # Le véhicule reste sur 'edge' (ancienne route).
                            # On doit remettre le next_target qu'on a pop ?
                            # Vehicle.pop_next_target() a retiré le noeud de la liste path.
                            # Il faut le remettre car on n'a pas bougé !
                            vehicle.path.insert(0, next_node)

                    except RuntimeError:
                        # Route inexistante (Erreur de pathfinding ou map)
                        edge.pop_last_vehicle()
                        self.remove_vehicle_safely(vehicle)
