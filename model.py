from pydantic import BaseModel, Field
from typing import Optional, Union, List
from datetime import datetime

class EnabledBool(BaseModel):
    enabled: bool

class EnabledBoolValueBool(BaseModel):
    enabled: bool
    value: bool

class EdgeCacheSettings(BaseModel):
    enabled: bool
    default_value: str = Field(..., alias='defaultValue')

class QueryParamsOptions(BaseModel):
    ignore_query_string: EnabledBoolValueBool = Field(..., alias='ignoreQueryString')

class CompressionOptions(BaseModel):
    gzip_on: EnabledBoolValueBool = Field(..., alias='gzipOn')

class RedirectOptions(BaseModel):
    redirect_http_to_https: Optional[EnabledBoolValueBool] = Field(alias='redirectHttpToHttps')

class Host(BaseModel):
    enabled: bool
    value: str

class HostOptions(BaseModel):
    host: Host

class Cors(BaseModel):
    enabled: bool
    value: List[str]

class AllowedHttpMethods(BaseModel):
    enabled: bool
    value: List[str]  #TODO: make enum

class Rewrite(BaseModel):
    enabled: bool
    body: str
    flag: str

class SecureKey(BaseModel):
    enabled: bool
    key: Optional[str]
    type: str

class IpAddressAcl(BaseModel):
    enabled: bool
    excepted_values: List[str] = Field(..., alias='exceptedValues')
    policy_type: str = Field(..., alias='policyType')

class SSLCertificate(BaseModel):
    type: str
    status: str

class Options(BaseModel):
    edge_cache_settings: EdgeCacheSettings = Field(..., alias='edgeCacheSettings')
    browser_cache_settings: EnabledBool = Field(..., alias='browserCacheSettings')
    query_params_options: Optional[QueryParamsOptions] = Field(None, alias='queryParamsOptions')
    slice: EnabledBoolValueBool
    compression_options: CompressionOptions = Field(..., alias='compressionOptions')
    redirect_options: Optional[RedirectOptions] = Field(None, alias='redirectOptions')
    host_options: Optional[HostOptions] = Field(None, alias='hostOptions')
    static_headers: EnabledBool = Field(..., alias='staticHeaders')
    cors: Optional[Cors]
    stale: EnabledBool
    allowed_http_methods: AllowedHttpMethods = Field(..., alias='allowedHttpMethods')
    proxy_cache_methods_set: EnabledBoolValueBool = Field(..., alias='proxyCacheMethodsSet')
    disable_proxy_forceRanges: EnabledBoolValueBool = Field(..., alias='disableProxyForceRanges')
    static_request_headers: EnabledBool = Field(..., alias='staticRequestHeaders')
    custom_server_name: EnabledBool = Field(..., alias='customServerName')
    ignore_cookie: EnabledBoolValueBool = Field(..., alias='ignoreCookie')
    rewrite: Optional[Rewrite]
    secure_key: SecureKey = Field(..., alias='secureKey')
    ip_address_acl: Optional[IpAddressAcl] = Field(None, alias='ipAddressAcl')

class CDNResource(BaseModel):
    active: bool
    options: Options
    secondary_hostnames: Optional[List[str]] = Field(..., alias='secondaryHostnames')
    ssl_certificate: SSLCertificate = Field(..., alias='sslCertificate')
    id: str
    folder_id: str = Field(..., alias='folderId')
    cname: str
    created_at: datetime = Field(..., alias='createdAt')
    updated_at: datetime = Field(..., alias='updatedAt')
    origin_group_id: str = Field(..., alias='originGroupId')
    origin_group_name: str = Field(..., alias='originGroupName')
    origin_protocol: str = Field(..., alias='originProtocol')

