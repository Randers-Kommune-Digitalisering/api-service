import os
import time
import base64
import logging
import threading
import pathlib
import requests_pkcs12

from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class DeltaClient:
    def __init__(self, cert_base64, cert_pass, base_url, top_adm_org_uuid, relative_assets_path='assets/delta/'):
        self.cert_base64 = cert_base64
        self.cert_pass = cert_pass
        self.base_url = base_url
        self.top_adm_org_uuid = top_adm_org_uuid
        self.assets_path = os.path.join(pathlib.Path(__file__).parent.resolve(), relative_assets_path)
        self.last_adm_org_list_updated = None
        self.adm_org_list = None
        self.cert_path = self._decode_and_write_cert()
        self.payloads = {os.path.splitext(file)[0]: os.path.join(os.path.join(self.assets_path, 'payloads/'), file) for file in os.listdir(os.path.join(self.assets_path, 'payloads/')) if file.endswith('.json')}
        self.headers = {'Content-Type': 'application/json'}

    def _decode_and_write_cert(self):
        try:
            decoded_data = base64.b64decode(self.cert_base64)
            cert_dir = os.path.join(self.assets_path, 'tmp/')
            os.makedirs(cert_dir, exist_ok=True)
            cert_path = os.path.join(cert_dir, 'delta_cert.p12')
            with open(cert_path, 'wb') as file:
                file.write(decoded_data)
                return cert_path
        except Exception as e:
            logger.error(f'Error setting certificate: {e}')
            return

    def _get_cert_path_and_pass(self):
        if self.cert_path is not None and self.cert_pass is not None:
            if os.path.isfile(self.cert_path):
                return self.cert_path, self.cert_pass
        return False, False

    def _get_payload(self, payload_name):
        if payload_name.endswith('.json'):
            payload_name = os.path.splitext(payload_name)[0]
        payload_path = self.payloads.get(payload_name)
        if payload_path:
            with open(payload_path, 'r') as file:
                return file.read()
        else:
            logger.error(f'Payload "{payload_name}" not found.')
            return

    def _set_params(self, payload, params):
        if isinstance(payload, str):
            if isinstance(params, dict):
                for key, value in params.items():
                    key = key.replace('<', '').replace('>', '') if key and '<' in key and '>' in key else key
                    payload = payload.replace(f'<{key}>', value)
            else:
                logger.error('Params must be a dictionary.')
                return
        else:
            logger.error('Payload must be a string.')
            return
        return payload

    def _make_post_request(self, payload):
        cert_path, cert_pass = self._get_cert_path_and_pass()
        if cert_path and cert_pass:
            try:
                path = '/query' if 'queries' in payload else '/graph-query' if 'graphQueries' in payload else '/history' if 'queryList' in payload else None
                if not path:
                    logger.error('Payload is invalid.')
                    return
                url = self.base_url.rstrip('/') + path
                response = requests_pkcs12.post(url, data=payload, headers=self.headers, pkcs12_filename=cert_path, pkcs12_password=cert_pass)
                return response
            except Exception as e:
                logger.error(f'Error making POST request: {e}')
        else:
            logger.error('Certificate path or password is invalid.')
        return

    def _recursive_get_adm_org_units(self, adm_unit_tree_json, list_of_adm_units):
        for adm in adm_unit_tree_json:
            if 'identity' in adm:
                if 'uuid' in adm['identity']:
                    list_of_adm_units.append(adm['identity']['uuid'])
            if 'childrenObjects' in adm:
                for child in adm['childrenObjects']:
                    self._recursive_get_adm_org_units([child], list_of_adm_units)

    def _check_has_employees_and_add_sub_adm_org_units(self, adm_org_list, payload):
        adm_org_dict = {}
        for adm_org in adm_org_list:
            payload_with_params = self._set_params(payload, {'uuid': adm_org})
            if not payload_with_params:
                logger.error('Error setting payload params.')
                return
            r = self._make_post_request(payload_with_params)

            if r.ok:
                json_res = r.json()
                if len(json_res['graphQueryResult'][0]['instances']) > 0:
                    sub_adm_orgs = []
                    self._recursive_get_adm_org_units(json_res['graphQueryResult'][0]['instances'], sub_adm_orgs)
                    sub_adm_orgs = [e for e in sub_adm_orgs if e != adm_org]
                    adm_org_dict[adm_org] = sub_adm_orgs

        # Deletes adm. org. units with sub adm. org. units with employees
        keys_to_remove = []
        for key, value in adm_org_dict.items():
            for sub_adm_org in value:
                if sub_adm_org in adm_org_dict.keys() and key not in keys_to_remove:
                    keys_to_remove.append(key)
                    break

        for key in keys_to_remove:
            adm_org_dict.pop(key)

        return adm_org_dict

    def _get_adm_org_list(self):
        try:
            payload = self._get_payload('adm_org_tree')
            payload_with_params = self._set_params(payload, {'uuid': self.top_adm_org_uuid})
            if not payload_with_params:
                logger.error('Error setting payload params.')
                return
            r = self._make_post_request(payload_with_params)
            if r.ok:
                json_res = r.json()
                if len(json_res['graphQueryResult'][0]['instances']) > 0:
                    adm_org_list = []
                    self._recursive_get_adm_org_units(json_res['graphQueryResult'][0]['instances'], adm_org_list)
                    payload = self._get_payload('adm_ord_with_employees_two_layers_down')
                    return self._check_has_employees_and_add_sub_adm_org_units(adm_org_list, payload)
        except Exception as e:
            logger.error(f'Error getting adm. org. list: {e}')
            return

    def _update_job(self):
        start = time.time()
        adm_org_list = self._get_adm_org_list()
        if adm_org_list:
            self.adm_org_list = adm_org_list
            self.last_adm_org_list_updated = datetime.now()
            logger.info(f'Adm. org. list updated in {str(timedelta(seconds=(time.time() - start)))}')
        else:
            logger.error('Error adm. org. list not updated.')

    def _update_adm_org_list_background(self):
        thread = threading.Thread(target=self._update_job)
        thread.start()

    # returns a dictionaries with the admin organization unit UUID as the key and a list of sub admin organization unit UUIDs as the value
    def get_adm_org_list(self):
        if not self.adm_org_list:
            self._update_job()
        else:
            if self.last_adm_org_list_updated:
                if (datetime.now() - self.last_adm_org_list_updated).total_seconds() > 4 * 60 * 60:
                    self._update_adm_org_list_background()
            else:
                self._update_adm_org_list_background()
        return self.adm_org_list

    # Returns a list of DQ numbers of employees that have changed in the last time_back_minutes
    def get_employees_changed(self, time_back_minutes=30):
        try:
            adm_units_with_employees = []
            for d in self.get_adm_unit_list():
                adm_units_with_employees += d.keys()
            payload_changes = self._get_payload('employee_changes')

            # Delta uses UTC time
            time_back_minutes = timedelta(minutes=time_back_minutes)
            from_time = (datetime.now(tz=timezone.utc) - time_back_minutes).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'
            to_time = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'

            payload_changes_with_params = self._set_params(payload_changes, {'fromTime': from_time, "toTime": to_time})

            r = self._make_post_request(payload_changes_with_params)

            if r.ok:
                employee_list = []
                json_res = r.json()
                if len(json_res['queryResultList'][0]['registrationList']) > 0:
                    for employee in json_res['queryResultList'][0]['registrationList']:
                        if len(employee['typeRefBiList']) > 0:
                            for change in employee['typeRefBiList']:
                                if change['value']['userKey'] == 'APOS-Types-Engagement-TypeRelation-AdmUnit':
                                    if change["value"]["refObjIdentity"]['uuid'] in adm_units_with_employees:
                                        employee_list.append({employee['objectUuid']: change["value"]["refObjIdentity"]['uuid']})

                if len(employee_list) > 0:
                    employee_dq_list = []
                    payload_employee = self._get_payload('employee_dq_number')
                    for employee in employee_list:
                        payload_employee_with_params = self._set_params(payload_employee, {'uuid': next(iter(employee.keys()))})
                        r = self._make_post_request(payload_employee_with_params)
                        if r.ok:
                            json_res = r.json()
                            if len(json_res['queryResults'][0]['instances']) > 0:
                                if len(json_res['queryResults'][0]['instances'][0]["inTypeRefs"]) > 0:
                                    for ref in json_res['queryResults'][0]['instances'][0]["inTypeRefs"]:
                                        if ref['refObjTypeUserKey'] == 'APOS-Types-User':
                                            employee_dq_list.append({ref['refObjIdentity']['userKey']: next(iter(employee.values()))})

                    return employee_dq_list

            return []
        except Exception as e:
            logger.error(f'Error getting employee changes: {e}')
            return
