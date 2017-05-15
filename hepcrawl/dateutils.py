# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Date parsing utilities that support dates before 1900."""

from __future__ import absolute_import, division, print_function

import re
import six
import time

from datetime import date as real_date
from datetime import datetime as real_datetime
import dateutil.parser as dparser


DATE_FORMATS_YEAR = ["%Y", "%y"]
DATE_FORMATS_MONTH = [
    "%Y-%m", "%Y %b", "%b %Y", "%Y %B", "%B %Y",
    "%y-%m", "%y %b", "%b %y", "%y %B", "%B %y",
]
DATE_FORMATS_FULL = [
    "%Y-%m-%d", "%d %m %Y", "%x", "%d %b %Y",
    "%d %B %Y", "%d %b %y", "%d %B %y", "%Y-%m-%dT%H:%M:%SZ", "%d-%m-%Y",
]

# This library does not support strftime's "%s" or "%y" format strings.
# Allowed if there's an even number of "%"s because they are escaped.
_illegal_formatting = re.compile(r"((^|[^%])(%%)*%[sy])")


class date(real_date):
    """Special date subclass with custom strftime implementation."""

    def strftime(self, fmt):
        return strftime(fmt, self)


class datetime(real_datetime):
    """Special datetime subclass with custom implementations."""

    def strftime(self, fmt):
        return strftime(fmt, self)

    @classmethod
    def combine(self, date, time):
        return self(date.year, date.month, date.day, time.hour, time.minute,
                    time.second, time.microsecond, time.tzinfo)

    def __add__(self, other):
        d = real_datetime.combine(self, self.timetz())
        d += other
        return self.combine(d, d.timetz())

    def date(self):
        return date(self.year, self.month, self.day)

    @staticmethod
    def strptime(date_string, format):
        return datetime(*(time.strptime(date_string, format)[0:6]))


def _findall(text, substr):
    # Also finds overlaps
    sites = []
    i = 0
    while True:
        j = text.find(substr, i)
        if j == -1:
            break
        sites.append(j)
        i = j + 1
    return sites


def strftime(fmt, dt):
    """A ``strftime(format, date object)`` that support dates before 1900."""
    if not isinstance(dt, real_date):
        dt = datetime(dt.tm_year, dt.tm_mon, dt.tm_mday, dt.tm_hour, dt.tm_min,
                      dt.tm_sec)
    if dt.year >= 1900:
        return time.strftime(fmt, dt.timetuple())
    illegal_formatting = _illegal_formatting.search(fmt)
    if illegal_formatting:
        raise TypeError("strftime of dates before 1900 does not handle %s" %
                        illegal_formatting.group(0))

    year = dt.year
    # For every non-leap year century, advance by
    # 6 years to get into the 28-year repeat cycle
    delta = 2000 - year
    off = 6 * (delta // 100 + delta // 400)
    year = year + off

    # Move to around the year 2000
    year = year + ((2000 - year) // 28) * 28
    timetuple = dt.timetuple()
    s1 = time.strftime(fmt, (year,) + timetuple[1:])
    sites1 = _findall(s1, str(year))

    s2 = time.strftime(fmt, (year + 28,) + timetuple[1:])
    sites2 = _findall(s2, str(year + 28))

    sites = []
    for site in sites1:
        if site in sites2:
            sites.append(site)

    s = s1
    syear = "%04d" % (dt.year,)
    for site in sites:
        s = s[:site] + syear + s[site + 4:]
    return s


def strptime(date_string, fmt):
    """A ``strptime(date string, format)`` that support dates before 1900."""
    return real_datetime(*(time.strptime(date_string, fmt)[:6]))


def create_valid_date(date, date_format_full="%Y-%m-%d",
                      date_format_month="%Y-%m", date_format_year="%Y"):
    """Iterate over possible formats and return a valid date if found."""
    valid_date = None
    date = six.text_type(date)
    for format in DATE_FORMATS_FULL:
        try:
            valid_date = strftime(date_format_full, (strptime(date, format)))
            break
        except ValueError:
            pass
    else:
        for format in DATE_FORMATS_MONTH:
            try:
                if date.count('-') > 1:
                    date = "-".join(date.split('-')[:2])
                valid_date = strftime(date_format_month, (strptime(date, format)))
                break
            except ValueError:
                pass
        else:
            for format in DATE_FORMATS_YEAR:
                try:
                    if date.count('-') > 0:
                        date = date.split('-')[0]
                    valid_date = strftime(date_format_year, (strptime(date, format)))
                    break
                except ValueError:
                    pass
    return valid_date


def parse_date(raw_date):
    """Get the date in correct format using ``dateutil.parser``.

    .. note::
        If no month or day can be found in the raw date string, they
        will be set to 1 (e.g., ``Mar 1999`` -> ``1999-03-01``). If the string cannot
        be parsed, return the string.
    """
    if not raw_date:
        return raw_date

    if not isinstance(raw_date, str):
        raw_date = str(raw_date)

    try:
        DEFAULT_DATE = real_datetime(1, 1, 1)
        parsed_date = dparser.parse(raw_date, default=DEFAULT_DATE)
        date_published = parsed_date.date().isoformat()
    except ValueError:
        date_published = raw_date

    return date_published


def format_date(raw_date):
    """Get the ISO formatted year and date.

    Calls first the format preserving date creator function, if that fails
    calls the function that uses ``dateutils``.
    """
    date_published = create_valid_date(raw_date)
    if not date_published:
        date_published = parse_date(raw_date)
    if not date_published:
        date_published = ''

    return date_published


def format_year(raw_date):
    """Get the year from the ISO formatted date."""
    date_published = format_date(raw_date)
    try:
        year = dparser.parse(date_published).year
    except ValueError:
        year = 0

    return year
