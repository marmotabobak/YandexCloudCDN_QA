import logging
import os
import random

import yaml


from app.authorization import Authorization

#TODO: get logging level from cli args
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
logging.info('Starting service')

from test.utils import get_connection_error_type


def main():
    ...
    # OAUTH = os.environ['OAUTH']
    # authorization = Authorization(oauth=OAUTH, iam_token_url=IAM_TOKEN_URL)
    # token = authorization.get_token()
    # print(token)

    # resources_processor = ResourcesAPIProcessor(
    #     entity_name=EntityName.CDN_RESOURCE,
    #     api_url=API_URL,
    #     api_entity=APIEntity.CDN_RESOURCE,
    #     folder_id=FOLDER_ID,
    #     token=token
    # )
    #
    # resource = resources_processor.make_default_cdn_resource(
    #     resource_id='cdnrxcdi4xlyuwp42xfl',
    #     folder_id=FOLDER_ID,
    #     cname=f'yccdn-qa-10.marmota-bobak.ru',
    #     origin_group_id=ORIGIN_GROUP_ID,
    # )
    #
    # resource.options.ip_address_acl = IpAddressAcl(
    #     enabled=False,
    #     excepted_values=['0.0.0.0/32', ],
    #     policy_type='POLICY_TYPE_ALLOW'
    # )
    # resource.options.edge_cache_settings.enabled = False
    #
    #
    # # resources_processor.update(resource)
    # #
    # if resources_processor.compare_item_to_existing(resource):
    #     print('!!!OK!!!')
    # else:
    #     print('=( FAIL =(')
    #

if __name__ == '__main__':
    # main()
    ...
    # OAUTH = os.environ['OAUTH']
    # authorization = Authorization(oauth=OAUTH, iam_token_url='https://iam.api.cloud.yandex.net/iam/v1/tokens')
    # token = authorization.get_token()
    # # print(token)
    # import requests
    # import socket
    # import urllib3
    #
    # try:
    #     requests.get('http://edge-qa-1.marmotabobak.ru/')
    # except requests.exceptions.ConnectionError as e:
    #     print(get_connection_error_type(e.__context__))

from typing import Callable, Any
from functools import wraps
import time
import random

def repeat_until_success_or_timeout(attempts: int = 10, attempt_delay: int = 0):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for i in range(attempts):
                logging.debug(f'Attempt #{i + 1} of {attempts}...')
                if func(*args, **kwargs):
                    return True
                if i < attempts - 1:
                    time.sleep(attempt_delay)
            print('!!!ERRR')
        return wrapper
    return decorator

def repeat_for_period_ot_time_or_until_fail(
        attempts_needed_to_succeed: int = 3,
        success_attempt_delay: int = 0,
        tries_if_fail: int = 2):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> bool:
            for _ in range(tries_if_fail):
                res = None
                for i in range(attempts_needed_to_succeed):
                    logging.debug(f'Attempt #{i + 1} of {attempts_needed_to_succeed}...')
                    res = func(*args, **kwargs)
                    if not res:
                        break
                    logging.debug(f'...OK. Sleeping for {success_attempt_delay} seconds...')
                    if i < attempts_needed_to_succeed - 1:
                        time.sleep(success_attempt_delay)
                if not res:
                    continue
                else:
                    return True
            return False
        return wrapper
    return decorator

@repeat_for_period_ot_time_or_until_fail()
def get_numb():
    n = random.randint(0, 1)
    print(n)
    return n == 1

print(get_numb())