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

from scrapy import Request, Spider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_license, get_nested, build_dict


class APSSpider(Spider):
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
        """Parse a APS JSON file into a HEP record."""
        aps_response = json.loads(response.body_as_unicode())

        for article in aps_response['data']:
            record = HEPLoader(item=HEPRecord(), response=response)

            record.add_value('dois', get_nested(article, 'identifiers', 'doi'))
            record.add_value('page_nr', str(article.get('numPages', '')))

            record.add_value('abstract', get_nested(article, 'abstract', 'value'))
            record.add_value('title', get_nested(article, 'title', 'value'))
            # record.add_value('subtitle', '')

            authors, collaborations = self._get_authors_and_collab(article)
            record.add_value('authors', authors)
            record.add_value('collaborations', collaborations)

            # record.add_value('free_keywords', free_keywords)
            # record.add_value('classification_numbers', classification_numbers)

            record.add_value('journal_title', get_nested(article, 'journal', 'abbreviatedName'))
            record.add_value('journal_issue', get_nested(article, 'issue', 'number'))
            record.add_value('journal_volume', get_nested(article, 'volume', 'number'))
            # record.add_value('journal_artid', )

            published_date = article.get('date', '')
            record.add_value('journal_year', int(published_date[:4]))
            record.add_value('date_published', published_date)
            record.add_value('copyright_holder', get_nested(article, 'rights', 'copyrightHolders')[0]['name'])
            record.add_value('copyright_year', str(get_nested(article, 'rights', 'copyrightYear')))
            record.add_value('copyright_statement', get_nested(article, 'rights', 'rightsStatement'))
            record.add_value('copyright_material', 'Article')

            license = get_license(
                license_url=get_nested(article, 'rights', 'licenses')[0]['url']
            )
            record.add_value('license', license)

            record.add_value('collections', ['HEP', 'Citeable', 'Published'])
            yield record.load_item()

        # Pagination support. Will yield until no more "next" pages are found
        if 'Link' in response.headers:
            links = link_header.parse(response.headers['Link'])
            next = links.links_by_attr_pairs([('rel', 'next')])
            if next:
                next_url = next[0].href
                yield Request(next_url)

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
