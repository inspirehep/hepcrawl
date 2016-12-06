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
import responses

import scrapy
from scrapy.http import HtmlResponse

from hepcrawl.spiders import dnb_spider
from hepcrawl.items import HEPRecord

from .responses import (
    fake_response_from_file,
    fake_response_from_string,
    get_node,
)


@pytest.fixture
def dnb_splash_page():
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'dnb',
            'test_splash.html'
        )
    )


@pytest.fixture
def record(dnb_splash_page, monkeypatch):
    """Return the results of the spider."""
    spider = dnb_spider.DNBSpider()

    def mock_direct_links(spider):
        """Prevent the spider from doing GET requests.

        The spider method `find_direct_links` does GET requests to detect
        the mime type of the links, so we have to mock it here.
        """
        return (
            ['http://d-nb.info/1079912991/34'],
            ['http://publikationen.ub.uni-frankfurt.de/frontdoor/'
             'index/index/docId/38625'],
        )

    monkeypatch.setattr(spider, 'find_direct_links', mock_direct_links)

    request = spider.parse(
        fake_response_from_file('dnb/test_1.xml')
    ).next()
    request.meta['urls'] = [
        'http://d-nb.info/1079912991/34',
        'http://publikationen.ub.uni-frankfurt.de/frontdoor/'
        'index/index/docId/38625'
    ]

    response = HtmlResponse(
        url=request.url,
        request=request,
        body=dnb_splash_page,
        encoding='utf-8',
    )

    return request.callback(response)


@pytest.fixture
@responses.activate
def record_without_splash():
    """Test parsing the XML without splash page links but with a direct link."""
    url = 'http://d-nb.info/1079843248/34'
    responses.add(responses.HEAD, url, status=200,
                  content_type='application/pdf')
    spider = dnb_spider.DNBSpider()
    body = """
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
    <ListRecords xsi:schemaLocation="http://www.loc.gov/MARC21/slim http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd">
        <record>
        <metadata>
            <slim:record xmlns:slim="http://www.loc.gov/MARC21/slim" type="Bibliographic">
                <slim:datafield tag="856" ind1=" " ind2="0">
                    <slim:subfield code="u">http://d-nb.info/1079843248/34</slim:subfield>
                </slim:datafield>
            </slim:record>
        </metadata>
        </record>
    </ListRecords>
    </OAI-PMH>
    """
    response = fake_response_from_string(body)
    nodes = get_node(spider, '//' + spider.itertag, response)
    return spider.parse_node(response, nodes[0])


@pytest.fixture
@responses.activate
def record_without_direct_link():
    """Test parsing the XML with splash page links but no direct link."""
    url = 'http://nbn-resolving.de/urn:nbn:de:hbz:294-44247'
    responses.add(responses.HEAD, url, status=200,
                  content_type='text/html')
    spider = dnb_spider.DNBSpider()
    body = """
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
    <ListRecords xsi:schemaLocation="http://www.loc.gov/MARC21/slim http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd">
        <record>
        <metadata>
            <slim:record xmlns:slim="http://www.loc.gov/MARC21/slim" type="Bibliographic">
                <slim:datafield tag="856" ind1=" " ind2="0">
                    <slim:subfield code="u">http://nbn-resolving.de/urn:nbn:de:hbz:294-44247</slim:subfield>
                </slim:datafield>
            </slim:record>
        </metadata>
        </record>
    </ListRecords>
    </OAI-PMH>
    """
    response = fake_response_from_string(body)
    nodes = get_node(spider, '//' + spider.itertag, response)
    return spider.parse_node(response, nodes[0])


def test_title(record):
    """Test title."""
    title = 'Auslegung und Messungen einer supraleitenden 325 MHz '\
            'CH-Struktur für Strahlbetrieb'
    assert 'title' in record
    assert record['title'] == title


def test_date_published(record):
    """Test date_published."""
    assert 'date_published' in record
    assert record['date_published'] == '2015'


def test_authors(record):
    """Test authors."""
    authors = ['Busch, Marco']
    surnames = ['Busch']
    affiliations = ['Frankfurt am Main, Johann Wolfgang Goethe-Univ.']

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


def test_supervisors(record):
    """Test thesis supervisors"""
    assert 'thesis_supervisor' in record
    assert record['thesis_supervisor'][0]['full_name'] == 'Podlech, Holger'


def test_source(record):
    """Test thesis source"""
    assert 'source' in record
    assert record['source'] == 'Univ.-Bibliothek Frankfurt am Main'


def test_language(record):
    """Test thesis language"""
    assert 'language' in record
    assert record['language'][0] == 'German'


def test_files(record):
    """Test files."""
    assert 'file_urls' in record
    assert record['file_urls'][0] == 'http://d-nb.info/1079912991/34'


def test_urls(record):
    """Test url in record."""
    urls = [
        'http://publikationen.ub.uni-frankfurt.de/frontdoor/'
        'index/index/docId/38625',
        'http://d-nb.info/1079912991/34',
    ]
    assert 'urls' in record
    assert len(record['urls']) == 2

    seen_urls = set()
    for url in record['urls']:
        assert url['value'] in urls
        assert url['value'] not in seen_urls
        seen_urls.add(url['value'])


def test_doctype(record):
    """Test doctype"""
    assert 'thesis' in record
    assert record['thesis']['degree_type'] == 'PhD'


def test_abstract(record):
    """Test that abstract has been fetched correctly."""
    abstract = (
        'Die vorliegende Arbeit handelt von der Entwicklung, dem Bau, den '
        'Zwischenmessungen sowie den abschließenden Tests unter kryogenen '
        'Bedingungen einer neuartigen, supraleitenden CH-Struktur für '
        'Strahlbetrieb mit hoher Strahllast. Diese Struktur setzt das Konzept '
        'des erfolgreich getesteten 19-zelligen 360 MHz CH-Prototypen fort, der '
        'einen weltweiten Spitzenwert in Bezug auf Beschleunigungsspannung im '
        'Niederenergiesegment erreichte, jedoch wurden einige Aspekte '
        'weiterentwickelt bzw. den neuen Rahmenbedingungen angepasst. Bei dem '
        'neuen Resonator wurde der Schwerpunkt auf ein kompaktes Design, '
        'effektives Tuning, leichte Präparationsmöglichkeiten und auf den '
        'Einsatz eines Leistungskopplers für Strahlbetrieb gelegt. Die '
        'Resonatorgeometrie besteht aus sieben Beschleunigungszellen, wird bei '
        '325 MHz betrieben und das Geschwindigkeitsprofil ist auf eine '
        'Teilcheneingangsenergie von 11.4 MeV/u ausgelegt. Veränderungen liegen '
        'in der um 90° gedrehten Stützengeometrie vor, um Platz für Tuner und '
        'Kopplerflansche zu gewährleisten, und in der Verwendung von schrägen '
        'Stützen am Resonatorein- und ausgang zur Verkürzung der Tanklänge und '
        'Erzielung eines flachen Feldverlaufs. Weiterhin wurden pro Tankdeckel '
        'zwei zusätzliche Spülflansche für die chemische Präparation sowie für '
        'die Hochdruckspüle mit hochreinem Wasser hinzugefügt. Das Tuning der '
        'Kavität erfolgt über einen neuartigen Ansatz, indem zwei bewegliche '
        'Balgtuner in das Resonatorvolumen eingebracht werden und extern über '
        'eine Tunerstange ausgelenkt werden können. Der Antrieb der Stange soll '
        'im späteren Betrieb wahlweise über einen Schrittmotor oder einen '
        'Piezoaktor stattfinden. Für ein langsames/ statisches Tuning kann der '
        'Schrittmotor den Tuner im Bereich +/- 1 mm auslenken, um größeren '
        'Frequenzabweichungen in der Größenordnung 100 kHz nach dem Abkühlen '
        'entgegenzuwirken. Das schnelle Tuning im niedrigen kHz-Bereich wird '
        'von einem Piezoaktor übernommen, welcher den Balg um einige µm bewegen '
        'kann, um Microphonics oder Lorentz-Force-Detuning zu kompensieren. Der '
        'Resonator wird von einem aus Titan bestehendem Heliummantel umgeben, '
        'wodurch ein geschlossener Heliumkreislauf gebildet wird. Derzeit '
        'befinden sich mehrere Projekte in der Planung bzw. im Bau, welche auf '
        'eine derartige Resonatorgeometrie zurückgreifen könnten. An der GSI '
        'basiert der Hauptteil des zukünftigen cw LINAC auf supraleitenden CH-'
        'Strukturen, um einen Strahl für die Synthese neuer, superschwerer '
        'Elemente zu liefern. Weiterhin könnte ein Upgrade des vorhandenen GSI '
        'UNILAC durch den Einsatz von supraleitenden CH-Resonatoren gestaltet '
        'werden. Zudem besteht die Möglichkeit, die bisherige Alvarez-Sektion '
        'des UNILAC alternativ durch eine kompakte, supraleitende CH-Sektion zu '
        'realisieren. Ebenfalls sollen die beiden parallelbetriebenen '
        'Injektorsektionen des MYRRHA-Projektes durch den Einsatz von '
        'supraleitenden CH-Strukturen erfolgen.'
    )

    assert 'abstract' in record
    assert record['abstract'] == abstract


def test_page_nr(record):
    """Test that page range is correct."""
    assert 'page_nr' in record
    assert record['page_nr'][0] == '133'


def test_record_without_splash(record_without_splash):
    file_url = 'http://d-nb.info/1079843248/34'

    assert 'abstract' not in record_without_splash
    assert 'page_nr' not in record_without_splash
    assert isinstance(record_without_splash, HEPRecord)
    assert record_without_splash['file_urls'][0] == file_url


def test_record_without_direct_link(record_without_direct_link):
    splash_url = 'http://nbn-resolving.de/urn:nbn:de:hbz:294-44247'

    assert isinstance(record_without_direct_link, scrapy.http.request.Request)
    assert record_without_direct_link.meta['urls'][0] == splash_url
