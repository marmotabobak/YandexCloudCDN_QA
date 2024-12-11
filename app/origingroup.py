import json
import logging
from typing import Optional, List, Dict, Iterator, Any

import requests
from pydantic import BaseModel, ValidationError

from app.model import CDNResource, SSLCertificate, CDNResourceOptions, EdgeCacheSettings, EnabledBoolValueDictStrStr, APIProcessorError
from app.apiprocessor import APIProcessor
from utils import make_random_8_symbols, make_query_string_from_args


class OriginGroupsAPIProcessor(APIProcessor):

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.query_args = {'folderId': self.folder_id}

    def create_item(self, item: CDNResource) -> Optional[str]:
        try:
            cdn_resource_dict = item.model_dump(exclude_none=True, by_alias=True)
        except ValidationError as e:
            logging.error('pydantic validation error')
            logging.debug(f'error details: {e}')
            return None

        if origin_group_id := cdn_resource_dict.get('originGroupId'):
            cdn_resource_dict['origin'] = {'originGroupId': origin_group_id}
            return super().create_item(item=cdn_resource_dict)
        else:
            logging.error('[originGroupId] attribute is absent at cdn_resource object')
            logging.debug(f'cdn_resource: {item}')
            return None