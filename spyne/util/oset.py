# http://code.activestate.com/recipes/576694/

from six.moves.collections_abc import MutableSet

KEY, PREV, NEXT = list(range(3))

"""This module contains an ordered set implementation from
http://code.activestate.com/recipes/576694/ """

class oset(MutableSet):
    """An ordered set implementation."""

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[PREV]
            curr[NEXT] = end[PREV] = self.map[key] = [key, curr, end]

    def extend(self, keys):
        for key in keys:
            if key not in self.map:
                end = self.end
                curr = end[PREV]
                curr[NEXT] = end[PREV] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[NEXT] = next
            next[PREV] = prev

    def __iter__(self):
        end = self.end
        curr = end[NEXT]
        while curr is not end:
            yield curr[KEY]
            curr = curr[NEXT]

    def __reversed__(self):
        end = self.end
        curr = end[PREV]
        while curr is not end:
            yield curr[KEY]
            curr = curr[PREV]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = next(reversed(self)) if last else next(iter(self))
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, oset):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

    @property
    def back(self):
        return self.end[1][0]

if __name__ == '__main__':
    print((oset('abracadabra')))
    stuff = oset()
    stuff.add(1)
    print(stuff)
    stuff.add(1)
    print(stuff)
    print((oset('simsalabim')))
    o = oset('abcde')
    print(o)
    print(o.end)

    o = oset()
    print(o.back)

    o = oset([3])
    print(o.back)
