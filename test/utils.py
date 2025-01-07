import time
from functools import wraps
from typing import Callable, Any

import pytest
import requests

from app.model import CDNResource
from test.logger import logger


class RevalidatedBeforeTTL(Exception): ...

class ResourceIsNotEqualToExisting(Exception): ...

class URLIsNot404(Exception): ...





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

def repeat_until_success_or_timeout(attempts: int = 20, attempt_delay: int = 15):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for i in range(attempts):
                logger.debug(f'Attempt #{i + 1} of {attempts}...')
                try:
                    res = func(*args, **kwargs)
                    return res
                except (AssertionError, ResourceIsNotEqualToExisting, RevalidatedBeforeTTL, URLIsNot404) as e:
                    logger.debug(f'...failed. Error: [{e}]. Sleeping for {attempt_delay} seconds...')
                    time.sleep(attempt_delay)
            pytest.fail('All attempts failed.')
        return wrapper
    return decorator