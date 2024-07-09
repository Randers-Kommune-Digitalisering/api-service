import re
import logging

from utils.config import DELTA_CERT_BASE64, DELTA_CERT_PASS, DELTA_BASE_URL, DELTA_TOP_ADM_UNIT_UUID
from delta import DeltaClient
from nexus.nexus_client import NEXUSClient, NexusRequest, execute_nexus_flow

logger = logging.getLogger(__name__)
nexus_client = NEXUSClient()
delta_client = DeltaClient(cert_base64=DELTA_CERT_BASE64, cert_pass=DELTA_CERT_PASS, base_url=DELTA_BASE_URL, top_adm_org_uuid=DELTA_TOP_ADM_UNIT_UUID)


def job():
    try:
        delta_active_orgs = delta_client.get_adm_org_lists()
        delta_active_orgs_list = list(delta_active_orgs.keys())
        for val in delta_active_orgs.values():
            delta_active_orgs_list.extend(val)

        active_org_list = _fetch_all_active_organisations(delta_active_orgs_list)
        employees_changed_list = delta_client.get_employees_changed()

        for index, employee in enumerate(employees_changed_list):
            logger.info(f"Processing employee {index + 1}/{len(employees_changed_list)}")
            execute_brugerauth(active_org_list, employee['user'], employee['organizations'])
        return True
    except Exception as e:
        logger.error(f"Error in job: {e}")
        return False


def execute_brugerauth(active_org_list: list, primary_identifier: str, input_organisation_uuid_list: list):
    professional = _fetch_professional(primary_identifier)
    if not professional:
        logger.error(f"Professional {primary_identifier} not found")

    # Get all assigned organisations for professional as list of dicts - [0] being id, [1] being uuid
    professional_org_list = _fetch_professional_org_syncIds(professional)
    # logger.info(f"Professional current organisation: {professional_org_list}")

    # uuids from active_org_list not found in input_organisation_uuid_list
    unassigned_organisation_ids = [item['id'] for item in active_org_list if item['sync_id'] in input_organisation_uuid_list]

    if len(unassigned_organisation_ids) == 0:
        logger.error(f"No organizations found for professional {primary_identifier}")

    # Filter out IDs present in professional_org_list
    unassigned_organisation_ids = [org_id for org_id in unassigned_organisation_ids if org_id not in [item['id'] for item in professional_org_list]]

    # Remove duplicates
    unassigned_organisation_ids = list(set(unassigned_organisation_ids))
    # logger.info(f"Professional unassigned organisation: {unassigned_organisation_ids}")

    try:
        if len(unassigned_organisation_ids) > 0:
            # Update the organisations for the professional
            if _update_professional_organisations(professional, unassigned_organisation_ids):
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


def _update_professional_organisations(professional, organisation_id_list):
    # Proffesional self
    request1 = NexusRequest(input_response=professional, link_href="self", method="GET")

    # json body with the list of organisation ids that should be added to the professional
    json_body = {
        "added": organisation_id_list,
        "removed": []
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
        # Find supplier with organizationId equal to org id
        supplier = next((item for item in suppliers if item.get('organizationId') == org['id']), None)
        if supplier:
            org['supplier'] = supplier
        else:
            # Special cases
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
                    # Special case for Borgerteam
                    if org.get('syncId') == "455c1030-8ad4-4da9-98d0-656ce864f2fb":
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
                    # Set supplier to None if not found
                    else:
                        # TODO: add more special cases
                        org['supplier'] = None

    return organisation_ids
