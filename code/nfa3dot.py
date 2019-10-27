#!/usr/bin/env python3

import argparse
import logging

import nfa3


def edge(start, end):
    if end is None:
        return
    attrs = ''
    if start.token.op == nfa3.LITERAL:
        attrs = '[ label = "%s" ]' % start.token.text
    print('  %s -> %s %s' % (start.n, end.n, attrs))


def to_graph(expression, all_states, active):
    print('digraph "%s" {' % expression)
    print('  rankdir=LR;')
    print('  label="%s";' % expression)
    print()
    for state in all_states:
        shape = 'circle'
        if state.token.op == nfa3.MATCH:
            shape = 'doublecircle'
        color = 'white'
        if state.n in active:
            color = 'yellow'
        print('  %s [ shape = %s, style = filled, fillcolor = %s ]' % (
            state.n, shape, color))
    print()
    for state in all_states:
        edge(state, state.out1)
        edge(state, state.out2)
    print('}')


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('expression')
    argparser.add_argument('-a', '--active', dest='active',
                           default=[], action='append')
    argparser.add_argument('-v', dest='verbose',
                           default=False, action='store_true')
    args = argparser.parse_args()

    if args.verbose:
        logging.basicConfig(
            format='%(message)s',
            level=logging.DEBUG,
        )

    tokens = nfa3.tokenize(args.expression)
    pf = nfa3.postfix(tokens)
    start_state, all_states = nfa3.post2nfa(pf)
    to_graph(args.expression, all_states, args.active)


if __name__ == '__main__':
    main()
