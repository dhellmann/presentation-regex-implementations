#!/usr/bin/env python3

from pike import match


def test_simple():
    assert match('a', 'aab')
    assert match('aa', 'aab')
    assert match('aab', 'aab')
    assert not match('aac', 'aab')


def test_star():
    assert match('a*b', 'b')
    assert match('a*b', 'ab')
    assert match('a*b', 'aab')
    assert not match('a*b', 'c')


def test_anchor():
    assert match('^a*b$', 'b')
    assert match('^a*b$', 'ab')
    assert match('^a*b$', 'aab')
    assert not match('^a*b$', 'caab')
    assert not match('^a*b$', 'aabc')
