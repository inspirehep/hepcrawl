# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2018 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BD License; see LICENSE file for
# more details.

import copy


class CrawlResult(object):
    """Representation of a crawling result.

    This class defines the API used by the pipeline to send crawl results.

    Attributes:
        record (dict): the crawled record.
        file_name (str): the name of the remote file crawled.
        source_data (str): content of the remote file crawled.
        errors (list): list of dictionaries with keys "exception" and
        "traceback", which collects all the errors occurred during the parsing
            phase.
    """
    def __init__(self, record, file_name="", source_data=""):
        self.record = record
        self.file_name = file_name
        self.source_data = source_data
        self.errors = []

    def add_error(self, exception_class, traceback):
        error = {
            'exception': exception_class,
            'traceback': traceback
        }
        self.errors.append(error)

    @staticmethod
    def from_parsed_item(parsed_item):
        result = CrawlResult(
            record=parsed_item['record'],
            file_name=parsed_item.get('file_name'),
            source_data=parsed_item.get('source_data')
        )

        if parsed_item.get('exception'):
            result.add_error(
                parsed_item['exception'],
                parsed_item['traceback']
            )

        return result

    def to_dict(self):
        return copy.deepcopy(self.__dict__)
