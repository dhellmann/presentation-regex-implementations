#!/usr/bin/env python3

import argparse
import itertools
import logging

import recursive_descent

node_counter = itertools.count()


def edge(start, end):
    if end is None:
        return
    print('  %s -> %s' % (start, end))


show_node_id = False

def mk_node(node_name, label, active):
    if show_node_id:
        label = '{!r} {}'.format(label, node_name)
    color = 'white'
    if node_name in active:
        color = 'yellow'
    print('  {} [ label = "{}", shape = circle, style = filled, fillcolor = {} ]'.format(
        node_name, label, color))


def to_graph(node, active):
    node_name = 'n{}'.format(next(node_counter))

    if isinstance(node, recursive_descent.Choice):
        a_name = to_graph(node.a, active)
        b_name = to_graph(node.b, active)
        mk_node(node_name, '|', active)
        edge(node_name, a_name)
        edge(node_name, b_name)

    elif isinstance(node, recursive_descent.Sequence):
        name1 = to_graph(node.first, active)
        name2 = to_graph(node.second, active)
        mk_node(node_name, '\N{CIRCLED PLUS}', active)
        edge(node_name, name1)
        edge(node_name, name2)

    elif isinstance(node, recursive_descent.Blank):
        mk_node(node_name, '', active)

    elif isinstance(node, recursive_descent.Repetition):
        internal_name = to_graph(node.internal, active)
        mk_node(node_name, '*', active)
        edge(node_name, internal_name)

    elif isinstance(node, recursive_descent.Primitive):
        mk_node(node_name, node.c, active)

    else:
        raise ValueError('Unknown node type {}'.format(node))

    return node_name


def main():
    global show_node_id

    argparser = argparse.ArgumentParser()
    argparser.add_argument('expression')
    argparser.add_argument('-a', '--active', dest='active',
                           default=[], action='append')
    argparser.add_argument('-i', '--ids', dest='ids',
                           default=False, action='store_true')
    argparser.add_argument('-v', dest='verbose',
                           default=False, action='store_true')
    args = argparser.parse_args()

    if args.verbose:
        logging.basicConfig(
            format='%(message)s',
            level=logging.DEBUG,
        )

    show_node_id = args.ids

    expr = recursive_descent.parse(args.expression)
    print('digraph "%s" {' % args.expression)
    print('  label="%s";' % args.expression)
    print()
    to_graph(expr, args.active)
    print('}')


if __name__ == '__main__':
    main()
