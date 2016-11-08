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

import shutil
import six

import pkg_resources
import pytest

from scrapy.http import HtmlResponse

from hepcrawl.spiders import iop_spider

from .responses import (
    fake_response_from_file,
    fake_response_from_string,
    get_node,
)

TEST_DIR = os.path.dirname(os.path.realpath(__file__))
TEST_TMP_DIR = os.path.join(TEST_DIR, "responses/iop/test_tmp/")
# Remove the test output directory if it exists:
if os.path.exists(TEST_TMP_DIR):
    shutil.rmtree(TEST_TMP_DIR)
os.makedirs(TEST_TMP_DIR)


@pytest.fixture
def scrape_iop_test_metadata():
    """Splash page path for JATS file."""
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'iop',
            'xml',
            'test_standard.xml'
        )
    )


@pytest.fixture
def record(scrape_iop_test_metadata):
    """Mock the STACKS scraping and build the final record.

    Here we are specifying the ISSN and issue.
    """
    stacks_url = os.path.join(
        TEST_DIR, "responses/iop/stacks_pages/retrieve_xml.html"
    )
    stacks_pdf_url = os.path.join(
        TEST_DIR, "responses/iop/stacks_pages/local_loading_pdf.html"
    )

    spider = iop_spider.IOPSpider()
    response = fake_response_from_file('iop/stacks_pages/retrieve_xml.html')
    spider.http_netrc = "tests/responses/iop/test_netrc"
    spider.stacks_url = "file://" + stacks_url
    spider.stacks_pdf_url = "file://" + stacks_pdf_url
    spider.local_store = "tests/responses/iop/test_tmp"
    spider.journal_issn = "1943-7722"
    spider.issue = "143/3"
    spider.ISSNS = ["1943-7722"]
    # Fake the ISSNS list because we don't have rights for the journal the
    # test metadata is from (it's from the public IOP web site). We should
    # probably not use our metadata for testing, as IOP is quite sensitive on
    # these things.

    request = spider.scrape_for_available_issues(response).next()
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=scrape_iop_test_metadata
    )

    node = get_node(spider, "Article", response)
    record = spider.parse_node(response, node)

    return record


def test_scrape_all_available():
    """Mock the STACKS scraping.

    Here we try taking all the available issues (two issues).
    """
    stacks_url = os.path.join(
        TEST_DIR, "responses/iop/stacks_pages/retrieve_xml_less.html"
    )
    stacks_pdf_url = os.path.join(
        TEST_DIR, "responses/iop/stacks_pages/local_loading_pdf.html"
    )

    spider = iop_spider.IOPSpider()
    response = fake_response_from_file(
        'iop/stacks_pages/retrieve_xml_less.html')
    spider.http_netrc = "tests/responses/iop/test_netrc"
    spider.stacks_url = "file://" + stacks_url
    spider.stacks_pdf_url = "file://" + stacks_pdf_url
    spider.local_store = "tests/responses/iop/test_tmp"

    requests = list(spider.scrape_for_available_issues(response))

    assert len(requests) == 2
    assert requests[0].meta["issn"] == '1674-4527'
    assert requests[1].meta["issn"] == '1674-4527'
    assert requests[0].meta["volume"] == '16'
    assert requests[1].meta["volume"] == '16'
    assert requests[0].meta["issue"] == '10'
    assert requests[1].meta["issue"] == '11'


def test_abstract(record):
    """Test extracting abstract."""
    assert "abstract" in record
    assert record["abstract"].startswith("Somatic BRAF mutation")


def test_title(record):
    """Test extracting title."""
    title = (
        'A Modified Lynch Syndrome Screening Algorithm in Colon Cancer: BRAF '
        'Immunohistochemistry Is Efficacious and Cost Beneficial.'
    )

    assert "title" in record
    assert record["title"] == title


def test_date_published(record):
    """Test extracting date_published."""
    assert "date_published" in record
    assert record["date_published"] == '2015-03'


def test_page_nr(record):
    """Test extracting page_nr"""
    assert "journal_fpage" in record
    assert "journal_lpage" in record
    assert record["journal_fpage"] == '336'
    assert record["journal_lpage"] == '343'


def test_free_keywords(record):
    """Test extracting free_keywords"""
    keywords = [u'BRAF', u'MLH1',
                u'Immunohistochemistry', u'Cost-benefit analysis']

    assert "free_keywords" in record
    for keyword in record["free_keywords"]:
        assert keyword["source"] == "author"
        assert keyword["value"] in keywords


def test_dois(record):
    """Test extracting dois."""
    assert record["dois"]
    assert record["dois"][0]["value"] == '110.1309/AJCP4D7RXOBHLKGJ'


def test_collections(record):
    """Test extracting collections."""
    collections = ['HEP', 'Citeable', 'Published']

    assert record["collections"]
    for collection in record["collections"]:
        assert collection["primary"] in collections


def test_publication_info(record):
    """Test extracting dois."""
    journal_title = "Am J Clin Pathol"
    journal_year = 2015
    journal_volume = "143"
    journal_issue = "3"
    journal_issn = "1943-7722"

    assert "journal_title" in record
    assert record["journal_title"] == journal_title
    assert "journal_year" in record
    assert record["journal_year"] == journal_year
    assert "journal_volume" in record
    assert record["journal_volume"] == journal_volume
    assert "journal_issue" in record
    assert record["journal_issue"] == journal_issue
    assert "journal_issn" in record
    assert record["journal_issn"][0] == journal_issn


def test_authors_old(record):
    """Test authors."""
    authors = ['Roth, Rachel M', 'Hampel, Heather', 'Arnold, Christina A',
               'Yearsley, Martha M', 'Marsh, William L', 'Frankel, Wendy L']

    affiliations = [
        [{'value': u'Department of Pathology, The Ohio State University '
            'Wexner Medical Center, Columbus'}],
        [{'value': u'Department of Human Genetics, The Ohio State University '
            'Wexner Medical Center Columbus'}],
        [{'value': u'Department of Pathology, The Ohio State University '
            'Wexner Medical Center, Columbus'},
         {'value': u'Department of Microbiology, The Ohio State University '
             'Wexner Medical Center, Columbus'}],
        [{'value': u'Department of Pathology, The Ohio State University '
            'Wexner Medical Center, Columbus'}],
        [{'value': u'Department of Pathology, The Ohio State University '
            'Wexner Medical Center, Columbus'}],
        [{'value': u'Department of Pathology, The Ohio State University '
            'Wexner Medical Center, Columbus'},
         {'value': u'Department of Human Genetics, The Ohio State University '
             'Wexner Medical Center, Columbus'}]
    ]

    assert "authors" in record
    assert len(record["authors"]) == 6
    for index, (name, aff) in enumerate(zip(authors, affiliations)):
        assert record["authors"][index]["full_name"] == name
        assert record["authors"][index]["affiliations"] == aff


def test_copyrights(record):
    """Test extracting copyright."""
    copyright_holder = "American Society for Clinical Pathology"
    copyright_statement = "Copyright\xa9 by the American Society for \n  Clinical Pathology"

    assert "copyright_holder" in record
    assert record["copyright_holder"] == copyright_holder
    assert "copyright_statement" in record
    assert record["copyright_statement"] == copyright_statement


def test_files(record):
    """Test files dictionary."""
    test_issue_path = "1943-7722/143/3/336/test_143_3_336.pdf"

    # pytest.set_trace()
    assert "additional_files" in record
    assert record["additional_files"][0]["access"] == 'INSPIRE-HIDDEN'
    assert record["additional_files"][0]["type"] == 'Fulltext'
    assert record["additional_files"][0][
        "url"] == TEST_TMP_DIR + test_issue_path


@pytest.fixture
def erratum_open_access_record():
    """Erratum record."""
    spider = iop_spider.IOPSpider()
    body = """
    <ArticleSet>
        <Article>
            <Journal>
                <PublisherName>Institute of Physics</PublisherName>
                <JournalTitle>J. Phys.: Conf. Ser.</JournalTitle>
                <Issn>1742-6596</Issn>
                <Volume>143</Volume>
                <Issue>3</Issue>
            </Journal>
            <FirstPage LZero="save">336</FirstPage>
        <PublicationType>Published Erratum</PublicationType>
        </Article>
    </ArticleSet>
    """
    response = fake_response_from_string(body)
    node = get_node(spider, "Article", response)
    spider.pdf_files = os.path.join(TEST_DIR, "responses/iop/pdf")
    parsed_record = spider.parse_node(response, node)

    assert parsed_record
    return parsed_record


def test_files_erratum_open_access_record(erratum_open_access_record):
    """Test files dict with open access journal with erratum article."""
    test_pdf_path = "responses/iop/pdf/1742-6596/143/3/336/test_143_3_336.pdf"

    assert "additional_files" in erratum_open_access_record
    assert erratum_open_access_record["additional_files"][
        0]["access"] == 'INSPIRE-PUBLIC'
    assert erratum_open_access_record[
        "additional_files"][0]["type"] == 'Erratum'
    assert erratum_open_access_record["additional_files"][
        0]["url"] == os.path.join(TEST_DIR, test_pdf_path)


def test_not_published_record():
    """Not-published paper should result in nothing."""
    spider = iop_spider.IOPSpider()
    body = """
    <ArticleSet>
        <Article>
            <Journal>
                <PubDate PubStatus="aheadofprint">
                    <Year>2015</Year>
                    <Month>03</Month>
                </PubDate>
            </Journal>
        </Article>
    </ArticleSet>
    """
    response = fake_response_from_string(body)
    node = get_node(spider, "Article", response)
    spider.pdf_files = os.path.join(TEST_DIR, "responses/iop/test_tmp/")
    records = spider.parse_node(response, node)

    assert records is None


@pytest.fixture
def tarfile():
    """Return path to test tar.gz file."""
    return os.path.join(
        os.path.dirname(__file__),
        'responses',
        'iop',
        'packages',
        'test.tar.gz'
    )


def test_tarfile(tarfile, tmpdir):
    """Test untarring a tar.gz package with a test PDF file."""
    spider = iop_spider.IOPSpider()
    pdf_files = spider.untar_files(tarfile, six.text_type(tmpdir))

    assert len(pdf_files) == 1
    assert "test_143_3_336.pdf" in pdf_files[0]


def test_handle_pdf_package(tarfile):
    """Test getting the target folder name for pdf files."""
    spider = iop_spider.IOPSpider()
    tarfile = "file://" + tarfile
    target_folder = spider.handle_pdf_package(tarfile)

    assert target_folder


def test_get_authentication():
    spider = iop_spider.IOPSpider()
    spider.stacks_url = "stacks_url"
    spider.http_netrc = "tests/responses/iop/test_netrc"
    user, passw = spider.get_authentications()

    assert user == "user"
    assert passw == "passw"


def test_get_authentication_no_netrc():
    spider = iop_spider.IOPSpider()
    spider.stacks_url = "stacks_url"
    spider.http_netrc = "here/are/no/credentials"
    user, passw = spider.get_authentications()

    assert user == ""
    assert passw == ""


def test_getting_invalid_journal():
    """Mock the STACKS scraping with invalid ISSN."""
    spider = iop_spider.IOPSpider()
    response = fake_response_from_file('iop/stacks_pages/retrieve_xml.html')
    spider.local_store = "tests/responses/iop/test_tmp"
    spider.journal_issn = "4532-1195"
    spider.issue = "143/3"

    with pytest.raises(ValueError):
        spider.scrape_for_available_issues(response).next()


def test_getting_nonavailable_journal():
    """Mock the STACKS scraping with valid but non-available ISSN."""
    spider = iop_spider.IOPSpider()
    response = fake_response_from_file('iop/stacks_pages/retrieve_xml.html')
    spider.journal_issn = "4532-1195"
    spider.issue = "111/1"
    spider.ISSNS = ["4532-1195"]  # fake the valid issns list

    with pytest.raises(KeyError):
        spider.scrape_for_available_issues(response).next()


def test_getting_nonavailable_issue():
    """Mock the STACKS scraping with valid but non-available issue."""
    spider = iop_spider.IOPSpider()
    response = fake_response_from_file('iop/stacks_pages/retrieve_xml.html')
    spider.journal_issn = "1943-7722"
    spider.issue = "111/1"
    spider.ISSNS = ["1943-7722"]  # fake the valid issns list

    with pytest.raises(ValueError):
        spider.scrape_for_available_issues(response).next()


def test_metadata_issn_conflict(scrape_iop_test_metadata):
    """Test scraping metadata which has a wrong ISSN."""
    stacks_url = os.path.join(
        TEST_DIR, "responses/iop/stacks_pages/retrieve_xml.html")
    stacks_pdf_url = os.path.join(
        TEST_DIR, "responses/iop/stacks_pages/local_loading_pdf.html")

    spider = iop_spider.IOPSpider()
    response = fake_response_from_file('iop/stacks_pages/retrieve_xml.html')
    spider.http_netrc = "tests/responses/iop/test_netrc"
    spider.stacks_url = "file://" + stacks_url
    spider.stacks_pdf_url = "file://" + stacks_pdf_url
    spider.local_store = "tests/responses/iop/test_tmp"
    spider.journal_issn = "0264-9381"
    spider.issue = "33/1"
    spider.ISSNS = ["1943-7722", "0264-9381"]

    request = spider.scrape_for_available_issues(response).next()
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=scrape_iop_test_metadata
    )

    node = get_node(spider, "Article", response)
    record = spider.parse_node(response, node)

    assert record is None


def test_scrape_one_new_issue(monkeypatch):
    """Test scraping one new issue of an existing journal."""
    spider = iop_spider.IOPSpider()
    stacks_url = os.path.join(
        TEST_DIR, "responses/iop/stacks_pages/retrieve_xml_less.html")
    stacks_pdf_url = os.path.join(
        TEST_DIR, "responses/iop/stacks_pages/local_loading_pdf.html")

    response = fake_response_from_file(
        'iop/stacks_pages/retrieve_xml_less.html')
    spider.http_netrc = "tests/responses/iop/test_netrc"
    spider.stacks_url = "file://" + stacks_url
    spider.stacks_pdf_url = "file://" + stacks_pdf_url
    spider.local_store = "tests/responses/iop/test_tmp"

    def mock_existing_issues():
        """Fake the dictionary of available issues."""
        return {'1674-4527': ['16/10']}

    monkeypatch.setattr(spider, 'get_existing_issues', mock_existing_issues)

    requests = list(spider.scrape_for_available_issues(response))

    assert len(requests) == 1
    assert requests[0].meta["issn"] == '1674-4527'
    assert requests[0].meta["volume"] == '16'
    assert requests[0].meta["issue"] == '11'
