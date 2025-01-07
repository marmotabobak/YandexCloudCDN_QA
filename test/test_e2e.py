import os

import allure
import pytest
import requests

from app.model import CDNResource
from test.logger import logger
from test.model import ResourcesInitializeMethod, EdgeResponseHeaders
from test.utils import RevalidatedBeforeTTL, resource_is_active, \
    resource_is_not_active, resource_is_active_and_no_acl_and_cache_enabled, resource_is_active_and_no_acl_and_ttl, \
    resource_is_active_and_no_acl_and_with_ttl, http_get_status_code, repeat_until_success_or_timeout, \
    resource_is_active_and_no_acl
from test.utils_for_test_class import UtilsForTestClass

# TODO: !True ONLY FOR DEBUG! Use False for Production
SKIP_TESTS = False

OAUTH = os.environ['OAUTH']
CONFIG_PATH = 'test/config.yaml'
# CONFIG_PATH = 'test/edge.yaml'

class TestCDN(UtilsForTestClass):

    @classmethod
    def setup_class(cls):
        cls.init(config_path=CONFIG_PATH)
        cls.init_iam_token()
        cls.init_resources_processors()

        logger.info('--- SETUP ---')
        cls.check_origin_is_200()
        cls.ping_edges()
        cls.init_resources()
        logger.info('--- SETUP finished ---')

    @classmethod
    def teardown_class(cls):
        logger.info('\n\n--- TEARDOWN ---')

        if cls.initialize_type == ResourcesInitializeMethod.from_scratch:
            logger.info('Deleting items...')
            cls.cdn_resources_proc.delete_several_items_by_ids([resource.id for resource in cls.cdn_resources])
            cls.origin_groups_proc.delete_item_by_id(cls.origin_group.id)
        elif cls.initialize_type == ResourcesInitializeMethod.use_existing:
            logger.info('Resetting resources to default...')
            # TODO: RESET TO DEFAULT

            # TODO: DEBUG COMMENT - UNCOMMENT FOR PRODUCTION
            # assert cls.resources_are_equal_to_existing(), 'Resources were not reset'

        logger.info('done')

    # fake test-case to separate setup_class log output from first test-case
    @classmethod
    def test_fake_finish_setup(cls):
        assert True

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
                request_code = http_get_status_code(f'{self.protocol}://{resource.cname}')
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
            response_code = http_get_status_code(f'{self.protocol}://{resource.cname}')
            assert response_code == 404, f'CDN resource {response_code}, should be 404'

    @pytest.mark.skipif(SKIP_TESTS, reason='FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @allure.feature('IP ACL')
    @allure.story('Resource is NOT available with ACL on')
    @repeat_until_success_or_timeout()
    def test_ip_address_acl_on(self):
        def filter_to_test(r: CDNResource) -> bool:
            if r.active and r.options and r.options.ip_address_acl and r.options.ip_address_acl:
                if r.options.ip_address_acl.policy_type == 'POLICY_TYPE_ALLOW':
                    return True
            return False

        resources_to_test = self.prepare_resources_list_to_test(filter_to_test)
        for resource in resources_to_test:
            request_code = http_get_status_code(f'{self.protocol}://{resource.cname}')
            assert request_code == 403, f'CDN resource {request_code}, should be 403'

    @pytest.mark.skipif(SKIP_TESTS, reason='FOR DEBUG ONLY - ACTIVATE FOR PRODUCTION USE')
    @allure.feature('IP ACL')
    @allure.story('Resource is available without ACL')
    @repeat_until_success_or_timeout()
    def test_ip_address_acl_off(self):
        resources_to_test = self.prepare_resources_list_to_test(resource_is_active_and_no_acl)
        for resource in resources_to_test:
            request_code = http_get_status_code(f'{self.protocol}://{resource.cname}')
            assert request_code != 403, f'CDN resource {request_code}, should not be 403'

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








