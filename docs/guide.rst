..
    This file is part of hepcrawl.
    Copyright (C) 2015 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.

.. currentmodule:: hepcrawl


Adding a new crawler
====================

Add a new file under ``hepcrawl/spider`` following the naming pattern ``myname_spider.py``.


Useful development tools
========================

The scrapy shell is very useful when writing the extraction from the source XML to an item.

``scrapy shell file:///path/to/sample.xml``

You can then run xpath expressions like:

``response.selector.xpath("//abstract")``


| INSPIRE Development Team
|   Email: feedback@inspirehep.net
|   Twitter: http://twitter.com/inspirehep
|   GitHub: http://github.com/inspirehep
|   URL: http://inspirehep.net
