Publication Scraper for UTRC Reports
====================================

This tool is designed to pull publication information associated with a given
author, institution, and date range.

## Prerequisites
- Git
- Docker
---
## Installation
```console
> git clone git@github.com:tacc/publication-scraper.git
> cd publication-scraper
> bash run.sh
```
**NOTE: You must first create a `.env` file containing your API keys for each endpoint! See [.env.sample](https://github.com/TACC/publication-scraper/blob/development/.env.sample) for example config.**
## Usage
Execute the script with `run.sh`, which will automatically build the `pubscraper` Docker container (if required) and run the main work script inside the container.
```console
> bash run.sh
Usage: pubscraper [OPTIONS]

Options:
  --version                       Show the version and exit.
  --log-level [NOTSET|DEBUG|INFO|WARNING|ERROR|CRITICAL]
                                  Set the log level  [default: 20]
  --log-file PATH                 Set the log file
  -i, --input_file PATH           Specify input file (.csv or .xlsx)
  -o, --output_file TEXT          Specify output file
  -n, --number INTEGER            Specify max number of publications to receive
                                  for each author
  -a, --apis [PubMed]              Specify APIs to query  [default: PubMed]
  --list                          Display APIs configured for search queries
  -f, --format [json|csv|xlsx]    Select the output format from: csv, xlsx, or
                                  json.  [default: json]
  -cd, --cutoff_date TEXT         Specify the latest date to pull publications.
                                  Example input: 2024 or 2024-05 or 2024-05-10.
  --help                          Show this message and exit.
```
To run the scraper with the default options (using the included sample input), invoke the `pubscraper` command:
```console
> bash run.sh pubscraper
```
By default, the script will request up to 10 publications from each selected
API for each author, writing the results to `output.json` (or `output.csv` /
`output.xlsx` depending on `--format`).

The tool expects a CSV or XLSX file as input, with columns:

root_institution_name| last_name| first_name|...
---|---|---|---
The University of Texas at Austin| Beavers| Kelsey m| ...
The University of Texas at Austin| Carson| James| ...

#### Output format can be specified with the `--format` or `-f` flag

Json output file (default format is json)
```console
> bash run.sh pubscraper -f json
> bash run.sh pubscraper --format json
```

```console
output.json

[
    {
        "Beavers Kelsey m": [
            {
                "from": "PubMed",
                "journal": "Scientific reports",
                "publication_date": "2026-Jan-27",
                "title": "Runaway coral-algal dysbiosis may be responsible for rapid coral tissue loss.",
                "authors": "Ashley M Rossin,Kelsey M Beavers,Carly E Karrick,Jeanne Bloomberg,Sonora Meiling,Gaby E Carpenter,Benjamin H Farmer,Brittney Green,Emily Van Buren,Alex Veglia,Amy Apprill,Marilyn Brandt,Adrienne M S Correa,Ian C Enochs,Stephen R Midway,Erinn M Muller,Laura Mydlarz,Tyler B Smith,Michael S Studivan,Daniel M Holstein",
                "affiliations": [
                    {
                        "author": "Ashley M Rossin",
                        "affiliations": [
                            "Department of Oceanography and Coastal Sciences, Louisiana State University, Baton Rouge, Louisiana, USA. ashley.rossin@noaa.gov.",
                            "Cooperative Institute for Marine and Atmospheric Studies, University of Miami, Miami, Florida, USA. ashley.rossin@noaa.gov.",
                            "NOAA's Atlantic Oceanographic and Meteorological Laboratory, Miami, Florida, USA. ashley.rossin@noaa.gov."
                        ]
                    },
                    ...
        {
        "Carson James": [
            {
                "from": "PubMed",
                "journal": "American journal of physiology. Lung cellular and molecular physiology",
                "publication_date": "2025-Nov-01",
                "title": "Sorted-cell proteomics reveals an AT1-associated epithelial cornification phenotype and suggests endothelial redox imbalance in human bronchopulmonary dysplasia.",
                "authors": "Mereena George Ushakumary,William B Chrisler,Gautam Bandyopadhyay,Heidie Huyck,Brittney L Gorman,Naina Beishembieva,Ariana Pitonzo,Zhenli J Lai,Thomas L Fillmore,Isaac Kwame Attah,Gail Deutsch,Jeffrey M Purkerson,Andrew M Dylag,Ravi S Misra,James P Carson,Joshua N Adkins,Gloria S Pryhuber,Geremy C Clair",
                "affiliations": [
                    {
                        "author": "Mereena George Ushakumary",
                        "affiliations": [
                            "Biological Sciences Division, Earth and Biological Sciences Directorate, Pacific Northwest National Laboratory, Richland, Washington, United States."
                        ]
                    },
                    ...
```


CSV output file 
```console
> bash run.sh pubscraper -f csv
> bash run.sh pubscraper --format csv
```

```console
output.csv

From,Author,DOI,Journal,Publication Date,Title,Authors
PubMed,Beavers Kelsey m,10.1038/s41598-026-35666-4,Scientific reports,2026-Jan-27,Runaway coral-algal dysbiosis may be responsible for rapid coral tissue loss.,"Ashley M Rossin,Kelsey M Beavers,Carly E Karrick,Jeanne Bloomberg,Sonora Meiling,Gaby E Carpenter,Benjamin H Farmer,Brittney Green,Emily Van Buren,Alex Veglia,Amy Apprill,Marilyn Brandt,Adrienne M S Correa,Ian C Enochs,Stephen R Midway,Erinn M Muller,Laura Mydlarz,Tyler B Smith,Michael S Studivan,Daniel M Holstein"
...
PubMed,Carson James,10.1152/ajplung.00098.2025,American journal of physiology. Lung cellular and molecular physiology,2025-Nov-01,Sorted-cell proteomics reveals an AT1-associated epithelial cornification phenotype and suggests endothelial redox imbalance in human bronchopulmonary dysplasia.,"Mereena George Ushakumary,William B Chrisler,Gautam Bandyopadhyay,Heidie Huyck,Brittney L Gorman,Naina Beishembieva,Ariana Pitonzo,Zhenli J Lai,Thomas L Fillmore,Isaac Kwame Attah,Gail Deutsch,Jeffrey M Purkerson,Andrew M Dylag,Ravi S Misra,James P Carson,Joshua N Adkins,Gloria S Pryhuber,Geremy C Clair"
...
```


XLSX output file 
```console
> bash run.sh pubscraper -f xlsx
> bash run.sh pubscraper --format xlsx
```

```console
output.xlsx
From	Author	DOI	Journal	Publication Date	Title	Authors
PubMed	Beavers Kelsey m	10.1038/s41598-026-35666-4	Scientific reports	2026-Jan-27	Runaway coral-algal dysbiosis may be responsible for rapid coral tissue loss.	Ashley M Rossin,Kelsey M Beavers,Carly E Karrick,Jeanne Bloomberg,Sonora Meiling,Gaby E Carpenter,Benjamin H Farmer,Brittney Green,Emily Van Buren,Alex Veglia,Amy Apprill,Marilyn Brandt,Adrienne M S Correa,Ian C Enochs,Stephen R Midway,Erinn M Muller,Laura Mydlarz,Tyler B Smith,Michael S Studivan,Daniel M Holstein
...
PubMed	Carson James	10.1152/ajplung.00098.2025	American journal of physiology. Lung cellular and molecular physiology	2025-Nov-01	Sorted-cell proteomics reveals an AT1-associated epithelial cornification phenotype and suggests endothelial redox imbalance in human bronchopulmonary dysplasia.	Mereena George Ushakumary,William B Chrisler,Gautam Bandyopadhyay,Heidie Huyck,Brittney L Gorman,Naina Beishembieva,Ariana Pitonzo,Zhenli J Lai,Thomas L Fillmore,Isaac Kwame Attah,Gail Deutsch,Jeffrey M Purkerson,Andrew M Dylag,Ravi S Misra,James P Carson,Joshua N Adkins,Gloria S Pryhuber,Geremy C Clair
...
```

#### Output format can be specified with the `--cutoff_date` or `-cd` flag

Adding `--cutoff_date` or `-cd` to command options will specify the latest date to pull publications. 
It can automatically recognize and parse various date formats such as YYYY-MM-DD, YYYY-MM, YYYY.

* For a publication with a date of "2024-05-10", it will be parsed as datetime(2024, 5, 10).
* For a publication with a date of "2024-05", it will be parsed as datetime(2024, 5, 1), with the day defaulting to 1.
* For a publication with a date of "2024", it will be parsed as datetime(2024, 1, 1), with the month and day defaulting to 1.

Cutoff date output file 

```console
> bash run.sh pubscraper -f csv -cd 2024-05
```

```console
output.csv

From,Author,DOI,Journal,Content Type,Publication Date,Title,Authors
PubMed,Dan Stanzione,10.1038/s41592-024-02296-5,Nature Methods,N/A,2024-05-07,Author Correction: brainlife.io: a decentralized and open-source cloud platform to support neuroscience research,"Hayashi S,Caron BA,Heinsfeld AS,Vinci-Booher S,McPherson B,Bullock DN,Bertò G,Niso G,Hanekamp S,Levitas D,Ray K,MacKenzie A,Avesani P,Kitchell L,Leong JK,Nascimento-Silva F,Koudoro S,Willis H,Jolly JK,Pisner D,Zuidema TR,Kurzawski JW,Mikellidou K,Bussalb A,Chaumon M,George N,Rorden C,Victory C,Bhatia D,Aydogan DB,Yeh FC,Delogu F,Guaje J,Veraart J,Fischer J,Faskowitz J,Fabrega R,Hunt D,McKee S,Brown ST,Heyman S,Iacovella V,Mejia AF,Marinazzo D,Craddock RC,Olivetti E,Hanson JL,Garyfallidis E,Stanzione D,Carson J,Henschel R,Hancock DY,Stewart CA,Schnyer D,Eke DO,Poldrack RA,Bollmann S,Stewart A,Bridge H,Sani I,Freiwald WA,Puce A,Port NL,Pestilli F"
Springer,Dan Stanzione,10.1007/s00784-024-05968-w,Clinical Oral Investigations,Article,2024-10-07,Performance of large language artificial intelligence models on solving restorative dentistry and endodontics student assessments,"Künzle, Paul, Paris, Sebastian"
Springer,Dan Stanzione,10.1007/s00395-024-01072-y,Basic Research in Cardiology,Article,2024-10-01,β3-Adrenergic receptor overexpression in cardiomyocytes preconditions mitochondria to withstand ischemia–reperfusion injury,"Fernández-Tocino, Miguel, Pun-Garcia, Andrés, Gómez, Mónica, Clemente-Moragón, Agustín, Oliver, Eduardo, Villena-Gutierrez, Rocío, Trigo-Anca, Sofía, Díaz-Guerra, Anabel, Sanz-Rosa, David, Prados, Belén, Campo, Lara, Andrés, Vicente, Fuster, Valentín, Pompa, José Luis, Cádiz, Laura, Ibañez, Borja"
Springer,Dan Stanzione,10.1007/s44290-024-00034-6,Discover Civil Engineering,Article,2024-08-05,Geophysical and geoenvironmental engineering assessment of contaminated workstation soils in a metamorphic environment,"Ale, Temitayo Olamide, Ale, Taiwo Ayomide, Faseki, Oluyemi Emmanuel, Ajidahun, Johnson, Oluyinka, Ololade Toyin"
```

## Development
### Development Prerequisites
- Python >=3.12
- Poetry (using [asdf-poetry](https://github.com/asdf-community/asdf-poetry) is recommended)
- poetry-bumpversion plugin
```console
> git clone git@github.com:tacc/publication-scraper.git
> cd publication-scraper
> poetry self add poetry-bumpversion
```

Before developing, first install the script with developmend dependencies:
```console
poetry install --with dev
```
Invoke the script with poetry to run during development:
```console
poetry run pubscraper
```

To update the version, use the `poetry version <major|minor|patch>` command (aided by the poetry-bumpversion plugin):
```console
> poetry version patch
Bumping version from 0.1.0 to 0.1.1
poetry_bumpversion: processed file pubscraper/version.py
```
This will update the version in both the `pyproject.toml` and the `pubscraper/version.py` files. If you want to first test the version bump, you can use the `--dry-run` flag:
```console
poetry version patch --dry-run
Bumping version from 0.1.0 to 0.1.1
poetry_bumpversion: processed file pubscraper/version.py
```
After updating the version and committing the changes back to the repo, you should `tag` the repo to match this version:
```console
git tag -a 0.1.1 -m "Version 0.1.1"
git push origin 0.1.1
```
