# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function

import os
import pprint
import re
from operator import itemgetter
from itertools import groupby
from netrc import netrc
from tempfile import mkstemp
from zipfile import ZipFile
from urlparse import urlparse

import ftputil
import ftputil.session
import ftplib
import requests

from scrapy import Selector

from .mappings import LICENSES, LICENSE_TEXTS

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


def ftp_connection_info(ftp_host, netrc_file, passive_mode=False):
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
    passive_mode=False,
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


def local_list_files(local_folder, target_folder):
    file_names = os.listdir(local_folder)
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
    """Get first item in iterable or default."""
    if iterable:
        for item in iterable:
            return item
    return default


def best_match(iterable, default=None):
    """Get first truthy value from iterable, fall back to default.

    This is useful to express a preference among several selectors,
    independently from the position where the matches appear in the document.

    Examples:

        >>> from scrapy import Selector
        >>> from hepcrawl.utils import best_match
        >>> document = '<root><bar>first</bar><foo>second</foo></root>'
        >>> selector = Selector(text=document)
        >>> selector.xpath('string(//foo|//bar)').extract_first()
        u'first'
        >>> best_match([selector.xpath('string(//foo)'),
        ...             selector.xpath('string(//bar)')]).extract_first()
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


def get_temporary_file(prefix="tmp_",
                       suffix="",
                       directory=None):
    """Generate a safe and closed filepath."""
    try:
        file_fd, filepath = mkstemp(prefix=prefix,
                                    suffix=suffix,
                                    dir=directory)
        os.close(file_fd)
    except IOError, e:
        try:
            os.remove(filepath)
        except Exception:
            pass
        raise e
    return filepath


def get_nested(root, *keys):
    """
    Returns the nested value of the provided key series.
    Returns '' otherwise
    """
    if not keys:
        return root
    if keys[0] not in root:
        return ''
    if keys[0] in root:
        return get_nested(root[keys[0]], *keys[1:])


def build_dict(seq, key):
    """
    Creates a dictionary from a list, using the specified key.

    Used to make searching in a list of objects faster (get operations are
    O(1)).
    """
    return dict((d[key], dict(d, index=i)) for (i, d) in enumerate(seq))


def get_mime_type(url):
    """Get mime type from url."""
    if not url:
        return ""
    resp = requests.head(url, allow_redirects=True)
    content_type = resp.headers.get("Content-Type")
    if content_type is None:
        raise Exception("No content-type found in URL {0}".format(url))
    return content_type


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
        lambda (index, item): index - item
    ):
        group = map(itemgetter(1), group)
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
        split_pub = filter(None, re.split(r'(\W+)', publication))
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
    license_url='',
    license_text='',
    license_material='',
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
    def _populate_license_material(license):
        if license_material:
            license['material'] = license_material

        return license

    def _get_license():
        license = get_license_by_url(license_url=license_url)
        if not license:
            license = get_license_by_text(license_text=license_text)

        return license

    license = _get_license()

    return [_populate_license_material(license)] if license else []


def get_license_by_url(license_url):
    if not license_url:
        return []

    license_str = ''
    for key in LICENSES.keys():
        if key in license_url.lower():
            license_str = re.sub(
                '(?i)^.*%s' % key,
                LICENSES[key],
                license_url.strip('/'),
            )
            break
    return {'license': license_str, 'url': license_url}


def get_license_by_text(license_text):
    if not license_text:
        return []

    for key in LICENSE_TEXTS.keys():
        if license_text.lower() in key.lower():
            license = get_license_by_url(license_url=LICENSE_TEXTS[key])

    return license


class RecordFile(object):
    """Metadata of a file needed for a record.

    Args:
        path(str): local path to the file.

        name(str): Optional, name of the file, if not passed, will use the name
            in the ``path``.

    Rises:
        PathDoesNotExist:
    """
    def __init__(self, path, name=None):
        self.path = path
        if not os.path.exists(self.path):
            raise PathDoesNotExist(
                "The given record file path '%s' does not exist." % self.path
            )

        if name is None:
            name = os.path.basename(path)

        self.name = name


class ParsedItem(dict):
    """Each of the individual items returned by the spider to the pipeline.

    Args:
        record(dict): Information about the crawled record, might be in
            different formats.

        record_format(str): Format of the above record, for example ``"hep"``
            or ``"hepcrawl"``.

        file_urls(list(str)): URLs to the files to be downloaded by
            ``FftFilesPipeline``.

        ftp_params(dict): Parameter for the
            :class:`hepcrawl.pipelines.FftFilesPipeline` to be able to connect
            to the ftp server, if any.

        record_files(list(RecordFile)): files attached to the record, usually
            populated by :class:`hepcrawl.pipelines.FftFilesPipeline` from the
            ``file_urls`` parameter.

    Attributes:
        *: this class bypasses the regular dict ``__getattr__`` allowing to
            access any of it's elements as attributes.
    """
    def __init__(
        self,
        record,
        record_format,
        file_urls=None,
        ftp_params=None,
        record_files=None,
        **kwargs
    ):
        super(ParsedItem, self).__init__(
            record=record,
            record_format=record_format,
            file_urls=file_urls,
            ftp_params=ftp_params,
            record_files=record_files,
            **kwargs
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
