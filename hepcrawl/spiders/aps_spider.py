# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for APS."""

from __future__ import absolute_import, print_function

import json
import link_header

from furl import furl

from scrapy import Request, Spider
from inspire_schemas.api import validate as validate_schema

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import (
    add_items_to_references,
    format_arxiv_id,
    get_journal_and_section,
    get_license,
    get_nested,
    build_dict,
)


class APSSpider(Spider):
    """APS crawler.

    Uses the APS REST API v2. See documentation here:
    http://harvest.aps.org/docs/harvest-api#endpoints

    Example usage:
    .. code-block:: console

        scrapy crawl APS -a 'from_date=2016-05-01' -a 'until_date=2016-05-15' -a 'sets=openaccess'
        scrapy crawl APS -a json_file=file://`pwd`/tests/responses/aps/aps_single_response.json

    """
    name = "APS"
    aps_base_url = "http://harvest.aps.org/v2/journals/articles"
    download_delay = 10
    custom_settings = {'MAX_CONCURRENT_REQUESTS_PER_DOMAIN': 2}

    def __init__(self, json_file=None, url=None, from_date=None, until_date=None,
                 date="published", journals=None, sets=None, per_page=100,
                 **kwargs):
        """Construct APS spider.

        Choose either `json_file` or `url` or mixture of other parameters.

        :param json_file: path to local record in JSON format
        :param url: url for querying the API, can also be constructed
        :param from_date: begin date of records in query
        :param until_date: end date of records in query
        :param date: you can choose modification or publication date
        :param journals: specify journals
        :param sets: specify OAI sets
        :param per_page: number of records per results page (max 100)
        """
        super(APSSpider, self).__init__(**kwargs)
        if url is None:
            # We Construct.
            params = {}
            if from_date:
                params['from'] = from_date
            if until_date:
                params['until'] = until_date
            if date:
                params['date'] = date
            if journals:
                params['journals'] = journals
            if per_page:
                params['per_page'] = per_page
            if sets:
                params['set'] = sets

            # Put it together: furl is awesome
            url = furl(APSSpider.aps_base_url).add(params).url
        self.url = url
        self.json_file = json_file

    def start_requests(self):
        """Just yield the url."""
        if self.json_file:
            yield Request(
                self.json_file,
                meta={'json_path': self.json_file},
            )
        else:
            yield Request(self.url)

    def parse(self, response):
        """
        Go through all the (JSON) records available and yield requests for
        scraping the corresponding XML record for references.
        """
        aps_response = json.loads(response.body_as_unicode())
        for article in aps_response['data']:
            doi = article['identifiers']['doi']
            link = "http://harvest.aps.org/v2/journals/articles/" + doi
            request = Request(
                link,
                headers={'Accept': 'text/xml'},
                callback=self.scrape_xml_for_ref
            )
            request.meta['article'] = article
            yield request

        # Pagination support. Will yield until no more "next" pages are found
        if 'Link' in response.headers:
            links = link_header.parse(response.headers['Link'])
            next_link = links.links_by_attr_pairs([('rel', 'next')])
            if next_link:
                next_url = next_link[0].href
                yield Request(next_url)

    def _parse_reference(self, ref, label):
        """Parse a reference."""
        # See harvestingkit for how this is done at the moment:
        # https://github.com/inspirehep/harvesting-kit/blob/master/harvestingkit/aps_package.py
        reference = {}

        sublabel = ref.xpath('./object-id/text()').extract_first()
        ref_type = ref.xpath('./@publication-type').extract_first()
        report_no = ref.xpath(
            './/pub-id[@pub-id-type="other"]/text()'
        ).extract_first()
        if not report_no:
            report_no = ref.xpath(
                './/pub-id[@pub-id-type="other"]/following-sibling::text()[1]'
            ).extract_first()
        doi = ref.xpath('.//pub-id[@pub-id-type="doi"]/text()').extract_first()
        institution = ref.xpath(".//institution/text()").extract_first()
        collaboration = ref.xpath(".//collab/text()").extract_first()

        # FIXME: do we want authors be a string or a list of raw author names?
        # In Elsevier it's a specially formatted string.
        # Here it's just a list.
        authors = []
        author_groups = ref.xpath(
            './/person-group[@person-group-type="author"]')
        for author_group in author_groups:
            authors.extend(author_group.xpath(
                './/string-name/text()').extract())
        editors = []
        editor_groups = ref.xpath(
            './/person-group[@person-group-type="editor"]')
        for editor_group in editor_groups:
            editors.extend(editor_group.xpath(
                './/string-name/text()').extract())

        title = ref.xpath(".//article-title/text()").extract_first()
        publication = ref.xpath(".//source/text()").extract_first()
        fpage = ref.xpath(".//page-range/text()").extract_first()
        issue = ref.xpath(".//issue/text()").extract_first()
        volume = ref.xpath(".//volume/text()").extract_first()
        year = ref.xpath(".//year/text()").extract_first()
        urls = ref.xpath(".//ext-link/text()").extract()
        arxiv_raw = ref.xpath(
            './/pub-id[@pub-id-type="arxiv"]/text()').extract()
        arxiv_id = format_arxiv_id(arxiv_raw)
        publisher = ref.xpath('.//publisher-name/text()').extract_first()
        publisher_loc = ref.xpath(
            './/publisher-loc/text()').extract_first()
        if not publisher_loc:
            publisher_loc = ref.xpath(
                './/publisher-name/following-sibling::text()[1]'
            ).extract_first()
        if publisher_loc:
            publisher = publisher_loc.strip(",. ") + ': ' + publisher
        issn = ref.xpath('.//issn/text()').extract_first()
        raw_reference = ref.extract()

        # Construct the reference dict
        reference = add_items_to_references(
            doctype=ref_type,
            arxiv_id=arxiv_id,
            doi="doi:{}".format(doi) if doi else None,
            fpage=fpage,
            title=title,
            issue=issue,
            year=year,
            authors=authors,
            editors=editors,
            collaboration=collaboration,
            publisher=publisher,
            issn=issn,
            report_no=report_no.rstrip(',. (') if report_no else None,
            raw_reference=raw_reference,
            misc=institution,
            number=sublabel if sublabel else label,
            url=urls if urls and "arxiv" not in urls[0].lower() else None
        )

        # Some items require special handling:
        if publication:
            journal_title, section = get_journal_and_section(publication)
            if journal_title:
                reference['journal_title'] = journal_title
                if volume:
                    volume = section + volume
                    reference['journal_volume'] = volume

        return reference

    def _parse_license(self, node):
        """Extract license information."""
        license_raw = node.xpath(
            './/license-p[@content-type="usage-statement"]')
        license_url = license_raw.xpath('.//uri/@*').extract_first()
        license_text = license_raw.xpath('.//uri/text()').extract_first()

        return license_text, license_url

    def scrape_xml_for_ref(self, response):
        """Get references, license and keywords from JATS format XML file."""
        node = response.selector
        ref_list = node.xpath('//ref-list//ref')
        references = []
        label = ''
        for reference in ref_list:
            label = reference.xpath('./label/text()').extract_first()
            label = label.strip('[]')
            inner_refs = reference.xpath('.//mixed-citation')
            if not inner_refs:
                references.append(self._parse_reference(reference, label))
            for in_ref in inner_refs:
                references.append(self._parse_reference(in_ref, label))

        response.meta['keywords'] = node.xpath('.//kwd/text()').extract()
        response.meta['license'] = self._parse_license(node)
        response.meta['references'] = references

        return self.build_item(response)

    def build_item(self, response):
        """Parse a APS JSON file into a HEP record."""
        article = response.meta['article']
        record = HEPLoader(item=HEPRecord(), response=response)

        record.add_value('dois', get_nested(article, 'identifiers', 'doi'))
        record.add_value('page_nr', str(article.get('numPages', '')))
        record.add_value('abstract', get_nested(article, 'abstract', 'value'))
        record.add_value('title', get_nested(article, 'title', 'value'))

        authors, collaborations = self._get_authors_and_collab(article)
        record.add_value('authors', authors)
        record.add_value('collaborations', collaborations)
        record.add_value('journal_title', get_nested(
            article, 'journal', 'abbreviatedName'))
        record.add_value('journal_issue', get_nested(
            article, 'issue', 'number'))
        record.add_value('journal_volume', get_nested(
            article, 'volume', 'number'))

        published_date = article.get('date', '')
        record.add_value('journal_year', int(published_date[:4]))
        record.add_value('date_published', published_date)
        record.add_value('field_categories', [
            {
                'term': term.get('label'),
                'scheme': 'APS',
                'source': 'aps',
            } for term in get_nested(
                article,
                'classificationSchemes',
                'subjectAreas'
            )
        ])
        record.add_value('copyright_holder', get_nested(
            article, 'rights', 'copyrightHolders')[0]['name'])
        record.add_value('copyright_year', str(
            get_nested(article, 'rights', 'copyrightYear')))
        record.add_value('copyright_statement', get_nested(
            article, 'rights', 'rightsStatement'))
        record.add_value('copyright_material', 'Article')

        license_text, license_url = response.meta.get('license')
        if license_text:
            license = get_license(
                license_text=license_text
            )
        else:
            license = get_license(
                license_url=license_url
            )
        if license:
            record.add_value('license', license)

        record.add_value('free_keywords', response.meta.get('keywords'))
        record.add_value('collections', ['HEP', 'Citeable', 'Published'])
        record.add_value('references', response.meta.get('references'))

        parsed_record = record.load_item()
        validate_schema(data=dict(parsed_record), schema_name='hep')

        yield parsed_record

    def _get_authors_and_collab(self, article):
        authors = []
        collaboration = []

        for author in article['authors']:
            if author['type'] == 'Person':
                author_affiliations = []
                if 'affiliations' in article and 'affiliationIds' in author:
                    affiliations = build_dict(article['affiliations'], 'id')
                    for aff_id in author['affiliationIds']:
                        author_affiliations.append({
                            'value': affiliations[aff_id]['name']
                        })

                authors.append({
                    'surname': author.get('surname', ''),
                    'given_names': author.get('firstname', ''),
                    'raw_name': author.get('name', ''),
                    'affiliations': author_affiliations
                })

            elif author['type'] == 'Collaboration':
                collaboration.append(author['name'])

        return authors, collaboration
