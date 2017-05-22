# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for EDP Sciences."""

from __future__ import absolute_import, division, print_function

import os
import urlparse
import tarfile
from tempfile import mkdtemp

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from ..extractors.jats import Jats
from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import (
    ftp_list_files,
    ftp_connection_info,
    get_first,
    get_journal_and_section,
    get_license,
    get_node,
    parse_domain,
)


class EDPSpider(Jats, XMLFeedSpider):
    """EDP Sciences crawler.

    This spider connects to a given FTP hosts and downloads zip files with
    XML files for extraction into HEP records.

    This means that it generates the URLs for Scrapy to crawl in a special way:

    1. First it connects to a FTP host and lists all the new TAR files found
       on the remote server and downloads them to a designated local folder,
       using ``EDPSpider.start_requests()``. The starting point of the crawl can also be a
       local file. Packages contain XML files with different formats (``gz`` package
       is ``JATS``, ``bz2`` package has ``rich`` and ``jp`` format XML files, ``jp`` is ``JATS``.)

    2. Then the TAR file is unpacked and it lists all the XML files found
       inside, via ``EDPSpider.handle_package()``. Note the callback from
       ``EDPSpider.start_requests()``.

    3. Each XML file is parsed via ``EDPSpider.parse_node()``.

    4. PDF file is fetched from the web page in ``EDPSpider.scrape_for_pdf()``.

    5. Finally, ``HEPRecord`` is created in ``EDPSpider.build_item()``.

    Examples:
        To run an ``EDPSpider``, you need to pass FTP connection information via
        ``ftp_netrc`` file::

            $ scrapy crawl EDP -a ftp_netrc=tmp/edps_netrc

        To run an ``EDPSpider`` using ``rich`` format::

            $ scrapy crawl EDP -a package_path=file://`pwd`/tests/responses/edp/test_rich.tar.bz2

        To run an ``EDPSpider`` using ``gz`` format::

            $ scrapy crawl EDP -a package_path=file://`pwd`/tests/responses/edp/test_gz.tar.gz

    Todo:

     Sometimes there are errors:

        .. code-block:: python

            Unhandled Error
            self.f.seek(-size-self.SIZE_SIZE, os.SEEK_END)
            exceptions.IOError: [Errno 22] Invalid argument

        OR

        .. code-block:: python

            ConnectionLost: ('FTP connection lost',
            <twisted.python.failure.Failure twisted.internet.error.ConnectionDone:
            Connection was closed cleanly.>)

        See old harvesting-kit:

            * https://github.com/inspirehep/harvesting-kit/blob/master/harvestingkit/edpsciences_package.py
            * https://github.com/inspirehep/inspire/blob/master/bibtasklets/bst_edpsciences_harvest.py
    """
    name = 'EDP'
    custom_settings = {}
    start_urls = []
    iterator = 'xml'
    itertag = 'article'
    download_delay = 10
    custom_settings = {'MAX_CONCURRENT_REQUESTS_PER_DOMAIN': 2}

    allowed_article_types = [
        'research-article',
        'corrected-article',
        'original-article',
        'introduction',
        'letter',
        'correction',
        'addendum',
        'review-article',
        'rapid-communications',
        'Article',
        'Erratum',
    ]

    OPEN_ACCESS_JOURNALS = {
        'EPJ Web of Conferences'
    }

    def __init__(self, package_path=None, ftp_folder="incoming", ftp_netrc=None, *args, **kwargs):
        """Construct EDP spider.

        :param package_path: path to local tar.gz or tar.bz2 package.
        :param ftp_folder: path on remote ftp server.
        :param ftp_netrc: path to netrc file.
        """
        super(EDPSpider, self).__init__(*args, **kwargs)
        self.ftp_folder = ftp_folder
        self.ftp_host = "ftp.edpsciences.org"
        self.ftp_netrc = ftp_netrc
        self.target_folder = mkdtemp(prefix='EDP_', dir='/tmp/')
        self.package_path = package_path
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)

    def start_requests(self):
        """List selected folder on remote FTP and yield new zip files."""
        if self.package_path:
            yield Request(self.package_path, callback=self.handle_package_file)
        else:
            ftp_host, ftp_params = ftp_connection_info(
                self.ftp_host, self.ftp_netrc)
            _, new_files = ftp_list_files(
                self.ftp_folder,
                self.target_folder,
                server=ftp_host,
                user=ftp_params['ftp_user'],
                password=ftp_params['ftp_password']
            )
            for remote_file in new_files:
                # Cast to byte-string for scrapy compatibility
                remote_file = str(remote_file)
                ftp_params["ftp_local_filename"] = os.path.join(
                    self.target_folder,
                    os.path.basename(remote_file)
                )
                remote_url = "ftp://{0}/{1}".format(ftp_host, remote_file)
                yield Request(
                    str(remote_url),
                    meta=ftp_params,
                    callback=self.handle_package_ftp
                )

    def handle_package_ftp(self, response):
        """Handle remote packages and yield every XML found."""
        self.logger.info("Visited %s" % response.url)
        zip_filepath = response.body
        zip_target_folder, _ = os.path.splitext(zip_filepath)
        if "tar" in zip_target_folder:
            zip_target_folder, _ = os.path.splitext(zip_target_folder)
        xml_files = self.untar_files(zip_filepath, zip_target_folder)
        for xml_file in xml_files:
            yield Request(
                "file://{0}".format(xml_file),
                meta={"package_path": zip_filepath}
            )

    def handle_package_file(self, response):
        """Handle a local package and yield every XML found."""
        zip_filepath = urlparse.urlsplit(response.url).path
        zip_target_folder, _ = os.path.splitext(zip_filepath)
        if "tar" in zip_target_folder:
            zip_target_folder, _ = os.path.splitext(zip_target_folder)
        xml_files = self.untar_files(zip_filepath, zip_target_folder)
        for xml_file in xml_files:
            request = Request(
                "file://{0}".format(xml_file),
                meta={"package_path": zip_filepath}
            )
            if "xml_rich" in xml_file:
                request.meta["rich"] = True
                self.itertag = "EDPSArticle"
            yield request

    @staticmethod
    def untar_files(zip_filepath, target_folder, flatten=False):
        """Unpack the tar.gz or tar.bz2 package and return XML file paths."""
        xml_files = []
        with tarfile.open(zip_filepath) as tar:
            for filename in tar.getmembers():
                if filename.path.endswith(".xml"):
                    if flatten:
                        filename.name = os.path.basename(filename.name)
                    absolute_path = os.path.join(target_folder, filename.path)
                    if not os.path.exists(absolute_path):
                        tar.extract(filename, path=target_folder)
                    xml_files.append(absolute_path)

        return xml_files

    def parse_node(self, response, node):
        """Parse the XML file and yield a request to scrape for the PDF."""
        node.remove_namespaces()
        if response.meta.get("rich"):
            article_type = node.xpath('./ArticleID/@Type').extract_first()
            dois = node.xpath('.//DOI/text()').extract()
            date_published = self._get_date_published_rich(node)
            journal_title = node.xpath(
                './/JournalShortTitle/text()|//JournalTitle/text()').extract_first()
        else:
            article_type = node.xpath('@article-type').extract_first()
            dois = node.xpath(
                './/article-id[@pub-id-type="doi"]/text()').extract()
            date_published = self._get_published_date(node)
            journal_title = node.xpath(
                './/abbrev-journal-title/text()|//journal-title/text()').extract_first()

        self.logger.info("Got article_type {0}".format(article_type))
        if article_type is None or article_type not in self.allowed_article_types:
            # Filter out non-interesting article types
            return None

        if dois and journal_title in self.OPEN_ACCESS_JOURNALS:
            # We should get the pdf only for open access journals
            link = "http://dx.doi.org/" + dois[0]
            request = Request(link, callback=self.scrape_for_pdf)
            request.meta["record"] = node.extract()
            request.meta["article_type"] = article_type
            request.meta["dois"] = dois
            request.meta["rich"] = response.meta.get("rich")
            request.meta["date_published"] = date_published
            request.meta["journal_title"] = journal_title
            return request
        else:
            response.meta["record"] = node.extract()
            response.meta["article_type"] = article_type
            response.meta["dois"] = dois
            response.meta["date_published"] = date_published
            response.meta["journal_title"] = journal_title
            if response.meta.get("rich"):
                return self.build_item_rich(response)
            else:
                return self.build_item_jats(response)

    def scrape_for_pdf(self, response):
        """Try to find the fulltext pdf from the web page."""
        pdf_links = []
        all_links = response.xpath(
            '//a[contains(@href, "pdf")]/@href').extract()
        domain = parse_domain(response.url)
        pdf_links = sorted(list(set(
            [urlparse.urljoin(domain, link) for link in all_links])))

        response.meta["pdf_links"] = pdf_links
        response.meta["urls"] = [response.url]
        if response.meta.get("rich"):
            return self.build_item_rich(response)
            # NOTE: actually this might not be desirable
            # as publications with this format are not open access
        else:
            return self.build_item_jats(response)

    def build_item_rich(self, response):
        """Build the final HEPRecord with "rich" format XML."""
        node = get_node(response.meta["record"])
        article_type = response.meta.get("article_type")
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        record.add_value('dois', response.meta.get("dois"))
        record.add_xpath('abstract', './/Abstract')
        record.add_xpath('title', './/ArticleTitle/Title')
        record.add_xpath('subtitle', './/ArticleTitle/Subtitle')
        record.add_value('authors', self._get_authors_rich(node))
        record.add_xpath('free_keywords', './/Subject/Keyword/text()')

        record.add_value('journal_title', response.meta['journal_title'])
        record.add_xpath('journal_issue', './/Issue/text()')
        record.add_xpath('journal_volume', './/Volume/text()')
        fpage = node.xpath('.//FirstPage/text()').extract_first()
        lpage = node.xpath('.//LastPage/text()').extract_first()
        record.add_value('journal_fpage', fpage)
        record.add_value('journal_lpage', lpage)
        if fpage and lpage:
            record.add_value('page_nr', str(int(lpage) - int(fpage) + 1))

        journal_year = node.xpath('.//IssueID/Year/text()').extract()
        if journal_year:
            record.add_value('journal_year', int(journal_year[0]))
        record.add_value('date_published', response.meta['date_published'])

        record.add_xpath('copyright_holder', './/Copyright/text()')
        record.add_value('collections', self._get_collections(
            node, article_type, response.meta['journal_title']))

        if "pdf_links" in response.meta:
            # NOTE: maybe this should be removed as the 'rich' format records
            # are not open access.
            record.add_value(
                "additional_files",
                self._create_fft_file(
                    get_first(response.meta["pdf_links"]),
                    "INSPIRE-PUBLIC",
                    "Fulltext"
                )
            )
        record.add_value("urls", response.meta.get("urls"))

        return record.load_item()

    def build_item_jats(self, response):
        """Build the final HEPRecord with JATS-format XML ('jp')."""
        node = get_node(response.meta["record"])
        article_type = response.meta.get("article_type")

        record = HEPLoader(item=HEPRecord(), selector=node, response=response)
        if article_type in ['correction',
                            'addendum']:
            record.add_xpath('related_article_doi',
                             './/related-article[@ext-link-type="doi"]/@href')
            record.add_value('journal_doctype', article_type)

        record.add_value('dois', response.meta.get("dois"))
        record.add_xpath('page_nr', ".//counts/page-count/@count")
        record.add_xpath('abstract', './/abstract[1]')
        record.add_xpath('title', './/article-title/text()')
        record.add_xpath('subtitle', './/subtitle/text()')
        record.add_value('authors', self._get_authors_jats(node))
        record.add_xpath('collaborations', ".//contrib/collab/text()")

        free_keywords, classification_numbers = self._get_keywords(node)
        record.add_value('free_keywords', free_keywords)
        record.add_value('classification_numbers', classification_numbers)

        record.add_value('journal_title', response.meta['journal_title'])
        record.add_xpath('journal_issue', './/front//issue/text()')
        record.add_xpath('journal_volume', './/front//volume/text()')
        record.add_xpath('journal_artid', './/elocation-id/text()')

        fpage = node.xpath('.//front//fpage/text()').extract()
        lpage = node.xpath('.//front//lpage/text()').extract()
        record.add_value('journal_fpage', fpage)
        record.add_value('journal_lpage', lpage)

        date_published = response.meta['date_published']
        record.add_value('journal_year', int(date_published[:4]))
        record.add_value('date_published', date_published)

        record.add_xpath('copyright_holder', './/copyright-holder/text()')
        record.add_xpath('copyright_year', './/copyright-year/text()')
        record.add_xpath('copyright_statement',
                         './/copyright-statement/text()')
        record.add_value('copyright_material', 'Article')

        license = get_license(
            license_url=node.xpath(
                './/license/license-p/ext-link/@href'
            ).extract_first()
        )
        record.add_value('license', license)

        record.add_value('collections', self._get_collections(
            node, article_type, response.meta['journal_title']))

        if "pdf_links" in response.meta:
            record.add_value(
                "additional_files",
                self._create_fft_file(
                    get_first(response.meta["pdf_links"]),
                    "INSPIRE-PUBLIC",
                    "Fulltext"
                )
            )
        record.add_value("urls", response.meta.get("urls"))

        references = self._get_references(node)
        record.add_value("references", references)

        return record.load_item()

    def _get_references(self, node):
        """Get the references."""
        # NOTE: this is *almost* the same as in APS spider or JATS extractor
        references = []
        ref_list = node.xpath("//ref-list//ref")
        references = []

        for reference in ref_list:
            label = reference.xpath("./label/text()").extract_first()
            if label:
                label = label.strip("[].")
            inner_refs = reference.xpath(".//mixed-citation")
            if not inner_refs:
                references.append(self._parse_reference(reference, label))  # FIXME: test missing, we might be testing this in APS
            for in_ref in inner_refs:
                references.append(self._parse_reference(in_ref, label))

        return references

    def _parse_reference(self, ref, label):
        """Parse a reference."""
        reference = {}
        # FIXME: get only raw references?
        raw_reference = ref.extract()

        sublabel = ref.xpath("./@id").extract_first()
        if label:
            # If multiple references under one label:
            if sublabel:
                sublabel = sublabel[-1]
                label = label + sublabel
        reference['number'] = label  # NOTE: this should not be int

        ref_type = ref.xpath("./@publication-type").extract_first()
        doi, urls = self._get_external_links(ref)
        collaboration = ref.xpath(".//collab/text()").extract_first()

        # FIXME: do we want authors be a string or a list of raw author names?
        # In Elsevier spider it's a specially formatted string.
        # Here it's just a list.
        authors = []
        authors_raw = ref.xpath('.//string-name')
        for author_group in authors_raw:
            surname = author_group.xpath('.//surname/text()').extract_first()
            firstnames = author_group.xpath('.//given-names/text()').extract_first()
            authors.append(surname + ", " + firstnames)

        title = ref.xpath(".//article-title/text()").extract_first()
        publication = ref.xpath(".//source/text()").extract_first()
        fpage = ref.xpath(".//fpage/text()").extract_first()
        issue = ref.xpath(".//issue/text()").extract_first()
        volume = ref.xpath(".//volume/text()").extract_first()
        year = ref.xpath(".//year/text()").extract_first()
        publisher = ref.xpath('.//publisher-name/text()').extract_first()
        publisher_loc = ref.xpath(
            './/publisher-loc/text()').extract_first()
        if not publisher_loc:
            publisher_loc = ref.xpath('.//publisher-name/following-sibling::text()[1]').extract_first()
        if publisher and publisher_loc:
            publisher = publisher_loc.strip(",. ") + ': ' + publisher

        # Construct the reference dict
        journal_title = ''
        if publication:
            journal_title, section = get_journal_and_section(publication)
            if journal_title:
                reference['journal_title'] = journal_title
                if volume:
                    volume = section + volume
                    reference['journal_volume'] = volume
        if ref_type:
            reference['doctype'] = ref_type
        if urls:
            reference['url'] = urls
        if doi:
            reference['doi'] = doi
        if fpage:
            reference['fpage'] = fpage
        if title:
            reference['title'] = title
        if issue:
            reference['issue'] = issue
        if year:
            reference['year'] = year
        if authors:
            reference['authors'] = authors
        if collaboration:
            reference['collaboration'] = collaboration
        if publisher:
            reference['publisher'] = publisher
        if raw_reference:
            reference['raw_reference'] = raw_reference

        return reference

    def _get_external_links(self, ref):
        """Get and format DOI and other external links."""
        ext_links = ref.xpath('.//ext-link/@href').extract()
        doi = ""
        urls = []
        for ext_link in ext_links:
            if "doi" in ext_link:
                doi = "doi:" + ext_link.replace("http://dx.doi.org/", "")
            else:
                urls.append(ext_link)

        return doi, urls

    def _get_date_published_rich(self, node):
        """Get published date."""
        date_published = ""
        year = node.xpath('.//Year/text()').extract_first()
        month = node.xpath('.//MonthNumber/text()').extract_first()
        if year:
            date_published = year
            if month:
                date_published += "-" + month
        return date_published

    def _get_collections(self, node, article_type, current_journal_title):
        """Return this articles' collection."""
        conference = node.xpath('.//conference').extract()
        if conference or current_journal_title == "International Journal of Modern Physics: Conference Series":
            return ['HEP', 'ConferencePaper']
        elif article_type == "review-article":
            return ['HEP', 'Review']
        else:
            return ['HEP', 'Published']

    def _get_authors_jats(self, node):
        """Get authors and return formatted dictionary.

        Note that the `get_authors` in JATS extractor doesn't work here.
        """
        authors = []
        for contrib in node.xpath('.//contrib[@contrib-type="author"]'):
            surname = contrib.xpath('name/surname/text()').extract()
            given_names = contrib.xpath('name/given-names/text()').extract()
            email = contrib.xpath('email/text()').extract_first()

            affs_raw = contrib.xpath('aff')
            affiliations = []
            reffered_id = contrib.xpath('xref[@ref-type="aff"]/@rid').extract()
            if reffered_id:
                aff = node.xpath('.//aff[@id="{0}"]/addr-line/institution/text()'.format(
                    get_first(reffered_id))).extract()
                if not aff:
                    aff = node.xpath('.//aff[@id="{0}"]/addr-line/text()'.format(
                        get_first(reffered_id))).extract()
                affs_raw += aff
            if affs_raw:
                affs_raw_no_email = []
                for aff_raw in affs_raw:
                    # Take e-mail from affiliation string
                    # FIXME: There is only one affiliation and email line per
                    # institution. The result is that every author will receive
                    # the email of the contact person as their own.
                    # There might also be a list of emails of all the authors.
                    if "e-mail" in aff_raw:
                        split_aff = aff_raw.split("e-mail")
                        affs_raw_no_email.append(split_aff[0].strip())
                        # FIXME: solution: strip the email but don't add it
                        # to 'email' key?
                        # if not email:  # uncomment if you want to add it after all
                        #    email = [split_aff[1].strip(": \n")]
                if affs_raw_no_email:
                    affs_raw = affs_raw_no_email
                affiliations = [{'value': aff} for aff in affs_raw]
            authors.append({
                'surname': get_first(surname, ""),
                'given_names': get_first(given_names, ""),
                'affiliations': affiliations,
                'email': email,
            })

        return authors

    def _get_authors_rich(self, node):
        """Get authors and return formatted dictionary."""
        authors = []
        for contrib in node.xpath('.//Author'):
            surname = contrib.xpath(
                'AuthorName//LastName/text()').extract_first()
            fname = contrib.xpath(
                'AuthorName//FirstName/text()').extract_first()
            mname = contrib.xpath(
                'AuthorName//MiddleName/text()').extract_first()
            given_names = ""
            if fname:
                given_names = fname
                if mname:
                    given_names += " " + mname
            affiliations = []
            reffered_id = contrib.xpath('AffiliationID/@Label').extract_first()
            if reffered_id:
                aff_raw = node.xpath(
                    './/Affiliation[@ID="{0}"]/UnstructuredAffiliation/text()'.format(reffered_id)).extract()
            if aff_raw:
                affiliations = [{'value': aff} for aff in aff_raw]
            authors.append({
                'surname': surname,
                'given_names': given_names,
                'affiliations': affiliations,
            })

        return authors

    def _create_fft_file(self, file_path, file_access, file_type):
        """Create a structured dictionary and add to 'files' item."""
        file_dict = {
            "access": file_access,
            "description": self.name.upper(),
            "url": file_path,
            "type": file_type,
        }
        return file_dict
