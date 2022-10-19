class Lict:
    def __init__(self, lst):
        self.rng = range(len(lst))
        self.lst = lst

    def items(self):
        return enumerate(self.lst)

    def __getitem__(self, key):
        return self.lst.__getitem__(key)

    def __setitem__(self, key, new_value):
        self.lst.__setitem__(key, new_value)

    def __iter__(self):
        return iter(self.rng)

    def __contains__(self, value):
        return value in self.rng

    def __len__(self):
        return len(self.rng)

    def values(self):
        return iter(self.lst)


if __name__ == "__main__":
    a = Lict([0] * 8)
    for i in a:
        a[i] = i * i
    for i, v in a.items():
        print(f'{i}: {v}')
    print(3 in a)
