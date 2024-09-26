import pytest
from unittest.mock import patch
from kp.kp_client import KPAPIClient

kp_url = "https://kp-mock.com"


@pytest.fixture
def kp_client():
    return KPAPIClient(username="test_user", password="test_password")


def test_get_request(kp_client):
    path = "test"
    url = kp_url + "/" + path
    mock_response = {"headers": {"Content-Type": "sometype"}, "result": "success"}

    with patch.object(KPAPIClient, 'get_auth_headers', return_value={"Cookie": "JSESSIONID=test_session_cookie"}):
        with patch.object(kp_client, '_make_request', return_value=mock_response):
            response = kp_client.get(path=url)

    assert response == mock_response


def test_make_request_success(kp_client):
    mock_response = {
        'Headers': {'Content-Type': 'application/json'},
        'data': {'key': 'value'}
    }

    with patch.object(kp_client, '_make_request', return_value=mock_response):
        response = kp_client._make_request('GET', 'test')
        assert response == mock_response
        headers = response.get('Headers', {})
        assert headers == mock_response.get('Headers', {})
