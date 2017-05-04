..
    This file is part of hepcrawl.
    Copyright (C) 2015, 2016, 2017 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.

Installation
============


Quick Installation
------------------


.. code-block:: console

    pip install hepcrawl


.. warning::

    Beware that you may need to install additional system level packages like libffi, libssl, libxslt, libxml2 etc.


Installation for developers
---------------------------

We start by creating a virtual environment for our Python packages:

.. code-block:: console

    mkvirtualenv hepcrawl
    cdvirtualenv
    mkdir src && cd src


Now we grab the code and install it in development mode:

.. code-block:: console

    git clone https://github.com/inspirehep/hepcrawl.git
    cd hepcrawl
    pip install -e .


Development mode ensures that any changes you do to your sources are automatically
taken into account = no need to install again after changing something.

Finally run the tests to make sure all is setup correctly:

.. code-block:: console

    python setup.py test


Run a crawler
-------------

Thanks to the command line tools provided by Scrapy, we can easily test the
spiders as we are developing them. Here is an example using the simple sample
spider:

.. code-block:: console

    cdvirtualenv src/hepcrawl
    scrapy crawl arXiv -a source_file=file://`pwd`/tests/responses/arxiv/sample_arxiv_record.xml


Run the crawler with INSPIRE (assuming you already have a virtualenv with everything set up).

The example below shows how to get all papers from the 24th June 2016 to the 26th June 2016 
from arXiv where the subject area is hep-th (HEP Theory). We use the arXiv spider and assign the
article workflow.

.. code-block:: console
    
    workon inspire-next
    
    inspirehep oaiharvester harvest -m arXiv -u http://export.arxiv.org/oai2 -f 2016-06-24 -t 2016-06-26 -s 'physics:hep-th' -a 'spider=arXiv' -a 'workflow=article'
    
Thanks for contributing!
