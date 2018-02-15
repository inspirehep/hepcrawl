..
    This file is part of hepcrawl.
    Copyright (C) 2015, 2016, 2017 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.

Installation
============


Quick Installation
++++++++++++++++++


.. code-block:: console

    pip install hepcrawl


.. warning::

    Beware that you may need to install additional system level packages like:
    ``libffi``, ``libssl``, ``libxslt``, ``libxml2``.


Installation for developers
+++++++++++++++++++++++++++

.. include:: ./docker_installation.rst


.. include:: ./native_installation.rst


Run a crawler
-------------

Thanks to the command line tools provided by Scrapy, we can easily test the
spiders as we are developing them. Here is an example using the simple sample
spider:

.. code-block:: console

    cdvirtualenv src/hepcrawl
    scrapy crawl arXiv -a source_file=file://`pwd`/tests/unit/responses/arxiv/sample_arxiv_record.xml


Run the crawler with INSPIRE (assuming you already have a virtualenv with everything set up).

The example below shows how to get all papers from the 24th June 2016 to the 26th June 2016
from arXiv where the subject area is hep-th (HEP Theory). We use the arXiv spider and assign the
article workflow.

.. code-block:: console

    workon inspire-next

    inspirehep oaiharvester harvest -m arXiv -u http://export.arxiv.org/oai2 -f 2016-06-24 -t 2016-06-26 -s 'physics:hep-th' -a 'spider=arXiv' -a 'workflow=article'

Thanks for contributing!
