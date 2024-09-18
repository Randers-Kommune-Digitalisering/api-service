import logging
from kp.kp_client import KPClient
from flask import Blueprint, request, jsonify
from utils.config import KP_USERNAME, KP_PASSWORD


logger = logging.getLogger(__name__)
kp_client = KPClient(KP_USERNAME, KP_PASSWORD)

api_kp_bp = Blueprint('api_kp', __name__, url_prefix='/api/kp')


@api_kp_bp.route('/token', methods=['GET'])
def fetch_kp_token():
    return jsonify(kp_client.fetch_token())


@api_kp_bp.route('/search/person', methods=['POST'])
def search_person():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "cpr is required"}), 400

        cpr = data.get('cpr')
        if not cpr:
            return jsonify({"error": "cpr is required"}), 400

        response = kp_client.search_person(cpr)
        if response is None:
            return jsonify({"error": "No response"}), 400

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"{e}"}), 500


@api_kp_bp.route('/get/person', methods=['POST'])
def get_person():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "id or cpr is required"}), 400

        cpr = data.get('cpr')
        id = data.get('id')

        if not id and not cpr:
            return jsonify({"error": "id or cpr is required"}), 400

        # Search to retrieve person id
        if cpr and not id:
            response = kp_client.search_person(cpr)
            if response is None:
                return jsonify({"error": "No response"}), 400
            else:
                id = response.get('personSearches')[0].get('id')

        if not id:
            return jsonify({"cpr": cpr, "error": True, "message": "No KP user ID was found using CPR. CPR likely does not exist in KP"}), 200

        # Get personal details
        response = kp_client.get_person(id)
        if response is None:
            return jsonify({"error": "No response"}), 400

        # Get cases
        cases = kp_client.get_cases(id)
        if cases:
            response['sager'] = cases

        # Get pension information
        pension = kp_client.get_pension(id)
        if pension:
            response['pension'] = pension

        # Get personal supplement
        personal_supplement = kp_client.get_personal_supplement(id)
        if personal_supplement:
            response['personligTillaegsprocent'] = personal_supplement.get('results')

        # Get health supplement
        health_supplement = kp_client.get_health_supplement(id)
        if health_supplement:
            response['helbredstillaegsprocent'] = health_supplement.get('results')

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"{e}"}), 500
