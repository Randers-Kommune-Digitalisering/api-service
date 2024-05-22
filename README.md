# Python app template projekt
Template til nye Python app projekter.
Projekt indeholder en bare bone Flask app
* healthz endpoint
* unit test af healthz endpoint

# Brug af python-app-template
1. Klik på "use this template" og vælg "create a new repository"
2. Udfyld skærmbillede med information om den nye service
3. Åbn dit nye git projekt

# Nyt Python app projekt
Nedenstående relaterer sig til et nyt Python app projekt der er baseret på denne template.

## Udvikling i et Codespace:
1. Gå til det nyoprettede repository i github.
2. Klik på den grønne <>Code knap og vælg "create codespace on \<branch>"
3. Kør ```. ./setup-dev-linux.sh ```, scriptet sætter et virtual environment op og installerer pakkerne i app/requirements.txt og requirements-dev.txt

## Udvikling lokalt:
1. Gå til det nyoprettede repository i github.
2. Klik på den grønne <>Code knap og kopier url'et, clone det med git: ```git clone <url>```
3. Kør ```. ./setup-dev-linux.sh ``` (Linux) eller ```setup-dev-windows.bat``` (Windows), scriptet sætter et virtual environment op og installerer pakkerne i app/requirements.txt og requirements-dev.txt

## Quick start

### Almindelige commands
* Start app'en:  ```python src/main.py```
* Start app'en i docker container: ```docker-compose up```
* Unit tests: ```pytest```
* Unit tests med coverage ```pytest --cov=src```
* Lint: ```flake8 --ignore=E501 src tests --show-source```

### Logning
* Logning til stdout, sat op i [logging.py](/src/utils/logging.py#L12), kaldes i [main](/src/main.py#L27)
* Logning gøres med logger og ikke print() functionen
* Eksempel på brug af logger [her](/src/background_job.py), [her](/src/database.py) og [her](/src/main.py#L35)
* Prometheus: eksempel på gauge [her](/src/utils/logging.py#L9) og brugt [her](/src/main.py#L17)

### Database
* Eksempel i [src/database.py](/src/database.py)
* Nødvendige pakker [src/Dockerfile](/src/Dockerfile#L13)
* Nødvendigt modul  [psycopg2](https://pypi.org/project/psycopg2/), [app/requirements.txt](/src/requirements.txt#L5)
* Opsætning af database lokalt [docker-compose.yml](/docker-compose.yml#L22)
* Nogle alternative moduler kunne være: [SQLAlchemy](https://www.sqlalchemy.org/), [MariaDB](https://pypi.org/project/mariadb/)

### Skriv til filer
* Hvis der skal skrives til filer skal det være på et eksternt mount
* Eksempel til at test lokalt [docker-compose.yml](/docker-compose.yml#L18)

### Kør kode på bestemt tidspunkt eller med interval
* Eksempel i [src/main.py](/src/main.py#L18)
* Nødvendigt modul [src/requirements.txt](/src/requirements.txt#L6)

# TODO
* deploy
* frontend - new template
