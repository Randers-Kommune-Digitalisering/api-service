import os
import pytest
from unittest.mock import patch
from nexus.nexus_client import NexusAPIClient

nexus_url = "https://nexus-mock.com"


@pytest.fixture
def nexus_client():
    return NexusAPIClient(client_id="test_id", client_secret="test_secret", url=nexus_url)


def test_post_request(nexus_client, requests_mock):
    path = "test"
    url = nexus_url + "/" + path
    mock_response = {"result": "success"}
    requests_mock.post(url, json=mock_response)

    with patch.object(NexusAPIClient, 'get_auth_headers', return_value={"Authorization": "Bearer test_token"}):
        response = nexus_client.post(path=path, json={"data": "value"})

    assert response == mock_response


def test_make_request_success(nexus_client, requests_mock):
    path = "test"
    url = nexus_url + "/" + path
    mock_response = {"key": "value"}
    requests_mock.get(url, json=mock_response)

    with patch.object(NexusAPIClient, 'get_auth_headers', return_value={"Authorization": "Bearer test_token"}):
        response = nexus_client.get(path)

    assert response == mock_response


def test_make_request_failure(nexus_client, requests_mock):
    path = "test"
    url = nexus_url + "/" + path
    requests_mock.get(url, status_code=404)

    with patch.object(NexusAPIClient, 'get_auth_headers', return_value={"Authorization": "Bearer test_token"}):
        response = nexus_client.get(path)

    assert response is None


def test_put_request(nexus_client, requests_mock):
    path = "test"
    url = nexus_url + "/" + path
    mock_response = {"result": "updated"}
    requests_mock.put(url, json=mock_response)

    with patch.object(NexusAPIClient, 'get_auth_headers', return_value={"Authorization": "Bearer test_token"}):
        response = nexus_client.put(path, json={"data": "value"})

    assert response == mock_response


def test_delete_request(nexus_client, requests_mock):
    path = "test"
    url = f"{nexus_client.base_url}/{path}"
    mock_response = b"success"  # Use bytes for mock response
    requests_mock.delete(url, content=mock_response)

    with patch.object(NexusAPIClient, 'get_auth_headers', return_value={"Authorization": "Bearer test_token"}):
        response = nexus_client.delete(path)

    assert response == mock_response


def test_request_access_token_success(nexus_client, requests_mock):
    url = nexus_url + '/' + os.environ["NEXUS_TOKEN_ROUTE"]
    mock_response = {
        "access_token": "test_access_token",
        "expires_in": 3600,
        "refresh_token": "test_refresh_token",
        "refresh_expires_in": 7200
    }
    requests_mock.post(url, json=mock_response)

    response = nexus_client.request_access_token()
    assert response == mock_response["access_token"]
    assert nexus_client.access_token == mock_response["access_token"]
    assert nexus_client.refresh_token == mock_response["refresh_token"]


def test_refresh_access_token_success(nexus_client, requests_mock):
    url = nexus_url + '/' + os.environ["NEXUS_TOKEN_ROUTE"]
    mock_response = {
        "access_token": "new_test_access_token",
        "expires_in": 3600,
        "refresh_token": "new_test_refresh_token",
        "refresh_expires_in": 7200
    }
    nexus_client.refresh_token = "old_test_refresh_token"
    requests_mock.post(url, json=mock_response)

    response = nexus_client.refresh_access_token()
    assert response == mock_response["access_token"]
    assert nexus_client.access_token == mock_response["access_token"]
    assert nexus_client.refresh_token == mock_response["refresh_token"]
