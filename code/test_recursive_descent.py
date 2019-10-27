#!/usr/bin/env python3

from recursive_descent import parse


def _check(expr, text, expected):
    regex = parse(expr)
    match = regex.match(text)
    if expected is None:
        assert match == expected
    else:
        assert match.text[0] == expected
    return match


def test_simple():
    _check('a', 'aab', 'a')
    _check('aa', 'aab', 'aa')
    _check('aab', 'aab', 'aab')
    _check('aac', 'aab', None)


def test_not_first_substring():
    match = _check('a', 'baab', 'a')
    assert match.extents == {
        0: (1, 2),
    }


def test_star():
    _check('a*b', 'b', 'b')
    _check('a*b', 'ab', 'ab')
    _check('a*b', 'aab', 'aab')
    _check('a*b', 'c', None)

def test_star_group_trailing():
    match = _check(
        r'a(bb)*a(c|d|e|fg)hij',
        'aafghij trailing',
        'aafghij',
    )
    assert match.text == {
        0: 'aafghij',
        2: 'fg',
    }
    assert match.extents == {
        0: (0, 7),
        2: (2, 4),
    }

    match2 = _check(
        r'a(bb)*a(c|d|e|fg)hij',
        'abbbbafghij trailing',
        'abbbbafghij',
    )
    assert match2.text == {
        0: 'abbbbafghij',
        1: 'bbbb',
        2: 'fg',
    }
    assert match2.extents == {
        0: (0, 11),
        1: (1, 5),
        2: (6, 8),
    }

def test_nested_group():
    match = _check(
        r'a(b(c|d))',
        'abd',
        'abd',
    )
    assert match.text == {
        0: 'abd',
        1: 'bd',
        2: 'd',
    }
    assert match.extents == {
        0: (0, 3),
        1: (1, 3),
        2: (2, 3),
    }
