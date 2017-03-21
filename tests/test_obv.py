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

import hepcrawl
from hepcrawl.spiders import obv_spider

from .responses import (
    fake_callback_request,
    fake_response_from_file,
)


@pytest.fixture(scope='module')
def full_metadata():
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'obv',
            'test_full_metadata.html'
        )
    )


@pytest.fixture(scope='module')
def full_metadata_without_splash_page():
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'obv',
            'test_full_metadata_alternative.html'
        )
    )


@pytest.fixture(scope='module')
def splash_page():
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'obv',
            'test_splash.html'
        )
    )


@pytest.fixture(scope='module')
def request_to_full_metadata(full_metadata):
    """Return mocked Scrapy request to the full metadata page."""
    return fake_callback_request(
        spider=obv_spider.OBVSpider(),
        response_from_file='obv/test_list.html',
        callback_request_to_file=full_metadata
    )


@pytest.fixture(scope='module')
def record(request_to_full_metadata, splash_page):
    """Return resulting HEPRecord from ÖBV spider with mocked responses.

    Using scope='module' makes pytest invoke this chain of fixtures only once.
    It speeds up testing considerably.
    """
    # request_to_full_metadata.url is a redirect so can't be used here.
    # That works correctly in non-testing situations.
    splash_url = 'http://repositum.tuwien.ac.at/urn:nbn:at:at-ubtuw:1-2637'
    response_from_full_metadata = HtmlResponse(
        url=splash_url,
        request=request_to_full_metadata,
        body=splash_page,
        encoding='utf-8',
    )

    return request_to_full_metadata.callback(response_from_full_metadata)


@pytest.fixture(scope='module')
def record_alternative(full_metadata_without_splash_page):
    """Return mocked Scrapy request to the (bit different) full metadata.

    It is a HEPRecord.
    """
    return fake_callback_request(
        spider=obv_spider.OBVSpider(),
        response_from_file='obv/test_list.html',
        callback_request_to_file=full_metadata_without_splash_page,
    )


def test_title(record):
    title = (
        u'Measurement of the decay B -&gt; Dlnu in fully reconstructed events '
        'and determination of the Cabibbo-Kobayashi-Maskawa matrix element |Vcb|'
    )

    assert 'title' in record
    assert record['title'] == title


def test_abstract(record):
    assert record['abstract'] == (
        'The physics of subatomic particles is described by the so-called '
        'Standard Model of particle physics. It is formulated as a quantum '
        'gauge field theory and successfully describes electromagnetism, weak '
        'interaction and strong interaction. Within the Standard Model, the '
        'Cabibbo-Kobayashi-Maskawa (CKM) mechanism describes the transitions '
        'between quarks of different generations. This is expressed in the 3x3 '
        'CKM matrix V which rotates the mass eigenstates of quarks into their '
        'weak eigenstates. The unitarity of the matrix constrains it to 4 '
        'independent values: 3 angles and 1 complex phase. These are '
        'fundamental parameters of the Standard Model and thus need to be '
        'determined experimentally. The aim of this analysis is to measure the '
        'magnitude of Vcb, the entry in the CKM matrix responsible for the '
        'transition of bottom to charm quarks. The highest precision available '
        'for the determination of |Vcb| can be achieved by analyzing '
        'semileptonic B meson decays. The B mesons studied in this thesis were '
        'produced at the Belle experiment at the KEKB electron-positron '
        'collider in Tsukuba, Japan via the Y(4S) resonance. This offers a '
        'perfect environment for the study of semileptonic B decays due to the '
        'high luminosities and the dominant decay mode of Y(4S)-&gt;B anti-B, '
        'resulting in a data sample very rich in B mesons. Recent years have '
        'seen a lot of interest in semileptonic B decays due to discrepancies '
        'in the order of two to three standard deviations in |Vcb| between the '
        'best measured decay modes B-&gt;D*lnu and B-&gt;Xclnu. In this '
        'analysis B-&gt;Dlnu is analyzed for the first time using the full '
        'Belle data sample at the Y(4S) resonance containing about 770 million '
        'B anti-B pairs to give insight into this problem and to increase the '
        'precision of the value of |Vcb|. One of the key components of this '
        'thesis is the full reconstruction of events by also assembling the '
        'second B meson from the Y(4S)-&gt;B anti-B decay in a hadronic mode. '
        'This results in the knowledge of the kinematics of all involved final '
        'state particles with exception of the neutrino. 4-momentum '
        'conservation can then be used to infer the neutrino and distinguish '
        'signal from background via the mass missing in the decay. Full '
        'reconstruction greatly reduces combinatorial background and allows for '
        'high precision measurements of the B-&gt;Dlnu decay kinematics. |Vcb| '
        'is extracted using the differential decay width of B-&gt;Dlnu which '
        'can be decomposed into the leptonic current and a form factor '
        'describing the hadronic components. I determine the B-&gt;Dlnu decay '
        'width in 10 bins of the kinematic variable w=vB*vD, where vB and vD '
        'are the 4-velocities of the B and D mesons. In order to measure |Vcb| '
        'I use calculations of the form factor by Lattice QCD groups and two '
        'different parameterization schemes. Interpreting the decay width with '
        'the B-&gt;Dlnu form-factor parameterization by Caprini, Lellouch and '
        'Neubert and using the predicted form factor at zero hadronic recoil by '
        'FNAL/MILC, the value |Vcb|*eta=(40.12+-1.34)10^-3 is obtained, where '
        'eta accounts for non-factorizable electroweak corrections. A slightly '
        'higher precision is possible utilizing the model-independent form-'
        'factor description by Boyd, Grinstein and Lebed and using multiple '
        'form-factor data from FNAL/MILC and HPQCD, leading to the value '
        '|Vcb|*eta=(41.10+-1.14)10^-3. In relation to |Vcb| determined from '
        'B-&gt;Xclnu and B-&gt;D*lnu, these values fall into the middle, not '
        'clearly favoring either. I further determine the branching ratios of '
        'the decay B-&gt;Dlnu to be '
        'BR(B0-&gt;Dlnu)=(2.31+-0.03(stat)+-0.11(syst)).'
    )


def test_authors(record):
    authors = [u'Glattauer, Robin']
    affiliation = (
        u'Technische Universit\xe4t Wien, Fakult\xe4t f\xfcr '
        'Physik, Atominstitut, E141'
    )

    assert 'authors' in record
    assert len(record['authors']) == len(authors)

    # here we are making sure order is kept
    for index, name in enumerate(authors):
        assert record['authors'][index]['full_name'] == name
        assert affiliation in [
            aff['value'] for aff in record['authors'][index]['affiliations']
        ]


def test_date_published(record):
    assert record['date_published'] == '2016'


def test_files(record):
    pdf_link = (
        u'http://repositum.tuwien.ac.at/obvutwhs/download/pdf/1314397'
        '?originalFilename=true'
    )

    assert record['additional_files'][0]['url'] == pdf_link


def test_thesis_information(record):
    institution = (
        u'Technische Universit\xe4t Wien, Fakult\xe4t f\xfcr Physik, '
        'Atominstitut, E141'
    )

    assert record['thesis']['date'] == u'2016-05'
    assert record['thesis']['institutions'][0]['name'] == institution


def test_thesis_supervisor(record):
    assert 'thesis_supervisor' in record
    assert record['thesis_supervisor'][0][
        'full_name'] == u'Schwanda, Christoph'


def test_page_nr(record):
    assert 'page_nr' in record
    assert record['page_nr'][0] == '117'


def test_no_splash(record_alternative):
    """Test scraping the listing when no splash page exists.

    The spider should skip the second scrape request and go straight to building
    the HEPRecord.
    """
    assert isinstance(record_alternative, hepcrawl.items.HEPRecord)
    assert 'additional_files' not in record_alternative


def test_no_valid_page_nr(record_alternative):
    """Test record when page numbering isn't parsed."""
    assert 'page_nr' not in record_alternative


def test_no_english_abstract(record_alternative):
    """Test the record when no English abstract can be found."""
    abstract = (
        'Die Physik subatomarer Teilchen wird durch das sogenannte '
        'Standardmodell der Teilchenphysik beschrieben. In der mathematischen '
        'Formulierung einer Quanteneichfeldtheorie beschreibt es die Phänomene '
        'von Elektromagnetismus, der schwachen und der starken Wechselwirkung. '
        '...'
    )

    assert record_alternative['abstract'] == abstract


def test_parsing_next():
    """Test following "next" links in the listing page."""
    spider = obv_spider.OBVSpider()
    parsed_response = spider.parse(
        fake_response_from_file('obv/test_list.html')
    )

    request_to_full_metadata = parsed_response.next()
    request_to_next_page = parsed_response.next()
    expected_url = (
        'http://search.obvsg.at/primo_library/libweb/action/search.do'
        '?ct=Next+Page&pag=nxt&pageNumberComingFrom=1&&indx=1&(a%20long'
        '%20query%20here)'
    )

    assert request_to_next_page
    assert request_to_next_page.url == expected_url


@responses.activate
def test_get_list_file():
    """Test getting the html file which is the starting point of scraping."""
    spider = obv_spider.OBVSpider()
    url = 'http://www.example.com/query_result_page'
    body = '<html>Fake content</html>'
    responses.add(responses.GET, url, body=body, status=200,
                  content_type='text/html')
    file_path = spider.get_list_file(url)

    assert file_path
    assert re.search(r'file://.*.html', file_path)
