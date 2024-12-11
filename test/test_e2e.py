import time

import pytest
import requests
import os
from typing import Callable, Any
from functools import wraps

from app.origingroup import OriginGroupsAPIProcessor
from app.resource import ResourcesAPIProcessor
from app.model import OriginGroup, Origin
from app.authorization import Authorization
from app.model import EntityName, APIEntity

OAUTH = os.environ['OAUTH']  #TODO: get from cli args/config
IAM_TOKEN_URL = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'
authorization = Authorization(oauth=OAUTH, iam_token_url=IAM_TOKEN_URL)
assert (token := authorization.get_token()), 'Error while getting token'

#TODO: !!! dns cname needs to be created before tests

API_URL = 'https://cdn.api.cloud.yandex.net/cdn/v1'
ORIGIN_URL = 'http://marmota-bobak.ru'
RESOURCE_CNAME = 'cdn.marmota-bobak.ru'
CDN_URL = 'http://cdn.marmota-bobak.ru'
FOLDER_ID = os.environ['FOLDER_ID']  #TODO: get from cli args/config
API_SLEEP = 5

def repeat_several_times_with_pause(times: int = 3, pause: int = 1):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            exception = None
            for i in range(times):
                try:
                    res = func(*args, **kwargs)
                    return res
                except AssertionError as e:
                    print(f'Attempt #{i+1} of {times} failed. Sleeping for {pause} seconds...')
                    exception = e
                    time.sleep(pause)
                    continue
            print(f'All attempts failed.')
            raise exception
        return wrapper
    return decorator

origin_groups_processor = OriginGroupsAPIProcessor(
    entity_name=EntityName.ORIGIN_GROUP,
    api_url=API_URL,
    api_entity=APIEntity.ORIGIN_GROUP,
    folder_id=FOLDER_ID,
    token=token
)

resources_processor = ResourcesAPIProcessor(
    entity_name=EntityName.CDN_RESOURCE,
    api_url=API_URL,
    api_entity=APIEntity.CDN_RESOURCE,
    folder_id=FOLDER_ID,
    token=token
)

@pytest.fixture
def origin_group_id() -> str:
    origin = Origin(source='marmota-bobak.ru', enabled=True)
    origin_group = OriginGroup(origins=[origin, ], name='test origin', folder_id=FOLDER_ID)
    return origin_groups_processor.create_item(item=origin_group)

@pytest.fixture
def resource(origin_group_id) -> str:
    resource = resources_processor.make_default_cdn_resource(
        folder_id=FOLDER_ID,
        cname=RESOURCE_CNAME,
        origin_group_id=origin_group_id
    )
    return resources_processor.create_item(item=resource)

@pytest.fixture
def delete_all_origin_groups():
    time.sleep(API_SLEEP)
    origin_groups_processor.delete_all_items()

@pytest.fixture
def delete_all_resources():
    time.sleep(API_SLEEP)
    resources_processor.delete_all_items()

@pytest.fixture
def delete_all_items(delete_all_resources, delete_all_origin_groups):
    ...

def test_ping_origin():
    request = requests.get(url=ORIGIN_URL)
    assert request.status_code == 200, 'Origin not available'

def test_origin_group_created(delete_all_items, origin_group_id):
    assert origin_group_id, 'Origin Group not created'

@repeat_several_times_with_pause(times=3, pause=1)
def test_resource_created(delete_all_items, resource):
    assert resource is not None, 'CDN resource not created'

@repeat_several_times_with_pause(times=5, pause=60)
def test_ping_cdn(delete_all_items, resource):
    request = requests.get(url=CDN_URL + '/ping/pong.txt')
    assert request.status_code == 200, 'CDN resource not available'



