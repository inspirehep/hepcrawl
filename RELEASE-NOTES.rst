..
    This file is part of hepcrawl.
    Copyright (C) 2015, 2016, 2017 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.

================
 HEPCrawl v0.2.0
================

HEPCrawl v0.2.0 was released on 2nd of June, 2016.

About
-----

HEPcrawl is a harvesting library based on Scrapy (http://scrapy.org) for INSPIRE-HEP
(http://inspirehep.net).

What's new
----------

- 11 new spiders, including arXiv, APS, Base OAI source, Elsevier and many more.
- Updated HEPRecord data items to conform with updates to INSPIRE data model.
- Reorganization of loaders to have one place for input and output processing of metadata.
- New pipelines for pushing content crawled to INSPIRE servers.
- Better error handling and reporting, including support for Sentry.

Installation
------------

   $ pip install hepcrawl==0.2.0

Documentation
-------------

   http://pythonhosted.org/hepcrawl/

Happy hacking and thanks for flying HEPCrawl.

| INSPIRE Development Team
|   Email: feedback@inspirehep.net
|   Twitter: http://twitter.com/inspirehep
|   GitHub: http://github.com/inspirehep
|   URL: http://inspirehep.net
