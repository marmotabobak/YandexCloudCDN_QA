import time

import pytest
import requests
import os
from typing import Callable, Any, List
from functools import wraps
from datetime import datetime, timedelta
from enum import Enum

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
ORIGIN_DOMAIN = 'marmota-bobak.ru'
ORIGIN_FULL_URL = 'http://marmota-bobak.ru'
RESOURCE_CNAME = 'cdn.marmota-bobak.ru'
CDN_URL = 'http://cdn.marmota-bobak.ru'
FOLDER_ID = os.environ['FOLDER_ID']  #TODO: get from cli args/config
API_SLEEP = 5
API_DELAY = 5 # should be 4 minutes (2*2) = 240 seconds

class ResourcesInitializeType(Enum):
    USE_EXISTING = 'use existing'
    MAKE_NEW = 'make new'

INITIALIZE_TYPE = ResourcesInitializeType.USE_EXISTING

def repeat_several_times_with_pause(times: int = 3, pause: int = 1):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for i in range(times):
                print(f'Attempt #{i + 1} of {times}...', end='')
                try:
                    res = func(*args, **kwargs)
                    print()
                    return res
                except AssertionError:
                    print(f'...failed. Sleeping for {pause} seconds...', end='')
                    time.sleep(pause)
                    continue
            pytest.fail('All attempts failed.')
        return wrapper
    return decorator

# TODO: repeat 10 times with 30 seconds pause (in case resources were deleted but it hasn't affected yet)
def resources_are_not_alive(cnames: List[str]) -> bool:
    sleep = 10
    attempt = 1
    ok = True
    now = datetime.now()
    finish_time = now + timedelta(seconds=API_DELAY)

    print(f'Checking resources availability for {API_DELAY} seconds...')
    while True:
        print(f'Attempt #{attempt}')
        for cname in cnames:
            try:
                print(f'GET {cname}...', end='')
                request = requests.get(url='http://' + cname)
                if request.status_code != 404:  # TODO: think about this check
                    ok = False
                    print(f'false (status code {request.status_code})')
                    break
                print('ok (status 404)')
            except requests.exceptions.ConnectionError:  # DNS CNAME records should be created before hence should be reachable TODO remake with DNS creation
                ok = False

        if not ok:
            break

        print(f'Intermediate success: all resources are 404.')
        if (now := datetime.now()) < finish_time:
            seconds_left = (finish_time-now).seconds
            print(f'{seconds_left} seconds left')
            print(f'Sleeping for {sleep} seconds...')
            time.sleep(sleep)
            attempt += 1
        else:
            break

    return ok

class TestCDN:
    @classmethod
    def setup_class(cls):
        cls.resources = []
        cls.cdn_cnames = [f'cdn-{i}.{ORIGIN_DOMAIN}' for i in range(3)]

        cls.resources_proc = ResourcesAPIProcessor(
            entity_name=EntityName.CDN_RESOURCE,
            api_url=API_URL,
            api_entity=APIEntity.CDN_RESOURCE,
            folder_id=FOLDER_ID,
            token=token
        )

        print('\n\n--- SETUP ---')
        cls.initialize_resources()
        print('--- SETUP finished ---\n\nProcessing test-cases...')

    @classmethod
    def initialize_resources(cls) -> None:
        if INITIALIZE_TYPE == ResourcesInitializeType.USE_EXISTING:
            cls.initialize_resources_from_existing()
        else:  # MAKE_NEW
            cls.delete_check_create_default_resources()

    @classmethod
    def initialize_resources_from_existing(cls):
        resource_default = cls.resources_proc.make_default_cdn_resource(
            folder_id=FOLDER_ID,
            cname='cdn-0.' + ORIGIN_DOMAIN,
            origin_group_id='7822618297624215564'
        )
        print('!!!', resource_default.cname)
        resource_default.options.static_headers.value['foo'] = 'bar'
        resource_default.id = 'cdnrobu25jvu5ltxyi32'

        cls.resources = [
            resource_default,
        ]

    @classmethod
    def delete_check_create_default_resources(cls):

        cls.origin_groups_proc = OriginGroupsAPIProcessor(
            entity_name=EntityName.ORIGIN_GROUP,
            api_url=API_URL,
            api_entity=APIEntity.ORIGIN_GROUP,
            folder_id=FOLDER_ID,
            token=token
        )

        cls.origin = Origin(source=ORIGIN_DOMAIN, enabled=True)
        cls.origin_group = OriginGroup(origins=[cls.origin, ], name='test-origin', folder_id=FOLDER_ID)
        cls.origin_groups_proc.create_item(item=cls.origin_group)

        if not resources_are_not_alive(cls.cdn_cnames):
            pytest.skip('Setup has failed')

        print(f'Success: all resources have been 404 for {API_DELAY} seconds.')

        for cname in cls.cdn_cnames:
            resource = cls.resources_proc.make_default_cdn_resource(
                folder_id=FOLDER_ID,
                cname=cname,
                origin_group_id=cls.origin_group.id
            )
            cls.resources_proc.create_item(resource)
            cls.resources.append(resource)

    @classmethod
    def teardown_class(cls):
        print('\n\n--- TEARDOWN ---')

        if INITIALIZE_TYPE == ResourcesInitializeType.MAKE_NEW:
            print('Deleting items...', end='')
            # !!! TODO: delete only those resources that have been created
            assert cls.resources_proc.delete_all_items(), 'Items have not been deleted'
            assert cls.origin_groups_proc.delete_item_by_id(cls.origin_group.id), 'Origin group has not been deleted'

        print('done')

    def test_ping_origin(self):
        request = requests.get(url=ORIGIN_FULL_URL)
        assert request.status_code == 200, 'Origin not available'

    def test_origin_group_created(self):
        if INITIALIZE_TYPE == ResourcesInitializeType.MAKE_NEW:
            assert self.origin_group.id, 'Origin group not created'

    def test_resource_created(self):
        assert self.resources and all(r.id for r in self.resources), 'CDN resources not created'

    # TODO: repeat more often - e.g. 10 times each 30 seconds or even more ofthen
    @repeat_several_times_with_pause(times=5, pause=60)
    def test_ping_cdn(self):
        for resource in self.resources:
            try:
                url = f'http://{resource.cname}'
                print(f'GET {url}...', end='')
                request = requests.get(url)
                assert request.status_code == 200, 'CDN resource not available'
            except requests.exceptions.ConnectionError:
                pytest.fail('CDN resource not available')

