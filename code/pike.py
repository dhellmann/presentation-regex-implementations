#!/usr/bin/env python3

# Based on the code in
# https://www.cs.princeton.edu/courses/archive/spr09/cos333/beautiful.html
# by Rob Pike.


def match(regexp, text):
    if regexp and regexp[0] == '^':
        return match_here(regexp[1:], text)
    while text:
        print('\nmatch({!r}, {!r})'.format(regexp, text))
        if match_here(regexp, text):
            return True
        text = text[1:]
    return False


def match_here(regexp, text):
    print('match_here({!r}, {!r})'.format(regexp, text))
    if not regexp:
        return True
    if len(regexp) > 1 and regexp[1] == '*':
        return match_star(regexp[0], regexp[2:], text)
    if len(regexp) == 1 and regexp[0] == '$':
        return len(text) == 0
    if text and regexp and (regexp[0] in ['.', text[0]]):
        return match_here(regexp[1:], text[1:])  # consuming memory
    return False


def match_star(c, regexp, text):
    while True:
        print('match_star({!r}, {!r}, {!r})'.format(c, regexp, text))
        if match_here(regexp, text):
            return True
        if c not in ['.', text[0]]:
            break
        text = text[1:]  # consuming memory
    return False
