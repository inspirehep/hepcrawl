# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Generic spider for OAI-PMH servers."""

import abc
import logging
from datetime import datetime
from six import string_types

from sickle import Sickle
from sickle.oaiexceptions import NoRecordsMatch

from scrapy.http import Request, XmlResponse
from scrapy.selector import Selector

from .last_run_store import LastRunStoreSpider


LOGGER = logging.getLogger(__name__)


class NoLastRunToLoad(Exception):
    """Error raised when there was a problem with loading the last_runs file"""
    def __init__(self, file_path, set_):
        self.message = u"Failed to load file at {} for set {}".format(
            file_path,
            set_,
        )


class OAIPMHSpider(LastRunStoreSpider):
    """
    Implements a spider for the OAI-PMH protocol by using the Python sickle
    library.

    In case of successful harvest (OAI-PMH crawling) the spider will remember
    the initial starting date and will use it as `from_date` argument on the
    next harvest.
    """
    __metaclass__ = abc.ABCMeta
    name = 'OAI-PMH'

    def __init__(
        self,
        url,
        format='oai_dc',
        sets=None,
        alias=None,
        from_date=None,
        until_date=None,
        *args, **kwargs
    ):
        super(OAIPMHSpider, self).__init__(*args, **kwargs)
        self.url = url
        self.format = format
        if isinstance(sets, string_types):
            sets = sets.split(',')
        self.sets = sets
        self.from_date = from_date
        self.until_date = until_date

    def start_requests(self):
        started_at = datetime.utcnow()

        LOGGER.info(
            u"Starting harvesting of {url} with sets={sets} and "
            u"metadataPrefix={metadata_prefix},"
            u"from={from_date}, "
            u"until={until_date}".format(
                url=self.url,
                sets=self.sets,
                metadata_prefix=self.format,
                from_date=self.from_date,
                until_date=self.until_date
            )
        )

        for oai_set in self.sets:
            from_date = self.from_date or self.resume_from(set_=oai_set)

            LOGGER.info(
                u"Starting harvesting of set={oai_set} from "
                "{from_date}".format(
                    oai_set=oai_set,
                    from_date=from_date,
                )
            )

            request = Request('oaipmh+%s' % self.url, self.parse)
            request.meta['set'] = oai_set
            request.meta['from_date'] = from_date
            yield request

            now = datetime.utcnow()
            self.save_run(started_at=started_at, set_=oai_set)

            LOGGER.info(
                "Harvesting of set %s completed. Next time will resume from %s"
                % (
                    oai_set,
                    self.until_date or now.strftime('%Y-%m-%d')
                )
            )

        LOGGER.info("Harvesting completed.")

    @abc.abstractmethod
    def parse_record(self, record):
        """
        This method need to be reimplemented in order to provide special
        parsing.

        Args:
            record (scrapy.selector.Selector): selector on the parsed record
        """
        raise NotImplementedError()

    def parse(self, response):
        sickle = Sickle(self.url)
        try:
            records = sickle.ListRecords(**{
                'metadataPrefix': self.format,
                'set': response.meta['set'],
                'from': response.meta['from_date'],
                'until': self.until_date,
            })
        except NoRecordsMatch as err:
            LOGGER.warning(err)
            raise StopIteration()
        for record in records:
            response = XmlResponse(self.url, encoding='utf-8', body=record.raw)
            selector = Selector(response, type='xml')
            yield self.parse_record(selector)

    def make_file_fingerprint(self, set_):
        return u'metadataPrefix={}&set={}'.format(self.format, set_)
