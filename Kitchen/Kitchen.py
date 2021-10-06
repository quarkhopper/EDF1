"""
Kitchen.py
This script is intended to run as a separate process and simulate a communication target outside the EDF. 
Run "python Kitchen.py" in the terminal to get it started. Two files will be created in the project root /Data dir:
kitchen_state: will contain the current state updated every cycle and will contain information on oven status, orders,
    and baked goods cooling on the rack
kitchen_command: write to this file to send commands to the kitchen. Format: [{"command_name": parameters}]
"""

import os
import sys
import time
from os.path import exists

sys.path.append('..')
from lib.Common import *

ingredient_types = ("sugar", "butter", "flour", "eggs")
comm_state_path = "../Data/kitchen_state"
comm_command_path = "../Data/kitchen_commands"


class CookBook:
    """
    recipes contain the name of the baked good, amounts of ingredients in required units, bake temperature and
    bake time
    """
    recipes = {
        "cake": Recipe("cake", {"sugar": 3, "butter": 3, "flour": 4, "eggs": 3}, 350, 30),
        "cookies": Recipe("cookies", {"sugar": 5, "butter": 4, "flour": 4, "eggs": 2}, 375, 10)
    }


class Kitchen:
    ambient_temp = 70
    garbage_size = 10

    def __init__(self):
        """
        Initial state of the kitchen. Starts with oven off and at ambient temperature, no orders, nothing on the rack,
        no ingredients in stock.
        """
        self.oven_on = False
        self.oven_temperature = Kitchen.ambient_temp
        self.oven_set = 0
        self.goods_in_oven = None
        # what is in stock
        self.ingredient_stock = {}
        # the balance of what is in stock to what is
        # needed to back everything in the orders queue
        self.ingredient_balance = {}
        for ingredient in ingredient_types:
            self.ingredient_stock[ingredient] = 0
            self.ingredient_balance[ingredient] = 0

        # names of recipes waiting to be baked into baked goods
        self.orders = []
        # goods that have finished baking go on the rack
        self.rack = []

        self.shutdown = False

        # delete any leftover command file
        if exists(comm_command_path):
            os.remove(comm_command_path)

    def run_kitchen(self):
        """
        Move through all phases of the kitchen routine and sleep
        :return:
        """
        self.adjust_oven_temp()
        self.simulate_goods_in_oven()
        self.simulate_goods_on_rack()
        self.update_balances()
        self.manage_comm()

        time.sleep(0.1)

    def adjust_oven_temp(self):
        """
        Adjust the temperature of the oven to simulate heating/cooling to the set point or to ambient temperature
        if off.
        :return:
        """
        if self.oven_on:
            if self.oven_temperature > self.oven_set:
                self.oven_temperature -= 1
            elif self.oven_temperature < self.oven_set:
                self.oven_temperature += 1
        else:
            self.oven_temperature -= 1

        self.oven_temperature = max(self.oven_temperature, Kitchen.ambient_temp)

    def simulate_goods_in_oven(self):
        """
        Simulate baked goods cooking. Temperature is instantly affected by the oven temperature. Food will only start
        to bake at the proper temperature. Orders for goods which there are not enough stock ingredients to back will be
        put at the back of the order queue and not baked.
        :return:
        """
        if self.goods_in_oven is None:
            if len(self.orders) > 0:
                # move the next order into the oven
                next_order = self.orders.pop(0)
                recipe = CookBook.recipes[next_order]
                baked_good = self.prepare_order(recipe)
                if baked_good is not None:
                    self.goods_in_oven = baked_good
                    self.oven_set = recipe.temperature
                else:
                    # put it at the back - not enough ingredient to bake it now
                    self.orders.append(next_order)
            else:
                self.oven_set = Kitchen.ambient_temp
        else:
            """
            adjust the temperature of whatever is in the oven. Start the bake timer when the temperature matches
            the recipe temperature of the item
            """
            recipe = CookBook.recipes[self.goods_in_oven.name]
            self.goods_in_oven.temperature = self.oven_temperature
            if self.oven_temperature == recipe.temperature:
                self.goods_in_oven.time_baking += 1

            if self.goods_in_oven.time_baking == recipe.bake_time:
                self.rack.append(self.goods_in_oven)
                self.goods_in_oven = None

    def simulate_goods_on_rack(self):
        """
        Simulate food cooling on the rack after baking
        :return:
        """
        for baked_good in self.rack:
            baked_good.temperature = max(baked_good.temperature - 1, Kitchen.ambient_temp)

    def update_balances(self):
        """
        Update the balance table to show calculations on excess / deficit in ingredients for the waiting orders
        :return:
        """
        for ingredient in self.ingredient_balance:
            self.ingredient_balance[ingredient] = self.ingredient_stock[ingredient]

        for ingredient, stock in self.ingredient_stock.items():
            for order in iter(self.orders):
                recipe = CookBook.recipes[order]
                self.ingredient_balance[ingredient] -= recipe.ingredients[ingredient]

    def prepare_order(self, recipe: Recipe) -> BakedGood or None:
        """
        use ingredients to prepare the order
        return none if insufficient ingredients
        :param recipe: the recipe to be prepared
        :return: an unbaked good, if there are sufficient ingredients
        """
        if not self.check_sufficient_ingredients(recipe):
            return None
        for ingredient in self.ingredient_stock:
            self.ingredient_stock[ingredient] -= recipe.ingredients[ingredient]
        return BakedGood(recipe.name)

    def check_sufficient_ingredients(self, recipe: Recipe) -> bool:
        """
        Check if there are sufficient ingredients to bake a good from the recipe
        :param recipe: the recipe to be prepared
        :return: True if the baked good can be prepared from the recipe
        """
        for ingredient in recipe.ingredients:
            if self.ingredient_stock[ingredient] - recipe.ingredients[ingredient] < 0: return False

        return True

    def manage_comm(self):
        """
        Manage all operations for writing to the state file and reading from the command file
        :return:
        """
        sync_state = {}
        command = str()
        if exists(comm_command_path):
            command_file = open(comm_command_path, "r+")
            command_json = command_file.read()
            command_file.close()
            if command_json:
                if exists(comm_command_path):
                    os.remove(comm_command_path)
                try:
                    commands = json.loads(command_json)
                    parse_kitchen_commands(self, commands)
                except Exception as ex:
                    print(ex)
        else:
            command_file = open(comm_command_path, "w")
            command_file.close()

        """
        prepare to serialize the kitchen state information to json for writing
        """
        app_state = {
            "recipes": [],
            "oven_on": self.oven_on,
            "oven_set": self.oven_set,
            "oven_temperature": self.oven_temperature,
            "stock": self.ingredient_stock,
            "balance": self.ingredient_balance,
            "orders": self.orders,
            "in_oven": None,
            "bake_time_left": 0,
            "rack": [],
        }
        for item in self.rack:
            app_state["rack"].append(item.to_dict())
        if self.goods_in_oven is not None:
            app_state["in_oven"] = self.goods_in_oven.to_dict()
            recipe = CookBook.recipes[self.goods_in_oven.name]
            app_state["bake_time_left"] = recipe.bake_time - self.goods_in_oven.time_baking
        for recipe in CookBook.recipes.values():
            app_state["recipes"].append(recipe.to_dict())

        sync_state = json.dumps(app_state)
        state_file = open(comm_state_path, "w")
        state_file.write(sync_state)
        state_file.close()

    """
    External commands: 
    """

    def add_order(self, baked_good_type: str):
        if baked_good_type in CookBook.recipes:
            self.orders.append(baked_good_type)

    def take_from_rack(self, baked_good_id: str):
        take_this = next((x for x in self.rack if x.id == baked_good_id), None)
        if take_this is not None:
            self.rack.remove(take_this)

    def stock(self, ingredients: {}):
        for ingredient in ingredient_types:
            if ingredient in ingredients:
                self.ingredient_stock[ingredient] += ingredients[ingredient]

    def set_oven_on(self, state):
        self.oven_on = state
        if not self.oven_on:
            self.oven_set = 0

    def shutdown(self, _):
        self.shutdown = True

    def start_kitchen(self):
        while True:
            self.run_kitchen()
            if self.shutdown:
                print("shutting down kitchen...")
                # always turn off the oven when you leave the kitchen
                self.set_oven_on(state=False)
                break

    """
    Static methods
    """


"""
These commands can be called by adding them to a list in the command file. Format is {"command_name": parameters}
Multiple commands can be sent at once. 
EXAMPLE:
[
	{"add_order": "cake"}, 
	{"add_order": "cookies"},
	{"stock": {
		"sugar": 10,
		"butter": 10,
		"flour": 10,
		"eggs": 10
	}},
	{"set_oven_on":true}
]
"""

command_map = {
    "add_order": Kitchen.add_order,  # type_of_baked_good
    "take_from_rack": Kitchen.take_from_rack,  # uuid
    "stock": Kitchen.stock,  # {} ingredients
    "set_oven_on": Kitchen.set_oven_on,  # bool
    "shutdown": Kitchen.shutdown  # end the app, no args
}


def parse_kitchen_commands(kitchen: Kitchen, commands: []):
    """
    Call the function appropriate for the command issued
    :param kitchen:
    :param commands:
    :return:
    """
    try:
        for command in commands:
            command_name, args = list(command.items())[0]
            if command_name in command_map:
                method = command_map[command_name]
                try:
                    method(kitchen, args)
                except Exception as ex:
                    print(ex)
    except Exception as ex:
        print(ex)


if __name__ == '__main__':
    singleton_kitchen = Kitchen()
    singleton_kitchen.start_kitchen()
