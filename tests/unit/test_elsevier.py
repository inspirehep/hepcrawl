# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function, unicode_literals

import fnmatch

import pytest
import requests_mock

from hepcrawl.spiders import elsevier_spider

from hepcrawl.testlib.fixtures import (
    fake_response_from_file,
    fake_response_from_string,
    get_node,
)


# Old tests for harvestingkit:
# https://github.com/inspirehep/harvesting-kit/blob/master/harvestingkit/tests/elsevier_package_tests.py

@pytest.fixture(scope="module")
def record():
    """Return results generator from the Elsevier spider."""
    spider = elsevier_spider.ElsevierSpider()
    with requests_mock.Mocker() as mock:
        mock.head(
            'http://www.sciencedirect.com/science/article/pii/sample_consyn_record',
            headers={
                'Content-Type': 'text/html',
            }
        )
        response = fake_response_from_file('elsevier/sample_consyn_record.xml')
        response.meta["xml_url"] = 'elsevier/sample_consyn_record.xml'
        tag = '//%s' % spider.itertag
        nodes = get_node(spider, tag, response)

        parsed_item = spider.parse_node(response, nodes)
        assert parsed_item
        assert parsed_item.record

        return parsed_item.record


@pytest.fixture(scope="module")
def parsed_node():
    """Test data that have different values than in the sample record."""
    # NOTE: this tries to make a GET request
    with requests_mock.Mocker() as mock:
        mock.head(
            'http://www.sciencedirect.com/science/article/pii/sample_consyn_record',
            headers={
                'Content-Type': 'text/html',
            }
        )
        spider = elsevier_spider.ElsevierSpider()
        body = """
        <doc xmlns:oa="http://vtw.elsevier.com/data/ns/properties/OpenAccess-1/"
            xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:dct="http://purl.org/dc/terms/"
            xmlns:prism="http://prismstandard.org/namespaces/basic/2.0/">
            <oa:openAccessInformation>
                <oa:openAccessStatus xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                http://vtw.elsevier.com/data/voc/oa/OpenAccessStatus#Full
                </oa:openAccessStatus>
                <oa:openAccessEffective xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2014-11-11T08:38:44Z</oa:openAccessEffective>
                <oa:sponsor xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                <oa:sponsorName>SCOAP&#xB3; - Sponsoring Consortium for Open Access Publishing in Particle Physics</oa:sponsorName>
                <oa:sponsorType>http://vtw.elsevier.com/data/voc/oa/SponsorType#FundingBody</oa:sponsorType>
                </oa:sponsor>
                <oa:userLicense xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">http://creativecommons.org/licenses/by/3.0/</oa:userLicense>
            </oa:openAccessInformation>
            <rdf:Description rdf:about="http://dx.doi.org/10.1016/0370-2693(88)91603-6">
                <dct:title>Toward classification of conformal theories</dct:title>
                <prism:doi>10.1016/0370-2693(88)91603-6</prism:doi>
                <prism:startingPage>421</prism:startingPage>
                <prism:publicationName>Physics Letters, Section B</prism:publicationName>
                <prism:volume>206</prism:volume>
                <dct:creator>Cumrun Vafa</dct:creator>
                <dct:subject>
                    <rdf:Bag>
                        <rdf:li>Heavy quarkonia</rdf:li>
                        <rdf:li>Quark gluon plasma</rdf:li>
                        <rdf:li>Mott effect</rdf:li>
                        <rdf:li>X(3872)</rdf:li>
                    </rdf:Bag>
                </dct:subject>
            </rdf:Description>
        </doc>"""

        response = fake_response_from_string(body)
        node = get_node(spider, '/doc', response)
        response.meta["xml_url"] = 'elsevier/sample_consyn_record.xml'
        parse_response = spider.parse_node(response, node)
        parse_response.status = 404

        parsed_item = spider.scrape_sciencedirect(parse_response)
        assert parsed_item
        assert parsed_item.record

        return parsed_item.record


def test_collection(parsed_node):
    assert parsed_node["collections"] == [{'primary': 'HEP'},
                                          {'primary': 'Citeable'},
                                          {'primary': 'Published'}]


def test_license_oa(parsed_node):
    expected_license = [{
        'license': None,
        'material': None,
        'url': 'http://creativecommons.org/licenses/by/3.0/',
    }]
    assert parsed_node["license"] == expected_license


def test_prism_dois(parsed_node):
    assert parsed_node["dois"]
    assert parsed_node["dois"][0]["value"] == u'10.1016/0370-2693(88)91603-6'


def test_dct_title(parsed_node):
    assert parsed_node["title"] == "Toward classification of conformal theories"


def test_rdf_keywords(parsed_node):
    keywords = ['Heavy quarkonia', 'Quark gluon plasma', 'Mott effect', 'X(3872)']
    assert [dic["value"] for dic in parsed_node["free_keywords"]] == keywords


def test_date_published_oa(parsed_node):
    assert parsed_node["journal_year"] == 2014
    assert parsed_node["date_published"] == "2014-11-11"


def test_prism_title(parsed_node):
    assert parsed_node["journal_title"] == u'Physics Letters'
    assert parsed_node["journal_volume"] == u'B206'


@pytest.fixture
def sd_url():
    spider = elsevier_spider.ElsevierSpider()
    xml_file = 'elsevier/sample_consyn_record.xml'
    return spider._get_sd_url(xml_file)


def test_get_sd_url(sd_url):
    assert sd_url
    assert sd_url == u'http://www.sciencedirect.com/science/article/pii/sample_consyn_record'


@pytest.fixture
def cover_display_date():
    """Parse and build the record with only date (day, month and year)."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:prism="http://prismstandard.org/namespaces/basic/2.0/">
        <rdf:Description>
            <prism:coverDisplayDate>1 December 2014</prism:coverDisplayDate>
        </rdf:Description>
    </doc>"""

    node = get_node(spider, '/doc', text=body)
    response = fake_response_from_string(body)
    parsed_item = spider.parse_node(response, node)
    assert parsed_item
    assert parsed_item.record

    return parsed_item.record


def test_cover_display_date(cover_display_date):
    """Test coverDisplayDate and correct formatting with day, year and month."""
    assert cover_display_date
    assert cover_display_date["journal_year"] == 2014
    assert cover_display_date["date_published"] == '2014-12-01'


@pytest.fixture
def cover_display_date_y_m():
    """Parse and build the record with only date (month and year)."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:prism="http://prismstandard.org/namespaces/basic/2.0/">
        <rdf:Description>
            <prism:coverDisplayDate>December 2014</prism:coverDisplayDate>
        </rdf:Description>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    response = fake_response_from_string(body)
    parsed_item = spider.parse_node(response, node)
    assert parsed_item
    assert parsed_item.record

    return parsed_item.record


def test_cover_display_date_y_m(cover_display_date_y_m):
    """Test coverDisplayDate and correct formatting with only year and month."""
    assert cover_display_date_y_m
    assert cover_display_date_y_m["journal_year"] == 2014
    assert cover_display_date_y_m["date_published"] == '2014-12'


@pytest.fixture
def cover_display_date_y():
    """Parse and build the record with only date (year)."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:prism="http://prismstandard.org/namespaces/basic/2.0/">
        <rdf:Description>
            <prism:coverDisplayDate>2014</prism:coverDisplayDate>
        </rdf:Description>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    response = fake_response_from_string(body)
    parsed_item = spider.parse_node(response, node)
    assert parsed_item
    assert parsed_item.record

    return parsed_item.record


def test_cover_display_date_y(cover_display_date_y):
    """Test coverDisplayDate and correct formatting with only year."""
    assert cover_display_date_y
    assert cover_display_date_y["journal_year"] == 2014
    assert cover_display_date_y["date_published"] == '2014'


@pytest.fixture(scope="module")
def item_info():
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ja="http://www.elsevier.com/xml/ja/schema"
        xmlns:ce="http://www.elsevier.com/xml/common/schema">
    <ja:item-info>
        <ja:jid>PLB</ja:jid>
        <ja:aid>91603</ja:aid>
        <ce:doi>10.1016/j.nima.2016.01.020</ce:doi>
        <ce:copyright type="unknown" year="1988">
        Elsevier
        </ce:copyright>
    </ja:item-info>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return (
        spider.get_copyright(node),
        spider._get_publication(node),
        spider.get_date(node)
    )


def test_copyright_holder(item_info):
    copyright, _, _ = item_info
    assert copyright
    assert copyright['cr_holder'] == u'Elsevier'
    assert copyright['cr_year'] == u'1988'


def test_get_publication_jid(item_info):
    _, publication, _ = item_info
    assert publication
    #assert publication == 'Physics letters B'
    assert publication == 'PLB'


def test_doi_date(item_info):
    _, _, date = item_info
    year, date_published = date
    assert item_info
    assert year == 2016
    assert date_published == u'2016'


def test_title(record):
    """Test extracting title."""
    assert record['title']
    assert record['title'] == "Toward classification of conformal theories"


def test_abstract(record):
    abstract = (
        "By studying the representations of the mapping class groups which "
        "arise in 2D conformal theories we derive some restrictions on the "
        "value of the conformal dimension hi of operators and the central "
        "charge c of the Virasoro algebra. As a simple application we show "
        "that when there are a finite number of operators in the conformal "
        "algebra, the hi and c are all rational."
        )
    assert record["abstract"]
    assert record["abstract"] == abstract


def test_date_published(record):
    """Test extracting date_published."""
    assert record['date_published']
    assert record['date_published'] == "1988-05-26"


def test_authors(record):
    """Test authors."""
    authors = ["Vafa, Cumrun"]
    affiliation = u'Lyman Laboratory of Physics, Harvard University, Cambridge, MA 02138, USA'
    assert record['authors']
    assert len(record['authors']) == len(authors)

    # here we are making sure order is kept
    for index, name in enumerate(authors):
        assert record['authors'][index]['full_name'] == name
        assert record['authors'][index]['affiliations'][0]['value'] == affiliation


def test_files(record):
    """Test file urls."""
    assert record["documents"]
    assert record["documents"][0]['url'] == "elsevier/sample_consyn_record.xml"


def test_dois(record):
    """Test that dois are good."""
    assert record["dois"]
    assert record["dois"][0]["value"] == "10.1016/0370-2693(88)91603-6"


def test_doctype(record):
    """Test that doctype is good."""
    assert record["journal_doctype"]
    assert record["journal_doctype"] == "full-length article"


def test_keywords(record):
    """Test that keywords are good."""
    keywords = ['Heavy quarkonia', 'Quark gluon plasma', 'Mott effect', 'X(3872)']
    assert record["free_keywords"]
    assert [dic["value"] for dic in record["free_keywords"]] == keywords


def test_copyright(record):
    """Test that copyright is good."""
    cr_statement = "Copyright 2014 Elsevier B.V. All rights reserved."
    assert record["copyright_statement"]
    assert record["copyright_statement"] == cr_statement


@pytest.fixture
def format_arxiv():
    spider = elsevier_spider.ElsevierSpider()
    return spider._format_arxiv_id([u'arxiv:1012.2314'])


def test_format_arxiv(format_arxiv):
    assert format_arxiv
    assert format_arxiv == u'arxiv:1012.2314'


@pytest.fixture
def authors():
    """Authors with different kinds of structures: affiliations,
    group affiliations, collaborations, two different author groups, and
    two alternative ways of writing affiliation info: ce:textfn or sa:affiliation."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sa="http://www.elsevier.com/xml/common/struct-aff/schema">
    <ce:author-group>
        <ce:author orcid="1234-5678-4321-8765">
          <ce:given-name>Physical</ce:given-name>
          <ce:surname>Scientist</ce:surname>
          <ce:cross-ref refid="aff1">
            <ce:sup>a</ce:sup>
          </ce:cross-ref>
        </ce:author>
        <ce:author>
          <ce:given-name>Philosophical</ce:given-name>
          <ce:surname>Doctor</ce:surname>
          <ce:cross-ref refid="aff2">
            <ce:sup>b</ce:sup>
          </ce:cross-ref>
          <ce:e-address>author.email@address.com</ce:e-address>
        </ce:author>
        <ce:affiliation>
          <ce:textfn>Research Center for Advanced Science</ce:textfn>
        </ce:affiliation>
        <ce:affiliation id="aff1">
          <ce:label>a</ce:label>
          <ce:textfn>Department of Physics</ce:textfn>
        </ce:affiliation>
        <ce:affiliation id="aff2">
          <ce:label>b</ce:label>
          <ce:textfn>Department of Astronomy</ce:textfn>
        </ce:affiliation>
        <ce:collaboration>
          <ce:text>The Serious Science Collaboration</ce:text>
          <ce:collab-aff>Cryogenic Lab</ce:collab-aff>
        </ce:collaboration>
      </ce:author-group>
      <ce:author-group>
        <ce:author>
          <ce:given-name>Guy</ce:given-name>
          <ce:surname>Random</ce:surname>
          <ce:cross-ref refid="aff3">
            <ce:sup>b</ce:sup>
          </ce:cross-ref>
        </ce:author>
        <ce:affiliation id="aff3">
          <ce:label>c</ce:label>
          <sa:affiliation>
            <sa:organization>Super Cool University</sa:organization>
            <sa:city>Coolstadt</sa:city>
          </sa:affiliation>
        </ce:affiliation>
        <ce:collaboration>
          <ce:text>Not So Serious Collaboration</ce:text>
        </ce:collaboration>
      </ce:author-group>
      </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_authors(node)


def test_get_authors(authors):
    assert authors
    assert authors == [
        {
            'orcid': 'ORCID:1234-5678-4321-8765',
            'affiliations': [{'value': u'Department of Physics'},
                             {'value': u'Research Center for Advanced Science'}],
            'collaborations': [u'The Serious Science Collaboration'],
            'surname': u'Scientist', 'given_names': u'Physical'
        }, {
            'collaborations': [u'The Serious Science Collaboration'],
            'affiliations': [{'value': u'Department of Astronomy'},
                             {'value': u'Research Center for Advanced Science'}],
            'surname': u'Doctor',
            'given_names': u'Philosophical',
            'email': u'author.email@address.com'
        }, {
            'collaborations': [u'Not So Serious Collaboration'],
            'affiliations': [{'value': u'Super Cool University, Coolstadt'}],
            'surname': u'Random',
            'given_names': u'Guy'
        }
    ]


@pytest.fixture
def ref_textref():
    """Raw textref string without inner structure."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema">
    <ce:bib-reference id="bib12">
        <ce:textref>D. Friedan and S. Shenker, unpublished.</ce:textref>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_textref(ref_textref):
    assert ref_textref
    assert ref_textref == [{
        'raw_reference': [u'D. Friedan and S. Shenker, unpublished.']
    }]


@pytest.fixture
def ref_textref_sublabels():
    """Raw textref strings with bad sublabels."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema">
    <ce:bib-reference id="bib14">
        <ce:label>[x3]</ce:label>
        <ce:other-ref id="CE0030">
            <ce:label>a</ce:label>
            <ce:textref>D. Kastor, E. Martinec and Z. Qiu, E. Fermi Institute preprint EFI-87-58.</ce:textref>
        </ce:other-ref>
        <ce:other-ref id="CE0035">
            <ce:label>b</ce:label>
            <ce:textref>G. Moore and N. Seiberg, unpublished.</ce:textref>
        </ce:other-ref>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_textref_sublabels(ref_textref_sublabels):
    assert ref_textref_sublabels
    assert ref_textref_sublabels == [
        {'raw_reference': [u'D. Kastor, E. Martinec and Z. Qiu, E. Fermi Institute preprint EFI-87-58.']},
        {'raw_reference': [u'G. Moore and N. Seiberg, unpublished.']}
    ]


@pytest.fixture
def ref_simple_journal():
    """ Simple journal article, two authors et al., paginated by issue. With notes."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema">
    <ce:bib-reference id="ref1">
        <ce:label>[1]</ce:label>
        <sb:reference>
            <sb:contribution>
            <sb:authors>
                <sb:author>
                <ce:given-name>A.</ce:given-name>
                <ce:surname>P&#xE4;ivi&#xF6;</ce:surname>
                </sb:author>
                <sb:author>
                <ce:given-name>L.J.</ce:given-name>
                <ce:surname>Becker</ce:surname>
                </sb:author>
                <sb:et-al/>
            </sb:authors>
            <sb:title>
                <sb:maintitle>Comparisons through the mind&#x2019;s eye</sb:maintitle>
            </sb:title>
            </sb:contribution>
            <sb:host>
            <ce:doi>[this is a doi number]</ce:doi>
            <sb:issue>
                <sb:series>
                <sb:title>
                    <sb:maintitle>Cognition</sb:maintitle>
                </sb:title>
                <sb:volume-nr>37</sb:volume-nr>
                </sb:series>
                <sb:issue-nr>2</sb:issue-nr>
                <sb:date>1975</sb:date>
            </sb:issue>
            <sb:pages>
                <sb:first-page>635</sb:first-page>
                <sb:last-page>647</sb:last-page>
            </sb:pages>
            </sb:host>
        </sb:reference>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_simple_journal(ref_simple_journal):
    assert ref_simple_journal
    assert ref_simple_journal == [{
        'volume': u'37',
        'doi': u'doi:[this is a doi number]',
        'title': u'Comparisons through the mind\u2019s eye',
        'journal': u'Cognition',
        'authors': [u'P\xe4ivi\xf6, A. & Becker, L.J. et al.'],
        'number': 1,
        'lpage': u'647',
        'fpage': u'635',
        'year': u'1975',
        'issue': u'2',
        'journal_pubnote': [u'Cognition,37(2),635-647']
    }]


@pytest.fixture
def ref_simple_journal_suppl():
    """An article in a journal supplement, only first page given.
    One author is a collaboration.
    """
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema">
    <ce:bib-reference id="ref2">
        <ce:label>[2]</ce:label>
        <sb:reference>
            <sb:contribution>
            <sb:authors>
                <sb:author>
                <ce:given-name>S.</ce:given-name>
                <ce:surname>Koczkas</ce:surname>
                </sb:author>
                <sb:author>
                <ce:given-name>G.</ce:given-name>
                <ce:surname>Holmberg</ce:surname>
                </sb:author>
                <sb:author>
                <ce:given-name>L.</ce:given-name>
                <ce:surname>Wedin</ce:surname>
                </sb:author>
                <sb:collaboration>The Collaboration</sb:collaboration>
            </sb:authors>
            <sb:title>
                <sb:maintitle>A pilot study of the effect of ...</sb:maintitle>
            </sb:title>
            </sb:contribution>
            <sb:host>
            <sb:issue>
                <sb:series>
                <sb:title>
                    <sb:maintitle>Acta Psychiatrica Scandinavica</sb:maintitle>
                </sb:title>
                <sb:volume-nr>63</sb:volume-nr>
                </sb:series>
                <sb:issue-nr>Suppl. 290</sb:issue-nr>
                <sb:date>1981</sb:date>
            </sb:issue>
            <sb:pages>
                <sb:first-page>328</sb:first-page>
            </sb:pages>
            </sb:host>
        </sb:reference>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_simple_journal_suppl(ref_simple_journal_suppl):
    assert ref_simple_journal_suppl
    assert ref_simple_journal_suppl == [{
        'title': u'A pilot study of the effect of ...',
        'collaboration': [u'The Collaboration'],
        'journal': u'Acta Psychiatrica Scandinavica',
        'authors': [u'Koczkas, S., Holmberg, G. & Wedin, L.'],
        'number': 2,
        'volume': u'63',
        'fpage': u'328',
        'year': u'1981',
        'issue': u'Suppl. 290',
        'journal_pubnote': [u'Acta Psychiatrica Scandinavica,63(Suppl.290),328']
    }]


@pytest.fixture
def ref_journal_issue():
    """Entire issue of a journal. In addition to the sb:title in the sb:series
    (the journal title), the issue of this example has a title and (guest) editors
    of its own. The additional text ’(special issue)’ is tagged as a comment. Only
    author surnames given.
    """
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema">
    <ce:bib-reference id="ref3">
        <ce:label>[3]</ce:label>
        <sb:reference>
            <sb:host>
            <sb:issue>
                <sb:editors>
                <sb:editor>
                    <ce:surname>Glaser</ce:surname>
                </sb:editor>
                <sb:editor>
                    <ce:surname>Bond</ce:surname>
                </sb:editor>
                </sb:editors>
                <sb:title>
                <sb:maintitle>Testing: concepts and research</sb:maintitle>
                </sb:title>
                <sb:series>
                <sb:title>
                    <sb:maintitle>American Psychologist</sb:maintitle>
                </sb:title>
                <sb:volume-nr>36</sb:volume-nr>
                </sb:series>
                <sb:issue-nr>10&ndash;12</sb:issue-nr>
                <sb:date>1981</sb:date>
            </sb:issue>
            </sb:host>
            <sb:comment>(special issue)</sb:comment>
        </sb:reference>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_journal_issue(ref_journal_issue):
    assert ref_journal_issue
    assert ref_journal_issue == [{
        'journal': u'Testing: concepts and research; American Psychologist',
        'misc': [u'special issue'],
        'editors': [u'Glaser & Bond'],
        'number': 3,
        'volume': u'36',
        'year': u'1981',
        'issue': u'1012',
        'journal_pubnote': [u'Testing: concepts and research; American Psychologist,36(1012)']
    }]


@pytest.fixture
def ref_translated_article():
    """ Non-English journal article, with an English sb:translated-title."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema">
    <ce:bib-reference id="ref4">
        <ce:label>[4]</ce:label>
        <sb:reference>
            <sb:contribution lang-type="iso" xml:lang="nl">
            <sb:authors>
                <sb:author>
                <ce:given-name>E.M.H.</ce:given-name>
                <ce:surname>Assink</ce:surname>
                </sb:author>
                <sb:author>
                <ce:given-name>N.</ce:given-name>
                <ce:surname>Verloop</ce:surname>
                </sb:author>
            </sb:authors>
            <sb:title>
                <sb:maintitle>Het aanleren van deel&ndash;geheel relaties</sb:maintitle>
            </sb:title>
            <sb:translated-title>
                <sb:maintitle>Teaching part&ndash;whole relations</sb:maintitle>
            </sb:translated-title>
            </sb:contribution>
            <sb:host>
            <sb:issue>
                <sb:series>
                <sb:title>
                    <sb:maintitle>Pedagogische Studie&#x308;n</sb:maintitle>
                </sb:title>
                <sb:volume-nr>54</sb:volume-nr>
                </sb:series>
                <sb:date>1977</sb:date>
            </sb:issue>
            <sb:pages>
                <sb:first-page>130</sb:first-page>
                <sb:last-page>142</sb:last-page>
            </sb:pages>
            </sb:host>
        </sb:reference>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_translated_article(ref_translated_article):
    assert ref_translated_article
    assert ref_translated_article == [{
        'volume': u'54',
        'title': u'Het aanleren van deelgeheel relaties (Teaching partwhole relations)',
        'journal': u'Pedagogische Studie\u0308n',
        'authors': [u'Assink, E.M.H. & Verloop, N.'],
        'number': 4,
        'lpage': u'142',
        'fpage': u'130',
        'year': u'1977',
        'journal_pubnote': [u'Pedagogische Studie\u0308n,54,130']
    }]


@pytest.fixture
def ref_monograph():
    """Monograph with notes."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema">
    <ce:bib-reference id="ref5">
        <ce:label>[5]</ce:label>
        <sb:reference>
            <sb:contribution>
            <sb:authors>
                <sb:author>
                <ce:given-name>W.</ce:given-name>
                <ce:surname>Strunk</ce:surname>
                <ce:suffix>Jr.</ce:suffix>
                </sb:author>
                <sb:author>
                <ce:given-name>E.B.</ce:given-name>
                <ce:surname>White</ce:surname>
                </sb:author>
            </sb:authors>
            <sb:title>
                <sb:maintitle>The elements of style</sb:maintitle>
            </sb:title>
            </sb:contribution>
            <sb:host>
            <sb:book>
                <sb:edition>3rd ed.</sb:edition>
                <sb:date>1979</sb:date>
                <sb:isbn>0-02-418190-0</sb:isbn>
                <sb:publisher>
                    <sb:name>MacMillan</sb:name>
                    <sb:location>New York</sb:location>
                </sb:publisher>
            </sb:book>
            </sb:host>
        </sb:reference>
        <ce:note>
            <ce:simple-para>This reference discusses the basic concepts in
            a very thorough manner.</ce:simple-para>
            <ce:simple-para>Its literature list is a main entry point
            into the discipline.</ce:simple-para>
        </ce:note>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_monograph(ref_monograph):
    assert ref_monograph
    assert ref_monograph == [{
        'publisher': u'New York: MacMillan',
        'book_title': u'The elements of style',
        'year': u'1979',
        'number': 5,
        'misc': [u'This reference discusses the basic concepts in a very thorough manner. Its literature list is a main entry point into the discipline.'],
        'authors': [u'Strunk, W. & White, E.B.'],
        'isbn': u'0-02-418190-0'
    }]


@pytest.fixture
def ref_book_no_authors():
    """Book without authors."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema">
    <ce:bib-reference id="ref6">
        <ce:label>[6]</ce:label>
        <sb:reference>
            <sb:host>
            <sb:book>
                <sb:title>
                <sb:maintitle>College bound seniors</sb:maintitle>
                </sb:title>
                <sb:date>1979</sb:date>
                <sb:publisher>
                <sb:name>College Board Publications</sb:name>
                <sb:location>Princeton, NJ</sb:location>
                </sb:publisher>
            </sb:book>
            </sb:host>
        </sb:reference>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_book_no_authors(ref_book_no_authors):
    assert ref_book_no_authors
    assert ref_book_no_authors == [
        {'publisher': u'Princeton, NJ: College Board Publications',
         'book_title': u'College bound seniors',
         'year': u'1979',
         'number': 6}
    ]


@pytest.fixture
def ref_book_translated():
    """Book originally published in another language, with a translator.
    In this example the original title and the original language are not given.
    """
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema">
    <ce:bib-reference id="ref7">
        <ce:label>[7]</ce:label>
        <sb:reference>
            <sb:contribution>
            <sb:authors>
                <sb:author>
                <ce:given-name>A.R.</ce:given-name>
                <ce:surname>Luria</ce:surname>
                </sb:author>
            </sb:authors>
            <sb:title>
                <sb:maintitle>The mind of a mnemonist</sb:maintitle>
            </sb:title>
            </sb:contribution>
            <sb:comment>(L. Solotarof, Trans.)</sb:comment>
            <sb:host>
            <sb:book>
                <sb:date>1969</sb:date>
                <sb:publisher>
                <sb:name>Avon books</sb:name>
                <sb:location>New York</sb:location>
                </sb:publisher>
            </sb:book>
            </sb:host>
            <sb:comment>(Original work published 1965)</sb:comment>
        </sb:reference>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_book_translated(ref_book_translated):
    assert ref_book_translated
    assert ref_book_translated == [{
        'authors': [u'Luria, A.R.'],
        'book_title': u'The mind of a mnemonist',
        'number': 7,
        'misc': [u'L. Solotarof, Trans. Original work published 1965'],
        'publisher': u'New York: Avon books',
        'year': u'1969'
    }]


@pytest.fixture
def ref_edited_book_article():
    """ Article in edited book. Only first page given."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema">
    <ce:bib-reference id="ref8">
        <ce:label>[8]</ce:label>
        <sb:reference>
            <sb:contribution>
            <sb:authors>
                <sb:author>
                <ce:given-name>A.S.</ce:given-name>
                <ce:surname>Gurman</ce:surname>
                </sb:author>
                <sb:author>
                <ce:given-name>D.P.</ce:given-name>
                <ce:surname>Kniskern</ce:surname>
                </sb:author>
            </sb:authors>
            <sb:title>
                <sb:maintitle>Family therapy outcome research: knowns and unknowns</sb:maintitle>
            </sb:title>
            </sb:contribution>
            <sb:host>
            <sb:edited-book>
                <sb:editors>
                <sb:editor>
                    <ce:given-name>G.F.</ce:given-name>
                    <ce:surname>Editor1</ce:surname>
                </sb:editor>
                <sb:editor>
                    <ce:given-name>X.S.</ce:given-name>
                    <ce:surname>Editor2</ce:surname>
                </sb:editor>
                </sb:editors>
                <sb:title>
                <sb:maintitle>Handbook of family therapy</sb:maintitle>
                </sb:title>
                <sb:date>1981</sb:date>
                <sb:publisher>
                <sb:name>Brunner/Mazel</sb:name>
                <sb:location>New York</sb:location>
                </sb:publisher>
            </sb:edited-book>
            <sb:pages>
                <sb:first-page>742</sb:first-page>
            </sb:pages>
            </sb:host>
        </sb:reference>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_edited_book_article(ref_edited_book_article):
    assert ref_edited_book_article
    assert ref_edited_book_article == [{
        'authors': [u'Gurman, A.S. & Kniskern, D.P.'],
        'book_title': u'Handbook of family therapy',
        'editors': [u'Editor1, G.F. & Editor2, X.S.'],
        'fpage': u'742',
        'number': 8,
        'publisher': u'New York: Brunner/Mazel',
        'title': u'Family therapy outcome research: knowns and unknowns',
        'year': u'1981'
    }]


@pytest.fixture
def ref_edited_book_article_repr():
    """Article in edited book, reprinted from another source."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema">
    <ce:bib-reference id="ref9">
        <ce:label>[9]</ce:label>
        <sb:reference>
            <sb:contribution>
            <sb:authors>
                <sb:author>
                <ce:given-name>C.E.</ce:given-name>
                <ce:surname>Sluzki</ce:surname>
                </sb:author>
                <sb:author>
                <ce:given-name>J.</ce:given-name>
                <ce:surname>Beavin</ce:surname>
                </sb:author>
            </sb:authors>
            <sb:title>
                <sb:maintitle>Symmetry and complementarity</sb:maintitle>
            </sb:title>
            </sb:contribution>
            <sb:host>
            <sb:edited-book>
                <sb:editors>
                <sb:editor>
                    <ce:given-name>P.</ce:given-name>
                    <ce:surname>Watzlawick</ce:surname>
                </sb:editor>
                <sb:editor>
                    <ce:given-name>J.H.</ce:given-name>
                    <ce:surname>Weakland</ce:surname>
                </sb:editor>
                </sb:editors>
                <sb:title>
                <sb:maintitle>The interactional view</sb:maintitle>
                </sb:title>
                <sb:date>1977</sb:date>
                <sb:publisher>
                <sb:name>Norton</sb:name>
                <sb:location>New York</sb:location>
                </sb:publisher>
            </sb:edited-book>
            <sb:pages>
                <sb:first-page>71</sb:first-page>
                <sb:last-page>87</sb:last-page>
            </sb:pages>
            </sb:host>
            <sb:comment>Reprinted from:</sb:comment>
            <sb:host>
            <sb:issue>
                <sb:series>
                <sb:title>
                    <sb:maintitle>Acta Psiquiatrica y Psicologica de America Latina</sb:maintitle>
                </sb:title>
                <sb:volume-nr>11</sb:volume-nr>
                </sb:series>
                <sb:date>1965</sb:date>
            </sb:issue>
            <sb:pages>
                <sb:first-page>321</sb:first-page>
                <sb:last-page>330</sb:last-page>
            </sb:pages>
            </sb:host>
        </sb:reference>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_edited_book_article_repr(ref_edited_book_article_repr):
    assert ref_edited_book_article_repr
    assert ref_edited_book_article_repr == [{
        'authors': [u'Sluzki, C.E. & Beavin, J.'],
        'book_title': u'The interactional view',
        'editors': [u'Watzlawick, P. & Weakland, J.H.'],
        'fpage': u'71',
        'journal': u'Acta Psiquiatrica y Psicologica de America Latina',
        'journal_pubnote': [u'Acta Psiquiatrica y Psicologica de America Latina,11,71'],
        'number': 9,
        'lpage': u'87',
        'misc': [u'Reprinted from'],
        'publisher': u'New York: Norton',
        'title': u'Symmetry and complementarity',
        'volume': u'11',
        'year': u'1977, 1965'
    }]


@pytest.fixture
def ref_book_proceedings_article():
    """Article in proceedings published as a book."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema">
    <ce:bib-reference id="ref10">
        <ce:label>[10]</ce:label>
        <sb:reference>
            <sb:contribution>
            <sb:authors>
                <sb:author>
                <ce:given-name>T.E.</ce:given-name>
                <ce:surname>Chaddock</ce:surname>
                </sb:author>
            </sb:authors>
            <sb:title>
                <sb:maintitle>Gastric emptying of a nutritionally balanced diet</sb:maintitle>
            </sb:title>
            </sb:contribution>
            <sb:host>
            <sb:edited-book>
                <sb:editors>
                <sb:editor>
                    <ce:given-name>E.E.</ce:given-name>
                    <ce:surname>Daniel</ce:surname>
                </sb:editor>
                </sb:editors>
                <sb:title>
                <sb:maintitle>Proceedings of the Fourth International Symposium on Gastrointestinal Motility</sb:maintitle>
                </sb:title>
                <sb:conference>ISGM4, 4&ndash;8 September 1973, Seattle, WA</sb:conference>
                <sb:date>1974</sb:date>
                <sb:publisher>
                <sb:name>Mitchell Press</sb:name>
                <sb:location>Vancouver, British Columbia, Canada</sb:location>
                </sb:publisher>
            </sb:edited-book>
            <sb:pages>
                <sb:first-page>83</sb:first-page>
                <sb:last-page>92</sb:last-page>
            </sb:pages>
            </sb:host>
        </sb:reference>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_book_proceedings_article(ref_book_proceedings_article):
    assert ref_book_proceedings_article
    assert ref_book_proceedings_article == [{
        'authors': [u'Chaddock, T.E.'],
        'book_title': u'Proceedings of the Fourth International Symposium on Gastrointestinal Motility',
        'editors': [u'Daniel, E.E.'],
        'fpage': u'83',
        'number': 10,
        'lpage': u'92',
        'publisher': u'Vancouver, British Columbia, Canada: Mitchell Press',
        'title': u'Gastric emptying of a nutritionally balanced diet',
        'year': u'1974'
    }]


@pytest.fixture
def ref_edited_book():
    """Edited book. In this example the whole edited book is cited."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema">
    <ce:bib-reference id="ref11">
        <ce:label>[11]</ce:label>
        <sb:reference>
            <sb:host>
            <sb:edited-book>
                <sb:editors>
                <sb:editor>
                    <ce:given-name>S.</ce:given-name>
                    <ce:surname>Letheridge</ce:surname>
                </sb:editor>
                <sb:editor>
                    <ce:given-name>C.R.</ce:given-name>
                    <ce:surname>Cannon</ce:surname>
                </sb:editor>
                </sb:editors>
                <sb:title>
                <sb:maintitle>Bilingual education</sb:maintitle>
                </sb:title>
                <sb:date>1980</sb:date>
                <sb:publisher>
                <sb:name>Praeger</sb:name>
                <sb:location>New York</sb:location>
                </sb:publisher>
            </sb:edited-book>
            </sb:host>
        </sb:reference>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_edited_book(ref_edited_book):
    assert ref_edited_book
    assert ref_edited_book == [{
        'publisher': u'New York: Praeger',
        'book_title': u'Bilingual education',
        'year': u'1980',
        'editors': [u'Letheridge, S. & Cannon, C.R.'],
        'number': 11
    }]


@pytest.fixture
def ref_multi_volume_edited():
    """A volume in a multi-volume edited work. The volume may have its own
    editors and title, as shown in this example.
    """
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema">
    <ce:bib-reference id="ref12">
        <ce:label>[12]</ce:label>
        <sb:reference>
            <sb:host>
            <sb:edited-book>
                <sb:editors>
                <sb:editor>
                    <ce:given-name>J.G.</ce:given-name>
                    <ce:surname>Wilson</ce:surname>
                </sb:editor>
                </sb:editors>
                <sb:title>
                <sb:maintitle>Basic teratology</sb:maintitle>
                </sb:title>
                <sb:book-series>
                <sb:editors>
                    <sb:editor>
                    <ce:given-name>J.G.</ce:given-name>
                    <ce:surname>Wilson</ce:surname>
                    </sb:editor>
                    <sb:editor>
                    <ce:given-name>F.C.</ce:given-name>
                    <ce:surname>Fraser</ce:surname>
                    </sb:editor>
                </sb:editors>
                <sb:series>
                    <sb:title>
                    <sb:maintitle>Handbook of teratology</sb:maintitle>
                    </sb:title>
                    <sb:volume-nr>Vol. 1</sb:volume-nr>
                </sb:series>
                </sb:book-series>
                <sb:date>1977</sb:date>
                <sb:publisher>
                <sb:name>Plenum Press</sb:name>
                <sb:location>New York</sb:location>
                </sb:publisher>
            </sb:edited-book>
            </sb:host>
        </sb:reference>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_multi_volume_edited(ref_multi_volume_edited):
    assert ref_multi_volume_edited
    assert ref_multi_volume_edited == [{
        'book_title': u'Basic teratology',
        'editors': [u'Wilson, J.G.'],
        'journal': u'Handbook of teratology',
        'journal_pubnote': [u'Handbook of teratology,1'],
        'number': 12,
        'publisher': u'New York: Plenum Press',
        'series_editors': [u'Wilson, J.G. & Fraser, F.C.'],
        'volume': u'1',
        'year': u'1977'
    }]


@pytest.fixture
def ref_multi_volume():
    """A volume in a multi-volume work.

    This volume has an author and a title. It is also split into two volumes.
    """
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema">
    <ce:bib-reference id="ref12">
        <ce:label>[12b]</ce:label>
        <sb:reference>
            <sb:host>
            <sb:book>
                <sb:authors>
                <sb:author>
                    <ce:given-name>J.G.</ce:given-name>
                    <ce:surname>Wilson</ce:surname>
                </sb:author>
                </sb:authors>
                <sb:title>
                <sb:maintitle>Basic teratology</sb:maintitle>
                </sb:title>
                <sb:book-series>
                <sb:editors>
                    <sb:editor>
                    <ce:given-name>J.G.</ce:given-name>
                    <ce:surname>Wilson</ce:surname>
                    </sb:editor>
                    <sb:editor>
                    <ce:given-name>F.C.</ce:given-name>
                    <ce:surname>Fraser</ce:surname>
                    </sb:editor>
                </sb:editors>
                <sb:series>
                    <sb:title>
                    <sb:maintitle>Handbook of teratology</sb:maintitle>
                    </sb:title>
                    <sb:volume-nr>Vols. 1-2</sb:volume-nr>
                </sb:series>
                </sb:book-series>
                <sb:date>1977</sb:date>
                <sb:publisher>
                <sb:name>Plenum Press</sb:name>
                <sb:location>New York</sb:location>
                </sb:publisher>
            </sb:book>
            </sb:host>
        </sb:reference>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_multi_volume(ref_multi_volume):
    assert ref_multi_volume
    assert ref_multi_volume == [{
        'authors': [u'Wilson, J.G.'],
        'book_title': u'Basic teratology',
        'journal': u'Handbook of teratology',
        'journal_pubnote': [u'Handbook of teratology,1-2'],
        'publisher': u'New York: Plenum Press',
        'series_editors': [u'Wilson, J.G. & Fraser, F.C.'],
        'volume': u'1-2',
        'year': u'1977'
    }]


@pytest.fixture
def ref_ehost():
    """An electronic host. In this example the sb:e-host contains the preprint,
    and the sb:issue contains the printed article. It also often occurs that
    the sb:e-host is the only host.
    """
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema"
        xmlns:xlink="http://www.w3.org/1999/xlink">
    <ce:bib-reference id="ref14">
        <ce:label>[14]</ce:label>
        <sb:reference>
            <sb:contribution>
            <sb:authors>
                <sb:author>
                <ce:given-name>F.</ce:given-name>
                <ce:surname>Yu</ce:surname>
                </sb:author>
                <sb:author>
                <ce:given-name>X.-S.</ce:given-name>
                <ce:surname>Wu</ce:surname>
                </sb:author>
            </sb:authors>
            </sb:contribution>
            <sb:host>
            <sb:issue>
                <sb:series>
                <sb:title>
                    <sb:maintitle>Phys. Rev. Lett.</sb:maintitle>
                </sb:title>
                <sb:volume-nr>68</sb:volume-nr>
                </sb:series>
                <sb:date>1992</sb:date>
            </sb:issue>
            <sb:pages>
                <sb:first-page>2996</sb:first-page>
            </sb:pages>
            </sb:host>
            <sb:host>
            <sb:e-host>
                <ce:inter-ref id="interref37" xlink:role="http://www.elsevier.com/xml/linking-roles/preprint" xlink:href="arxiv:/hep-th/9112009">hep-th/9112009</ce:inter-ref>
            </sb:e-host>
            </sb:host>
        </sb:reference>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_ehost(ref_ehost):
    assert ref_ehost
    assert ref_ehost == [{
        'arxiv_id': u'hep-th/9112009',
        'authors': [u'Yu, F. & Wu, X.-S.'],
        'fpage': u'2996',
        'journal': u'Phys. Rev. Lett.',
        'journal_pubnote': [u'Phys.Rev.Lett.,68,2996'],
        'number': 14,
        'volume': u'68',
        'year': u'1992'
    }]


@pytest.fixture
def ref_eproceedings_article():
    """Article in proceedings, published on the web."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema"
        xmlns:xlink="http://www.w3.org/1999/xlink">
    <ce:bib-reference id="ref15">
        <ce:label>[15]</ce:label>
        <sb:reference>
            <sb:contribution>
            <sb:authors>
                <sb:author>
                <ce:given-name>F.</ce:given-name>
                <ce:surname>Douglis</ce:surname>
                </sb:author>
                <sb:author>
                <ce:given-name>Th.</ce:given-name>
                <ce:surname>Ball</ce:surname>
                </sb:author>
            </sb:authors>
            <sb:title>
                <sb:maintitle>
                <ce:inter-ref id="interref38" xlink:href="http://www.research.att.com/papers/aide.ps.gz">Tracking and viewing changes on the web</ce:inter-ref>
                </sb:maintitle>
            </sb:title>
            </sb:contribution>
            <sb:host>
            <sb:edited-book>
                <sb:title>
                <ce:inter-ref id="interref39" xlink:role="http://www.elsevier.com/xml/linking-roles/text/html" xlink:href="http://usenix.org/sd96.html">Proc. 1996 USENIX Technical Conference</ce:inter-ref>
                </sb:title>
                <sb:date>January 1996</sb:date>
            </sb:edited-book>
            </sb:host>
        </sb:reference>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_eproceedings_article(ref_eproceedings_article):
    assert ref_eproceedings_article
    assert ref_eproceedings_article == [{
        'book_title': u'Proc. 1996 USENIX Technical Conference',
        'title': u'Tracking and viewing changes on the web',
        'year': u'1996',
        'number': 15,
        'url': [u'http://www.research.att.com/papers/aide.ps.gz', u'http://usenix.org/sd96.html'],
        'authors': [u'Douglis, F. & Ball, Th.']
    }]


@pytest.fixture
def ref_comment_and_note():
    """Entire issue of a journal. In addition to the sb:title in the sb:series
    (the journal title), the issue of this example has a title and (guest) editors
    of its own. The additional text ’(special issue)’ is tagged as a comment. Only
    author surnames given.
    """
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema">
    <ce:bib-reference id="ref3">
        <sb:reference>
            <sb:host>
            <sb:issue>
                <sb:series>
                    <sb:title>
                        <sb:maintitle>American Psychologist</sb:maintitle>
                    </sb:title>
                </sb:series>
            </sb:issue>
            </sb:host>
            <sb:comment>(special issue)</sb:comment>
        </sb:reference>
        <ce:note>
            <ce:simple-para>This reference discusses the basic concepts in
            a very thorough manner.</ce:simple-para>
            <ce:simple-para>Its literature list is a main entry point
            into the discipline.</ce:simple-para>
        </ce:note>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_comment_and_note(ref_comment_and_note):
    """Test what happens if there are both comment and note."""
    assert ref_comment_and_note
    assert ref_comment_and_note[0]["misc"] == [
        'special issue',
        ('This reference discusses the basic concepts in a very thorough manner. '
         'Its literature list is a main entry point into the discipline.')
    ]


@pytest.fixture
def ref_multi_years():
    """Multi-year reference."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ce="http://www.elsevier.com/xml/common/schema"
        xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/schema">
    <ce:bib-reference id="ref11">
        <sb:reference>
            <sb:host>
            <sb:edited-book>
                <sb:date>1980</sb:date>
                <sb:date>1981</sb:date>
                <sb:date>1982</sb:date>
                <sb:date>1985</sb:date>
            </sb:edited-book>
            </sb:host>
        </sb:reference>
    </ce:bib-reference>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    return spider.get_references(node)


def test_ref_multi_years(ref_multi_years):
    """Test multi year reference formatting."""
    assert ref_multi_years
    assert ref_multi_years[0]["year"] == "1980-1982, 1985"


@pytest.fixture
def handled_feed():
    """Return a request to scrape zip files indicated in the atom feed."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <title>30378-00001-FULL-XML-ASTROPART PHYS (0927-6505) 1.7.ZIP</title>
            <link href="file://tests/unit/responses/elsevier/fake_astropart.zip"/>
            <id>564321351</id>
            <updated>2015-10-31T10:29:32.774545Z</updated>
            <summary>ASTROPART PHYS (0927-6505)</summary>
        </entry>
        <entry>
            <title>9261-00001-FULL-XML-NIMA (0168-9002) 1.7.2014.ZIP</title>
            <link href="file://tests/unit/responses/elsevier/fake_nima.zip"/>
            <id>asdsdasda</id>
            <updated>2015-10-31T10:29:32.774545Z</updated>
            <summary>NIMA (0168-9002)</summary>
        </entry>
    </feed>"""
    response = fake_response_from_string(body)
    get_node(spider, '/doc', response)
    return spider.handle_feed(response)


def test_hadle_feed(handled_feed):
    """Test if response url info is correct."""
    zip_files = []
    for feed in handled_feed:
        zip_files.append(feed.url)
    assert zip_files
    assert zip_files == [
        'file://tests/unit/responses/elsevier/fake_astropart.zip',
        'file://tests/unit/responses/elsevier/fake_nima.zip'
    ]


@pytest.fixture
def handled_package(handled_feed):
    """Take the handle_feed request and use it to yield
    requests to process individual xml files.
    """
    spider = elsevier_spider.ElsevierSpider()
    astropart, nima = handled_feed
    return (
        spider.handle_package(astropart),
        spider.handle_package(nima)
    )


def test_handle_package(handled_package):
    """Check whether the response metadata is correct.
    Now testing with mock zip files without real copyrighted content.
    """
    astropart, nima = handled_package
    for astro, nima in zip(astropart, nima):
        assert nima
        assert astro
        assert astro.meta["source_folder"] == "tests/unit/responses/elsevier/fake_astropart.zip"
        url_to_match = u'file:///tmp/elsevier_fake_astropart_*/0927-6505/aip/S0927650515001656/S0927650515001656.xml'
        assert astro.meta["xml_url"] == fnmatch.filter([astro.meta["xml_url"]], url_to_match)[0]

        assert nima.meta["source_folder"] == "tests/unit/responses/elsevier/fake_nima.zip"
        url_to_match = u'file:///tmp/elsevier_fake_nima_*/0168-9002/S0168900215X00398/S0168900215015636/S0168900215015636.xml'
        assert nima.meta["xml_url"] == fnmatch.filter([nima.meta["xml_url"]], url_to_match)[0]


@pytest.fixture
def conference():
    """Test conference doctype and collection detection.

    This also has simple-article element, but it should
    be overridden by the conference doctype."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <doc xmlns:ja="http://www.elsevier.com/xml/ja/schema">
    <ja:simple-article>
        xaxaxa
    </ja:simple-article>
    <conference-info>
        <full-name>International Conference on conferences</full-name>
        <venue>CERN, Geneva</venue>
        <date-range>
        <start-date>20200315</start-date>
        </date-range>
    </conference-info>
    </doc>"""
    node = get_node(spider, '/doc', text=body)
    doctype = spider.get_doctype(node)
    return spider.get_collections(doctype)


def test_conference(conference):
    """Test conference doctype detection."""
    assert conference
    assert conference == ['HEP', 'Citeable', 'Published', 'ConferencePaper']


@pytest.fixture
def sciencedirect():
    """Scrape data from a minimal example web page."""
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <html>
    <head>
        <meta name="citation_journal_title" content="Physics Letters B">
        <meta name="citation_title" content="Toward classification of conformal theories">
        <meta name="citation_doi" content="10.1016/0370-2693(88)91603-6">
        <meta name="citation_issn" content="0370-2693">
        <meta name="citation_volume" content="206">
        <meta name="citation_issue" content="3">
        <meta name="citation_publication_date" content="1988/05/26">
        <meta name="citation_firstpage" content="421">
        <meta name="citation_lastpage" content="426">
    </head>
    </html>"""
    response = fake_response_from_string(body)
    response.meta["keys_missing"] = set([
        "journal_title", "volume", "issue", "fpage", "lpage", "year",
        "date_published", "dois", "page_nr",
        ])
    response.meta["info"] = {}
    response.meta["node"] = get_node(spider, '/head', text=body)

    parsed_item = spider.scrape_sciencedirect(response)
    assert parsed_item
    assert parsed_item.record

    return parsed_item.record


def test_sciencedirect(sciencedirect):
    """Test scraping sciencedirect web page for missing values."""
    assert sciencedirect
    assert sciencedirect["date_published"] == '1988-05-26'
    assert sciencedirect["dois"] == [{'value': u'10.1016/0370-2693(88)91603-6'}]
    assert sciencedirect["journal_volume"] == u'206'
    assert sciencedirect["journal_issue"] == u'3'
    assert sciencedirect["journal_fpage"] == u'421'
    assert sciencedirect["journal_lpage"] == u'426'
    assert sciencedirect["journal_year"] == 1988


@pytest.fixture
def sciencedirect_proof():
    """Scrape data from a minimal example web page. This hasn't been published
    yet. There is only the online paper, i.e. this is a proof.
    """
    spider = elsevier_spider.ElsevierSpider()
    body = """
    <html>
    <head>
        <meta name="citation_volume" content="Online 1.1.2016">
    </head>
    </html>"""
    response = fake_response_from_string(body)
    response.meta["keys_missing"] = set(["volume"])
    response.meta["info"] = {}
    response.meta["node"] = get_node(spider, '/head', text=body)
    return spider.scrape_sciencedirect(response)


def test_sciencedirect_proof(sciencedirect_proof):
    """Test scraping sciencedirect web page for missing values.

    As this is a paper proof, resulting HEPRecord should be None.
    """
    assert sciencedirect_proof is None
