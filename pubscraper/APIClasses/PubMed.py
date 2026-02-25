import requests
import json
import time
import logging
import os
from xml.etree import ElementTree as ET

from ratelimit import limits, sleep_and_retry

from pubscraper.APIClasses.Base import Base
import pubscraper.config as config

logger = logging.getLogger(__name__)


class PubMed(Base):
    def __init__(self):
        self.search_url = config.PUBMED_SEARCH_URL
        self.fetch_url = config.PUBMED_FETCH_URL

    @sleep_and_retry
    @limits(calls=2, period=1)
    def _make_request(self, url, params):
        try:
            response = requests.get(url, params=params, timeout=10)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from {url}: {e}")
            raise
        response.raise_for_status()
        return response

    def _parse_author_name(self, author_name):
        """
        Parse an author name string into (last, first, middle) components.
        Input format: "Last First [Middle]"
        Middle initial may be attached to the first name (e.g. "Kelsey m").
        """
        parts = author_name.strip().split()
        if len(parts) < 2:
            return author_name, "", ""
        last = parts[0]
        first = parts[1]
        middle = " ".join(parts[2:]) if len(parts) > 2 else ""
        return last, first, middle

    def _get_UIDs_by_author(self, author_name, rows=10):
        """
        Retrieve a given author's UID publications.
        :param author_name: name of author in format "Last First [Middle]"
        :param rows: number of results to return (default is 10)
        :return: A list of UIDs corresponding to papers written by the author
        """
        if not author_name or not author_name.strip():
            logger.debug("Skipping empty author name")
            return None

        last, first, middle = self._parse_author_name(author_name)
        if not last or not first:
            logger.warning(f"Invalid author name format: {author_name}")
            return None

        search_terms = []
        if middle:
            search_terms.append(
                f"{last}+{first}+{middle}[Full Author Name]"
            )
        search_terms.append(f"{last}+{first}[Author]")

        for search_term in search_terms:
            params = {
                "db": "pubmed",
                "term": search_term,
                "retmax": rows,
                "retmode": "JSON",
            }

            try:
                response = self._make_request(self.search_url, params=params)
                data = response.json()

                if "esearchresult" in data and "idlist" in data["esearchresult"]:
                    id_list = data["esearchresult"]["idlist"]
                    if id_list:
                        logger.info(
                            f"Found {len(id_list)} publications for {author_name}"
                        )
                        return id_list

            except Exception as e:
                logger.error(f"PubMed API Request error: {e}")
                continue

        logger.info(f"No publications found for author: {author_name}")
        return None

    def _get_publication_details(self, UIDs, author_name=None, institution=None):
        """
        Get detailed publication information using efetch.
        :param UIDs: list of UIDs
        :param author_name: name of author to check affiliations for
        :param institution: institution name to filter by (if provided)
        :return: list of publication dictionaries
        """
        if not UIDs:
            return None

        params = {"db": "pubmed", "id": ",".join(UIDs), "retmode": "xml"}

        try:
            response = self._make_request(self.fetch_url, params=params)
            root = ET.fromstring(response.text)

            publications = []
            for article in root.findall(".//PubmedArticle"):
                try:
                    title = article.find(".//ArticleTitle").text
                    journal = article.find(".//Journal/Title").text
                    doi = next(
                        (
                            id_elem.text
                            for id_elem in article.findall(".//ArticleId")
                            if id_elem.get("IdType") == "doi"
                        ),
                        "",
                    )

                    pub_date = article.find(".//PubDate")
                    year = pub_date.find("Year")
                    month = pub_date.find("Month")
                    day = pub_date.find("Day")
                    publication_date = (
                        f"{year.text if year is not None else ''}"
                        f"-{month.text if month is not None else ''}"
                        f"-{day.text if day is not None else ''}"
                    )

                    authors = []
                    affiliations = []
                    for author_elem in article.findall(".//Author"):
                        last_name = author_elem.find("LastName")
                        fore_name = author_elem.find("ForeName")
                        full_name = " ".join(
                            filter(
                                None,
                                [
                                    fore_name.text if fore_name is not None else "",
                                    last_name.text if last_name is not None else "",
                                ],
                            )
                        )
                        authors.append(full_name)

                        aff_list = author_elem.findall(
                            ".//AffiliationInfo/Affiliation"
                        )
                        author_affiliations = [
                            aff.text for aff in aff_list if aff.text
                        ]

                        if author_affiliations:
                            affiliations.append(
                                {
                                    "author": full_name,
                                    "affiliations": author_affiliations,
                                }
                            )

                    pub = {
                        "from": "PubMed",
                        "journal": journal,
                        "publication_date": publication_date,
                        "title": title,
                        "authors": ",".join(authors),
                        "affiliations": affiliations,
                        "doi": doi,
                    }
                    publications.append(pub)

                except Exception as e:
                    logger.warning(f"Error processing article: {e}")
                    continue

            if publications:
                logger.info(f"Successfully processed {len(publications)} publications")
            return publications or None

        except Exception as e:
            logger.error(f"Error fetching data from PubMed: {e}")
            return None

    def get_publications_by_author(
        self, author_name, rows=10, institution=None
    ):
        """
        Given the name of an author, search PubMed for works written by that author.
        Returns candidate publications; filtering by author/affiliation is done in post-processing.
        :param author_name: name of author in "Last First [Middle]" format
        :param rows: maximum number of publications to return (default is 10)
        :param institution: unused, kept for interface compatibility
        :return: a list of publication dicts
        """
        logger.debug(f"Fetching publications for author: {author_name}")
        UIDs = self._get_UIDs_by_author(author_name, rows)
        if not UIDs:
            logger.info(f"No publications found for {author_name}")
            return None

        publications = self._get_publication_details(UIDs, author_name, institution)
        if publications:
            logger.debug(f"Successfully retrieved {len(publications)} publications")
        return publications


def search_multiple_authors(authors, rows=10):
    """
    Search PubMed for works written by multiple authors.
    :param authors: list of author names
    :param rows: maximum number of publications to return per author (default is 10)
    :return: a dict {author_name: [publications]} for each author
    """
    pubmed = PubMed()
    all_results = {}

    for author in authors:
        if not author or author.strip() == "" or author == "None None":
            logger.warning(f"Skipping invalid author name: {author}")
            continue
        try:
            publications = pubmed.get_publications_by_author(author, rows)
            if publications:
                all_results[author] = publications
        except Exception as e:
            logger.error(f"Error fetching data for {author}: {e}")
        time.sleep(config.TIME_SLEEP)

    return all_results
