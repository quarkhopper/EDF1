from lib.KitchenController import *


class KitchenRunner:
    def __init__(self):
        self.controller = KitchenController()
        self.controller.get_event("oven_power").observe(KitchenRunner.oven_status_observer)
        self.controller.get_event("oven_power").respond(KitchenRunner.oven_status_responder)
        self.controller.get_event("master").observe(KitchenRunner.controller_watcher)

    def start(self):
        message = self.controller.set_oven_power(True)
        print(f"<Direct return from blocking function>: {message.to_string()}\n\n")
        message = self.controller.set_oven_power(True)
        print(f"<Direct return from blocking function>: {message.to_string()}\n\n")


    @staticmethod
    def oven_status_observer(message: EventMessage):
        print(f"<oven status observer>: {message.to_string()}\n\n")

    @staticmethod
    def oven_status_responder(message: EventMessage):
        print(f"<oven status responder>: {message.to_string()}\n\n")

    @staticmethod
    def controller_watcher(message: EventMessage):
        print(f'<controller watcher subscribed to master event>: {message.to_string()}\n\n')


if __name__ == '__main__':
    singleton_runner = KitchenRunner()
    singleton_runner.start()
