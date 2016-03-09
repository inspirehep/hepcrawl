# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals


import pytest

from hepcrawl.dateutils import format_date, format_year


@pytest.fixture
def dates():
    """Return list of tuples of formatted year and date."""
    dates = {}
    raw_dates = ["2013-05-09T05:16:48Z", "1973", "1916 Mar 4", "2014-2", "2012-5-55",
            "2012 Feb", "1 May 1992", "5-2022", "5-222HH", 1995, "today", "1988/05/26"]
    
    for raw_date in raw_dates:
        dates[raw_date] = format_year(raw_date), format_date(raw_date)
    return dates 


def test_dates(dates):
    """Test that the date formatter function formats the dates and years
    correctly."""
    assert dates
    assert dates["2013-05-09T05:16:48Z"] == (2013, '2013-05-09')
    assert dates["1973"] == (1973, '1973')
    assert dates["1916 Mar 4"] == (1916, '1916-03-04') 
    assert dates["2014-2"] == (2014, '2014-02')
    assert dates["2012-5-55"] == (2012, '2012-05')
    assert dates["2012 Feb"] == (2012, '2012-02')
    assert dates["1 May 1992"] == (1992, '1992-05-01')
    assert dates["5-2022"] == (2022, '2022-05-01')
    assert dates["5-222HH"] == (0, '5-222HH')
    assert dates[1995] == (1995, '1995')
    assert dates["today"] == (0, 'today')
    assert dates["1988/05/26"] == (1988, '1988-05-26')
