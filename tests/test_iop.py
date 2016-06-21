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

import six

import pytest

from hepcrawl.spiders import iop_spider

from .responses import (
    fake_response_from_file,
    fake_response_from_string,
    get_node,
)

tests_dir = os.path.dirname(os.path.realpath(__file__))
test_pdf_dir = os.path.join(tests_dir, "responses/iop/pdf/")


@pytest.fixture
def record():
    """Return results generator from the WSP spider."""
    spider = iop_spider.IOPSpider()
    response = fake_response_from_file('iop/xml/test_standard.xml')
    node = get_node(spider, "Article", response)
    spider.pdf_files = test_pdf_dir
    return spider.parse_node(response, node)


def test_abstract(record):
    """Test extracting abstract."""
    abstract = (
        "Somatic BRAF mutation in colon cancer essentially excludes Lynch "
        "syndrome. We compared BRAF V600E immunohistochemistry (IHC) with BRAF "
        "mutation in core, biopsy, and whole-section slides to determine "
        "whether IHC is similar and to assess the cost-benefit of IHC. "
        "Resection cases (2009-2013) with absent MLH1 and PMS2 and prior BRAF "
        "mutation polymerase chain reaction results were chosen (n = 57). To "
        "mimic biopsy specimens, tissue microarrays (TMAs) were constructed. In "
        "addition, available biopsies performed prior to the resection were "
        "available in 15 cases. BRAF V600E IHC was performed and graded on "
        "TMAs, available biopsy specimens, and whole-section slides. Mutation "
        "status was compared with IHC, and cost-benefit analysis was performed. "
        "BRAF V600E IHC was similar in TMAs, biopsy specimens, and whole- "
        "section slides, with only four (7%) showing discordance between IHC "
        "and mutation status. Using BRAF V600E IHC in our Lynch syndrome "
        "screening algorithm, we found a 10% cost savings compared with "
        "mutational analysis. BRAF V600E IHC was concordant between TMAs, "
        "biopsy specimens, and whole-section slides, suggesting biopsy "
        "specimens are as useful as whole sections. IHC remained cost "
        "beneficial compared with mutational analysis, even though more "
        "patients needed additional molecular testing to exclude Lynch "
        "syndrome."
    )


def test_title(record):
    """Test extracting title."""
    title = 'A Modified Lynch Syndrome Screening Algorithm in Colon Cancer: BRAF Immunohistochemistry Is Efficacious and Cost Beneficial.'
    assert "title" in record
    assert record["title"] == title


def test_date_published(record):
    """Test extracting date_published."""
    assert "date_published" in record
    assert record["date_published"] == '2015-03'


def test_page_nr(record):
    """Test extracting page_nr"""
    assert "journal_pages" in record
    assert record["journal_pages"] == '336-343'


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
    journal_year = "2015"
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


def test_authors(record):
    """Test authors."""
    authors = ['Roth, Rachel M', 'Hampel, Heather', 'Arnold, Christina A',
               'Yearsley, Martha M', 'Marsh, William L', 'Frankel, Wendy L']

    affiliations = [
        [{'value': u'Department of Pathology, The Ohio State University Wexner Medical Center, Columbus'}],
        [{'value': u'Department of Human Genetics, The Ohio State University Wexner Medical Center Columbus'}],
        [{'value': u'Department of Pathology, The Ohio State University Wexner Medical Center, Columbus'},
         {'value': u'Department of Microbiology, The Ohio State University Wexner Medical Center, Columbus'}],
        [{'value': u'Department of Pathology, The Ohio State University Wexner Medical Center, Columbus'}],
        [{'value': u'Department of Pathology, The Ohio State University Wexner Medical Center, Columbus'}],
        [{'value': u'Department of Pathology, The Ohio State University Wexner Medical Center, Columbus'},
         {'value': u'Department of Human Genetics, The Ohio State University Wexner Medical Center, Columbus'}]
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
    pdf_filename = "test_143_3_336.pdf"

    assert "additional_files" in record
    assert record["additional_files"][1]["access"] == 'INSPIRE-HIDDEN'
    assert record["additional_files"][1]["type"] == 'Fulltext'
    assert record["additional_files"][1]["url"] == test_pdf_dir + pdf_filename


@pytest.fixture
def erratum_open_access_record():
    """Return results generator from the WSP spider."""
    spider = iop_spider.IOPSpider()
    body = """
    <ArticleSet>
        <Article>
            <Journal>
                <PublisherName>Institute of Physics</PublisherName>
                <JournalTitle>J. Phys.: Conf. Ser.</JournalTitle>
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
    tests_dir = os.path.dirname(os.path.realpath(__file__))
    spider.pdf_files = os.path.join(tests_dir, "responses/iop/pdf/")
    return spider.parse_node(response, node)


def test_files_erratum_open_access_record(erratum_open_access_record):
    """Test files dict with open access journal with erratum article."""
    pdf_filename = "test_143_3_336.pdf"
    assert "additional_files" in erratum_open_access_record
    assert erratum_open_access_record["additional_files"][
        1]["access"] == 'INSPIRE-PUBLIC'
    assert erratum_open_access_record[
        "additional_files"][1]["type"] == 'Erratum'
    assert erratum_open_access_record["additional_files"][
        1]["url"] == test_pdf_dir + pdf_filename


@pytest.fixture
def not_published_record():
    """Test that scraping not-published paper will not build a HEPRecord."""
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
    tests_dir = os.path.dirname(os.path.realpath(__file__))
    spider.pdf_files = os.path.join(tests_dir, "responses/iop/pdf/")
    return spider.parse_node(response, node)


def test_not_published_record(not_published_record):
    """Not-published paper should result in nothing."""
    assert not_published_record is None


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


def test_handle_package(tarfile):
    """Test getting the target folder name for pdf files."""
    spider = iop_spider.IOPSpider()
    tarfile = "file://" + tarfile
    target_folder = spider.handle_package(tarfile)

    assert target_folder
