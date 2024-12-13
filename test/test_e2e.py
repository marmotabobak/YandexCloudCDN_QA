import time

import pytest
import requests
import os
from typing import Callable, Any, List
from functools import wraps
from datetime import datetime, timedelta

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
            except requests.exceptions.ConnectionError:  # DNS CNAME records should be created hence should be reachable TODO remake with DNS creation
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

        print('\n\n--- SETUP ---')

        cls.cdn_cnames = [f'cdn-{i}.{ORIGIN_DOMAIN}' for i in range(3)]

        cls.origin_groups_proc = OriginGroupsAPIProcessor(
            entity_name=EntityName.ORIGIN_GROUP,
            api_url=API_URL,
            api_entity=APIEntity.ORIGIN_GROUP,
            folder_id=FOLDER_ID,
            token=token
        )

        cls.resources_proc = ResourcesAPIProcessor(
            entity_name=EntityName.CDN_RESOURCE,
            api_url=API_URL,
            api_entity=APIEntity.CDN_RESOURCE,
            folder_id=FOLDER_ID,
            token=token
        )

        cls.origin = Origin(source=ORIGIN_DOMAIN, enabled=True)
        cls.origin_group = OriginGroup(origins=[cls.origin, ], name='test-origin', folder_id=FOLDER_ID)
        cls.resources = []

        cls.resources_proc.delete_all_items()
        # cls.origin_groups_proc.delete_all_items()  # it's better to be done but due to bug there is a problem at our cdn

        # here we create origin group and cdn resources TODO make optionally - not to create but use already created and check that they are default
        if not resources_are_not_alive(cls.cdn_cnames):
            pytest.skip('Setup has failed')

        print(f'Success: all resources have been 404 for {API_DELAY} seconds.')
        print('Creating origin group and resources...', end='')
        origin_group_id = cls.origin_groups_proc.create_item(item=cls.origin_group)

        for cname in cls.cdn_cnames:
            resource = cls.resources_proc.make_default_cdn_resource(
                folder_id=FOLDER_ID,
                cname=cname,
                origin_group_id=origin_group_id
            )
            cls.resources_proc.create_item(resource)
            cls.resources.append(resource)
        print('done')

        print('--- SETUP finished ---\n\nProcessing test-cases...')

    @classmethod
    def teardown_class(cls):
        print('\n\n--- TEARDOWND ---')
        print('Deleting items...', end='')
        assert cls.resources_proc.delete_all_items(), 'Items have not been deleted'
        assert cls.origin_groups_proc.delete_item_by_id(cls.origin_group.id), 'Origin group has not been deleted'  # better to delete all but there is a bug =)
        print('done')

    def test_ping_origin(self):
        request = requests.get(url=ORIGIN_FULL_URL)
        assert request.status_code == 200, 'Origin not available'

    def test_origin_group_created(self):
        assert self.origin_group.id, 'Origin group not created'

    def test_resource_created(self):
        assert self.resources and all(r.id for r in self.resources), 'CDN resources not created'

    @repeat_several_times_with_pause(times=5, pause=60)
    def test_ping_cdn(self):
        for cdn_cname in self.cdn_cnames:
            try:
                url = f'http://{cdn_cname}'
                print(f'GET {url}...', end='')
                request = requests.get(url)
                assert request.status_code == 200, 'CDN resource not available'
            except requests.exceptions.ConnectionError:
                pytest.fail('CDN resource not available')

