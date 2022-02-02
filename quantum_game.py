from __future__ import annotations
from cgi import print_environ
from random import choice
from re import S, X
from ssl import Options
import string
import qiskit
from numpy import pi
from sympy import false

REGISTER_SIZE = 4
BACKEND = qiskit.BasicAer.get_backend('qasm_simulator')

class Player:
    ID_counter: int = 0

    def __init__(self, name):
        self.id = Player.ID_counter
        Player.ID_counter += 1

        self.name = name
        

class Node:
    def __init__(self, name):
        self.name: string = name
        self.connections: set[Node] = set()
        self.state = None

    def connect_node(self, node: Node):
        self.connections.add(node)

    def connect_nodes(self, nodes: list[Node]):
        self.connections.union(nodes)

    def set_state(self, player=None):
        print(player)        
        if player == None:
            self.state = None
        else:
            self.state = player
    
    def __str__(self):
        return f"{self.name}"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.name == other
        elif isinstance(other, Node):
            return self.name == other.name
        else:
            return False
    
    def __hash__(self) -> int:
        return hash(self.name)
    
    def __ne__(self, other):
        return not self == other
            
            
           
    # def Map(self):
    #     self.nodes: list[Node]


class Map:
    def __init__(self, data, players: list[Player]):
        self.players = players
        nodes: dict[str, Node] = {}
        for key in data.keys():
            node = Node(key)
            if node.name == "PLAYER 1":
                node.set_state(players[0])
            elif node.name == "PLAYER 2":
                node.set_state(players[1])

            nodes[key] = node
            
        for key, value in data.items():
            for node in value:
                nodes[key].connect_node(nodes[node])
        self.nodes = nodes
        
    def is_game_done(self) -> bool:
        count = set()
        for node in self.nodes.values():
            count.add(node.state)
            if len(count) > 1: return False
        return True
    
    def apply_states(self, changes):
        for node, value in changes.items():
            print(value)
            self.nodes[node].set_state(self.players[value])
        
    def possible_targets(self, player: Player):
        actionable_nodes = self.edge_detect(player)
        return {node.name: node for node in actionable_nodes}

    def edge_detect(self, player):
        nodes = set()
        for node in self.nodes.values():
            if node.state == player:
                for connection in node.connections:
                    if connection.state != player:
                        nodes.add(connection)
        return nodes


ACTIONS = {}

class Action:
    def __init__(self, player) -> None:
        self.player: Player = player
        self.targets: list[Node] = []
        self.swaps: list[tuple[Node, Node]] = []

    def get_target(self, choices):
        x = self.options_check(f"Player {self.player.name}, enter target node: ", [choice for choice in choices if choice not in self.targets])
        
        self.targets.append(x)
    
    def get_swap(self, choices):        
        if input(f"Player {self.player.name}, do you want to swap y/n: ") != "y": return    
                
        x = self.options_check(f"Player {self.player.name}, enter origin Node: ", self.targets)
        
        options = set(self.targets) | choices
        options.remove(x)
        y = self.options_check(f"Player {self.player.name}, enter swap Node: ", options)

        self.swaps.append((x, y))
    
    def options_check(self, msg, options, err="error - try again: "):
        print(f"Options: {','.join(options)}")
        x = input(msg)
        while(x not in options):
            x = input(err)
        return x
    

class Quantum_runner:
    def __init__(self, actions: dict[Player, Action]):
        register_size = sum([len(action.targets) for action in actions.values()])
    
        self.qreg_q = qiskit.QuantumRegister(register_size, 'q')
        self.creg_c = qiskit.ClassicalRegister(register_size, 'c')
        self.nodes={}

        self.circuit = qiskit.QuantumCircuit(self.qreg_q, self.creg_c)    
        
        self.build_circuit(actions)
        self.actions: list[Action] = actions
        

    def build_circuit(self, actions: dict[Player, Action]):
        # Build the targets section ensuring one player is aiming for 1 and the other for 0
        index = 0        
        for player, action in actions.items():
            for target in action.targets:
                self.nodes[target] = index
                if player.id == 0:
                    self.circuit.x(self.qreg_q[index])
                index +=1
        
        # perform swaps on selected nodes
        for player, action in actions.items():
            print(action.swaps)
            for (x, y) in action.swaps:
                print(self.nodes[x])
                self.circuit.swap(self.qreg_q[self.nodes[x]], self.qreg_q[self.nodes[y]])
        self.measure_circuit()
        print(self.circuit)
    

    def process_quantum_turn(self):
        job = qiskit.execute(self.circuit, BACKEND, shots=1000)
        result = job.result()        
        counts = result.get_counts(self.circuit)
        val = max(counts, key=counts.get)
        
        return {node:int(val[index]) for (node, index) in self.nodes.items()}
    
    def measure_circuit(self):
        for i in range(len(self.qreg_q)):
            self.circuit.measure(self.qreg_q[i], self.creg_c[i])
    

class Game:
    def __init__(self, players: list[Player], map):
        self.map: Map = Map(map, players)       
        self.players: list[Player] = players
        print("game initialised")

    def run(self):
        print("running game")
        while not self.map.is_game_done():
            self.actions = {}

            for player in self.players:
                action = Action(player)
                self.actions[player] = self.get_player_targets(player, action)
                
            for player in self.players:
                self.actions[player] = self.get_player_swaps(player, self.actions[player])
            
            runner = Quantum_runner(self.actions)
            
            results = runner.process_quantum_turn()
            print(results)

            self.map.apply_states(results)
            
        self.end()

    def get_player_swaps(self, player, action: Action) -> list[Action]:
        print(f"\n\nPlayer - {player.name}, swap available")

        choices = set().union(*[action.targets for (key, action) in self.actions.items() if key != player])
        action.get_swap(choices)
        return action
    
    def get_player_targets(self, player, action: Action) -> list[Action]:
        print(f"\n\nPlayer - {player.name}, targets available")
        choices = self.map.possible_targets(player)
        
        for i in range(len(choices) if len(choices) < REGISTER_SIZE//2 else REGISTER_SIZE//2):
            action.get_target(choices)
        return action

    def end(self):
        print("ending game")


map_test = {
        'PLAYER 1': ['A'], 
        'A': ['PLAYER 1', 'H', 'B'], 
        'B': ['A', 'C', 'H', 'I', 'D'], 
        'C': ['B', 'D'], 
        'D': ['B', 'C', 'E', 'F', 'I'], 
        'E': ['PLAYER 2', 'F', 'D'], 
        'F': ['D', 'E', 'G', 'H', 'I'], 
        'G': ['H', 'F'], 
        'H': ['A', 'B', 'F', 'G', 'I'], 
        'I': ['B', 'D', 'F', 'H'],
        'PLAYER 2': ['E']
}

if __name__ == "__main__":
    game = Game([Player("Cal"), Player("bot")], map_test)
    game.run()
