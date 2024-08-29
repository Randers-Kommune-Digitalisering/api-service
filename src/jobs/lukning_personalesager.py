import logging
import json
import re
import PyPDF2
import io
import csv
from pdf2image import convert_from_bytes
import pytesseract
from collections import defaultdict

from dateutil import parser
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from utils.config import (SD_USERNAME, SD_PASSWORD, SD_URL,
                              SBSYS_URL, SBSYS_PSAG_PASSWORD, SBSYS_PSAG_USERNAME,
                              SBSIP_PSAG_CLIENT_ID, SBSIP_PSAG_CLIENT_SECRET)
from utils.browserless import browserless_sd_personalesag_files
from sd.sd_client import SDClient
from sbsys.sbsys_client import SbsysClient

logger = logging.getLogger(__name__)
sd_client = SDClient(SD_USERNAME, SD_PASSWORD, SD_URL)
sbsys_client = SbsysClient(SBSIP_PSAG_CLIENT_ID, SBSIP_PSAG_CLIENT_SECRET,
                           SBSYS_PSAG_USERNAME, SBSYS_PSAG_PASSWORD, SBSYS_URL)

active_status_codes = ["0", "1", "3"]
passive_status_codes = ["7", "8", "9", "S"]

institutions_flattened = []
institutions_nested = []
months_ago = 3


def execute_lukning():
    global institutions_flattened, institutions_nested
    # Update institutions and departments
    # institutions_flattened = fetch_institutions_flattened("9R")
    # institutions_nested = fetch_institution_nested("9R")
    institutions_flattened = read_json_file('files/institutions_and_departments.json')
    institutions_nested = read_json_file('files/institution_list.json')

    # Gather dataset of person with changed employment
    # person_list = fetch_employments_changed(months_ago, institutions_and_departments)
    # person_list = read_json_file('files/employment_changed.json')
    person_list = read_json_file('files/person_employments.json')

    SD_to_sbsys_personalesager = []

    # 1. Fetch all employments for each person
    # 2. Determine whether any of person's personalesager are eligible for closing
    # 3  Prepare SD and SBSYS data to compare place of employment -
    #    by seperating employments into related employments and unrelated employments
    # 4. Match SD employments to SBSYS personalesager
    # 5. Close personalesager that match to employments that became passive x or later months ago, log and save in database
    try:
        for i in range(len(person_list)):
            logger.debug(i)
            person = person_list[i]
            cpr = person.get('PersonCivilRegistrationIdentifier', "")
            employments = person.get('Employment', {})
            # 2. Does person have employments with passive_status_codes?
            if not is_person_eligible_for_closing(employments):
                continue

            # 3. Prepare SD and SBSYS data to compare place of employment
            seperated_employments = separate_employment(person, institutions_nested)

            if not seperated_employments:
                logger.info(f"Employments were not successfully seperated into related and unrelated employments for {cpr}")
                continue

            # 4. Match SD employents to SBSYS personalesager
            matched_employments = match_employments_to_personalesager(seperated_employments)

            if not matched_employments:
                logger.info(f"Employments were not successfully matched to personalesager for cpr {cpr}")
                continue

            if not matched_employments.get('DepartmentCompareSuccess', False):
                logger.info(f"DepartmentCompareSuccess is false for cpr: {cpr}")
                continue

            # 5. Close personalesager
            close_personalesager(matched_employments)

            SD_to_sbsys_personalesager.append(matched_employments)

        for person in person_list:
            break
            employments = fetch_employments(person, institutions_flattened)
        write_json('files/SD_to_sbsys_personalesager.json', SD_to_sbsys_personalesager)
    except Exception as e:
        logger.error(f"Error during execute_lukning: {e}")


def is_person_eligible_for_closing(employments):
    for employment in employments:
        if employment['EmploymentStatus']['EmploymentStatusCode'] in passive_status_codes:
            return True
    return False


def is_sag_eligible_for_closing(sag):

    # Calculate the date that is 3 months ago from today
    three_months_ago = datetime.now() - timedelta(days=3 * 30)

    # Iterate through all employments in the sag
    employments = sag.get('Employments', [])
    if not employments:
        logger.warning("is_sag_eligible_for_closing: employments in sag is empty")
        return False

    if isinstance(employments, dict):
        employments = [employments]

    for employment in employments:
        # Check if the EmploymentStatusCode is not in the passive status codes
        employment_status_code = str(employment.get('EmploymentStatus', {}).get('EmploymentStatusCode'))
        if employment_status_code not in passive_status_codes:
            return False

        # Check if the ActivationDate is within the last 3 months
        activation_date_str = employment.get('EmploymentStatus', {}).get('ActivationDate')
        if activation_date_str:
            activation_date = datetime.strptime(activation_date_str, '%Y-%m-%d')
            if activation_date > three_months_ago:
                return False

    # If all conditions are met, return True
    return True



def fetch_employments_changed(months_ago: int, inst_and_departments: list):
    # Get the current date and format it as DD.MM.YYYY
    effective_date = "01.01.5000"

    # Get the first and last day of the month three months ago using the function
    activation_date, deactivation_date = _get_first_and_last_day_x_months_ago(months_ago)

    i = 1
    person_list = []
    # Fetch changed employments foreach SD institution code
    for inst in inst_and_departments:
        path = 'GetEmploymentChanged20111201'
        inst_code = inst.get('InstitutionIdentifier', "")
        if not inst_code:
            logger.warning("fetch_employments_changed - InstitutionIdentifier not found")
            continue
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
                logger.warning(f"No employment changed data found for inst code: {inst_code}")
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
        logger.debug("Fetch employment changed: " + str(i) + "/" + str(len(inst_and_departments)))
        i = i+1
    # Write the flattened data to a JSON file
    write_json('files/employment_changed.json', person_list)
    return person_list


def fetch_institutions_flattened(region_identifier):
    inst_and_dep = []
    # Get institutions
    path = 'GetInstitution20080201'
    try:
        params = {
            'RegionIdentifier': region_identifier
        }
        response = sd_client.post_request(path=path, params=params)

        if not response:
            logger.warning("No response from SD client")
            return None

        if not response['GetInstitution20080201']:
            logger.warning("GetInstitution20080201 object not found")
            return None

        if not response['GetInstitution20080201']['Region']:
            logger.warning("Region object not found")
            return None
        region = response['GetInstitution20080201']['Region']


        if not region['Institution']:
            logger.warning("Institution list not found")
            return None
        inst_list = region['Institution']

        # Get departments
        path = 'GetDepartment20080201'
        date_today = datetime.now().strftime('%d.%m.%Y')
        for inst in inst_list:
            institution_identifier = inst.get('InstitutionIdentifier', None)
            institution_name = inst.get('InstitutionName', None)

            if not institution_identifier or not institution_name:
                logger.warning("InstitutionIdentifier or InstitutionName is None")
                continue
            # Define the SD params
            params = {
                'InstitutionIdentifier': institution_identifier,
                'ActivationDate': date_today,
                'DeactivationDate': date_today,
                'DepartmentNameIndicator': 'true'
            }

            response = sd_client.post_request(path=path, params=params)

            if not response:
                logger.warning("No response from SD client")
                return None

            if not response['GetDepartment20080201']:
                logger.warning("GetDepartment20080201 object not found")
                return None

            if not response['GetDepartment20080201']['Department']:
                logger.warning("Department list not found")
                return None
            department_list = response['GetDepartment20080201']['Department']

            inst_and_dep_dict = {'InstitutionIdentifier': institution_identifier,
                                 'InstitutionName': institution_name,
                                 'Department': department_list}
            inst_and_dep.append(inst_and_dep_dict)
        write_json('files/institutions_and_departments.json', inst_and_dep)
        return inst_and_dep

    except Exception as e:
        logger.error(f"Error while fetching inst and departments: {e} \n"
                     f"Region code: {region_identifier}")
        return []


def fetch_institution_nested(region_identifier):
    path = 'GetOrganization'

    # Define the SD params
    params = {
        'RegionCode': region_identifier

    }

    organization = sd_client.get_request(path, params)
    organization = organization.get('OrganizationInformation', None)
    organization = organization.get('Region', None)
    institution = organization.get('Institution', [])
    write_json('files/institution_list.json', institution)
    return institution


def process_employments(employments, inst_code):
    try:
        if isinstance(employments, dict):
            employments = [employments]
        elif not isinstance(employments, list):
            logger.error(f"Unexpected 'Employment' type: {type(employments)}")
            return []

        inst_and_department = read_json_file('files/institutions_and_departments.json')
        # Add InstitutionIdentifier to each employment object

        for employment in employments:
            employment["InstitutionIdentifier"] = inst_code
            if employment.get('EmploymentDepartment', {}):
                employment['Department'] = employment.pop('EmploymentDepartment')
            # List comprehension to retrieve the matching department for each employment
            matching_department = [
                dept for inst in inst_and_department for dept in inst.get('Department', [])
                if dept['DepartmentIdentifier'] == employment.get('Department', {}).get('DepartmentIdentifier')
            ]

            if len(matching_department) == 1:
                # If a matching department is found, assign the DepartmentName and DepartmentLevel
                employment['Department']['DepartmentName'] = matching_department[0]['DepartmentName']
                employment["Department"]["DepartmentLevel"] = matching_department[0]['DepartmentLevelCode']
            else:
                logger.warning(f"process_employments: matching_department has a length of {len(matching_department)}, it should have len 1 ")
            employment["Department"]["Level3Parent"] = "test"
    except Exception as e:
        logger.error(f"Error during process_employments: {e}")
    return employments


def find_matching_department(department, department_identifier, latest_level_3_department=None):
    """
    Recursively searches for the department with the given DepartmentIdentifier
    within the provided department structure. Also keeps track of the latest
    level 3 department encountered.
    """

    if isinstance(department, dict):
        # Check if the current department matches the given DepartmentIdentifier
        if department.get('DepartmentCode') == department_identifier:
            return latest_level_3_department, department

        # Check if the current department is level 3 and update the latest_level_3_department
        if department.get('DepartmentLevel') == '3':
            latest_level_3_department = department

        # If 'Department' key exists, recursively search in the sub-departments
        if 'Department' in department:
            sub_department = department['Department']
            if isinstance(sub_department, dict):
                # Recursive call for a nested dictionary
                level_3_dept, matching_dept = find_matching_department(sub_department, department_identifier, latest_level_3_department)
                if matching_dept:
                    return level_3_dept, matching_dept
            elif isinstance(sub_department, list):
                # Recursive call for a list of sub-departments
                for sub_dept in sub_department:
                    level_3_dept, matching_dept = find_matching_department(sub_dept, department_identifier, latest_level_3_department)
                    if matching_dept:
                        return level_3_dept, matching_dept

    # Return None if no matching department is found
    return None, None


def separate_employment(person, inst_list):
    """
    Separates employments into MatchedEmployments and remaining Employments based on the criteria.
    """

    def find_parent_level_3_department(institution, department_identifier):
        """
        Finds the level 3 department in the institution that contains the department
        with the given department_identifier.
        """

        if not institution:
            logger.warning("Institution is None")
            return None

        department_list = institution.get('Department', None)
        if not department_list:
            logger.warning(
                f"Department list in institution {institution.get('AdministrationInstitutionCode', '')} is empty")
            return None

        for department in department_list:
            level_3_dept, matching_dept = find_matching_department(department, department_identifier)
            # If the returned tuple is (None, None), continue with the next iteration
            if level_3_dept is None and matching_dept is None:
                continue
            return level_3_dept, matching_dept

        return None, None

    def find_matching_employments(employments, institution):
        matched = []
        unmatched = []
        department_list = []

        for employment in employments:
            dept_id = employment.get('Department', {}).get('DepartmentIdentifier')
            level_3_and_sub_department = find_parent_level_3_department(institution, dept_id)

            if not level_3_and_sub_department or level_3_and_sub_department == (None, None):
                # Employment doesn't belong to any level 3 sub-department or no match found
                unmatched.append(employment)
                continue

            department_list.append((level_3_and_sub_department, employment))

        # Group by DepartmentCode in the first tuple element (level_3_dept)
        department_code_groups = defaultdict(list)
        for (level_3_dept, sub_dept), employment in department_list:
            dept_code = level_3_dept.get('DepartmentCode')
            department_code_groups[dept_code].append((sub_dept, employment))

        # Find matches where more than one employment exists within the same DepartmentCode group
        for dept_code, grouped_employments in department_code_groups.items():
            if len(grouped_employments) > 1:
                # Add matched employments to the matched list
                matched.append([employment for _, employment in grouped_employments])
            elif len(grouped_employments) == 1:
                unmatched.append([employment for _, employment in grouped_employments])
            else:
                continue


        return matched, unmatched

    employments = person.get('Employment', [])
    matched_employments_list = []
    remaining_employments = []

    # Group employments by InstitutionIdentifier
    institutions_group = {}
    for employment in employments:
        inst_identifier = employment.get('InstitutionIdentifier', "")
        if inst_identifier not in institutions_group:
            institutions_group[inst_identifier] = []
        institutions_group[inst_identifier].append(employment)

    for inst_identifier, institution_employments in institutions_group.items():
        matching_institutions = [institution for institution in inst_list if
                                 institution.get('InstitutionCode') == inst_identifier]
        institution = matching_institutions[0] if matching_institutions else None

        if not institution:
            # If no institution matches, add employments to unmatched
            remaining_employments.extend(institution_employments)
            continue

        matched_employments, unmatched_employments = find_matching_employments(institution_employments, institution)

        if matched_employments:
            matched_employments_list.extend(matched_employments)
        # Add unmatched employments back to the remaining employments
        remaining_employments.extend(unmatched_employments)

        # Assign matched and unmatched employments back to the person object
        person['EmploymentRelated'] = matched_employments_list
        person['EmploymentUnrelated'] = remaining_employments
        person['EmploymentRelatedCount'] = len(matched_employments_list)
        person['EmploymentUnrelatedCount'] = len(remaining_employments)

        cpr = person.get('PersonCivilRegistrationIdentifier', "")
        sager = fetch_active_personalesager(cpr=cpr)

        person['Sbsys'] = {}
        person['Sbsys']['Sager'] = []
        if sager:
            person['Sbsys']['SagerCount'] = len(sager)

            for sag in sager:
                sag_dict = {
                    "Id": sag.get('Id', ""),
                    "Ansaettelsessted":  sag.get('Ansaettelsessted', {}).get('Navn', "")
                }
                person['Sbsys']['Sager'].append(sag_dict)
        else:
            return None
        if len(matched_employments_list) + len(remaining_employments) == len(person['Sbsys']['Sager']):
            person['DepartmentCompareSuccess'] = True
        else:
            person['DepartmentCompareSuccess'] = False

        person['DepartmentCompare'] = {
            'Ansaettelsessted': [sag['Ansaettelsessted'] for sag in person['Sbsys']['Sager'] if 'Ansaettelsessted' in sag],
            'DepartmentIdentifier': [department['Department']['DepartmentName'] for department in
                                     person['Employment'] if
                                     'Department' in department and 'DepartmentName' in department['Department']]
        }

        # Flatten matched_employments_list and combine with remaining_employments
        all_processed_employments = []
        for match_group in matched_employments_list:
            for emp in match_group:
                all_processed_employments.append(emp)
        for unmatched_emp in remaining_employments:
            if isinstance(unmatched_emp, dict):
                all_processed_employments.append(unmatched_emp)
            elif isinstance(unmatched_emp, list):
                for emp in unmatched_emp:
                    all_processed_employments.append(emp)

        # Convert lists to sets of employment identifiers for comparison
        processed_ids = {emp['EmploymentIdentifier'] for emp in all_processed_employments if isinstance(emp, dict)}
        original_ids = {emp['EmploymentIdentifier'] for emp in person.get('Employment', [])}

        # Check if the processed employments match the original 'Employment' list
        if processed_ids == original_ids:
            person['Employment'] = person.get('Employment', [])
        else:
            person['EmploymentMismatch'] = "Mismatch between processed employments and original employments."
            return None
    return person


def fetch_employments(person, inst_list):
    # Get the current date and format it as DD.MM.YYYY
    effective_date = "01.01.5000"

    # Fetch changed employments foreach SD institution code
    i = 1
    result_person_list = []

    cpr = person.get('PersonCivilRegistrationIdentifier')

    for inst in inst_list:
        inst_identifier = inst.get('InstitutionIdentifier', None)
        if not inst_identifier:
            logger.error("fetch_employments InstitutionIdentifier is None")
            return

        path = 'GetEmployment20111201'

        # Define the SD params
        params = {
            'InstitutionIdentifier': inst_identifier,
            'EmploymentStatusIndicator': 'true',
            'PersonCivilRegistrationIdentifier': cpr,
            'EmploymentIdentifier': '',
            'DepartmentIdentifier': '',
            'ProfessionIndicator': 'false',
            'DepartmentIndicator': 'true',
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
                logger.warning(f"No employment data found for inst code: {inst_identifier}")
                continue

            if isinstance(person_data, dict):
                person_data = [person_data]

            for person in person_data:
                employment = person.get('Employment', [])
                if not employment:
                    logger.warning(f"Person has no employment object: {person} ")
                    continue

                # If 'Employment' is an object, change to array, and add inst_code
                person['Employment'] = process_employments(employment, inst_identifier)

                # Check if the person is already in the person_list
                existing_person = next((p for p in result_person_list if p['PersonCivilRegistrationIdentifier'] == person[
                    'PersonCivilRegistrationIdentifier']), None)

                if existing_person:
                    # If person exists, merge employments
                    existing_person['Employment'].extend(person['Employment'])
                else:
                    # If person does not exist, add to person_list
                    result_person_list.append(person)

            # json_data = json.dumps(person_list, indent=4)
            # logger.debug(json_data)
        except Exception as e:
            logger.error(f"Error while fetching employments: {e} \n"
                         f"inst code: {inst_identifier}")
            return None
        logger.debug("Fetch employment: " + str(i) + "/" + str(len(result_person_list)))
        i = i+1

    # Write data to a JSON file
    # write_json('files/person_employments.json', result_person_list)
    return result_person_list


def write_json(filename, data):
    # Write data to a JSON file
    with open(filename, 'w') as jsonfile:
        json.dump(data, jsonfile, ensure_ascii=False, indent=4)
    # logger.debug(f"{filename} file created")


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


def match_employments_to_personalesager(person):
    if not person.get('DepartmentCompareSuccess', False):
        return None

    # Initialize the comparison success flag to True
    comparison_success = True

    # Iterate over each Sager in Sbsys
    for sager in person['Sbsys']['Sager']:
        ansaettelsessted = sager['Ansaettelsessted']
        found_match = False

        # Check in EmploymentMatch
        for employment_group in person['EmploymentRelated']:
            # Check if any employment in the group matches the Ansættelsessted
            for employment in employment_group:
                department = employment.get('Department', {})
                if department.get('DepartmentName') == ansaettelsessted:
                    # If a match is found, assign all employments in this group to the Sager
                    sager['Employments'] = employment_group
                    found_match = True
                    break

            if found_match:
                break  # Stop searching if a match is found

        # If no match was found in EmploymentMatch, check EmploymentUnmatch
        if not found_match:
            for employment_group in person['EmploymentUnrelated']:
                # Check if any employment in the group matches the Ansættelsessted
                if isinstance(employment_group, dict):
                    department = employment_group.get('Department', {})

                    if department.get('DepartmentName') == ansaettelsessted:
                        # If a match is found, assign all employments in this group to the Sager
                        sager['Employments'] = employment_group
                        found_match = True

                elif isinstance(employment_group, list):
                    for employment in employment_group:
                        department = employment.get('Department', {})

                        if department.get('DepartmentName') == ansaettelsessted:
                            # If a match is found, assign all employments in this group to the Sager
                            sager['Employments'] = employment_group
                            found_match = True
                            break
                else:
                    logger.warning(f"employment_group is None")
                    return None
                if found_match:
                    break  # Stop searching if a match is found

        # If no match was found, set comparison_success to False
        if not found_match:
            comparison_success = False

    # Check if all Sbsys Sager have matched employments
    for sager in person['Sbsys']['Sager']:
        if 'Employments' not in sager:
            comparison_success = False
            break

    # Set the comparison result in person
    person['DepartmentCompareSuccess'] = comparison_success
    # After processing, `person['Sbsys']['Sager']` should now include the relevant Employment details
    return person


def fetch_active_personalesager(cpr: str):
    try:
        if len(cpr) == 10:
            cpr = cpr[:6] + '-' + cpr[6:]  # Reformat the CPR

        # sag_search payload
        payload = {
            "PrimaerPerson": {
                "CprNummer": cpr
            }
        }
        response = sbsys_client.sag_search(payload)

        if not response:
            logger.info(f"sag_search response is None - No sager found for cpr: {cpr}")
            return None

        # Fetch the sag objects from 'Results' in response
        sager = response.get('Results', None)
        if not sager:
            logger.info(f"Results in sag_search is empty - No sager found for cpr: {cpr}")
            return None

        # Filter active sager by checking if SagsStatus.Navn is 'Aktiv'
        active_sager = [sag for sag in sager if sag.get('SagsStatus', {}).get('Navn') == 'Aktiv']

        if not active_sager:
            logger.info(f"No active sager found for cpr: {cpr}")
            return None

        # Filter personalesager based on KLE and FACET numbers starting with "81.03.00-G01"
        active_personalesager = [sag for sag in active_sager if sag.get('Nummer', '').startswith('81.03.00-G01')]

        if not active_personalesager:
            logger.info(f"No active personalesager found for cpr: {cpr}")
            return None

        return active_personalesager

    except Exception as e:
        logger.error(f"Error while fetching active personalesager: {e}")
        return None


def close_personalesager(person):
    sager = person.get('Sbsys', {}).get('Sager', {})

    if not sager:
        logger.warning(f"close_personalesager: Sager not found for person,")
        return None

    for sag in sager:
        if not is_sag_eligible_for_closing(sag):
            logger.info(f"Sag is not eligible for closing, Id: {sag.get('Id', "")}")
            sag['isSagClosed'] = False
            continue

        if not check_database_connection():
            logger.warning(f"Database connection failed. Aborting personalesag closing..")
            return None

        sag = close_sag(sag)

    return person


def close_sag(sag):
    sag_id = sag.get('Id', "")
    if not sag_id:
        logger.warning(f"close_sag: sag_id is none")

    #TODO Udfør erindringer, journaliser kladder, sæt status til Lukket
    sag['isSagClosed'] = True
    return sag


def check_database_connection():
    #TODO check database connection, before attempting to close sbsys personalesag
    return True