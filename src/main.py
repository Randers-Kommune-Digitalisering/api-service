from flask import Flask, jsonify
from healthcheck import HealthCheck
from prometheus_client import generate_latest
# from apscheduler.schedulers.background import BackgroundScheduler

from utils.logging import set_logging_configuration, APP_RUNNING
from utils.config import POD_NAME
from nexus_client import NEXUSClient
from nexus_flow_brugerauth import build_flow
# from background_job import test_job
# from database import test_database

# Create an instance of NEXUSClient
nexus_client = NEXUSClient()


def create_app():
    app = Flask(__name__)
    health = HealthCheck()
    app.add_url_rule("/healthz", "healthcheck", view_func=lambda: health.run())
    app.add_url_rule('/metrics', "metrics", view_func=generate_latest)
    APP_RUNNING.labels(POD_NAME).set(1)
    return app

# def create_scheduler():
#     scheduler = BackgroundScheduler()
#     scheduler.add_job(test_job, 'interval', seconds=5) # Every 5 seconds
#     scheduler.add_job(test_job, 'cron', day_of_week='mon', hour=7) # Every Monday at 7 AM
#     return scheduler


set_logging_configuration()
# scheduler = create_scheduler()
app = create_app()

# @app.route('/test-database', methods=['GET'])
# def test_database():
#     ok = test_database()
#     if ok:
#         app.logger.info('Database ok')
#         return ok
#     return 'failed', 500


@app.route('/test-home-resource', methods=['GET'])
def test_home_resource_route():
    print("Test resource")
    try:
        response = nexus_client.home_resource()
        return jsonify(response), 200
    except Exception as e:
        app.logger.error(f"Error fetching home resource: {e}")
        return str(e), 500


def test_home_resource():
    try:
        response = nexus_client.home_resource()
        print(response)
        return jsonify(response)
    except Exception as e:
        return str(e)


if __name__ == "__main__":  # pragma: no cover
    # scheduler.start()
    # app.run(debug=DEBUG, host='0.0.0.0', port=PORT)
    # test_home_resource()
    build_flow("dqb1029")
