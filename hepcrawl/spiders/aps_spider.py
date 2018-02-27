# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for APS."""

from __future__ import absolute_import, division, print_function

import json
import link_header

from furl import furl

from scrapy import Request

from inspire_utils.record import get_value

from . import StatefulSpider
from ..items import HEPRecord
from ..loaders import HEPLoader
from ..parsers import JatsParser
from ..utils import (
    get_licenses,
    build_dict,
    ParsedItem,
    strict_kwargs,
)


class APSSpider(StatefulSpider):
    """APS crawler.

    Uses the APS REST API v2.
    `See documentation here`_.

    Example:
        Using the APS spider::

            $ scrapy crawl APS -a 'from_date=2016-05-01' -a 'until_date=2016-05-15' -a 'set=openaccess'

    .. _See documentation here:
        http://harvest.aps.org/docs/harvest-api#endpoints
    """
    name = 'APS'
    aps_base_url = "http://harvest.aps.org/v2/journals/articles"

    @strict_kwargs
    def __init__(self, url=None, from_date=None, until_date=None,
                 date="published", journals=None, sets=None, per_page=100,
                 **kwargs):
        """Construct APS spider."""
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

    def start_requests(self):
        """Just yield the url."""
        yield Request(self.url)

    def parse(self, response):
        """Parse a APS record into a HEP record.

        Attempts to parse an XML JATS full text first, if available, and falls
        back to parsing JSON if such is not available.
        """
        aps_response = json.loads(response.body_as_unicode())

        for article in aps_response['data']:
            doi = get_value(article, 'identifiers.doi', default='')

            if doi:
                request = Request(url='{}/{}'.format(self.aps_base_url, doi),
                              headers={'Accept': 'text/xml'},
                              callback=self._parse_jats,
                              errback=self._parse_json_on_failure)
                request.meta['json_article'] = article
                request.meta['original_response'] = response
                yield request

        # Pagination support. Will yield until no more "next" pages are found
        if 'Link' in response.headers:
            links = link_header.parse(response.headers['Link'])
            next = links.links_by_attr_pairs([('rel', 'next')])
            if next:
                next_url = next[0].href
                yield Request(next_url)

    def _parse_jats(self, response):
        """Parse an XML JATS response."""
        parser = JatsParser(response.selector, source=self.name)

        file_name = self._file_name_from_url(response.url)
        parser.attach_fulltext_document(file_name, response.url)

        return ParsedItem(
            record=parser.parse(),
            record_format='hep',
        )

    def _parse_json_on_failure(self, failure):
        """Parse a JSON article entry."""
        original_response = failure.request.meta['original_response']
        record = HEPLoader(item=HEPRecord(), response=original_response)
        article = failure.request.meta['json_article']

        doi = get_value(article, 'identifiers.doi', default='')
        record.add_dois(dois_values=[doi])
        record.add_value('page_nr', str(article.get('numPages', '')))

        record.add_value('abstract', get_value(article, 'abstract.value', default=''))
        record.add_value('title', get_value(article, 'title.value', default=''))
        # record.add_value('subtitle', '')

        authors, collaborations = self._get_authors_and_collab(article)
        record.add_value('authors', authors)
        record.add_value('collaborations', collaborations)

        # record.add_value('free_keywords', free_keywords)
        # record.add_value('classification_numbers', classification_numbers)

        record.add_value('journal_title',
                         get_value(article, 'journal.abbreviatedName', default=''))
        record.add_value('journal_issue',
                         get_value(article, 'issue.number', default=''))
        record.add_value('journal_volume',
                         get_value(article, 'volume.number', default=''))
        # record.add_value('journal_artid', )

        published_date = article.get('date', '')
        record.add_value('journal_year', int(published_date[:4]))
        record.add_value('date_published', published_date)
        record.add_value('copyright_holder',
                         get_value(article, 'rights.copyrightHolders.name[0]', default=''))
        record.add_value('copyright_year',
                         str(get_value(article, 'rights.copyrightYear', default='')))
        record.add_value('copyright_statement',
                         get_value(article, 'rights.rightsStatement', default=''))
        record.add_value('copyright_material', 'publication')

        license = get_licenses(
            license_url=get_value(article, 'rights.licenses.url[0]', default='')
        )
        record.add_value('license', license)

        record.add_value('collections', ['HEP', 'Citeable', 'Published'])

        return ParsedItem(
            record=record.load_item(),
            record_format='hepcrawl',
        )

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
                    "raw_name": author.get('name', ''),
                    'affiliations': author_affiliations
                })

            elif author['type'] == 'Collaboration':
                collaboration.append(author['name'])

        return authors, collaboration

    def _file_name_from_url(self, url):
        return "{}.xml".format(url[url.rfind('/') + 1:])
