
from enum import Enum

class TrieResult(Enum):
    CONTINUE = 0,
    FINISH = 1,
    BREAK = 2

class Node:

    def __init__(self, char, string):
        self.children = []
        self.char = char
        self.string = string

    def add_child(self, child):
        self.children.append(child)

    def add_word(self, word):
        if word:
            for child in self.children:
                if child.char == word[0]:
                    if len(word) > 1:
                        child.add_word(word[1:])
                    break
            else:
                new_node = Node(word[0], self.string + word[0])
                if len(word) > 1:
                    new_node.add_word(word[1:])
                self.add_child(new_node)

    def get(self, char):
        for child in self.children:
            if child.char == char:
                return child
        return None

class Trie:
    
    def __init__(self, words=[]):
        self.pointer = None
        self.roots = []
        for word in words:
            self.add_word(word)

    def step(self, char):
        if not self.pointer:
            for root in self.roots:
                if root.char == char:
                    self.pointer = root
                    break
            else:
                return TrieResult.BREAK, None
        else:
            find = self.pointer.get(char)
            if find is None:
                return TrieResult.BREAK, None
            else:
                self.pointer = find

        return ((TrieResult.CONTINUE, None)
                if self.pointer.children
                else (TrieResult.FINISH, self.pointer.string))

    def reset(self):
        self.pointer = None

    def add_word(self, word):
        if word:
            for root in self.roots:
                if root.char == word[0]:
                    if len(word) > 1:
                        root.add_word(word[1:])
                    break
            else:
                new_node = Node(word[0], word[0])
                if len(word) > 1:
                    new_node.add_word(word[1:])
                self.roots.append(new_node)


