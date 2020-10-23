# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017, 2018, 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function

import datetime
import inspect
import fnmatch
import os
import pprint
import re
from functools import wraps
from itertools import groupby
from netrc import netrc
from six.moves.urllib.parse import urlparse
from zipfile import ZipFile

import ftputil
import ftputil.session
import ftplib
from inspire_schemas.builders import LiteratureBuilder
from scrapy import Selector

from hepcrawl.tohep import (hep_to_hep, _normalize_hepcrawl_record,
                            hepcrawl_to_hep, UnknownItemFormat)

RE_FOR_THE = re.compile(
    r'\b(?:for|on behalf of|representing)\b',
    re.IGNORECASE,
)
INST_PHRASES = ['for the development', ]


class PathDoesNotExist(IOError):
    pass


def unzip_xml_files(filename, target_folder):
    """Unzip files (XML only) into target folder."""
    z = ZipFile(filename)
    xml_files = []
    for filename in z.namelist():
        if filename.endswith(".xml"):
            absolute_path = os.path.join(target_folder, filename)
            if not os.path.exists(absolute_path):
                z.extract(filename, target_folder)
            xml_files.append(absolute_path)
    return xml_files


def ftp_connection_info(ftp_host, netrc_file, passive_mode=True):
    """Return ftp connection info from netrc and optional host address."""
    if not ftp_host:
        ftp_host = netrc(netrc_file).hosts.keys()[0]
    logininfo = netrc(netrc_file).authenticators(ftp_host)
    connection_params = {
        "ftp_user": logininfo[0],
        "ftp_password": logininfo[2],
        "ftp_passive": passive_mode,
    }
    return ftp_host, connection_params


def ftp_list_files(
    server_folder,
    ftp_host,
    user,
    password,
    destination_folder=None,
    passive_mode=True,
    only_missing_files=True,
):
    """

    Args:
        server_folder(str): remote folder to list.

        ftp_host(str): name of the host. Example: 'ftp.cern.ch'

        user(str): For authentication.

        password(str): For authentication.

        destination_folder(str): local folder to compare with.

        passive_mode(bool): True if it should use firewall friendly ftp passive
            mode.

        only_missing_files(bool): If True will only list the files that are not
            already in the ``destination_folder``.
    """
    session_factory = ftputil.session.session_factory(
        base_class=ftplib.FTP,
        port=21,
        use_passive_mode=passive_mode,
        encrypt_data_channel=True,
    )

    with ftputil.FTPHost(
        ftp_host,
        user,
        password,
        session_factory=session_factory,
    ) as host:
        file_names = host.listdir(os.path.join(host.curdir, server_folder))
        if only_missing_files:
            return list_missing_files(
                server_folder,
                destination_folder,
                file_names,
            )
        else:
            return [
                os.path.join(
                    server_folder,
                    file_name
                ) for file_name in file_names
            ]


def local_list_files(local_folder, target_folder, glob_expression='*'):
    file_names = [
        file_name
        for file_name in os.listdir(local_folder)
        if (
            os.path.isfile(os.path.join(local_folder, file_name)) and
            fnmatch.fnmatch(file_name, glob_expression)
        )
    ]
    return list_missing_files(local_folder, target_folder, file_names)


def list_missing_files(remote_folder, target_folder, file_names):
    missing_files = []
    for file_name in file_names:
        destination_file = os.path.join(target_folder, file_name)
        source_file = os.path.join(remote_folder, file_name)
        if not os.path.exists(destination_file):
            missing_files.append(source_file)

    return missing_files


def get_first(iterable, default=None):
    """Get first truthy value from iterable, fall back to default.

    This is useful to express a preference among several selectors,
    independently from the position where the matches appear in the document.

    Examples:

        >>> from scrapy import Selector
        >>> from hepcrawl.utils import get_first
        >>> document = '<root><bar>first</bar><foo>second</foo></root>'
        >>> selector = Selector(text=document)
        >>> selector.xpath('string(//foo|//bar)').extract_first()
        u'first'
        >>> get_first([selector.xpath('string(//foo)'),
        ...           selector.xpath('string(//bar)')]).extract_first()
        u'second'
    """
    matches = (val for val in iterable if val)
    return next(matches, default)


def collapse_initials(name):
    """Remove the space between initials, eg ``T. A.`` --> ``T.A.``"""
    if len(name.split(".")) > 1:
        name = re.sub(r'([A-Z]\.)[\s\-]+(?=[A-Z]\.)', r'\1', name)
    return name


def split_fullname(author, switch_name_order=False):
    """Split an author name to surname and given names.

    It accepts author strings with and without comma separation.
    As default surname is first in case of comma separation, otherwise last.
    Multi-part surnames are incorrectly detected in strings without comma
    separation.
    """
    if not author:
        return "", ""

    if "," in author:
        fullname = [n.strip() for n in author.split(',')]
        surname_first = True
    else:
        fullname = [n.strip() for n in author.split()]
        surname_first = False

    if switch_name_order:
        surname_first = not surname_first

    if surname_first:
        surname = fullname[0]
        given_names = " ".join(fullname[1:])
    else:
        surname = fullname[-1]
        given_names = " ".join(fullname[:-1])

    return surname, given_names


def build_dict(seq, key):
    """
    Creates a dictionary from a list, using the specified key.

    Used to make searching in a list of objects faster (get operations are
    O(1)).
    """
    return dict((d[key], dict(d, index=i)) for (i, d) in enumerate(seq))


def parse_domain(url):
    """Parse domain from a given url."""
    parsed_uri = urlparse(url)
    domain = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
    return domain


def has_numbers(text):
    """Detects if a string contains numbers"""
    return any(char.isdigit() for char in text)


def range_as_string(data):
    """Detects integer ranges in a list and returns a string representing them.
    E.g. ``["1981", "1982", "1985"]`` -> ``1981-1982, 1985``
    """
    data = [int(i) for i in data]
    ranges = []
    for key, group in groupby(
        enumerate(data),
        lambda index_item: index_item[0] - index_item[1]
    ):
        group = [year for _, year in group]
        if len(group) > 1:
            rangestring = "{}-{}".format(str(group[0]), str(group[-1]))
            ranges.append(rangestring)
        else:
            ranges.append(str(group[0]))
    return ", ".join(ranges)


def get_node(text, namespaces=None):
    """Get a scrapy selector for the given text node."""
    node = Selector(text=text, type="xml")
    if namespaces:
        for ns in namespaces:
            node.register_namespace(ns[0], ns[1])
    return node


def coll_cleanforthe(coll):
    """ Cleanup collaboration, try to find author """
    author = None

    if any(phrase for phrase in INST_PHRASES if phrase in coll.lower()):
        # don't touch it, doesn't look like a collaboration
        return coll, author

    coll = coll.strip('.; ')

    if RE_FOR_THE.search(coll):
        # get strings leading and trailing 'for the'
        (lead, trail) = RE_FOR_THE.split(coll, maxsplit=1)
        if re.search(r'\w', lead):
            author = lead.strip()
        if re.search(r'\w', trail):
            coll = trail

    coll = re.sub('(?i)^ *the ', '', coll)
    coll = re.sub('(?i) *collaborations? *', '', coll)
    coll = coll.strip()

    return coll, author


def get_journal_and_section(publication):
    """Take journal title string and try to extract possible section letter."""
    section = ''
    journal_title = ''
    possible_sections = ["A", "B", "C", "D", "E"]
    try:
        split_pub = [element for element in re.split(r'(\W+)', publication) if element]
        if split_pub[-1] in possible_sections:
            section = split_pub.pop(-1)
        journal_title = "".join(
            [
                word
                for word in split_pub
                if "section" not in word.lower()
            ]
        ).strip(", ")
    except IndexError:
        pass

    return journal_title, section


def get_licenses(
    license_url=None,
    license_text=None,
    license_material=None,
):
    """Get the license dictionary from the url or the text of the license.

    Args:
        license_url(str): Url of the license to generate.

        license_text(str): Text with the description of the license (sometimes
            is all we got...).

        license_material(str): Material of the license.

    Returns:
        list(dict): list of dictionaries that are licenses, empty list
            if no license could be extracted.
    """
    if license_url or license_text:
        license = [{
            'license': license_text,
            'url': license_url,
            'material': license_material,
        }]
    else:
        license = []

    return license


def strict_kwargs(func):
    """This decorator will disallow any keyword arguments that
    do not begin with an underscore sign in the decorated method.
    This is mainly to make errors while passing arguments to spiders
    immediately visible. As we cannot remove kwargs from there altogether
    (used by scrapyd), with this we can ensure that we are not passing unwanted
    data by mistake.

    Additionaly this will add all of the 'public' not-None kwargs to an
    `_init_kwargs` field in the object for easier passing and all of the
    arguments (including non-overloaded ones) to `_all_kwargs`.
    (To make passing them forward easier.)

    Args:
        func (function): a spider method

    Returns:
        function: method which will disallow any keyword arguments that
            do not begin with an underscore sign.
    """
    argspec = inspect.getargspec(func)
    defined_arguments = argspec.args[1:]
    spider_fields = ['settings', 'crawler_settings']

    allowed_arguments = defined_arguments + spider_fields

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        disallowed_kwargs = [
            key for key in kwargs
            if not key.startswith('_') and key not in allowed_arguments
        ]

        if disallowed_kwargs:
            raise TypeError(
                'Only underscored kwargs or %s allowed in %s. '
                'Check %s for typos.' % (
                    ', '.join(spider_fields),
                    func,
                    ', '.join(disallowed_kwargs),
                )
            )

        return func(self, *args, **kwargs)
    return wrapper


class RecordFile(object):
    """Metadata of a file needed for a record.

    Args:
        path(str): local path to the file.

        name(str): Optional, name of the file, if not passed, will use the name
            in the ``path``.

    Rises:
        PathDoesNotExist:
    """
    def __init__(self, path=None, name=None):
        self.path = path
        if self._is_local_path(self.path) and not os.path.exists(self.path):
            raise PathDoesNotExist(
                "The given record file path '%s' does not exist." % self.path
            )

        if name is None:
            name = os.path.basename(path)

        self.name = name

    def _is_local_path(self, url):
        parsed_url = urlparse(url)
        return not parsed_url.scheme

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return '%s(path="%s", name="%s")' % (
            self.__class__.__name__,
            self.path,
            self.name,
        )


class ParsedItem(dict):
    """Each of the individual items returned by the spider to the pipeline.

    Args:
        record(dict): Information about the crawled record, might be in
            different formats.

        record_format(str): Format of the above record, for example ``"hep"``
            or ``"hepcrawl"``.

        file_urls(list(str)): URLs to the files to be downloaded by
            ``DocumentsPipeline``.

        file_requests(list(Request)): Request objects of files to be downloaded
            by ``DocumentsPipeline``

        ftp_params(dict): Parameter for the
            :class:`hepcrawl.pipelines.DocumentsPipeline` to be able to connect
            to the ftp server, if any.

        record_files(list(RecordFile)): files attached to the record, usually
            populated by :class:`hepcrawl.pipelines.DocumentsPipeline` from the
            ``file_urls`` parameter.


        source_file(str): name of the crawled file.

    Attributes:
        *: this class bypasses the regular dict ``__getattr__`` allowing to
            access any of it's elements as attributes.
    """
    def __init__(
        self,
        record,
        record_format,
        file_urls=None,
        file_requests=None,
        ftp_params=None,
        record_files=None,
        file_name=None,
    ):
        super(ParsedItem, self).__init__(
            record=record,
            record_format=record_format,
            file_urls=file_urls,
            file_requests=file_requests,
            ftp_params=ftp_params,
            record_files=record_files,
            file_name=file_name,
        )

    def __getattr__(self, key):
        if key not in self:
            raise AttributeError(
                "'%s' object has no attribute '%s'" % (
                    self.__class__.__name__,
                    key,
                )
            )

        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

    def __str__(self):
        return pprint.pformat(self)

    @staticmethod
    def from_exception(record_format, exception, traceback, source_data, file_name):
        parsed_item = ParsedItem(
            record={},
            record_format=record_format,
            file_name=file_name,
        )
        parsed_item.exception = exception
        parsed_item.traceback = traceback
        parsed_item.source_data = source_data
        return parsed_item

    def to_hep(self, source):
        """Get an output ready hep formatted record from the given
        :class:`hepcrawl.utils.ParsedItem`, whatever format it's record might be.

        Args:
            source(str): string identifying the source for this item (ex. 'arXiv').

        Returns:
            hepcrawl.utils.ParsedItem: the new item, with the internal record
                formated as hep record.

        Raises:
            UnknownItemFormat: if the source item format is unknown.
        """
        builder = LiteratureBuilder(
            source=source
        )

        builder.add_acquisition_source(
            source=source,
            method='hepcrawl',
            date=datetime.datetime.now().isoformat(),
            submission_number=os.environ.get('SCRAPY_JOB', ''),
        )

        self.record['acquisition_source'] = builder.record['acquisition_source']

        if self.record_format == 'hep':
            record = hep_to_hep(
                hep_record=self.record,
                record_files=self.record_files,
            )
            for document in record.get('documents', []):
                if 'old_url' in document and 'original_url' not in document:
                    document['original_url'] = document['old_url']
                    del document['old_url']
            return record
        elif self.record_format == 'hepcrawl':
            record = _normalize_hepcrawl_record(
                item=self.record,
                source=source,
            )
            return hepcrawl_to_hep(dict(record))
        else:
            raise UnknownItemFormat(
                'Unknown ParsedItem::{}'.format(self.record_format)
            )
