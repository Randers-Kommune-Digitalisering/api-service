import logging

# from nexus.nexus_request import NexusRequest, execute_nexus_flow
from nexus.nexus_client import NexusClient
from flask import Blueprint, request, jsonify
from utils.config import NEXUS_CLIENT_ID, NEXUS_CLIENT_SECRET, NEXUS_URL
from jobs.nexus_flow_lukning import execute_lukning

logger = logging.getLogger(__name__)
nexus_client = NexusClient(NEXUS_CLIENT_ID, NEXUS_CLIENT_SECRET, NEXUS_URL)

api_nexus_bp = Blueprint('api_nexus', __name__, url_prefix='/api/nexus')


@api_nexus_bp.route('/fetch-lendings', methods=['POST'])
def fetch_lendings_endpoint():
    data = request.get_json()
    cpr = data.get('cpr')
    if not cpr:
        return jsonify({"error": "CPR is required"}), 400

    lendings = _fetch_lendings(cpr)
    return jsonify(lendings), 200


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


@api_nexus_bp.route('/execute-lukning', methods=['POST'])
def _execute_lukning():
    data = request.get_json()
    cpr = data.get('cpr')
    if not cpr:
        return jsonify({"error": "CPR is required"}), 400
    try:
        lukning = execute_lukning(cpr)
        return jsonify(lukning), 200
    except Exception as e:
        logger.error(f"Failed to execute lukning: {e}")
        return jsonify({"error": "An error occurred while executing lukning"}), 500
