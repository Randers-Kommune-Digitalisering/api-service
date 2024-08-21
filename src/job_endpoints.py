import importlib
import logging
import time

from datetime import timedelta
from flask import Blueprint, request, jsonify


logger = logging.getLogger(__name__)
job_api_bp = Blueprint('job_api', __name__)


def get_job(job_name):
    try:
        module_name = f'jobs.{job_name.replace("-", "_")}'
        module = importlib.import_module(module_name)
        job = getattr(module, 'job')
        return job
    except (ImportError, AttributeError):
        return None


# endpoints are module names in jobs but with dashes instead of underscores. E.g. nexus_flow_brugerauth.py -> nexus-flow-brugerauth
@job_api_bp.route('/jobs/<job_name>', methods=['POST'])
def start_job(job_name):
    try:
        if request.headers.get('Content-Type') != 'application/json':
            return jsonify({
                'success': False,
                'message': 'Invalid content type. Expected JSON.'
            }), 400

        payload = request.get_json()
        if not payload:
            return jsonify({
                'success': False,
                'message': 'Invalid payload or missing "start" key'
            }), 400

        if payload.get('start') is not True:
            return jsonify({
                'success': False,
                'message': 'Invalid payload or missing "start" key'
            }), 400

        job = get_job(job_name)
        if job:
            logger.info(f'Starting job: {job_name}')
            start = time.time()
            if job():
                logger.info(f'Finished job: {job_name} in {str(timedelta(seconds=time.time() - start))}')
                return jsonify({
                    'success': True,
                    'message': f'{job_name} finished',
                    'time': str(timedelta(seconds=time.time() - start))
                }), 200
            else:
                logger.error(f'Failed job: {job_name} in {str(timedelta(seconds=time.time() - start))}')
                return jsonify({
                    'success': False,
                    'message': f'{job_name} failed',
                    'time': str(timedelta(seconds=time.time() - start))
                }), 500
        else:
            return jsonify({
                'success': False,
                'message': f'Invalid job name: {job_name}'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
