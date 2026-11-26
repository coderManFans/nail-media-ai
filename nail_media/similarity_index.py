from .image_features import distance

class BKTree:
    def __init__(self):
        self.root = None

    def add(self, key, value):
        if self.root is None:
            self.root = [key,[value],{}]
            return
        node = self.root
        while True:
            d = distance(key,node[0])
            if d == 0:
                node[1].append(value)
                return
            if d not in node[2]:
                node[2][d] = [key,[value],{}]
                return
            node = node[2][d]

    def search(self,key,radius=4):
        stack = [self.root] if self.root else []
        while stack:
            node = stack.pop()
            d = distance(key,node[0])
            if d <= radius:
                yield from node[1]
            stack.extend(child for edge,child in node[2].items() if d-radius<=edge<=d+radius)
