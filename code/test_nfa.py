#!/usr/bin/env python3

import pprint

from nfa import _check


def test_simple():
    _check(
        r'aba',
        'aba',
        'aba',
    )


def test_not_first_substring():
    match = _check('a', 'baab', 'a')
    assert match.extents == {
        0: (1, 2),
    }

def test_trailing():
    _check(
        r'ab',
        'aba',
        'ab',
    )

def test_star_simple():
    _check(
        r'ab*a',
        'aba',
        'aba',
    )
    _check(
        r'ab*a',
        'aa',
        'aa',
    )
    _check(
        r'ab*a',
        'abba',
        'abba',
    )
    _check(
        r'ab*a',
        'ada',
        None,
    )

def test_plus():
    _check('a+a', 'aaa', 'aaa')
    _check('a+a', 'aaaa', 'aaaa')
    _check('a+a', 'aa', 'aa')
    _check('a+a', 'a', None)

def test_nested_groups():
    match = _check('a((b)(c))', 'abc', 'abc')
    assert match.text == {
        0: 'abc',
        1: 'bc',
        2: 'b',
        3: 'c',
    }
    assert match.extents == {
        0: (0, 3),
        1: (1, 3),
        2: (1, 2),
        3: (2, 3),
    }
    _check('a((b)(c))', 'acb', None)

def test_alternatives():
    _check('a|b|c', 'a', 'a')
    _check('a|b|c', 'b', 'b')
    _check('a|b|c', 'c', 'c')
    _check('a|b|c', 'd', None)

def test_alternative_in_group():
    _check('a(a|b|c)', 'aa', 'aa')
    _check('a(a|b|c)', 'ab', 'ab')
    _check('a(a|b|c)', 'ac', 'ac')
    _check('a(a|b|c)', 'ad', None)
    _check('a(a|b|c)', 'a', None)

def test_only_prefix_matches_with_group():
    _check('a(a|b|c)', 'aab', 'aa')

def test_plus_group_trailing():
    _check(
        r'a(bb)+a(c|d|e|fg)hij',
        'abbbbafghij trailing',
        'abbbbafghij',
    )

def test_star_group_trailing():
    _check(
        r'a(bb)*a(c|d|e|fg)hij',
        'aafghij trailing',
        'aafghij',
    )
    _check(
        r'a(bb)*a(c|d|e|fg)hij',
        'abbbbafghij trailing',
        'abbbbafghij',
    )

def test_groups_common_prefix():
    _check('a((bc)|(bd))+', 'abc', 'abc')
    _check('a((bc)|(bd))+', 'abcbd', 'abcbd')
    _check('a((bc)|(bd))+', 'abd', 'abd')
    _check('a((bc)|(bd))+', 'abdbc', 'abdbc')
    _check('a((bc)|(bd))+', 'acd', None)

def test_complex_with_trailing():
    _check(
        r'ab?c+.(first(second|third)+)',
        r'abc.firstsecondthird trailing',
        r'abc.firstsecondthird',
    )
