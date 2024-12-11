from dataclasses import Field

from pydantic import BaseModel, ValidationError
from typing import List, Optional, Dict, Union
import requests
import json
from enum import Enum
from app.model import CDNResource
import logging
from utils import repeat_and_sleep

class EntityName(Enum):
    CDN_RESOURCE = 'resource'
    ORIGIN_GROUP = 'originGroup'

class APIEntity(Enum):
    CDN_RESOURCE = 'resources'
    ORIGIN_GROUP = 'originGroups'


class APIProcessorError(BaseModel):
    code: Optional[int] = None
    message: str
    details: Optional[List[Dict[str, str]]] = None
    error: Optional[str] = None


class APIProcessor(BaseModel):
    entity_name: EntityName
    token: str
    api_url: str
    api_entity: APIEntity
    folder_id: str
    query_args: Optional[Dict[str, str]] = None

    def get_items_ids_list(self) -> Optional[List[str]]:
        url = f'{self.api_url}/{self.api_entity.value}?folderId={self.folder_id}'
        headers = {'Authorization': f'Bearer {self.token}'}
        request = requests.get(url=url, headers=headers)

        if request.status_code != 200:
            logging.error(f'status [{request.status_code}], response text [{request.text}]')
            return None

        try:
            response_dict = request.json()
            if 'code' in response_dict:
                error_code, error_message = response_dict.get('code'), response_dict.get('message')
                logging.error('internal error')
                logging.error(f'details: code [{error_code}], message [{error_message}]')
                return None

            if resources := response_dict.get(self.api_entity.value, None):
                logging.debug(f'response text: {request.text}')
                return [resource['id'] for resource in resources]
            else:
                logging.debug(f'no responses list found, response text: [{request.text}]')
                return None

        except json.JSONDecodeError as e:
            logging.debug(f'JSONDecodeError, details: {e}')
            return None
        # except KeyError as e:
        #     logging.debug(f'JSONDecodeError, details: {e}')
        #     return None

    def get_item(self, item_id: str) -> Optional[CDNResource]:

        if not item_id:
            logging.error(f'None or empty item_id: [{item_id}]')
            return None

        url = f'{self.api_url}/{self.api_entity.value}/{item_id}'
        if self.query_args:
            url += ''

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
        finally:
            logging.debug(f'response text: {request.text}')

    def delete_item(self, item_id: str) -> None:
        url = f'{self.api_url}/{self.api_entity.value}/{item_id}'
        if self.query_args:
            url += ''

        headers = {'Authorization': f'Bearer {self.token}'}
        request = requests.delete(url=url, headers=headers)

        if request.status_code != 200:
            logging.error(f'status [{request.status_code}], response text [{request.text}]')
            return None

        logging.info(f'item [{item_id}] deleted successfully')

    def delete_several_items(self, items_ids_list: List[str]) -> None:
        for item_id in items_ids_list:
            self.delete_item(item_id=item_id)

    def delete_all_items(self) -> None:
        if (items_ids_list := self.get_items_ids_list()) is not None:
            for item_id in items_ids_list:
                self.delete_item(item_id=item_id)
        else:
            logging.info('trying to delete all items... none found to be deleted')

    @repeat_and_sleep(times_to_repeat=3, sleep_duration=1)
    def create_item(self, item: Union[dict, CDNResource]) -> Optional[str]:  # payload not object as need to prepare payload at specific class before
        url = f'{self.api_url}/{self.api_entity.value}/'
        headers = {'Authorization': f'Bearer {self.token}'}
        request = requests.post(url=url, headers=headers, json=item)

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
                        return None
                    logging.error(f'API error: {error.message}, code {error.code}')
                    return None

                if item_id := response_dict.get('metadata', {}).get(self.entity_name.value+'Id'):
                    logging.info(f'{self.entity_name.value} [{item_id}] created successfully')
                    logging.debug(response_dict)
                    return item_id

            except json.JSONDecodeError as e:
                logging.error('JSONDecodeError')
                logging.debug(f'error details: {e}')
                return None
            # except KeyError as e:
            #     logging.error('No such key')
            #     logging.debug(f'error details: {e}')
            #     return None
            finally:
                logging.debug(f'request payload: {item}')
                logging.debug(f'response text: {request.text}')
        elif response_status == 400:
            logging.error('bad request')
            logging.debug(f'request payload: {item}')
            logging.debug(f'response text: {request.text}')
            return None
