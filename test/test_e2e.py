import logging
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

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger(__name__)

class ResourcesInitializeType(Enum):
    USE_EXISTING = 'use existing'
    MAKE_NEW = 'make new'

INITIALIZE_TYPE = ResourcesInitializeType.MAKE_NEW

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
                logger.debug(f'Attempt #{i + 1} of {times}...')
                try:
                    res = func(*args, **kwargs)
                    return res
                except AssertionError:
                    logger.debug(f'...failed. Sleeping for {pause} seconds...')
                    time.sleep(pause)
                    continue
            pytest.fail('All attempts failed.')
        return wrapper
    return decorator

# TODO: repeat 10 times with 30 seconds pause (in case resources were deleted but it hasn't affected yet)
@repeat_several_times_with_pause(times=10, pause=30)
def resources_are_not_alive(cnames: List[str]) -> bool:
    sleep = 10
    attempt = 1
    res = True
    now = datetime.now()
    finish_time = now + timedelta(seconds=API_DELAY)

    logger.info(f'Checking resources availability for {API_DELAY} seconds...')
    while True:
        logger.debug(f'Attempt #{attempt}')
        for cname in cnames:
            try:
                logger.debug(f'GET {cname}...')
                request = requests.get(url='http://' + cname)
                if request.status_code != 404:  # TODO: think about this check
                    logger.error('!!!1')
                    res = False
                    logger.info(f'false (status code {request.status_code})')
                    break
                logger.debug('ok (status 404)')
            except requests.exceptions.ConnectionError:  # DNS CNAME records should be created before hence should be reachable TODO remake with DNS creation
                logger.error('!!!2')
                res = False

        if not res:
            logger.error('!!!3')
            break

        logger.debug(f'Intermediate success: all resources are 404.')
        if (now := datetime.now()) < finish_time:
            seconds_left = (finish_time-now).seconds
            logger.debug(f'{seconds_left} seconds left')
            logger.debug(f'Sleeping for {sleep} seconds...')
            time.sleep(sleep)
            attempt += 1
        else:
            break

    return res

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

        logger.info('--- SETUP ---')

        if not cls.ping_origin():
            pytest.fail('Origin is not available')

        cls.initialize_resources()
        logger.info('--- SETUP finished ---')

    @classmethod
    def test_setup(cls):
        assert True

    @staticmethod
    def ping_origin() -> bool:
        request = requests.get(url=ORIGIN_FULL_URL)
        return request.status_code == 200

    @classmethod
    def initialize_resources(cls) -> None:
        if INITIALIZE_TYPE == ResourcesInitializeType.USE_EXISTING:
            cls.initialize_resources_from_existing()
        else:  # MAKE_NEW
            cls.make_new_resources()

    @classmethod
    def initialize_resources_from_existing(cls):
        resource_default = cls.resources_proc.make_default_cdn_resource(
            folder_id=FOLDER_ID,
            cname='cdn-0.' + ORIGIN_DOMAIN,
            origin_group_id='7822618297624215564'
        )
        resource_default.options.static_headers.value['foo'] = 'bar'
        resource_default.id = 'cdnrfxp2jhbyommz5fjj'

        cls.resources = [
            resource_default,
        ]

        if not cls.resources_are_created():
            pytest.fail('Resources have not been created')

    @classmethod
    def resources_are_created(cls) -> bool:
        if not (all_resources_ids := cls.resources_proc.get_items_ids_list()):
            return False
        return all(resource.id in all_resources_ids for resource in cls.resources)

    @classmethod
    def make_new_resources(cls):

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
            pytest.fail('Setup has failed')

        logger.info(f'Success: all resources have been 404 for {API_DELAY} seconds.')

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
        logger.info('\n\n--- TEARDOWN ---')

        if INITIALIZE_TYPE == ResourcesInitializeType.MAKE_NEW:
            logger.info('Deleting items...')
            assert cls.resources_proc.delete_several_items_by_ids([resource.id for resource in cls.resources]), \
                'Items have not been deleted'
            assert cls.origin_groups_proc.delete_item_by_id(cls.origin_group.id), 'Origin group has not been deleted'

        logger.info('done')

    def test_origin_group_created(self):
        if INITIALIZE_TYPE == ResourcesInitializeType.MAKE_NEW:
            assert self.origin_group.id, 'Origin group not created'

    def test_resource_created(self):
        assert self.resources and all(r.id for r in self.resources), 'CDN resources not created'

    # TODO: repeat more often - e.g. 10 times each 30 seconds or even more ofthen
    @repeat_several_times_with_pause(times=10, pause=30)
    def test_ping_cdn(self):
        for resource in self.resources:
            try:
                url = f'http://{resource.cname}'
                logger.debug(f'GET {url}...')
                request = requests.get(url)
                assert request.status_code == 200, 'CDN resource not available'
            except requests.exceptions.ConnectionError:
                pytest.fail('CDN resource not available')

