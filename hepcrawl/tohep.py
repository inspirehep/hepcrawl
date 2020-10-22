# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Functions used to convert records and items from one format to another.


Currently there are only two formats for records that we consider:

    * Hepcrawl format: internal format used by the spiders as middle step
      before the pipeline, it's a generic wider format that should have at
      least the same info as the HEP format used by Inspire.

    * HEP format: Inspire compatible format, it's the fromat that you get as a
      result of the crawl.

"""

from __future__ import absolute_import, division, print_function

import logging
import os

from inspire_schemas.api import LiteratureBuilder

LOGGER = logging.getLogger(__name__)


class UnknownItemFormat(Exception):
    pass


def _get_updated_documents(current_documents, record_files):
    """

    Args:
        current_documents(list(dict)): current documents as generated
            by ``dojson``. We expect each of them to have, at least, a key
            named ``old_url``.

        record_files(list(RecordFile)): files attached to the record as
            populated by :class:`hepcrawl.pipelines.DocumentsPipeline`.
    """
    record_files_index = {
        os.path.basename(record_file.name): record_file.path
        for record_file in record_files
    }
    new_documents = []
    for document in current_documents:
        url = document.get('old_url', document.get('url', ''))
        full_file_name = os.path.basename(url)
        if url and full_file_name in record_files_index:
            document['old_url'] = document['url']
            document['url'] = record_files_index[full_file_name]
            if not 'key' in document:
                document['key'] = full_file_name
        elif url:
            document['url'] = document['old_url']

        new_documents.append(document)

    return new_documents


def _has_publication_info(item):
    return item.get('pubinfo_freetext') or \
        item.get('journal_volume') or \
        item.get('journal_title') or \
        item.get('journal_year') or \
        item.get('journal_issue') or \
        item.get('journal_fpage') or \
        item.get('journal_lpage') or \
        item.get('journal_artid') or \
        item.get('journal_doctype')


def _remove_fields(item, keys):
    """Remove the given keys from the dict."""
    for key in keys:
        # remove the key if there, no error if not there
        item.pop(key, None)


def _normalize_hepcrawl_record(item, source):
    if 'related_article_doi' in item:
        item['dois'] += item.pop('related_article_doi', [])

    item['titles'] = [{
        'title': item.pop('title', ''),
        'subtitle': item.pop('subtitle', ''),
        'source': item.pop('source', source),
    }]

    item['abstracts'] = [{
        'value': item.pop('abstract', ''),
        'source': source,
    }]

    item['imprints'] = [{
        'date': item.pop('date_published', ''),
    }]

    item['copyright'] = [{
        'holder': item.pop('copyright_holder', ''),
        'year': item.pop('copyright_year', ''),
        'statement': item.pop('copyright_statement', ''),
        'material': item.pop('copyright_material', ''),
    }]

    if _has_publication_info(item):
        item['publication_info'] = [{
            'journal_title': item.pop('journal_title', ''),
            'journal_volume': item.pop('journal_volume', ''),
            'journal_issue': item.pop('journal_issue', ''),
            'artid': item.pop('journal_artid', ''),
            'page_start': item.pop('journal_fpage', ''),
            'page_end': item.pop('journal_lpage', ''),
            'note': item.pop('journal_doctype', ''),
            'pubinfo_freetext': item.pop('pubinfo_freetext', ''),
            'pubinfo_material': item.pop('pubinfo_material', ''),
        }]
        if item.get('journal_year'):
            item['publication_info'][0]['year'] = int(
                item.pop('journal_year')
            )

    _remove_fields(
        item,
        [
            'journal_title',
            'journal_volume',
            'journal_year',
            'journal_issue',
            'journal_fpage',
            'journal_lpage',
            'journal_doctype',
            'journal_artid',
            'pubinfo_freetext',
            'pubinfo_material',
        ]
    )

    return item


def hep_to_hep(hep_record, record_files):
    """This is needed to be able to patch the ``documents`` in the record.

    As earlier in the process we don't really have all the files yet. It should
    be used by any spiders that generate hep format instead of the internal
    hepcrawl one (normally, marc-ingesting spiders).
    """
    if record_files:
        LOGGER.debug('Updating documents from: %s', hep_record['documents'])
        LOGGER.debug('With record_files: %s', record_files)
        hep_record['documents'] = _get_updated_documents(
            current_documents=hep_record['documents'],
            record_files=record_files,
        )
        LOGGER.debug('Updated documents to: %s', hep_record['documents'])

    return hep_record


def hepcrawl_to_hep(crawler_record):
    """
    Args:
        crawler_record(dict): dictionary representing the hepcrawl formatted
            record.


    Returns:
        dict: The hep formatted record.
    """

    def _filter_affiliation(affiliations):
        return [
            affilation.get('value')
            for affilation in affiliations
            if affilation.get('value')
        ]

    builder = LiteratureBuilder(
        source=crawler_record['acquisition_source']['source']
    )

    for author in crawler_record.get('authors', []):
        builder.add_author(builder.make_author(
            full_name=author['full_name'],
            raw_affiliations=_filter_affiliation(author['affiliations']),
        ))

    for title in crawler_record.get('titles', []):
        builder.add_title(
            title=title.get('title'),
            subtitle=title.get('subtitle'),
            source=title.get('source')
        )

    for abstract in crawler_record.get('abstracts', []):
        builder.add_abstract(
            abstract=abstract.get('value'),
            source=abstract.get('source')
        )

    for arxiv_eprint in crawler_record.get('arxiv_eprints', []):
        builder.add_arxiv_eprint(
            arxiv_id=arxiv_eprint.get('value'),
            arxiv_categories=arxiv_eprint.get('categories')
        )

    for doi in crawler_record.get('dois', []):
        builder.add_doi(
            doi=doi.get('value'),
            material=doi.get('material'),
        )

    for private_note in crawler_record.get('private_notes', []):
        builder.add_private_note(
            private_notes=private_note
        )

    for public_note in crawler_record.get('public_notes', []):
        builder.add_public_note(
            public_note=public_note.get('value'),
            source=public_note.get('source')
        )

    for license in crawler_record.get('license', []):
        builder.add_license(
            url=license.get('url'),
            license=license.get('license'),
            material=license.get('material'),
        )

    for collaboration in crawler_record.get('collaborations', []):
        builder.add_collaboration(
            collaboration=collaboration.get('value')
        )

    for imprint in crawler_record.get('imprints', []):
        builder.add_imprint_date(
            imprint_date=imprint.get('date')
        )

    for copyright in crawler_record.get('copyright', []):
        builder.add_copyright(
            holder=copyright.get('holder'),
            material=copyright.get('material'),
            statement=copyright.get('statement')
        )

    builder.add_preprint_date(
        preprint_date=crawler_record.get('preprint_date')
    )

    acquisition_source = crawler_record.get('acquisition_source', {})
    builder.add_acquisition_source(
        method=acquisition_source['method'],
        date=acquisition_source['datetime'],
        source=acquisition_source['source'],
        submission_number=acquisition_source['submission_number'],
    )

    try:
        builder.add_number_of_pages(
            number_of_pages=int(crawler_record.get('page_nr', [])[0])
        )
    except (TypeError, ValueError, IndexError):
        pass

    publication_types = [
        'introductory',
        'lectures',
        'review',
        'manual',
    ]

    document_types = [
        'book',
        'note',
        'report',
        'proceedings',
        'thesis',
    ]

    added_doc_type = False

    for collection in crawler_record.get('collections', []):
        collection = collection['primary'].strip().lower()

        if collection == 'arxiv':
            continue  # ignored
        elif collection == 'citeable':
            builder.set_citeable(True)
        elif collection == 'core':
            builder.set_core(True)
        elif collection == 'noncore':
            builder.set_core(False)
        elif collection == 'published':
            builder.set_refereed(True)
        elif collection == 'withdrawn':
            builder.set_withdrawn(True)
        elif collection in publication_types:
            builder.add_publication_type(collection)
        elif collection == 'bookchapter':
            added_doc_type = True
            builder.add_document_type('book chapter')
        elif collection == 'conferencepaper':
            added_doc_type = True
            builder.add_document_type('conference paper')
        elif collection in document_types:
            added_doc_type = True
            builder.add_document_type(collection)

    if not added_doc_type:
        builder.add_document_type('article')

    _pub_info = crawler_record.get('publication_info', [{}])[0]
    builder.add_publication_info(
        year=_pub_info.get('year'),
        artid=_pub_info.get('artid'),
        page_end=_pub_info.get('page_end'),
        page_start=_pub_info.get('page_start'),
        journal_issue=_pub_info.get('journal_issue'),
        journal_title=_pub_info.get('journal_title'),
        journal_volume=_pub_info.get('journal_volume'),
        pubinfo_freetext=_pub_info.get('pubinfo_freetext'),
        material=_pub_info.get('pubinfo_material'),
    )

    for report_number in crawler_record.get('report_numbers', []):
        builder.add_report_number(
            report_number=report_number.get('value'),
            source=report_number.get('source')
        )

    for url in crawler_record.get('urls', []):
        builder.add_url(url=url.get('value'))

    for document in crawler_record.get('documents', []):
        builder.add_document(
            description=document.get('description'),
            fulltext=document.get('fulltext'),
            hidden=document.get('hidden'),
            key=document['key'],
            material=document.get('material'),
            original_url=document.get('original_url'),
            url=document['url'],
        )

    return builder.record
