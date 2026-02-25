import requests
import json
import logging
from dateutil.parser import parse

from ratelimit import limits, sleep_and_retry

from pubscraper.APIClasses.Base import Base
import pubscraper.config as config

logger = logging.getLogger(__name__)


class CrossRef(Base):
    def __init__(self):
        self.base_url = config.CROSSREF_URL

    @sleep_and_retry
    @limits(calls=5, period=1)
    def _make_request(self, url, params):
        try:
            response = requests.get(url, params=params, timeout=10)
        except requests.exceptions.RequestException as e:
            logger.error(f"CrossRef API request error: {e}")
            raise
        response.raise_for_status()
        return response

    def _extract_journal(self, publication_item):
        try:
            return publication_item["container-title"][0]
        except (KeyError, IndexError):
            logger.debug("Error fetching container-title")
            return None

    def _extract_authors(self, publication_item):
        authors = []
        for author in publication_item.get("author", []):
            try:
                name = author["given"] + " " + author["family"]
            except KeyError:
                try:
                    name = author["family"]
                except KeyError:
                    logger.debug(f"No author name found in {author}")
                    return None
            authors.append(name)
        return ",".join(authors)

    def _extract_affiliations(self, publication_item):
        """Extract per-author affiliations from a CrossRef work item (may be empty)."""
        affiliations = []
        for author in publication_item.get("author", []):
            try:
                name = (author.get("given", "") + " " + author.get("family", "")).strip()
            except (KeyError, TypeError):
                continue

            aff_list = author.get("affiliation", [])
            author_affiliations = [
                aff.get("name", "") for aff in aff_list if aff.get("name")
            ]
            affiliations.append({"author": name, "affiliations": author_affiliations})

        return affiliations

    def _extract_publication_date(self, publication_item):
        try:
            date_time = publication_item.get("created", {}).get("date-time", None)
            if date_time:
                return date_time
            return None
        except Exception as e:
            logger.error(f"Error extracting date-time: {e}")
            return None

    def _extract_title(self, publication_item):
        try:
            return publication_item["title"][0]
        except (KeyError, IndexError):
            logger.debug("Error fetching title")
            return None

    def _is_valid_pub(self, pub):
        for item in pub:
            if pub[item] is None:
                return False
        return True

    def _aggregate_publications(self, author_name, rows=10, offset=0):
        """
        Search CrossRef for works by an author name. Returns all items with
        valid metadata; filtering by author/affiliation is done in post-processing.
        """
        if rows < 0:
            raise ValueError("Rows must be a positive number")

        if author_name == "":
            logger.warning("Received empty string for author name, returning None")
            return 0, None

        params = {
            "query.author": author_name.replace(" ", "+"),
            "rows": rows,
            "offset": offset,
            "mailto": "jlh7459@my.utexas.edu",
        }

        try:
            response = self._make_request(self.base_url, params=params)
        except requests.exceptions.RequestException:
            return 0, []

        data = response.json()
        total_results = data["message"]["total-results"]

        publications = []
        for publication_item in data["message"]["items"]:
            affiliations = self._extract_affiliations(publication_item)

            raw_publication_date = self._extract_publication_date(publication_item)
            if raw_publication_date:
                try:
                    publication_date = parse(raw_publication_date).strftime("%Y-%m-%d")
                except Exception:
                    publication_date = None
            else:
                publication_date = None

            journal = self._extract_journal(publication_item)
            title = self._extract_title(publication_item)
            authors = self._extract_authors(publication_item)
            try:
                doi = publication_item["DOI"]
            except KeyError:
                doi = None

            pub = {
                "from": "CrossRef",
                "journal": journal,
                "publication_date": publication_date,
                "title": title,
                "authors": authors,
                "affiliations": affiliations,
                "doi": doi,
            }

            if self._is_valid_pub(pub):
                publications.append(pub)

        return total_results, publications

    def get_publications_by_author(self, author_name, rows=10, institution=None):
        """
        Search CrossRef for works by an author, paginating up to max_pages.
        Returns candidate publications; filtering is done in post-processing.
        """
        if rows < 0:
            raise ValueError("Rows must be a positive number")

        if author_name == "":
            logger.warning("Received empty string for author name, returning None")
            return None

        publications = []
        desired_rows = rows
        offset = 0
        remaining = rows
        page_size = rows
        pages_fetched = 0
        max_pages = config.CROSSREF_MAX_PAGES

        while len(publications) < desired_rows and pages_fetched < max_pages:
            total_results, pubs = self._aggregate_publications(
                author_name, remaining, offset
            )
            if pubs is None:
                return None

            publications += pubs
            pages_fetched += 1

            if total_results <= offset + page_size:
                return publications or None

            offset += page_size
            remaining = desired_rows - len(publications)

            if remaining <= 0:
                break

        if publications:
            logger.debug(
                f"CrossRef: stopped after {pages_fetched} pages for {author_name}"
            )
        return publications or None


def search_multiple_authors(authors, rows=10):
    crossref = CrossRef()
    all_results = {}

    for author in authors:
        if author == "":
            logger.warning("Received empty string for author name, continuing...")
            continue
        try:
            publications = crossref.get_publications_by_author(author, rows)
            all_results[author] = publications
        except Exception as e:
            logger.error(f"Error fetching data for {author}, {e}")

    return all_results
