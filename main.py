import logging
import os

from app.authorization import Authorization
from app.resource import ResourcesAPIProcessor
from app.origingroup import OriginGroupsAPIProcessor
from app.apiprocessor import EntityName, APIEntity
from app.model import OriginGroup, Origin, OriginMeta, OriginMetaCommon

#TODO: get logging level from cli args
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
logging.info('Starting service')

OAUTH = os.environ['OAUTH']  #TODO: get from cli args
FOLDER_ID = os.environ['FOLDER_ID']  #TODO: get from cli args

IAM_TOKEN_URL = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'
API_URL = 'https://cdn.api.cloud.yandex.net/cdn/v1'

def main():
    authorization = Authorization(oauth=OAUTH, iam_token_url=IAM_TOKEN_URL)
    if not (token := authorization.get_token()):
        logging.error('iam-token has not been received')
        return
    else:
        logging.info('got iam-token')

    resources_processor = ResourcesAPIProcessor(
        entity_name=EntityName.CDN_RESOURCE,
        api_url=API_URL,
        api_entity=APIEntity.CDN_RESOURCE,
        folder_id=FOLDER_ID,
        token=token
    )

    origin_groups_processor = OriginGroupsAPIProcessor(
        entity_name=EntityName.ORIGIN_GROUP,
        api_url=API_URL,
        api_entity=APIEntity.ORIGIN_GROUP,
        folder_id=FOLDER_ID,
        token=token
    )

    resources_processor.delete_all_items()
    origin_groups_processor.delete_all_items()

    origin = Origin(source='marmota-bobak.ru', enabled=True)
    origin_group = OriginGroup(origins=[origin, ], name='test origin', folder_id=FOLDER_ID)
    origin_group_id = origin_groups_processor.create_item(item=origin_group)

    resource = resources_processor.make_default_cdn_resource(
        folder_id=FOLDER_ID,
        cname='cdn.marmota-bobak.ru',
        origin_group_id=origin_group_id
    )
    resource_id = resources_processor.create_item(item=resource)

    # cdn_ids = cdn_resources_processor.create_several_default_cdn_resources(
    #     folder_id=FOLDER_ID,
    #     cname_domain=default_cname_domain,
    #     origin_group_id=default_origin_group_id,
    #     n = 2
    # )




if __name__ == '__main__':
    main()


