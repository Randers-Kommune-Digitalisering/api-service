import logging

from utils.config import DELTA_CERT_BASE64, DELTA_CERT_PASS, DELTA_BASE_URL, DELTA_TOP_ADM_UNIT_UUID, NEXUS_CLIENT_ID, NEXUS_CLIENT_SECRET, NEXUS_URL
from delta import DeltaClient
from nexus.nexus_client import NexusClient, NexusRequest, execute_nexus_flow

logger = logging.getLogger(__name__)
nexus_client = NexusClient(NEXUS_CLIENT_ID, NEXUS_CLIENT_SECRET, NEXUS_URL)
delta_client = DeltaClient(cert_base64=DELTA_CERT_BASE64, cert_pass=DELTA_CERT_PASS, base_url=DELTA_BASE_URL, top_adm_org_uuid=DELTA_TOP_ADM_UNIT_UUID)


# ### TEST STUFFF  START ### #

# import json
# get_adm_org_list = delta_client.get_adm_org_list()
# with open('adm_org_list.json', 'w') as f:
#     json.dump(get_adm_org_list, f)

with open('adm_org_list.json', 'r') as f:
    import json
    import datetime
    data = json.load(f)
    delta_client.adm_org_list = data
    delta_client.last_adm_org_list_updated = datetime.datetime.now()


def test():
    ##############################
    id = '9c4bdf85-3af6-4e43-adc5-ee6a5f14a94f'
    admunit = 'f41628ce-0c2b-4ba9-9b3a-e1d212fe3d3b'
    ##############################

    active_org_list = _fetch_all_active_organisations()
    all_delta_orgs = delta_client.get_all_organizations()
    employee_list = []

    payload_employee = delta_client._get_payload('employee_dq_number')
    payload_employee_with_params = delta_client._set_params(payload_employee, {'uuid': id})
    r = delta_client._make_post_request(payload_employee_with_params)
    r.raise_for_status()
    json_res = r.json()
    if len(json_res['queryResults'][0]['instances']) > 0:
        first_res = json_res['queryResults'][0]['instances'][0]
        # Check employee is active
        if first_res['state'] == 'STATE_ACTIVE' and len(first_res['typeRefs']) > 0:
            for relation in first_res['typeRefs']:
                if relation['userKey'] == 'APOS-Types-Engagement-TypeRelation-AdmUnit':
                    # Check if relation to admin unit is correct
                    if relation['refObjIdentity']['uuid'] == admunit:
                        if len(first_res["inTypeRefs"]) > 0:
                            for ref in first_res["inTypeRefs"]:
                                if ref['refObjTypeUserKey'] == 'APOS-Types-User':
                                    # Add employee to dictionary with key DQ number and value admin unit UUID
                                    employee_list.append(({'user': ref['refObjIdentity']['userKey'], 'organizations': [admunit] + delta_client.adm_org_list[admunit]}))

    execute_brugerauth(active_org_list, employee_list[0]['user'], employee_list[0]['organizations'], all_delta_orgs)
# ### TEST STUFFF END ### #


def job():
    try:
        active_org_list = _fetch_all_active_organisations()
        all_delta_orgs = delta_client.get_all_organizations()
        employees_changed_list = delta_client.get_employees_changed()
        for index, employee in enumerate(employees_changed_list):
            logger.info(f"Processing employee {index + 1}/{len(employees_changed_list)}")
            execute_brugerauth(active_org_list, employee['user'], employee['organizations'], all_delta_orgs)
        return True
    except Exception as e:
        logger.error(f"Error in job: {e}")
        return False


def execute_brugerauth(active_org_list: list, primary_identifier: str, input_organisation_uuid_list: list, all_organisation_uuid_list: list = None):
    print(all_organisation_uuid_list)
    professional = _fetch_professional(primary_identifier)
    if not professional:
        logger.error(f"Professional {primary_identifier} not found")
        # logger.info(f"Professional {primary_identifier} not found in Nexus - creating")
        # # TODO: Add filtering for which professionals to create
        # new_professional = _fetch_external_professional(primary_identifier)
        # if new_professional:
        #     professional = nexus_client.post_request(professional['_links']['create']['href'], json=professional)
        #     if professional:
        #         logger.info(f"Professional {primary_identifier} created")
        #     else:
        #         logger.error(f"Failed to create professional {primary_identifier} - skipping")
        #         return
        # else:
        #     logger.error(f"Professional {primary_identifier} not found in external system - skipping")
        #     return

    # Get all assigned organisations for professional as list of dicts - [0] being id, [1] being uuid
    professional_org_list = _fetch_professional_org_syncIds(professional)
    # logger.info(f"Professional current organisation: {professional_org_list}")

    # uuids from active_org_list not found in input_organisation_uuid_list
    organisation_ids_to_assign = [item['id'] for item in active_org_list if item['sync_id'] in input_organisation_uuid_list]

    if len(organisation_ids_to_assign) == 0:
        # TODO: Reomve ? or return None?
        logger.error(f"No organizations found for professional {primary_identifier}")

    # Filter out IDs present in professional_org_list
    unassigned_organisation_ids_to_assign = [org_id for org_id in organisation_ids_to_assign if org_id not in [item['id'] for item in professional_org_list]]

    # Remove duplicates
    unassigned_organisation_ids_to_assign = list(set(unassigned_organisation_ids_to_assign))

    # Get a list of all delta uuid which are not set for the user and get corosponding nexus ids
    uuids_to_remove = list(set(all_organisation_uuid_list) - set(input_organisation_uuid_list))
    organisation_ids_to_remove = [item['id'] for item in active_org_list if item['sync_id'] in uuids_to_remove]

    # Filter out IDs not present in professional_org_list and remove duplicates
    assigned_organisation_ids_to_remove = [org_id for org_id in organisation_ids_to_remove if org_id in [item['id'] for item in professional_org_list]]
    assigned_organisation_ids_to_remove = list(set(assigned_organisation_ids_to_remove))

    try:
        if len(unassigned_organisation_ids_to_assign) > 0:
            # Update the organisations for the professional
            if _update_professional_organisations(professional, unassigned_organisation_ids_to_assign, assigned_organisation_ids_to_remove):
                logger.info(f'Professional {primary_identifier} updated with organisations')
            else:
                logger.error(f'Failed to update professional {primary_identifier} with organisations')
        else:
            logger.info(f'Professional {primary_identifier} already has all organisations - not updating')

        # Get top organisation's supplier
        current = next((item for item in active_org_list if item['sync_id'] == input_organisation_uuid_list[0]), None)
        supplier = current.get('supplier')

        # If it has a supplier update it
        if supplier:
            if _update_professional_supplier(professional, supplier, primary_identifier):
                logger.info(f"Professional {primary_identifier} updated with supplier")
            else:
                logger.error(f"Failed to update professional {primary_identifier} with supplier")
        else:
            logger.info(f'Top organisation for professional {primary_identifier} has a  no supplier - not updating')

        logger.info(f'Professional {primary_identifier} updated sucessfully')
    except Exception as e:
        logger.error(f'Failed to update professional {primary_identifier}: {e}')


def _fetch_professional(primary_identifier):
    # Find professional by query
    if len(nexus_client.find_professional_by_query(primary_identifier)) > 0:
        return nexus_client.find_professional_by_query(primary_identifier)[0]


def _update_professional_organisations(professional, organisation_ids_to_add, organisation_ids_to_remove):
    # Proffesional self
    request1 = NexusRequest(input_response=professional, link_href="self", method="GET")

    # json body with the list of organisation ids that should be added to the professional
    json_body = {
        "added": organisation_ids_to_add,
        "removed": organisation_ids_to_remove
    }

    # Proffesional organisations
    request2 = NexusRequest(link_href="updateOrganizations", method="POST", payload=json_body)

    # Create a list of NexusRequest objects
    professional_org_change_request_list = [
        request1,
        request2
    ]

    # Get all assigned organisations for professional
    professional_org_change_list = execute_nexus_flow(professional_org_change_request_list)
    return professional_org_change_list


def _update_professional_supplier(professional, supplier, primary_identifier):
    # Professional self
    request = NexusRequest(input_response=professional, link_href="self", method="GET")
    professional_self = execute_nexus_flow([request])

    # Professional configuration
    request = NexusRequest(input_response=professional_self, link_href="configuration", method="GET")
    professional_config = execute_nexus_flow([request])

    # Only update supplier if it is None/null
    if not professional_config.get('defaultOrganizationSupplier'):
        professional_config['defaultOrganizationSupplier'] = supplier
        request = NexusRequest(input_response=professional_config, link_href='update', method='PUT', payload=professional_config)
        return execute_nexus_flow([request])
    else:
        logger.info(f'Professional {primary_identifier} already has a supplier - not updating')


def _fetch_professional_org_syncIds(professional):
    # Proffesional self
    request1 = NexusRequest(input_response=professional, link_href="self", method="GET")

    # Proffesional organisations
    request2 = NexusRequest(link_href="organizations", method="GET")

    # Create a list of NexusRequest objects
    professional_org_request_list = [
        request1,
        request2
    ]

    # Get all assigned organisations for professional
    professional_org_list = execute_nexus_flow(professional_org_request_list)
    return _collect_syncIds_from_list_or_org(professional_org_list)


def _fetch_all_active_organisations():
    # Home resource
    home_resource = nexus_client.home_resource()

    # Active organisations
    request1 = NexusRequest(input_response=home_resource, link_href="activeOrganizationsTree", method="GET")
    # Suppliers
    request2 = NexusRequest(input_response=home_resource, link_href="suppliers", method="GET")

    all_active_organisations = execute_nexus_flow([request1])
    all_suppliers = execute_nexus_flow([request2])

    organisation_ids = _collect_syncIds_from_list_or_org(all_active_organisations)
    return _add_supplier_ids(organisation_ids, all_suppliers)


def _collect_syncIds_from_list_or_org(org_input):
    # Collect syncIds from a list of organizations or a single organization.

    if not isinstance(org_input, list):
        org_input = [org_input]  # Wrap the single organization in a list

    return _collect_syncIds_from_list(org_input)


def _collect_syncIds_from_list(org_list: list):
    # Collect syncIds from a list of organizations.

    sync_ids = []
    for org in org_list:
        sync_ids.extend(_collect_syncIds_and_ids_from_org(org))
    return sync_ids


def _collect_syncIds_and_ids_from_org(org: object):
    # Recursively collects syncIds and ids from an organization and its children.
    sync_ids_and_ids = []
    if isinstance(org, dict):
        if 'syncId' in org and org['syncId'] is not None:
            sync_ids_and_ids.append({'id': org['id'], 'sync_id': org['syncId']})
        for child in org.get('children', []):
            sync_ids_and_ids.extend(_collect_syncIds_and_ids_from_org(child))
    else:
        logger.info(f"Unexpected type for org: {type(org)}")
    return sync_ids_and_ids


def _add_supplier_ids(organisation_ids: list, suppliers: list):
    for sup in suppliers:
        if type(sup) is str:
            print(sup)
    for org in organisation_ids:
        supplier = next((item for item in suppliers if item.get('organizationId') == org['id']), None)
        org['supplier'] = supplier
    return organisation_ids
