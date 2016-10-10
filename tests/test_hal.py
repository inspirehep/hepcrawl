# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import pytest

from hepcrawl.spiders import hal_spider

from .responses import (
    fake_response_from_file,
    fake_response_from_string,
    get_node,
)


@pytest.fixture
def record():
    """Return the results from the Hindawi spider."""
    spider = hal_spider.HALSpider()
    response = fake_response_from_file('hal/test_physics_thesis.xml')
    nodes = get_node(spider, '//OAI-PMH:record', response)

    return spider.parse_node(response, nodes[0])


@pytest.mark.xfail
def test_title(record):
    """Test title."""
    title_fr = (
        u'Ordres non conventionnels et entrelac\xe9s du mod\xe8le de '
        'Hubbard \xe0 basse dimensionnalit\xe9'
    )
    title_en = (
        u'Unconventional and intertwined orders of the '
        'low-dimensional Hubbard model'
    )

    assert 'title' in record
    assert 'translated_title' in record
    assert record['title'] == title_fr
    assert record['translated_title'] == title_en


def test_date_published(record):
    """Test date_published."""
    assert 'date_published' in record
    assert record['date_published'] == '2015-12'


def test_authors(record):
    """Test authors."""
    authors = [u'Lepr\xe9vost, A.']
    surnames = [u'Lepr\xe9vost']
    affiliations = [
        u'Laboratoire de cristallographie et sciences des mat\xe9riaux',
        u'Laboratoire de Physique Corpusculaire de Caen'
    ]

    assert 'authors' in record
    astr = record['authors']
    assert len(astr) == len(authors)

    # here we are making sure order is kept
    for index in range(len(authors)):
        assert astr[index]['full_name'] == authors[index]
        assert astr[index]['surname'] == surnames[index]
        assert affiliations[index] in [
            aff['value'] for aff in astr[index]['affiliations']
        ]


def test_files(record):
    """Test files."""
    file_urls = [
        'http://hal.in2p3.fr/tel-01238742/document',
        'http://hal.in2p3.fr/tel-01238742/file/Leprevost_Th%C3%A8se_rd_HAL.pdf'
    ]

    assert 'additional_files' in record
    assert record['additional_files'][0]['url'] == file_urls[0]
    assert record['additional_files'][0]['embargo_until'] == '2015-12-07'
    assert record['additional_files'][1]['url'] == file_urls[1]
    assert record['additional_files'][1]['embargo_until'] == '2015-12-07'


def test_collections(record):
    """Test extracting collections."""
    collections = ['HEP', 'THESIS']

    assert 'collections' in record
    for collection in record['collections']:
        assert collection['primary'] in collections


def test_license(record):
    """Test extracting license information."""
    license = 'CC-BY-4.0'
    license_url = 'http://creativecommons.org/licenses/by/4.0/'
    assert 'license' in record
    assert record['license'][0]['license'] == license
    assert record['license'][0]['url'] == license_url



def test_record_wrong_topic():
    """Test record skipping when it's not a physics thesis."""
    spider = hal_spider.HALSpider()
    body = """
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
    <record>
        <header>
            <setSpec>type:THESE</setSpec>
            <setSpec>subject:shs</setSpec>
            <setSpec>collection:STAR</setSpec>
        </header>
    </record>
    </OAI-PMH>
    """
    response = fake_response_from_string(body)
    nodes = get_node(spider, '//' + spider.itertag, response)
    record = spider.parse_node(response, nodes[0])

    assert record is None


@pytest.mark.xfail
def test_language_english():
    """Test record when English is the primary language."""
    spider = hal_spider.HALSpider()
    body = """
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
    <record>
    <header>
        <setSpec>type:THESE</setSpec>
        <setSpec>subject:phys</setSpec>
    </header>
    <metadata xmlns:tei="http://www.tei-c.org/ns/1.0">
        <tei:TEI xmlns:hal="http://hal.archives-ouvertes.fr/">
        <tei:text>
        <tei:body>
        <tei:listBibl>
        <tei:biblFull>
        <tei:titleStmt>
            <tei:title xml:lang="en">Unconventional and intertwined orders of the low-dimensional Hubbard model</tei:title>
            <tei:title xml:lang="fr">Ordres non conventionnels et entrelacés du modèle de Hubbard à basse dimensionnalité</tei:title>
        </tei:titleStmt>
        <tei:langUsage>
            <tei:language ident="fr">English</tei:language>
        </tei:langUsage>
        </tei:biblFull>
        </tei:listBibl>
        </tei:body>
        </tei:text>
        </tei:TEI>
    </metadata>
    </record>
    </OAI-PMH>
    """
    response = fake_response_from_string(body)
    nodes = get_node(spider, '//' + spider.itertag, response)
    record = spider.parse_node(response, nodes[0])

    title_fr = (
        u'Ordres non conventionnels et entrelac\xe9s du mod\xe8le de '
        'Hubbard \xe0 basse dimensionnalit\xe9'
    )
    title_en = (
        u'Unconventional and intertwined orders of the '
        'low-dimensional Hubbard model'
    )

    assert record['title'] == title_en
    assert record['translated_title'] == title_fr
