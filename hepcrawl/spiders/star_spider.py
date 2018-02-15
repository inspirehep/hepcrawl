# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for STAR."""

from __future__ import absolute_import, print_function

from scrapy import Request
from scrapy.spiders import XMLFeedSpider
from inspire_schemas.api import validate as validate_schema

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_license, get_mime_type, get_node


class STARSpider(XMLFeedSpider):

    """STAR crawler

    STAR collection: http://www.abes.fr/Theses/Les-applications/STAR
    STAR OAI: http://staroai.theses.fr/OAIHandler?verb=Identify
    Web interface: http://www.theses.fr/

    Scrapes STAR XML files one at a time, the file can contain multiple records.
    This spider harvests only theses.

    NOTE: The actual files should be retrieved from STAR via its OAI interface.

    sets to use: dcc:530 (and ddc:520)
    metadata format: tef (oai_dc is also an option)

    Example OAI url:
    http://staroai.theses.fr/OAIHandler?verb=ListRecords&metadataPrefix=tef&from=2015-12-08&until=2016-01-10&set=ddc:530


    1. The XML will be parsed and the final HEPRecord built in `parse_node`.

    Example usage:
    .. code-block:: console

        scrapy crawl STAR -a source_file=file://`pwd`/tests/responses/star/test_1.xml

    Happy crawling!
    """

    name = 'STAR'
    start_urls = []
    iterator = 'xml'
    itertag = '//OAI-PMH:record'
    download_delay = 10
    custom_settings = {'MAX_CONCURRENT_REQUESTS_PER_DOMAIN': 2}
    namespaces = [
        ('OAI-PMH', 'http://www.openarchives.org/OAI/2.0/'),
        ('mets', 'http://www.loc.gov/METS/'),
        ('metsRights', 'http://cosimo.stanford.edu/sdr/metsrights/'),
        ('xsi', 'http://www.w3.org/2001/XMLSchema-instance'),
        ('dc', 'http://purl.org/dc/elements/1.1/'),
        ('suj', 'http://www.theses.fr/namespace/sujets'),
        ('dcterms', 'http://purl.org/dc/terms/'),
        ('tef', 'http://www.abes.fr/abes/documents/tef'),
    ]

    def __init__(self, source_file=None, *args, **kwargs):
        """Construct STAR spider."""
        super(STARSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file

    def start_requests(self):
        """Default starting point for scraping shall be the local XML file."""
        yield Request(self.source_file)

    def get_authors(self, node):
        """Gets the authors."""
        authors_raw = node.xpath('.//tef:auteur')
        authors = []
        affiliations = node.xpath(
            './/tef:ecoleDoctorale/tef:nom/text()'
        ).extract()
        for author in authors_raw:
            authors.append({
                'surname': author.xpath('.//tef:nom/text()').extract_first(),
                'given_names': author.xpath(
                    './/tef:prenom/text()'
                ).extract_first(),
                'affiliations': [{'value': aff} for aff in affiliations]
            })

        return authors

    @staticmethod
    def get_thesis_supervisors(node):
        """Create a structured supervisor dictionary."""
        supervisors_raw = node.xpath('.//tef:directeurThese')
        supervisors = []
        for supervisor in supervisors_raw:
            supervisors.append({
                'surname': supervisor.xpath('./tef:nom/text()').extract_first(),
                'given_names': supervisor.xpath(
                    './tef:prenom/text()'
                ).extract_first(),
            })

        return supervisors

    def get_thesis_info(self, node):
        """Create thesis info dictionary."""
        date = node.xpath('.//dcterms:dateAccepted/text()').extract_first()
        institutions = node.xpath(
            './/tef:thesis.degree.grantor/tef:nom/text()'
        ).extract()

        thesis = {'degree_type': 'PhD'}
        if date:
            thesis['date'] = date
        if institutions:
            thesis['institutions'] = [{'name': inst} for inst in institutions]

        return thesis

    def get_links(self, node):
        """Get splash page and pdf links."""
        report_number = node.xpath(
            './/dc:identifier[@xsi:type="tef:NNT"]/text()').extract_first()
        if not report_number:
            return [], []

        splash_links = ['http://www.theses.fr/{}'.format(report_number)]
        pdf_links = ['http://www.theses.fr/{}/abes'.format(report_number)]

        if 'pdf' in get_mime_type(pdf_links[0]):
            # There might be a direct link to a pdf or a splash page
            return splash_links, pdf_links
        else:
            # Add link to original repo.
            # These links seem to lead to Montpellier repository, they are
            # using some javascript to generate the page, so getting the
            # pdf link from there is not straightforward.
            # TODO: fulltext scraping from Montpellier splash page
            splash_links.append(splash_links[0] + '/document')
            return splash_links, []

    def get_titles(self, node, language):
        """Get titles and title translations."""
        title = node.xpath(
            './/dc:title[@xml:lang="fr"]/text()').extract_first()
        title_trans = node.xpath(
            './/dcterms:alternative[@xml:lang="en"]/text()').extract_first()
        if 'fr' not in language.lower():
            title, title_trans = title_trans, title

        return title, title_trans

    def create_fft_dicts(self, pdf_urls, file_access, file_type):
        """Create structured dictionaries to add to 'additional_files' item."""
        pdf_file_dicts = []
        for file_path in pdf_urls:
            pdf_file_dicts.append({
                'access': file_access,
                'description': 'ABES',
                'url': file_path,
                'type': file_type,
            })

        return pdf_file_dicts

    def create_reportnr_dicts(self, node):
        """Create structured dictionaries to add to 'report_numbers' item."""
        report_numbers_raw = node.xpath(
            './/dc:identifier[@xsi:type="tef:NNT"]/text()')
        report_nos = []
        for rep_nr in report_numbers_raw:
            report_nos.append({
                'value': rep_nr.extract(),
                'source': 'ABES',
            })

        return report_nos

    def get_keywords(self, node):
        """Get keywords."""
        keywords = node.xpath('.//dc:subject[@xml:lang="en"]/text()').extract()
        if not keywords:
            keywords = node.xpath('.//dc:subject/text()').extract()

        return keywords

    def get_abstract(self, node):
        """Get the abstract."""
        abstract = node.xpath(
            './/dcterms:abstract[@xml:lang="en"]/text()').extract_first()
        if not abstract:
            abstract = node.xpath('.//dcterms:abstract/text()').extract_first()

        return abstract

    def parse_node(self, response, node):
        """Iterate through all the records and build HEPRecords."""
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        language = node.xpath('.//dc:language/text()').extract_first()
        title, title_trans = self.get_titles(node, language)

        record.add_value('title', title)
        # FIXME: Trans title item is in another PR
        # record.add_value('title_translation', title_trans)
        record.add_value('authors', self.get_authors(node))
        record.add_value('abstract', self.get_abstract(node))

        record.add_xpath('date_published', './/dcterms:dateAccepted /text()')
        record.add_value('thesis_supervisor',
                         self.get_thesis_supervisors(node))
        record.add_value('language', language)
        # FIXME: 'free_keywords' item is changed to 'keywords' in another PR
        keywords = self.get_keywords(node)
        record.add_value('free_keywords', keywords)

        splash_links, pdf_links = self.get_links(node)
        embargo = node.xpath(
            './/metsRights:ConstraintDescription/text()'
        ).extract_first()

        if splash_links:
            record.add_value('urls', splash_links)
        if pdf_links:
            record.add_value(
                'additional_files',
                self.create_fft_dicts(pdf_links, 'INSPIRE-PUBLIC', 'Fulltext')
            )
        # FIXME: how do we want to preserve the information about fulltext embargo?
        # license = get_license(
            # license_url=node.xpath('.//tei:licence/@target').extract_first()
        # )
        # record.add_value('license', license)
        # FIXME: What is the license? Apparently they are using something like:
        # https://www.etalab.gouv.fr/licence-ouverte-open-licence

        record.add_value('report_numbers', self.create_reportnr_dicts(node))
        record.add_value('thesis', self.get_thesis_info(node))
        record.add_value('collections', ['HEP', 'THESIS'])
        record.add_value('source', 'ABES')

        parsed_record = record.load_item()
        validate_schema(data=dict(parsed_record), schema_name='hep')
        return parsed_record
