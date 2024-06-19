import logging

from nexus.nexus_request import NexusRequest, execute_nexus_flow
from nexus.nexus_client import NEXUSClient
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)
nexus_client = NEXUSClient()

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/fetch_lendings', methods=['POST'])
def fetch_lendings_endpoint():

    data = request.get_json()
    cpr = data.get('cpr')
    if not cpr:
        return jsonify({"error": "CPR is required"}), 400

    lendings = _fetch_lendings(cpr)
    return jsonify(lendings)


def _fetch_lendings(cpr):
    patient = nexus_client.fetch_patient_by_query(cpr)
    if not patient:
        return []

    # Fetch patient lendings
    patient_lendings = nexus_client.get_request(patient['_links']['lendings']['href'].lstrip('/') + "&active=true")
    if not patient_lendings:
        return []

    # Save a list of lendings category names
    patient_lendings = [lending['item']['product']['categoryName'] for lending in patient_lendings]
    if not patient_lendings:
        return []

    return patient_lendings
