from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict

from pydantic import BaseModel, Field, ConfigDict


class EntityName(Enum):
    CDN_RESOURCE = 'resource'
    ORIGIN_GROUP = 'originGroup'

class APIEntity(Enum):
    CDN_RESOURCE = 'resources'
    ORIGIN_GROUP = 'originGroups'


class APIProcessorError(BaseModel):
    code: Optional[int] = Field(None)
    message: str
    details: Optional[List[Dict[str, str]]] = Field(None)
    error: Optional[str] = Field(None)


class BaseModelWithAliases(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

class EnabledBool(BaseModelWithAliases):
    enabled: bool

class EnabledBoolValueBool(BaseModelWithAliases):
    enabled: bool
    value: bool

class EnabledBoolValueDictStrStr(BaseModelWithAliases):
    enabled: bool
    value: Optional[Dict[str, str]] = Field(None)

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
    enabled: Optional[bool] = Field(None)
    value: Optional[List[str]] = Field(None)

class AllowedHttpMethods(BaseModelWithAliases):
    enabled: bool
    value: List[str]  #TODO: make enum

class Rewrite(BaseModelWithAliases):
    enabled: bool
    body: Optional[str] = Field(None)
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
    static_request_headers: Optional[EnabledBoolValueDictStrStr] = Field(None, alias='staticRequestHeaders')
    custom_server_name: Optional[EnabledBool] = Field(None, alias='customServerName')
    ignore_cookie: Optional[EnabledBoolValueBool] = Field(None, alias='ignoreCookie')
    rewrite: Optional[Rewrite] = Field(None)
    secure_key: Optional[SecureKey] = Field(None, alias='secureKey')
    ip_address_acl: Optional[IpAddressAcl] = Field(None, alias='ipAddressAcl')

    def __eq__(self, other: CDNResourceOptions) -> bool:

        self_dict = self.model_dump()
        other_dict = other.model_dump()

        if (not self.edge_cache_settings or not self.edge_cache_settings.enabled) and (not other.edge_cache_settings or not other.edge_cache_settings.enabled):
            self_dict.pop('edge_cache_settings', None)
            other_dict.pop('edge_cache_settings', None)

        if (not self.rewrite or not self.rewrite.enabled) and (not other.rewrite or not other.rewrite.enabled):
            self_dict.pop('rewrite', None)
            other_dict.pop('rewrite', None)

        if (not self.ip_address_acl or not self.ip_address_acl.enabled) and (not other.ip_address_acl or not other.ip_address_acl.enabled):
            self_dict.pop('ip_address_acl', None)
            other_dict.pop('ip_address_acl', None)

        if (not self.query_params_options or not self.query_params_options.ignore_query_string.value) and (not other.query_params_options or not other.query_params_options.ignore_query_string.value):
            self_dict.pop('query_params_options', None)
            other_dict.pop('query_params_options', None)

        for option_name, option_value in self_dict.items():
            other_option_value = other_dict[option_name]
            if option_value != other_option_value:
                logging.debug(f'{option_name} is not equal: self=[{option_value}], other =[{other_option_value}]')
                # TODO: DEBUG - delete
                print(f'{option_name} is not equal: self=[{option_value}], other =[{other_option_value}]')
                return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

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

    def __eq__(self, other: CDNResource, not_to_compare: set = None) -> bool:

        not_to_compare = {'created_at', 'updated_at', 'origin_group_name', 'options'} if not_to_compare is None else {}

        if self.options != other.options:
            return False

        self_dict = self.model_dump(exclude=not_to_compare)
        other_dict = other.model_dump(exclude=not_to_compare)
        return self_dict == other_dict

    def __ne__(self, other):
        return not self.__eq__(other)

class OriginMetaCommon(BaseModelWithAliases):
    name: str

class OriginMeta(BaseModelWithAliases):
    common: OriginMetaCommon

class Origin(BaseModelWithAliases):
    source: str
    enabled: Optional[bool] = Field(None)
    id: Optional[str] = Field(None)
    origin_group_id: Optional[str] = Field(None, alias='originGroupId')
    backup: Optional[bool] = Field(None)
    meta: Optional[OriginMeta] = Field(None)

# TODO: make origins and oeigin groups comparable (__eq()__ and __ne()__)
class OriginGroup(BaseModelWithAliases):
    use_next: Optional[bool] = Field(None, alias='useNext')
    origins: List[Origin]
    id: Optional[str] = Field(None)
    folder_id: str = Field(..., alias='folderId')
    name: str

