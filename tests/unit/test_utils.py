# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function, unicode_literals

import os

import pytest
import responses
import six

from hepcrawl.utils import (
    build_dict,
    coll_cleanforthe,
    collapse_initials,
    ftp_connection_info,
    get_first,
    get_journal_and_section,
    get_mime_type,
    get_nested,
    get_node,
    has_numbers,
    parse_domain,
    range_as_string,
    split_fullname,
    unzip_xml_files,
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
    assert url == 'ftp.example.com'
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


def test_split_fullname():
    """Test author fullname splitting."""
    author1 = 'Doe, John Magic'
    author2 = 'Doe Boe, John Magic'
    author3 = 'Doe Boe John Magic'
    author4 = 'John Magic Doe'
    author5 = 'John Magic Doe Boe'
    author6 = 'John Magic, Doe Boe'
    author7 = ''
    assert split_fullname(author1) == ('Doe', 'John Magic')
    assert split_fullname(author2) == ('Doe Boe', 'John Magic')
    assert split_fullname(author3, switch_name_order=True) == ('Doe', 'Boe John Magic')
    assert split_fullname(author4) == ('Doe', 'John Magic')
    assert split_fullname(author5) == ('Boe', 'John Magic Doe')
    assert split_fullname(author6, switch_name_order=True) == ('Doe Boe', 'John Magic')
    assert split_fullname(author7) == ('', '')


def test_parse_domain():
    """Test domain parsing."""
    url = 'http://www.example.com/0351/content'
    domain = 'http://www.example.com/'
    assert parse_domain(url) == domain


@responses.activate
def test_get_mime_type():
    """Test MIME type getting when Content-Type is given."""
    url = 'http://www.example.com/files/einstein_1905.pdf'
    responses.add(responses.HEAD, url, status=200, content_type='application/pdf')
    assert get_mime_type(url) == 'application/pdf'
    assert get_mime_type(None) == ''
    assert get_mime_type('') == ''


@responses.activate
def test_get_mime_type_no_content():
    """Test MIME type getting when no Content-Type given."""
    url = 'http://www.example.com/files/einstein_1905.pdf'
    responses.add(responses.HEAD, url, status=200, content_type=None)
    with pytest.raises(Exception):
        assert get_mime_type(url)


def test_has_numbers():
    """Test number detection"""
    text1 = "154 numbers"
    text2 = "no numbers"
    assert has_numbers(text1) is True
    assert has_numbers(text2) is False


def test_range_as_string():
    """Test range detection in a list of (string) integers."""
    years1 = ["1981", "1982", "1983"]
    years2 = ["1981", "1982", "1985"]
    years3 = ["1981", "1989", "1995"]
    years4 = ["1981", "1982", "1989", "2015", "2016"]
    years5 = [500, 501, 600]
    assert range_as_string(years1) == "1981-1983"
    assert range_as_string(years2) == "1981-1982, 1985"
    assert range_as_string(years3) == "1981, 1989, 1995"
    assert range_as_string(years4) == "1981-1982, 1989, 2015-2016"
    assert range_as_string(years5) == "500-501, 600"


def test_collapse_initials():
    """Test removal of space from initials."""
    author = "F. M. Lastname"
    excpected = "F.M. Lastname"
    result = collapse_initials(author)

    assert result == excpected


def test_get_node():
    """Test getting node from XML string with namespaces."""
    body = """
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
    <ListRecords xsi:schemaLocation="http://www.loc.gov/MARC21/slim http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd">
    <record>
        <metadata>
            <slim:record xmlns:slim="http://www.loc.gov/MARC21/slim" type="Bibliographic">
                <slim:datafield>This is the record.</slim:datafield>
            </slim:record>
        </metadata>
    </record>
    </ListRecords>
    """
    namespaces = [
        ("OAI-PMH", "http://www.openarchives.org/OAI/2.0/"),
        ("slim", "http://www.loc.gov/MARC21/slim"),
    ]
    node = get_node(text=body, namespaces=namespaces)
    record = node.xpath("//slim:record/slim:datafield/text()").extract_first()

    assert node
    assert record == "This is the record."


def test_coll_cleanforthe():
    """Test author and collaboration getting."""
    forenames = "Jieci"
    keyname = "Wang for the Planck Collaboration"

    name_string = " %s %s " % (forenames, keyname)
    collaboration, author = coll_cleanforthe(name_string)

    assert collaboration == "Planck"
    assert author == "Jieci Wang"


def test_coll_cleanforthe_not_collaboration():
    """Test author and collaboration getting when there is something that looks
    like a collaboration, but it really isn't."""
    forenames = "Jieci"
    keyname = "Wang for the development of some thing"

    name_string = " %s %s " % (forenames, keyname)
    collaboration, author = coll_cleanforthe(name_string)

    assert collaboration == name_string
    assert author is None


def test_get_journal_and_section():
    """Test formatting journal name and extracting section."""
    publication = "Physics Letters B"
    journal_title, section = get_journal_and_section(publication)

    assert journal_title == "Physics Letters"
    assert section == "B"


def test_get_journal_and_section_invalid():
    """Test formatting journal name and extracting section when input is not valid."""
    publication = ""
    journal_title, section = get_journal_and_section(publication)

    assert journal_title == ''
    assert section == ''
