import logging
from datetime import datetime
from nexus.nexus_client import NEXUSClient, NexusRequest, execute_nexus_flow

logger = logging.getLogger(__name__)
nexus_client = NEXUSClient()


def execute_lukning(cpr: str):
    try:
        # Find patient by CPR
        patient = nexus_client.fetch_patient_by_query(query=cpr)
        if not patient:
            logger.error("Patient not found.")
            return

        # _cancel_events(patient)
        # _set_conditions_inactive(patient)
        # _set_pathways_inactive(patient)
        _remove_basket_grants(patient)
        # _remove_patient_grants([2298969])

    except Exception as e:
        logger.error(f"Error in job: {e}")


def _cancel_events(patient):
    try:
        borgerkalender = nexus_client.fetch_borgerkalender(patient)
        # Create a dictionary with stopDate as the current datetime
        current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        stop_date_dict = {"stopDate": current_datetime}

        # Fetch events to stop
        request1 = NexusRequest(input_response=borgerkalender,
                                link_href="getEventsToStop",
                                method="GET",
                                params=stop_date_dict)

        # Execute events_list
        events_list = execute_nexus_flow([request1])

        # Save ids of upcoming events
        event_ids = [event['event']['id'] for event in events_list['events']]

        # If list is empty, stopEvents request will time out
        if not event_ids:
            logger.info("No events to cancel.")
            return

        # Cancel events request
        request1 = NexusRequest(input_response=events_list,
                                link_href="stopEvents",
                                method="POST",
                                payload=event_ids)

        # Execute cancel events
        response = execute_nexus_flow([request1])
        logger.info("Events cancelled")
        return response

    except Exception as e:
        logger.error(f"Error cancelling events: {e}")


def _set_conditions_inactive(patient):
    try:
        active_condition_id = 28748
        inactive_condition_id = 28747

        # Fetch patient conditions
        request1 = NexusRequest(input_response=patient,
                                link_href="patientConditions",
                                method="GET")

        # Execute patient conditions
        patient_conditions = execute_nexus_flow([request1])

        # Save ids of active conditions
        active_conditions = [item for item in patient_conditions if
                             item['id'] and item['state']['id'] == active_condition_id]
        active_conditions_ids = [item['id'] for item in active_conditions]
        logger.info("Active condition IDs: %s", active_conditions_ids)

        if not active_conditions_ids:
            logger.info("No active conditions found.")
            return

        # Convert list of ids to a comma-separated string
        condition_ids_str = ','.join(map(str, active_conditions_ids))
        params = {"conditionIds": condition_ids_str}

        # Create bulk prototype
        request1 = NexusRequest(input_response=patient,
                                link_href="conditionsBulkPrototype",
                                method="GET",
                                params=params)

        # Execute conditions bulk prototype
        conditions_bulk_prototype = execute_nexus_flow([request1])

        if conditions_bulk_prototype is None:
            logger.error("Failed to retrieve conditions bulk prototype.")
            return

        # Prepare payload with state set to inactive
        inactive_state = next(
            (state for state in conditions_bulk_prototype['state']['possibleValues']
             if state['id'] == inactive_condition_id), None)

        if inactive_state is None:
            logger.error("Inactive state not found.")
            return

        # Set state to inactive
        conditions_bulk_prototype['state']['value'] = inactive_state

        # Create new condition observation - observation state set to inactive
        request1 = NexusRequest(input_response=conditions_bulk_prototype,
                                link_href="create",
                                method="POST",
                                payload=conditions_bulk_prototype)

        # Execute condition observation - active conditions are set to inactive
        response = execute_nexus_flow([request1])
        logger.info("Conditions set to inactive")
        return response

    except Exception as e:
        logger.error(f"Error setting conditions inactive: {e}")


def _set_pathways_inactive(patient):
    try:
        afslutning_af_borger_dashboard_id = 6866
        pathway_collection_header_title = ["Alle borgers Handlingsanvisninger", "Skemaer - afslutning af borger"]
        set_pathway_inactive_action_id = 37102
        set_form_inactive_action_id = 30504

        # patient preferences
        request1 = NexusRequest(input_response=patient,
                                link_href="patientPreferences",
                                method="GET")
        patient_preferences = execute_nexus_flow([request1])

        # Reference to Citizen dashboard for "Afslutning af borger"
        citizen_dashboard_afslutning = next((item for item in patient_preferences["CITIZEN_DASHBOARD"] if
                                            item['id'] == afslutning_af_borger_dashboard_id), None)

        # Self object for Citizen dashboard for "Afslutning af borger"
        request1 = NexusRequest(input_response=citizen_dashboard_afslutning,
                                link_href="self",
                                method="GET")
        citizen_dashboard_afslutning = execute_nexus_flow([request1])

        # Fetch the pathway collection matching the header title
        patient_pathway_collection = [item for item in citizen_dashboard_afslutning['view']['widgets'] if
                                      item['headerTitle'] in pathway_collection_header_title]

        # Iterate over the pathway collection, and find pathway references
        for pathway in patient_pathway_collection:
            # Check if the pathway has patient activities
            if 'patientActivities' in pathway['_links']:
                # Patient activities
                request1 = NexusRequest(input_response=pathway,
                                        link_href="patientActivities",
                                        method="GET")
                patient_activities = execute_nexus_flow([request1])

                # Iterate over patient activities, and set status to inactive
                for activity in patient_activities:
                    # activity self
                    request1 = NexusRequest(input_response=activity,
                                            link_href="self",
                                            method="GET")
                    activity_self = execute_nexus_flow([request1])

                    request1 = NexusRequest(input_response=activity_self,
                                            link_href="availableActions",
                                            method="GET")

                    available_actions = execute_nexus_flow([request1])

                    # Fetch the inactive action object
                    inactive_action = next(item for item in available_actions
                                           if item['id'] == set_form_inactive_action_id)
                    request1 = NexusRequest(input_response=inactive_action,
                                            link_href="updateFormData",
                                            method="PUT", payload=activity_self)
                    execute_nexus_flow([request1])

            # Pathway reference
            request1 = NexusRequest(input_response=pathway,
                                    link_href="pathwayReferences",
                                    method="GET")
            pathway_references = execute_nexus_flow([request1])

            # Iterate over the pathway references, and set status to inactive
            for reference in pathway_references:
                # Fetch referenced object of the current pathway
                request2 = NexusRequest(input_response=reference,
                                        link_href="referencedObject",
                                        method="GET")
                pathway_reference = execute_nexus_flow([request1, request2])

                # Fetch available actions for the current pathway
                request1 = NexusRequest(input_response=pathway_reference,
                                        link_href="availableActions",
                                        method="GET")
                available_actions = execute_nexus_flow([request1])

                # Fetch the inactive action object
                inactive_action = next(item for item in available_actions if item['id'] == set_pathway_inactive_action_id)
                request1 = NexusRequest(input_response=inactive_action,
                                        link_href="updateFormData",
                                        method="PUT", payload=pathway_reference)
                execute_nexus_flow([request1])
        logger.info("Pathways set to inactive")
        return True

    except Exception as e:
        logger.error(f"Error setting pathways inactive: {e}")


def _remove_basket_grants(patient):
    # TODO "Kun plantlagt, ikke bestilt"?
    try:
        remove_basket_remove_action_id = 402
        borgerkalender = nexus_client.fetch_borgerkalender(patient)

        request1 = NexusRequest(input_response=borgerkalender,
                                link_href="basketGrants",
                                method="GET")
        basket_grants_search = execute_nexus_flow([request1])

        for basket_grants in basket_grants_search['pages']:
            request1 = NexusRequest(input_response=basket_grants,
                                    link_href="basketGrants",
                                    method="GET")
            basket_grants = execute_nexus_flow([request1])
            for basket_grant in basket_grants:
                basket_types = basket_grant['children']
                for basket_type in basket_types:
                    basket_areas = basket_type['children']
                    for basket_area in basket_areas:
                        grants = basket_area['children']
                        for grant in grants:
                            execute_action = next((item for item in grant['actions']
                                                  if item['id'] == remove_basket_remove_action_id), None)
                            if execute_action is None:
                                logger.error("Basket grant inactive action not found.")
                                return

                            request1 = NexusRequest(input_response=execute_action,
                                                    link_href="executeAction",
                                                    method="PUT", payload=[])
                            execute_nexus_flow([request1])

        logger.info("Basket grants removing")
        return True
    except Exception as e:
        logger.error(f"Error removing basket grants: {e}")


def _remove_patient_grants(grant_id):
    try:
        # Hardcoded value to open the Afslut window for grants/tilstande
        grant_afslut_id = 418

        # Home resource
        home_res = nexus_client.home_resource()

        for id in grant_id:
            # Get patient grant by id
            patient_grant = nexus_client.get_request(home_res["_links"]["patientGrantById"]["href"] + "/" + str(id))

            # Fetch afslut object by grant_afslut_id
            afslut_object = next(item for item in patient_grant["currentWorkflowTransitions"]
                                 if item["id"] == grant_afslut_id)

            # Open the afslut window
            afslut_window = NexusRequest(input_response=afslut_object,
                                         link_href="prepareEdit",
                                         method="GET")
            afslut_window_response = execute_nexus_flow([afslut_window])

            # Save the edit, thus removing the grant
            save_afslut_window = NexusRequest(input_response=afslut_window_response, link_href="save",
                                              method="POST",
                                              payload=afslut_window_response)
            execute_nexus_flow([save_afslut_window])
            logger.info("Grant removed")
        return True

    except Exception as e:
        logger.error(f"Error removing patient grants: {e}")
