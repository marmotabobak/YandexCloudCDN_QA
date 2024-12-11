import json
import logging
from typing import Optional, List, Dict, Iterator, Any

import requests
from pydantic import BaseModel, ValidationError

from app.model import CDNResource, SSLCertificate, CDNResourceOptions, EdgeCacheSettings, EnabledBoolValueDictStrStr, APIProcessorError, OriginGroup
from app.apiprocessor import APIProcessor
from utils import make_random_8_symbols, make_query_string_from_args


class OriginGroupsAPIProcessor(APIProcessor):

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.query_args = {'folderId': self.folder_id}