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

from datetime import datetime
import hashlib
import json
import link_header
import logging
import re

from errno import EEXIST as FILE_EXISTS, ENOENT as NO_SUCH_FILE_OR_DIR
from furl import furl
from os import path, makedirs
from scrapy import Request, Spider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..settings import LAST_RUNS_PATH
from ..utils import get_license, get_nested, build_dict

LOGGER = logging.getLogger(__name__)

class APSSpider(Spider):
    """APS crawler.

    Uses the APS REST API v2. See documentation here:
    http://harvest.aps.org/docs/harvest-api#endpoints

    scrapy crawl APS -a 'from_date=2016-05-01' -a 'until_date=2016-05-15' -a 'sets=openaccess'
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
            self.params = {}
            if from_date:
                self.params['from'] = from_date
            else:
                last_run = self._load_last_run()
                if last_run:
                    f = last_run['last_run_finished_at'].split('T')[0]
                    self.params['from'] = f
            if until_date:
                self.params['until'] = until_date
            if date:
                self.params['date'] = date
            if journals:
                self.params['journals'] = journals
            if per_page:
                self.params['per_page'] = per_page
            if sets:
                self.params['set'] = sets

            # Put it together: furl is awesome
            url = furl(APSSpider.aps_base_url).add(self.params).url
        self.url = url

    def _last_run_file_path(self):
        """Render a path to a file where last run information is stored.
        Returns:
            string: path to last runs path
        """
        lasts_run_path = LAST_RUNS_PATH
        #file_name = hashlib.sha1(self._make_alias()).hexdigest() + '.json'
        file_name = 'test.json'
        return path.join(lasts_run_path, self.name, file_name)

    def _load_last_run(self):
        """Return stored last run information
        Returns:
            Optional[dict]: last run information or None if don't exist
        """
        file_path = self._last_run_file_path()
        try:
            with open(file_path) as f:
                last_run = json.load(f)
                LOGGER.info('Last run file loaded: {}'.format(repr(last_run)))
                return last_run
        except IOError as exc:
            if exc.errno == NO_SUCH_FILE_OR_DIR:
                return None
                # raise NoLastRunToLoad(file_path)
            raise


    def _save_run(self, started_at):
        """Store last run information
        Args:
            started_at (datetime.datetime)
        Raises:
            IOError: if writing the file is unsuccessful
        """
        print(self.params)
        last_run_info = {
            'spider': self.name,
            #'url': self.url,
            #'metadata_prefix': self.metadata_prefix,
            'set': self.params['set'],
            'from': self.params.get('from', None),
            'until': self.params.get('until', None),
            'date': self.params['date'],
            'journals': self.params.get('journals', None),
            'per_page': self.params['per_page'],
            'last_run_started_at': started_at.isoformat(),
            'last_run_finished_at': datetime.utcnow().isoformat(),
        }
        file_path = self._last_run_file_path()
        LOGGER.info("Last run file saved to {}".format(file_path))
        try:
            makedirs(path.dirname(file_path))
        except OSError as exc:
            if exc.errno != FILE_EXISTS:
                raise
        with open(file_path, 'w') as f:
            json.dump(last_run_info, f, indent=4)

    #def _make_alias(self):
    #    return 'metadataPrefix={metadata_prefix}&set={set}'.format(
    #        metadata_prefix=self.params['date'],
    #        set=self.params['set']
    #    )

    def start_requests(self):
        """Just yield the url."""
        started_at = datetime.utcnow()

        yield Request(self.url)

        self._save_run(started_at)


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
            record.add_value('field_categories', [
                {
                    'term': term.get('label'),
                    'scheme': 'APS',
                    'source': '',
                } for term in get_nested(
                    article,
                    'classificationSchemes',
                    'subjectAreas'
                )
            ])
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
