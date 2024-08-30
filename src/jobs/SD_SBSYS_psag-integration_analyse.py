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
from datetime import datetime
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


sd_inst_codes = ["AI", "OV", "RS", "OR",
                 "OB", "OW", "OY", "OQ",
                 "RQ", "OX", "RY", "BQ",
                 "OU", "RO", "OK", "CV",
                 "CZ", "RG", "BX", "RI",
                 "BW", "OZ", "RJ", "RW",
                 "OT", "CU"]
active_status_codes = ["0", "1", "3"]
passive_status_codes = ["7", "8", "9", "S"]


months_ago = 3

def execute_lukning():
    validate_matching_employments()
    return
    # person_employment_changed_list = fetch_employments_changed(months_ago=months_ago)
    institution_list = read_json_file('files/institution_list.json')
    person_list = read_json_file('files/employment_changed.json')
    #cpr_list = extract_cpr_and_institution(read_json_file('files/employment_changed.json'),institution_list)
    # cpr_list = extract_cpr_and_institution(person_employment_changed_list)
    test_person = [{
        "PersonCivilRegistrationIdentifier": "2007742986",
        "Employment": []
    }]
    # person_employment_list = fetch_employments(test_person, institution_list)
    person_employment_list = read_json_file('files/person_employments.json')

    # Get the matching employments
    matching_employments = separate_employments(person_employment_list, institution_list)
    write_json('files/matching_employments.json', matching_employments)



    # active_person_list, passive_person_list = filter_persons_by_employment_status(person_employment_list)
    # active_person_list = read_json_file('files/active_persons.json')

def validate_matching_employments():
    matching_employments = read_json_file('files/matching_employments.json')
    total_match_count = 0
    total_unmatch_count = 0
    for emp in matching_employments:
        match_count = emp.get('EmploymentMatchCount', None)
        unmatch_count = emp.get('EmploymentUnmatchCount', None)

        sbsys = emp.get('Sbsys', {})
        if not isinstance(match_count, int) or not isinstance(unmatch_count, int) or not sbsys:
            # logger.warning("match_count, unmatch_count, sbsys is None")
            continue
        sager = sbsys.get('Sager', [])

        # Remove duplicates based on "Ansættelsessted"
        unique_dict_list = []
        seen = set()

        for d in sager:
            ansaettelsessted = d.get("Ansættelsessted")
            if ansaettelsessted not in seen:
                seen.add(ansaettelsessted)
                unique_dict_list.append(d)

        # sager = sbsys.get('SagerCount', 0)
        if match_count + unmatch_count == len(unique_dict_list):
            total_match_count = total_match_count + 1
        else:
            total_unmatch_count = total_unmatch_count + 1
    logger.debug(f"total_match_count: {total_match_count}")
    logger.debug(f"total_unmatch_count: {total_unmatch_count}")


def execute_lukning1():
    institutions_and_departments = read_json_file('files/institutions_and_departments.json')

    person_list = read_json_file('files/person_employments.json')

    path = 'GetOrganization'

    # Define the SD params
    params = {
        'RegionCode': '9R'

    }
    person = []
    # organization = sd_client.get_request(path, params)
    # organization = organization.get('OrganizationInformation', None)
    # organization = organization.get('Region', None)
    # institution = organization.get('Institution', [])
    # write_json('files/institution_list.json', institution)

    institution = read_json_file('files/institution_list.json')
    # Get the matching employments
    matching_employments = separate_employments(person_list, institution)
    write_json('files/matching_employments.json', matching_employments)

    return
    passive_person_list = []
    active_person_list = read_json_file('files/active_persons.json')
    process_personalesager(active_person_list=active_person_list,
                           passive_person_list=passive_person_list,
                           delforloeb_title="01 Ansættelse",
                           institutions_and_departments=institutions_and_departments)
    return

    i = 0
    k = 0
    range_count = 1
    for x in range(range_count):
        sag_id = find_personalesag_by_sd_employment(cpr="2003951483", employment_identifier="13263", inst_code="RG", institutions_and_departments=institutions_and_departments)
        if not sag_id:
            k = k + 1
            logger.debug(f"Unsuccessful personalesag match count: {k} out of {range_count}")
            continue
        i = i + 1
        logger.debug(f"Successful personalesag match count: {i} out of {range_count}")

    logger.debug(f"Final tally of successful personalesag match count: {i} out of {range_count}")
    logger.debug(f"Final tally of unsuccessful personalesag match count: {k} out of {range_count}")

    return
    person_employment_changed_list = fetch_employments_changed(months_ago=months_ago)

    # cpr_list = extract_cpr_and_institution(read_json_file('files/employment_changed.json'))
    cpr_list = extract_cpr_and_institution(person_employment_changed_list)

    person_employment_list = fetch_employments(cpr_list)
    # person_employment_list = read_json_file('files/person_employments.json')

    active_person_list, passive_person_list = filter_persons_by_employment_status(person_employment_list)
    # active_person_list = read_json_file('files/active_persons.json')

    passive_person_list = []
    process_personalesager(active_person_list=active_person_list,
                           passive_person_list=passive_person_list,
                           delforloeb_title="01 Ansættelse",
                           institutions_and_departments=institutions_and_departments)


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


def separate_employments(person_list, inst_list):
    """
    Separates employments into MatchedEmployments and Employments based on the criteria.
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

    for person in person_list:
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
        person['EmploymentMatch'] = matched_employments_list
        person['EmploymentUnmatch'] = remaining_employments
        person['EmploymentMatchCount'] = len(matched_employments_list)
        person['EmploymentUnmatchCount'] = len(remaining_employments)

        cpr = person.get('PersonCivilRegistrationIdentifier', "")
        sager = fetch_active_personalesager(cpr=cpr)

        person['Sbsys'] = {}
        person['Sbsys']['Sager'] = []
        if sager:
            person['Sbsys']['SagerCount'] = len(sager)

            for sag in sager:
                sag_dict = {
                    "Id": sag.get('Id', ""),
                    "Ansættelsessted":  sag.get('Ansaettelsessted', {}).get('Navn', "")
                }
                person['Sbsys']['Sager'].append(sag_dict)
        else:
            person_list.remove(person)
            continue
        if len(matched_employments_list) + len(remaining_employments) == len(person['Sbsys']['Sager']):
            person['DepartmentCompareSuccess'] = True
        else:
            person['DepartmentCompareSuccess'] = False

        person['DepartmentCompare'] = {
            'Ansættelsessted': [sag['Ansættelsessted'] for sag in person['Sbsys']['Sager'] if 'Ansættelsessted' in sag],
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
    return person_list


def process_personalesager(active_person_list: list, passive_person_list: list, delforloeb_title: str, institutions_and_departments: list):
    for person in passive_person_list:
        break

    statistics_json = []
    statistics_csv = []
    i = 0
    active_person_count = len(active_person_list)
    start_index = 11
    for i in range(start_index, len(active_person_list)):
        person = active_person_list[i]
        if i == start_index + 1:
            break
        cpr = person.get('PersonCivilRegistrationIdentifier', None)
        employment_list = person.get('Employment', None)
        employment_result_list = []
        for employment in employment_list:
            employment_status_code = employment.get('EmploymentStatus', None).get('EmploymentStatusCode', None)
            if not employment_status_code in active_status_codes:
                continue
            employment_identifier = employment.get('EmploymentIdentifier', None)
            inst_code = employment.get('InstitutionIdentifier', None)

            # Merge the result of find_personalesag_by_sd_employment into the combined dictionary
            sag = find_personalesag_by_sd_employment(
                cpr=cpr,
                employment_identifier=employment_identifier,
                inst_code=inst_code,
                institutions_and_departments=institutions_and_departments
            )

            sag_id = sag.get('Id', None)

            # Combine the dictionaries into one
            employment_result = {
                'EmploymentIdentifier': employment_identifier,
                'InstitutionIdentifier': inst_code,
                'sag_id': sag_id
            }

            employment_result_list.append(employment_result)

        combined_result = {
            'cpr': cpr,
            'result': employment_result_list
        }
        # Append the combined dictionary to the statistics list
        statistics_json.append(combined_result)

        i = i + 1
        logger.debug(f"Proccession personalesager {i} / {active_person_count}")

        # Reformat cpr to include '-' -required Sbsys cpr formatting
        cpr = cpr[:6] + "-" + cpr[6:]

        # Fetch the person active personalesager
        sager = fetch_active_personalesager(cpr)

        if not sager:
            continue

        personale_sager_count = len(sager)
        sager_closed_count = 0
        employment_count = len(employment_list)
        total_employment_match_count = 0
        active_employment_count = count_parameter_in_nested_list(employment_list,
                                                                 ["EmploymentStatus", "EmploymentStatusCode"],
                                                                 active_status_codes)
        matched_active_employments_count = len(combined_result.get('result', []))
        statistics_csv.append(compile_statistics(cpr, personale_sager_count, sager_closed_count, employment_count,
                                             total_employment_match_count, active_employment_count,
                                             matched_active_employments_count))

    write_json('files/statistics.json', statistics_json)
    write_statistics_to_csv(statistics_csv, 'files/statistics.csv')
    return
    for person in active_person_list:
        if i == 20:
            break


        cpr = person.get('PersonCivilRegistrationIdentifier', None)
        employment_list = person.get('Employment', None)

        if not cpr or not employment_list:
            continue

        # Reformat cpr to include '-' -required Sbsys cpr formatting
        cpr = cpr[:6] + "-" + cpr[6:]

        # Fetch the person active personalesager
        sager = fetch_active_personalesager(cpr)

        if not sager:
            continue

        employment_match_list = []
        # Go through sager and compare ansaettelsessted from sag to DepartmentCode from SD employment
        for sag in sager:
            sag_id = sag.get('Id', None)

            if not sag_id:
                logger.info(f"sag_id is None - No sag id found for sag with cpr: {cpr}")
                continue

            # Fetch the files from given delforloeb in current sag
            allowed_filetypes = [".pdf"]
            # delforloeb_files = fetch_delforloeb_files(sag_id=sag_id, delforloeb_title=delforloeb_title, allowed_filetypes=allowed_filetypes)

            sag_employment_location = sag.get('Ansaettelsessted', None).get('Navn', None)
            if not sag_employment_location:
                logger.info(f"sag_employment_location is None - No Ansaettelsessted found on sag id: {sag_id}")
                continue

            department_codes = find_department_codes(institutions_and_departments, sag_employment_location)
            if not department_codes:
                logger.info(f"department_codes is None - sag with id: {sag_id} {sag_employment_location} does not correspond with any SD departments")
                continue

            employment_location_match_list = filter_employment_by_department(employment_list, department_codes['DepartmentCodes'], sag_id, sag_employment_location)
            write_json(f'files/match_result/{cpr}_employment_location_match_list_{sag_id}.json', employment_location_match_list)
            employment_match_list.append(employment_location_match_list)

            continue # Skip reading files

            # Go through the files found in the given delforloeb
            delforloeb_files = []
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
                    employment_dates = None
                    # Handle the extracted dates as needed
                    logger.debug(f"Employment Dates: {employment_dates}")
                    return employment_dates

        personale_sager_count = len(sager)
        sager_closed_count = 0
        employment_count = len(employment_list)
        total_employment_match_count = len(combine_lists(employment_match_list))
        active_employment_count = count_parameter_in_nested_list(employment_list, ["EmploymentStatus", "EmploymentStatusCode"], active_status_codes)
        matched_active_employments_count = count_parameter_in_nested_list(combine_lists(employment_match_list), ["EmploymentStatus", "EmploymentStatusCode"], active_status_codes)
        # statistics.append(compile_statistics(cpr, personale_sager_count, sager_closed_count, employment_count, total_employment_match_count, active_employment_count, matched_active_employments_count))

        i = i + 1
        logger.debug(f"Proccession personalesager {i} / {active_person_count}")

    # write_statistics_to_csv(statistics)
    return


def find_personalesag_by_sd_employment(cpr: str, employment_identifier: str, inst_code: str, institutions_and_departments: list):
    # Fetch SD employment
    employment = sd_client.GetEmployment20111201(cpr=cpr, employment_identifier=employment_identifier, inst_code=inst_code)
    if not employment:
        logger.warning(f"No employment found with cpr: {cpr}, employment_identifier: {employment_identifier}, or inst_code: {inst_code}")
        return None

    employment_location_code = employment.get('EmploymentDepartment', None).get('DepartmentIdentifier', None)
    if not employment_location_code:
        logger.warning(f"No department identifier found with cpr: {cpr}, employment_identifier: {employment_identifier}, and inst_code: {inst_code}")
        return None

    if not institutions_and_departments:
        logger.warning(f"No institutions_and_departments were found on region code 9R")
        return None

    # Fetch the person active personalesager
    sager = fetch_active_personalesager(cpr)

    if not sager:
        logger.warning(f"No sag found with cpr: {cpr}")
        return

    # Go through sager and compare ansaettelsessted from sag to DepartmentCode from SD employment
    for sag in sager:
        matched_sag = compare_sag_ansaettelssted(sag, employment, institutions_and_departments)
        if matched_sag:
            return matched_sag

    input_strings = [f'{cpr} {employment_identifier}']
    sd_employment_files = fetch_sd_employment_files(input_strings)
    write_json('files/files_match_result/sd_files_result.json', sd_employment_files)

    if not sd_employment_files:
        logger.warning("sd_employment_files is None")
        return None

    sd_file_result = sd_employment_files.get('allResults', None)
    if not sd_file_result:
        logger.warning("sd_file_result is None")
        return None

    if not len(sd_file_result) == 1:
        logger.warning(f"sd_file_result has a length of '{len(sd_file_result)}', but it should have a length of '1'")
        return None

    # Select the first element of the list with one element
    sd_file_result = sd_file_result[0]
    # Check if result is empty
    if not sd_file_result['result']:
        # Go through sager and compare ansaettelsessted from sag to DepartmentCode from SD employment
        for sag in sager:
            matched_sag = compare_sag_ansaettelssted(sag, employment, institutions_and_departments)
            if matched_sag:
                return matched_sag

    # Go through sager and compare file name and archive date with personalesag in SD
    for sag in sager:
        sag_id = sag.get('Id', None)

        if not sag_id:
            logger.info(f"sag_id is None - No sag id found for sag with cpr: {cpr}")
            continue

        # Fetch the files from given delforloeb in current sag
        matched_sag = compare_sag_and_results(sd_file_result, sag)
        if not matched_sag:
            continue

        # logger.debug(matched_sag)
        return matched_sag

    return None


def compare_sag_ansaettelssted(sag: dict, employment, institutions_and_departments):
    sag_id = sag.get('Id', None)

    if not sag_id:
        logger.warning(f"sag_id is None - No sag id found in compare_sag_ansaettelssted")
        return None

    sag_employment_location = sag.get('Ansaettelsessted', None).get('Navn', None)
    if not sag_employment_location:
        logger.info(f"sag_employment_location is None - No Ansaettelsessted found on sag id: {sag_id}")
        return None

    department_codes = find_department_codes(institutions_and_departments, sag_employment_location)
    if not department_codes:
        logger.info(
            f"department_codes is None - sag with id: {sag_id} {sag_employment_location} does not correspond with any SD departments")
        return None

    # Compare the sag_employment_location from personalesag to departmentname
    employment_location_match_list = filter_employment_by_department([employment],
                                                                     department_codes['DepartmentCodes'], sag_id,
                                                                     sag_employment_location)
    if len(employment_location_match_list) == 1 and employment_location_match_list[0]['MatchData']:
        logger.info(f"Match found for ansaettelsessted between employment_identifier, and sag_id: "
                    f"{employment_location_match_list[0].get('EmploymentIdentifier', None)}"
                    f", {sag_id}")
        return sag
    elif len(employment_location_match_list) > 1:
        logger.warning(
            f"employment_location_match_list has a length of: {len(employment_location_match_list)} - It should have a legth of one, since there is only one employment")
    else:
        return None
        logger.debug(
            f"No personalesag match found for employment_identifier, and employment_department: {employment.get('EmploymentIdentifier', None)},"
            f" {employment.get('EmploymentDepartment', None).get('DepartmentIdentifier', None)}"
            f" \nFound sag with id, and location: {sag_id}, {sag_employment_location} - Which has department code {department_codes['DepartmentCodes']}")
    return None


def compare_sag_and_results(sd_result: dict, sag: dict):
    sag_id = sag.get('Id', None)
    if not sag_id:
        logger.warning("compare_sag_and_results received None sag_id")
        return None

    if not sd_result:
        logger.warning("compare_sag_and_results received None sd_result")
        return None

    # Fetch the files from given delforloeb in current sag
    sag_documents = fetch_delforloeb_files(sag_id=sag_id, delforloeb_title="01 Ansættelse",
                                              allowed_filetypes=[], document_keywords=[])
    write_json(f'files/files_match_result/delforloeb_files{sag_id}.json', sag_documents)
    if not sag_documents:
        logger.info(f"sag with id: {sag_id} has no documents")
        return None

    logger.info(f"Comparing for inputString: {sd_result['inputString']}")

    all_match = True  # Assume all documents will match initially

    for document in sag_documents:
        try:
            # Convert RegistreringsDato to the same format as arkivdato for comparison
            registrerings_dato = datetime.strptime(document['RegistreringsDato'], "%Y-%m-%dT%H:%M:%S.%f%z").strftime(
                "%d.%m.%Y")
        except ValueError:
            # Handle cases where there might be no microseconds
            registrerings_dato = datetime.strptime(document['RegistreringsDato'], "%Y-%m-%dT%H:%M:%S%z").strftime("%d.%m.%Y")

        # Remove excess whitespace in document Navn
        sag_navn = ' '.join(document['Navn'].split())

        # Check if there's any item in sd_result that matches both navn and arkivdato
        match_found = False
        for item in sd_result['result']:
            if item['navn'] == sag_navn and item['arkivdato'] == registrerings_dato:
                # logger.info(f"Match found: {item} for sag: {sag_id}")
                match_found = True
                break

        if not match_found:
            # logger.info(f"No match found for document {document} in sag: {sag_id}")
            all_match = False
            break  # If any document doesn't match, we can stop the comparison

    return sag if all_match else None


def fetch_sd_employment_files(input_strings: list):
    try:
        # Make the request and get the response
        response = browserless_sd_personalesag_files(input_strings)

        # Check if the response status code is 200
        if response.status_code == 200:
            # Return the content if the status is 200
            return response.json()  # Assuming the content is JSON
        else:
            # Handle the error case (you can raise an exception or return an error message)
            raise Exception(f"Request failed with status code: {response.status_code}")
    except Exception as e:
        logger.error(f"fetch_sd_employment_files error: {e}")
        return None



def compile_statistics(cpr, sager_count, sager_closed_count, employment_count, matched_employment_count, active_employment_count, matched_active_employments_count):
   return {
        'person_id': cpr,
        'sager_found': sager_count,
        'cases_closed': sager_closed_count,
        'employments_found': employment_count,
        'matched_employments': matched_employment_count,
        'active_employements': active_employment_count,
        'matched_active_employments': matched_active_employments_count,
    }


def write_statistics_to_csv(statistics, filename='files/statistics.csv'):
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['person_id', 'sager_found', 'cases_closed', 'employments_found', 'matched_employments', 'active_employements', 'matched_active_employments']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for stat in statistics:
            writer.writerow(stat)


def combine_lists(nested_lists):
    combined_list = []
    for lst in nested_lists:
        if isinstance(lst, list):
            combined_list.extend(lst)
        else:
            combined_list.append(lst)
    return combined_list


def count_parameter_in_nested_list(nested_list, parameter_names, values):
    def get_nested_value(structure, keys):
        if isinstance(structure, list):
            results = []
            for item in structure:
                result = get_nested_value(item, keys)
                if result is not None:
                    results.extend(result if isinstance(result, list) else [result])
            return results
        elif isinstance(structure, dict):
            value = structure
            for key in keys:
                value = value.get(key, None)
                if value is None:
                    break
            return [value] if value is not None else None
        else:
            return None

    count = 0
    for item in nested_list:
        nested_values = get_nested_value(item, parameter_names)
        if nested_values:
            count += sum(1 for value in nested_values if value in values)
    return count


def fetch_institutions_and_departments(region_identifier):
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


def fetch_inst_codes(inst_list):
    inst_codes = []


def fetch_departments(inst_list):
    department_list = []


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
        logger.debug("Fetch employment changed: " + str(i) + "/" + str(len(sd_inst_codes)))
        i = i+1
    # Write the flattened data to a JSON file
    write_json('files/employment_changed.json', person_list)
    return person_list


def fetch_employments(person_list, inst_list):
    # Get the current date and format it as DD.MM.YYYY
    effective_date = datetime.now().strftime('%d.%m.%Y')

    # Fetch changed employments foreach SD institution code
    i = 1
    employments_in_institutions = []
    result_person_list = []

    for inst in inst_list:
        break
        inst_code = inst['InstitutionCode']
        person_employment_list = sd_client.GetEmployment20070401(cpr="", employment_identifier="", inst_code=inst_code)
        institution = {
            "InstitutionIdentifier": inst_code,
            "Person": person_employment_list,

        }
        if not person_employment_list:
            employments_in_institutions.append(institution)
            continue
        employments_in_institutions.append(institution)
    # write_json('files/employments_in_institutions.json', employments_in_institutions)
    employments_in_institutions = read_json_file('files/employments_in_institutions.json')
    empty_institution_list = [inst for inst in employments_in_institutions if not inst['Person']]
    non_empty_institution_list = [inst for inst in employments_in_institutions if inst['Person']]

    for person_outer in person_list:
        cpr = person_outer['PersonCivilRegistrationIdentifier']
        employments = []
        for inst in non_empty_institution_list:
            persons = inst.get('Person', None)
            inst_identifier = inst['InstitutionIdentifier']
            if isinstance(persons, dict):
                if persons['PersonCivilRegistrationIdentifier'] == cpr:
                    # If 'Employment' is an object, change to array, and add inst_code
                    employments.append(process_employments(persons['Employment'], inst_identifier))
            elif isinstance(persons, list):
                for person_inner in persons:
                    if person_inner['PersonCivilRegistrationIdentifier'] == cpr:
                        # If 'Employment' is an object, change to array, and add inst_code
                        employments.append(process_employments(person_inner['Employment'], inst_identifier))
                        break
        employments = [item for sublist in employments for item in sublist]

        result_person_list.append({
            "PersonCivilRegistrationIdentifier": cpr,
            "Employment": employments
        })
        for inst in empty_institution_list:
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
    write_json('files/person_employments_2007742986.json', result_person_list)
    return result_person_list


def extract_cpr_and_institution(person_list):
    result = []
    person_list = [{
        "PersonCivilRegistrationIdentifier": "2002671908",
        "Employment": [
            {
                "EmploymentIdentifier": "EAAAF",
                "EmploymentDate": "2024-05-27",
                "AnniversaryDate": "2024-05-27",
                "EmploymentDepartment": {
                    "ActivationDate": "2024-05-27",
                    "DeactivationDate": "9999-12-31",
                    "DepartmentIdentifier": "ZBRÅ"
                },
                "EmploymentStatus": {
                    "ActivationDate": "2024-06-22",
                    "DeactivationDate": "9999-12-31",
                    "EmploymentStatusCode": "8"
                },
                "InstitutionIdentifier": "OV"
            }
        ]
    }]
    try:
        for person in person_list:
            cpr = person.get("PersonCivilRegistrationIdentifier")
            if cpr is None:
                continue

            # Extract Employment records
            employment_list = person.get("Employment", [])
            if not isinstance(employment_list, list):
                employment_list = [employment_list]

            # Store InstitutionIdentifier in a list
            institutions = []
            for employment in employment_list:
                institution = employment.get("InstitutionIdentifier", "")
                if not institution:
                    continue

                if institution in institutions:
                    continue

                institutions.append(institution)

            # Append to result
            result.append((cpr, institutions))

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
            employment["Department"]["Level3Parent"] = "hej"
    except Exception as e:
        logger.error(f"Error during process_employments: {e}")
    return employments


def filter_persons_by_employment_status(person_list):
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


def filter_employment_by_department(employment_list, department_code_list, sag_id, department_name):
    filtered_employment = []
    for department_code in department_code_list:
        for employment in employment_list:
            if employment.get('EmploymentDepartment', {}).get('DepartmentIdentifier') == department_code:
                employment['MatchData'] = {
                    'SagId': sag_id,
                    'DepartmentName': department_name,
                    'DepartmentCode': department_code
                }
                filtered_employment.append(employment)
    return filtered_employment


def find_department_codes(inst_list: list, sag_employment_location: str):
    def recursive_search(department):
        if isinstance(department, list):
            codes = []
            for dept in department:
                result = recursive_search(dept)
                if result:
                    codes.extend(result['DepartmentCodes'])
            return {
                'DepartmentCodeName': sag_employment_location,
                'DepartmentCodes': list(set(codes))  # Ensure unique codes
            } if codes else None
        elif isinstance(department, dict):
            codes = []
            department_name = department.get('DepartmentName', '')
            # Ensure department_name is a string and not None
            if isinstance(department_name, str):
                # Check for partial match with full string
                if sag_employment_location in department_name:
                    codes.append(department.get('DepartmentIdentifier'))
                # Check if DepartmentCodeName is exactly 30 characters
                if len(department_name) == 30 and sag_employment_location.startswith(department_name):
                    codes.append(department.get('DepartmentIdentifier'))
            # Recursively search within nested departments
            if 'Department' in department and department['Department'] is not None:
                result = recursive_search(department['Department'])
                if result:
                    codes.extend(result['DepartmentCodes'])
            return {
                'DepartmentCodeName': sag_employment_location,
                'DepartmentCodes': list(set(codes))  # Ensure unique codes
            } if codes else None
        return None

    all_codes = []
    for institution in inst_list:
        result = recursive_search(institution.get('Department', {}))
        if result:
            all_codes.append(result)

    # Combine results for the same department name
    combined_results = {}
    for item in all_codes:
        if item['DepartmentCodeName'] in combined_results:
            combined_results[item['DepartmentCodeName']]['DepartmentCodes'].extend(item['DepartmentCodes'])
            combined_results[item['DepartmentCodeName']]['DepartmentCodes'] = list(
                set(combined_results[item['DepartmentCodeName']]['DepartmentCodes']))
        else:
            combined_results[item['DepartmentCodeName']] = item

    # Convert combined results to a list
    result_list = list(combined_results.values())

    # Return a single object if there is exactly one match, otherwise return the list
    if len(result_list) == 1:
        return result_list[0]
    return result_list


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


def fetch_delforloeb_files(sag_id: int, delforloeb_title: str, allowed_filetypes: list, document_keywords: list):
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

        return documents

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