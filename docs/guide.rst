..
    This file is part of hepcrawl.
    Copyright (C) 2015, 2016, 2017 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.

.. currentmodule:: hepcrawl


Useful tools
============

Testing your spider
-------------------

Thanks to the command line tools provided by Scrapy, we can easily test the
spiders as we are developing them:


.. code-block:: console

    scrapy crawl WSP -a 'ftp_host=ftp.example.com' -a 'ftp_netrc=/path/to/netrc'


``WSP`` is the name of the spider as defined in the ``name`` attribute of the spider.

As you see, you can also pass custom arguments to the spider via the ``-a`` flag. These will
be directly mapped to the constructor of the spider.

If you want to change the directory where your JSON file will be stored, pass
the settings variable ``JSON_OUTPUT_DIR`` to any ``scrapy crawl`` command:

.. code-block:: console

    scrapy crawl WSP -s 'JSON_OUTPUT_DIR=/tmp/' -a 'ftp_host=ftp.example.com' -a 'ftp_netrc=/path/to/netrc'


Writing extraction code with scrapy shell
-----------------------------------------

In order to help you implement the extraction from the XML files, scrapy provides
a shell simulating a response:

.. code-block:: console

    scrapy shell file:///path/to/sample.xml


You can then run xpath expressions in the shell:

.. code-block:: python

    response.selector.xpath(".//abstract").extract()
    ["...some abstract ..."]
