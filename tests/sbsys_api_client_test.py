import pytest
from unittest.mock import patch
from sbsys.sbsys_client import SbsysAPIClient

sbsys_url = "https://sbsys-mock.com"


@pytest.fixture
def sbsys_client():
    return SbsysAPIClient(client_id="test_id", client_secret="test_secret", username="test_user", password="test_password", url=sbsys_url)


def test_post_request(sbsys_client, requests_mock):
    path = "test"
    url = sbsys_url + "/" + path
    mock_response = {"result": "success"}
    requests_mock.post(url, json=mock_response)

    with patch.object(SbsysAPIClient, 'get_auth_headers', return_value={"Authorization": "Bearer test_token"}):
        response = sbsys_client.post(path=path, json={"data": "value"})

    assert response == mock_response


def test_make_request_success(sbsys_client, requests_mock):
    path = "test"
    url = sbsys_url + "/" + path
    mock_response = {"key": "value"}
    requests_mock.get(url, json=mock_response)

    with patch.object(SbsysAPIClient, 'get_auth_headers', return_value={"Authorization": "Bearer test_token"}):
        response = sbsys_client.get(path)

    assert response == mock_response


def test_make_request_failure(sbsys_client, requests_mock):
    path = "test"
    url = sbsys_url + "/" + path
    requests_mock.get(url, status_code=404)

    with patch.object(SbsysAPIClient, 'get_auth_headers', return_value={"Authorization": "Bearer test_token"}):
        response = sbsys_client.get(path)

    assert response is None


def test_put_request(sbsys_client, requests_mock):
    path = "test"
    url = sbsys_url + "/" + path
    mock_response = {"result": "updated"}
    requests_mock.put(url, json=mock_response)

    with patch.object(SbsysAPIClient, 'get_auth_headers', return_value={"Authorization": "Bearer test_token"}):
        response = sbsys_client.put(path, json={"data": "value"})

    assert response == mock_response


def test_delete_request(sbsys_client, requests_mock):
    path = "test"
    url = f"{sbsys_client.base_url}/{path}"
    mock_response = b"success"  # Use bytes for mock response
    requests_mock.delete(url, content=mock_response)

    with patch.object(SbsysAPIClient, 'get_auth_headers', return_value={"Authorization": "Bearer test_token"}):
        response = sbsys_client.delete(path)

    assert response == mock_response


def test_request_access_token_success(sbsys_client, requests_mock):
    url = "https://test/auth/realms/sbsip/protocol/openid-connect/token"
    mock_response = {
        "access_token": "test_access_token",
        "expires_in": 3600
    }
    requests_mock.post(url, json=mock_response)

    response = sbsys_client.request_access_token()
    assert response == mock_response["access_token"]
    assert sbsys_client.access_token == mock_response["access_token"]
