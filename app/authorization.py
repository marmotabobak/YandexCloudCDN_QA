import json
import logging
import os
from typing import Optional

import requests


#TODO: make singleton
class Authorization:
    def __init__(self, oauth: str, iam_token_url: str):
        self.oauth = oauth
        self.iam_token_url = iam_token_url
        self.token = self._get_iam_token()

    #TODO: getter?
    def get_token(self):
        return self.token

    def _get_iam_token(self) -> Optional[str]:
        logging.info('Getting iam token...')

        payload = {'yandexPassportOauthToken': self.oauth}
        logging.debug(f'Payload: {payload}')
        try:
            response = requests.post(url=self.iam_token_url, json=payload)
            logging.debug(f'Response: {response.text}')

            if response.status_code != 200:
                logging.error(f'...FAIL. Status code: {response.status_code}')
                return None

            try:
                response_dict = response.json()
                if token := response_dict.get('iamToken', None):
                    return token
                else:
                    logging.error('...FAIL. iamToken key not found in response.')
                    return None
            except json.JSONDecodeError as e:
                logging.error(f'...FAIL. Error while parsing response as JSON. Error details: {e}')
                return None

        except requests.exceptions.ConnectionError as e:
            logging.error(f'Connection error')
            logging.debug(f'error details: {e}')
            return None