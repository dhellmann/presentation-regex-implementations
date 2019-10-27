#!/usr/bin/env python3

import argparse
import logging

import nfa


def edge(f, start, end):
    if end is None:
        return
    attrs = ''
    if start.token.op == nfa.LITERAL:
        attrs = '[ label = "%s" ]' % start.token.text
    f.write('  %s -> %s %s\n' % (start.n, end.n, attrs))


def node_to_graph(f, expression, all_states, active):
    f.write('digraph "%s" {\n' % expression)
    f.write('  rankdir=LR;\n')
    for state in all_states:
        shape = 'circle'
        if state.token.op == nfa.MATCH:
            shape = 'doublecircle'
        color = 'white'
        if state.n in active:
            color = 'yellow'
        f.write('  %s [ shape = %s, style = filled, fillcolor = %s ]\n' % (
            state.n, shape, color))
    f.write('\n')
    for state in all_states:
        edge(f, state, state.out1)
        edge(f, state, state.out2)
    f.write('}\n')


def to_graph(expression, outfile, active=[]):
    tokens = nfa.tokenize(expression)
    pf = nfa.postfix(tokens)
    start_state, all_states = nfa.post2nfa(pf)
    with open(outfile, 'w') as f:
        node_to_graph(f, expression, all_states, active)
