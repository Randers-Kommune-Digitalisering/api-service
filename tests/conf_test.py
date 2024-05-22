import pytest
from main import create_app


@pytest.fixture()
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


def test_healthz(client):
    response = client.get('/healthz')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'success'


def test_metrics(client):
    # POD_NAME env var set in pytest.ini
    response = client.get('/metrics')
    assert response.status_code == 200
    assert 'up gauge\nup{name="test-pod"} 1.0' in response.text
