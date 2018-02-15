# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import os
import re

import pkg_resources
import pytest
import responses
from scrapy.http import HtmlResponse

from hepcrawl.spiders import unesp_spider
from .responses import (
    fake_response_from_file,
    fake_response_from_string,
)


@pytest.fixture
def scrape_unesp_metadata():
    """Return the full metadata page."""
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'unesp',
            'test_record.html'
        )
    )


@pytest.fixture
def record(scrape_unesp_metadata):
    """Return results from the UNESP spider.

    Request to the full metadata is faked.
    """
    spider = unesp_spider.UNESPSpider()
    request = spider.parse(
        fake_response_from_file('unesp/test_list.html')
    ).next()

    response = HtmlResponse(
        url=request.url,
        request=request,
        body=scrape_unesp_metadata,
        **{'encoding': 'utf-8'}
    )
    return request.callback(response)


def test_title(record):
    """Test title."""
    title = (
        u'Efeitos da equa\xe7\xe3o de estado em hidrodin\xe2mica '
        'relativ\xedstica atrav\xe9s de alguns observ\xe1veis'
    )
    assert record['title'] == title


def test_abstract(record):
    """Test abstract."""
    assert record['abstract'] == (
        'We present results of a systematic study of the role of the equation '
        'of state in the hydrodynamic model. We simulate Au+Au collisions for '
        'two energies of the Relativistic Heavy Ion Collider (RHIC), 130 and '
        '200 GeV per nucleon, in order to compare our results to the collider '
        'data. By using the same initial conditions and freeze-out scenario, we '
        'analysed the eﬀects of diﬀerent equations of state on some physical '
        'observables trough the results of their respective hydrodynamical '
        'evolution. The observables of interest investigate here are particle '
        'spectra, elliptic ﬂow, used to study the impact of the equations of '
        'state on ﬁnal state anisotropies, and radii parameters estimated by '
        'the Hambury-Brown-Twiss eﬀect (HBT). Three diﬀerent types of equation '
        'of state are studied, each focusing on diﬀerent features of the '
        'system, such as the nature of the phase transition, strangeness and '
        'baryon densities. These diﬀerent equations of state imply diﬀerent '
        'hydrodynamic responses on the observables. Although the three '
        'equations of state used in the calculations describe the data '
        'reasonably well, some small diﬀerences are observed, showing weak '
        'sensitivity of the results on the particular choice of equation of '
        'state'
    )


def test_authors(record):
    """Test authors."""
    authors = [u'Dudek, Danuce Marcele']
    affiliation = u'Universidade Estadual Paulista (UNESP)'

    assert 'authors' in record
    assert len(record['authors']) == len(authors)

    # here we are making sure order is kept
    for index, name in enumerate(authors):
        assert record['authors'][index]['full_name'] == name
        assert affiliation in [
            aff['value'] for aff in record['authors'][index]['affiliations']
        ]


def test_date_published(record):
    """Test date published."""
    assert record['date_published'] == '2014-03-31'


def test_files(record):
    """Test pdf files."""
    url = 'http://repositorio.unesp.br/bitstream/handle/11449/123975/000829075.pdf'
    assert record['additional_files'][0]['url'] == url


def test_thesis(record):
    """Test thesis information."""
    institution = 'Universidade Estadual Paulista (UNESP)'

    assert record['thesis']['date'] == '2014-03-31'
    assert record['thesis']['institutions'][0]['name'] == institution


def test_thesis_supervisor(record):
    """Test thesis supervisor."""
    supervisor = u'Padula, Sandra dos Santos'
    assert record['thesis_supervisor'][0]['full_name'] == supervisor


def test_page_nr(record):
    """Test page numbers."""
    assert record['page_nr'] == ['122']


def test_non_thesis():
    """Test a HEPrecord for a Master's thesis (should be None as we don't
    want them)."""
    spider = unesp_spider.UNESPSpider()
    body = """
    <html>
        <body>
            <tr class="ds-table-row odd ">
                <td class="label-cell">dc.type.degree</td>
                <td>M.Sc.</td>
                <td>en_US</td>
            </tr>
        </body>
    </html>
    """
    response = fake_response_from_string(body)
    non_thesis_record = spider.build_item(response)

    assert non_thesis_record is None


def test_multiple_supervisors():
    """Test record with multiple supervisors."""
    spider = unesp_spider.UNESPSpider()
    body = """
    <html>
        <body>
            <tr class="ds-table-row odd ">
                <td class="label-cell">dc.contributor.advisor</td>
                <td>Seth Lloyd and J.D. Joannopoulos</td>
            </tr>
        <body>
    <html>
    """
    response = fake_response_from_string(body)
    record = spider.build_item(response)

    assert record
    assert record['thesis_supervisor'][0]['full_name'] == u'Lloyd, Seth'
    assert record['thesis_supervisor'][1]['full_name'] == u'Joannopoulos, J.D.'


def test_record_with_embargo():
    """Test record with a 24-month embargo."""
    spider = unesp_spider.UNESPSpider()
    body = """
    <html>
        <body>
            <tr class="ds-table-row even ">
                <td class="label-cell">dc.rights.accessRights</td>
                <td class="word-break">Acesso restrito</td>
            </tr>
            <tr class="ds-table-row odd ">
                <td class="label-cell">unesp.embargo</td>
                <td class="word-break">24 meses ap&oacute;s a data da defesa</td>
            </tr>
        <body>
    <html>
    """
    response = fake_response_from_string(body)
    record = spider.build_item(response)

    assert record is None


@responses.activate
def test_get_list_files():
    """Test getting the records list with fake post requests."""
    spider = unesp_spider.UNESPSpider()
    url = 'http://www.example.com/search'
    spider.start_urls = [url]
    responses.add(responses.POST, url, status=200, content_type='text/html')
    list_of_records = spider.get_list_file('2010')

    search_result = re.search(
        r'^(file:///tmp/UNESP_\w+\.html)', list_of_records)

    assert list_of_records
    assert search_result  # Should be something like u'file:///tmp/UNESP_CUgJKB.html'
