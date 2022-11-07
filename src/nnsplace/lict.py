"""
Lict
"""
from collections.abc import Mapping
from typing import List, TypeVar, Iterator

V = TypeVar('V')


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

    def items(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return enumerate(self.lst)

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


if __name__ == "__main__":
    a = Lict([0] * 8)
    for i in a:
        a[i] = i * i
    for i, v in a.items():
        print(f'{i}: {v}')
    print(3 in a)
