..
    This file is part of hepcrawl.
    Copyright (C) 2015 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.


==========
 HEPcrawl
==========

HEPcrawl is a harvesting library based on Scrapy (http://scrapy.org) for INSPIRE-HEP
(http://inspirehep.net) that focuses on automatic and semi-automatic retrieval of
new content from all the sources the site aggregates. In particular content from
major and minor publishers in the field of High-Energy Physics.

The project is currently in early stage of development.

Installation for developers
===========================

We start by creating a virtual environment for our Python packages:

.. code-block:: shell

    mkvirtualenv hepcrawl
    cdvirtualenv
    mkdir src && cd src


Now we grab the code and install it in development mode:

.. code-block:: shell

    git clone https://github.com/inspirehep/hepcrawl.git
    cd hepcrawl
    pip install -e .


Development mode ensures that any changes you do to your sources are automatically
taken into account = no need to install again after changing something.

Finally run the tests to make sure all is setup correctly:

.. code-block:: shell

    python setup.py test


Run example crawler
===================

Thanks to the command line tools provided by Scrapy, we can easily test the
spiders as we are developing them. Here is an example using the simple sample
spider:

.. code-block:: console

    cdvirtualenv src/hepcrawl
    scrapy crawl arXiv -a source_file=file://`pwd`/tests/responses/arxiv/sample_arxiv_record.xml


Thanks for contributing!
