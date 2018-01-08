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

import six

import pkg_resources
import pytest

from hepcrawl.spiders import edp_spider
from hepcrawl.items import HEPRecord

from scrapy.http import HtmlResponse, Request

from hepcrawl.testlib.fixtures import (
    fake_response_from_file,
    fake_response_from_string,
    get_node,
)


@pytest.fixture
def scrape_pos_page_body():
    """Splash page path for JATS file."""
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'edp',
            'jats_splash.html'
        )
    )


@pytest.fixture
def targzfile():
    """Path to test tar.gz file with JATS XML file."""
    return os.path.join(
        os.path.dirname(__file__),
        'responses',
        'edp',
        'test_gz.tar.gz'
    )


@pytest.fixture
def package_jats(targzfile):
    """Extract tar.gz package with JATS XML file."""
    spider = edp_spider.EDPSpider()
    response = fake_response_from_string(text="", url="file://" + targzfile)
    return spider.handle_package_file(response).next()


@pytest.fixture
def record_jats(package_jats, scrape_pos_page_body):
    """Return results from the EDP spider with JATS format.

    This is an open access journal, so we can scrape the splash page.
    """
    spider = edp_spider.EDPSpider()
    xml_path = package_jats.url.replace("file://", "")
    fake_resp = fake_response_from_file(xml_path)
    node = get_node(spider, "//article", fake_resp)[0]
    request = spider.parse_node(fake_resp, node)
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=scrape_pos_page_body,
        **{'encoding': 'utf-8'}
    )

    parsed_item = request.callback(response)
    assert parsed_item
    assert parsed_item.record

    return parsed_item.record


@pytest.fixture
def tarbzfile():
    """Path to test tar.bz file with 'rich' XML file"""
    return os.path.join(
        os.path.dirname(__file__),
        'responses',
        'edp',
        'test_rich.tar.bz2'
    )

@pytest.fixture
def package_rich(tarbzfile):
    """Extract tar.gz package with 'rich' XML file."""
    spider = edp_spider.EDPSpider()
    response = fake_response_from_string(text="", url="file://" + tarbzfile)
    return spider.handle_package_file(response).next()

@pytest.fixture
def record_rich(package_rich):
    """Return results from the EDP spider with 'rich' format.

    This is not an open access journal, so no splash scraping.
    """
    spider = edp_spider.EDPSpider()
    xml_path = package_rich.url.replace("file://", "")
    fake_resp = fake_response_from_file(xml_path)
    fake_resp.meta["rich"] = True
    node = get_node(spider, "//EDPSArticle", fake_resp)[0]

    parsed_item = spider.parse_node(fake_resp, node)
    assert parsed_item
    assert parsed_item.record

    return parsed_item.record


def test_title(record_jats):
    """Test extracting title."""
    title = "Calculation of photo-nuclear reaction cross sections for O"

    assert 'title' in record_jats
    assert record_jats['title'] == title


def test_abstract(record_jats):
    """Test abstract."""
    abstract = (
        "Because of the high thermal expansion coefficient of uranium, the fuel "
        "used in nuclear power plants is usually in the form of UO$_{2}$ which "
        "has ceramic structure and small thermal expansion coefficient. "
        "UO$_{2}$ include one uranium atom and two oxygen atoms. After fission "
        "progress, total energy values of emitted gamma are about 14 MeV. This "
        "gamma energy may cause transmutation of $^{16}$O isotopes. "
        "Transmutation of $^{16}$O isotopes changes physical properties of "
        "nuclear fuel. Due to above explanations, it is very important to "
        "calculate photo-nuclear reaction cross sections of $^{16}$O. In this "
        "study; for (γ,p), (γ,np), (γ,n) and (γ,2n) reactions of $^{16}$O, "
        "photo-nuclear reaction cross-sections were calculated using different "
        "models for pre-equilibrium and equilibrium effects. Taking incident "
        "gamma energy values up to 40 MeV, Hybrid and Cascade Exciton Models "
        "were used for pre-equilibrium calculations and Weisskopf-Ewing "
        "(Equilibrium) Model was used for equilibrium model calculations. "
        "Calculation results were compared with experimental and theoretical "
        "data. While experimental results were obtained from EXFOR, TENDL-2013, "
        "JENDL/PD-2004 and ENDF/B VII.1 data base were used to get theoretical "
        "results."
    )

    assert 'abstract' in record_jats
    assert record_jats['abstract'] == abstract


def test_date_published(record_jats):
    """Test extracting date_published."""
    date_published = "2015-01-01"

    assert 'date_published' in record_jats
    assert record_jats['date_published'] == date_published


def test_collections(record_jats):
    """Test extracting collections."""
    collections = ["HEP", "ConferencePaper"]

    assert 'collections' in record_jats
    for coll in collections:
        assert {"primary": coll} in record_jats['collections']


def test_language(record_jats):
    """Test extracting language."""
    assert 'language' not in record_jats


def test_page_nr(record_jats):
    """Test page numbers."""
    assert 'page_nr' in record_jats
    assert record_jats['page_nr'][0] == "3"


def test_doi(record_jats):
    """Test DOI."""
    doi = "10.1051/epjconf/201510001001"
    assert 'dois' in record_jats
    assert record_jats['dois'][0]['value'] == doi


def test_publication_info(record_jats):
    """Test extracting publication info."""
    assert 'journal_title' in record_jats
    assert record_jats['journal_title'] == "EPJ Web of Conferences"
    assert 'journal_year' in record_jats
    assert record_jats['journal_year'] == 2015
    assert 'journal_artid' in record_jats
    assert record_jats['journal_artid'] == "01001"
    assert 'journal_volume' in record_jats
    assert record_jats['journal_volume'] == "100"
    assert 'journal_fpage' in record_jats
    assert record_jats['journal_fpage'] == "1"
    assert 'journal_lpage' in record_jats
    assert record_jats['journal_lpage'] == "3"
    assert 'journal_issue' in record_jats
    assert record_jats['journal_issue'] == "1"


def test_keywords(record_jats):
    """Test free keywords."""
    keywords = ["nuclear", "physics"]

    assert 'free_keywords' in record_jats
    for keyw in record_jats["free_keywords"]:
        assert keyw["value"] in keywords


def test_authors(record_jats):
    """Test authors."""
    authors = ["Arasoglu, Ali", "Ozdemir, Omer Faruk"]
    surnames = ["Arasoglu", "Ozdemir"]
    affiliations = [u"Y\xfcz\xfcnc\xfc Yil University, Science Faculty, Physics Department"]

    assert 'authors' in record_jats
    astr = record_jats['authors']
    assert len(astr) == len(authors)
    # here we are making sure order is kept
    for index in range(len(authors)):
        assert astr[index]['full_name'] == authors[index]
        assert astr[index]['surname'] == surnames[index]
        if index < 3:
            assert astr[index]['affiliations'][0]['value'] == affiliations[0]
        else:
            assert astr[index]['affiliations'][0]['value'] == affiliations[1]


def test_license(record_jats):
    """Test OA-license."""
    expected_license = [{
        'license': None,
        'material': None,
        'url': 'http://creativecommons.org/licenses/by/4.0/',
    }]

    assert record_jats['license'] == expected_license


def test_copyrights(record_jats):
    """Test various copyright items."""
    copyright_holder = "Owned by the authors, published by EDP Sciences"
    copyright_material = "Article"
    copyright_statement = u"\xa9 Owned by the authors, published by EDP Sciences, 2015"
    copyright_year = "2015"

    assert 'copyright_holder' in record_jats
    assert record_jats['copyright_holder'] == copyright_holder
    assert 'copyright_material' in record_jats
    assert record_jats['copyright_material'] == copyright_material
    assert 'copyright_statement' in record_jats
    assert record_jats['copyright_statement'] == copyright_statement
    assert 'copyright_year' in record_jats
    assert record_jats['copyright_year'] == copyright_year


def test_title_rich(record_rich):
    """Test extracting title."""
    title = "A representative sample of Be stars"
    subtitle = "II. $K$ band spectroscopy"

    assert 'title' in record_rich
    assert 'subtitle' in record_rich
    assert record_rich['title'] == title
    assert record_rich['subtitle'] == subtitle


def test_date_published_rich(record_rich):
    """Test extracting date_published."""
    date_published = "2000-01"

    assert 'date_published' in record_rich
    assert record_rich['date_published'] == date_published


def test_collections_rich(record_rich):
    """Test extracting collections."""
    collections = ["HEP", "Published"]

    assert 'collections' in record_rich
    for coll in collections:
        assert {"primary": coll} in record_rich['collections']


def test_language_rich(record_rich):
    """Test extracting language."""
    assert 'language' not in record_rich


def test_pages_rich(record_rich):
    """Test page extraction."""
    assert record_rich["page_nr"][0] == "13"
    assert record_rich["journal_fpage"] == "65"
    assert record_rich["journal_lpage"] == "77"


def test_publication_info_rich(record_rich):
    """Test extracting dois."""
    journal_title = "Astronomy and Astrophysics Supplement Series"
    journal_year = 2000
    journal_volume = "141"

    assert 'journal_title' in record_rich
    assert record_rich['journal_title'] == journal_title
    assert 'journal_year' in record_rich
    assert record_rich['journal_year'] == journal_year
    assert 'journal_volume' in record_rich
    assert record_rich['journal_volume'] == journal_volume


def test_authors_rich(record_rich):
    """Test authors."""
    authors = ["Clark, J.S.", "Steele, I.A."]
    surnames = ["Clark", "Steele"]
    affiliations = [
        "Astronomy Centre, CPES, University of Sussex, Brighton, BN1 9QH, UK",
        "Astrophysics Research Institute, Liverpool John Moores University, Liverpool, L41 1LD, UK"
    ]

    assert 'authors' in record_rich
    astr = record_rich['authors']
    assert len(astr) == len(authors)
    # here we are making sure order is kept
    for index in range(len(authors)):
        assert astr[index]['full_name'] == authors[index]
        assert astr[index]['surname'] == surnames[index]
        assert astr[index]["affiliations"][0]["value"] == affiliations[index]


def test_tarfile(tarbzfile, tmpdir):
    """Test untarring a tar.bz package with a test XML file.

    Also test directory structure flattening.
    """
    spider = edp_spider.EDPSpider()
    xml_files = spider.untar_files(tarbzfile, six.text_type(tmpdir))
    xml_files_flat = spider.untar_files(
        tarbzfile, six.text_type(tmpdir), flatten=True)

    assert len(xml_files) == 1
    assert "aas/xml_rich/2000/01/ds1691.xml" in xml_files[0]
    assert "ds1691.xml" in xml_files_flat[0]
    assert "aas/xml_rich/2000/01" not in xml_files_flat[0]


def test_handle_package_ftp(tarbzfile):
    """Test getting the target folder name for xml files."""
    spider = edp_spider.EDPSpider()
    response = fake_response_from_string(text=tarbzfile)
    request = spider.handle_package_ftp(response).next()

    assert isinstance(request, Request)
    assert request.meta["source_folder"] == tarbzfile


def test_no_dois_jats():
    """Test parsing when no DOI in record. JATS format."""
    spider = edp_spider.EDPSpider()
    body = """
    <article xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" article-type="research-article" xml:lang="en" dtd-version="3.0">
        <front>
            <article-meta>
            <article-id pub-id-type="publisher-id">aa14485-10</article-id><article-id pub-id-type="other">2010A%26A...516A..97N</article-id>
                <title-group>
                    <article-title xml:lang="en">Dielectronic recombination of argon-like ions</article-title>
                </title-group>
            </article-meta>
        </front>
    </article>
    """
    response = fake_response_from_string(body)
    node = get_node(spider, "//article", response)[0]

    parsed_item = spider.parse_node(response, node)
    assert parsed_item
    assert parsed_item.record
    record = parsed_item.record

    assert "dois" not in record
    assert isinstance(record, HEPRecord)


def test_no_dois_rich():
    """Test parsing when no DOI in record. 'Rich' format."""
    spider = edp_spider.EDPSpider()
    body = """
    <EDPSArticle>
        <ArticleID Type="Article">
            <EDPSRef>ds1691</EDPSRef>
        </ArticleID>
    </EDPSArticle>
    """
    response = fake_response_from_string(body)
    response.meta["rich"] = True
    node = get_node(spider, "//EDPSArticle", response)[0]

    parsed_item = spider.parse_node(response, node)
    assert parsed_item
    assert parsed_item.record
    record = parsed_item.record

    assert "dois" not in record
    assert isinstance(record, HEPRecord)


def test_addendum_jats():
    """Test parsing when article type is addendum. JATS format."""
    spider = edp_spider.EDPSpider()
    body = """
    <article xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" article-type="addendum" xml:lang="en" dtd-version="3.0">
        <front>
            <article-meta>
            <article-id pub-id-type="publisher-id">aa14485-10</article-id><article-id pub-id-type="other">2010A%26A...516A..97N</article-id>
                <title-group>
                    <article-title xml:lang="en">Dielectronic recombination of argon-like ions</article-title>
                </title-group>
                <related-article ext-link-type="doi" href="10.1051/0004-6361/201014485">
                </related-article>
            </article-meta>
        </front>
    </article>
    """
    response = fake_response_from_string(body)
    node = get_node(spider, "//article", response)[0]

    parsed_item = spider.parse_node(response, node)
    assert parsed_item
    assert parsed_item.record
    record = parsed_item.record

    assert "related_article_doi" in record
    assert record["related_article_doi"][0][
        "value"] == "10.1051/0004-6361/201014485"


def test_author_with_email():
    """Test getting author email. JATS format."""
    spider = edp_spider.EDPSpider()
    body = """
    <article xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" article-type="addendum" xml:lang="en" dtd-version="3.0">
        <front>
            <article-meta>
            <contrib-group content-type="authors">
            <contrib contrib-type="author" corresp="yes"><name><surname>Sname</surname><given-names>Fname</given-names></name><email>Fname.Sname@university.org</email><xref ref-type="aff" rid="AFF1"/><xref ref-type="corresp" rid="FN1">a</xref></contrib>
            </contrib-group>
            </article-meta>
        </front>
    </article>
    """
    response = fake_response_from_string(body)
    node = get_node(spider, "//article", response)[0]

    parsed_item = spider.parse_node(response, node)
    assert parsed_item
    assert parsed_item.record
    record = parsed_item.record

    assert 'email' in record['authors'][0]
    assert record['authors'][0]['email'] == "Fname.Sname@university.org"


def test_aff_with_email():
    """Test popping email from the affiliation string. JATS format."""
    spider = edp_spider.EDPSpider()
    body = """
    <article xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" article-type="research-article" xml:lang="en" dtd-version="3.0">
        <front>
            <article-meta>
            <contrib-group>
                <contrib contrib-type="author">
                    <name>
                        <surname>Gorczyca</surname>
                        <given-names>T. W.</given-names>
                    </name>
                    <xref ref-type="aff" rid="AFF1">1</xref>
                </contrib>
                <aff id="AFF1">
                    <label>1</label>
                    <addr-line>Department of Physics, Western Michigan University, Kalamazoo, MI 49008, USA e-mail: gorczyca@wmich.edu
                    </addr-line>
                </aff>
            <contrib-group>
            </article-meta>
        </front>
    </article>
    """
    response = fake_response_from_string(body)
    node = get_node(spider, "//article", response)[0]

    parsed_item = spider.parse_node(response, node)
    assert parsed_item
    assert parsed_item.record
    record = parsed_item.record

    affiliation = "Department of Physics, Western Michigan University, Kalamazoo, MI 49008, USA"
    assert 'affiliations' in record['authors'][0]
    assert record['authors'][0]['affiliations'][0]['value'] == affiliation
    assert "e-mail" not in record['authors'][0]['affiliations'][0]['value']
    assert record['authors'][0]['email'] is None


def test_no_valid_article():
    """Test parsing when filtering out non-interesting article types."""
    spider = edp_spider.EDPSpider()
    body = """
    <article xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" article-type="lecture" xml:lang="en" dtd-version="3.0">
    </article>
    """
    response = fake_response_from_string(body)
    node = get_node(spider, "//article", response)[0]
    record = spider.parse_node(response, node)

    assert record is None


def test_collections_review():
    """Test collections when doctype is review. JATS format."""
    spider = edp_spider.EDPSpider()
    body = """
    <article xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" article-type="review-article" xml:lang="en" dtd-version="3.0">
    </article>
    """
    response = fake_response_from_string(body)
    node = get_node(spider, "//article", response)[0]

    parsed_item = spider.parse_node(response, node)
    assert parsed_item
    assert parsed_item.record
    record = parsed_item.record

    assert "collections" in record
    assert record["collections"] == [{'primary': 'HEP'}, {'primary': 'Review'}]


@pytest.fixture
def record_references_only():
    """Parse references."""
    spider = edp_spider.EDPSpider()
    body = """
    <article xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" article-type="research-article" xml:lang="en" dtd-version="3.0">
        <back>
        <ref-list>
        <title>References</title>
            <ref id="R5"><label>5.</label><mixed-citation publication-type="journal" id="a"><string-name><given-names>R.V.</given-names> <surname>Krishnan</surname></string-name>, <string-name><given-names>G.</given-names> <surname>Panneerselvam</surname></string-name>, <string-name><given-names>P.</given-names> <surname>Manikandan</surname></string-name> <string-name><given-names>M.P.</given-names> <surname>Antony</surname></string-name>, <string-name><given-names>K.</given-names> <surname>Nagarajan</surname></string-name>, <source>J. Nucl. Radiochem. Sci.</source>, <volume>10</volume>.<issue>1</issue>, <fpage>19</fpage>–<lpage>26</lpage> (<year>2009</year>).</mixed-citation></ref>

            <ref id="R44"><label>44.</label><mixed-citation publication-type="journal"><string-name><given-names>L.</given-names> <surname>Cronin</surname></string-name>, <string-name><given-names>P.</given-names> <surname>Sojka</surname></string-name>, <string-name><given-names>A.</given-names> <surname>Lefebvre</surname></string-name>, <source>SAE Technical Paper</source>, DOI: <ext-link ext-link-type="uri" xlink:href="http://dx.doi.org/10.4271/852086">10.4271/852086</ext-link>, (<year>1985</year>)</mixed-citation></ref>

            <ref id="R3"><label>3.</label><mixed-citation publication-type="book"><string-name><given-names>T.</given-names> <surname>Aliyev</surname></string-name>, <string-name><given-names>Т.</given-names> <surname>Belyaev</surname></string-name>, <string-name><given-names>S.</given-names> <surname>Gallagher</surname></string-name> <article-title>Simulation in ANSYS flow to the gas purification section of the multicomponent gas mixture through the dust cyclone CKBN GP-628</article-title>. <source>Mechanical engineering</source>, <publisher-loc>Moscow</publisher-loc>, №<issue>10</issue>, (<year>2014</year>).</mixed-citation></ref>

        </ref-list>
        </back>
    </article>
    """
    response = fake_response_from_string(body)
    node = get_node(spider, "//article", response)[0]

    parsed_item = spider.parse_node(response, node)
    assert parsed_item
    assert parsed_item.record

    return parsed_item.record


def test_references(record_references_only):
    """Test references."""
    reference = {
        'authors': [u'Krishnan, R.V.',
                             u'Panneerselvam, G.',
                             u'Manikandan, P.',
                             u'Antony, M.P.',
                             u'Nagarajan, K.'],
        'doctype': u'journal',
        'fpage': u'19',
        'issue': u'1',
        'journal_title': u'J. Nucl. Radiochem. Sci.',
        'journal_volume': u'10',
        'number': u'5a',
        'raw_reference': u'<mixed-citation publication-type="journal" id="a"><string-name><given-names>R.V.</given-names> <surname>Krishnan</surname></string-name>, <string-name><given-names>G.</given-names> <surname>Panneerselvam</surname></string-name>, <string-name><given-names>P.</given-names> <surname>Manikandan</surname></string-name> <string-name><given-names>M.P.</given-names> <surname>Antony</surname></string-name>, <string-name><given-names>K.</given-names> <surname>Nagarajan</surname></string-name>, <source>J. Nucl. Radiochem. Sci.</source>, <volume>10</volume>.<issue>1</issue>, <fpage>19</fpage>\u2013<lpage>26</lpage> (<year>2009</year>).</mixed-citation>',
        'year': u'2009'
    }

    assert "references" in record_references_only
    assert record_references_only["references"][0] == reference


def test_reference_doi(record_references_only):
    """Test reference DOI extraction."""
    assert "references" in record_references_only
    assert "doi" in record_references_only["references"][1]
    assert record_references_only["references"][1]["doi"] == "doi:10.4271/852086"


def test_reference_title(record_references_only):
    """Test reference with a title."""
    title = "Simulation in ANSYS flow to the gas purification section of the multicomponent gas mixture through the dust cyclone CKBN GP-628"
    assert "references" in record_references_only
    assert "title" in record_references_only["references"][2]
    assert record_references_only["references"][2]["title"] == title
