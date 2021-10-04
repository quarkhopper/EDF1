import json

import Kitchen.Kitchen

from Events import *
from os.path import exists


class KitchenController:
    command_file_path = "../Data/kitchen_commands"
    state_file_path = "../Data/kitchen_state"

    def __init__(self):
        self.events = []
        self.create_events()

    def create_events(self):
        """
        Create all events describing operation within this controller
        :return:
        """
        e_cake = Event("cake_ready", tags=["kitchen_controller", "food_ready"])
        self.events.append(e_cake)
        e_cookies = Event("cookies_ready", tags=["kitchen_controller", "food_ready"])
        self.events.append(e_cookies)
        e_food = Event("food_ready", tags=["kitchen_controller", "food_ready"])
        self.events.append(e_food)

        """
        Set up e_food to be invoked whenever the specific food type events
        are invoked. These are cascading events and give more variety to the 
        types of information that might be logged and tracked
        """
        e_cake.subscribe_event(e_food)
        e_cookies.subscribe(e_food)

        e_food_check = Event("food_check", tags=["kitchen_controller", "status"])
        self.events.append(e_food_check)

        e_food_cold = Event("food_cold", tags=["kitchen_controller", "status", "problems"])
        self.events.append(e_food_cold)

        e_food_check.subscribe_event(e_food_cold)

        e_stock_check = Event("stock_checked", tags=["kitchen_controller", "status"])
        self.events.append(e_stock_check)

        e_insuf_stock = Event("insufficient_stock", tags=["kitchen_controller", "status", "problems"])
        self.events.append(e_insuf_stock)

        e_stock_check.subscribe_event(e_insuf_stock)

        """
        Remaining events are not cascading, so simply add them to the events list
        """

        self.events.extend([
            Event("order_placed", tags=["kitchen_controller", "status"]),
            Event("stock_updated", tags=["kitchen_controller", "status"]),
            Event("shut_down", tags=["kitchen_controller", "system"]),
            Event("oven_power", tags=["kitchen_controller", "status"])
        ])

        """
        This event is an example of a single event that is fired when any other event of this controller is invoked.
        This isn't really a very realistic event since one would probably want to use the controller tag instead to find
        events to subscribe to. 
        """

        e_master = Event("master", tags=["kitchen_controller"])

        for event in self.events:
            event.subscribe_event(e_master)

        self.events.append(e_master)

    def subscribe_to_events(self, callback: EventCallback, tags=[], names=[]):
        for tag in tags:
            events = (e for e in self.events if tag in e.tags)
            self.add_callback_to_events(events, callback)
        for name in names:
            events = (e for e in self.events if name == e.name)
            self.add_callback_to_events(events, callback)

    def get_event(self, name: str) -> Event:
        return next((e for e in self.events if e.name == name), None)

    @staticmethod
    def add_callback_to_events(events: [], callback: EventCallback):
        for event in events:
            event.subscribe(callback)

    """
    Oven power action
    """

    def set_oven_power(self, on: bool) -> (bool, any, Exception):
        KitchenController.send_commands([{"set_oven_on": on}])
        event = self.get_event("oven_power")
        return event.invoke(EventInvoker(KitchenController.check_oven_power_on))

    @staticmethod
    def check_oven_power_on():
        state = KitchenController.get_kitchen_state()
        return state["oven_on"]

    """
    General supporting function 
    """

    @staticmethod
    def get_kitchen_state() -> {}:
        if not exists(KitchenController.state_file_path):
            return None
        state_file = open(KitchenController.state_file_path, "r")
        state_json = state_file.read()
        state_file.close()
        if state_json:
            return json.loads(state_json)
        else:
            return None

    @staticmethod
    def send_commands(commands: []):
        command_file = open(KitchenController.command_file_path, "w")
        command_json = json.dumps(commands)
        command_file.write(command_json)
        command_file.close()
