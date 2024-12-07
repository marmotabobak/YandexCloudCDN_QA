import json
import logging
import time
from functools import wraps
from typing import Optional, List, Callable, Any

import requests
from pydantic import BaseModel
from pydantic import ValidationError

from model import CDNResource


def repeat_and_sleep(times_to_repeat: int = 3, sleep_duration: int = 1):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            logging.info(f'Processing function [{func}] for [{times_to_repeat}] '
                         f'times with [{sleep_duration}] second(s) sleep...')
            for i in range(times_to_repeat):
                logging.info(f'Attempt #{i+1}...')
                res = func(*args, **kwargs)
                if res is not None:
                    return res
                logging.info(f'...failed. Sleeping for {sleep_duration} second(s)...')
                time.sleep(sleep_duration)
            else:
                logging.error(f'failed to successfully complete func [{func}]')
                return None
        return wrapper
    return decorator

class CDNResourceProcessorResponseError(BaseModel):
    code: int
    message: str

#TODO: use pydantic
class CDNResourcesProcessor:
    def __init__(self, api_url: str, folder_id: str, token: str):
        self.token = token
        self.api_url = api_url
        self.folder_id = folder_id

    def get_cdn_resources_ids(self) -> Optional[List[str]]:
        url = f'{self.api_url}/resources?folderId={self.folder_id}'
        headers = {'Authorization': f'Bearer {self.token}'}
        request = requests.get(url=url, headers=headers)

        if request.status_code != 200:
            ...  # log
            return None

        try:
            response_dict = request.json()
            if resources := response_dict.get('resources', None):
                return [resource['id'] for resource in resources]
            else:
                ...  # log
                return None
        except json.JSONDecodeError as e:
            ...  # log
            return None
        except KeyError as e:
            ...  # log
            return None
        except Exception as e:
            ...  # log
            return None

    def delete_cdn_resource(self, cdn_id: str) -> None:
        url = f'{self.api_url}/resources/{cdn_id}'
        headers = {'Authorization': f'Bearer {self.token}'}
        request = requests.delete(url=url, headers=headers)

        if request.status_code != 200:
            ...  # log

        logging.info(f'CDN Resource [{cdn_id}] deleted successfully')

    def delete_cdn_resources(self, ids: List[str]) -> None:
        for cdn_id in ids:
            self.delete_cdn_resource(cdn_id)

    def delete_all_cdn_resources(self) -> None:
        if (cdn_resources_list := self.get_cdn_resources_ids()) is not None:
            for cdn_id in cdn_resources_list:
                self.delete_cdn_resource(cdn_id=cdn_id)
        else:
            logging.info('Trying to delete all CDN Resources... none found to delete')

    def get_cdn_resource(self, cdn_id: str) -> Optional[CDNResource]:
        url = f'{self.api_url}/resources/{cdn_id}'
        headers = {'Authorization': f'Bearer {self.token}'}
        request = requests.get(url=url, headers=headers)
        try:
            return CDNResource.model_validate(request.json())
        except json.JSONDecodeError as e:
            logging.error(f'json decode error')
            logging.debug(f'error details: {e}')
            return None
        except ValidationError as e:
            logging.error(f'pydantic validation error')
            logging.debug(f'error details: {e}')
            return None
        except Exception as e:
            logging.error(f'unknown error')
            logging.debug(f'error details: {e}')
            return None
        finally:
            logging.debug(f'response text: {request.text}')

    @repeat_and_sleep(times_to_repeat=3, sleep_duration=1)
    def create_cdn_resource(self, cdn_resource: CDNResource) -> Optional[str]:
        url = f'{self.api_url}/resources/'
        headers = {'Authorization': f'Bearer {self.token}'}
        payload = {
            'folderId': cdn_resource.folder_id,
            'cname': cdn_resource.cname,
            'origin': {
                'originGroupId': cdn_resource.origin_group_id
            },
            'originProtocol': cdn_resource.origin_protocol
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
                    except Exception as e:
                        logging.debug('unknown error')
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
            except Exception as e:
                ...  # log
                return None
            finally:
                logging.debug(f'response text: {request.text}')
        elif response_status == 400:
            logging.error('bad request')
            logging.debug(request.text)
            return None

