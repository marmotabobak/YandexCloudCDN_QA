import time
from functools import wraps
from typing import Callable, Any

import pytest
import requests
from requests.exceptions import ReadTimeout
from enum import Enum
from urllib3.exceptions import MaxRetryError, NameResolutionError, ProtocolError


from app.model import CDNResource
from test.logger import logger


class RevalidatedBeforeTTL(Exception): ...

class ResourceIsNotEqualToExisting(Exception): ...


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


def http_get_status_code(url: str) -> int:
    logger.info(f'GET {url}...')
    response = requests.get(url, timeout=5)
    return response.status_code

def repeat_until_success_or_timeout(attempts: int = 20, attempt_delay: int = 15):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for i in range(attempts):
                logger.debug(f'Attempt #{i + 1} of {attempts}...')
                try:
                    res = func(*args, **kwargs)
                    return res
                except (AssertionError, ResourceIsNotEqualToExisting, RevalidatedBeforeTTL, ReadTimeout) as e:
                    logger.debug(f'...failed. Error: [{e}]. Sleeping for {attempt_delay} seconds...')
                    if i < attempts - 1:
                        time.sleep(attempt_delay)
            pytest.fail('All attempts failed.')
        return wrapper
    return decorator

def repeat_for_period_ot_time_or_until_fail(
        attempts_needed_to_succeed: int = 5,
        success_attempt_delay: int = 1,
        tries_if_fail: int = 2):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> bool:
            for _ in range(tries_if_fail):
                res = None
                for i in range(attempts_needed_to_succeed):
                    logger.debug(f'Attempt #{i + 1} of {attempts_needed_to_succeed}...')
                    res = func(*args, **kwargs)
                    if not res:
                        break
                    logger.debug(f'...OK. Sleeping for {success_attempt_delay} seconds...')
                    if i < attempts_needed_to_succeed - 1:
                        time.sleep(success_attempt_delay)
                if not res:
                    continue
                else:
                    return True
            return False
        return wrapper
    return decorator

class ConnectionErrorType(Enum):
    NAME_RESOLUTION_ERROR = 'Name resolution error'
    RESET_BY_PEER = 'Connection reset by peer'
    UNKNOWN = 'Unknown connection error'

def get_connection_error_type(err: BaseException) -> ConnectionErrorType:
    if isinstance(err, MaxRetryError) and isinstance(err.reason, NameResolutionError):  # dns not resolved
        return ConnectionErrorType.NAME_RESOLUTION_ERROR
    if isinstance(err, ProtocolError) and isinstance(err.args, tuple):
        if len(err.args) >= 2 and (err_details := err.args[1]) and isinstance(err_details, ConnectionResetError):
            err_args = err_details.args
            if isinstance(err_args, tuple) and len(err_args) and err_args[0] in (54, 10054):  # 54 Unix, 10054 Windows
                return ConnectionErrorType.RESET_BY_PEER
    return ConnectionErrorType.UNKNOWN