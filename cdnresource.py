from model import CDNResource, SSLCertificate


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