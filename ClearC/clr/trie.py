"""
This module provides a trie data structure for char-by-char
checking whether a string matches one of many.
"""
from enum import Enum


class TrieResult(Enum):
    """
    This class enumerates possible results of checking a char against the trie's current state.
    """

    CONTINUE = 0
    FINISH = 1
    BREAK = 2


class Node:
    """
    This class is a node for the trie, with a character value and a list of children.
    """

    def __init__(self, char, string):
        self.children = []
        self.char = char
        self.string = string

    def add_child(self, child):
        """
        This function adds a node as a child to this node.
        """
        self.children.append(child)

    def add_word(self, word):
        """
        This function adds a word to this node as a branch of children for each
        character in the word.
        """
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
        """
        This function gets the child of this node with a given character value, or None
        if there is no such child.
        """
        for child in self.children:
            if child.char == char:
                return child
        return None


class Trie:
    """
    This class stores a trie of nodes, optionally initialized with
    an iterable collection of words and storing an internal state for
    walking along the trie char-by-char.
    """

    def __init__(self, words=None):
        self.roots = list()
        self.pointer = None
        self.broken = False
        if words:
            for word in words:
                self.add_word(word)

    def step(self, char):
        """
        This function steps the pointer along the trie by adding
        a given character, return a result about whether a leaf was
        reached or if there was no child with the given character along
        with the accumulated string.
        """
        if self.broken:
            return TrieResult.BREAK, None
        if not self.pointer:
            for root in self.roots:
                if root.char == char:
                    self.pointer = root
                    break
            else:
                self.broken = True
                return TrieResult.BREAK, None
        else:
            find = self.pointer.get(char)
            if find is None:
                self.broken = True
                return TrieResult.BREAK, None
            self.pointer = find

        return (
            (TrieResult.CONTINUE, self.pointer.string)
            if self.pointer.children
            else (TrieResult.FINISH, self.pointer.string)
        )

    def reset(self):
        """
        This function resets the internal state of trie-walking.
        """
        self.pointer = None
        self.broken = False

    def add_word(self, word):
        """
        This function adds a word to the root node of the trie as a
        branch from the sequence of characters.
        """
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
