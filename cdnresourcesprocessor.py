import requests
import json
from typing import Optional, List
from model import CDNResource
from pydantic import ValidationError
import logging

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
        except KeyError as e:
            ...  # log
        except Exception as e:
            ...  # log

    def delete_cdn_resource(self, cdn_id: str) -> None:
        url = f'{self.api_url}/resources/{cdn_id}'
        headers = {'Authorization': f'Bearer {self.token}'}
        request = requests.delete(url=url, headers=headers)

        if request.status_code != 200:
            ...  # log

    def delete_cdn_resources(self, ids: List[str]) -> None:
        for cdn_id in ids:
            self.delete_cdn_resource(cdn_id)

    def delete_all_cdn_resources(self) -> None:
        if (cdn_resources_list := self.get_cdn_resources_ids()) is not None:
            for cdn_id in cdn_resources_list:
                self.delete_cdn_resource(cdn_id=cdn_id)

    def get_cdn_resource(self, cdn_id: str) -> CDNResource:
        url = f'{self.api_url}/resources/{cdn_id}'
        headers = {'Authorization': f'Bearer {self.token}'}
        request = requests.get(url=url, headers=headers)
        try:
            return CDNResource.model_validate(request.json())
        except json.JSONDecodeError as e:
            logging.error(f'cdn resource [{cdn_id}] json decode error')
            logging.debug(f'error details: {e}')
        except ValidationError as e:
            logging.error(f'cdn resource [{cdn_id}] validation error')
            logging.debug(f'error details: {e}')
        except Exception as e:
            logging.error(f'unknown error')
            logging.debug(f'error details: {e}')
        finally:
            logging.debug(f'response text: {request.text}')


    def create_cdn_resource(self) -> None:
        ...