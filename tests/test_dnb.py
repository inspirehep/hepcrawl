# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import pytest
import responses
import requests

from scrapy.selector import Selector

from hepcrawl.spiders import dnb_spider

from .responses import fake_response_from_file

@pytest.fixture
def record():
    """Return results generator from the DNB spider."""
    spider = dnb_spider.DNBSpider()
    response = fake_response_from_file("dnb/test_1.xml")
    selector = Selector(response, type="xml")
    spider._register_namespaces(selector)
    nodes = selector.xpath("//%s" % spider.itertag)
    response.meta["node"] = nodes[0]
    response.meta["direct_links"] = ["http://d-nb.info/1079912991/34"]
    response.meta["urls"] = [
        "http://nbn-resolving.de/urn:nbn:de:hebis:30:3-386257", 
        "http://d-nb.info/1079912991/34", 
        "http://publikationen.ub.uni-frankfurt.de/frontdoor/index/index/docId/38625"
    ]
    return spider.build_item(response)

@pytest.fixture
def authors():
    spider = dnb_spider.DNBSpider()
    response = fake_response_from_file("dnb/test_1.xml")
    selector = Selector(response, type="xml")
    spider._register_namespaces(selector)
    nodes = selector.xpath("//%s" % spider.itertag)
    return spider.get_authors(nodes[0])

@pytest.fixture
def urls():
    spider = dnb_spider.DNBSpider()
    response = fake_response_from_file("dnb/test_1.xml")
    selector = Selector(response, type="xml")
    spider._register_namespaces(selector)
    nodes = selector.xpath("//%s" % spider.itertag)
    return spider.get_urls_in_record(nodes[0])

@pytest.fixture
def direct_links():
    spider = dnb_spider.DNBSpider()
    urls = [
        "http://nbn-resolving.de/urn:nbn:de:hebis:30:3-386257", 
        "http://d-nb.info/1079912991/34", 
        "http://publikationen.ub.uni-frankfurt.de/frontdoor/index/index/docId/38625"
    ]
    return spider.find_direct_links(urls)

@pytest.fixture
def affiliations():
    spider = dnb_spider.DNBSpider()
    response = fake_response_from_file("dnb/test_1.xml")
    selector = Selector(response, type="xml")
    spider._register_namespaces(selector)
    nodes = selector.xpath("//%s" % spider.itertag)
    return spider.get_affiliations(nodes[0])

@pytest.fixture
def parse_node_requests():
    """Returns a fake request to the record file."""
    spider = dnb_spider.DNBSpider()

    orig_response = fake_response_from_file("dnb/test_1.xml")
    selector = Selector(orig_response, type="xml")
    spider._register_namespaces(selector)
    nodes = selector.xpath("//%s" % spider.itertag)

    return spider.parse_node(orig_response, nodes[0])

@pytest.fixture
def splash():
    """Returns a call to build_item(), and ultimately the HEPrecord"""
    spider = dnb_spider.DNBSpider()

    orig_response = fake_response_from_file("dnb/test_1.xml")
    selector = Selector(orig_response, type="xml")
    spider._register_namespaces(selector)
    nodes = selector.xpath("//%s" % spider.itertag)

    response = fake_response_from_file("dnb/test_splash.html", url="http://publikationen.ub.uni-frankfurt.de/frontdoor/index/index/docId/38625")
    response.meta["urls"] = ["http://nbn-resolving.de/urn:nbn:de:hebis:30:3-386257", 
                            "http://d-nb.info/1079912991/34", 
                            "http://publikationen.ub.uni-frankfurt.de/frontdoor/index/index/docId/38625"]
    response.meta["node"] = nodes[0]

    return spider.scrape_for_abstract(response)

def test_title(record):
    """Test title."""
    title = "Auslegung und Messungen einer supraleitenden 325 MHz CH-Struktur für Strahlbetrieb"
    assert record["title"]
    assert record["title"] == title


def test_date_published(record):
    """Test date_published."""
    date_published = "2015"
    assert record["date_published"]
    assert record["date_published"] == date_published


def test_authors(record):
    """Test authors."""
    authors = ["Busch, Marco"]
    assert record["authors"]
    assert len(record["authors"]) == len(authors)

    # here we are making sure order is kept
    for index, name in enumerate(authors):
        assert record["authors"][index]["full_name"] == name

def test_supervisors(record):
    """Test thesis supervisors"""
    supervisors = ["Podlech, Holger"]
    assert record["thesis_supervisor"]
    assert record["thesis_supervisor"] == supervisors

def test_source(record):
    """Test thesis source"""
    source = [u'Univ.-Bibliothek Frankfurt am Main']
    assert record["source"]
    assert record["source"] == source

def test_language(record):
    """Test thesis language"""
    language = [u'ger']
    assert record["language"]
    assert record["language"] == language

def test_files(record):
    """Test files."""
    files = ["http://d-nb.info/1079912991/34"]
    assert "files" in record
    assert record["files"] == files

def test_urls(record):
    """Test url in record."""
    urls = [
        "http://nbn-resolving.de/urn:nbn:de:hebis:30:3-386257", 
        "http://d-nb.info/1079912991/34", 
        "http://publikationen.ub.uni-frankfurt.de/frontdoor/index/index/docId/38625"
    ]
    assert "urls" in record
    assert record["urls"] == urls

def test_doctype(record):
    """Test doctype"""
    doctype = "PhD"
    assert record["thesis"]
    assert record["thesis"][0]["degree_type"] == doctype

def test_parse_node(parse_node_requests):
    """Test request metadata that has been defined in parse_node()."""
    urls = [u'http://nbn-resolving.de/urn:nbn:de:hebis:30:3-386257', 
            u'http://d-nb.info/1079912991/34', 
            u'http://publikationen.ub.uni-frankfurt.de/frontdoor/index/index/docId/38625']
    assert parse_node_requests.meta["urls"]
    assert parse_node_requests.meta["direct_links"]
    assert parse_node_requests.meta["urls"] == urls
    assert parse_node_requests.meta["direct_links"] == [u'http://d-nb.info/1079912991/34']

def test_scrape(splash):
    """Test data that has been fetched in scrape_for_abstract()."""
    abstract_gt = ( 
            "Die vorliegende Arbeit handelt von der Entwicklung, dem Bau, den "
            "Zwischenmessungen sowie den abschließenden Tests unter kryogenen "
            "Bedingungen einer neuartigen, supraleitenden CH-Struktur für "
            "Strahlbetrieb mit hoher Strahllast. Diese Struktur setzt das Konzept "
            "des erfolgreich getesteten 19-zelligen 360 MHz CH-Prototypen fort, der "
            "einen weltweiten Spitzenwert in Bezug auf Beschleunigungsspannung im "
            "Niederenergiesegment erreichte, jedoch wurden einige Aspekte "
            "weiterentwickelt bzw. den neuen Rahmenbedingungen angepasst. Bei dem "
            "neuen Resonator wurde der Schwerpunkt auf ein kompaktes Design, "
            "effektives Tuning, leichte Präparationsmöglichkeiten und auf den "
            "Einsatz eines Leistungskopplers für Strahlbetrieb gelegt. Die "
            "Resonatorgeometrie besteht aus sieben Beschleunigungszellen, wird bei "
            "325 MHz betrieben und das Geschwindigkeitsprofil ist auf eine "
            "Teilcheneingangsenergie von 11.4 MeV/u ausgelegt. Veränderungen liegen "
            "in der um 90° gedrehten Stützengeometrie vor, um Platz für Tuner und "
            "Kopplerflansche zu gewährleisten, und in der Verwendung von schrägen "
            "Stützen am Resonatorein- und ausgang zur Verkürzung der Tanklänge und "
            "Erzielung eines flachen Feldverlaufs. Weiterhin wurden pro Tankdeckel "
            "zwei zusätzliche Spülflansche für die chemische Präparation sowie für "
            "die Hochdruckspüle mit hochreinem Wasser hinzugefügt. Das Tuning der "
            "Kavität erfolgt über einen neuartigen Ansatz, indem zwei bewegliche "
            "Balgtuner in das Resonatorvolumen eingebracht werden und extern über "
            "eine Tunerstange ausgelenkt werden können. Der Antrieb der Stange soll "
            "im späteren Betrieb wahlweise über einen Schrittmotor oder einen "
            "Piezoaktor stattfinden. Für ein langsames/ statisches Tuning kann der "
            "Schrittmotor den Tuner im Bereich +/- 1 mm auslenken, um größeren "
            "Frequenzabweichungen in der Größenordnung 100 kHz nach dem Abkühlen "
            "entgegenzuwirken. Das schnelle Tuning im niedrigen kHz-Bereich wird "
            "von einem Piezoaktor übernommen, welcher den Balg um einige µm bewegen "
            "kann, um Microphonics oder Lorentz-Force-Detuning zu kompensieren. Der "
            "Resonator wird von einem aus Titan bestehendem Heliummantel umgeben, "
            "wodurch ein geschlossener Heliumkreislauf gebildet wird. Derzeit "
            "befinden sich mehrere Projekte in der Planung bzw. im Bau, welche auf "
            "eine derartige Resonatorgeometrie zurückgreifen könnten. An der GSI "
            "basiert der Hauptteil des zukünftigen cw LINAC auf supraleitenden CH-"
            "Strukturen, um einen Strahl für die Synthese neuer, superschwerer "
            "Elemente zu liefern. Weiterhin könnte ein Upgrade des vorhandenen GSI "
            "UNILAC durch den Einsatz von supraleitenden CH-Resonatoren gestaltet "
            "werden. Zudem besteht die Möglichkeit, die bisherige Alvarez-Sektion "
            "des UNILAC alternativ durch eine kompakte, supraleitende CH-Sektion zu "
            "realisieren. Ebenfalls sollen die beiden parallelbetriebenen "
            "Injektorsektionen des MYRRHA-Projektes durch den Einsatz von "
            "supraleitenden CH-Strukturen erfolgen."

        )
    page_nr_gt = "133"

    assert splash["abstract"]
    assert splash["abstract"] == abstract_gt
    assert splash["page_nr"]
    assert splash["page_nr"] == page_nr_gt

def test_get_affiliations(affiliations):
    """Test affiliation getting."""
    assert affiliations == ["Frankfurt am Main, Johann Wolfgang Goethe-Univ."]

def test_get_authors(authors):
    """Test author getting."""
    assert authors
    assert authors == [
        {
            "affiliation": "Frankfurt am Main, Johann Wolfgang Goethe-Univ.", 
            "surname": "Busch", 
            "given_names": "Marco", 
            "full_name": "Busch, Marco"
        }
    ]

def test_get_urls(urls):
    """Test url getting from the xml."""
    assert urls == [
        u"http://nbn-resolving.de/urn:nbn:de:hebis:30:3-386257", 
        u"http://d-nb.info/1079912991/34", 
        u"http://publikationen.ub.uni-frankfurt.de/frontdoor/index/index/docId/38625"
    ]

def test_find_direct_links(direct_links):
    """Test direct and splash link recognising."""
    splash_links = direct_links[1]
    assert direct_links[0] == ["http://d-nb.info/1079912991/34"]
    assert splash_links == [
        u"http://nbn-resolving.de/urn:nbn:de:hebis:30:3-386257", 
        u"http://publikationen.ub.uni-frankfurt.de/frontdoor/index/index/docId/38625"
    ]
