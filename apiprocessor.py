#TODO: use pydantic
class APIProcessor:
    def __init__(self, api_url: str, folder_id: str, token: str):
        self.token = token
        self.api_url = api_url
        self.folder_id = folder_id