from app.model import CDNResource
from typing import Callable, List
import pytest
import requests
from test.logger import logger


def resource_is_active(resource: CDNResource) -> bool:
    return resource.active

def resource_is_not_active(resource: CDNResource) -> bool:
    return not resource_is_active(resource)

def resource_is_active_and_no_acl(resource: CDNResource) -> bool:
    return all(
        (
            resource_is_active(resource),
            resource.options,
            not resource.options.ip_address_acl or not resource.options.ip_address_acl.enabled,
        )
    )

def resource_is_active_and_no_acl_and_cache_enabled(resource: CDNResource) -> bool:
    return all(
        (
            resource_is_active_and_no_acl(resource),
            resource.options.edge_cache_settings,
        )
    )

def resource_is_active_and_no_acl_and_ttl(resource: CDNResource) -> bool:
    return all(
        (
            resource_is_active_and_no_acl_and_cache_enabled(resource),
            resource.options.edge_cache_settings.enabled,
        )
    )

def resource_is_active_and_no_acl_and_with_ttl(ttl: int) -> Callable:
    def func(resource: CDNResource):
        return all(
            (
                resource_is_active_and_no_acl_and_ttl(resource),
                resource.options.edge_cache_settings.default_value == str(ttl)
            )
        )
    return func





def http_get_url(url: str) -> int:
    logger.debug(f'GET {url}...')
    request = requests.get(url)
    return request.status_code
