# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider that stores information about last run in a file."""

from __future__ import absolute_import, division, print_function

import abc
import hashlib
import json
import logging

from datetime import datetime
from dateutil import parser as dateparser
from errno import EEXIST as FILE_EXISTS, ENOENT as NO_SUCH_FILE_OR_DIR
from os import path, makedirs

from .. import StatefulSpider

LOGGER = logging.getLogger(__name__)


class NoLastRunToLoad(Exception):
    """Error raised when there was a problem with loading the last_runs file"""
    def __init__(self, file_path, set_):
        self.message = "Failed to load file at {} for set {}"\
            .format(file_path, set_)


class LastRunStoreSpider(StatefulSpider):
    """Takes care of storing information about spiders' last run."""
    __metaclass__ = abc.ABCMeta
    from_date = None
    until_date = None
    format = None
    url = None

    @abc.abstractmethod
    def make_file_fingerprint(self, set_):
        """Create an identifier for last run files

        Args:
            set_ (string): the set being harvested
        """
        raise NotImplementedError()

    def _last_run_file_path(self, set_):
        """Render a path to a file where last run information is stored.

        Args:
            set_ (string): OAI set being harvested

        Returns:
            string: path to last runs path
        """
        lasts_run_path = self.settings['LAST_RUNS_PATH']
        file_name = hashlib.sha1(self.make_file_fingerprint(set_)).hexdigest() + '.json'
        return path.join(lasts_run_path, self.name, file_name)

    def _load_last_run(self, set_):
        """Return stored last run information

        Args:
            set_ (string): set to load the last run information for

        Returns:
            dict: last run information or None if don't exist

        Raises:
            NoLastRunToLoad: if no last run file exists yet
        """
        file_path = self._last_run_file_path(set_)
        try:
            with open(file_path) as f:
                last_run = json.load(f)
                LOGGER.info('Last run file loaded: {}'.format(repr(last_run)))
                return last_run
        except IOError as exc:
            if exc.errno == NO_SUCH_FILE_OR_DIR:
                raise NoLastRunToLoad(file_path, set_)
            raise

    def save_run(self, started_at, set_):
        """Store last run information

        Args:
            started_at (datetime.datetime)
            set_ (string): set being harvested

        Raises:
            IOError: if writing the file is unsuccessful
        """
        last_run_info = {
            'spider': self.name,
            'url': self.url,
            'set': set_,
            'from_date': self.from_date,
            'until_date': self.until_date,
            'format': self.format,
            'last_run_started_at': started_at.isoformat(),
            'last_run_finished_at': datetime.utcnow().isoformat(),
        }
        file_path = self._last_run_file_path(set_)
        LOGGER.info("Last run file saved to {}".format(file_path))
        try:
            makedirs(path.dirname(file_path))
        except OSError as exc:
            if exc.errno != FILE_EXISTS:
                raise
        with open(file_path, 'w') as f:
            json.dump(last_run_info, f, indent=4)

    def resume_from(self, set_):
        try:
            last_run = self._load_last_run(set_)
            resume_at = last_run['until_date'] or last_run['last_run_finished_at']
            date_parsed = dateparser.parse(resume_at)
            return date_parsed.strftime('%Y-%m-%d')
        except NoLastRunToLoad:
            return None
