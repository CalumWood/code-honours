from __future__ import annotations
import qiskit

REGISTER_SIZE = 4
BACKEND = qiskit.BasicAer.get_backend('qasm_simulator')

class Quantum_runner:
    def __init__(self, actions: dict[Player, Action]):
        register_size = sum([len(action.data['Targets']) for action in actions.values()])
    
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
            for target in action.data['Targets']:
                self.nodes[target] = index
                if player.id == 0:
                    self.circuit.x(self.qreg_q[index])
                index +=1
        
        # perform swaps on selected nodes
        for player, action in actions.items():
            print(action.swaps)
            for (x, y) in action.data['Swaps']:
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

class Player:
    players = {}
        
    def __init__(self, name):
        self.id = len(Player.players) + 1
        
        self.name = name
        Player.players[name] = self
        print(f"player created: {self.name}")
    
    def __str__(self) -> str:
        return str(self.name)
    
    def toJSON(self):
        return self.id
    
    # for server login
    def get(name):
        user = Player.players.get(name)
        if user is None:
            Player.players[name] = Player(name)
            user = Player.get(name)
        return user
    
    # def get_id(id):
    #     user = Player.players.get(name)
    #     if user is None:
    #         Player.players[name] = Player(name)
    #         user = Player.get(name)
    #     return user
    
    def is_authenticated(self):
        return True        
    def is_active(self):
        return True
    def is_anonymous(self):
        return False
    def get_id(self):
        return self.id
    
class Node:
    ID_counter: int = 0

    def __init__(self, name):        
        self.id = Node.ID_counter
        Node.ID_counter += 1
        
        self.name: str = name
        self.connections: set[Node] = set()
        self.set_state()

    def connect_node(self, node: Node):
        self.connections.add(node)

    def connect_nodes(self, nodes: list[Node]):
        self.connections.union(nodes)

    def set_state(self, player=None):     
        if player == None:
            self.state = 0
        else:
            self.state = player.id
    
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
        return hash(self.id)
    
    def __ne__(self, other):
        return not self == other
            
    def node_info(self):
        return {"id": self.id, "label": self.name, "group": self.state }

    def connections_info(self):
        return [frozenset({self.id, connection.id}) for connection in self.connections]

class Map:
    def __init__(self, data, players: list[Player]=[]):
        self.players = players
        self.slots = []
        nodes: dict[str, Node] = {}
        for key in data.keys():
            node = Node(key)
            if 'Slot' in node.name:
                self.slots.append(node)
            nodes[key] = node
            
        for key, value in data.items():
            for node in value:
                nodes[key].connect_node(nodes[node])
        self.nodes = nodes
    
    def add_player(self, player):
        self.players.append(player)
        if len(self.slots) > 0:
            slot = self.slots.pop()
            print(f"{player.name} added to {slot.name}")
            slot.set_state(player)
            
    def get_nodes(self):
        return [node.node_info() for node in self.nodes.values()]
    
    def get_connections(self):
        sets = [node.connections_info() for node in self.nodes.values()]
        sets = set([item for items in sets for item in items])
        return [{"from": list(connection)[0], "to": list(connection)[1], "id": id} for id, connection in enumerate(sets)]
        
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
    
class Action:
    def __init__(self, player: Player, phases) -> None:
        self.player: Player = player
        self.data = {phase: [] for phase in phases}
        # self.targets: list[Node] = []
        # self.swaps: list[tuple[Node, Node]] = []
        # self.phase: str = Action.phases.keys()[0]
    
    def check_status(self, phase):
        print(phase)
        if phase in self.data.keys() or not phase: return True
        return False if not self.data[phase] else True
    
    def set_phase(self, phase, data):
        self.data[phase] = data
        print(self.data)

    def get_target(self, choices):
        x = self.options_check(f"Player {self.player.name}, enter target node: ", 
                    [choice for choice in choices if choice not in self.targets])
        
        self.targets.append(x)
    
    def get_swap(self, choices):        
        if input(f"Player {self.player.name}, do you want to swap y/n: ") != "y": return    
                
        x = self.options_check(f"Player {self.player.name}, enter origin Node: ", self.targets)
        
        options = set(self.targets) | choices
        options.remove(x)
        y = self.options_check(f"Player {self.player.name}, enter swap Node: ", options)

        self.swaps.append((x, y))
    
    # def set_phase(self, data):
    #     self.phases[self.phase](data)
        
    def options_check(self, msg, options, err="error - try again: "):
        print(f"Options: {','.join(options)}")
        x = input(msg)
        while(x not in options):
            x = input(err)
        return x
    
class Turn:
    def __init__(self, game) -> None:
        self.phases = {"Targets": [1, self.get_target_choices], "Swaps": [2, self.get_swap_choices]}
        self.game = game
        self.actions = {player: Action(player, self.phases.keys()) for player in self.game.players}
        self.phase = 0
        
    def get_phase_key(self):
        print( f"{self.phase} - {len(self.phases.keys())}")
        return list(self.phases.keys())[self.phase] if self.phase < len(self.phases.keys()) else None
    
    def check_phase_status(self):
        for action in self.actions.values():
            if not action.check_status(self.get_phase_key()): return False
        return True
    
    def check_status(self):
        return self.phase == len(self.phases.keys())
    
    def next_phase(self):
        self.phase += 1
        print(f"next phase - {self.get_phase_key()} - {self.check_phase_status()}")
        if not self.get_phase_key(): return True
                
    def get_phase(self):
        return self.phases.get(self.get_phase_key())
    
    def get_action(self, player):
        return self.actions[player]

    def get_player_choice(self, player):
        choices = self.get_phase()[1](player)
        return choices, self.get_phase_key()
    
    def set_player_choice(self, player, data):
        self.actions[player].set_phase(self.get_phase_key(), data)
        status = self.check_phase_status()
        print(status)
        if status:
            self.next_phase()
        return status
    
    def get_target_choices(self, player):
        return [[value.id for value in self.game.map.possible_targets(player).values()]]
    
    def get_swap_choices(self, player):
        sources = self.get_action(player).data['Targets']
        targets = []
        for action in self.actions.values():
            targets += action.data['Targets']
        
        return [sources, targets]
        # choices = set().union(*[action.targets for (key, action) in self.actions.items() if key != player])
        # return choices, set(self.get_action(player).targets) | choices


    
class Game:
    def __init__(self, players: set[Player] = set(), map=None):
        self.map: Map = Map(map_test)
        self.players: set[Player] = players
        self.turn = None
        self.turns = 0
        if map: self.map = Map(map, self.players)
        print("game created")

    def add_player(self, player):
        print(player.id)
        if player not in self.players:
            self.players.add(player.id)
            self.map.add_player(player)
            print(str(self.players) + '\n')
        
    def get_players_list(self):
        print(self.players)
        return [player for player in self.players]
        
    def set_map(self, map):
        self.map = Map(map, self.players)
    
    def get_map(self):
        return self.map
    
    phases = ["Targets", "Swaps"]
    
    def get_phase(self):
        return
    
    def get_action_requests(self, player):
        return self.turn.get_player_choice(player if player is not int else player.id)
    
    def set_action_requests(self, player, data):
        done = self.turn.set_player_choice(player, data)
        if done and self.turn.check_status():
            self.end_turn()
        return done
    
    def get_state(self):
        state = "started"
        if (self.map and len(self.players) == 2):
            state = "initialised" 
        # else if:
            
        # else:
        #     return state
        
        return state
        
    def is_initialised(self):
        if (self.map and len(self.players) == 2):
            return True
        else:
            return False
    
    def is_running(self):
        return bool(self.turn)
    
    def next_turn(self):
        self.turns += 1
        self.turn = Turn(self)
        
    def run_remote(self):
        self.next_turn()
        
    def end_turn(self):
        print("end turn")
        runner = Quantum_runner(self.turn.actions)
        results = runner.process_quantum_turn()
        print(results)
        self.map.apply_states(results)
        self.next_turn()


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
        'Slot 1': ['A'], 
        'A': ['Slot 1', 'H', 'B'], 
        'B': ['A', 'C', 'H', 'I', 'D'], 
        'C': ['B', 'D'], 
        'D': ['B', 'C', 'E', 'F', 'I'], 
        'E': ['Slot 2', 'F', 'D'], 
        'F': ['D', 'E', 'G', 'H', 'I'], 
        'G': ['H', 'F'], 
        'H': ['A', 'B', 'F', 'G', 'I'], 
        'I': ['B', 'D', 'F', 'H'],
        'Slot 2': ['E']
}