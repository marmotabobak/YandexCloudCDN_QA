import logging
import os
import time

from app.authorization import Authorization
from app.resource import ResourcesAPIProcessor
from app.origingroup import OriginGroupsAPIProcessor
from app.apiprocessor import EntityName, APIEntity
from app.model import OriginGroup, Origin, OriginMeta, OriginMetaCommon

#TODO: get logging level from cli args
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
logging.info('Starting service')


def main():
    OAUTH = os.environ['OAUTH']
    IAM_TOKEN_URL = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'

    API_URL = 'https://cdn.api.cloud.yandex.net/cdn/v1'
    FOLDER_ID = 'b1g0nv5cjfie2efe0dnm'
    ORIGIN_GROUP_ID='194852979077665688'

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

    EXISTING_RESOURCES_IDS = ['cdnrevowkuszfkeblnfc', 'cdnreiln4kbk5uztr5rc',
                              'cdnrqxwudm2tdwzmsl4w', 'cdnrrcdn3q4fltujg7bq', 'cdnrbv6obmkkydjfkxkl',
                              'cdnrt4cp7nuni3yusj2i', 'cdnrjrpnthbe3um5wt5s', 'cdnrdntvcu6cisuovrzj',
                              'cdnr3qmdtk7igcn4ioti', 'cdnrtofltsfkvexeor73']


    # resources_processor.delete_all_items()
    i = 0
    for id in EXISTING_RESOURCES_IDS:
        resource = resources_processor.make_default_cdn_resource(
            resource_id=id,
            folder_id=FOLDER_ID,
            cname=f'cdn-{i}.marmota-bobak.ru',
            origin_group_id=ORIGIN_GROUP_ID,
        )
        i += 1
        existing_resource = resources_processor.get_item_by_id(id)

        resource_dict = resource.model_dump(exclude={'created_at', 'updated_at', 'origin_group_name'})
        existing_resource_dict = existing_resource.model_dump(exclude={'created_at', 'updated_at', 'origin_group_name'})

        if resource_dict != existing_resource_dict:
            print(resource_dict)
            print(existing_resource_dict)


    #
    # origin_groups_processor = OriginGroupsAPIProcessor(
    #     entity_name=EntityName.ORIGIN_GROUP,
    #     api_url=API_URL,
    #     api_entity=APIEntity.ORIGIN_GROUP,
    #     folder_id=FOLDER_ID,
    #     token=token
    # )
    #
    # origin = Origin(source='marmota-bobak.ru', enabled=True)
    # origin_group = OriginGroup(origins=[origin, ], name='test-origin', folder_id=FOLDER_ID)
    #
    # for i in range(10):
    #     origin_group_id = origin_groups_processor.create_item(origin_group)
    #     resource = resources_processor.make_default_cdn_resource(
    #         folder_id=FOLDER_ID,
    #         cname=f'cdnxxx{i}.marmota-bobak.ru',
    #         origin_group_id=origin_group_id
    #     )
    #     resources_processor.create_item(resource)
    #
    #     resources_processor.delete_item_by_id(resource.id)
    #     origin_groups_processor.delete_item_by_id(origin_group.id)



    # resources_processor.create_several_default_cdn_resources(
    #     cname_domain='marmota-bobak.ru',
    #     origin_group_id=origin_group_id,
    #     n=10
    # )
    ...


if __name__ == '__main__':
    main()


