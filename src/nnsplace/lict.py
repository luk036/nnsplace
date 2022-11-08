"""
Dict-like containers
"""
from collections.abc import Mapping
from typing import Iterator, List, TypeVar

V = TypeVar("V")


class Lict(Mapping[int, V]):
    """Lict

    Args:
        Mapping (_type_): _description_
    """

    def __init__(self, lst: List[V]):
        """_summary_

        Args:
            lst (List[V]): _description_
        """
        self.rng = range(len(lst))
        self.lst = lst

    def __getitem__(self, key: int) -> V:
        """_summary_

        Args:
            key (int): _description_

        Returns:
            V: _description_
        """
        return self.lst.__getitem__(key)

    def __setitem__(self, key: int, new_value: V):
        """_summary_

        Args:
            key (int): _description_
            new_value (V): _description_
        """
        self.lst.__setitem__(key, new_value)

    def __iter__(self) -> Iterator[int]:
        """_summary_

        Returns:
            Iterable: _description_
        """
        return iter(self.rng)

    def __contains__(self, key: object) -> bool:
        return key in self.rng

    def __len__(self) -> int:
        """_summary_

        Returns:
            int: _description_
        """
        return len(self.rng)

    def values(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return iter(self.lst)

    def items(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return enumerate(self.lst)


class ShiftLict(Mapping[int, V]):
    """Lict with arbitrary range"""

    def __init__(self, lst: List[V], start=0):
        """_summary_

        Args:
            lst (List[V]): _description_
        """
        self.start = start
        self.rng = range(start, len(lst) + start)
        self.lst = lst

    def set_start(self, start):
        """[summary]

        Args:
            start ([type]): [description]
        """
        self.start = start
        self.rng = range(start, len(self.lst) + start)

    def __getitem__(self, key: int) -> V:
        """[summary]

        Args:
            key ([type]): [description]

        Returns:
            V: [description]
        """
        return self.lst.__getitem__(key - self.start)

    def __setitem__(self, key: int, newValue: V):
        """[summary]

        Args:
            key (int): [description]
            newValue (V): [description]
        """
        self.lst.__setitem__(key - self.start, newValue)

    def __iter__(self) -> Iterator[int]:
        """_summary_

        Returns:
            Iterable: _description_
        """
        return iter(self.rng)

    def __contains__(self, key: object) -> bool:
        return key in self.rng

    def __len__(self) -> int:
        """_summary_

        Returns:
            int: _description_
        """
        return len(self.rng)

    def values(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return iter(self.lst)

    def items(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return zip(self.rng, self.lst)


if __name__ == "__main__":
    a = Lict([0] * 8)
    for i in a:
        a[i] = i * i
    for i, v in a.items():
        print(f"{i}: {v}")
    print(3 in a)
