import json
import logging
from typing import Optional, List, Dict

import requests
from pydantic import BaseModel, ValidationError

from app.model import CDNResource, SSLCertificate, CDNResourceOptions, EdgeCacheSettings, EnabledBoolValueDictStrStr
from app.apiprocessor import APIProcessor
from utils import repeat_and_sleep, make_random_8_symbols

class CDNResourceProcessorResponseError(BaseModel):
    code: int
    message: str
    details: List[Dict[str, str]]

class CDNResourcesAPIProcessor(APIProcessor):

    @repeat_and_sleep(times_to_repeat=3, sleep_duration=1)
    def create_cdn_resource(self, cdn_resource: CDNResource) -> Optional[str]:
        url = f'{self.api_url}/resources/'
        headers = {'Authorization': f'Bearer {self.token}'}
        if not (payload := self.make_json_from_object_with_correct_origin_group(cdn_resource)):
            logging.error('[originGroupId] attribute is absent at cdn_resource object')
            logging.debug(f'cdn_resource: {cdn_resource}')
            return None

        request = requests.post(url=url, headers=headers, json=payload)

        response_status = request.status_code
        if response_status == 200:
            try:
                response_dict = request.json()

                if error := response_dict.get('error'):
                    try:
                        error = CDNResourceProcessorResponseError.model_validate(error)
                    except ValidationError as e:
                        logging.error('pydantic validation error')
                        logging.debug(f'error details: {e}')

                    logging.error(f'API error: {error.message}, code {error.code}')
                    return None

                if 'metadata' in response_dict and (cdn_resource_id := response_dict['metadata'].get('resourceId')):
                    logging.info(f'CDN Resource [{cdn_resource_id}] created successfully')
                    logging.debug(response_dict)
                    return cdn_resource_id

            except json.JSONDecodeError as e:
                logging.error('JSONDecodeError')
                logging.debug(f'error details: {e}')
                return None
            except KeyError as e:
                logging.error('No such key')
                logging.debug(f'error details: {e}')
                return None
            finally:
                logging.debug(f'request payload: {payload}')
                logging.debug(f'response text: {request.text}')
        elif response_status == 400:
            logging.error('bad request')
            logging.debug(f'request payload: {payload}')
            logging.debug(f'response text: {request.text}')
            return None

    def create_several_default_cdn_resources(
            self,
            folder_id: str,
            cname_domain:str,
            origin_group_id: str,
            cdn_resource: CDNResource=None,
            n: int = 1
    ) -> Optional[List[str]]:

        res = []

        if not cdn_resource:
            cdn_resource = self.make_default_cdn_resource(
                folder_id=folder_id,
                cname='',
                origin_group_id=origin_group_id
            )

        cname_generator = self.random_cname_generator(cname_domain=cname_domain)
        for i in range(n):
            cdn_resource.cname = next(cname_generator)
            if not (cdn_id := self.create_cdn_resource(cdn_resource=cdn_resource)):  # на случай, если сгенерирован такой-же cname TODO: заменить на обработку кастомной ошибки одинакового cname
                cdn_resource.cname = next(cname_generator)
                if not (cdn_id := self.create_cdn_resource(cdn_resource=cdn_resource)):
                    logging.error(f'Error creating cdn resource #{i}')
            res.append(cdn_id)


        if not res:
            logging.error('Error while creating resources: none resources created')

        logging.info(f'{len(res)} resources created')
        logging.debug('resources created: ', res)

        return res

    @staticmethod
    def random_cname_generator(cname_domain: str) -> str:
        while True:
            yield f'{make_random_8_symbols()}.{cname_domain}'

    def update_cdn_resource(self, new_cdn_resource: CDNResource):
        url = f'{self.api_url}/resources/'
        headers = {'Authorization': f'Bearer {self.token}'}
        payload = {
            'folderId': new_cdn_resource.folder_id,
            'cname': new_cdn_resource.cname,
            'origin': {
                'originGroupId': new_cdn_resource.origin_group_id
            },
            'originProtocol': new_cdn_resource.origin_protocol
        }

        request = requests.post(url=url, headers=headers, json=payload)

        response_status = request.status_code
        if response_status == 200:
            try:
                response_dict = request.json()

                if error := response_dict.get('error'):
                    try:
                        error = CDNResourceProcessorResponseError.model_validate(error)
                    except ValidationError as e:
                        logging.error('pydantic validation error')
                        logging.debug(f'error details: {e}')

                    logging.error(f'API error: {error.message}, code {error.code}')
                    return None

                if 'metadata' in response_dict and (cdn_resource_id := response_dict['metadata'].get('resourceId')):
                    logging.info(f'CDN Resource [{cdn_resource_id}] created successfully')
                    logging.debug(response_dict)
                    return cdn_resource_id

            except json.JSONDecodeError as e:
                ...  # log
                return None
            except KeyError as e:
                ...  # log
                return None
            finally:
                logging.debug(f'response text: {request.text}')
        elif response_status == 400:
            logging.error('bad request')
            logging.debug(request.text)
            return None

    @staticmethod
    def make_cdn_resource_ssl_certificate_attribute(ssl_type: str = None) -> SSLCertificate:
        # TODO: make different types
        if not ssl_type:
            return SSLCertificate(
                type='DONT_USE',
                status='READY'
            )

    @staticmethod
    def make_default_cdn_resource(folder_id: str, cname: str, origin_group_id: str, ) -> CDNResource:
        options = CDNResourceOptions(
            edge_cache_settings=EdgeCacheSettings(enabled=True, default_value='10'),
            static_headers=EnabledBoolValueDictStrStr(
                enabled=True,
                value={make_random_8_symbols(): make_random_8_symbols()}
            )
        )
        return CDNResource(
            folder_id=folder_id,
            cname=cname,
            origin_group_id=origin_group_id,
            origin_protocol='HTTP',
            options=options
        )

    @staticmethod
    def make_json_from_object_with_correct_origin_group(cdn_resource: CDNResource) -> Optional[dict]:
        cdn_resource_dict = cdn_resource.model_dump(exclude_none=True, by_alias=True)
        if origin_group_id := cdn_resource_dict.get('originGroupId'):
            cdn_resource_dict['origin'] = {'originGroupId': origin_group_id}
            return cdn_resource_dict
        return None

