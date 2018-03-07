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
import six

from hepcrawl.utils import (
    build_dict,
    coll_cleanforthe,
    collapse_initials,
    ftp_connection_info,
    get_first,
    get_journal_and_section,
    get_node,
    has_numbers,
    parse_domain,
    ParsedItem,
    range_as_string,
    split_fullname,
    unzip_xml_files,
    strict_kwargs,
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
def list_for_dict():
    """An example list to test the build_dict function."""
    return [
        {'id': 0, 'value': 'John', 'age': 20},
        {'id': 1, 'value': 'Mark', 'age': 27},
        {'id': 2, 'value': 'Bruce', 'age': 9}
    ]


class Dummy(object):
    """A sample class with @strict_kwargs constructor."""
    @strict_kwargs
    def __init__(self, good1_no_default, good2=10, good3=20, good4=30, *args, **kwargs):
        self.good1_no_default = good1_no_default
        self.good2 = good2
        self.good3 = good3
        self.good4 = good4
        self.args = args
        self.kwargs = kwargs


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


def test_strict_kwargs_pass():
    """Test the `strict_kwargs` decorator allowing the kwargs."""
    dummy = Dummy(
        good1_no_default=1,
        good2=2,
        good3=None,
        _private=4,
        settings={'DUMMY': True},
        crawler_settings={'DUMMY': True},
    )
    assert callable(dummy.__init__)
    assert dummy.good1_no_default == 1
    assert dummy.good2 == 2
    assert dummy.good3 == None
    assert dummy.good4 == 30
    assert dummy.kwargs == {'_private': 4, 'settings': {'DUMMY': True}, 'crawler_settings': {'DUMMY': True}}


def test_strict_kwargs_fail():
    """Test the `strict_kwargs` decorator disallowing some kwargs."""
    with pytest.raises(TypeError):
        Dummy(**{'good1_no_default': 1, 'good2': 2, u'bąd_þärãm': 4})


def test_parsed_item_from_exception():
    record_format = 'hep'
    source_data = 'some XML'
    file_name = 'broken.xml'

    try:
        raise KeyError('this is an error message')
    except KeyError as e:
        item = ParsedItem.from_exception(
            record_format=record_format,
            exception=e,
            traceback='error traceback',
            source_data=source_data,
            file_name=file_name
        )

        assert item['traceback'] == 'error traceback'
        assert type(item['exception']) is KeyError
        assert item['source_data'] == 'some XML'
        assert item['file_name'] == 'broken.xml'
