from itertools import repeat


class repeat_array:
    """list with arbitrary range"""

    def __init__(self, value, size):
        """
        The function initializes an object with a value and size attribute.
        
        :param value: The value parameter is used to store the value of an object. It can be of any data
        type, such as an integer, string, or even another object
        :param size: The `size` parameter represents the size of an object or entity. It could refer to the
        physical size, such as the dimensions of an object, or it could represent a quantity or capacity,
        such as the number of elements in a list or the maximum number of items that can be stored in a
        """
        self.value = value
        self.size = size

    def __getitem__(self, key):
        """
        The `__getitem__` function returns the value associated with a given key.
        
        :param key: The `key` parameter is the index or key used to access an element in the object
        :return: The value of the attribute "value" is being returned.
        """
        return self.value

    def __len__(self):
        """
        The function returns the size of an object.
        :return: The size of the object.
        """
        return self.size

    def __iter__(self):
        """
        The function returns an iterator that repeats the value of the object a specified number of times.
        :return: The `repeat` function is being returned.
        """
        return repeat(self.value, self.size)


class shift_array(list):
    """list with arbitrary range"""

    def __new__(cls, *args, **kwargs):
        """[summary]

        Returns:
            [type]: [description]
        """
        return list.__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        """
        The function is a constructor that initializes an object with a start value of 0 and calls the
        constructor of the parent class "list".
        """
        self.start = 0
        list.__init__(self, *args, **kwargs)

    def set_start(self, start):
        """
        The function sets the value of the "start" attribute.
        
        :param start: The `start` parameter is a value that will be assigned to the `start` attribute of the
        object
        """
        self.start = start

    def __getitem__(self, key):
        """
        The `__getitem__` function returns the item at the specified index, adjusted by the `start`
        attribute.
        
        :param key: The `key` parameter is the index or slice object used to access the elements of the
        list. It can be an integer index or a slice object that specifies a range of indices
        :return: The method is returning the item at the specified index in the list.
        """
        return list.__getitem__(self, key - self.start)

    def __setitem__(self, key, newValue):
        """
        The `__setitem__` function is used to set the value of an item in a list-like object, adjusting the
        index based on the start value.
        
        :param key: The key parameter represents the index of the element in the list that you want to set a
        new value for
        :param newValue: The `newValue` parameter is the value that you want to set for the given key in the
        list
        """
        list.__setitem__(self, key - self.start, newValue)


if __name__ == "__main__":
    arr = repeat_array(1, 10)
    print(arr[4])
    for i in arr:
        print(i)

    b = shift_array([9, 4, 1, 3, 8, 7, 6, 5])
    b.set_start(10)
    print(b[14])
    for i in b:
        print(i)
