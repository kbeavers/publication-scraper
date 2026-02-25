import csv
import json
import logging
import time
import os

import tablib
from openpyxl import load_workbook
from dateutil.parser import parse

import click
from click_loglevel import LogLevel

from pubscraper.version import __version__
import pubscraper.config as config

from pubscraper.APIClasses.PubMed import PubMed
from pubscraper.APIClasses.CrossRef import CrossRef
from pubscraper.filters import filter_all_publications_by_author_and_affiliation


LOG_FORMAT = config.LOGGER_FORMAT_STRING
LOG_LEVEL = config.LOGGER_LEVEL
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

APIS = {
    "PubMed": PubMed(),
    "CrossRef": CrossRef(),
}


def set_logging_level(ctx, param, value):
    """
    Callback function for click that sets the logging level
    """
    logger.setLevel(value)
    return value


def set_log_file(ctx, param, value):
    """
    Callback function for click that sets a log file
    """
    if value:
        fileHandler = logging.FileHandler(value, mode="w")
        logFormatter = logging.Formatter(LOG_FORMAT)
        fileHandler.setFormatter(logFormatter)
        logger.addHandler(fileHandler)
    return value


def list_configured_apis(ctx, param, value):
    """
    Callback function for click that lists available APIs
    """
    if value:
        click.secho("Available endpoints:", underline=True)
        for endpoint in APIS.keys():
            click.secho(f"  {endpoint}", fg="blue")
        ctx.exit()


def read_input_file(input_file):
    """
    Read author data from CSV or XLSX input files.
    Returns a dict of {display_name: [author_search_name, institution]}.

    Expected columns: root_institution_name, last_name, first_name
    The first_name may include a middle initial (e.g. "Kelsey m").
    """
    name_dict = {}
    ext = os.path.splitext(input_file)[1].lower()

    if ext == ".csv":
        with open(input_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                institution = row.get("root_institution_name", "").strip()
                last_name = row.get("last_name", "").strip()
                first_name = row.get("first_name", "").strip()

                if not last_name or not first_name:
                    continue

                display_name = f"{last_name} {first_name}"
                search_name = f"{last_name} {first_name}"
                name_dict[display_name] = [search_name, institution]

    elif ext in (".xlsx", ".xls"):
        workbook = load_workbook(filename=input_file, read_only=True)
        worksheet = workbook.active
        rows = worksheet.rows
        header = [cell.value for cell in next(rows)]

        inst_idx = _find_column(header, "root_institution_name")
        last_idx = _find_column(header, "last_name")
        first_idx = _find_column(header, "first_name")

        for row in rows:
            institution = str(row[inst_idx].value or "").strip() if inst_idx is not None else ""
            last_name = str(row[last_idx].value or "").strip() if last_idx is not None else ""
            first_name = str(row[first_idx].value or "").strip() if first_idx is not None else ""

            if not last_name or not first_name:
                continue

            display_name = f"{last_name} {first_name}"
            search_name = f"{last_name} {first_name}"
            name_dict[display_name] = [search_name, institution]

        workbook.close()
    else:
        raise ValueError(f"Unsupported file format: {ext}. Use .csv or .xlsx")

    return name_dict


def _find_column(header, name):
    """Find a column index by name (case-insensitive)."""
    for i, col in enumerate(header):
        if col and col.strip().lower() == name.lower():
            return i
    return None


@click.command()
@click.version_option(__version__)
@click.option(
    "--log-level",
    type=LogLevel(),
    default=logging.INFO,
    is_eager=True,
    callback=set_logging_level,
    help="Set the log level",
    show_default=True,
)
@click.option(
    "--log-file",
    type=click.Path(writable=True),
    is_eager=True,
    callback=set_log_file,
    help="Set the log file",
)
@click.option(
    "-i",
    "--input_file",
    type=click.Path(exists=True),
    default="example_input.csv",
    help="Specify input file (.csv or .xlsx)",
)
@click.option("-o", "--output_file", default="output", help="Specify output file")
@click.option(
    "-n",
    "--number",
    type=int,
    default=10,
    help="Specify max number of publications to receive for each author",
)
@click.option(
    "--apis",
    "-a",
    type=click.Choice(
        [api for api in APIS.keys()],
        case_sensitive=False,
    ),
    multiple=True,
    default=[api for api in APIS.keys()],
    show_default=True,
    help="Specify APIs to query",
)
@click.option(
    "--list",
    "list_apis",
    is_flag=True,
    default=False,
    is_eager=True,
    callback=list_configured_apis,
    help="Display APIs configured for search queries",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(
        ["json", "csv", "xlsx"],
        case_sensitive=False,
    ),
    default="json",
    show_default=True,
    help="Select the output format from: csv, xlsx, or json.",
)
@click.option(
    "--cutoff_date",
    "-cd",
    type=str,
    default=None,
    show_default=True,
    help="Specify the latest date to pull publications. Example input: 2024 or 2024-05 or 2024-05-10.",
)
def main(
    log_level,
    log_file,
    input_file,
    number,
    output_file,
    apis,
    list_apis,
    format,
    cutoff_date,
):
    logger.debug(f"Logging is set to level {logging.getLevelName(log_level)}")
    if log_file:
        logger.debug(f"Writing logs to {log_file}")

    logger.info(f"Querying the following APIs:\n{', '.join(apis)}")

    try:
        name_dict = read_input_file(input_file)
        logger.debug(f"Number of names in name_dict: {len(name_dict)}")
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Couldn't read input file {input_file}: {e}")
        exit(1)

    logger.debug(f"Requesting {number} publications for each author")

    authors_and_pubs = []

    for display_name, (search_name, institution) in name_dict.items():
        results = {display_name: []}
        authors_pubs = []

        for api_name in apis:
            api = APIS[api_name]
            pubs_found = api.get_publications_by_author(
                search_name, number, institution=institution
            )
            if pubs_found:
                for pub in pubs_found:
                    publication_date_str = pub.get("publication_date", "")

                    if cutoff_date:
                        try:
                            publication_date = (
                                parse(publication_date_str).strftime("%Y-%m-%d")
                                if publication_date_str
                                else ""
                            )
                        except Exception:
                            publication_date = ""
                        if publication_date and publication_date > cutoff_date:
                            authors_pubs.append(pub)
                    else:
                        authors_pubs.append(pub)

        results.update({display_name: authors_pubs})
        authors_and_pubs.append(results)
        time.sleep(config.TIME_SLEEP)

    filter_all_publications_by_author_and_affiliation(authors_and_pubs, name_dict)

    logger.debug(f"Results: {json.dumps(authors_and_pubs, indent=2)}")
    logger.info(f"Exporting the dataset in the specified format: {format} ")

    try:
        os.remove(output_file)
        logger.debug(f"Successfully removed {output_file}")
    except Exception:
        logger.warning(f"Could not remove {output_file}")

    dataset = tablib.Dataset()

    dataset.headers = [
        "From",
        "Author",
        "DOI",
        "Journal",
        "Publication Date",
        "Title",
        "Authors",
    ]

    for author_result in authors_and_pubs:
        for author, publications in author_result.items():
            for pub in publications:
                if isinstance(pub, dict):
                    dataset.append(
                        [
                            pub.get("from", "N/A"),
                            author,
                            pub.get("doi", "N/A"),
                            pub.get("journal", "N/A"),
                            pub.get("publication_date", "N/A"),
                            pub.get("title", "N/A"),
                            pub.get("authors", "N/A"),
                        ]
                    )

    if format == "xlsx":
        with open(f"output.{format}", "wb") as f:
            f.write(dataset.export("xlsx"))
    else:
        with open(f"output.{format}", "w") as f:
            if format == "csv":
                f.write(dataset.export("csv"))
            elif format == "json":
                json.dump(authors_and_pubs, f, indent=4)

    logger.info(f"Data successfully exported to {output_file}.{format}")

    return 0


if __name__ == "__main__":
    main()
