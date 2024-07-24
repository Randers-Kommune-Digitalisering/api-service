import logging
import requests
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
from requests.auth import HTTPBasicAuth
from utils.config import (SD_USERNAME, SD_PASSWORD, SD_URL,
                              SBSYS_URL, SBSYS_PSAG_PASSWORD, SBSYS_PSAG_USERNAME,
                              SBSIP_PSAG_CLIENT_ID, SBSIP_PSAG_CLIENT_SECRET)
from sd.sd_client import SDClient
from sbsys.sbsys_client import SbsysClient

logger = logging.getLogger(__name__)
sd_client = SDClient(SD_USERNAME, SD_PASSWORD, SD_URL)
sbsys_client = SbsysClient(SBSIP_PSAG_CLIENT_ID, SBSIP_PSAG_CLIENT_SECRET,
                           SBSYS_PSAG_USERNAME, SBSYS_PSAG_PASSWORD, SBSYS_URL)

sd_inst_codes = ["AI", "OV", "RS", "OR",
                 "OB", "OW", "OY", "OQ",
                 "RQ", "OX", "RY", "BQ",
                 "OU", "RO", "OK", "CV",
                 "CZ", "RG", "BX", "RI",
                 "BW", "OZ", "RJ", "RW",
                 "OT", "CU"]

def execute_lukning():
    # person_list = fetch_employments_changed()
    person_list = [{"PersonCivilRegistrationIdentifier": "0211223989",
                   "Employment": [
                        {
                            "EmploymentIdentifier": "00287",
                            "EmploymentStatus": {
                                "ActivationDate": "2024-04-08",
                                "DeactivationDate": "9999-12-31",
                                "EmploymentStatusCode": "8"
                            }
                        },
                        {
                            "EmploymentIdentifier": "00289",
                            "EmploymentDate": "2024-04-08",
                            "AnniversaryDate": "2024-04-08",
                            "EmploymentStatus": {
                                "ActivationDate": "2024-04-08",
                                "DeactivationDate": "9999-12-31",
                                "EmploymentStatusCode": "1"
                            }
                        }
                    ]
                     }]

    for person in person_list:
        cpr = person.get('PersonCivilRegistrationIdentifier', None)

        if not cpr:
            continue

        # Reformat cpr to include '-' -required Sbsys cpr formatting
        cpr = cpr[:6] + "-" + cpr[6:]
        sager = fetch_active_personalesager(cpr)

        if not sager:
            continue

        for sag in sager:
            sag_id = sag.get('Id', None)

            if not sag_id:
                logger.info(f"sag_id is None - No sag id found for sag with cpr: {cpr}")
                continue
            files = fetch_delforloeb_files(sag_id=sag_id, delforloeb_title="01 Ansættelse")





def fetch_employments_changed():
    person_list = []
    # Fetch changed employments foreach SD institution code
    for inst_code in sd_inst_codes:
        path = 'GetEmploymentChanged20111201'

        # Get the current date and format it as DD.MM.YYYY
        effective_date = datetime.now().strftime('%d.%m.%Y')

        # Get the first and last day of the month three months ago using the function
        activation_date, deactivation_date = _get_first_and_last_day_x_months_ago(3)

        # Define the SD params
        params = {
            'InstitutionIdentifier': 'RW',
            'EmploymentStatusIndicator': 'true',
            'PersonCivilRegistrationIdentifier': '',
            'EmploymentIdentifier': '',
            'DepartmentIdentifier': '',
            'ProfessionIndicator': 'false',
            'DepartmentIndicator': 'false',
            'WorkingTimeIndicator': 'false',
            'SalaryCodeGroupIndicator': 'false',
            'SalaryAgreementIndicator': 'false',
            'ActivationDate': activation_date,
            'DeactivationDate': deactivation_date,
            'StatusActiveIndicator': 'true',
            'StatusPassiveIndicator': 'false',
            'submit': 'OK',
            'EffectiveDate': effective_date
        }

        try:
            response = sd_client.post_request(path=path, params=params)

            if not response:
                logger.warning("No response from SD client")
                return None

            if not response['GetEmploymentChanged20111201']:
                logger.warning("GetEmploymentChanged20111201 object not found")
                return None

            person_data = response['GetEmploymentChanged20111201'].get('Person', None)
            if person_data:
                for person in person_data:
                    person_list.append(person)
                response = response['GetEmploymentChanged20111201']
                # pretty_response = json.dumps(response, indent=4)
                # logger.debug(f"Response content:\n{pretty_response}")
            return None
        except Exception as e:
            logger.error(f"Error while fetching employments changed: {e}")
            return None
    return person_list


def fetch_employments():
    return None

def _get_first_and_last_day_x_months_ago(x: int):
    # Get the current date
    today = datetime.today()

    # Calculate the date three months ago
    three_months_ago = today - relativedelta(months=x)

    # Get the first day of the month three months ago, and format date to DD.MM.YYYY
    first_day_of_three_months_ago = three_months_ago.replace(day=1).strftime('%d.%m.%Y')

    # Get the last day of the month three months ago, and format the date to DD.MM.YYYY
    last_day_of_three_months_ago = (first_day_of_three_months_ago + relativedelta(months=1) - relativedelta(days=1)).strftime('%d.%m.%Y')

    return first_day_of_three_months_ago, last_day_of_three_months_ago


def fetch_active_personalesager(cpr: str):

    # sag_search payload
    payload={
        "PrimaerPerson": {
            "CprNummer": cpr
        },
        "SagsTyper": [
            {
                "Id": 5 # Personalesag sagstype
            }
        ]
    }
    try:
        response = sbsys_client.sag_search(payload)

        if not response:
            logger.info(f"sag_serach response is None - No personalesager found for cpr: {cpr}")
            return None

        # Fetch the sag objects from 'Results' in response
        sager = response.get('Results', None)
        if not sager:
            logger.info(f"Results in sag_search is empty - No personalesager found for cpr: {cpr}")
            return None

        # Filter active personalesager by checking if SagsStatus.Navn is 'Aktiv'
        active_personalesager = [sag for sag in sager if sag.get('SagsStatus', {}).get('Navn') == 'Aktiv']

        if not active_personalesager:
            logger.info(f"No active personalesager found for cpr: {cpr}")
            return None

        return active_personalesager

    except Exception as e:
        logger.error(f"Error while fetching active personalesager:  {e}")


    return


def fetch_delforloeb_files(sag_id: int, delforloeb_title: str):
    # Fetch the list of delforloeb for a given sag
    delforloeb_list = sbsys_client.get_request(path=f"api/delforloeb/sag/{sag_id}")
    if not delforloeb_list:
        logger.info(f"No delforloeb found for sag id: {sag_id}")
        return None

    # Fetch the id of the delforloeb with 'Titel' matching the formal parameter delforloeb_title
    delforloeb_id = next(
        (item["ID"] for item in delforloeb_list if item.get("Titel") == delforloeb_title),
        None
    )

    # Check if delforloeb_id is None
    if not delforloeb_id:
        logger.info(f"No delforloeb found with titel: {delforloeb_title}")
        return None

    # Fetch the delforloeb for a given delforloeb id
    delforloeb = sbsys_client.get_request(path=f"api/delforloeb/{delforloeb_id}")

    # Check if delforloeb is None
    if not delforloeb:
        logger.info(f"No delforloeb found with id: {delforloeb_id}")
        return None

    documents = delforloeb.get('Dokumenter', None)

    # Check if list of 'Dokumenter' is Empty
    if not documents:
        logger.info(f"No list of 'Dokumenter' found with delforloeb id: {delforloeb_id}")
        return None

    # List of ansættelsesbrev keywords
    document_keywords = ["Ansættelsesdata"]

    # Create list of documents that have given keywords in 'DokumentNavn'
    filtered_documents = []
    for document in documents:
        files = document.get('Filer', None)
        if not files:
            continue
        document_name = document.get('DokumentNavn', '').lower()  # Use .get() with a default value
        if document_name:  # Check if document_name is not an empty string
            # Check if any keyword is in the document_name
            if any(keyword.lower() in document_name for keyword in document_keywords):
                filtered_documents.append(files)

    logger.debug(filtered_documents)

