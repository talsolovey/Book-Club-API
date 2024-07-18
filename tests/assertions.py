import requests

def assert_status_code(response: requests.Response, status_code: int):
    assert response.status_code == status_code