import logging
import os

from app.authorization import Authorization
from app.cdnresource import CDNResourcesAPIProcessor
from app.apiprocessor import EntityName, APIEntity

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

    cdn_resources_processor = CDNResourcesAPIProcessor(
        entity_name=EntityName.CDN_RESOURCE,
        api_url=API_URL,
        api_entity=APIEntity.CDN_RESOURCE,
        folder_id=FOLDER_ID,
        token=token
    )
    cdn_resources_processor.delete_all_items()

    #DEBUG
    default_cname_domain = 'marmota-bobak.ru'
    default_origin_group_id = '341382'

    # cdn_resource = cdn_resources_processor.make_default_cdn_resource(
    #     folder_id=FOLDER_ID,
    #     cname='cdn2d1.marmota-bobak.ru',
    #     origin_group_id=default_origin_group_id
    # )
    # cdn_resources_processor.create_item(cdn_resource)


    cdn_ids = cdn_resources_processor.create_several_default_cdn_resources(
        folder_id=FOLDER_ID,
        cname_domain=default_cname_domain,
        origin_group_id=default_origin_group_id,
        n = 2
    )
    print(cdn_ids)
    # print(cdn_resources_processor.get_item(item_id=cdn_ids[0]))

    # cdn_resources_processor.delete_all_cdn_resources()

if __name__ == '__main__':
    main()


