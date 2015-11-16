# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import pytest

from hepcrawl.spiders import base_spider

from .responses import fake_response_from_file


@pytest.fixture
def results():
    """Return results generator from the WSP spider."""
    spider = base_spider.BaseSpider()
    return spider.parse(fake_response_from_file('base/test_record1_no_namespaces.xml')) #this doesn't understand namespaces!!!! >:(
    #return spider.parse(fake_response_from_file('base/test_record1.xml')) 

def test_abstract(results):
    """Test extracting abstract."""
    abstract = (
        "In heavy-ion induced fusion-fission reactions, the angular distribution of fission fragments is sensitive to the mean square angular momentum brought in by the fusion process, and the nuclear shape and temperature at the fission saddle point. Experimental fission fragment angular distributions are often used to infer one or more of these properties. Historically the analysis of these distributions has re­ lied on the alignment of the total angular momentum J of the compound nucleus, perpendicular to the projectile velocity. A full theoretical approach, written into a computer code for the first time, allows the effect of ground-state spin of the projectile and target nuclei to be correctly treated. This approach takes into account the change in alignment of J due to the inclusion of this spin, an effect which is shown to be markedly stronger if the nucleus with appreciable spin also has a strong quadrupole deformation. This change in alignment of J results in a much reduced fission fragment anisotropy. In extreme cases, the anisotropy may be below unity, and it ceases to be sufficient to characterise the fission fragment angular distribution. The calculations have been tested experimentally, by measuring fission and sur­ vival cross-sections and fission fragment angular distributions for the four reactions 31P+175,176Lu and 28.29 Si+178Hf, where 176Lu is a strongly-deformed nucleus with an intrinsic spin of 7 units, and 178Hf has very similar deformation, but zero spin. The reactions form the compound nuclei 206.207Rn. The total fusion excitation func­ tions are well-reproduced by calculations, but the fission fragment anisotropies are reproduced only when the nuclear spin and deformation are taken into account, con­ firming the theory and supporting the recent understanding of the role of nuclear deformation in the fusion process and of compound nucleus angular momentum in the fission process. Having established the effect in the well-understood fusion-fission reactions, the effect of nuclear spin is examined for the less well understood quasi-fission reaction. Experiments were performed to measure fission cross-sections and fission fragment angular distributions for the reactions 16O+235,238U, where 235U has a spin of 7/2 and 238U has a spin of zero. Both nuclei are quadrupole-deformed, and 160+238U was already known to exhibit evidence for quasi-fission. Theoretical calculations indicate that the fitted anisotropy is sensitive to the range of angles over which the angular distribution is measured, showing that where quasi-fission is present, the anisotropy is not sufficient to entirely characterise the fission fragment angular dis­ tribution. Comparison of the measured anisotropies with fusion-fission calculations shows clearly that the reaction is quasi-fission dominated. However, although exist­ ing quasi-fission models predict a strong effect from the spin of 235U, it is shown that the observed effect is appreciably stronger still in the experimental angular range. This should be an important tool in evaluating future models of the quasi-fission process."
    )
    for record in results: #this does not work, because  parse_node might return a new request...test doesn't know what to do
        print(record)
        assert 'abstract' in record
        assert record['abstract'] == abstract

def test_title(results):
    """Test extracting title."""
    title = "The effect of ground-state spin on fission and quasi-fission anisotropies"
    for record in results:
        assert 'title' in record
        assert record['title'] == title


def test_date_published(results):
    """Test extracting date_published."""
    date_published = "2013-05-09T05:16:48Z"
    for record in results:
        print(record)
        assert 'date_published' in record
        assert record['date_published'] == date_published


#def test_page_nr(results):
    #"""Test extracting page_nr"""
    #page_nr = "7"
    #for record in results:
        #assert 'page_nr' in record
        #assert record['page_nr'] == page_nr


#def test_free_keywords(results):
    #"""Test extracting free_keywords"""
    #free_keywords = ['Perovskite CH$_{3}$NH$_{3}$PbI$_{3}$', 'solar cell', 'lithium']
    #for record in results:
        #assert 'free_keywords' in record
        #for keyword in record['free_keywords']:
            #assert keyword["source"] == "author"
            #assert keyword["value"] in free_keywords
            #free_keywords.remove(keyword['value'])


#def test_license(results):
    #"""Test extracting license information."""
    #license = "Creative Commons Attribution (CC-BY) 4.0 License"
    #license_url = "https://creativecommons.org/licenses/by/4.0"
    #license_type = "open-access"
    #for record in results:
        #assert 'license' in record
        #assert record['license'] == license
        #assert 'license_url' in record
        #assert record['license_url'] == license_url
        #assert 'license_type' in record
        #assert record['license_type'] == license_type


#def test_dois(results):
    #"""Test extracting dois."""
    #dois = ["10.1142/S1793292014400013"]
    #for record in results:
        #assert 'dois' in record
        #assert record['dois'] == dois


#def test_collections(results):
    #"""Test extracting collections."""
    #collections = ["HEP", "Published"]
    #for record in results:
        #assert 'collections' in record
        #assert record['collections'] == collections


#def test_collaboration(results):
    #"""Test extracting collaboration."""
    #collaboration = ["Belle Collaboration"]
    #for record in results:
        #assert 'collaboration' in record
        #assert record['collaboration'] == collaboration


#def test_publication_info(results):
    #"""Test extracting dois."""
    #journal_title = "NANO"
    #journal_year = "2014"
    #journal_artid = "1440001"
    #journal_volume = "9"
    #journal_issue = "05"
    #for record in results:
        #assert 'journal_title' in record
        #assert record['journal_title'] == journal_title
        #assert 'journal_year' in record
        #assert record['journal_year'] == journal_year
        #assert 'journal_artid' in record
        #assert record['journal_artid'] == journal_artid
        #assert 'journal_volume' in record
        #assert record['journal_volume'] == journal_volume
        #assert 'journal_issue' in record
        #assert record['journal_issue'] == journal_issue


def test_authors(results):
    """Test authors."""
    authors = ["Butt, Rachel Deborah"]
    affiliation = "jaa"
    #xref_affiliation = "Physics Department, Brookhaven National Laboratory, Upton, NY 11973, USA"
    #collab = "Belle Collaboration"
    for record in results:
        print(record)
        assert 'authors' in record
        assert len(record['authors']) == len(authors)

        # here we are making sure order is kept
        for index, name in enumerate(authors):
            assert record['authors'][index]['full_name'] == name
            assert affiliation in record['authors'][index]['affiliations']
            
            #if index == 1:
                #assert xref_affiliation in [
                    #aff['value'] for aff in record['authors'][index]['affiliations']
                #]


#def test_copyrights(results):
    #"""Test extracting copyright."""
    #copyright_holder = "World Scientific Publishing Company"
    #copyright_year = "2014"
    #copyright_statement = ""
    #copyright_material = "Article"
    #for record in results:
        #assert 'copyright_holder' in record
        #assert record['copyright_holder'] == copyright_holder
        #assert 'copyright_year' in record
        #assert record['copyright_year'] == copyright_year
        #assert 'copyright_statement' not in record
        #assert 'copyright_material' in record
        #assert record['copyright_material'] == copyright_material
