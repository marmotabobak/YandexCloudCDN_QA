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
from app.model import OriginGroup, Origin, IpAddressAcl
from app.authorization import Authorization
from app.model import EntityName, APIEntity

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger(__name__)

class ResourcesInitializeType(Enum):
    USE_EXISTING = 'use existing'
    MAKE_NEW = 'make new'

INITIALIZE_TYPE = ResourcesInitializeType.USE_EXISTING

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
# FOLDER_ID = os.environ['FOLDER_ID']  #TODO: get from cli args/config
FOLDER_ID = 'b1gjifkk80hojm6nv42n'
ORIGIN_GROUP_ID = '5867945351699784427'
API_SLEEP = 5
API_DELAY = 5 # should be 4 minutes (2*2) = 240 seconds
EXISTING_RESOURCES_IDS = {
    'cdnroq3y4e74osnivr7e': 'yccdn-qa-1.marmota-bobak.ru',
    'cdnrcblizmcdlwnddrko': 'yccdn-qa-2.marmota-bobak.ru',
    'cdnrqvhjv4tyhbfwimw3': 'yccdn-qa-3.marmota-bobak.ru',
    'cdnr5t2qvpsnaaglie2c': 'yccdn-qa-4.marmota-bobak.ru',
    'cdnrpnabfdp7u6drjaua': 'yccdn-qa-5.marmota-bobak.ru',
    'cdnr7bbwrxhguo63wkpl': 'yccdn-qa-6.marmota-bobak.ru',
    'cdnrrausbqmlmhzq6ffp': 'yccdn-qa-7.marmota-bobak.ru',
    'cdnrfvuvfped42dkmyrv': 'yccdn-qa-8.marmota-bobak.ru',
    'cdnrcqdphowdoxyxrufs': 'yccdn-qa-9.marmota-bobak.ru',
    'cdnrxcdi4xlyuwp42xfl': 'yccdn-qa-10.marmota-bobak.ru'
}

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
        #TODO: make resources from yaml and then compare them with what really in Cloud are

        for resource_id, cname in EXISTING_RESOURCES_IDS.items():
            resource = cls.resources_proc.make_default_cdn_resource(
                resource_id=resource_id,
                folder_id=FOLDER_ID,
                cname=cname,
                origin_group_id=ORIGIN_GROUP_ID,
            )
            cls.resources.append(resource)

        cls.resources[9].options.ip_address_acl = IpAddressAcl(
            enabled=True,
            excepted_values=['0.0.0.0/32', ],
            policy_type='POLICY_TYPE_ALLOW'
        )

        if not cls.resources_are_equal_to_existing():
            pytest.fail('Resources are not equal')

    @classmethod
    def resources_are_equal_to_existing(cls) -> bool:
        for resource in cls.resources:
            if not cls.resources_proc.compare_item_to_existing(resource):
                logger.debug(f'resource with cname {resource.cname} is not same as existing')
                print('!!!', resource.cname)
                return False
        return True


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

    # fake test-case to separate setup_class log output from first test-case
    @classmethod
    def test_setup(cls):
        assert True

    def test_origin_group_created(self):
        if INITIALIZE_TYPE == ResourcesInitializeType.MAKE_NEW:
            assert self.origin_group.id, 'Origin group not created'

    def test_resource_created(self):
        assert self.resources and all(r.id for r in self.resources), 'CDN resources not created'

    # TODO: repeat more often - e.g. 10 times each 30 seconds or even more often
    @repeat_several_times_with_pause(times=10, pause=10)
    def test_active_and_not_active_resources(self):
        for resource in self.resources:
            url = f'http://{resource.cname}'
            logger.debug(f'GET {url}...')
            try:
                request = requests.get(url)
                request_code = request.status_code
                logger.debug('!!!' + str(request_code) + str(resource.active))
                if resource.active:
                    assert request_code == 200, f'CDN resource {request_code}, should be 200'
                else:  # inactive
                    assert request_code == 404, f'CDN resource {request_code}, should be 404'
            except requests.exceptions.ConnectionError:
                pytest.fail('CDN resource not available')


