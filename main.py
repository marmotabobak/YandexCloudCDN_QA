import os
from authorization import Authorization
from cdnresourcesprocessor import CDNResourcesProcessor
from model import CDNResource

OAUTH = os.environ['OAUTH']  #TODO: read from args
FOLDER_ID = os.environ['FOLDER_ID']

IAM_TOKEN_URL = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'
API_URL = 'https://cdn.api.cloud.yandex.net/cdn/v1'

def main():
    authorization = Authorization(oauth=OAUTH, iam_token_url=IAM_TOKEN_URL)
    token = authorization.get_token()

    cdn_resources_processor = CDNResourcesProcessor(api_url=API_URL, folder_id=FOLDER_ID, token=token)
    # cdn_resources_processor.delete_all_cdn_resources()
    cdn_resources_ids = cdn_resources_processor.get_cdn_resources_ids()
    cdn_resource = cdn_resources_processor.get_cdn_resource(cdn_resources_ids[0])
    print(cdn_resource.options)

if __name__ == '__main__':
    main()


