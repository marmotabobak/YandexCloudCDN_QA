import json
import logging
from typing import Optional, List, Dict, Iterator

import requests
from pydantic import BaseModel, ValidationError

from app.model import *
from app.apiprocessor import APIProcessor
from utils import make_random_8_symbols


class ResourcesAPIProcessor(APIProcessor):

    def make_dict_from_item(self, item: CDNResource) -> Optional[dict]:
        if not (item_dict := super().make_dict_from_item(item)):
            logging.error('error while transforming cdn resource to dict')
            logging.debug(f'cdn resource: {item}')
            return None

        if not (origin_group_id := item_dict.get('originGroupId')):
            logging.error('[originGroupId] attribute is absent at cdn resource dict')
            logging.debug(f'cdn resource dict: {item_dict}')
            return None

        # TODO: move to create method as it is used only there
        item_dict['origin'] = {'originGroupId': origin_group_id}
        del (item_dict['originGroupId'])
        return item_dict

    def create_several_default_cdn_resources(
            self,
            cname_domain:str,
            origin_group_id: str,
            cdn_resource: CDNResource=None,
            n: int = 1
    ) -> Optional[List[str]]:

        res = []

        if not cdn_resource:
            cdn_resource = self.make_default_cdn_resource(
                folder_id=self.folder_id,
                cname='',
                origin_group_id=origin_group_id
            )

        cname_generator = self.random_cname_generator(cname_domain=cname_domain)
        for i in range(n):
            cdn_resource.cname = next(cname_generator)
            if not (cdn_id := self.create_item(item=cdn_resource)):
                cdn_resource.cname = next(cname_generator)  # крайне маловероятно, но повторно генерим cname - на случай, если предыдущий совпал с уже существующим TODO: заменить на обработку кастомной ошибки одинакового cname
                if not (cdn_id := self.create_item(item=cdn_resource)):
                    logging.error(f'Error creating cdn resource #{i+1}')

            if cdn_id:
                logging.info(f'сdn resource #{i+1} with id [{cdn_id}] created')
                res.append(cdn_id)


        if not res:
            logging.error('Error while creating resources: none resources created')

        logging.info(f'{len(res)} resources created')
        logging.debug(f'resources created: [{res}]')

        return res

    @staticmethod
    def random_cname_generator(cname_domain: str) -> Iterator[str]:
        while True:
            yield f'{make_random_8_symbols()}.{cname_domain}'

    def update(self, updated_resource: CDNResource):
        url = f'{self.api_url}/resources/{updated_resource.id}'
        headers = {'Authorization': f'Bearer {self.token}'}

        payload = updated_resource.model_dump(exclude={'created_at', 'updated_at'}, by_alias=True)
        request = requests.patch(url=url, headers=headers, json=payload)

        response_status = request.status_code
        if response_status == 200:
            try:
                response_dict = request.json()

                if error := response_dict.get('error'):
                    try:
                        error = APIProcessorError.model_validate(error)
                    except ValidationError as e:
                        logging.error('pydantic validation error')
                        logging.debug(f'error details: {e}')

                    logging.error(f'API error: {error.message}, code {error.code}')
                    return None

                if 'metadata' in response_dict and (cdn_resource_id := response_dict['metadata'].get('resourceId')):
                    logging.info(f'CDN Resource [{cdn_resource_id}] updated successfully')
                    logging.debug(response_dict)
                    return cdn_resource_id

            except json.JSONDecodeError as e:
                logging.error('JSONDecodeError')
                logging.debug(f'error details: {e}')
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
    def make_default_cdn_resource(folder_id: str, cname: str, origin_group_id: str, resource_id: str=None) -> CDNResource:
        return CDNResource(
            active=True,
            options=CDNResourceOptions(
                edge_cache_settings=EdgeCacheSettings(enabled=True, default_value='10'),
                browser_cache_settings=EnabledBool(enabled=False),
                query_params_options=QueryParamsOptions(
                    ignore_query_string=EnabledBoolValueBool(enabled=True, value=True)),
                slice=EnabledBoolValueBool(enabled=True, value=False),
                compression_options=CompressionOptions(gzip_on=EnabledBoolValueBool(enabled=True, value=True)),
                static_headers=EnabledBoolValueDictStrStr(enabled=True, value={'fizz': 'buzz'}),
                cors=Cors(enabled=False),
                stale=EnabledBool(enabled=False),
                allowed_http_methods=AllowedHttpMethods(enabled=True, value=['GET', 'HEAD', 'OPTIONS']),
                proxy_cache_methods_set=EnabledBoolValueBool(enabled=True, value=False),
                disable_proxy_forceRanges=EnabledBoolValueBool(enabled=True, value=True),
                static_request_headers=EnabledBoolValueDictStrStr(enabled=True, value={'foo': 'bar'}),
                custom_server_name=EnabledBool(enabled=False),
                ignore_cookie=EnabledBoolValueBool(enabled=True, value=True),
                secure_key=SecureKey(enabled=False, type='DISABLE_IP_SIGNING'),
            ),
            ssl_certificate = SSLCertificate(type='DONT_USE', status='READY'),
            id = resource_id,
            folder_id = folder_id,
            cname = cname,
            origin_group_id = origin_group_id,
            origin_protocol = 'HTTP'
        )

