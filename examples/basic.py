import time
from typing import List, Dict, Set


def greet(name: str, dog: int) -> str:
    """
    A docstring with a bunch of really really really really really really really
    long content.

    Maybe some new lines and some example code like this:

    >>> print("hello!")
    """
    return "Hello " + name + " " + str(dog + 10)


# def greet(name: str, dog: str) -> str:
#     print("Hello!")
#     return "Bye " + name


def other(a: bool) -> str:
    return f"{a=}"


def ds2(e: List[int]) -> str:
    return str(sum(e))


def ds(e: List[int], f: Dict[str, int], g: Set[int]) -> str:
    return "OK"
