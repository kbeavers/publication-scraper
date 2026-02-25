import os

import pytest
from click.testing import CliRunner

from pubscraper import main
from pubscraper.main import read_input_file, _find_column
from pubscraper.version import __version__

RESPONSE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "responses_main"
)


def get_response_text(response_file):
    with open(response_file) as f:
        response_content = f.read()
    return response_content


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def csv_input(tmp_path):
    csv_file = tmp_path / "test_input.csv"
    csv_file.write_text(
        "root_institution_name,last_name,first_name\n"
        "The University of Texas at Austin,Beavers,Kelsey m\n"
        "The University of Texas at Austin,Carson,James\n"
    )
    return str(csv_file)


@pytest.fixture()
def xlsx_input(tmp_path):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["root_institution_name", "last_name", "first_name"])
    ws.append(["The University of Texas at Austin", "Beavers", "Kelsey m"])
    ws.append(["The University of Texas at Austin", "Carson", "James"])
    xlsx_file = tmp_path / "test_input.xlsx"
    wb.save(xlsx_file)
    return str(xlsx_file)


def test_print_version(runner):
    version_string = f"version {__version__}"
    result = runner.invoke(main.main, ["--version"])
    assert result.exit_code == 0
    assert version_string in result.output


def test_bad_input_file(runner):
    result = runner.invoke(main.main, ["-i", "nonexistent_input.txt"])
    assert result.exit_code == 2


def test_bad_api_selection(runner):
    result = runner.invoke(main.main, ["-a", "BadAPI"])
    assert result.exit_code == 2


def test_print_list_succeeds(runner):
    response_text = get_response_text(os.path.join(RESPONSE_DIR, "list.txt"))
    result = runner.invoke(main.main, ["--list"])
    assert result.exit_code == 0
    assert result.output == response_text


def test_print_help_succeeds(runner):
    result = runner.invoke(main.main, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "--input_file" in result.output


def test_read_csv_input(csv_input):
    name_dict = read_input_file(csv_input)
    assert len(name_dict) == 2
    assert "Beavers Kelsey m" in name_dict
    assert "Carson James" in name_dict
    search_name, institution = name_dict["Beavers Kelsey m"]
    assert search_name == "Beavers Kelsey m"
    assert institution == "The University of Texas at Austin"


def test_read_xlsx_input(xlsx_input):
    name_dict = read_input_file(xlsx_input)
    assert len(name_dict) == 2
    assert "Beavers Kelsey m" in name_dict
    assert "Carson James" in name_dict
    search_name, institution = name_dict["Beavers Kelsey m"]
    assert search_name == "Beavers Kelsey m"
    assert institution == "The University of Texas at Austin"


def test_read_unsupported_format(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("some data")
    with pytest.raises(ValueError, match="Unsupported file format"):
        read_input_file(str(txt_file))


def test_read_csv_skips_empty_names(tmp_path):
    csv_file = tmp_path / "test_empty.csv"
    csv_file.write_text(
        "root_institution_name,last_name,first_name\n"
        "Some Inst,Beavers,Kelsey\n"
        "Some Inst,,\n"
        "Some Inst,Smith,\n"
    )
    name_dict = read_input_file(str(csv_file))
    assert len(name_dict) == 1
    assert "Beavers Kelsey" in name_dict


def test_find_column():
    header = ["root_institution_name", "last_name", "first_name"]
    assert _find_column(header, "last_name") == 1
    assert _find_column(header, "Last_Name") == 1
    assert _find_column(header, "nonexistent") is None


def test_find_column_with_whitespace():
    header = [" root_institution_name ", " last_name ", " first_name "]
    assert _find_column(header, "last_name") == 1
