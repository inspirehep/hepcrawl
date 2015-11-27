# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import os

import pytest
import six

from hepcrawl.utils import (
    unzip_xml_files,
    ftp_connection_info,
    get_first,
    get_nested,
    build_dict
)


@pytest.fixture
def zipfile():
    """Return path to test zip file."""
    return os.path.join(
        os.path.dirname(__file__),
        'data',
        'test.zip'
    )


@pytest.fixture
def netrcfile():
    """Return path to test zip file."""
    return os.path.join(
        os.path.dirname(__file__),
        'data',
        'netrc'
    )


@pytest.fixture
def nested_json():
    """An example JSON to test the get_nested function."""
    return {
        'a': {
            'b': 'example_b',
            'b1': {
                'c': 'example_c'
            }
        },
        'a1': 'example_a1'
    }


@pytest.fixture
def list_for_dict():
    """An example list to test the build_dict function."""
    return [
        {'id': 0, 'value': 'John', 'age': 20},
        {'id': 1, 'value': 'Mark', 'age': 27},
        {'id': 2, 'value': 'Bruce', 'age': 9}
    ]


def test_unzip_xml(zipfile, tmpdir):
    """Test unzipping of xml files using zipfile and tmpdir fixtures."""
    assert len(unzip_xml_files(zipfile, six.text_type(tmpdir))) == 1


def test_get_first(zipfile, tmpdir):
    """Test unzipping of xml files using zipfile and tmpdir fixtures."""
    assert get_first([]) is None
    assert get_first([1]) == 1
    assert get_first([], 2) == 2


def test_ftp_connection_info(netrcfile):
    """Test unzipping of xml files using zipfile and tmpdir fixtures."""
    url, info = ftp_connection_info('ftp.example.com', netrcfile)
    assert url == 'ftp://ftp.example.com'
    assert 'ftp_user' in info
    assert info['ftp_user'] == 'test'
    assert 'ftp_password' in info
    assert info['ftp_password'] == 'test'


def test_get_nested(nested_json):
    """Test the results of recursively parsing a nested dict."""
    assert get_nested(nested_json, 'a1') == 'example_a1'
    assert get_nested(nested_json, 'a', 'b') == 'example_b'
    assert get_nested(nested_json, 'a', 'b1', 'c') == 'example_c'
    assert get_nested(nested_json, 'a', 'b2') == ''


def test_build_dict(list_for_dict):
    """Test the list to dict function, based on a specific key."""
    dict_from_list = build_dict(list_for_dict, 'id')
    assert dict_from_list[0]['value'] == 'John'
    assert dict_from_list[1]['value'] == 'Mark'
    assert dict_from_list[2]['value'] == 'Bruce'

    dict_from_list = build_dict(list_for_dict, 'value')
    assert dict_from_list['John']['age'] == 20
    assert dict_from_list['Mark']['age'] == 27
    assert dict_from_list['Bruce']['age'] == 9
