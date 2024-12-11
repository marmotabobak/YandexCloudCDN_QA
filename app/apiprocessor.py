from pydantic import BaseModel
from typing import List, Optional
import requests
import json
from enum import Enum

class APIEntity(Enum):
    CDN_RESOURCE = 'resources'
    ORIGIN_GROUP = 'originGroups'

class APIProcessor(BaseModel):
    token: str
    api_url: str
    api_entity: APIEntity
    folder_id: str

    def get_items_list(self) -> Optional[List[str]]:
        url = f'{self.api_url}/{self.api_entity}/?folderId={self.folder_id}'
        headers = {'Authorization': f'Bearer {self.token}'}
        request = requests.get(url=url, headers=headers)

        if request.status_code != 200:
            ...  # log
            return None

        try:
            response_dict = request.json()
            if resources := response_dict.get(self.api_entity, None):
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