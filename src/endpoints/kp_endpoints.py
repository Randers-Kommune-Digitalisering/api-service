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
    data = request.get_json()
    cpr = data.get('cpr')
    if not cpr:
        return jsonify({"error": "CPR is required"}), 400
    response = kp_client.search_person(cpr)
    if response is None:
        return jsonify({"error": "No response"}), 400
    return jsonify(response)
