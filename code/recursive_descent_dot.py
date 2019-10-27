#!/usr/bin/env python3

import argparse
import itertools
import logging

import recursive_descent

node_counter = itertools.count()


def edge(start, end, write):
    if end is None:
        return
    write('  %s -> %s\n' % (start, end))


show_node_id = False

def mk_node(node_name, label, active, write):
    if show_node_id:
        label = '{!r} {}'.format(label, node_name)
    color = 'white'
    if node_name in active:
        color = 'yellow'
    write('  {} [ label = "{}", shape = circle, style = filled, fillcolor = {} ]\n'.format(
        node_name, label, color))


def node_to_graph(node, active, write):
    node_name = 'n{}'.format(next(node_counter))

    if isinstance(node, recursive_descent.Choice):
        a_name = node_to_graph(node.a, active, write)
        b_name = node_to_graph(node.b, active, write)
        mk_node(node_name, '|', active, write)
        edge(node_name, a_name, write)
        edge(node_name, b_name, write)

    elif isinstance(node, recursive_descent.Concatenate):
        name1 = node_to_graph(node.first, active, write)
        name2 = node_to_graph(node.second, active, write)
        mk_node(node_name, '\N{CIRCLED PLUS}', active, write)
        edge(node_name, name1, write)
        edge(node_name, name2, write)

    elif isinstance(node, recursive_descent.Blank):
        mk_node(node_name, '', active, write)

    elif isinstance(node, recursive_descent.Repetition):
        internal_name = node_to_graph(node.internal, active, write)
        mk_node(node_name, '*', active, write)
        edge(node_name, internal_name, write)

    elif isinstance(node, recursive_descent.Primitive):
        mk_node(node_name, node.c, active, write)

    else:
        raise ValueError('Unknown node type {}'.format(node))

    return node_name


def to_graph(expression, outfile, active=[]):
    expr = recursive_descent.parse(expression)
    with open(outfile, 'w') as f:
        print('writing to {}'.format(outfile))
        f.write('digraph "%s" {\n' % expression)
        node_to_graph(expr, active, f.write)
        f.write('}\n')
