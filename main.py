import logging
import os
import time
import json
import requests
from utils import ping, http_get_request_through_ip_address


from app.authorization import Authorization
from app.resource import ResourcesAPIProcessor
from app.origingroup import OriginGroupsAPIProcessor
from app.apiprocessor import EntityName, APIEntity
from app.model import OriginGroup, Origin, OriginMeta, OriginMetaCommon, IpAddressAcl, CDNResource

#TODO: get logging level from cli args
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
logging.info('Starting service')


def main():
    OAUTH = os.environ['OAUTH']
    IAM_TOKEN_URL = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'

    API_URL = 'https://cdn.api.cloud.yandex.net/cdn/v1'
    FOLDER_ID = 'b1gjifkk80hojm6nv42n'
    ORIGIN_GROUP_ID='5867945351699784427'
    EXISTING_RESOURCES_IDS = [
        'cdnroq3y4e74osnivr7e', 'cdnrcblizmcdlwnddrko', 'cdnrqvhjv4tyhbfwimw3', 'cdnr5t2qvpsnaaglie2c',
        'cdnrpnabfdp7u6drjaua', 'cdnr7bbwrxhguo63wkpl', 'cdnrrausbqmlmhzq6ffp', 'cdnrfvuvfped42dkmyrv',
        'cdnrcqdphowdoxyxrufs', 'cdnrxcdi4xlyuwp42xfl'
    ]

    authorization = Authorization(oauth=OAUTH, iam_token_url=IAM_TOKEN_URL)
    token = authorization.get_token()
    print(token)

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

