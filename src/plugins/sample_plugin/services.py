class Greeter:
    def __init__(self, greeting: str = "Hello", target: str = "World"):
        self.greeting = greeting
        self.target = target

    def greet(self) -> str:
        return f"{self.greeting}, {self.target}!"


def greeter_factory():
    return Greeter()
