# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for OSTI/SLAC"""

from __future__ import absolute_import, division, print_function

import json
from datetime import datetime

from furl import furl

import link_header

from scrapy import Request

from .common.lastrunstore_spider import LastRunStoreSpider
from ..parsers import OSTIParser
from ..utils import (
    ParsedItem,
    strict_kwargs,
)


class OSTISpider(LastRunStoreSpider):
    """OSTI crawler

    Uses the OSTI REST API v1 https://www.osti.gov/api/v1/docs
    to harvest records associated with SLAC from OSTI

    Example:
        Using the OSTI spider::

            $ scrapy crawl OSTI -a "from_date=2019-04-01"

    """

    name = 'OSTI'
    osti_base_url = 'https://www.osti.gov/api/v1/records'

    @strict_kwargs
    def __init__(self,
                 from_date=None,
                 until_date=None,
                 rows=400,
                 product_types=u'Journal Article,Technical Report,Book,Thesis/Dissertation',
                 journal_types='',
                 research_org=u'slac',
                 **kwargs):
        super(OSTISpider, self).__init__(**kwargs)
        self.from_date = from_date
        self.until_date = until_date
        self.product_types = product_types
        self.journal_types = journal_types
        self.rows = rows
        self.research_org = research_org

    @property
    def url(self):
        """Constructs the URL to use for querying OSTI.

        Returns:
            str: URL
        """
        params = {}
        params['entry_date_start'] = self.from_date \
            or self.resume_from(set_=self.set)
        if self.until_date:
            params['entry_date_end'] = self.until_date
        if self.rows:
            params['rows'] = self.rows
        if self.product_types:
            params['product_type'] = self.product_types
        if self.journal_types:
            params['journal_type'] = self.journal_types
        if self.research_org:
            params['research_org'] = self.research_org

        return furl(OSTISpider.osti_base_url).add(params).url

    @property
    def set(self):
        """Acronym of the research organization for which to harvest publications.

        Returns:
            str: e.g. u'SLAC'
        """
        return self.research_org

    @property
    def headers(self):
        """HTTP headers to use in requests.

        Returns:
            dict:
        """
        return {'Accept': 'application/json'}

    def start_requests(self):
        """Just yield the scrapy.Request."""
        started_at = datetime.utcnow()
        self.logger.debug("URL is %s" % self.url)
        yield Request(self.url,
                      headers=self.headers)
        self.save_run(started_at=started_at, set_=self.set)

    def parse(self, response):
        """Parse OSTI response into HEP records.

        Returns:
            generator: dict: json
        """

        osti_response = json.loads(response.text)
        for record in osti_response:
            parser = OSTIParser(record, source=self.name)

            yield ParsedItem(
                record=parser.parse(),
                record_format="hep",
            )

        total_count = response.headers.get('X-Total-Count')
        if int(total_count) > len(osti_response):
            self.logger.debug("do paging, total of %s records" % int(total_count))

        # Pagination support. Will yield until no more "next" pages are found
        if 'Link' in response.headers:
            links = link_header.parse(response.headers[u'Link'].decode())
            nextlink = links.links_by_attr_pairs([(u'rel', u'next')])
            if nextlink:
                next_url = nextlink[0].href
                self.logger.debug("using next link %s" % next_url)
                yield Request(next_url,
                              headers=self.headers,
                              callback=self.parse)

    def make_file_fingerprint(self, set_):
        """Create a label to use in filename storing last_run information.

        Returns:
            str:
        """
        return u'set={}'.format(set_)

    @property
    def product_types(self):
        """Product type URL parameter

        Returns:
            str:
        """
        return self.__product_types

    @product_types.setter
    def product_types(self, ptypes):
        """Setter for product_type URL parameter with verification against
           allowed list
        """
        prod_types = ('Journal Article', 'Technical Report',
                      'Data', 'Software',
                      'Patent', 'Conference',
                      'Book', 'Program Document',
                      'Thesis/Dissertation',
                      'Multimedia', 'Miscellaneous')
        self.__product_types = ', '.join((pt.strip() for
                                          pt in ptypes.split(',')
                                          if pt.strip() in prod_types))

    @property
    def journal_types(self):
        """Journal type URL parameter

        Returns:
            str:
        """
        return self.__journal_types

    @journal_types.setter
    def journal_types(self, jtypes):
        """Setter for journal_type URL parameter with verification against
           allowed list
        """
        journal_types = {'AM': 'Accepted Manuscript',
                         'PA': 'Published Article',
                         'PM': "Publisher's Accepted Manuscript",
                         'OT': 'Other'}

        self.__journal_types = ', '.join((journal_types[jt.strip()] for
                                          jt in jtypes.split(',')
                                          if jt.strip() in journal_types))
