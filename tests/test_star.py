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

from hepcrawl.spiders import star_spider

from .responses import (
    fake_response_from_file,
    fake_response_from_string,
    get_node,
)


@pytest.fixture
def record(monkeypatch):
    """Return the results from the STAR spider."""
    spider = star_spider.STARSpider()

    def mock_get_links(spider):
        """Prevent the spider from doing GET requests.
        The spider method `get_links` does GET requests to detect
        the mime type of the links, so we have to mock it here.
        """
        return (
            ['http://www.theses.fr/2015PA112125'],
            ['http://www.theses.fr/2015PA112125/abes'],
        )

    monkeypatch.setattr(spider, 'get_links', mock_get_links)
    response = fake_response_from_file('star/test_1.xml')
    nodes = get_node(spider, '//OAI-PMH:record', response)

    return spider.parse_node(response, nodes[0])


@pytest.fixture
def alt_record():
    """Return results from a bit different record."""
    spider = star_spider.STARSpider()
    body = """
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
    <record>
    <metadata>
    <mets:mets xmlns:mets="http://www.loc.gov/METS/" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:tef="http://www.abes.fr/abes/documents/tef">
    <mets:dmdSec>
    <mets:mdWrap>
    <mets:xmlData>
        <tef:thesisRecord>
            <dc:title xml:lang="fr">Parallélisation de simulations interactives de champs ultrasonores pour le contrôle non destructif</dc:title>
            <dcterms:alternative xml:lang="en">Parallelization of ultrasonic field simulations for non destructive testing</dcterms:alternative>
            <dc:language xsi:type="dcterms:RFC3066">en</dc:language>
            <dc:subject xml:lang="fr">Programmation parallèle</dc:subject>
            <dcterms:abstract xml:lang="fr">La simulation est de plus en plus...</dcterms:abstract>
        </tef:thesisRecord>
    </mets:xmlData>
    </mets:mdWrap>
    </mets:dmdSec>
    </mets:mets>
    </metadata>
    </record>
    </OAI-PMH>
    """
    response = fake_response_from_string(body)
    nodes = get_node(spider, '//' + spider.itertag, response)

    return spider.parse_node(response, nodes[0])


@pytest.mark.xfail  # FIXME: wait for trans language item
def test_title(record):
    """Test title."""
    title_fr = (
        u'Parallélisation de simulations interactives de '
        'champs ultrasonores pour le contrôle non destructif'
    )
    title_en = (
        u'Parallelization of ultrasonic field simulations '
        'for non destructive testing'
    )

    assert 'title' in record
    assert 'translated_title' in record
    assert record['title'] == title_fr
    assert record['translated_title'] == title_en


def test_date_published(record):
    """Test date_published."""
    assert 'date_published' in record
    assert record['date_published'] == '2015-07-03'


def test_authors(record):
    """Test authors."""
    authors = [u'Lambert, Jason']
    surnames = [u'Lambert']
    affiliations = [
        u"Ecole doctorale Sciences et Technologies de l'Information, "
        "des T\xe9l\xe9communications et des Syst\xe8mes (Orsay, Essonne)"
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
        'http://www.theses.fr/2015PA112125/abes',
    ]

    assert 'additional_files' in record
    assert record['additional_files'][0]['url'] == file_urls[0]


def test_collections(record):
    """Test extracting collections."""
    collections = ['HEP', 'THESIS']

    assert 'collections' in record
    for collection in record['collections']:
        assert collection['primary'] in collections


def test_report_nr(record):
    assert 'report_numbers' in record
    assert record['report_numbers'][0]['value'] == u'2015PA112125'


@pytest.mark.xfail  # FIXME: what should the license be like?
def test_license(record):
    """Test extracting license information."""
    license = 'CC-BY-4.0'
    license_url = 'http://creativecommons.org/licenses/by/4.0/'
    assert 'license' in record
    assert record['license'][0]['license'] == license
    assert record['license'][0]['url'] == license_url


@pytest.mark.xfail  # FIXME: wait for trans language item
def test_primary_language_english(alt_record):
    title_fr = (
        u'Parallélisation de simulations interactives de '
        'champs ultrasonores pour le contrôle non destructif'
    )
    title_en = (
        u'Parallelization of ultrasonic field simulations '
        'for non destructive testing'
    )

    assert alt_record['title'] == title_en
    assert alt_record['translated_title'] == title_fr


def test_no_english_keywords(alt_record):
    keyword = 'Programmation parallèle'

    assert alt_record['free_keywords'][0]['value'] == keyword


def test_no_english_abstract(alt_record):
    abstract = 'La simulation est de plus en plus...'

    assert alt_record['abstract'] == abstract
