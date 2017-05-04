..
    This file is part of hepcrawl.
    Copyright (C) 2015, 2016, 2017 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.

.. currentmodule:: hepcrawl


Developers Guide
================

Spiders in HEPcrawl
-------------------

Here is a introduction to spiders: http://doc.scrapy.org/en/latest/topics/spiders.html

See also the official spider `tutorial`_ for Scrapy.

Spiders are classes which inherit from Scrapy Spider classes and contains the main
logic of retrieval of content from the source and the extraction of metadata
from the source records. All spiders are located under ``spiders/`` folder and
follows the naming standard `mysource_spider.py`.

Traditionally, we receive metadata in XML format so our spiders usually inherit
from a special XML parsing spider from Scrapy called ``XMLFeedSpider``.

.. code-block:: python

    from scrapy.spiders import XMLFeedSpider

    class MySpider(XMLFeedSpider):

        name = "myspider"
        itertag = 'article'  # XML tag to iterate over within each XML file

        def start_requests(self):
            # Retrieval of all data

        def parse_node(self, response, node):
            # extraction from XML per record


When you create a new spider, you need to implement at least two methods:

   * `start_requests`: get the content from the source
   * `parse_node`: extract the metadata from the downloaded content into a record


Getting data with ``start_requests``
------------------------------------

``start_requests`` handles the retrieval of data from the source,
and `yield`_ each record(s) file (in this case XML file). You can even chain
these requests to do things like `following links`_.

For example in the World Scientific use case, we need to:

   1. Connect to a FTP server and get ZIP files
   2. For each ZIP file, extract it's contents and parse every XML

So our ``start_requests`` function is first checking a remote FTP server for
newly added zip files and yield's the full FTP path to the zip file to Scrapy.
Scrapy knows how to download things from an FTP and gets each zip file. While
yielding we also tell Scrapy to call another function (``handle_package``)
for each zip file. This is called a `callback`_ function and it is necessary to
do step 2. from above.

This function then extracts all XML files from the zip files and finally `yield`
each XML file (without any more callbacks) to Scrapy which now calls ``parse_node``
and extracting metadata from a single XML file can finally begin.

.. _callback: http://doc.scrapy.org/en/latest/topics/request-response.html?highlight=callback
.. _yield: http://anandology.com/python-practice-book/iterators.html#generators
.. _following links: http://doc.scrapy.org/en/latest/intro/tutorial.html#following-links
.. _tutorial: http://doc.scrapy.org/en/latest/intro/tutorial.html#our-first-spider

Creating records in ``parse_node``
----------------------------------

``parse_node`` handles the extraction of records for a ``XMLFeedSpider``
into so-called `items`_. An item is basically a intermediate record object
where the data from the XML is put into.

The function iterates over the XML tag specified in ``itertag``, which means
that it supports multiple records inside a single XML file.

The goal of the ``parse_node`` function is to generate a ``HEPRecord``, which in
the Scrapy world is called item. This is defined in ``items.py`` and is an
**intermediate** format of the record metadata that is extracted from every
source. It tries to resemble the HEP JSON Schema as closely as
feasible, with some exceptions.

.. code-block:: python

    class HEPRecord(scrapy.Item):

        title = scrapy.Field()
        abstract = scrapy.Field()
        page_nr = scrapy.Field()
        journal_artid = scrapy.Field()
        # etc..


To do the extraction, you are given a ``node`` object which is a `selector`_ on
the XML record. You can now xpath (and even css) to extract content directly
into the item, via some helper functions:

.. code-block:: python

    def parse_node(self, response, node):
        """Parse a XML file into a HEP record."""

        # for simplicity, remove all namespaces (optional)
        node.remove_namespaces()

        # Create a HEPRecord object with an special loader (more on this later)
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        record.add_xpath('page_nr', "//counts/page-count/@count")
        record.add_xpath('abstract', '//abstract[1]')
        record.add_xpath('title', '//article-title/text()')

        return record.load_item()


Here you see that you can directly assign a value to the ``HEPRecord`` via
the ``add_xpath`` function, but you are not forced to do so:

.. code-block:: python

    fpage = node.xpath('.//fpage/text()').extract()
    lpage = node.xpath('.//lpage/text()').extract()
    if fpage:
        record.add_value('journal_fpage', fpage)
    if lpage:
        record.add_value('journal_lpage', lpage)


NOTE: The value added when using ``add_xpath`` usually resolves into a Python list of values.
So remember that you need to deal with lists.

Using the ``add_value`` you can add the value you want to a field when you need
to do some extra logic.


.. _items: http://doc.scrapy.org/en/latest/topics/items.html
.. _selector: http://doc.scrapy.org/en/latest/topics/selectors.html


Re-using common metadata handling using item loaders
----------------------------------------------------

Since INSPIRE has multiple sources of content we will need to have multiple spiders
that retrieves and extracts data differently. However, the intermediate ``HEPRecord``
is the common output of all sources.

This means that any additional metadata handling, such as converting journal titles
or author names to the correct format can be done in one place only. This is managed
in the ``HEPLoader`` `item loader`_ located in ``loaders.py``.

The loader defines the `input and output processors`_ for the ``HEPRecord`` item.
The input processor processes the extracted data as soon as it’s received
(through the add_xpath(), add_css() or add_value() methods). The output processor
takes the data processed by the input processors and assigns them to the field in
the item.

For example, a ``HEPRecord`` has a field called ``abstract`` for the abstract. We want
to take the incoming abstract string and convert some HTML tags to their LaTeX
counterparts. First we define our input processor inside ``inputs.py``:

.. code-block:: python

    def convert_html_subscripts_to_latex(text):
        """Convert some HTML tags to latex equivalents."""
        text = re.sub("<sub>(.*?)</sub>", r"$_{\1}$", text)
        text = re.sub("<sup>(.*?)</sup>", r"$^{\1}$", text)
        return text


Then we add our input processor to the ``HEPLoader``:


.. code-block:: python

    from scrapy.loader.processors import MapCompose
    from .inputs import convert_html_subscripts_to_latex

    class HEPLoader(ItemLoader):

        abstract_in = MapCompose(
            convert_html_subscripts_to_latex,
            unicode.strip,
        )


To automatically link the input processors to the correct item field, we add the
suffix ``_in`` to the field name. Then we use a special processor called
``MapCompose`` which takes functions as parameters and they will each be called
with each value in the field.

.. code-block:: python

    record.add_xpath('abstract', '//abstract[1]')

will add a list with one item:

.. code-block:: python

    [".. some abstract from the XML .."]

The input processors like `convert_html_subscripts_to_latex` is then called
with ``".. some abstract from the XML .."`` (per value, not the whole list).

.. _item loader: http://doc.scrapy.org/en/latest/topics/loaders.html
.. _input and output processors: http://doc.scrapy.org/en/latest/topics/loaders.html#declaring-input-and-output-processors

We can also define output processors to control how the values are assigned to the fields
in the items. For example, instead of a list only assign the first value in the list:


.. code-block:: python

    from scrapy.loader.processors import MapCompose, TakeFirst
    from .inputs import convert_html_subscripts_to_latex

    class HEPLoader(ItemLoader):

        abstract_in = MapCompose(
            convert_html_subscripts_to_latex,
            unicode.strip,
        )
        abstract_out = TakeFirst()


Take a look `here`_ for some useful concepts when dealing with item loaders.

.. _here: http://doc.scrapy.org/en/latest/topics/loaders.html#reusing-and-extending-item-loaders


Exporting the final record with item pipelines
----------------------------------------------

Finally, the data in the items are exported to INSPIRE via special item pipelines.

These classes are located under ``pipelines.py`` and exports harvested records to
JSON files and pushes them to INSPIRE-HEP.

**This documentation is still work in progress**
