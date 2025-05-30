from collections import namedtuple
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class YandexCloudAPI(BaseModel):
    iam_token_url: str = Field(..., description='Yandex Cloud url to get iam token')
    api_url: str = Field(..., description='Yandex Cloud API url')

class SetupInitializeResourcesCheck(BaseModel):
    total_duration_seconds: int = Field(..., description='Period of time of the check to be successfully completed')
    sleep_duration_between_attempts: int = Field(..., description='Sleep duration between successful attempts '
                                                                  'inside of total period of time. '
                                                                  'Used not to DDoS during overall check.')
class TTLSettings(BaseModel):
    short_ttl: int = Field(..., description='Edge cache "fast" ttl to check edge revalidates')
    long_ttl: int = Field(..., description='Edge cache "long" ttl to check edge does not revalidate')
    error_rate: float = Field(..., description='Acceptable margin of error to calculate TTL revalidation period')

class RequestsType(str, Enum):
    random = 'random'
    targeted = 'targeted'

class EdgeCurlSettings(BaseModel):
    periods_to_test: int = Field(..., description='Number of attempts to curl edges for testing')
    finish_once_success: bool = Field(..., description='Successfully stop test if any of edges successfully passed')
    requests_type: RequestsType

class DefaultProtocol(str, Enum):
    http = 'http'
    https = 'https'

class ClientHeadersSettings(BaseModel):
    use_random_headers: bool = Field(..., description='Flag to use randomly generated client headers')
    custom_header_value: str = Field(..., description='Default client headers value if not randomly generated')

class ResourcesInitializeMethod(str, Enum):
    use_existing = 'use_existing'  # Use existing resources for tests
    update_existing = 'update_existing'  # Use existing but update them first
    from_scratch = 'from_scratch'  # Clean existing and create new resources for tests

class ApiTestParameters(BaseModel):
    setup_initialize_resources_check: SetupInitializeResourcesCheck = Field(..., description='')
    ttl_settings: TTLSettings = Field(..., description='Edge cache ttl to check if edge revalidates')
    edge_curl_settings: EdgeCurlSettings = Field(..., description='')
    default_protocol: DefaultProtocol = Field(..., description='Default (http/https) protocol to use')
    client_headers_settings: ClientHeadersSettings = Field(..., description='Settings for client headers')
    resources_initialize_method: str = Field(..., description='')

class Origin(BaseModel):
    origin_group_id: Optional[str] = Field(None, description='')
    domain: str = Field(..., description='')

class CDNResource(BaseModel):
    id: Optional[str] = Field(None, description='')
    cname: str = Field(..., description='')

class EdgeCacheHost(BaseModel):
    url: Optional[str] = Field(None, description='')
    ip_address: str = Field(..., description='')

class Resources(BaseModel):
    folder_id: str = Field(..., description='')
    origin_group_name: Optional[str] = Field(None, description='')
    origin: Origin = Field(..., description='')
    cdn_resources: List[CDNResource] = Field(..., description='')
    edge_cache_hosts: Optional[List[EdgeCacheHost]] = Field(None, description='')

class Config(BaseModel):
    yandex_cloud_api: YandexCloudAPI = Field(..., description='')
    api_test_parameters: ApiTestParameters = Field(..., description='')
    resources: Resources = Field(..., description='')

class EdgeResponseHeaders(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cache_host: str = Field(..., alias='Cache-Host')
    cache_status: Optional[str] = Field(None, alias='Cache-Status')
    param_to_test: Optional[str] = Field(None, alias='param-to-test')

HostResponse = namedtuple('HostResponse', 'time, status')

class CheckType(str, Enum):
    CNAME_404 = 'cnames are 404'
    RESOURCE_EQUAL = 'resources are equal to existing'
