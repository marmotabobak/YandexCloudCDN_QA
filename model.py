from pydantic import BaseModel, Field
from typing import Optional, Union, List
from datetime import datetime

class Enabled(BaseModel):
    enabled: bool

class EnabledValue(BaseModel):
    enabled: bool
    value: bool

class SSLCertificate(BaseModel):
    type: str
    status: str

class EdgeCacheSettings(BaseModel):
    enabled: bool
    default_value: str = Field(..., alias='defaultValue')

class QueryParamsOptions(BaseModel):
    ignore_query_string: EnabledValue = Field(..., alias='ignoreQueryString')

class CompressionOptions(BaseModel):
    gzip_on: EnabledValue = Field(..., alias='gzipOn')

class AllowedHttpMethods(BaseModel):
    enabled: bool
    value: List[str]  #TODO: make enum

class SecureKey(BaseModel):
    enabled: bool
    type: str

class Options(BaseModel):
    edge_cache_settings: EdgeCacheSettings = Field(..., alias='edgeCacheSettings')
    browser_cache_settings: Enabled = Field(..., alias='browserCacheSettings')
    query_params_options: QueryParamsOptions = Field(..., alias='queryParamsOptions')
    slice: EnabledValue
    compression_options: CompressionOptions = Field(..., alias='compressionOptions')
    static_headers: Enabled = Field(..., alias='staticHeaders')
    stale: Enabled
    allowed_http_methods: AllowedHttpMethods = Field(..., alias='allowedHttpMethods')
    proxy_cache_methodsSet: EnabledValue = Field(..., alias='proxyCacheMethodsSet')
    disable_proxy_forceRanges: EnabledValue = Field(..., alias='disableProxyForceRanges')
    static_request_headers: Enabled = Field(..., alias='staticRequestHeaders')
    custom_server_name: Enabled = Field(..., alias='customServerName')
    ignore_cookie: EnabledValue = Field(..., alias='ignoreCookie')
    secure_key: SecureKey = Field(..., alias='secureKey')

class CDNResource(BaseModel):
    id: str
    folder_id: str = Field(..., alias='folderId')
    cname: str
    created_at: datetime = Field(..., alias='createdAt')
    updated_at: datetime = Field(..., alias='updatedAt')
    origin_group_id: str = Field(..., alias='originGroupId')
    origin_group_name: str = Field(..., alias='originGroupName')
    origin_protocol: str = Field(..., alias='originProtocol')
    active: bool
    ssl_certificate: SSLCertificate = Field(..., alias='sslCertificate')
    options: Options

