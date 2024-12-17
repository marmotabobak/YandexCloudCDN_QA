from pydantic import BaseModel, ValidationError
from typing import List, Optional, Dict, Union
import requests
import json
from app.model import CDNResource, EntityName, APIEntity, APIProcessorError, OriginGroup
import logging
from utils import repeat_and_sleep, make_query_string_from_args


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

    def get_item_by_id(self, item_id: str) -> Optional[CDNResource]:

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

    @repeat_and_sleep(times_to_repeat=5, sleep_duration=1)
    def delete_item_by_id(self, item_id: str) -> Optional[bool]:
        url = f'{self.api_url}/{self.api_entity.value}/{item_id}'
        url += f'?{make_query_string_from_args(self.query_args)}' if self.query_args else ''

        headers = {'Authorization': f'Bearer {self.token}'}
        request = requests.delete(url=url, headers=headers)

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

            if error := response_dict.get('error'):
                error_code, error_message = error.get('code'), error.get('message')
                logging.error('internal error')
                logging.error(f'details: code [{error_code}], message [{error_message}]')
                return None

        except json.JSONDecodeError as e:
            logging.debug(f'JSONDecodeError, details: {e}')
            return None

        logging.info(f'item [{item_id}] deleted successfully')
        return True

    def delete_several_items_by_ids(self, items_ids_list: List[str]) -> bool:
        for item_id in items_ids_list:
            if not self.delete_item_by_id(item_id=item_id):
                return False
        return True

    def delete_all_items(self) -> bool:
        res = True
        if (items_ids_list := self.get_items_ids_list()) is not None:
            for item_id in items_ids_list:
                if not self.delete_item_by_id(item_id=item_id):
                    res = False
        else:
            logging.info(f'trying to delete all [{self.api_entity.value}] items... none found to be deleted')
        return res

    def make_dict_from_item(self, item: Union[CDNResource, OriginGroup]) -> Optional[dict]:
        try:
            return item.model_dump(exclude_none=True, by_alias=True)
        except ValidationError as e:
            logging.error('pydantic validation error')
            logging.debug(f'error details: {e}')
            return None

    @repeat_and_sleep(times_to_repeat=5, sleep_duration=1)
    def create_item(self, item: Union[CDNResource, OriginGroup]) -> Optional[str]:  # payload not object as need to prepare payload at specific class before

        if not (payload := self.make_dict_from_item(item)):
            logging.error('error while parsing item to payload')
            logging.debug(f'item dict: {item}')
            return None

        url = f'{self.api_url}/{self.api_entity.value}/'
        headers = {'Authorization': f'Bearer {self.token}'}
        request = requests.post(url=url, headers=headers, json=payload)

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
                    item.id = item_id
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
                logging.debug(f'request payload: {json.dumps(payload)}')
                logging.debug(f'response text: {request.text}')
        elif response_status == 400:
            logging.error('bad request')
            logging.debug(f'request payload: {json.dumps(payload)}')
            logging.debug(f'response text: {request.text}')
            return None

    def compare_item_to_existing(self, item: Union[CDNResource, OriginGroup]) -> bool:
        existing_item = self.get_item_by_id(item.id)
        return item == existing_item


