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

from scrapy import Request, Spider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_nested, build_dict


class APSSpider(Spider):
    """APS crawler."""

    name = 'APS'

    def __init__(self, url=None, **kwargs):
        """Construct APS spider."""
        super(APSSpider, self).__init__(**kwargs)
        self.url = url

    def start_requests(self):
        # TODO: Add authentication handling
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
            record.add_value('journal_year', published_date[:4])
            record.add_value('date_published', published_date)
            record.add_value('subject_terms', [
                term.get('label')
                for term in get_nested(article, 'classificationSchemes', 'subjectAreas')
            ])
            record.add_value('copyright_holder', get_nested(article, 'rights', 'copyrightHolders')[0]['name'])
            record.add_value('copyright_year', str(get_nested(article, 'rights', 'copyrightYear')))
            record.add_value('copyright_statement', get_nested(article, 'rights', 'rightsStatement'))
            record.add_value('copyright_material', 'Article')

            # record.add_xpath('license', '//license/license-p/ext-link/text()')
            # record.add_xpath('license_type', '//license/@license-type')
            record.add_value('license_url', get_nested(article, 'rights', 'licenses')[0]['url'])

            record.add_value('collections', ['HEP', 'Citeable', 'Published'])
            yield record.load_item()

    def _get_authors_and_collab(self, article):
        authors = []
        collaboration = []

        for author in article['authors']:
            if author['type'] == 'Person':
                author_affiliations = []
                affiliations = build_dict(article['affiliations'], 'id')
                for aff_id in author['affiliationIds']:
                    author_affiliations.append({
                        'value': affiliations[aff_id]['name']
                    })

                authors.append({
                    'surname': author.get('surname', ''),
                    'given_names': author.get('firstname', ''),
                    "full_name": author.get('name', ''),
                    'affiliations': author_affiliations
                })

            elif author['type'] == 'Collaboration':
                collaboration.append(author['name'])

        return authors, collaboration
