..
    This file is part of hepcrawl.
    Copyright (C) 2015, 2016, 2017 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.

.. currentmodule:: hepcrawl


Testing HEPcrawl
================

Writing tests for HEPcrawl
--------------------------

In HEPcrawl currently there are unit and some functional tests. In general, in unit tests we want to test some parts of
the project and not all the project itself. In order to test our project end to end we write functional tests. A
functional test simulates the whole environment that a ``spider`` runs.

For example, let's have a spider that crawls from FTP server and creates a record that in the end pushes to `Inspire-next
<https://github.com/inspirehep/inspire-next>`_ project. For the functional test we will need:

1. An FTP server, which could be a docker container with mounted volumes.
2. A celery worker, Hepcrawl docker container.
3. A rabbitmq broker, rabbitmq docker container.
4. A scrapyd service, Hepcrawl docker container.
5. A Hepcrawl docker container to execute the test.

We can easily combine the above docker containers with specific settings by using simply a ``docker-compose`` file.

Once we have an idea on how our functional test should be we will use the
``hepcrawl.testlib.celery_monitor.CeleryMonitor`` class in order to handle all the pushed records to ``Inspire-next``
project, which should be mocked by using the ``hepcrawl.teslib.tasks.submit_results`` celery task. For further
details about settings and example of functional test please refer to ``docker-compose.test.yml`` file.

.. tip::

    It is very important to write two kind of tests:

        * the normal senario, it should contain normal/expected data,
        * the extreme senario, it should contain invalid/damaged records, environment issues etc.

    In this way we can cover more senarios and catch future issues that may be unable to catch later.

.. tip::

    Try to create some tests that run back to back in order to simulate real a situation.


Useful tools
============

Running your spider
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


Debugging HEPcrawl
------------------

There are several ways that HEPcrawl project can be debugged.

Using the log
+++++++++++++

Every time that a spider runs produces
log files. Those files either are output of the command:

.. code-block:: console

    $ scrapy crawl desy 'source_folder=/path/to/sample_dir'

For example the above command's output is the following log:

.. code-block:: console

    2017-08-27 14:52:10 [scrapy.utils.log] INFO: Scrapy 1.4.0 started (bot: hepcrawl)
    2017-08-27 14:52:10 [scrapy.utils.log] INFO: Overridden settings: {'NEWSPIDER_MODULE': 'hepcrawl.spiders', 'SPIDER_MODULES': ['hepcrawl.spiders'], 'DUPEFILTER_CLASS': 'scrapy.dupefilters.BaseDupeFilter', 'USER_AGENT': 'hepcrawl (+http://www.inspirehep.net)', 'BOT_NAME': 'hepcrawl'}
    2017-08-27 14:52:10 [scrapy.middleware] INFO: Enabled extensions:
    ['scrapy.extensions.memusage.MemoryUsage',
     'scrapy.extensions.logstats.LogStats',
     'scrapy.extensions.telnet.TelnetConsole',
     'scrapy.extensions.corestats.CoreStats',
     'scrapy.extensions.spiderstate.SpiderState',
     'hepcrawl.extensions.ErrorHandler']
    2017-08-27 14:52:10 [scrapy.middleware] INFO: Enabled downloader middlewares:
    ['scrapy.downloadermiddlewares.httpauth.HttpAuthMiddleware',
     'scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware',
     'scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware',
     'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware',
     'hepcrawl.middlewares.ErrorHandlingMiddleware',
     'scrapy.downloadermiddlewares.retry.RetryMiddleware',
     'scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware',
     'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware',
     'scrapy.downloadermiddlewares.redirect.RedirectMiddleware',
     'scrapy.downloadermiddlewares.cookies.CookiesMiddleware',
     'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware',
     'scrapy.downloadermiddlewares.stats.DownloaderStats']
    2017-08-27 14:52:10 [scrapy.middleware] INFO: Enabled spider middlewares:
    ['scrapy.spidermiddlewares.httperror.HttpErrorMiddleware',
     'scrapy.spidermiddlewares.offsite.OffsiteMiddleware',
     'hepcrawl.middlewares.ErrorHandlingMiddleware',
     'scrapy.spidermiddlewares.referer.RefererMiddleware',
     'scrapy.spidermiddlewares.urllength.UrlLengthMiddleware',
     'scrapy.spidermiddlewares.depth.DepthMiddleware']
    2017-08-27 14:52:10 [scrapy.middleware] INFO: Enabled item pipelines:
    ['hepcrawl.pipelines.FftFilesPipeline',
     'hepcrawl.pipelines.InspireCeleryPushPipeline']
    2017-08-27 14:52:10 [scrapy.core.engine] INFO: Spider opened
    2017-08-27 14:52:10 [scrapy.extensions.logstats] INFO: Crawled 0 pages (at 0 pages/min), scraped 0 items (at 0 items/min)
    2017-08-27 14:52:10 [scrapy.extensions.telnet] DEBUG: Telnet console listening on 127.0.0.1:6023
    2017-08-27 14:52:10 [desy] DEBUG: Local: Try to crawl local file: /home/spiros/REPOS/hepcrawl/tests/functional/desy/fixtures/ftp_server/DESY/desy_no_namespace_collection_records.xml
    2017-08-27 14:52:10 [scrapy.core.engine] DEBUG: Crawled (200) <GET file:///home/spiros/REPOS/hepcrawl/tests/functional/desy/fixtures/ftp_server/DESY/desy_no_namespace_collection_records.xml> (referer: None)
    2017-08-27 14:52:10 [desy] DEBUG: Local: Try to crawl local file: /home/spiros/REPOS/hepcrawl/tests/functional/desy/fixtures/ftp_server/DESY/desy_collection_records.xml
    2017-08-27 14:52:10 [scrapy.core.engine] DEBUG: Crawled (200) <GET file:///home/spiros/REPOS/hepcrawl/tests/functional/desy/fixtures/ftp_server/DESY/desy_collection_records.xml> (referer: None)
    2017-08-27 14:52:10 [desy] DEBUG: Got record from url/path: file:///home/spiros/REPOS/hepcrawl/tests/functional/desy/fixtures/ftp_server/DESY/desy_no_namespace_collection_records.xml
    2017-08-27 14:52:10 [desy] DEBUG: FTP enabled: False
    2017-08-27 14:52:10 [scrapy.core.engine] DEBUG: Crawled (200) <GET file://None/home/spiros/REPOS/hepcrawl/tests/functional/desy/fixtures/ftp_server/DESY/FFT/test_fft_1.txt> (referer: None)
    2017-08-27 14:52:10 [scrapy.pipelines.files] DEBUG: File (downloaded): Downloaded file from <GET file://None/home/spiros/REPOS/hepcrawl/tests/functional/desy/fixtures/ftp_server/DESY/FFT/test_fft_1.txt> referred in <None>
    2017-08-27 14:52:10 [scrapy.core.engine] DEBUG: Crawled (200) <GET file://None/home/spiros/REPOS/hepcrawl/tests/functional/desy/fixtures/ftp_server/DESY/FFT/test_fft_2.txt> (referer: None)
    2017-08-27 14:52:10 [scrapy.pipelines.files] DEBUG: File (downloaded): Downloaded file from <GET file://None/home/spiros/REPOS/hepcrawl/tests/functional/desy/fixtures/ftp_server/DESY/FFT/test_fft_2.txt> referred in <None>
    2017-08-27 14:52:10 [desy] DEBUG: Got record from url/path: file:///home/spiros/REPOS/hepcrawl/tests/functional/desy/fixtures/ftp_server/DESY/desy_collection_records.xml
    2017-08-27 14:52:10 [desy] DEBUG: FTP enabled: False
    2017-08-27 14:52:11 [desy] DEBUG: Validated item by Inspire Schemas.
    2017-08-27 14:52:11 [scrapy.core.scraper] DEBUG: Scraped from <200 file:///home/spiros/REPOS/hepcrawl/tests/functional/desy/fixtures/ftp_server/DESY/desy_no_namespace_collection_records.xml>
    {'acquisition_source': {'source': 'desy', 'method': 'hepcrawl', 'submission_number': '', 'datetime': '2017-08-27T14:52:11.061844'}, '_collections': ['Literature'], 'control_number': 333333, 'public_notes': [{'value': '*Brief entry*'}], 'self': {'$ref': 'https://labs.inspirehep.net/api/literature/333333'}, 'number_of_pages': 6, 'titles': [{'source': 'JACoW', 'title': 'Towards a Fully Integrated Accelerator on a Chip: Dielectric Laser\n                Acceleration (DLA) From the Source to Relativistic Electrons\n            '}], '_fft': [{'version': 1, 'creation_datetime': '2017-06-27T09:43:17', 'description': '00013 Decomposition of the problematic rotation curves in our sample according to the best-fit \\textsc{core}NFW models. Colors and symbols are as in Figure \\ref{fig:dc14_fits}.', 'format': '.txt', 'path': '/home/spiros/REPOS/hepcrawl/files/full/31c54ddbaba4e949bf446bda0704adcc38491cdc.txt', 'type': 'Main', 'filename': 'cNFW_rogue_curves'}, {'version': 1, 'creation_datetime': '2017-06-27T09:43:16', 'description': '00005 Comparison of the parameters of the best-fit DC14 models to the cosmological halo mass-concentration relation from \\cite{dutton14} (left) and the stellar mass-halo mass relation from \\cite{behroozi13} (right). The error bars correspond to the extremal values of the multidimensional 68\\% confidence region for each fit. The theoretical relations are shown as red lines and their 1$\\sigma$ and 2$\\sigma$ scatter are represented by the dark and light grey bands, respectively. The mass-concentration relation from \\cite{maccio08} and the stellar mass-halo mass relation from \\cite{behroozi13} are also shown as the black dashed lines.', 'format': '.txt', 'path': '/home/spiros/REPOS/hepcrawl/files/full/84b2132efc3331fc95fd5ce9dc94f7939c8173eb.txt', 'type': 'Main', 'filename': 'scalingRelations_DutBeh_DC14_all_Oh'}], 'urls': [{'description': 'Fulltext', 'value': 'http://inspirehep.net/record/1608652/files/Towards a fully\n                integrated acc on a chip.pdf\n            '}], 'dois': [{'value': '10.18429/JACoW-IPAC2017-WEYB1'}], 'publication_info': [{'parent_isbn': '9783954501823'}, {'page_end': '2525', 'year': 2017, 'page_start': '2520'}], '$schema': 'hep.json', 'document_type': ['article'], 'abstracts': [{'source': 'Deutsches Elektronen-Synchrotron', 'value': 'Dielectric laser acceleration of electrons has recently been\n                demonstrated with significantly higher accelerating gradients than other\n                structure-based linear accelerators. Towards the development of an integrated 1 MeV\n                electron accelerator based on dielectric laser accelerator technologies,\n                development in several relevant technologies is needed. In this work, recent\n                developments on electron sources, bunching, accelerating, focussing, deflecting and\n                laser coupling structures are reported. With an eye to the near future, components\n                required for a 1 MeV kinetic energy tabletop accelerator producing sub-femtosecond\n                electron bunches are outlined.\n            '}]}
    2017-08-27 14:52:11 [desy] DEBUG: Validated item by Inspire Schemas.
    2017-08-27 14:52:11 [scrapy.core.scraper] DEBUG: Scraped from <200 file:///home/spiros/REPOS/hepcrawl/tests/functional/desy/fixtures/ftp_server/DESY/desy_no_namespace_collection_records.xml>
    {'acquisition_source': {'source': 'desy', 'method': 'hepcrawl', 'submission_number': '', 'datetime': '2017-08-27T14:52:11.081626'}, '_collections': ['Literature'], 'control_number': 444444, 'public_notes': [{'value': '*Brief entry*'}], 'self': {'$ref': 'https://labs.inspirehep.net/api/literature/444444'}, 'number_of_pages': 6, 'titles': [{'source': 'JACoW', 'title': 'Towards a Fully Integrated Accelerator on a Chip: Dielectric Laser\n                Acceleration (DLA) From the Source to Relativistic Electrons\n            '}], '_fft': [{'version': 1, 'creation_datetime': '2017-06-27T09:43:17', 'description': '00013 Decomposition of the problematic rotation curves in our sample according to the best-fit \\textsc{core}NFW models. Colors and symbols are as in Figure \\ref{fig:dc14_fits}.', 'format': '.txt', 'path': '/home/spiros/REPOS/hepcrawl/files/full/31c54ddbaba4e949bf446bda0704adcc38491cdc.txt', 'type': 'Main', 'filename': 'cNFW_rogue_curves'}, {'version': 1, 'creation_datetime': '2017-06-27T09:43:16', 'description': '00005 Comparison of the parameters of the best-fit DC14 models to the cosmological halo mass-concentration relation from \\cite{dutton14} (left) and the stellar mass-halo mass relation from \\cite{behroozi13} (right). The error bars correspond to the extremal values of the multidimensional 68\\% confidence region for each fit. The theoretical relations are shown as red lines and their 1$\\sigma$ and 2$\\sigma$ scatter are represented by the dark and light grey bands, respectively. The mass-concentration relation from \\cite{maccio08} and the stellar mass-halo mass relation from \\cite{behroozi13} are also shown as the black dashed lines.', 'format': '.txt', 'path': '/home/spiros/REPOS/hepcrawl/files/full/84b2132efc3331fc95fd5ce9dc94f7939c8173eb.txt', 'type': 'Main', 'filename': 'scalingRelations_DutBeh_DC14_all_Oh'}], 'urls': [{'description': 'Fulltext', 'value': 'http://inspirehep.net/record/1608652/files/Towards a fully\n                integrated acc on a chip.pdf\n            '}], 'dois': [{'value': '10.18429/JACoW-IPAC2017-WEYB1'}], 'publication_info': [{'parent_isbn': '9783954501823'}, {'page_end': '2525', 'year': 2017, 'page_start': '2520'}], '$schema': 'hep.json', 'document_type': ['article'], 'abstracts': [{'source': 'Deutsches Elektronen-Synchrotron', 'value': 'Dielectric laser acceleration of electrons has recently been\n                demonstrated with significantly higher accelerating gradients than other\n                structure-based linear accelerators. Towards the development of an integrated 1 MeV\n                electron accelerator based on dielectric laser accelerator technologies,\n                development in several relevant technologies is needed. In this work, recent\n                developments on electron sources, bunching, accelerating, focussing, deflecting and\n                laser coupling structures are reported. With an eye to the near future, components\n                required for a 1 MeV kinetic energy tabletop accelerator producing sub-femtosecond\n                electron bunches are outlined.\n            '}]}
    2017-08-27 14:52:11 [desy] DEBUG: Validated item by Inspire Schemas.
    2017-08-27 14:52:11 [scrapy.core.scraper] DEBUG: Scraped from <200 file:///home/spiros/REPOS/hepcrawl/tests/functional/desy/fixtures/ftp_server/DESY/desy_collection_records.xml>
    {'acquisition_source': {'source': 'desy', 'method': 'hepcrawl', 'submission_number': '', 'datetime': '2017-08-27T14:52:11.098980'}, '_collections': ['Literature'], 'control_number': 111111, 'public_notes': [{'value': '*Brief entry*'}], 'self': {'$ref': 'https://labs.inspirehep.net/api/literature/111111'}, 'number_of_pages': 6, 'titles': [{'source': 'JACoW', 'title': 'Towards a Fully Integrated Accelerator on a Chip: Dielectric Laser\n                Acceleration (DLA) From the Source to Relativistic Electrons\n            '}], '_fft': [{'version': 1, 'creation_datetime': '2017-06-27T09:43:17', 'description': '00013 Decomposition of the problematic rotation curves in our sample according to the best-fit \\textsc{core}NFW models. Colors and symbols are as in Figure \\ref{fig:dc14_fits}.', 'format': '.txt', 'path': '/home/spiros/REPOS/hepcrawl/files/full/31c54ddbaba4e949bf446bda0704adcc38491cdc.txt', 'type': 'Main', 'filename': 'cNFW_rogue_curves'}, {'version': 1, 'creation_datetime': '2017-06-27T09:43:16', 'description': '00005 Comparison of the parameters of the best-fit DC14 models to the cosmological halo mass-concentration relation from \\cite{dutton14} (left) and the stellar mass-halo mass relation from \\cite{behroozi13} (right). The error bars correspond to the extremal values of the multidimensional 68\\% confidence region for each fit. The theoretical relations are shown as red lines and their 1$\\sigma$ and 2$\\sigma$ scatter are represented by the dark and light grey bands, respectively. The mass-concentration relation from \\cite{maccio08} and the stellar mass-halo mass relation from \\cite{behroozi13} are also shown as the black dashed lines.', 'format': '.txt', 'path': '/home/spiros/REPOS/hepcrawl/files/full/84b2132efc3331fc95fd5ce9dc94f7939c8173eb.txt', 'type': 'Main', 'filename': 'scalingRelations_DutBeh_DC14_all_Oh'}], 'urls': [{'description': 'Fulltext', 'value': 'http://inspirehep.net/record/1608652/files/Towards a fully\n                integrated acc on a chip.pdf\n            '}], 'dois': [{'value': '10.18429/JACoW-IPAC2017-WEYB1'}], 'publication_info': [{'parent_isbn': '9783954501823'}, {'page_end': '2525', 'year': 2017, 'page_start': '2520'}], '$schema': 'hep.json', 'document_type': ['article'], 'abstracts': [{'source': 'Deutsches Elektronen-Synchrotron', 'value': 'Dielectric laser acceleration of electrons has recently been\n                demonstrated with significantly higher accelerating gradients than other\n                structure-based linear accelerators. Towards the development of an integrated 1 MeV\n                electron accelerator based on dielectric laser accelerator technologies,\n                development in several relevant technologies is needed. In this work, recent\n                developments on electron sources, bunching, accelerating, focussing, deflecting and\n                laser coupling structures are reported. With an eye to the near future, components\n                required for a 1 MeV kinetic energy tabletop accelerator producing sub-femtosecond\n                electron bunches are outlined.\n            '}]}
    2017-08-27 14:52:11 [desy] DEBUG: Validated item by Inspire Schemas.
    2017-08-27 14:52:11 [scrapy.core.scraper] DEBUG: Scraped from <200 file:///home/spiros/REPOS/hepcrawl/tests/functional/desy/fixtures/ftp_server/DESY/desy_collection_records.xml>
    {'acquisition_source': {'source': 'desy', 'method': 'hepcrawl', 'submission_number': '', 'datetime': '2017-08-27T14:52:11.116105'}, '_collections': ['Literature'], 'control_number': 222222, 'public_notes': [{'value': '*Brief entry*'}], 'self': {'$ref': 'https://labs.inspirehep.net/api/literature/222222'}, 'number_of_pages': 6, 'titles': [{'source': 'JACoW', 'title': 'Towards a Fully Integrated Accelerator on a Chip: Dielectric Laser\n                Acceleration (DLA) From the Source to Relativistic Electrons\n            '}], '_fft': [{'version': 1, 'creation_datetime': '2017-06-27T09:43:17', 'description': '00013 Decomposition of the problematic rotation curves in our sample according to the best-fit \\textsc{core}NFW models. Colors and symbols are as in Figure \\ref{fig:dc14_fits}.', 'format': '.txt', 'path': '/home/spiros/REPOS/hepcrawl/files/full/31c54ddbaba4e949bf446bda0704adcc38491cdc.txt', 'type': 'Main', 'filename': 'cNFW_rogue_curves'}, {'version': 1, 'creation_datetime': '2017-06-27T09:43:16', 'description': '00005 Comparison of the parameters of the best-fit DC14 models to the cosmological halo mass-concentration relation from \\cite{dutton14} (left) and the stellar mass-halo mass relation from \\cite{behroozi13} (right). The error bars correspond to the extremal values of the multidimensional 68\\% confidence region for each fit. The theoretical relations are shown as red lines and their 1$\\sigma$ and 2$\\sigma$ scatter are represented by the dark and light grey bands, respectively. The mass-concentration relation from \\cite{maccio08} and the stellar mass-halo mass relation from \\cite{behroozi13} are also shown as the black dashed lines.', 'format': '.txt', 'path': '/home/spiros/REPOS/hepcrawl/files/full/84b2132efc3331fc95fd5ce9dc94f7939c8173eb.txt', 'type': 'Main', 'filename': 'scalingRelations_DutBeh_DC14_all_Oh'}], 'urls': [{'description': 'Fulltext', 'value': 'http://inspirehep.net/record/1608652/files/Towards a fully\n                integrated acc on a chip.pdf\n            '}], 'dois': [{'value': '10.18429/JACoW-IPAC2017-WEYB1'}], 'publication_info': [{'parent_isbn': '9783954501823'}, {'page_end': '2525', 'year': 2017, 'page_start': '2520'}], '$schema': 'hep.json', 'document_type': ['article'], 'abstracts': [{'source': 'Deutsches Elektronen-Synchrotron', 'value': 'Dielectric laser acceleration of electrons has recently been\n                demonstrated with significantly higher accelerating gradients than other\n                structure-based linear accelerators. Towards the development of an integrated 1 MeV\n                electron accelerator based on dielectric laser accelerator technologies,\n                development in several relevant technologies is needed. In this work, recent\n                developments on electron sources, bunching, accelerating, focussing, deflecting and\n                laser coupling structures are reported. With an eye to the near future, components\n                required for a 1 MeV kinetic energy tabletop accelerator producing sub-femtosecond\n                electron bunches are outlined.\n            '}]}
    2017-08-27 14:52:11 [scrapy.core.engine] INFO: Closing spider (finished)
    2017-08-27 14:52:11 [scrapy.statscollectors] INFO: Dumping Scrapy stats:
    {'downloader/request_bytes': 1215,
     'downloader/request_count': 4,
     'downloader/request_method_count/GET': 4,
     'downloader/response_bytes': 18303,
     'downloader/response_count': 4,
     'downloader/response_status_count/200': 4,
     'file_count': 2,
     'file_status_count/downloaded': 2,
     'finish_reason': 'finished',
     'finish_time': datetime.datetime(2017, 8, 27, 12, 52, 11, 132914),
     'item_scraped_count': 4,
     'log_count/DEBUG': 21,
     'log_count/INFO': 7,
     'memusage/max': 98328576,
     'memusage/startup': 98328576,
     'response_received_count': 4,
     'scheduler/dequeued': 2,
     'scheduler/dequeued/disk': 2,
     'scheduler/enqueued': 2,
     'scheduler/enqueued/disk': 2,
     'start_time': datetime.datetime(2017, 8, 27, 12, 52, 10, 841575)}
    2017-08-27 14:52:11 [scrapy.core.engine] INFO: Spider closed (finished)

.. tip::

    If we run the spider using the ``scrapyd`` application then this log file is stored in a
    directory like: ``~/path_to_repo/hepcrawl/logs/[project=hepcrawl]/[spider=desy]/[job_id].log``

.. tip::

    Try to set logging logic in the project.

    If we need to add logs in a spider we just write:

    .. code-block:: python

        self.log('This is a log message from a spider: Try to crawl local file: {variable}'.format(**vars))


    If we need to add logs in pipeline we have to use:

    .. code-block:: python

        import logging
        logger = logging.getLogger(__name__)
        logger.log(logging.INFO, 'This is a log message from pipelines: {variable}'.format(**vars))


Using debugger
++++++++++++++

We can use a debugger like ``ipdb`` by writting the following code in the module that we would like
to debug:

.. code-block:: python

    import ipdb
    ipdb.set_trace()


Afterwords, by running our spider the debugger will be opened for debugging at the line of the code
that we putted the above code lines.

.. tip::

    If we run our spider by using:

    .. code-block:: console

        $ scrapy crawl desy 'source_folder=/path/to/sample_dir'

    Then the debugger is enabled in the same terminal session. Otherwise if we run our spider by
    using ``docker`` we have to find the running container ``id`` or ``name`` of the spider and then
    access it via the following command:

    .. code-block:: console

        $ docker exec -it [``container_id`` or ``container_name``] /bin/bash


Using docker-compose log file
+++++++++++++++++++++++++++++

If we have to debug our spider inside her environment (celery, rabbitmq, https or ftp server, etc.)
by using ``docker-compose`` file we can access the log file of all the containers in this docker-compose
file by the following command:

    .. code-block:: console

        $ docker-compose -f [docker-compose file].yml logs -f
