# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Generic spider for OAI-PMH servers."""

import logging
from enum import Enum
from errno import EEXIST
from datetime import datetime
from dateutil import parser as dateparser
import hashlib
import json
from os import path, makedirs

from sickle import Sickle
from sickle.oaiexceptions import NoRecordsMatch

from scrapy.http import Request, XmlResponse
from scrapy.selector import Selector
from . import StatefulSpider


LOGGER = logging.getLogger(__name__)


class _Granularity(Enum):
    DATE = 'YYYY-MM-DD'
    SECOND = 'YYYY-MM-DDThh:mm:ssZ'

    def format(self, datetime_object):
        if self == self.DATE:
            return datetime_object.strftime('%Y-%m-%d')
        if self == self.SECOND:
            return datetime_object.strftime('%Y-%m-%dT%H:%M:%SZ')


class OAIPMHSpider(StatefulSpider):
    """
    Implements a spider for the OAI-PMH protocol by using the Python sickle library.

    In case of successful harvest (OAI-PMH crawling) the spider will remember
    the initial starting date and will use it as `from_date` argument on the
    next harvest.
    """
    name = 'OAI-PMH'
    granularity = _Granularity.DATE

    def __init__(
        self,
        url,
        metadata_prefix='oai_dc',
        oai_set=None,
        alias=None,
        from_date=None,
        until_date=None,
        granularity=_Granularity.DATE,
        record_class=Record,
        *args, **kwargs
    ):
        super(OAIPMHSpider, self).__init__(*args, **kwargs)
        self.url = url
        self.metadata_prefix = metadata_prefix
        self.set = oai_set
        self.granularity = granularity
        self.alias = alias or self._make_alias()
        self.from_date = from_date
        self.until_date = until_date
        self.record_class = record_class

    def start_requests(self):
        self.from_date = self.from_date or self._resume_from
        started_at = datetime.utcnow()

        LOGGER.info("Starting harvesting of {url} with set={set} and "
                    "metadataPrefix={metadata_prefix}, from={from_date}, "
                    "until={until_date}".format(
            url=self.url,
            set=self.set,
            metadata_prefix=self.metadata_prefix,
            from_date=self.from_date,
            until_date=self.until_date
        ))

        request = Request('oaipmh+{}'.format(self.url), self.parse)
        yield request

        now = datetime.utcnow()
        self._save_run(started_at)

        LOGGER.info("Harvesting completed. Next harvesting will resume from {}"
                    .format(self.until_date or self.granularity.format(now)))

    def parse_record(self, record):
        """
        This method need to be reimplemented in order to provide special parsing.

        Args:
            record (scrapy.selector.Selector): selector on the parsed record
        """
        raise NotImplementedError()

    def parse(self, response):
        sickle = Sickle(self.url, class_mapping={
            'ListRecords': self.record_class,
            'GetRecord': self.record_class,
        })
        try:
            records = sickle.ListRecords(**{
                'metadataPrefix': self.metadata_prefix,
                'set': self.set,
                'from': self.from_date,
                'until': self.until_date,
            })
        except NoRecordsMatch as err:
            LOGGER.warning(err)
            raise StopIteration()
        for record in records:
            response = XmlResponse(self.url, encoding='utf-8', body=record.raw)
            selector = Selector(response, type='xml')
            yield self.parse_record(selector)

    def _make_alias(self):
        return '{url}?metadataPrefix={metadata_prefix}&set={set}'.format(
            url=self.url,
            metadata_prefix=self.metadata_prefix,
            set=self.set
        )

    def _last_run_file_path(self):
        """Render a path to a file where last run information is stored.

        Returns:
            string: path to last runs path
        """
        lasts_run_path = self.settings['LAST_RUNS_PATH']
        file_name = hashlib.sha1(self._make_alias()).hexdigest() + '.json'
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
        except IOError:
            return None

    def _save_run(self, started_at):
        """Store last run information

        Args:
            started_at (datetime.datetime)

        Raises:
            IOError: if writing the file is unsuccessful
        """
        last_run_info = {
            'spider': self.name,
            'url': self.url,
            'metadata_prefix': self.metadata_prefix,
            'set': self.set,
            'granularity': self.granularity.value,
            'from_date': self.from_date,
            'until_date': self.until_date,
            'last_run_started_at': started_at.isoformat(),
            'last_run_finished_at': datetime.utcnow().isoformat(),
        }
        file_path = self._last_run_file_path()
        LOGGER.info("Last run file saved to {}".format(file_path))
        try:
            makedirs(path.dirname(file_path))
        except OSError as exc:
            if exc.errno == EEXIST:
                pass
            else:
                raise
        with open(file_path, 'w') as f:
            json.dump(last_run_info, f, indent=4)

    @property
    def _resume_from(self):
        last_run = self._load_last_run()
        if not last_run:
            return None
        resume_at = last_run['until_date'] or last_run['last_run_finished_at']
        date_parsed = dateparser.parse(resume_at)
        return self.granularity.format(date_parsed)
