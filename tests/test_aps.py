# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import os

import pkg_resources
import pytest

from scrapy.http import TextResponse
from hepcrawl.spiders import aps_spider

from .responses import (
    fake_response_from_file,
)


@pytest.fixture
def aps_xml_record():
    """Returns the XML file where references can be scraped."""
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'aps',
            'aps_single_response_test_ref.xml'
        )
    )


@pytest.fixture
def record(aps_xml_record):
    """Return results from the APS spider.

    The scraping request is faked here with `aps_xml_record` and calling
    the request.callback.
    """
    spider = aps_spider.APSSpider()
    request = spider.parse(
        fake_response_from_file('aps/aps_single_response.json')
    ).next()
    response = TextResponse(
        url=request.url,
        request=request,
        body=aps_xml_record,
        encoding='utf-8',
    )
    parsed_record = request.callback(response).next()
    assert parsed_record

    return parsed_record


def test_abstract(record):
    """Test extracting abstract."""
    abstract = (
        'We use a popular fictional disease, zombies, in order to introduce '
        'techniques used in modern epidemiology modeling, and ideas and '
        'techniques used in the numerical study of critical phenomena. We '
        'consider variants of zombie models, from fully connected continuous '
        'time dynamics to a full scale exact stochastic dynamic simulation of a '
        'zombie outbreak on the continental United States. Along the way, we '
        'offer a closed form analytical expression for the fully connected '
        'differential equation, and demonstrate that the single person per site '
        'two dimensional square lattice version of zombies lies in the '
        'percolation universality class. We end with a quantitative study of '
        'the full scale US outbreak, including the average susceptibility of '
        'different geographical regions.'

    )

    assert 'abstract' in record
    assert record['abstract'] == abstract


def test_title(record):
    title = (
        'You can run, you can hide: The epidemiology and '
        'statistical mechanics of zombies'
    )

    assert 'title' in record
    assert record['title'] == title


def test_date_published(record):
    assert 'date_published' in record
    assert record['date_published'] == '2015-11-02'


def test_page_nr(record):
    assert 'page_nr' in record
    assert record['page_nr'][0] == '11'


def test_free_keywords(record):
    keywords = ['89.75.Hc', '87.23.Cc', '87.23.Ge', '87.10.Mn']

    assert 'free_keywords' in record
    for keyw in record['free_keywords']:
        assert keyw['value'] in keywords


def test_license(record):
    expected_license = [{
        'license': 'CC-BY-3.0',
        'url': 'http://creativecommons.org/licenses/by/3.0/',
    }]

    assert 'license' in record
    assert record['license'] == expected_license


def test_dois(record):
    assert 'dois' in record
    assert record['dois'][0]['value'] == '10.1103/PhysRevE.92.052801'


def test_collections(record):
    collections = ['HEP', 'Citeable', 'Published']

    assert 'collections' in record
    for coll in collections:
        assert {'primary': coll} in record['collections']


def test_collaborations(record):
    assert 'collaborations' in record
    assert record['collaborations'][0]['value'] == 'OSQAR Collaboration'


def test_field_categories(record):
    subjects = [{
        'scheme': 'APS',
        'source': 'aps',
        'term': 'Quantum Information',
    }]

    assert 'field_categories' in record
    assert record['field_categories'] == subjects


def test_publication_info(record):
    assert 'journal_title' in record
    assert record['journal_title'] == 'Phys. Rev. E'
    assert 'journal_year' in record
    assert record['journal_year'] == 2015
    assert 'journal_volume' in record
    assert record['journal_volume'] == '92'
    assert 'journal_issue' in record
    assert record['journal_issue'] == '5'


def test_authors(record):
    affiliation = (
        u'Laboratory of Atomic and Solid State Physics, Cornell '
        'University, Ithaca, New York 14853, USA'
    )
    author_full_names = [
        'Alemi, Alexander A.', 'Bierbaum, Matthew',
        'Myers, Christopher R.', 'Sethna, James P.'
    ]

    assert 'authors' in record
    assert len(record['authors']) == 4

    record_full_names = [author['full_name'] for author in record['authors']]
    # assert that we have the same list of authors
    assert set(author_full_names) == set(record_full_names)
    for author in record['authors']:
        assert author['affiliations'][0]['value'] == affiliation


def test_copyrights(record):
    """Test extracting copyright."""
    copyright_holder = 'authors'
    copyright_year = '2015'
    copyright_statement = 'Published by the American Physical Society'
    copyright_material = 'Article'

    assert 'copyright_holder' in record
    assert record['copyright_holder'] == copyright_holder
    assert 'copyright_year' in record
    assert record['copyright_year'] == copyright_year
    assert 'copyright_statement' in record
    assert record['copyright_statement'] == copyright_statement
    assert 'copyright_material' in record
    assert record['copyright_material'] == copyright_material


def test_references(record):
    reference1 = {
        'authors': [u'J. Fu', u'S. Wu', u'H. Li', u'L. R. Petzold'],
        'doctype': u'journal',
        'doi': u'doi:10.1016/j.jcp.2014.06.025',
        'fpage': u'524',
        'issn': u'0021-9991',
        'journal_title': u'J. Comput. Phys.',
        'journal_volume': u'274',
        'number': u'25',
        'raw_reference': u'<mixed-citation publication-type="journal"><object-id>25</object-id><person-group person-group-type="author"><string-name>J. Fu</string-name>, <string-name>S. Wu</string-name>, <string-name>H. Li</string-name>, and <string-name>L. R. Petzold</string-name></person-group>, <article-title>The time dependent propensity function for acceleration of spatial stochastic simulation of reaction-diffusion systems</article-title>, <source>J. Comput. Phys.</source><volume>274</volume>, <page-range>524</page-range> (<year>2014</year>).<pub-id pub-id-type="coden">JCTPAH</pub-id><issn>0021-9991</issn><pub-id pub-id-type="doi" specific-use="suppress-display">10.1016/j.jcp.2014.06.025</pub-id></mixed-citation>',
        'title': u'The time dependent propensity function for acceleration of spatial stochastic simulation of reaction-diffusion systems',
        'year': u'2014'
    }
    reference2 = {
        'authors': [u'A. V. Surname'],
        'collaboration': u'COLLAB Collaboration',
        'doctype': u'report',
        'number': u'1a',
        'publisher': u'New York: Freeman',
        'raw_reference': u'<mixed-citation id="c1a" publication-type="report"><object-id>1a</object-id><person-group person-group-type="author"><string-name>A. V. Surname</string-name>(<collab>COLLAB Collaboration</collab>)</person-group>, Report No. <pub-id pub-id-type="other"></pub-id>ICTP/2007/082. (<publisher-name>Freeman</publisher-name>, New York, <year>1973</year>)</mixed-citation>',
        'report_no': u'ICTP/2007/082',
        'year': u'1973'
    }
    reference3 = {
        'arxiv_id': u'arxiv:1604.05602',
        'doctype': u'book',
        'editors': [u'E. V. Surname'],
        'issue': u'67',
        'misc': u'CERN',
        'number': u'1b',
        'raw_reference': u'<mixed-citation id="c1b" publication-type="book" specific-use="translation"><object-id>1b</object-id><person-group person-group-type="editor"><string-name>E. V. Surname</string-name></person-group> <institution>CERN</institution>, <issue>67</issue> <pub-id pub-id-type="coden">SPHJAR</pub-id><pub-id pub-id-type="arxiv">1604.05602</pub-id>(<ext-link ext-link-type="uri" xlink:href="http://www.example.com">http://www.example.com</ext-link>)</mixed-citation>',
        'url': [u'http://www.example.com']
    }

    assert 'references' in record
    for ref in record['references']:
        assert 'doctype' in ref
        if ref['doctype'] == 'journal':
            assert ref == reference1
        elif ref['doctype'] == 'report':
            assert ref == reference2
        elif ref['doctype'] == 'book':
            assert ref == reference3


@pytest.fixture
def record_no_mixed_citation():
    """Return results with different reference XML structure.

    No <mixed-citation> or <object-id>.
    """
    spider = aps_spider.APSSpider()
    body = """
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD with OASIS Tables with MathML3 v1.1d1 20130915//EN" "JATS-journalpublishing-oasis-article1-mathml3.dtd">
    <article xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:oasis="http://www.niso.org/standards/z39-96/ns/oasis-exchange/table" article-type="research-article" xml:lang="en">
    <front/>
    <body/>
    <back>
        <ack/>
        <ref-list>
        <title>REFERENCES</title>
        <ref id="c1"><label>[1]</label><person-group person-group-type="author"><string-name>A. V. Surname</string-name>(<collab>COLLAB Collaboration</collab>)</person-group>, Report No. <pub-id pub-id-type="other"/>ICTP/2007/082. (<publisher-name>Freeman</publisher-name>, New York, <year>1973</year>)</ref>
        </ref-list>
    </back>
    </article>
    """
    request = spider.parse(
        fake_response_from_file('aps/aps_single_response.json')
    ).next()
    response = TextResponse(
        url=request.url,
        request=request,
        body=body,
        encoding='utf-8',
    )
    return request.callback(response).next()


def test_references_no_mixed_citation(record_no_mixed_citation):
    """Test references with different XML structure.

    No <mixed-citation> or <object-id>.
    """
    reference = {
        'authors': [u'A. V. Surname'],
        'collaboration': u'COLLAB Collaboration',
        'number': u'1',
        'publisher': u'New York: Freeman',
        'raw_reference': u'<ref id="c1"><label>[1]</label><person-group person-group-type="author"><string-name>A. V. Surname</string-name>(<collab>COLLAB Collaboration</collab>)</person-group>, Report No. <pub-id pub-id-type="other"></pub-id>ICTP/2007/082. (<publisher-name>Freeman</publisher-name>, New York, <year>1973</year>)</ref>',
        'report_no': u'ICTP/2007/082',
        'year': u'1973'

    }

    assert 'references' in record_no_mixed_citation
    assert record_no_mixed_citation['references'][0] == reference
    assert 'number' in record_no_mixed_citation['references'][0]
    assert record_no_mixed_citation['references'][0]['number'] == '1'


def test_parsing_next():
    """Test following "next" links in response header."""
    spider = aps_spider.APSSpider()
    response = fake_response_from_file('aps/aps_single_response.json')

    response.headers = {
        'X-Content-Type-Options': 'nosniff', 'Content-Encoding': 'gzip',
        'Transfer-Encoding': 'chunked', 'Vary': 'Accept-Encoding',
        'Server': 'nginx/1.7.9', 'Connection': 'close',
        'Link': '<http://www.example.com/nextpage>; rel="next"',
        'Date': 'Fri, 16 Sep 2016 13:38:41 GMT',
        'Content-Type': 'application/json'
    }

    parsed_response = spider.parse(response)
    request_to_scrape_xml = parsed_response.next()
    request_to_next_page = parsed_response.next()

    assert request_to_next_page
    assert request_to_next_page.url == 'http://www.example.com/nextpage'
