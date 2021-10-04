import json
import uuid


class Recipe:

    def __init__(self, name: str, ingredients: {}, temperature: int, bake_time: int):
        self.name = name
        self.ingredients = ingredients
        self.temperature = temperature
        self.bake_time = bake_time

    def to_dict(self) -> {}:
        return {
            "name": self.name,
            "ingredients": self.ingredients,
            "temperature": self.temperature,
            "bake_time": self.bake_time
        }

    @staticmethod
    def from_dict(data: {}) -> 'Recipe':
        return Recipe(data["name"], data["ingredients"], data["temperature"], data["bake_time"])


class BakedGood:
    def __init__(self, recipe_name: str):
        self.id = uuid.uuid4()
        self.name = recipe_name
        self.temperature = 0
        self.time_baking = 0

    def to_dict(self) -> {}:
        return {
            "id": str(self.id),
            "name": self.name,
            "temperature": self.temperature,
            "time_baking": self.time_baking,
        }

    @staticmethod
    def from_dict(data: {}) -> 'BakedGood':
        obj = BakedGood(data["name"])
        obj.id = uuid.UUID(data["id"])
        obj.name = data["name"]
        obj.temperature = data["temperature"]
        obj.time_baking = data["time_baking"]
        return obj
