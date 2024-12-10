from datetime import datetime
from typing import Optional, List, Dict

from pydantic import BaseModel, Field


class APIProcessor(BaseModel):
    token: str
    api_url: str
    folder_id: str

class BaseModelWithAliases(BaseModel):
    class Config:
        populate_by_name = True

class EnabledBool(BaseModelWithAliases):
    enabled: bool

class EnabledBoolValueBool(BaseModelWithAliases):
    enabled: bool
    value: bool

class EnabledBoolValueDictStrStr(BaseModelWithAliases):
    enabled: bool
    value: Dict[str, str]

class EdgeCacheSettings(BaseModelWithAliases):
    enabled: bool
    default_value: str = Field(..., alias='defaultValue')

class QueryParamsOptions(BaseModelWithAliases):
    ignore_query_string: EnabledBoolValueBool = Field(..., alias='ignoreQueryString')

class CompressionOptions(BaseModelWithAliases):
    gzip_on: EnabledBoolValueBool = Field(..., alias='gzipOn')

class RedirectOptions(BaseModelWithAliases):
    redirect_http_to_https: Optional[EnabledBoolValueBool] = Field(alias='redirectHttpToHttps')

class Host(BaseModelWithAliases):
    enabled: bool
    value: str

class HostOptions(BaseModelWithAliases):
    host: Optional[Host] = Field(None)
    forward_host_header: Optional[EnabledBoolValueBool] = Field(None, alias='forwardHostHeader')

class Cors(BaseModelWithAliases):
    enabled: bool
    value: List[str]

class AllowedHttpMethods(BaseModelWithAliases):
    enabled: bool
    value: List[str]  #TODO: make enum

class Rewrite(BaseModelWithAliases):
    enabled: bool
    body: str
    flag: str

class SecureKey(BaseModelWithAliases):
    enabled: bool
    key: Optional[str] = Field(None)
    type: str

class IpAddressAcl(BaseModelWithAliases):
    enabled: bool
    excepted_values: List[str] = Field(..., alias='exceptedValues')
    policy_type: str = Field(..., alias='policyType')

class SSLCertificate(BaseModelWithAliases):
    type: str
    status: str

class CDNResourceOptions(BaseModelWithAliases):
    edge_cache_settings: Optional[EdgeCacheSettings] = Field(None, alias='edgeCacheSettings')
    browser_cache_settings: Optional[EnabledBool] = Field(None, alias='browserCacheSettings')
    query_params_options: Optional[QueryParamsOptions] = Field(None, alias='queryParamsOptions')
    slice: Optional[EnabledBoolValueBool] = Field(None)
    compression_options: Optional[CompressionOptions] = Field(None, alias='compressionOptions')
    redirect_options: Optional[RedirectOptions] = Field(None, alias='redirectOptions')
    host_options: Optional[HostOptions] = Field(None, alias='hostOptions')
    static_headers: Optional[EnabledBoolValueDictStrStr] = Field(None, alias='staticHeaders')
    cors: Optional[Cors] = Field(None)
    stale: Optional[EnabledBool] = Field(None)
    allowed_http_methods: Optional[AllowedHttpMethods] = Field(None, alias='allowedHttpMethods')
    proxy_cache_methods_set: Optional[EnabledBoolValueBool] = Field(None, alias='proxyCacheMethodsSet')
    disable_proxy_forceRanges: Optional[EnabledBoolValueBool] = Field(None, alias='disableProxyForceRanges')
    static_request_headers: Optional[EnabledBool] = Field(None, alias='staticRequestHeaders')
    custom_server_name: Optional[EnabledBool] = Field(None, alias='customServerName')
    ignore_cookie: Optional[EnabledBoolValueBool] = Field(None, alias='ignoreCookie')
    rewrite: Optional[Rewrite] = Field(None)
    secure_key: Optional[SecureKey] = Field(None, alias='secureKey')
    ip_address_acl: Optional[IpAddressAcl] = Field(None, alias='ipAddressAcl')

class CDNResource(BaseModelWithAliases):
    active: Optional[bool] = Field(None)
    options: Optional[CDNResourceOptions] = Field(None)
    secondary_hostnames: Optional[List[str]] = Field(None, alias='secondaryHostnames')
    ssl_certificate: Optional[SSLCertificate] = Field(None, alias='sslCertificate')
    id: Optional[str] = Field(None)
    folder_id: str = Field(..., alias='folderId')
    cname: str
    created_at: Optional[datetime] = Field(None, alias='createdAt')
    updated_at: Optional[datetime] = Field(None, alias='updatedAt')
    origin_group_id: str = Field(..., alias='originGroupId')
    origin_group_name: Optional[str] = Field(None, alias='originGroupName')
    origin_protocol: str = Field(..., alias='originProtocol')

