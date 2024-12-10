import json
import logging
from typing import Optional

import requests


#TODO: make singletone
class Authorization:
    def __init__(self, oauth: str, iam_token_url: str):
        self.oauth = oauth
        self.iam_token_url = iam_token_url
        self.token = self._get_iam_token()

    #TODO: getter?
    def get_token(self):
        return self.token

    def _get_iam_token(self) -> Optional[str]:
        payload = {'yandexPassportOauthToken': self.oauth}
        try:
            request = requests.post(url=self.iam_token_url, json=payload)

            if request.status_code != 200:
                ...  # log
                return None

            try:
                response_dict = request.json()
                if token := response_dict.get('iamToken', None):
                    return token
                else:
                    ...  # log
                    return None
            except json.JSONDecodeError as e:
                ...  # log
                return None

        except requests.exceptions.ConnectionError as e:
            logging.error(f'Connection error')
            logging.debug(f'error details: {e}')
            return None

