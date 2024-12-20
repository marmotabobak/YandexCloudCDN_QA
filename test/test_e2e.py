import logging
import time

import pytest
import requests
import os
from typing import Callable, Any, List, Optional, Dict, Iterable, Tuple
from functools import wraps
from datetime import datetime, timedelta
from enum import Enum
from collections import namedtuple
from pydantic import BaseModel, ConfigDict, Field
from utils import ping, http_get_request_through_ip_address, increment, make_random_8_symbols
from copy import  deepcopy

from app.origingroup import OriginGroupsAPIProcessor
from app.resource import ResourcesAPIProcessor
from app.model import OriginGroup, Origin, IpAddressAcl, CDNResource
from app.authorization import Authorization
from app.model import EntityName, APIEntity, EdgeCacheSettings, QueryParamsOptions, EnabledBoolValueBool, EnabledBoolValueDictStrStr

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger(__name__)

# TODO: implement negative tests

class RevalidatedTooEarly(Exception):
    ...

class EdgeResponseHeaders(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cache_host: str = Field(..., alias='Cache-Host')
    cache_status: Optional[str] = Field(None, alias='Cache-Status')
    fizz: Optional[str] = Field(None)

HostResponse = namedtuple('HostResponse', 'time, status')

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
API_DELAY = 5
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
SHORT_TTL = 10
LONG_TTL = 3600
EDGE_CACHE_PERIODS_TO_TEST = 2
EDGE_CACHE_HOSTS = {
    'm9-srv01.yccdn.cloud.yandex.net': '188.72.104.2',
    'm9-srv02.yccdn.cloud.yandex.net': '188.72.104.3',
    'm9-srv03.yccdn.cloud.yandex.net': '188.72.104.4',
    'm9-srv04.yccdn.cloud.yandex.net': '188.72.104.5',
    'm9-srv05.yccdn.cloud.yandex.net': '188.72.104.6',
    'mar-srv01.yccdn.cloud.yandex.net': '188.72.105.2',
    'mar-srv02.yccdn.cloud.yandex.net': '188.72.105.3',
    'mar-srv03.yccdn.cloud.yandex.net': '188.72.105.4',
    'mar-srv04.yccdn.cloud.yandex.net': '188.72.105.5',
    'mar-srv05.yccdn.cloud.yandex.net': '188.72.105.6',
}
CURL_FINISH_ONCE_SUCCESS = True


def repeat_until_success_or_timeout(attempts: int = 20, attempt_delay: int = 15):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for i in range(attempts):
                logger.debug(f'Attempt #{i + 1} of {attempts}...')
                try:
                    res = func(*args, **kwargs)
                    return res
                except (AssertionError, RevalidatedTooEarly):
                    logger.debug(f'...failed. Sleeping for {attempt_delay} seconds...')
                    time.sleep(attempt_delay)
            pytest.fail('All attempts failed.')
        return wrapper
    return decorator

@repeat_until_success_or_timeout()
def resources_are_not_alive_for_period_of_time(
        cnames: List[str],
        duration_to_success: int = API_DELAY,
        attempt_sleep: int = API_SLEEP
) -> bool:

    attempt = 1
    res = True
    now = datetime.now()
    finish_time = now + timedelta(seconds=duration_to_success)

    logger.info(f'Checking resources availability for {duration_to_success} seconds...')
    while True:
        logger.debug(f'Attempt #{attempt}')
        for cname in cnames:
            try:
                logger.debug(f'GET {cname}...')
                request = requests.get(url='http://' + cname)
                if request.status_code != 404:  # TODO: think about this check
                    res = False
                    logger.info(f'false (status code {request.status_code})')
                    break
                logger.debug('ok (status 404)')
            except requests.exceptions.ConnectionError:  # DNS CNAME records should be created before hence should be reachable TODO remake with DNS creation
                res = False

        if not res:
            break

        logger.debug(f'Intermediate success: all resources are 404.')
        if (now := datetime.now()) < finish_time:
            seconds_left = (finish_time-now).seconds
            logger.debug(f'{seconds_left} seconds left')
            logger.debug(f'Sleeping for {attempt_sleep} seconds...')
            time.sleep(attempt_sleep)
            attempt += 1
        else:
            break

    return res


@repeat_until_success_or_timeout()
def resources_are_equal_for_period_of_time(
        resources_proc: ResourcesAPIProcessor,
        resources: List[CDNResource],
        duration_to_success: int = API_DELAY,
        attempt_sleep: int = API_SLEEP
) -> bool:
    attempt = 1
    res = True
    now = datetime.now()
    finish_time = now + timedelta(seconds=duration_to_success)

    logger.info(f'Checking resources equality for {duration_to_success} seconds...')
    while True:
        logger.debug(f'Attempt #{attempt}')
        for resource in resources:
            logger.debug(f'Comparing resource [{resource.id}]...')
            if not resources_proc.compare_item_to_existing(resource):
                res = False
                logger.info(f'false')
                break
            logger.debug('ok')

        if not res:
            break

        logger.debug(f'Intermediate success: all resources are equal to existing ones')
        if (now := datetime.now()) < finish_time:
            seconds_left = (finish_time - now).seconds
            logger.debug(f'{seconds_left} seconds left')
            logger.debug(f'Sleeping for {attempt_sleep} seconds...')
            time.sleep(attempt_sleep)
            attempt += 1
        else:
            break

    return res

class TestCDN:
    @classmethod
    def setup_class(cls):

        cls.resources = []
        cls.cdn_cnames = []  # for making new resources only

        cls.method_to_curl_resources = cls.randomly_curl_resources

        cls.custom_header = make_random_8_symbols()

        cls.resources_proc = ResourcesAPIProcessor(
            entity_name=EntityName.CDN_RESOURCE,
            api_url=API_URL,
            api_entity=APIEntity.CDN_RESOURCE,
            folder_id=FOLDER_ID,
            token=token
        )

        logger.info('--- SETUP ---')

        # if not cls.origin_is_available_with_200():
        #     pytest.fail('Origin is not available')
        #
        # if edges := cls.get_not_pinged_edges():
        #     logging.warning(f'Edges are not pinged successfully: {edges}')

        cls.initialize_resources()
        logger.info('--- SETUP finished ---')

    @staticmethod
    def origin_is_available_with_200() -> bool:
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

        # TODO: DEBUG COMMENT - UNCOMMENT FOR PRODUCTION
        # if not resources_are_equal_for_period_of_time(cls.resources_proc, cls.resources):
        #     pytest.fail('Existing resources are not equal to default')
        logger.info(f'Success: all resources have been equal to default for {API_DELAY} seconds')

        cls.resources[0].active = False  # 'cdnroq3y4e74osnivr7e': 'yccdn-qa-1.marmota-bobak.ru'

        cls.resources[1].options.edge_cache_settings = EdgeCacheSettings(enabled=True, default_value=str(SHORT_TTL))  # 'cdnrcblizmcdlwnddrko': 'yccdn-qa-2.marmota-bobak.ru'

        cls.resources[2].options.edge_cache_settings = EdgeCacheSettings(enabled=False, default_value=str(SHORT_TTL))  # 'cdnrqvhjv4tyhbfwimw3': 'yccdn-qa-3.marmota-bobak.ru'

        cls.resources[3].options.query_params_options = QueryParamsOptions(ignore_query_string=EnabledBoolValueBool(enabled=True, value=True))  # 'cdnr5t2qvpsnaaglie2c': 'yccdn-qa-4.marmota-bobak.ru'

        cls.resources[4].options.query_params_options = QueryParamsOptions(ignore_query_string=EnabledBoolValueBool(enabled=True, value=False))  # 'cdnrpnabfdp7u6drjaua': 'yccdn-qa-5.marmota-bobak.ru'

        cls.resources[5].options.edge_cache_settings = EdgeCacheSettings(enabled=True, default_value=str(LONG_TTL))

        cls.resources[6].options.static_headers = EnabledBoolValueDictStrStr(enabled=True, value={'param-to-test': cls.custom_header})

        cls.resources[9].options.ip_address_acl = IpAddressAcl(    # 'cdnrxcdi4xlyuwp42xfl': 'yccdn-qa-10.marmota-bobak.ru'
            enabled=True,
            excepted_values=['0.0.0.0/32', ],
            policy_type='POLICY_TYPE_ALLOW'
        )

        # for resource in cls.resources:
        #     cls.resources_proc.update(resource)

        # if not cls.resources_are_equal_to_existing():
        #     pytest.fail('Updated resources are not equal to existing ones')

    @classmethod
    def resources_are_equal_to_existing(cls) -> bool:
        for resource in cls.resources:
            if not cls.resources_proc.compare_item_to_existing(resource):
                logger.debug(f'Resource [{resource.id}] with cname {resource.cname} is not same as existing')
                logger.debug(f'Processor resource: {resource}')
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

        if not resources_are_not_alive_for_period_of_time(cls.cdn_cnames):
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
        elif INITIALIZE_TYPE == ResourcesInitializeType.USE_EXISTING:
            logger.info('Resetting resources to default...')
            # TODO: RESET TO DEFAULT
            # assert cls.resources_are_equal_to_existing(), 'Resources were not reset'

        logger.info('done')

    # fake test-case to separate setup_class log output from first test-case
    @classmethod
    def test_setup(cls):
        assert True

    # TODO: make random check but with return once success
    # TODO: make async otherwise too few requests and needs too many periods_count (such as 5) to assert successfully
    # NB! better use targeted requests to specific cache hosts
    @classmethod
    def randomly_curl_resources(
            cls,
            resources: List[CDNResource],
            protocol: str = 'http',
            period_of_time: int = SHORT_TTL,
            periods_count: int = EDGE_CACHE_PERIODS_TO_TEST,
            add_query_arg: bool = False,
            finish_once_success: bool = CURL_FINISH_ONCE_SUCCESS
    ) -> bool:

        start_time = time.time()
        resources_statuses = {}
        query_generator = increment()

        time_to_test = periods_count * period_of_time
        logger.info(f'GET resources [{[r.cname for r in resources]}] for {time_to_test} seconds...')

        while time.time() < start_time + time_to_test:
            for resource in resources:
                url = f'{protocol}://{resource.cname}'
                if add_query_arg:
                    url += '?foo=' + str(next(query_generator))
                response = requests.get(url)
                response_headers = EdgeResponseHeaders(**response.headers)
                if not response_headers.cache_status:
                    logger.debug(response_headers)
                    pytest.fail('Cache-Status header is absent')
                host_response = HostResponse(time=time.time(), status=response_headers.cache_status)
                resources_statuses.setdefault(
                    resource.id,
                    {response_headers.cache_host: []}
                ).setdefault(response_headers.cache_host, []).append(host_response)

                if finish_once_success:
                    if cls.resource_is_correctly_processed_by_edge(
                            statuses=resources_statuses[resource.id][response_headers.cache_host],
                            period_of_time=period_of_time
                    ):
                        return True

        logger.debug(f'resources statuses: {resources_statuses}')

        # TODO: don't copy but create above where original dict is created
        resources_statuses_copy = deepcopy(resources_statuses)

        for resource_id, resource_statuses in resources_statuses.items():
            for host_name, host_responses in resource_statuses.items():
                if cls.resource_is_correctly_processed_by_edge(statuses=host_responses, period_of_time=period_of_time):
                    resources_statuses_copy[resource_id].pop(host_name)
            if not resources_statuses_copy[resource_id]:
                resources_statuses_copy.pop(resource_id)

        logger.debug(f'resources statuses after processing: {resources_statuses_copy}')

        return resources_statuses_copy == {}

    @classmethod
    # TODO: refactor - too long method
    # TODO: make async otherwise too few requests and needs too many periods_count (such as 5) to assert successfully
    # NB! better use targeted requests to specific cache hosts
    def targeted_http_curl_resources(
            cls,
            resources: List[CDNResource],
            period_of_time: int = SHORT_TTL,
            periods_count: int = EDGE_CACHE_PERIODS_TO_TEST,
            add_query_arg: bool = False,
            finish_once_success: bool = CURL_FINISH_ONCE_SUCCESS
    ) -> bool:

        resources_statuses = {}
        resources_statuses_template = {}
        query_generator = increment()

        for resource in resources:
            resources_statuses[resource.id] = {}
            resources_statuses_template[resource.id] = {}
            for edge_host_host, edge_ip_address in EDGE_CACHE_HOSTS.items():

                url = resource.cname
                if add_query_arg:
                    url += '?foo=' + str(next(query_generator))
                response = http_get_request_through_ip_address(url, edge_ip_address)
                response_headers = EdgeResponseHeaders(**response.headers)
                logger.debug(response_headers)

                if not response_headers.cache_status:
                    pytest.fail('Cache-Status header is absent')

                host_response = HostResponse(time=time.time(), status=response_headers.cache_status)
                resources_statuses[resource.id][edge_host_host] = [host_response, ]
                resources_statuses_template[resource.id][edge_host_host] = None

        time_to_test = periods_count * period_of_time
        logger.info(f'GET resources [{[r.cname for r in resources]}] for up to {time_to_test} seconds...')

        start_time = time.time()
        while time.time() < start_time + time_to_test:
            for resource in resources:
                if resource.id in resources_statuses_template:
                    for edge_host, edge_ip_address in EDGE_CACHE_HOSTS.items():
                        if edge_host in resources_statuses_template[resource.id]:

                            url = resource.cname
                            if add_query_arg:
                                url += '?foo=' + str(next(query_generator))
                            response = http_get_request_through_ip_address(url, edge_ip_address)
                            response_headers = EdgeResponseHeaders(**response.headers)

                            if not response_headers.cache_status:
                                pytest.fail('Cache-Status header is absent')

                            host_response = HostResponse(time=time.time(), status=response_headers.cache_status)
                            resources_statuses[resource.id][response_headers.cache_host].append(host_response)

                            if cls.resource_is_correctly_processed_by_edge(
                                statuses=resources_statuses[resource.id][response_headers.cache_host],
                                period_of_time=period_of_time
                            ):

                                if finish_once_success:
                                    return True

                                del resources_statuses_template[resource.id][response_headers.cache_host]

                    if resources_statuses_template[resource.id] == {}:
                        del resources_statuses_template[resource.id]

            if resources_statuses_template == {}:
                return True

        return False

    @staticmethod
    def resource_is_correctly_processed_by_edge(
            statuses: List[HostResponse],
            period_of_time: int = SHORT_TTL,
            error_rate: float = 0.9
    ) -> bool:

        last_revalidated_or_miss = None

        for host_response in statuses:
            if host_response.status in ('REVALIDATED', 'MISS'):
                if last_revalidated_or_miss:
                    # TODO: Check no the time of response received but response prepared by host? (Header 'Date:...')
                    # return host_response.time - last_revalidated_or_miss > error_rate * period_of_time
                    if host_response.time - last_revalidated_or_miss > error_rate * period_of_time:
                        return True
                    else:
                        raise RevalidatedTooEarly()
                last_revalidated_or_miss = host_response.time

        return False

    @staticmethod
    def get_not_pinged_edges() -> List[str]:
        res = []
        for edge_host in EDGE_CACHE_HOSTS:
            if not ping(edge_host, attempts=2):
                res.append(edge_host)
        return res

    @classmethod
    def prepare_resources_list_to_test(cls, conditions_not_to_test: Callable) -> List[CDNResource]:
        resources_to_test = [r for r in cls.resources if not conditions_not_to_test(r)]
        if not resources_to_test:
            pytest.fail(f'No resources found to test disabled edge_cache_settings')
        return resources_to_test

    @staticmethod
    def resource_is_not_active_or_acl_or_no_cache_settings(resource: CDNResource) -> bool:
        return any(
            (
                not resource.active,
                not resource.options,
                resource.options.ip_address_acl and resource.options.ip_address_acl.enabled,
                not resource.options.edge_cache_settings,
            )
        )

    @classmethod
    def resource_is_not_active_or_acl_or_no_ttl(cls, resource: CDNResource) -> bool:
        return any(
            (
                cls.resource_is_not_active_or_acl_or_no_cache_settings(resource),
                not resource.options.edge_cache_settings.enabled,
            )
        )

    @classmethod
    def resource_is_not_active_or_acl_or_not_short_ttl(cls, resource: CDNResource) -> bool:
        return any(
            (
                cls.resource_is_not_active_or_acl_or_no_ttl(resource),
                resource.options.edge_cache_settings.default_value != str(SHORT_TTL)
            )
        )





    @pytest.mark.skip('FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    def test_origin_group_created(self):
        if INITIALIZE_TYPE == ResourcesInitializeType.MAKE_NEW:
            assert self.origin_group.id, 'Origin group not created'

    @pytest.mark.skip('FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    def test_resources_are_created(self):
        assert self.resources and all(r.id for r in self.resources), 'CDN resources not created'

    @pytest.mark.skip('FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @repeat_until_success_or_timeout()
    def test_active_and_not_active_resources(self):
        for resource in self.resources:
            url = f'http://{resource.cname}'
            logger.debug(f'GET {url}...')
            request = requests.get(url)
            request_code = request.status_code
            if resource.active:
                assert request_code in (200, 403), f'CDN resource {request_code}, should be 200 or 403'
            else:  # inactive
                assert request_code == 404, f'CDN resource {request_code}, should be 404'

    @pytest.mark.skip('FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @repeat_until_success_or_timeout()
    def test_ip_address_acl(self):
        for resource in self.resources:
            url = f'http://{resource.cname}'
            logger.info(f'GET {url}...')
            request = requests.get(url)
            request_code = request.status_code
            if resource.options.ip_address_acl and resource.options.ip_address_acl.enabled:
                if resource.options.ip_address_acl.policy_type == 'POLICY_TYPE_ALLOW':  # consider ip-address is NOT our else refactor
                    assert request_code == 403, f'CDN resource {request_code}, should be 403'
                else:
                    ...  #TODO: to add
            else:  # allowed
                assert request_code != 403, f'CDN resource 403, should be not'

    # @pytest.mark.skip('FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @repeat_until_success_or_timeout()
    def test_edge_cache_settings_enabled_revalidate_out_of_ttl(self):

        resources_to_test = self.prepare_resources_list_to_test(self.resource_is_not_active_or_acl_or_not_short_ttl)

        assert self.method_to_curl_resources(
            resources=resources_to_test
        ), 'Not all statuses were processed correctly'

    # @pytest.mark.skip('FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @repeat_until_success_or_timeout()
    def test_edge_cache_settings_enabled_revalidate_too_early_error(self):

        resources_to_test = self.prepare_resources_list_to_test(self.resource_is_not_active_or_acl_or_not_short_ttl)

        with pytest.raises(RevalidatedTooEarly):
            self.method_to_curl_resources(resources=resources_to_test, period_of_time=2*SHORT_TTL)

    # @pytest.mark.skip('FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @repeat_until_success_or_timeout()
    def test_edge_cache_settings_enabled_do_not_revalidate_within_ttl(self):
        def filter_not_to_test(r: CDNResource) -> bool:
            return any(
                (
                    self.resource_is_not_active_or_acl_or_no_ttl(r),
                    r.options.edge_cache_settings.default_value != str(LONG_TTL)

                )
            )

        resources_to_test = self.prepare_resources_list_to_test(filter_not_to_test)

        assert not self.method_to_curl_resources(
            resources=resources_to_test
        ), 'Not all statuses were processed correctly'

    # @pytest.mark.skip('FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @repeat_until_success_or_timeout()
    def test_edge_cache_settings_disabled(self):
        def filter_not_to_test(r: CDNResource) -> bool:
            return any(
                (
                    self.resource_is_not_active_or_acl_or_no_cache_settings(r),
                    r.options.edge_cache_settings.enabled,
                )
            )

        resources_to_test = self.prepare_resources_list_to_test(filter_not_to_test)

        logger.info(f'GET resources [{[r.cname for r in resources_to_test]}]...')
        for resource in resources_to_test:
            url = f'http://{resource.cname}'
            request = requests.get(url)
            request_headers = EdgeResponseHeaders(**request.headers)
            assert not request_headers.cache_status

    # @pytest.mark.skip('FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @repeat_until_success_or_timeout()
    def test_ignore_query_string(self):
        def filter_not_to_test(r: CDNResource) -> bool:
            return any(
                (
                    self.resource_is_not_active_or_acl_or_not_short_ttl(r),
                    not r.options.query_params_options,
                    not r.options.query_params_options.ignore_query_string,
                    not r.options.query_params_options.ignore_query_string.enabled,
                    not r.options.query_params_options.ignore_query_string.value,
                )
            )

        resources_to_test = self.prepare_resources_list_to_test(filter_not_to_test)

        assert self.method_to_curl_resources(resources_to_test, add_query_arg=True)

    # @pytest.mark.skip('FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @repeat_until_success_or_timeout()
    def test_do_not_ignore_query_string(self):
        def filter_not_to_test(r: CDNResource) -> bool:
            return any(
                (
                    self.resource_is_not_active_or_acl_or_no_ttl(r),
                    not r.options.query_params_options,
                    not r.options.query_params_options.ignore_query_string,
                    r.options.query_params_options.ignore_query_string.value,
                )
            )

        resources_to_test = self.prepare_resources_list_to_test(filter_not_to_test)

        with pytest.raises(RevalidatedTooEarly):
            self.method_to_curl_resources(resources_to_test, add_query_arg=True)






