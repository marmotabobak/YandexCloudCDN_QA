import requests
import json
from typing import Optional

#TODO: use pydantic
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
        except Exception as e:
            ...  # log
            return None