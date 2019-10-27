#!/usr/bin/env python3

# Based on the implementation in
# https://swtch.com/~rsc/regexp/regexp1.html except that the tokens
# are a represented by a class instead of just the character (to allow
# for more operators)

import collections
import itertools
import logging

GROUP_START = '('
GROUP_END = ')'
LITERAL = 'lit'
ALTERNATE = '|'

AT_LEAST_ZERO = '*'
AT_LEAST_ONE = '+'
AT_MOST_ONE = '?'

BACKSLASH = '\\'
CONCAT = 'concat'
MATCH = 'match'

# All operator tokens
OPS = set([
    GROUP_START, GROUP_END,
    ALTERNATE,
    AT_LEAST_ZERO, AT_LEAST_ONE, AT_MOST_ONE,
])

# Unary operator tokens
UOPS = set([
    AT_LEAST_ZERO, AT_LEAST_ONE, AT_MOST_ONE,
])

# Operators that split the path through the NFA.
SPLIT_OPS = set([
    AT_LEAST_ZERO, AT_LEAST_ONE, AT_MOST_ONE,
    ALTERNATE,
])


def tokenize(s):
    "Turn a string with a regular expression into Tokens"
    # Keep track of the active groups enclosing each token. Start with
    # 0, because all tokens are in the default group.
    group_counter = itertools.count()
    groups = [next(group_counter)]

    i = 0
    while i < len(s):
        c = s[i]

        # Groups are numbered left to right when we enter them, so
        # each time we see a ( increment the group counter and add it
        # to the stack. When we see a ) remove the top group from the
        # stack.
        if c == GROUP_START:
            groups.append(next(group_counter))
        elif c == GROUP_END:
            groups.pop()

        if c in OPS:
            yield Token(c, i, c, groups)
        elif c == BACKSLASH:
            # FIXME: Handle character classes like \d
            yield Token(LITERAL, i+1, s[i+1], groups)
            # Increment i an extra time here, to move past the
            # backslash. The increment at the end of the loop will
            # then move past the character.
            i += 1
        # FIXME: Handle '.'
        else:
            yield Token(LITERAL, i, c, groups)
        i += 1


class Token:
    def __init__(self, op, pos, text, groups=None):
        self.op = op
        self.pos = pos
        self.text = text
        self.groups = list(groups or [])

    def __str__(self):
        return 'Token(op={!r}, pos={}, text={!r} groups={})'.format(
            self.op, self.pos, self.text, self.groups)

    def __repr__(self):
        return str(self)


def postfix(tokens):
    "Return tokens in postfix order."
    # The postfix representation we're building.
    post = []

    # Keep track of how many "atoms" (expression snippets) are on the
    # stack, and how many of those are part of computing alternatives.
    num_atoms = 0
    num_alternates = 0

    # Each time we enter a group we push state here so we can reset
    # the counters. Using an explicit stack like this allows us to
    # avoid recursion.
    group_state = []

    def add(item):
        logging.debug('adding %s', item)
        post.append(item)

    def flush_concat():
        # Add concatenation operators for all of the atoms on the
        # stack now.
        nonlocal num_atoms
        num_atoms -= 1
        while num_atoms > 0:
            add(Token(CONCAT, -1, ''))
            num_atoms -= 1

    def flush_alternates():
        # Add alternative operators for all of the atoms on the
        # stack. Note that this causes each alternative to be a binary
        # choice, which is OK because grouping for alternatives is
        # commutative.
        nonlocal num_alternates
        while num_alternates > 0:
            add(Token(ALTERNATE, -1, '|'))
            num_alternates -= 1

    def close_subexpression():
        flush_concat()
        flush_alternates()

    for t in tokens:
        logging.debug('\nt={} natoms={} nalts={}, group_state={}'.format(
            t, num_atoms, num_alternates, group_state))

        if t.op == GROUP_START:
            # Due to precedence rules, entering a group means we need
            # to resolve the most recent concatenation.
            if num_atoms > 1:
                num_atoms -= 1
                add(Token(CONCAT, -1, ''))

            # Save and reset the counters for inside the group.
            group_state.append((num_atoms, num_alternates))
            num_alternates = 0
            num_atoms = 0

        elif t.op == GROUP_END:
            # At the end of a group resolve any open operations then
            # restore the counters from outside of the group by
            # popping the stack.
            close_subexpression()
            num_atoms, num_alternates = group_state.pop()
            num_atoms += 1

        elif t.op == ALTERNATE:
            # Each time we see a | we need to ensure all of the
            # existing expressions are closed to honor the precedence
            # rules. We count how many times we see a | so that we can
            # add the appropriate operators at the end of the
            # (sub)expression.
            flush_concat()
            num_alternates += 1

        elif t.op in OPS:
            # Normal operations are added verbatim.
            add(t)

        elif t.op == LITERAL:
            # If there are already multiple expressions concatenate
            # them before adding the new literal value.
            if num_atoms > 1:
                num_atoms -= 1
                add(Token(CONCAT, -1, ''))
            add(t)
            num_atoms += 1

        else:
            raise ValueError('unhandled token {}'.format(t))

    # When we reach the end of the string expression, close
    # everything.
    close_subexpression()

    return post


def post2nfa(tokens):
    "Turn the postfix order token set into an NFA."

    stack = []
    all_states = []

    def show_stack():
        logging.debug('stack: %s', stack)

    def pop():
        e = stack.pop()
        logging.debug('popping %s', e)
        return e

    def push(f):
        logging.debug('pushing %s', f.n)
        stack.append(f)
        show_stack()

    for t in tokens:
        logging.debug('\n{}'.format(t))
        show_stack()

        if t.op == LITERAL:
            # Push a new fragment with no links.
            #
            #  * - s ->
            #
            s = State(t, None, None)
            all_states.append(s)
            f = Frag(s, [s.set_out1])
            push(f)

        elif t.op == CONCAT:
            # Chain the 2 items on top of the stack together in order
            # and replace them with a new fragment that starts with
            # the first one and ends with the second.
            #
            #  * - e1 -> * - e2 ->
            #
            e2 = pop()
            e1 = pop()
            e1.patch(e2.start)
            f = Frag(e1.start, e2.out_setters)
            push(f)

        elif t.op == ALTERNATE:
            # Create a new fragment that chooses between the 2 items
            # on top of the stack and set things up so we can link
            # their out states to the same place.
            #
            #    /- e1 ->
            # * -|
            #    \- e2 ->
            #
            e2 = pop()
            e1 = pop()
            s = State(t, e1.start, e2.start)
            all_states.append(s)
            f = Frag(s, e1.out_setters + e2.out_setters)
            push(f)

        elif t.op == AT_LEAST_ZERO:
            # Make the expression on top of the stack optional by
            # replacing it with a new fragment that bypasses the
            # existing expression through out1 but allows it through
            # out2 and setting the out link from the existing
            # expression back to the new state.
            #
            #  /-> e \
            #  |     |
            #  * <---/
            #  |
            #  \------>
            #
            e = pop()
            s = State(t, e.start, None)
            all_states.append(s)
            s.set_out2(e.start)  # s -> e
            e.patch(s)  # e -> s
            f = Frag(s, [s.set_out1])  # s -> next
            push(f)

        elif t.op == AT_LEAST_ONE:
            # Require one instance of the expression on top of the
            # stack, linking the new state back to the start state of
            # that expression. Set up so the out2 link can be used for
            # the "no more occurrences" path.
            #
            #  /----\
            #  |    |
            #  V    |
            #  e -> * ->
            #
            e = pop()
            s = State(t, e.start, None)
            all_states.append(s)
            e.patch(s)
            f = Frag(e.start, [s.set_out2])
            push(f)

        elif t.op == AT_MOST_ONE:
            # Allow at most one instance of the expression on top of
            # the stack
            #
            #  /-> e ->
            #  |
            #  * ----->
            #
            e = pop()
            s = State(t, e.start, None)
            all_states.append(s)
            f = Frag(s, e.out_setters + [s.set_out2])
            push(f)

        else:
            raise ValueError('Unhandled token {}'.format(t))

    # Take the final item off of the stack as our expression.
    e = pop()
    if stack:
        # We should have had only one expression on the stack before
        # popping. If we have something left, we messed up combining
        # the fragments.
        raise ValueError(stack)

    # Add an explicit "match" state so the code that walks the NFA can
    # tell when it is done.
    logging.debug('\nadding matchstate')
    matchstate = State(Token(MATCH, -1, ''), None, None)
    all_states.append(matchstate)
    e.patch(matchstate)

    return (e.start, all_states)


class State:
    "One state in the NFA."

    _counter = itertools.count(0)

    def __init__(self, token, out1, out2):
        # Give each state a uniq id
        self.n = 's{}'.format(next(self._counter))
        self.token = token
        # The way we build the NFA means there will only be at most 2
        # outgoing links from any state.
        self.out1 = out1
        self.out2 = out2
        logging.debug('new %s', self)

    def set_out1(self, state):
        logging.debug('set_out1({}, {})'.format(self.n, state.n))
        if self.out1 != None:
            logging.warning('WARNING: resetting from {}'.format(
                self.out1.n))
        self.out1 = state

    def set_out2(self, state):
        logging.debug('set_out2({}, {})'.format(self.n, state.n))
        if self.out2 != None:
            logging.warning('WARNING: resetting from {}'.format(
                self.out.n))
        self.out2 = state

    def __repr__(self):
        out1 = self.out1.n if self.out1 else None
        out2 = self.out2.n if self.out2 else None
        return 'State({}, token={}, out1={}, out2={})'.format(
            self.n, self.token, out1, out2)


class Frag:
    "An NFA fragment."

    _counter = itertools.count(0)

    def __init__(self, start, out_setters):
        # Give each fragment a unique ID
        self.n = 'f{}'.format(next(self._counter))
        # Remember the start state for this fragment
        self.start = start
        # Each fragment keeps track of the callables to use to set its
        # output state. We need a list because when we have a choice
        # we have multiple paths. We keep a list of callables so our
        # owner can control which output link of a given state is set.
        self.out_setters = out_setters
        logging.debug('new %s', self)

    def __repr__(self):
        return 'Frag({}, {}-{})'.format(
            self.n, self.start.n, self.start.token)

    def patch(self, start):
        for os in self.out_setters:
            os(start)


def match(pattern, s):
    "Parse a pattern and match it against the input text s."
    logging.debug('pattern: %s', pattern)

    tokens = list(tokenize(pattern))
    logging.debug('tokens %s', tokens)

    pf = postfix(tokens)

    logging.debug('postfix: %s', pf)

    nfa, all_states = post2nfa(pf)
    logging.debug('\nnfa starting with: %s', nfa)
    logging.debug('all_states %s', all_states)

    for start in range(len(s)):
        m = _match(nfa, s, start)
        if m:
            return m
    return None


def _match(nfa, s, start):
    "Apply an NFA to s beginning with the start position."
    logging.debug('\nmatch checking {!r}'.format(s))
    paths = next_paths(Path(nfa, None))
    i = start

    ever_matched = []

    while i < len(s):
        c = s[i]
        logging.debug('\nmatch i={} c={}'.format(i, c))
        paths = step(paths, c, i)
        if not paths:
            logging.debug('no more paths')
            break

        # Look for a match token in the upcoming states to tell if we
        # have found a match. Remember if we do, but don't exit now,
        # because we want to be greedy with matching the text.
        for path in paths:
            if MATCH == path.state.token.op:
                logging.debug('found match state at %s', i)
                ever_matched.append(path)

        i += 1

    if ever_matched:
        logging.debug('\nfound {} paths'.format(len(ever_matched)))
        for m in ever_matched:
            logging.debug('  %s %s %s', m.length(), m, m.matches())
        with_lengths = sorted(
            (m.length(), m)
            for m in ever_matched
        )
        return Match(s, with_lengths[-1][1])
    return None


def next_paths(path):
    "Compute the next paths from an existing paths' state."
    logging.debug(
        'next_paths %s %s',
        path.state,
        path.prev.as_chain() if path.prev else None,
    )
    out_paths = []
    # Skip states that aren't character matches, but traverse them to
    # find the next state in both directions.
    if path.state.token.op in SPLIT_OPS:
        out_paths.extend(next_paths(Path(path.state.out1, path)))
        out_paths.extend(next_paths(Path(path.state.out2, path)))
    else:
        out_paths.append(path)
    return out_paths


def step(paths, c, i):
    """Step through the NFA states based on the input character,
    returning the paths that can be used."""
    logging.debug(
        'step %s %c %d',
        [(p.state.n, p.state.token.text) for p in paths],
        c,
        i,
    )
    out_paths = []
    for path in paths:
        state = path.state
        if state.token.text == c:
            logging.debug('stepping %s %s', state.n, state.token.groups)
            path.c = c
            path.i = i
            out_paths.extend(next_paths(Path(state.out1, path)))
    return out_paths


class Path:
    "A remembered traversal of the NFA."

    def __init__(self, state, prev):
        self.state = state
        self.prev = prev
        self.c = None
        self.i = -1

    def matches(self):
        here = []
        if self.c is not None:
            here.append((
                self.state.n,
                self.state.token.op,
                self.c,
                self.state.token.groups,
            ))
        if self.prev is None:
            return here
        return self.prev.matches() + here

    def __repr__(self):
        return self.as_chain()

    def as_chain(self):
        here = '{}({!r})'.format(self.state.n, self.c)
        if self.prev is None:
            return here
        return '{}:{}'.format(self.prev.as_chain(), here)

    def length(self):
        here = 0
        if self.state.token.op == LITERAL:
            here = 1
        if self.prev is None:
            return here
        return self.prev.length() + here

    def reverse(self):
        if self.prev is not None:
            yield from self.prev.reverse()
        yield self


class Match:
    "Result of matching successfully."

    def __init__(self, s, path):
        self.s = s
        self.path = path
        self.text, self.extents = self._handle_groups(self.path)

    def __repr__(self):
        return repr(self.text)

    def _handle_groups(self, path):
        text = {}
        extents = {}
        for p in path.reverse():
            if p.c is None:
                # Skip the empty states
                continue
            logging.debug(
                '_handle_groups %s %s %s %s',
                p.state.n,
                p.state.token.op,
                p.c,
                p.state.token.groups,
            )
            for grp in p.state.token.groups:
                s = text.get(grp, '')
                s += p.c
                text[grp] = s

                # Use -1 to indicate a position we have not yet filled
                # in.
                new_start, new_end = extents.get(grp, (-1, -1))
                logging.debug('  extent {}: {}, {}'.format(
                    grp, new_start, new_end))
                # Only move the start position if we haven't started
                # this extent before.
                if new_start == -1:
                    new_start = p.i
                # Only move the end position if the extent has grown.
                if p.i > new_end:
                    new_end = p.i
                extents[grp] = (new_start, new_end)

        # The character position values in the paths are inclusive,
        # but the expected end values should be 1 character past the
        # actual match so we can use them in slices.
        real_extents = {
            k: (v[0], v[1]+1)
            for k, v in extents.items()
        }

        return (text, real_extents)


def _check(pattern, text, expected):
    matched = match(pattern, text)
    logging.debug('match returned {} expected {!r}'.format(
        matched, expected))

    if expected is None:
        assert matched is None
    else:
        assert matched.text[0] == expected

    return matched


if __name__ == '__main__':
    _check('a(a|(b|c))+', 'aabd', 'aab')
