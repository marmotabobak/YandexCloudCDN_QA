from model import CDNResource, SSLCertificate
from typing import Optional


def make_cdn_resource_ssl_certificate_attribute(ssl_type: str = None) -> SSLCertificate:
    #TODO: make different types
    if not ssl_type:
        return SSLCertificate(
            type='DONT_USE',
            status='READY'
        )

def make_default_cdn_resource(folder_id: str, cname: str, origin_group_id: str, ) -> CDNResource:
    return CDNResource(
        folder_id=folder_id,
        cname=cname,
        origin_group_id=origin_group_id,
        origin_protocol='HTTP'
    )

def make_json_from_object_with_correct_origin_group(cdn_resource: CDNResource) -> Optional[dict]:
    cdn_resource_dict = cdn_resource.model_dump(exclude_none=True, by_alias=True)
    if origin_group_id := cdn_resource_dict.get('originGroupId'):
        cdn_resource_dict['origin'] = {'originGroupId': origin_group_id}
        return cdn_resource_dict
    return None
