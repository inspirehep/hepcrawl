# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Common extraction from the JATS XML format."""

from __future__ import absolute_import, division, print_function

import datetime

from ..utils import get_first


class Jats(object):
    """Special extractions for JATS formats."""

    def _get_published_date(self, node):
        """Return a ISO string of published date (e.g. 2001-01-01)."""
        def format_date(day, month, year):
            day = int(get_first(day, 1))
            month = int(get_first(month, 1))
            year = int(get_first(year, 1))
            return datetime.date(day=day, month=month, year=year).isoformat()

        if node.xpath(".//date[@date-type='published']"):
            return format_date(
                day=node.xpath(".//date[@date-type='published']/day/text()").extract(),
                month=node.xpath(".//date[@date-type='published']/month/text()").extract(),
                year=node.xpath(".//date[@date-type='published']/year/text()").extract(),
            )
        elif node.xpath(".//pub-date[@pub-type='ppub']"):
            return format_date(
                day=node.xpath(".//pub-date[@pub-type='ppub']/day/text()").extract(),
                month=node.xpath(".//pub-date[@pub-type='ppub']/month/text()").extract(),
                year=node.xpath(".//pub-date[@pub-type='ppub']/year/text()").extract(),
            )
        elif node.xpath(".//pub-date[@pub-type='epub']"):
            return format_date(
                day=node.xpath(".//pub-date[@pub-type='epub']/day/text()").extract(),
                month=node.xpath(".//pub-date[@pub-type='epub']/month/text()").extract(),
                year=node.xpath(".//pub-date[@pub-type='epub']/year/text()").extract(),
            )
        elif node.xpath(".//pub-date"):
            return format_date(
                day=node.xpath(".//pub-date/day/text()").extract(),
                month=node.xpath(".//pub-date/month/text()").extract(),
                year=node.xpath(".//pub-date/year/text()").extract(),
            )
        else:
            # In the worst case we return today
            return datetime.date.today().isoformat()

    def _get_keywords(self, node):
        """Return tuple of keywords, PACS from node."""
        free_keywords = []
        classification_numbers = []
        for group in node.xpath('.//kwd-group'):
            if "pacs" in group.xpath('@kwd-group-type').extract():
                for keyword in group.xpath('kwd/text()').extract():
                    classification_numbers.append(keyword)
            else:
                for keyword in group.xpath('kwd').extract():
                    free_keywords.append(keyword)
        return free_keywords, classification_numbers

    def _get_authors(self, node):
        authors = []
        for contrib in node.xpath(".//contrib[@contrib-type='author']"):
            surname = contrib.xpath("string-name/surname/text()").extract()
            given_names = contrib.xpath("string-name/given-names/text()").extract()
            email = contrib.xpath("email/text()").extract()
            affiliations = contrib.xpath('aff')
            reffered_id = contrib.xpath("xref[@ref-type='aff']/@rid").extract()
            if reffered_id:
                affiliations += node.xpath(".//aff[@id='{0}']".format(
                    get_first(reffered_id))
                )
            affiliations = [
                {'value': get_first(aff.re('<aff.+?>(.*)</aff>'))}
                for aff in affiliations
                if aff.re('<aff.+?>(.*)</aff>')
            ]

            authors.append({
                'surname': get_first(surname, ""),
                'given_names': get_first(given_names, ""),
                'affiliations': affiliations,
                'email': get_first(email, ""),
            })
        return authors
