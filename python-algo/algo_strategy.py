import gamelib
import random
import math
import warnings
from sys import maxsize
import json
import time

build_pos = {
    "turn 0": {
        "wall": [
            [0, 13],
            [1, 13],
            [2, 13],
            [3, 13],
            [4, 12],
            [5, 11],
            [6, 10],
            [7, 10],
            [8, 9],
            [9, 9],
            [10, 9],
            [11, 9],
            [13, 9],
            [14, 9],
            [16, 9],
            [17, 9],
            [18, 9],
            [19, 9],
            [20, 10],
            [21, 10],
            [22, 11],
            [23, 12],
            [24, 13],
            [25, 13],
            [26, 13],
            [27, 13],
            [1, 12],
            [26, 12],
        ],
        "turret": [[3, 12], [24, 12], [7, 9], [20, 9], [12, 8], [15, 8]],
    },
    "turn 1": {
        "wall": [[12, 9], [15, 9]],
        "turret": [],
    },
    "turn 2": {
        "wall": [[4, 11], [5, 10], [22, 10], [23, 11]],
        "turret": [],
    },
    "turn 3": {
        "wall": [],
        "turret": [],
    },
}

upgrade_pos = {
    "turn 0": {
        "wall": [],
        "turret": [],
    },
    "turn 1": {
        "wall": [[0, 13], [27, 13]],
        "turret": [],
    },
    "turn 2": {
        "wall": [],
        "turret": [],
    },
    "turn 3": {
        "wall": [[26, 13], [26, 12]],
        "turret": [[7, 9]],
    },
}

attack_hole_pos = {
    "wall": {
        "left_corner": [[0, 13], [1, 13], [1, 12]],
        "right_corner": [[27, 13], [26, 13], [26, 12]],
    },
}

# send spouts starting from round 4
spout_attack_pos_with_number = {
    "left": [([21, 7], 5), ([23, 9], 1000)],
    "right": [([6, 7], 5), ([4, 9], 1000)],
}

# wall front layers
wall_front_layers = (
    [
        [0, 13],
        [1, 13],
        [1, 12],
        [26, 12],
        [26, 13],
        [27, 13],
        [2, 13],
        [3, 13],
        [4, 12],
        [23, 12],
        [24, 13],
        [25, 13],
        [5, 11],
        [6, 10],
        [7, 10],
        [20, 10],
        [21, 10],
        [22, 11],
        [8, 9],
        [9, 9],
        [10, 9],
        [11, 9],
        [12, 9],
        [13, 9],
        [14, 9],
        [15, 9],
        [16, 9],
        [17, 9],
        [18, 9],
        [19, 9],
    ],  # layer 0
    [
        [4, 11],
        [5, 10],
        [6, 9],
        [5, 12],
        [6, 11],
        [21, 11],
        [22, 12],
        [21, 9],
        [22, 10],
        [23, 11],
        [8, 10],
        [9, 10],
        [10, 10],
        [11, 10],
        [12, 10],
        [13, 10],
        [14, 10],
        [15, 10],
        [16, 10],
        [17, 10],
        [18, 10],
        [19, 10],
        [20, 10],
    ],  # layer 1
)

# vital turret positions
vital_turret_pos = [
    [3, 12],
    [24, 12],
    [7, 9],
    [20, 9],
    [12, 8],
    [15, 8],
    [9, 8],
    [18, 8],
]

# support positions
vitual_support_pos = [[8, 8], [19, 8]]


# SP left after each turn:
# turn 0: 0
# turn 1: 1
# turn 2: 2
# turn 4: 1.1


class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()

    def on_game_start(self, config):
        """
        Read in config and perform any initial setup here
        """
        gamelib.debug_write("Configuring your custom algo strategy...")
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write(
            "Performing turn {} of your custom algo strategy".format(
                game_state.turn_number
            )
        )
        game_state.suppress_warnings(
            True
        )  # Comment or remove this line to enable warnings.

        self.overall_strategy(game_state)

        game_state.submit_turn()

    def overall_strategy(self, game_state):
        # go through the predefined routine
        self.predefined_routine(game_state)

        # fix defense
        self.fix_defense_and_upgrade(game_state)

        # remove low health defence for SP
        self.remove_low_health_defence(game_state)

        # attack if it's the right turn
        self.spout_attack(game_state, "left")

    def predefined_routine(self, game_state):
        global build_pos, upgrade_pos

        # predefined only up to turn 3
        if game_state.turn_number >= 4:
            return
        turn_str = "turn {}".format(game_state.turn_number)
        # build
        game_state.attempt_spawn(WALL, build_pos[turn_str]["wall"])
        game_state.attempt_spawn(TURRET, build_pos[turn_str]["turret"])
        # upgrade
        game_state.attempt_upgrade(upgrade_pos[turn_str]["wall"])
        game_state.attempt_upgrade(upgrade_pos[turn_str]["turret"])

    def spout_attack(self, game_state, attack_direction):
        global attack_hole_pos, spout_attack_pos_with_number

        # remove corner walls to prepare for attack
        if game_state.turn_number % 4 == 3:
            if attack_direction == "left":
                game_state.attempt_remove(attack_hole_pos["wall"]["left_corner"])
            elif attack_direction == "right":
                game_state.attempt_remove(attack_hole_pos["wall"]["right_corner"])

        # attack from corners
        if game_state.turn_number >= 4 and game_state.turn_number % 4 == 0:
            for pos, number in spout_attack_pos_with_number[attack_direction]:
                game_state.attempt_spawn(SCOUT, pos, number)

        # do nothing if it's not the right turn to either attack or remove walls to prepare for attack

    def fix_defense_and_upgrade(self, game_state):
        global wall_front_layers, vital_turret_pos, vitual_support_pos, attack_hole_pos

        # if there is a hole in the wall, fill it
        for wall_pos in wall_front_layers[0]:
            # when it's the attack turn, the holes are intentional
            if game_state.turn_number % 4 == 0 and (
                wall_pos in attack_hole_pos["wall"]["left_corner"]
                or wall_pos in attack_hole_pos["wall"]["right_corner"]
            ):
                continue
            # fill the wall
            if not game_state.contains_stationary_unit(wall_pos):
                game_state.attempt_spawn(WALL, wall_pos)

        # if there is a hole in the turret, fill it
        for turret_pos in vital_turret_pos:
            if not game_state.contains_stationary_unit(turret_pos):
                game_state.attempt_spawn(TURRET, turret_pos)

        # upgrade corner walls
        game_state.attempt_upgrade(attack_hole_pos["wall"]["left_corner"])
        game_state.attempt_upgrade(attack_hole_pos["wall"]["right_corner"])

        # try to upgrade the turret
        for turret_pos in vital_turret_pos:
            if game_state.contains_stationary_unit(turret_pos):
                game_state.attempt_upgrade([turret_pos])

        # strengthen the wall with a second layer
        for wall_pos in wall_front_layers[1]:
            # the second layer does not contain any intentional holes for attack
            if not game_state.contains_stationary_unit(wall_pos):
                game_state.attempt_spawn(WALL, wall_pos)

        # try to place support
        for support_pos in vitual_support_pos:
            if not game_state.contains_stationary_unit(support_pos):
                game_state.attempt_spawn(SUPPORT, support_pos)

    def remove_low_health_defence(self, game_state):
        global wall_front_layers, vital_turret_pos, vitual_support_pos

        remove_locations = []
        for locations in [
            wall_front_layers[0],
            wall_front_layers[1],
            vital_turret_pos,
            vitual_support_pos,
        ]:
            for pos in locations:
                if len(game_state.game_map[pos[0], pos[1]]) == 0:
                    continue
                if (
                    game_state.game_map[pos[0], pos[1]][0].health
                    <= game_state.game_map[pos[0], pos[1]][0].max_health / 2
                ):
                    remove_locations.append(pos)

        if len(remove_locations) > 0:
            game_state.attempt_remove(remove_locations)
    
    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
