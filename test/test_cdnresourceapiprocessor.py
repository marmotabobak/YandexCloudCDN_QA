import pytest
import requests
import logging

logging.basicConfig(level=logging.INFO)

ORIGIN_URL = 'http://marmota-bobak.ru'

@pytest.fixture
def make_default_cdn_resource():
    cdn_resource = make_default_cdn_resource()


def test_ping_origin():
    request = requests.get(url=ORIGIN_URL)
    assert request.status_code == 200, 'Origin not available'

