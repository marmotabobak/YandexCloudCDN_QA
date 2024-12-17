import logging
import os
import time
import json

from requests import delete

from app.authorization import Authorization
from app.resource import ResourcesAPIProcessor
from app.origingroup import OriginGroupsAPIProcessor
from app.apiprocessor import EntityName, APIEntity
from app.model import OriginGroup, Origin, OriginMeta, OriginMetaCommon, IpAddressAcl

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
    # print(token)

    resources_processor = ResourcesAPIProcessor(
        entity_name=EntityName.CDN_RESOURCE,
        api_url=API_URL,
        api_entity=APIEntity.CDN_RESOURCE,
        folder_id=FOLDER_ID,
        token=token
    )

    resource = resources_processor.make_default_cdn_resource(
        resource_id='cdnrxcdi4xlyuwp42xfl',
        folder_id=FOLDER_ID,
        cname=f'yccdn-qa-10.marmota-bobak.ru',
        origin_group_id=ORIGIN_GROUP_ID,
    )
    # resource.options.ip_address_acl = IpAddressAcl(
    #     enabled=True,
    #     excepted_values=['0.0.0.0/32', ],
    #     policy_type='POLICY_TYPE_ALLOW'
    # )

    # resources_processor.update(resource)

    resource_dict = resource.model_dump(exclude={'created_at', 'updated_at', 'origin_group_name'})

    existing_resource = resources_processor.get_item_by_id(resource.id)

    existing_resource_dict = existing_resource.model_dump(exclude={'created_at', 'updated_at', 'origin_group_name'})

    if resource_dict != existing_resource_dict:
        print('=( FAIL =(')
        for k, v in resource_dict['options'].items():
            if v != existing_resource_dict['options'][k]:
                print(k, v, existing_resource_dict['options'][k])
    else:
        print('!!!OK!!!')



if __name__ == '__main__':
    main()


