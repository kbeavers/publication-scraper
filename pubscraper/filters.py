"""
Post-processing filters for publication results.
Removes publications that don't match the target author or lack a UT system affiliation.
"""

import logging

import pubscraper.config as config

logger = logging.getLogger(__name__)


def _parse_search_name(search_name):
    """
    Parse input author string "Last First [Middle]" into (last, first, middle).
    """
    parts = search_name.strip().split()
    if len(parts) < 2:
        return None, None, None
    last = parts[0]
    first = parts[1]
    middle = " ".join(parts[2:]).strip() if len(parts) > 2 else ""
    return last.lower(), first.lower(), middle.lower()


def _parse_publication_author(name_str):
    """
    Parse publication author string into (last, first, middle).
    Handles "First Middle Last" (e.g. "Kelsey M Beavers") and "Last, First" forms.
    """
    if not name_str or not name_str.strip():
        return None, None, None
    s = name_str.strip()
    if "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
        if len(parts) == 2:
            last = parts[0]
            first_mid = parts[1].split()
            first = first_mid[0] if first_mid else ""
            middle = " ".join(first_mid[1:]) if len(first_mid) > 1 else ""
            return last.lower(), first.lower(), middle.lower()
    tokens = s.split()
    if len(tokens) == 1:
        return tokens[0].lower(), "", ""
    if len(tokens) == 2:
        return tokens[1].lower(), tokens[0].lower(), ""
    last = tokens[-1].lower()
    first = tokens[0].lower()
    middle = " ".join(tokens[1:-1]).lower()
    return last, first, middle


def author_name_matches(search_name, publication_author_name):
    """
    Return True if publication_author_name refers to the same person as search_name.
    search_name: "Last First [Middle]" (e.g. "Beavers Kelsey m")
    publication_author_name: e.g. "Kelsey M Beavers" or "Kelsey Beavers"
    """
    search_last, search_first, search_mid = _parse_search_name(search_name)
    pub_last, pub_first, pub_mid = _parse_publication_author(publication_author_name)

    if not search_last or not pub_last:
        return False
    if search_last != pub_last:
        return False
    if not search_first or not pub_first:
        return True
    if search_first[0] != pub_first[0]:
        return False
    if len(search_first) > 1 and len(pub_first) > 1 and search_first != pub_first:
        return False
    if search_mid and pub_mid:
        if search_mid[0] != pub_mid[0]:
            return False
    return True


def _affiliation_matches_ut(affiliation_str):
    """True if affiliation_str contains any UT system keyword."""
    if not affiliation_str:
        return False
    aff_lower = affiliation_str.lower()
    for keyword in config.UT_SYSTEM_KEYWORDS:
        if keyword in aff_lower:
            return True
    return False


def publication_has_ut_affiliation_for_author(pub, search_name):
    """
    Return True if this publication lists the target author with at least one
    UT system affiliation. pub must have "affiliations" list of
    {"author": str, "affiliations": [str]}.
    """
    affiliations = pub.get("affiliations") or []
    for author_info in affiliations:
        author_str = author_info.get("author", "")
        if not author_name_matches(search_name, author_str):
            continue
        for aff in author_info.get("affiliations") or []:
            if _affiliation_matches_ut(aff):
                return True
    return False


def filter_publications_for_author(publications, search_name):
    """
    Keep only publications where the target author (search_name) appears with
    a UT system affiliation.
    """
    filtered = []
    for pub in publications:
        if not isinstance(pub, dict):
            continue
        if publication_has_ut_affiliation_for_author(pub, search_name):
            filtered.append(pub)
    return filtered


def filter_all_publications_by_author_and_affiliation(authors_and_pubs, name_dict):
    """
    In-place filter of authors_and_pubs. For each author block, keep only
    publications that match the author and have a UT system affiliation.

    authors_and_pubs: list of [{display_name: [pub, pub, ...]}]
    name_dict: {display_name: (search_name, institution)}
    """
    for block in authors_and_pubs:
        for display_name, publications in list(block.items()):
            entry = name_dict.get(display_name)
            search_name = entry[0] if entry else display_name
            filtered = filter_publications_for_author(publications, search_name)
            block[display_name] = filtered
            if len(filtered) != len(publications):
                logger.debug(
                    f"Filtered {display_name}: kept {len(filtered)} of {len(publications)}"
                )
    return authors_and_pubs
