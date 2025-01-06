import os
import time
from copy import deepcopy
from datetime import datetime, timedelta
from typing import List, Union, Callable

import allure
import pytest
import requests
import yaml

from app.authorization import Authorization
from app.model import EntityName, APIEntity, EdgeCacheSettings, QueryParamsOptions, EnabledBoolValueBool, \
    EnabledBoolValueDictStrStr
from app.model import OriginGroup, Origin, IpAddressAcl, CDNResource
from app.origingroup import OriginGroupsAPIProcessor
from app.resource import ResourcesAPIProcessor
from app.utils import ping, http_get_request_through_ip_address, increment, make_random_8_symbols
from test.logger import logger
from test.model import Config, RequestsType, ResourcesInitializeMethod, HostResponse, CheckType, EdgeResponseHeaders
from test.utils import RevalidatedBeforeTTL, ResourceIsNotEqualToExisting, URLIsNot404, resource_is_active, \
    resource_is_not_active, resource_is_active_and_no_acl_and_cache_enabled, resource_is_active_and_no_acl_and_ttl, \
    resource_is_active_and_no_acl_and_with_ttl, http_get_url, repeat_until_success_or_timeout

# TODO: !True ONLY FOR DEBUG! Use False for Production
SKIP_CHECK_RESOURCES_ARE_DEFAULT = True
SKIP_CHECK_EQUAL_TO_EXISTING = False
SKIP_PING_EDGED = True
SKIP_UPDATE_RESOURCES = True
SKIP_TESTS = False

OAUTH = os.environ['OAUTH']
CONFIG_PATH = 'test/config.yaml'
# CONFIG_PATH = 'test/edge.yaml'

class TestCDN:

    @classmethod
    def setup_class(cls):
        cls.init_config()
        cls.init_iam_token()
        cls.init_attributes()

        logger.info('--- SETUP ---')

        logger.info('Checking origins 200...')
        if not cls.origin_is_available_with_200():
            pytest.fail('Origin is not available')
        logger.info('OK')

        if not SKIP_PING_EDGED and cls.edge_cache_hosts:
            logger.info('Pinging edges...')
            if edges := cls.get_not_pinged_edges():
                pytest.fail(f'Edges are not pinged successfully: {edges}')
            logger.info('OK')

        logger.info(f'Initializing and checking resources for {cls.initialize_duration_check} seconds...')
        cls.initialize_resources()
        logger.info('OK')

        logger.info('--- SETUP finished ---')

    @classmethod
    def init_config(cls):
        with open(CONFIG_PATH) as fp:
            config_dict = yaml.safe_load(fp)
        cls.config = Config.model_validate(config_dict)

        cls.api_url = cls.config.yandex_cloud_api.api_url
        cls.curl_method = cls.config.api_test_parameters.edge_curl_settings.requests_type
        cls.use_random_headers = cls.config.api_test_parameters.client_headers_settings.use_random_headers
        cls.custom_header_value = cls.config.api_test_parameters.client_headers_settings.custom_header_value
        cls.initialize_duration_check = (cls.config.api_test_parameters.setup_initialize_resources_check.
                                         total_duration_seconds)
        cls.initialize_sleep_between_attempts = (cls.config.api_test_parameters.setup_initialize_resources_check.
                                                 sleep_duration_between_attempts)
        cls.origin_domain = cls.config.resources.origin.domain
        cls.protocol = cls.config.api_test_parameters.default_protocol.value
        cls.initialize_type = cls.config.api_test_parameters.resources_initialize_method
        cls.folder_id = cls.config.resources.folder_id
        cls.short_ttl = cls.config.api_test_parameters.ttl_settings.short_ttl
        cls.long_ttl = cls.config.api_test_parameters.ttl_settings.long_ttl
        cls.periods_to_test = cls.config.api_test_parameters.edge_curl_settings.periods_to_test
        cls.finish_once_success = cls.config.api_test_parameters.edge_curl_settings.finish_once_success
        cls.iam_token_url = cls.config.yandex_cloud_api.iam_token_url
        cls.cdn_resources = cls.config.resources.cdn_resources
        cls.origin = cls.config.resources.origin
        cls.edge_cache_hosts = cls.config.resources.edge_cache_hosts
        cls.ttl_error_rate = cls.config.api_test_parameters.ttl_settings.error_rate

    @classmethod
    def init_attributes(cls):
        cls.custom_header = make_random_8_symbols() if cls.use_random_headers else cls.custom_header_value

        if cls.curl_method == RequestsType.targeted:
            cls.method_to_curl_resources = cls.targeted_http_curl_resources
        else:
            cls.method_to_curl_resources = cls.randomly_curl_resources

        cls.resources_proc = ResourcesAPIProcessor(
            entity_name=EntityName.CDN_RESOURCE,
            api_url=cls.api_url,
            api_entity=APIEntity.CDN_RESOURCE,
            folder_id=cls.folder_id,
            token=cls.token
        )

    @classmethod
    def init_iam_token(cls):
        authorization = Authorization(oauth=OAUTH, iam_token_url=cls.iam_token_url)
        assert (token := authorization.get_token()), 'Error while getting token'
        cls.token = token

    @classmethod
    @repeat_until_success_or_timeout()
    def check_entities_for_period_of_time(
        cls,
        entities_to_check: Union[List[str], List[CDNResource]],
        check_type: CheckType,
        duration_to_success: int = None,
        attempt_sleep: int = None
    ) -> bool:

        if check_type == CheckType.CNAME_404:
            entity_text = 'cnames are 404'
            method_to_check = cls.cname_is_404
        elif check_type == CheckType.RESOURCE_EQUAL:
            entity_text = 'resources are equal to existing'
            method_to_check = cls.resource_is_equal_to_existing
        else:
            logger.error('Unknown check_type')
            return False

        if duration_to_success is None:
            duration_to_success = cls.initialize_duration_check
        if attempt_sleep is None:
            attempt_sleep = cls.initialize_sleep_between_attempts

        attempt = 1
        now = datetime.now()
        finish_time = now + timedelta(seconds=duration_to_success)

        logger.info(f'Checking {entity_text} for {duration_to_success} seconds...')
        while True:
            logger.debug(f'Attempt #{attempt}')
            for entity in entities_to_check:
                method_to_check(entity)
                logger.debug('...OK')

            logger.debug(f'Intermediate success: all {entity_text}')
            if (now := datetime.now()) < finish_time:
                seconds_left = (finish_time - now).seconds
                logger.debug(f'{seconds_left} seconds left. Sleeping for {attempt_sleep} seconds...')
                time.sleep(attempt_sleep)
                attempt += 1
            else:
                return True

    @classmethod
    def cname_is_404(cls, cname: str) -> None:
        try:
            logger.debug(f'GET {cname}...')
            request = requests.get(url=f'{cls.protocol}://{cname}')
            if request.status_code != 404:  # TODO: think about this check
                logger.error(f'Status code {request.status_code})')
                raise URLIsNot404()
        except requests.exceptions.ConnectionError as e:  # DNS CNAME records should be created before hence should be reachable TODO remake with DNS creation
            logger.error(e)
            raise e

    @classmethod
    def resource_is_equal_to_existing(cls, resource: CDNResource) -> None:
        logger.debug(f'Comparing resource [{resource.id}]...')
        if not cls.resources_proc.compare_item_to_existing(resource):
            raise ResourceIsNotEqualToExisting()

    @classmethod
    def origin_is_available_with_200(cls) -> bool:
        request = requests.get(url=f'{cls.protocol}://{cls.origin_domain}')
        return request.status_code == 200

    @classmethod
    def initialize_resources(cls) -> None:
        if cls.initialize_type == ResourcesInitializeMethod.use_existing:
            cls.initialize_resources_from_existing()
        else:  # from scratch
            cls.make_new_resources()

    @classmethod
    def initialize_resources_from_existing(cls):
        #TODO: make resources from yaml and then compare them with what really in Cloud are

        cdn_resources = []
        for cdn_resource in cls.cdn_resources:
            resource = cls.resources_proc.make_default_cdn_resource(
                resource_id=cdn_resource.id,
                folder_id=cls.folder_id,
                cname=cdn_resource.cname,
                origin_group_id=cls.origin.origin_group_id,
            )
            cdn_resources.append(resource)
        cls.cdn_resources = cdn_resources

        if not SKIP_CHECK_RESOURCES_ARE_DEFAULT:
            if not cls.check_entities_for_period_of_time(
                    check_type=CheckType.RESOURCE_EQUAL,
                    entities_to_check=cls.cdn_resources
            ):
                pytest.fail('Resources are not default')

        cls.cdn_resources[0].active = False  # 'cdnroq3y4e74osnivr7e': 'yccdn-qa-1.marmota-bobak.ru'

        cls.cdn_resources[1].options.edge_cache_settings = EdgeCacheSettings(enabled=True, default_value=str(cls.short_ttl))  # 'cdnrcblizmcdlwnddrko': 'yccdn-qa-2.marmota-bobak.ru'

        cls.cdn_resources[2].options.edge_cache_settings = EdgeCacheSettings(enabled=False, default_value=str(cls.short_ttl))  # 'cdnrqvhjv4tyhbfwimw3': 'yccdn-qa-3.marmota-bobak.ru'

        cls.cdn_resources[3].options.query_params_options = QueryParamsOptions(ignore_query_string=EnabledBoolValueBool(enabled=True, value=True))  # 'cdnr5t2qvpsnaaglie2c': 'yccdn-qa-4.marmota-bobak.ru'

        cls.cdn_resources[4].options.query_params_options = QueryParamsOptions(ignore_query_string=EnabledBoolValueBool(enabled=True, value=False))  # 'cdnrpnabfdp7u6drjaua': 'yccdn-qa-5.marmota-bobak.ru'

        cls.cdn_resources[5].options.edge_cache_settings = EdgeCacheSettings(enabled=True, default_value=str(cls.long_ttl))

        cls.cdn_resources[6].options.static_headers = EnabledBoolValueDictStrStr(enabled=True, value={'param-to-test': cls.custom_header})

        cls.cdn_resources[9].options.ip_address_acl = IpAddressAcl(    # 'cdnrxcdi4xlyuwp42xfl': 'yccdn-qa-10.marmota-bobak.ru'
            enabled=True,
            excepted_values=['0.0.0.0/32', ],
            policy_type='POLICY_TYPE_ALLOW'
        )

        if not SKIP_UPDATE_RESOURCES:
            for resource in cls.cdn_resources:
                cls.resources_proc.update(resource)

        if not SKIP_CHECK_EQUAL_TO_EXISTING:
            if not cls.resources_are_equal_to_existing():
                pytest.fail('Resources are not equal to existing')

    @classmethod
    def resources_are_equal_to_existing(cls) -> bool:
        for resource in cls.cdn_resources:
            logger.debug(f'Checking resource: {resource}')
            if not cls.resources_proc.compare_item_to_existing(resource):
                logger.error(f'Resource [{resource.id}] with cname {resource.cname} is not same as existing')
                return False
        return True

    @classmethod
    def make_new_resources(cls):

        cls.origin_groups_proc = OriginGroupsAPIProcessor(
            entity_name=EntityName.ORIGIN_GROUP,
            api_url=cls.api_url,
            api_entity=APIEntity.ORIGIN_GROUP,
            folder_id=cls.folder_id,
            token=cls.token
        )

        cls.origin = Origin(source=cls.origin_domain, enabled=True)
        cls.origin_group = OriginGroup(origins=[cls.origin, ], name='test-origin', folder_id=cls.folder_id)
        cls.origin_groups_proc.create_item(item=cls.origin_group)

        if not cls.check_entities_for_period_of_time(check_type=CheckType.CNAME_404, entities_to_check=cls.cdn_cnames):
            pytest.fail('Setup has failed')

        logger.info(f'Success: all resources have been 404 for {cls.initialize_duration_check} seconds.')

        for cdn_resource in cls.cdn_resources:
            resource = cls.resources_proc.make_default_cdn_resource(
                folder_id=cls.folder_id,
                cname=cdn_resource['cname'],
                origin_group_id=cls.origin_group.id
            )
            cls.resources_proc.create_item(resource)
            cls.cdn_resources.append(resource)

    @classmethod
    def teardown_class(cls):
        logger.info('\n\n--- TEARDOWN ---')

        if cls.initialize_type == ResourcesInitializeMethod.from_scratch:
            logger.info('Deleting items...')
            assert cls.resources_proc.delete_several_items_by_ids([resource.id for resource in cls.cdn_resources]), \
                'Items have not been deleted'
            assert cls.origin_groups_proc.delete_item_by_id(cls.origin_group.id), 'Origin group has not been deleted'
        elif cls.initialize_type == ResourcesInitializeMethod.use_existing:
            logger.info('Resetting resources to default...')
            # TODO: RESET TO DEFAULT

            # TODO: DEBUG COMMENT - UNCOMMENT FOR PRODUCTION
            # assert cls.resources_are_equal_to_existing(), 'Resources were not reset'

        logger.info('done')

    # fake test-case to separate setup_class log output from first test-case
    @classmethod
    def test_setup(cls):
        assert True

    @classmethod
    def init_parameters_for_curl(
            cls,
            period_of_time: int = None,
            periods_count: int = None,
            finish_once_success: bool = None
    ):
        if period_of_time is None:
            period_of_time = cls.short_ttl
        if periods_count is None:
            periods_count = cls.periods_to_test
        if finish_once_success is None:
            finish_once_success = cls.finish_once_success

        time_to_test = periods_count * period_of_time
        start_time = time.time()

        return period_of_time, finish_once_success, time_to_test, start_time

    # TODO: make random check but with return once success
    # TODO: make async otherwise too few requests and needs too many periods_count (such as 5) to assert successfully
    # NB! better use targeted requests to specific cache hosts
    @classmethod
    def randomly_curl_resources(
            cls,
            resources: List[CDNResource],
            protocol: str = None,
            period_of_time: int = None,
            periods_count: int = None,
            add_query_arg: bool = False,
            finish_once_success: bool = None
    ) -> bool:

        if protocol is None:
            protocol = cls.protocol

        resources_statuses = {}
        query_generator = increment()
        period_of_time, finish_once_success, time_to_test, start_time = cls.init_parameters_for_curl(
            period_of_time, periods_count, finish_once_success
        )

        logger.info(f'GET resources [{[r.cname for r in resources]}] for {time_to_test} seconds...')
        while time.time() < start_time + time_to_test:
            for resource in resources:
                url = f'{protocol}://{resource.cname}'
                if add_query_arg:
                    url += '?foo=' + str(next(query_generator))
                logger.debug(f'GET {url}...')
                response = requests.get(url)
                response_headers = EdgeResponseHeaders(**response.headers)
                logger.debug(response_headers)
                if not response_headers.cache_status:
                    logger.debug(response_headers)
                    pytest.fail('Cache-Status header is absent')
                host_response = HostResponse(time=time.time(), status=response_headers.cache_status)
                resources_statuses.setdefault(
                    resource.id,
                    {response_headers.cache_host: []}
                ).setdefault(response_headers.cache_host, []).append(host_response)

                if finish_once_success:
                    if cls.cache_is_revalidated_during_ttl(
                            statuses=resources_statuses[resource.id][response_headers.cache_host],
                            period_of_time=period_of_time
                    ):
                        return True

        logger.debug(f'resources statuses: {resources_statuses}')

        # TODO: don't copy but create above where original dict is created
        resources_statuses_copy = deepcopy(resources_statuses)

        for resource_id, resource_statuses in resources_statuses.items():
            for host_name, host_responses in resource_statuses.items():
                if cls.cache_is_revalidated_during_ttl(statuses=host_responses, period_of_time=period_of_time):
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
            period_of_time: int = None,
            periods_count: int = None,
            add_query_arg: bool = False,
            finish_once_success: bool = None
    ) -> bool:

        if not cls.edge_cache_hosts:
            pytest.fail('Edge cache hosts should be defined for targeted curl')

        resources_statuses = {}
        resources_statuses_template = {}
        query_generator = increment()

        for resource in resources:
            resources_statuses[resource.id] = {}
            resources_statuses_template[resource.id] = {}
            for edge_host in cls.edge_cache_hosts:

                url = resource.cname
                if add_query_arg:
                    url += '?foo=' + str(next(query_generator))
                logger.debug(f'GET {url}...')
                response = http_get_request_through_ip_address(url, edge_host['ip_address'])
                response_headers = EdgeResponseHeaders(**response.headers)
                logger.debug(response_headers)

                if not response_headers.cache_status:
                    pytest.fail('Cache-Status header is absent')

                host_response = HostResponse(time=time.time(), status=response_headers.cache_status)
                resources_statuses[resource.id][edge_host['url']] = [host_response, ]
                resources_statuses_template[resource.id][edge_host['url']] = None

        period_of_time, finish_once_success, time_to_test, start_time = (
            cls.init_parameters_for_curl(period_of_time, periods_count, finish_once_success)
        )

        logger.info(f'GET resources [{[r.cname for r in resources]}] for up to {time_to_test} seconds...')
        while time.time() < start_time + time_to_test:
            for resource in resources:
                if resource.id in resources_statuses_template:
                    for edge_host in cls.edge_cache_hosts:
                        if edge_host in resources_statuses_template[resource.id]:

                            url = resource.cname
                            if add_query_arg:
                                url += '?foo=' + str(next(query_generator))
                            logger.debug(f'GET {url}...')
                            response = http_get_request_through_ip_address(url, edge_host['ip_address'])
                            response_headers = EdgeResponseHeaders(**response.headers)

                            if not response_headers.cache_status:
                                pytest.fail('Cache-Status header is absent')

                            host_response = HostResponse(time=time.time(), status=response_headers.cache_status)
                            resources_statuses[resource.id][response_headers.cache_host].append(host_response)

                            if cls.cache_is_revalidated_during_ttl(
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

    @classmethod
    def cache_is_revalidated_during_ttl(
            cls,
            statuses: List[HostResponse],
            period_of_time: int = None,
            ttl_error_rate: float = None
    ) -> bool:

        if period_of_time is None:
            period_of_time = cls.short_ttl
        if ttl_error_rate is None:
            ttl_error_rate = cls.ttl_error_rate

        last_revalidated_or_miss = None

        for host_response in statuses:
            if host_response.status in ('REVALIDATED', 'MISS'):
                if last_revalidated_or_miss:
                    # TODO: Check not the time of response received but response prepared by host? (Header 'Date:...')
                    # return host_response.time - last_revalidated_or_miss > error_rate * period_of_time
                    if host_response.time - last_revalidated_or_miss > ttl_error_rate * period_of_time:
                        return True
                    else:
                        raise RevalidatedBeforeTTL()
                last_revalidated_or_miss = host_response.time

        return False

    @classmethod
    def get_not_pinged_edges(cls) -> List[str]:
        res = []
        for edge_host_url in cls.edge_cache_hosts:
            if not ping(edge_host_url.url, attempts=2):
                res.append(edge_host_url.url)
        return res

    @classmethod
    def prepare_resources_list_to_test(cls, conditions: Callable) -> List[CDNResource]:
        resources_to_test = [r for r in cls.cdn_resources if conditions(r)]
        if not resources_to_test:
            pytest.fail(f'No resources found to test disabled edge_cache_settings')
        return resources_to_test




    @pytest.mark.skipif(SKIP_TESTS, reason='FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    def test_origin_group_created(self):
        if self.initialize_type == ResourcesInitializeMethod.from_scratch:
            assert self.origin_group.id, 'Origin group not created'

    @pytest.mark.skipif(SKIP_TESTS, reason='FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    def test_resources_are_created(self):
        assert self.cdn_resources and all(r.id for r in self.cdn_resources), 'CDN resources not created'

    @pytest.mark.skipif(SKIP_TESTS, reason='FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @allure.feature('Active resource')
    @allure.story('Active resource returns 200 or 403')
    @repeat_until_success_or_timeout()
    def test_active_resources(self):
        resources_to_test = self.prepare_resources_list_to_test(resource_is_active)

        for resource in resources_to_test:
            try:
                request_code = http_get_url(f'{self.protocol}://{resource.cname}')
            except requests.exceptions.ConnectionError as e:
                raise AssertionError(e)
            assert request_code in (200, 403), f'CDN resource {request_code}, should be 200 or 403'

    @pytest.mark.skipif(SKIP_TESTS, reason='FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @allure.feature('Active resource')
    @allure.story('Inactive resource returns 404')
    @repeat_until_success_or_timeout()
    def test_not_active_resources(self):
        resources_to_test = self.prepare_resources_list_to_test(resource_is_not_active)

        for resource in resources_to_test:
            request_code = http_get_url(f'{self.protocol}://{resource.cname}')
            assert request_code == 404, f'CDN resource {request_code}, should be 404'

    @pytest.mark.skipif(SKIP_TESTS, reason='FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @allure.feature('IP ACL')
    @repeat_until_success_or_timeout()
    def test_ip_address_acl(self):
        for resource in self.cdn_resources:
            url = f'{self.protocol}://{resource.cname}'
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

    @pytest.mark.skipif(SKIP_TESTS, reason='FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @allure.feature('Edge cache settings')
    @allure.story('Enabled cache revalidates after ttl')
    @repeat_until_success_or_timeout()
    def test_edge_cache_settings_enabled_revalidate_after_ttl(self):

        resources_to_test = self.prepare_resources_list_to_test(
            resource_is_active_and_no_acl_and_with_ttl(ttl=self.short_ttl)
        )
        assert self.method_to_curl_resources(resources=resources_to_test), 'Not all statuses were processed correctly'

    @pytest.mark.skipif(SKIP_TESTS, reason='FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @allure.feature('Edge cache settings')
    @allure.story('Enabled cache does not revalidates during ttl')
    @repeat_until_success_or_timeout()
    def test_edge_cache_settings_enabled_do_not_revalidate_within_ttl(self):
        def filter_to_test(r: CDNResource) -> bool:
            return all(
                (
                    resource_is_active_and_no_acl_and_ttl(r),
                    r.options.edge_cache_settings.default_value == str(self.long_ttl)

                )
            )

        resources_to_test = self.prepare_resources_list_to_test(filter_to_test)

        assert not self.method_to_curl_resources(
            resources=resources_to_test
        ), 'Not all statuses were processed correctly'

    @pytest.mark.skipif(SKIP_TESTS, reason='FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @allure.feature('Edge cache settings')
    @allure.story('Disabled cache does not add Cache-Status header')
    @repeat_until_success_or_timeout()
    def test_edge_cache_settings_disabled(self):
        def filter_to_test(r: CDNResource) -> bool:
            return all(
                (
                    resource_is_active_and_no_acl_and_cache_enabled(r),
                    not r.options.edge_cache_settings.enabled,
                )
            )

        resources_to_test = self.prepare_resources_list_to_test(filter_to_test)

        logger.info(f'GET resources [{[r.cname for r in resources_to_test]}]...')
        for resource in resources_to_test:
            url = f'{self.protocol}://{resource.cname}'
            response = requests.get(url)
            response_headers = EdgeResponseHeaders(**response.headers)
            assert not response_headers.cache_status

    @pytest.mark.skipif(SKIP_TESTS, reason='FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @allure.feature('Query')
    @allure.story('Ignore query params')
    @repeat_until_success_or_timeout()
    def test_ignore_query_string(self):
        def filter_to_test(r: CDNResource) -> bool:
            return all(
                (
                    resource_is_active_and_no_acl_and_with_ttl(ttl=self.short_ttl)(resource=r),
                    r.options.query_params_options,
                    r.options.query_params_options.ignore_query_string,
                    r.options.query_params_options.ignore_query_string.enabled,
                    r.options.query_params_options.ignore_query_string.value,
                )
            )

        resources_to_test = self.prepare_resources_list_to_test(filter_to_test)

        assert self.method_to_curl_resources(resources_to_test, add_query_arg=True)

    @pytest.mark.skipif(SKIP_TESTS, reason='FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @allure.feature('Query')
    @allure.story('Do not ignore query params')
    @repeat_until_success_or_timeout()
    def test_do_not_ignore_query_string(self):
        def filter_to_test(r: CDNResource) -> bool:
            return all(
                (
                    resource_is_active_and_no_acl_and_ttl(r),
                    r.options.query_params_options,
                    r.options.query_params_options.ignore_query_string,
                    not r.options.query_params_options.ignore_query_string.value,
                )
            )

        resources_to_test = self.prepare_resources_list_to_test(filter_to_test)

        with pytest.raises(RevalidatedBeforeTTL):
            self.method_to_curl_resources(resources_to_test, add_query_arg=True)

    @pytest.mark.skipif(SKIP_TESTS, reason='FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @allure.feature('Client header')
    @allure.story('Client custom header is set')
    @repeat_until_success_or_timeout()
    def test_static_header_is_set(self):
        def filter_to_test(r: CDNResource) -> bool:
            return all(
                (
                    resource_is_active_and_no_acl_and_with_ttl(ttl=self.short_ttl)(resource=r),
                    r.options.static_headers,
                    r.options.static_headers.enabled,
                    'param-to-test' in r.options.static_headers.value
                )
            )

        resources_to_test = self.prepare_resources_list_to_test(filter_to_test)
        logger.info(f'GET resources [{[r.cname for r in resources_to_test]}]...')

        for resource in resources_to_test:
            url = f'{self.protocol}://{resource.cname}'
            response = requests.get(url=url)
            response_headers = EdgeResponseHeaders(**response.headers)
            param_value = response_headers.param_to_test

            logger.debug(f'request: GET {url}')
            logger.debug(f'response headers: {response_headers}')

            assert param_value == self.custom_header, (f'expected header [param-to-test] '
                                                       f'with value [{self.custom_header}], got {param_value}')








