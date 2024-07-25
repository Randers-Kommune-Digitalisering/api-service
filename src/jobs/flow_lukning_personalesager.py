import logging
import requests
import json
import json
import re
import PyPDF2
import io
from pdf2image import convert_from_bytes
import pytesseract

from dateutil import parser
from datetime import datetime
from dateutil.relativedelta import relativedelta

from utils.config import (SD_USERNAME, SD_PASSWORD, SD_URL,
                              SBSYS_URL, SBSYS_PSAG_PASSWORD, SBSYS_PSAG_USERNAME,
                              SBSIP_PSAG_CLIENT_ID, SBSIP_PSAG_CLIENT_SECRET)
from sd.sd_client import SDClient
from sbsys.sbsys_client import SbsysClient

logger = logging.getLogger(__name__)
sd_client = SDClient(SD_USERNAME, SD_PASSWORD, SD_URL)
sbsys_client = SbsysClient(SBSIP_PSAG_CLIENT_ID, SBSIP_PSAG_CLIENT_SECRET,
                           SBSYS_PSAG_USERNAME, SBSYS_PSAG_PASSWORD, SBSYS_URL)

date_patterns = [
        r"Du er fra den (d{1,2}. [a-zA-Z]+ \d{4}) ansat",
        r"Du er fra (\d{1,2}\.\s*[a-zA-Z]+\s*\d{4}) ansat",
        r"du fra den (\d{1,2}\.\s*[a-zA-Z]+\s*\d{4}) er ansat",
        r"Du er fra (\d{1,2}\.\s*[a-zA-Z]+\s*\d{4}) til",
        r"Anseet .dato (\d{2}\.\d{2}\.\d{4})",
        r"Startdato: (\d{2}-\d{2}-\d{4})",
        r"Du vil blive ansat i perioden (\d{6})",
        r"fra den (\d{2}\/\d{2}\s\d{4})",
        r"Ansat den (\d{2}\.\d{2}\.\d{4})",
        r"Aftalen\s*begynder\s*\(dato\)\s*:\s*(\d{2}\.\d{2}\.\d{4})",
        r"Praktikforlab\s*(\d{2}-\d{2}-\d{4})",
        r"Tilknytningsdato\s*:\s*(\d{1,2}\.\s*[a-zA-Z]+\s*\d{4})",
        r"Tilknytningsdato : (\d{1,2}\.\s*[a-zA-Z]+\s*\d{4})",
        r"Ansættelsesdato\s*:\s*(\d{1,2}\.\s*[a-zA-Z]+\s*\d{4})",
]
sd_inst_codes = ["AI", "OV", "RS", "OR",
                 "OB", "OW", "OY", "OQ",
                 "RQ", "OX", "RY", "BQ",
                 "OU", "RO", "OK", "CV",
                 "CZ", "RG", "BX", "RI",
                 "BW", "OZ", "RJ", "RW",
                 "OT", "CU"]
active_status_codes = ["0", "1", "3"]
passive_status_codes = ["7", "8", "9", "S"]

def execute_lukning():
    months_ago = 3
    #person_employment_changed_list = fetch_employments_changed(months_ago=months_ago)

    # cpr_list = extract_cpr_and_institution(read_json_file('files/employment_changed.json'))
    #cpr_list = extract_cpr_and_institution(person_employment_changed_list)

    #person_list = fetch_employments(cpr_list)
    # person_list = read_json_file('files/person_employments.json')

    # active_person_list, passive_person_list = filter_persons_by_employment_status(person_list,
    #                                                                              active_status_codes,
    #                                                                              passive_status_codes)
    active_person_list = read_json_file('files/active_persons.json')
    passive_person_list = []
    process_personalesager(active_person_list=active_person_list,
                           passive_person_list=passive_person_list,
                           delforloeb_title="01 Ansættelse")


def process_personalesager(active_person_list: list, passive_person_list: list, delforloeb_title: str):
    for person in passive_person_list:
        break

    for person in active_person_list:
        cpr = person.get('PersonCivilRegistrationIdentifier', None)

        if not cpr:
            continue

        # Reformat cpr to include '-' -required Sbsys cpr formatting
        cpr = cpr[:6] + "-" + cpr[6:]

        # Fetch the person active personalesager
        sager = fetch_active_personalesager(cpr)

        if not sager:
            continue

        # Go through sager and fetch files
        for sag in sager:
            sag_id = sag.get('Id', None)

            if not sag_id:
                logger.info(f"sag_id is None - No sag id found for sag with cpr: {cpr}")
                continue

            # Fetch the files from given delforloeb in current sag
            allowed_filetypes = [".pdf"]
            delforloeb_files = fetch_delforloeb_files(sag_id=sag_id, delforloeb_title=delforloeb_title, allowed_filetypes=allowed_filetypes)

            # Go through the files found in the given delforloeb
            for delforloeb_file in delforloeb_files:
                if isinstance(delforloeb_file, list) and len(delforloeb_file) == 1:
                    delforloeb_file = delforloeb_file[0]
                else:
                    logger.warning(f"Delforloeb file is an array with a size larger than 1 - sag id: {sag_id}")
                    continue

                file_id = delforloeb_file.get('ShortId', None)
                if not file_id:
                    logger.warning(f"file_id is None - Broken file object in sag: {sag_id}")
                    continue

                # Download file
                response = sbsys_client.get_request(path=f"api/fil/{file_id}")
                if not response:
                    logger.error(f"api/fil get request response was None: {sag_id}")
                    return

                file = response.content
                if not file:
                    logger.warning(f"No file was found with file id: {file_id}")
                    continue

                # Use BytesIO to handle file content in memory
                with io.BytesIO(file) as f:
                    logger.debug(f)
                    employment_dates = read_pdf_and_extract_dates(f)
                    # Handle the extracted dates as needed
                    logger.debug(f"Employment Dates: {employment_dates}")
                    return employment_dates

        return


def fetch_employments_changed(months_ago: int):
    # Get the current date and format it as DD.MM.YYYY
    effective_date = datetime.now().strftime('%d.%m.%Y')

    # Get the first and last day of the month three months ago using the function
    activation_date, deactivation_date = _get_first_and_last_day_x_months_ago(months_ago)

    i = 1
    person_list = []
    # Fetch changed employments foreach SD institution code
    for inst_code in sd_inst_codes:
        path = 'GetEmploymentChanged20111201'

        # Define the SD params
        params = {
            'InstitutionIdentifier': inst_code,
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
            if not person_data:
                logger.warning(f"No person data found for inst code: {inst_code}")
                continue

            if isinstance(person_data, dict):
                person_data = [person_data]

            for person in person_data:
                employment = person.get('Employment', None)
                if not employment:
                    logger.warning(f"Person has no employment object: {person} ")
                    continue

                # If 'Employment' is an object, change to array, and add inst_code
                person['Employment'] = process_employments(employment, inst_code)

                # Check if the person is already in the person_list
                existing_person = next((p for p in person_list if p['PersonCivilRegistrationIdentifier'] == person[
                    'PersonCivilRegistrationIdentifier']), None)

                if existing_person:
                    # If person exists, merge employments
                    existing_person['Employment'].extend(person['Employment'])
                else:
                    # If person does not exist, add to person_list
                    person_list.append(person)

            # json_data = json.dumps(person_list, indent=4)
            # logger.debug(json_data)
        except Exception as e:
            logger.error(f"Error while fetching employments changed: {e} \n"
                         f"inst code: {inst_code}")
            return None
        logger.debug("Fetch employment changed: " + str(i) + "/" + str(len(sd_inst_codes)))
        i = i+1
    # Write the flattened data to a JSON file
    write_json('files/employment_changed.json', person_list)
    return person_list


def fetch_employments(cpr_inst_list):
    # Get the current date and format it as DD.MM.YYYY
    effective_date = datetime.now().strftime('%d.%m.%Y')

    person_list = []
    # Fetch changed employments foreach SD institution code
    i = 1
    for cpr_and_inst in cpr_inst_list:
        path = 'GetEmployment20111201'

        cpr = cpr_and_inst[0]
        inst_codes = cpr_and_inst[1]
        logger.debug(cpr)
        logger.debug((inst_codes))
        for inst_code in inst_codes:
            # Define the SD params
            params = {
                'InstitutionIdentifier': inst_code,
                'EmploymentStatusIndicator': 'true',
                'PersonCivilRegistrationIdentifier': cpr,
                'EmploymentIdentifier': '',
                'DepartmentIdentifier': '',
                'ProfessionIndicator': 'false',
                'DepartmentIndicator': 'false',
                'WorkingTimeIndicator': 'false',
                'SalaryCodeGroupIndicator': 'false',
                'SalaryAgreementIndicator': 'false',
                'StatusActiveIndicator': 'true',
                'StatusPassiveIndicator': 'true',
                'submit': 'OK',
                'EffectiveDate': effective_date
            }

            try:
                response = sd_client.get_request(path=path, params=params)

                if not response:
                    logger.warning("No response from SD client")
                    continue

                if not response['GetEmployment20111201']:
                    logger.warning("GetEmployment20111201 object not found")
                    return None

                person_data = response['GetEmployment20111201'].get('Person', None)
                if not person_data:
                    logger.warning(f"No person data found for inst code: {inst_code}")
                    continue

                if isinstance(person_data, dict):
                    person_data = [person_data]

                for person in person_data:
                    employment = person.get('Employment', None)
                    if not employment:
                        logger.warning(f"Person has no employment object: {person} ")
                        continue

                    # If 'Employment' is an object, change to array, and add inst_code
                    person['Employment'] = process_employments(employment, inst_code)

                    # Check if the person is already in the person_list
                    existing_person = next((p for p in person_list if p['PersonCivilRegistrationIdentifier'] == person[
                        'PersonCivilRegistrationIdentifier']), None)

                    if existing_person:
                        # If person exists, merge employments
                        existing_person['Employment'].extend(person['Employment'])
                    else:
                        # If person does not exist, add to person_list
                        person_list.append(person)

                # json_data = json.dumps(person_list, indent=4)
                # logger.debug(json_data)
            except Exception as e:
                logger.error(f"Error while fetching employments changed: {e} \n"
                             f"inst code: {inst_code}")
                return None
        logger.debug("Fetch employment: " + str(i) + "/" + str(len(cpr_inst_list)))
        i = i+1

    # Write the flattened data to a JSON file
    write_json('files/person_employments.json', person_list)
    return person_list


def extract_cpr_and_institution(person_list):
    result = []
    try:
        for person in person_list:
            cpr = person.get("PersonCivilRegistrationIdentifier")
            if cpr is None:
                continue

            # Extract Employment records
            employment_list = person.get("Employment", [])
            if not isinstance(employment_list, list):
                employment_list = [employment_list]

            # Use a set to store unique InstitutionIdentifiers
            institutions = set()
            for employment in employment_list:
                institution = employment.get("InstitutionIdentifier", "")
                if institution:
                    institutions.add(institution)

            # Convert the set to a list
            unique_institutions = list(institutions)

            # Append to result
            result.append((cpr, unique_institutions))

    except Exception as e:
        logger.error(f"Error during extract_cpr_and_institution: {e}")

    return result


def process_employments(employments, inst_code):
    try:
        if isinstance(employments, dict):
            employments = [employments]
        elif not isinstance(employments, list):
            logger.error(f"Unexpected 'Employment' type: {type(employments)}")
            return []

        # Add InstitutionIdentifier to each employment object
        for employment in employments:
            employment["InstitutionIdentifier"] = inst_code
    except Exception as e:
        logger.error(f"Error during process_employments: {e}")
    return employments


def filter_persons_by_employment_status(person_list, active_status_codes, passive_status_codes):
    active_persons = []
    passive_persons = []
    try:
        for person in person_list:
            employment_list = person.get('Employment', [])
            if not isinstance(employment_list, list):
                employment_list = [employment_list]

            # Determine if the person should be classified as active or passive
            is_active = False
            is_passive = False

            for employment in employment_list:
                employment_status_list = employment.get('EmploymentStatus', [])
                if not isinstance(employment_status_list, list):
                    employment_status_list = [employment_status_list]

                for employment_status in employment_status_list:
                    status_code = employment_status.get('EmploymentStatusCode', '')

                    if status_code in active_status_codes:
                        is_active = True
                        break
                    elif status_code in passive_status_codes:
                        is_passive = True

                if is_active:
                    break

            if is_active:
                active_persons.append(person)
            elif is_passive:
                passive_persons.append(person)
    except Exception as e:
        logger.error(f"Error during filter_persons_by_employment_status: {e}")

    write_json('files/active_persons.json', active_persons)
    write_json('files/passive_persons.json', passive_persons)

    return active_persons, passive_persons


def write_json(filename, data):
    # Write data to a JSON file
    with open(filename, 'w') as jsonfile:
        json.dump(data, jsonfile, indent=4)
    logger.debug(f"{filename} file created")


def read_json_file(filename):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"Error: The file '{filename}' does not exist.")
        return None
    except json.JSONDecodeError:
        print("Error: The file could not be decoded as JSON.")
        return None


def _get_first_and_last_day_x_months_ago(x: int):
    try:
        # Get the current date
        today = datetime.today()

        # Calculate the date three months ago
        three_months_ago = today - relativedelta(months=x)

        # Get the first day of the month three months ago
        first_day_of_three_months_ago = three_months_ago.replace(day=1)

        # Get the last day of the month three months ago
        last_day_of_three_months_ago = (first_day_of_three_months_ago + relativedelta(months=1) - relativedelta(days=1))

        # Format the date to DD.MM.YYYY
        first_day_of_three_months_ago.strftime('%d.%m.%Y')
        last_day_of_three_months_ago.strftime('%d.%m.%Y')
        return first_day_of_three_months_ago, last_day_of_three_months_ago
    except Exception as e:
        logger.error(f"Error during _get_first_and_last_day_x_months_ago: {e}")


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


def fetch_delforloeb_files(sag_id: int, delforloeb_title: str, allowed_filetypes: list):
    try:
        # Fetch the list of delforloeb for a given sag
        delforloeb_list = sbsys_client.get_request(path=f"api/delforloeb/sag/{sag_id}")
        if not delforloeb_list:
            logger.warning(f"No delforloeb found for sag id: {sag_id}")
            return None

        # Fetch the id of the delforloeb with 'Titel' matching the formal parameter delforloeb_title
        delforloeb_id = next(
            (item["ID"] for item in delforloeb_list if item.get("Titel") == delforloeb_title),
            None
        )

        # Check if delforloeb_id is None
        if not delforloeb_id:
            logger.warning(f"No delforloeb found with titel: {delforloeb_title}")
            return None

        # Fetch the delforloeb for a given delforloeb id
        delforloeb = sbsys_client.get_request(path=f"api/delforloeb/{delforloeb_id}")

        # Check if delforloeb is None
        if not delforloeb:
            logger.warning(f"No delforloeb found with id: {delforloeb_id}")
            return None

        documents = delforloeb.get('Dokumenter', None)

        # Check if list of 'Dokumenter' is Empty
        if not documents:
            logger.info(f"No list of 'Dokumenter' found with delforloeb id: {delforloeb_id}")
            return None

        # List of ansættelsesbrev keywords
        document_keywords = ["ansættelsesbrev", "ansættelse", "ansættese", "ansæt", "Praktikoversigt",
                        "Tilknytningskontrakt", "timeløn", "uddannelsesaftale"]

        # Create list of documents that have given keywords in 'DokumentNavn'
        filtered_files = []
        for document in documents:
            files = document.get('Filer', None)
            if not files:
                continue

            if allowed_filetypes:
                files = [file for file in files if file.get('Filendelse') in allowed_filetypes]

            document_name = document.get('DokumentNavn', '').lower()
            if document_name:  # Check if document_name is not an empty string
                # Check if any keyword is in the document_name
                if any(keyword.lower() in document_name for keyword in document_keywords):
                    filtered_files.append(files)

        # logger.debug(filtered_files)
        return filtered_files

    except Exception as e:
        logger.error(f"Error during fetch_delforloeb_files: {e}")


def extract_text_from_pdf(file_like):
    text = ""
    reader = PyPDF2.PdfReader(file_like)
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        text += page.extract_text() or ""
    if text != "":
        logger.debug("text found")
    return text


def extract_text_with_ocr(file_like, language='dan'):
    # Convert the PDF file (in bytes) to images
    file_like.seek(0)  # Reset file pointer to the beginning
    images = convert_from_bytes(file_like.read())

    ocr_text = ""
    for image in images:
        ocr_text += pytesseract.image_to_string(image, lang=language)
    if ocr_text != "":
        logger.debug("ocr_text found")
    return ocr_text


def extract_employment_dates(text):
    # Regex pattern to match different date formats

    dates = []
    for pattern in date_patterns:
        logger.debug("trying date pattern: " + pattern)
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            logger.debug("Found match: " + match)
            try:
                parsed_date = parser.parse(match, fuzzy=True)
                formatted_date = parsed_date.strftime("%Y-%m-%d")
                dates.append(formatted_date)
            except Exception as e:
                print(f"Error parsing date '{match}': {e}")

    return dates


def read_pdf_and_extract_dates(file_like):
    # Extract text from PDF using PyPDF2
    text = extract_text_from_pdf(file_like)

    # If no text is extracted, use OCR to extract text
    if not text.strip():
        logger.debug("No text was found, trying ocr")
        file_like.seek(0)  # Reset file pointer to the beginning
        text = extract_text_with_ocr(file_like)

    # Extract dates from the text
    employment_dates = extract_employment_dates(text)
    return employment_dates
