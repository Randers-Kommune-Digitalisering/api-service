import re
import logging

from utils.config import DELTA_CERT_BASE64, DELTA_CERT_PASS, DELTA_BASE_URL, DELTA_TOP_ADM_UNIT_UUID, NEXUS_CLIENT_ID, NEXUS_CLIENT_SECRET, NEXUS_URL
from delta import DeltaClient
from nexus.nexus_client import NexusClient, NexusRequest, execute_nexus_flow

logger = logging.getLogger(__name__)
nexus_client = NexusClient(NEXUS_CLIENT_ID, NEXUS_CLIENT_SECRET, NEXUS_URL)
delta_client = DeltaClient(cert_base64=DELTA_CERT_BASE64, cert_pass=DELTA_CERT_PASS, base_url=DELTA_BASE_URL, top_adm_org_uuid=DELTA_TOP_ADM_UNIT_UUID)


def job():
    try:
        active_org_list = _fetch_all_active_organisations()
        all_delta_orgs = delta_client.get_all_organizations()
        employees_changed_list = delta_client.get_employees_changed()
        if employees_changed_list:
          logger.info("Employees changed - updating Nexus from external system")
          _sync_orgs_and_users()
          for index, employee in enumerate(employees_changed_list):
              logger.info(f"Processing employee {index + 1}/{len(employees_changed_list)}")
              execute_brugerauth(active_org_list, employee['user'], employee['organizations'], all_delta_orgs)
        else:
          logger.info("No employees changed")
        return True
    except Exception as e:
        logger.error(f"Error in job: {e}")
        return False


def execute_brugerauth(active_org_list: list, primary_identifier: str, input_organisation_uuid_list: list, all_organisation_uuid_list: list = None):
    professional = _fetch_professional(primary_identifier)

    if not professional:
        logger.info(f"Professional {primary_identifier} not found in Nexus - creating")
        new_professional = _fetch_external_professional(primary_identifier)
        if new_professional:
            professional = nexus_client.post_request(new_professional['_links']['create']['href'], json=new_professional)
            if professional:
                logger.info(f"Professional {primary_identifier} created")
            else:
                logger.error(f"Failed to create professional {primary_identifier} - skipping")
                return
        else:
            logger.error(f"Professional {primary_identifier} not found in external system - skipping")
            return

    # Get all assigned organisations for professional as list of dicts - [0] being id, [1] being uuid
    professional_org_list = _fetch_professional_org_syncIds(professional)
    # logger.info(f"Professional current organisation: {professional_org_list}")

    # uuids from active_org_list not found in input_organisation_uuid_list
    organisation_ids_to_assign = [item['id'] for item in active_org_list if item['sync_id'] in input_organisation_uuid_list]

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
        if len(unassigned_organisation_ids_to_assign) > 0 or len(assigned_organisation_ids_to_remove) > 0:
            # Update the organisations for the professional
            if _update_professional_organisations(professional, unassigned_organisation_ids_to_assign, assigned_organisation_ids_to_remove):
                logger.info(f'Professional {primary_identifier} updated with organisations')
            else:
                logger.error(f'Failed to update professional {primary_identifier} with organisations')
        else:
            logger.info(f'Professional {primary_identifier} already has correct organisations assigned - not updating')

        # Get top organisation's supplier
        if input_organisation_uuid_list:
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


def _fetch_external_professional(primary_identifier):
    res = nexus_client.find_external_professional_by_query(primary_identifier)
    if res:
        if 'reason' in res:
            if res['reason'] == 'ProfessionalWithStsSnNotFetched':
                return None
            else:
                raise Exception(f"Error fetching external professional: {res}")
        else:
            res['primaryIdentifier'] = primary_identifier
            res['primaryAddress']['route'] = 'home:importProfessionalFromSts'
            res['activeDirectoryConfiguration']['route'] = 'home:importProfessionalFromSts'
            return res
    else:
        logger.error(f"Error fetching external professional: {res}")


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

    professional_config['defaultOrganizationSupplier'] = supplier
    request = NexusRequest(input_response=professional_config, link_href='update', method='PUT', payload=professional_config)
    return execute_nexus_flow([request])


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


def _fetch_all_active_organisations(delta_orgs: list):
    # Home resource
    home_resource = nexus_client.home_resource()

    # Active organisations
    request1 = NexusRequest(input_response=home_resource, link_href="activeOrganizationsTree", method="GET")

    all_active_organisations = execute_nexus_flow([request1])
    organisation_ids = _collect_syncIds_from_list_or_org(all_active_organisations)

    relevant_organisation_ids = [org for org in organisation_ids if org.get('syncId') in delta_orgs]

    all_suppliers = _get_active_suppliers()

    return _add_supplier_ids(relevant_organisation_ids, all_suppliers)


def _get_active_suppliers():
    home_resource = nexus_client.home_resource()

    request = NexusRequest(input_response=home_resource, link_href="suppliers", method="GET")

    all_suppliers = execute_nexus_flow([request])

    acvite_suppliers = [supplier for supplier in all_suppliers if supplier.get('active')]

    return acvite_suppliers


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
            sync_ids_and_ids.append({'id': org['id'], 'syncId': org['syncId'], 'name': org['name']})
        for child in org.get('children', []):
            sync_ids_and_ids.extend(_collect_syncIds_and_ids_from_org(child))
    else:
        logger.info(f"Unexpected type for org: {type(org)}")
    return sync_ids_and_ids


def _add_supplier_ids(organisation_ids: list, suppliers: list):
    for org in organisation_ids:
        # Special cases
        # Special case for Det Danske Madhus
        if org.get('syncId') == "91eb882f-8a4c-43f1-9417-7b6207f6d806":
            org['supplier'] = None
        # Special case for Borgerteam
        elif org.get('syncId') == "455c1030-8ad4-4da9-98d0-656ce864f2fb":
            supplier = next((item for item in suppliers if item.get('id') == 419), None)
            if not supplier:
                logger.warn(f"Supplier not found for organisation {org['name']}")
            org['supplier'] = supplier
        # Special case for Plejecentret Solbakken
        elif org.get('syncId') == "7a0887f8-e713-4877-8d19-c06a9698f574":
            supplier = next((item for item in suppliers if item.get('id') == 77), None)
            if not supplier:
                logger.warn(f"Supplier not found for organisation {org['name']}")
            org['supplier'] = supplier
        # Special case for Distrikt Kollektivhuset
        elif org.get('syncId') == "bdcc0024-0bae-4017-854b-37d36328c50e":
            supplier = next((item for item in suppliers if item.get('id') == 431), None)
            if not supplier:
                logger.warn(f"Supplier not found for organisation {org['name']}")
            org['supplier'] = supplier
        # Special case for Hospice Randers
        elif org.get('syncId') == "608350bc-e60e-44ab-81b1-22e8757ccefb":
            supplier = next((item for item in suppliers if item.get('id') == 69), None)
            if not supplier:
                logger.warn(f"Supplier not found for organisation {org['name']}")
            org['supplier'] = supplier
        else:
            # Find supplier with organizationId equal to org id
            supplier = next((item for item in suppliers if item.get('organizationId') == org['id']), None)
            if supplier:
                org['supplier'] = supplier
            else:
                # Districts - supplier containing 'dag' and 'distrikt' and org name without 'distrikt' in name
                supplier_list = [item for item in suppliers if all(s in ' '.join(re.sub("[-/_]", " ", item.get('name').lower()).split()) for s in ['dag', 'distrikt', re.sub("[-/_]", " ", org.get('name').lower().replace('distrikt', ''))])]

                if len(supplier_list) == 1:
                    supplier = supplier_list[0]
                    org['supplier'] = supplier
                else:
                    # Find supplier with name equal to org name
                    supplier = next((item for item in suppliers if item.get('name') == org['name']), None)
                    if supplier:
                        org['supplier'] = supplier
                    else:
                        # Find supplier with name containing org name - eg. org: Træningshøjskole supplier: Træningshøjskolen
                        supplier = next((item for item in suppliers if org['name'] in item.get('name')), None)
                        if supplier:
                            org['supplier'] = supplier
                        else:
                            # Find supplier where org name contains supplier name - eg. org: Plejecenter Aldershvile supplier: Aldershvile
                            # Or set supplier to None and don't set supplier for users in that org.
                            supplier = next((item for item in suppliers if item.get('name') in org['name']), None)
                            org['supplier'] = supplier

    return organisation_ids


def _sync_orgs_and_users():
    home_resource = nexus_client.home_resource()
    request1 = NexusRequest(input_response=home_resource, link_href="synchronizeStsOrganizations", method="POST")

    return execute_nexus_flow([request1])
