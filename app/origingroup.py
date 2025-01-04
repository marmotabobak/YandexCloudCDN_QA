from typing import Any

from app.apiprocessor import APIProcessor


class OriginGroupsAPIProcessor(APIProcessor):

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.query_args = {'folderId': self.folder_id}