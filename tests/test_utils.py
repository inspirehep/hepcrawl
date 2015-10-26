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
