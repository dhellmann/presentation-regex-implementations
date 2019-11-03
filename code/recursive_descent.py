#!/usr/bin/env python

# A recursive descent parser for regular expressions.
# based on http://matt.might.net/articles/parsing-regex-with-recursive-descent/
#
# <regex> ::= <term> '|' <regex>
#             |  <term>
#
# <term> ::= { <factor> }
#
# <factor> ::= <base> { '*' }
#
# <base> ::= <char>
#            |  '(' <regex> ')'

import logging


def parse(input):

    p = 0
    group_number_n = 0

    def more():
        return p < len(input)

    def peek():
        if not more():
            raise ValueError('Out of input')
        return input[p]

    def next():
        c = peek()
        eat(c)
        return c

    def eat(expected):
        nonlocal p
        if peek() != expected:
            raise ValueError('Expected {!r} got {!r}'.format(
                expected, peek()))
        p += 1

    def regex(groups):
        # <regex> ::= <term> '|' <regex>
        #             |  <term>
        t = term(groups)

        if more() and peek() == '|':
            eat('|')
            subexpr = regex(groups)
            return Choice(t, subexpr, groups)

        return t

    def term(groups):
        # <term> ::= { <factor> }
        f = Blank(groups)

        while more() and peek() != ')' and peek() != '|':
            nextFactor = factor(groups)
            f = Concatenate(f, nextFactor, groups)

        return f

    def factor(groups):
        # <factor> ::= <base> { '*' }
        b = base(groups)

        while more() and peek() == '*':
            eat('*')
            b = Repetition(b, groups)

        return b

    def base(groups):
        # <base> ::= <char>
        #            |  '(' <regex> ')'
        nonlocal group_number_n
        p = peek()
        if p == '(':
            eat('(')
            group_number_n += 1
            r = regex(groups + [group_number_n])
            eat(')')
            return r
        return Primitive(next(), groups)

    return regex([0])


class Matchable:

    def match(self, text):
        logging.debug('\nMATCH')
        for start in range(len(text)):
            m, consumed, match = self._match(text, start, Match())
            if m:
                return match
        return None


class Match:

    def __init__(self):
        self.text = {0: ''}
        self.extents = {}

    def add(self, substr, start, end, groups):
        logging.debug('Match.add({!r}, {}, {}, {})'.format(
            substr, start, end, groups))
        logging.debug('  before text: {}'.format(self.text))
        logging.debug('  before extents: {}'.format(self.extents))
        for g in groups:

            existing = self.text.get(g, '')
            self.text[g] = existing + substr

            # Use -1 to indicate a position we have not yet filled in.
            new_start, new_end = self.extents.get(g, (-1, -1))
            logging.debug('  extent {}: {}, {}'.format(
                g, new_start, new_end))
            # Only move the start position if we haven't started this
            # extent before.
            if new_start == -1:
                new_start = start
            # Only move the end position if the extent has grown.
            if end > new_end:
                new_end = end
            self.extents[g] = (new_start, new_end)

        logging.debug('  after text: {}'.format(self.text))
        logging.debug('  after extents: {}'.format(self.extents))

    def dupe(self):
        c = Match()
        c.text = dict(self.text)
        c.extents = dict(self.extents)
        return c


class Choice(Matchable):

    def __init__(self, a, b, groups):
        self.a = a
        self.b = b
        self.groups = groups
        logging.debug(self)

    def __str__(self):
        return 'Choice({}, {}, {})'.format(self.a, self.b, self.groups)

    def _match(self, text, start, match):
        logging.debug('{}.match({!r}, {})'.format(self, text, start))
        for candidate in [self.a, self.b]:
            m, consumed, sub_match = candidate._match(
                text, start, match.dupe())
            if m:
                return (m, consumed, sub_match)
        return (False, start, match)


class Concatenate(Matchable):

    def __init__(self, first, second, groups):
        self.first = first
        self.second = second
        self.groups = groups
        logging.debug(self)

    def __str__(self):
        return 'Concatenate({}, {}, {})'.format(
            self.first, self.second, self.groups)

    def _match(self, text, start, match):
        logging.debug('{}.match({!r}, {})'.format(self, text, start))
        m, consumed, sub_match = self.first._match(
            text, start, match.dupe())
        if not m:
            return (False, start, match)
        m, consumed, sub_match2 = self.second._match(
            text, consumed, sub_match)
        if not m:
            return (False, start, match)
        return (m, consumed, sub_match2)


class Blank(Matchable):

    def __init__(self, groups):
        self.groups = groups
        logging.debug(self)
        return

    def __str__(self):
        return 'Blank({})'.format(self.groups)

    def _match(self, text, start, match):
        logging.debug('{}.match({!r}, {})'.format(self, text, start))
        return (True, start, match)


class Repetition(Matchable):

    def __init__(self, internal, groups):
        self.internal = internal
        self.groups = groups
        logging.debug(self)

    def __str__(self):
        return 'Repetition({}, {})'.format(self.internal, self.groups)

    def _match(self, text, start, match):
        logging.debug('{}.match({!r}, {})'.format(self, text, start))
        m, consumed, sub_match = self.internal._match(
            text, start, match.dupe())
        while m:
            m, consumed, sub_match = self.internal._match(
                text, consumed, sub_match.dupe())
        return (True, consumed, sub_match)


class Primitive(Matchable):

    def __init__(self, c, groups):
        self.c = c
        self.groups = groups
        logging.debug(self)

    def __str__(self):
        return 'Primitive({!r}, {})'.format(self.c, self.groups)

    def _match(self, text, start, match):
        logging.debug('{}.match({!r}, {})'.format(self, text, start))
        if text[start] == self.c:
            match.add(self.c, start, start+1, self.groups)
            return (True, start+1, match)
        return (False, start, match)
