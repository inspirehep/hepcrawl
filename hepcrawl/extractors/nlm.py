# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Common extraction from the NLM XML format."""

from __future__ import absolute_import, division, print_function


class NLM(object):
    """Special extractions for NLM formats."""

    @staticmethod
    def get_authors(node):
        """Get the authors."""
        authors = []
        for author in node.xpath("./AuthorList//Author"):
            surname = author.xpath("./LastName/text()").extract_first()
            firstname = author.xpath("./FirstName/text()").extract_first()
            middlename = author.xpath("./MiddleName/text()").extract_first()
            affiliations = author.xpath(".//Affiliation/text()").extract()

            if not surname:
                surname = ""
            given_names = ""
            if firstname and middlename:
                given_names = "{} {}".format(firstname, middlename)
            elif firstname:
                given_names = firstname

            auth_dict = {}
            auth_dict["surname"] = surname
            auth_dict["given_names"] = given_names
            if affiliations:
                auth_dict["affiliations"] = [
                    {"value": aff} for aff in affiliations]
            authors.append(auth_dict)

        return authors

    @staticmethod
    def get_collections(doctype):
        """Return the article's collection."""
        collections = ["HEP", "Citeable", "Published"]
        if doctype:
            if doctype == "Review":
                collections += ["Review"]
            if "conference" in doctype.lower():
                collections += ["ConferencePaper"]
        return collections

    @staticmethod
    def get_dois(node):
        """Get DOI."""
        dois = node.xpath(
            ".//ArticleIdList/ArticleId[@IdType='doi']/text()").extract()
        if not dois:
            dois = node.xpath(
                ".//ELocationID[@EIdType='doi']/text()").extract()

        return dois

    @staticmethod
    def get_date_published(node):
        """Publication date."""
        year = node.xpath(".//Journal/PubDate/Year/text()").extract_first()
        month = node.xpath(".//Journal/PubDate/Month/text()").extract_first()
        day = node.xpath(".//Journal/PubDate/Day/text()").extract_first()

        date_published = ""
        if year:
            date_published = year
        if month:
            date_published += "-" + month
        if day:
            date_published += "-" + day

        return date_published

    @staticmethod
    def get_pub_status(node):
        """Publication status.

        .. note::
            Cases of publication status:

                * aheadofprint
                * ppublish
                * epublish
                * received
                * accepted
                * revised
                * ecollection
        """
        pubstatus = node.xpath(".//Journal/PubDate/@PubStatus").extract_first()

        return pubstatus

    @staticmethod
    def get_doctype(node):
        """Publication type.

        .. note::
            Cases of publication type:

                * Addresses
                * Bibliography
                * Case Reports
                * Classical Article
                * Clinical Conference
                * Clinical Trial
                * Congresses
                * Consensus Development Conference
                * Consensus Development Conference, NIH
                * Corrected and Republished Article
                * Editorial
                * Festschrift
                * Guideline
                * Interview
                * Journal Article
                * Lectures
                * etter
                * Meta-Analysis
                * News
                * Newspaper Article
                * Observational Study
                * Patient Education Handout
                * Practice Guideline
                * Published Erratum
                * Retraction of Publication
                * Review
                * Video-Audio Media
                * Webcasts
        """
        pubtype = node.xpath(".//PublicationType/text()").extract_first()
        return pubtype

    @staticmethod
    def get_page_numbers(node):
        """Get page numbers and number of pages."""

        fpage = node.xpath(".//FirstPage/text()").extract_first()
        lpage = node.xpath(".//LastPage/text()").extract_first()
        if fpage and lpage:
            page_nr = str(int(lpage) - int(fpage) + 1)
        else:
            page_nr = ''

        return (
            fpage,
            lpage,
            page_nr,
        )
