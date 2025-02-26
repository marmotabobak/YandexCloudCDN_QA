import json
import logging
from typing import List, Optional, Dict, Union

import requests
from pydantic import BaseModel, ValidationError, Field

from app.model import CDNResource, ItemType, APIFolder, APIProcessorError, OriginGroup
from app.utils import repeat_and_sleep, make_query_string_from_args


class APIProcessor(BaseModel):
    """ Processing Yandex Cloud entities management via Yandex Cloud API
    """

    item_type: ItemType = Field(..., description='Type of items to be processed: origin, cdn resource')
    api_endpoint: APIFolder = Field(..., description='Yandex Cloud API endpoint: equals to plural entity_name')
    api_endpoint_query_args: Optional[Dict[str, str]] = Field(
        None, description='Yandex Cloud API endpoint query arguments (in case they are needed to specify the request)'
    )
    api_token: str = Field(..., description='Yandex Cloud API iam-token')
    api_url: str = Field(..., description='Yandex Cloud API url')
    folder_id: str = Field(..., description='Yandex Cloud folder id')

    def get_items_ids_list(self) -> Optional[List[str]]:
        """ Returns the list of all existing items in the folder
        """

        url = f'{self.api_url}/{self.api_endpoint.value}?folderId={self.folder_id}'
        headers = {'Authorization': f'Bearer {self.api_token}'}
        response = requests.get(url=url, headers=headers)
        logging.debug(f'Request: url [{url}], headers[{response.request.headers}]')  # TODO: how to put this to decorator - how to pass request to it?

        if response.status_code != 200:
            logging.error(f'status [{response.status_code}], response text [{response.text}]')
            return None

        try:
            response_dict = response.json()
            if error_code := response_dict.get('code') :
                error_message = response_dict.get('message')
                logging.error(f'internal error: details: code [{error_code}], message [{error_message}]')
                return None

            if resources := response_dict.get(self.api_endpoint.value, None):
                return [resource['id'] for resource in resources]

        except json.JSONDecodeError as e:  # TODO: how to get this to common decorator but use finally anyway?
            logging.debug(f'JSONDecodeError, details: {e}')
            return None

        finally:
            logging.debug(f'response text: {response.text}')  # TODO: how to put this to decorator - how to pass response.text to it?

    @repeat_and_sleep(times_to_repeat=5, sleep_duration=1)
    def delete_item_by_id(self, item_id: str) -> Optional[bool]:
        """ Delete specific item by its id
        """

        logging.info(f'Deleting [{item_id}] {self.api_endpoint.value}...')
        if not item_id:
            logging.error('...item_id is absent')
            return None

        url = f'{self.api_url}/{self.api_endpoint.value}/{item_id}'
        url += f'?{make_query_string_from_args(self.api_endpoint_query_args)}' if self.api_endpoint_query_args else ''

        headers = {'Authorization': f'Bearer {self.api_token}'}
        response = requests.delete(url=url, headers=headers)
        logging.debug(f'Request URL and headers: {response.request.url}, {response.request.headers}')
        logging.debug(f'Response text: {response.text}')

        if response.status_code != 200:
            logging.error(f'Status [{response.status_code}]')
            return None

        try:
            response_dict = response.json()

            # TODO: research tso blocks below - seem strange. if not strange then comment why =)
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
        finally:
            logging.debug(f'response text: {response.text}')

        logging.info(f'...OK')
        return True

    def delete_several_items_by_ids(self, items_ids_list: List[str]) -> bool:
        """ Delete the list of items
        """

        logging.info(f'Deleting [{items_ids_list}] {self.item_type}s...')
        if not items_ids_list:
            logging.error('...list is absent')
            return False

        for item_id in items_ids_list:
            if not self.delete_item_by_id(item_id=item_id):
                return False
        return True

    def delete_all_items(self) -> bool:
        """ Delete all items in the folder
        """

        logging.info(f'Deleting all [{self.item_type.value}]s...')
        res = True

        if (items_ids_list := self.get_items_ids_list()) is not None:
            for item_id in items_ids_list:
                if not self.delete_item_by_id(item_id=item_id):
                    res = False
        else:
            logging.info('...none found to be deleted')
        return res

    def make_dict_from_item(self, item: Union[CDNResource, OriginGroup]) -> Optional[dict]:
        """ Return dictionary made from item object
        """

        try:
            return item.model_dump(exclude_none=True, by_alias=True)
        except ValidationError as e:
            logging.error('pydantic validation error')
            logging.debug(f'error details: {e}')
            return None

    @repeat_and_sleep(times_to_repeat=5, sleep_duration=1)
    def create_item(self, item: Union[CDNResource, OriginGroup]) -> Optional[str]:
        """ Create item
        """

        logging.info(f'Creating {self.item_type}...')

        if not (payload := self.make_dict_from_item(item)):
            logging.error('error while parsing item to payload')
            logging.debug(f'item dict: {item}')
            return None

        url = f'{self.api_url}/{self.api_endpoint.value}/'
        headers = {'Authorization': f'Bearer {self.api_token}'}
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

                if item_id := response_dict.get('metadata', {}).get(self.item_type.value + 'Id'):
                    item.id = item_id
                    logging.info(f'{self.item_type.value} [{item_id}] created successfully')
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
        else:
            ...  # TODO: ?


