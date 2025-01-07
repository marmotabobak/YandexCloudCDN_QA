import logging
import os
import yaml


from app.authorization import Authorization

#TODO: get logging level from cli args
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
logging.info('Starting service')


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
    import requests
    try:
        request = requests.get(url='http://edge-qa-1.marmotabobak.ru')
    except Exception as e:
        print(e)
    print(1)


