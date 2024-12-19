import logging
import os
import time
import json
import requests
from utils import ping, http_get_request_through_ip_address


from app.authorization import Authorization
from app.resource import ResourcesAPIProcessor
from app.origingroup import OriginGroupsAPIProcessor
from app.apiprocessor import EntityName, APIEntity
from app.model import OriginGroup, Origin, OriginMeta, OriginMetaCommon, IpAddressAcl, CDNResource

#TODO: get logging level from cli args
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
logging.info('Starting service')


def main():
    OAUTH = os.environ['OAUTH']
    IAM_TOKEN_URL = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'

    API_URL = 'https://cdn.api.cloud.yandex.net/cdn/v1'
    FOLDER_ID = 'b1gjifkk80hojm6nv42n'
    ORIGIN_GROUP_ID='5867945351699784427'
    EXISTING_RESOURCES_IDS = [
        'cdnroq3y4e74osnivr7e', 'cdnrcblizmcdlwnddrko', 'cdnrqvhjv4tyhbfwimw3', 'cdnr5t2qvpsnaaglie2c',
        'cdnrpnabfdp7u6drjaua', 'cdnr7bbwrxhguo63wkpl', 'cdnrrausbqmlmhzq6ffp', 'cdnrfvuvfped42dkmyrv',
        'cdnrcqdphowdoxyxrufs', 'cdnrxcdi4xlyuwp42xfl'
    ]

    authorization = Authorization(oauth=OAUTH, iam_token_url=IAM_TOKEN_URL)
    token = authorization.get_token()
    print(token)

    # resources_processor = ResourcesAPIProcessor(
    #     entity_name=EntityName.CDN_RESOURCE,
    #     api_url=API_URL,
    #     api_entity=APIEntity.CDN_RESOURCE,
    #     folder_id=FOLDER_ID,
    #     token=token
    # )
    #
    # resource = resources_processor.make_default_cdn_resource(
    #     resource_id='cdnrxcdi4xlyuwp42xfl',
    #     folder_id=FOLDER_ID,
    #     cname=f'yccdn-qa-10.marmota-bobak.ru',
    #     origin_group_id=ORIGIN_GROUP_ID,
    # )
    #
    # resource.options.ip_address_acl = IpAddressAcl(
    #     enabled=False,
    #     excepted_values=['0.0.0.0/32', ],
    #     policy_type='POLICY_TYPE_ALLOW'
    # )
    # resource.options.edge_cache_settings.enabled = False
    #
    #
    # # resources_processor.update(resource)
    # #
    # if resources_processor.compare_item_to_existing(resource):
    #     print('!!!OK!!!')
    # else:
    #     print('=( FAIL =(')
    #

    EDGE_CACHE_HOSTS = {
        'm9-srv01.yccdn.cloud.yandex.net',
        'm9-srv02.yccdn.cloud.yandex.net',
        'm9-srv03.yccdn.cloud.yandex.net',
        'm9-srv04.yccdn.cloud.yandex.net',
        'm9-srv05.yccdn.cloud.yandex.net',
        'mar-srv01.yccdn.cloud.yandex.net',
        'mar-srv02.yccdn.cloud.yandex.net',
        'mar-srv03.yccdn.cloud.yandex.net',
        'mar-srv04.yccdn.cloud.yandex.net',
        'mar-srv05.yccdn.cloud.yandex.net',
    }

    import re

    def extract_ip_addresses(text):
        # Регулярное выражение для поиска IPv4 адресов
        ipv4_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'

        # Найти все IPv4 адреса в тексте
        ip_addresses = re.findall(ipv4_pattern, text)

        return ip_addresses

    text = """
    Здесь может быть любой текст, содержащий IP-адреса,
    например, вот такие: 192.168.1.1, 10.0.0.1, а также невалидные 256.256.256.256
    """
    ip_addresses = extract_ip_addresses(text)

    res = {}

    print("Найденные IP-адреса:", ip_addresses)
    for host in EDGE_CACHE_HOSTS:
        res[host] = extract_ip_addresses(str(ping(host).stdout))[0]

    print(res)

from collections import namedtuple

if __name__ == '__main__':

    HostResponse = namedtuple('HostResponse', 'time, status')

    resources_statuses = {'cdnrcblizmcdlwnddrko': {
        'm9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734607653.3567202, status='REVALIDATED'),
                                            HostResponse(time=1734607653.81166, status='REVALIDATED'),
                                            HostResponse(time=1734607666.778333, status='HIT')],
        'm9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734607654.87186, status='REVALIDATED'),
                                            HostResponse(time=1734607656.422912, status='HIT'),
                                            HostResponse(time=1734607657.882797, status='HIT')],
        'm9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734607659.3911839, status='REVALIDATED'),
                                            HostResponse(time=1734607668.237928, status='HIT')],
        'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734607665.276594, status='REVALIDATED'),
                                            HostResponse(time=1734607669.75223, status='HIT')]},
     'cdnr5t2qvpsnaaglie2c': {
         'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734607651.41418, status='REVALIDATED'),
                                             HostResponse(time=1734607665.481198, status='REVALIDATED')],
         'm9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734607653.557069, status='REVALIDATED'),
                                             HostResponse(time=1734607655.0628, status='HIT'),
                                             HostResponse(time=1734607661.047679, status='HIT'),
                                             HostResponse(time=1734607662.532598, status='HIT'),
                                             HostResponse(time=1734607664.0157099, status='REVALIDATED')],
         'm9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734607656.624649, status='REVALIDATED')],
         'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734607658.084886, status='REVALIDATED'),
                                             HostResponse(time=1734607659.580658, status='HIT'),
                                             HostResponse(time=1734607666.968261, status='HIT')],
         'm9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734607668.440819, status='REVALIDATED'),
                                             HostResponse(time=1734607669.948155, status='HIT')]},
     'cdnrpnabfdp7u6drjaua': {
         'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734607651.75037, status='REVALIDATED')],
         'm9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734607653.761121, status='REVALIDATED'),
                                             HostResponse(time=1734607667.1684291, status='REVALIDATED'),
                                             HostResponse(time=1734607668.635177, status='HIT')],
         'm9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734607655.2657878, status='REVALIDATED'),
                                             HostResponse(time=1734607656.81601, status='HIT')],
         'm9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734607658.285589, status='REVALIDATED'),
                                             HostResponse(time=1734607670.152386, status='REVALIDATED')],
         'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734607659.7817442, status='REVALIDATED'),
                                             HostResponse(time=1734607661.238715, status='HIT'),
                                             HostResponse(time=1734607662.722004, status='HIT'),
                                             HostResponse(time=1734607664.207475, status='HIT'),
                                             HostResponse(time=1734607665.673443, status='HIT')]},
     'cdnr7bbwrxhguo63wkpl': {
         'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734607652.059811, status='REVALIDATED')],
         'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734607653.963779, status='REVALIDATED'),
                                             HostResponse(time=1734607661.42964, status='HIT'),
                                             HostResponse(time=1734607662.91133, status='HIT'),
                                             HostResponse(time=1734607665.913888, status='REVALIDATED')],
         'm9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734607655.464503, status='REVALIDATED'),
                                             HostResponse(time=1734607668.84319, status='REVALIDATED'),
                                             HostResponse(time=1734607670.361404, status='HIT')],
         'm9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734607657.019401, status='REVALIDATED'),
                                             HostResponse(time=1734607659.971966, status='HIT'),
                                             HostResponse(time=1734607664.39823, status='HIT'),
                                             HostResponse(time=1734607667.358999, status='HIT')],
         'm9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734607658.4876878, status='REVALIDATED')]},
     'cdnrrausbqmlmhzq6ffp': {
         'm9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734607652.386179, status='REVALIDATED'),
                                             HostResponse(time=1734607654.1551502, status='HIT'),
                                             HostResponse(time=1734607657.209794, status='HIT')],
         'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734607655.6651158, status='REVALIDATED'),
                                             HostResponse(time=1734607667.557775, status='REVALIDATED')],
         'm9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734607658.692925, status='REVALIDATED'),
                                             HostResponse(time=1734607670.572149, status='REVALIDATED')],
         'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734607660.172931, status='REVALIDATED'),
                                             HostResponse(time=1734607663.1000772, status='HIT'),
                                             HostResponse(time=1734607664.589509, status='HIT'),
                                             HostResponse(time=1734607666.104325, status='HIT')],
         'm9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734607661.6332219, status='REVALIDATED'),
                                             HostResponse(time=1734607669.036971, status='HIT')]},
     'cdnrfvuvfped42dkmyrv': {
         'm9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734607652.724385, status='REVALIDATED'),
                                             HostResponse(time=1734607654.3456562, status='HIT'),
                                             HostResponse(time=1734607663.3033679, status='REVALIDATED'),
                                             HostResponse(time=1734607664.7791371, status='HIT'),
                                             HostResponse(time=1734607667.7487931, status='HIT'),
                                             HostResponse(time=1734607670.783301, status='HIT')],
         'm9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734607655.9349911, status='REVALIDATED'),
                                             HostResponse(time=1734607657.400393, status='HIT')],
         'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734607658.894423, status='REVALIDATED')],
         'm9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734607660.374252, status='REVALIDATED'),
                                             HostResponse(time=1734607669.233088, status='HIT')],
         'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734607661.83552, status='REVALIDATED'),
                                             HostResponse(time=1734607666.293695, status='HIT')]},
     'cdnrcqdphowdoxyxrufs': {
         'm9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734607653.050347, status='REVALIDATED'),
                                             HostResponse(time=1734607660.5650592, status='HIT')],
         'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734607654.550314, status='REVALIDATED'),
                                             HostResponse(time=1734607656.126506, status='HIT'),
                                             HostResponse(time=1734607657.5891578, status='HIT'),
                                             HostResponse(time=1734607659.084857, status='HIT')],
         'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734607662.035869, status='REVALIDATED'),
                                             HostResponse(time=1734607664.967901, status='HIT'),
                                             HostResponse(time=1734607666.484892, status='HIT'),
                                             HostResponse(time=1734607667.9410172, status='HIT')],
         'm9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734607663.506625, status='REVALIDATED'),
                                             HostResponse(time=1734607669.4491022, status='HIT'),
                                             HostResponse(time=1734607670.981534, status='HIT')]}}

    def foo(responses):
        last_revalidated_or_miss = None
        response_time = None

        for host_response in responses:
            if host_response.status in ('REVALIDATED', 'MISS'):
                if last_revalidated_or_miss:
                    # TODO: Check no the time of response received but response prepared by host? (Header 'Date:...')
                    response_time = host_response.time - last_revalidated_or_miss
                    return response_time > 9
                last_revalidated_or_miss = host_response.time

        if not last_revalidated_or_miss:
            return False

        return True if response_time else False


    from copy import deepcopy

    copy = {'cdnrcblizmcdlwnddrko': {'m9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734609973.8023438, status='REVALIDATED'), HostResponse(time=1734609975.4861271, status='HIT'), HostResponse(time=1734609992.5025349, status='REVALIDATED')], 'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734609977.1633222, status='REVALIDATED'), HostResponse(time=1734609991.089825, status='REVALIDATED')], 'm9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734609978.547582, status='REVALIDATED'), HostResponse(time=1734609981.264586, status='HIT'), HostResponse(time=1734609985.42264, status='HIT'), HostResponse(time=1734609988.3533802, status='HIT')], 'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734609979.919399, status='REVALIDATED'), HostResponse(time=1734609982.655073, status='HIT'), HostResponse(time=1734609986.876336, status='HIT'), HostResponse(time=1734609989.7206159, status='HIT')], 'm9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734609984.042739, status='REVALIDATED')]}, 'cdnr5t2qvpsnaaglie2c': {'m9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734609974.126483, status='REVALIDATED'), HostResponse(time=1734609978.739198, status='HIT'), HostResponse(time=1734609980.111427, status='HIT'), HostResponse(time=1734609992.705832, status='REVALIDATED')], 'm9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734609975.7002182, status='REVALIDATED'), HostResponse(time=1734609977.351656, status='HIT')], 'm9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734609981.46276, status='REVALIDATED'), HostResponse(time=1734609987.06851, status='HIT')], 'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734609982.857396, status='REVALIDATED'), HostResponse(time=1734609984.231827, status='HIT'), HostResponse(time=1734609985.620715, status='HIT'), HostResponse(time=1734609988.543952, status='HIT'), HostResponse(time=1734609989.911343, status='HIT'), HostResponse(time=1734609991.280736, status='HIT')]}, 'cdnrpnabfdp7u6drjaua': {'m9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734609974.328208, status='REVALIDATED'), HostResponse(time=1734609980.3021572, status='HIT'), HostResponse(time=1734609981.653877, status='HIT')], 'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734609975.916308, status='REVALIDATED'), HostResponse(time=1734609977.539412, status='HIT')], 'm9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734609978.9430962, status='REVALIDATED'), HostResponse(time=1734609987.2601228, status='HIT'), HostResponse(time=1734609991.486927, status='REVALIDATED')], 'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734609983.0568829, status='REVALIDATED'), HostResponse(time=1734609985.8107688, status='HIT'), HostResponse(time=1734609990.100963, status='HIT'), HostResponse(time=1734609992.8972092, status='HIT')], 'm9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734609984.431162, status='REVALIDATED'), HostResponse(time=1734609988.736942, status='HIT')]}, 'cdnr7bbwrxhguo63wkpl': {'m9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734609974.5276768, status='REVALIDATED'), HostResponse(time=1734609979.1334138, status='HIT'), HostResponse(time=1734609983.2475772, status='HIT')], 'm9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734609976.2266681, status='REVALIDATED'), HostResponse(time=1734609977.726892, status='HIT'), HostResponse(time=1734609981.874933, status='HIT')], 'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734609980.50496, status='REVALIDATED'), HostResponse(time=1734609991.6890109, status='REVALIDATED')], 'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734609984.636409, status='REVALIDATED'), HostResponse(time=1734609986.001812, status='HIT'), HostResponse(time=1734609988.928585, status='HIT'), HostResponse(time=1734609990.290024, status='HIT')], 'm9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734609987.462921, status='REVALIDATED'), HostResponse(time=1734609993.087923, status='HIT')]}, 'cdnrrausbqmlmhzq6ffp': {'m9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734609974.775959, status='REVALIDATED'), HostResponse(time=1734609979.323583, status='HIT'), HostResponse(time=1734609980.695578, status='HIT'), HostResponse(time=1734609982.064589, status='HIT')], 'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734609976.544598, status='REVALIDATED'), HostResponse(time=1734609984.8275578, status='HIT')], 'm9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734609977.9289322, status='REVALIDATED'), HostResponse(time=1734609987.653475, status='HIT'), HostResponse(time=1734609991.8933399, status='REVALIDATED')], 'm9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734609983.4552078, status='REVALIDATED'), HostResponse(time=1734609986.2026591, status='HIT'), HostResponse(time=1734609990.4865391, status='HIT'), HostResponse(time=1734609993.277811, status='HIT')], 'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734609989.131944, status='REVALIDATED')]}, 'cdnrfvuvfped42dkmyrv': {'m9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734609974.976245, status='REVALIDATED'), HostResponse(time=1734609992.0989451, status='REVALIDATED'), HostResponse(time=1734609993.468123, status='HIT')], 'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734609976.758272, status='REVALIDATED'), HostResponse(time=1734609979.516853, status='HIT'), HostResponse(time=1734609980.886115, status='HIT'), HostResponse(time=1734609983.653746, status='HIT'), HostResponse(time=1734609986.4690099, status='HIT'), HostResponse(time=1734609990.690939, status='REVALIDATED')], 'm9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734609978.128871, status='REVALIDATED'), HostResponse(time=1734609985.01723, status='HIT')], 'm9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734609982.265175, status='REVALIDATED')], 'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734609987.8555589, status='REVALIDATED'), HostResponse(time=1734609989.322738, status='HIT')]}, 'cdnrcqdphowdoxyxrufs': {'m9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734609975.296619, status='REVALIDATED'), HostResponse(time=1734609982.4547799, status='HIT'), HostResponse(time=1734609992.301845, status='REVALIDATED'), HostResponse(time=1734609993.657182, status='HIT')], 'm9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734609976.960761, status='REVALIDATED'), HostResponse(time=1734609983.844481, status='HIT'), HostResponse(time=1734609989.527947, status='REVALIDATED'), HostResponse(time=1734609990.881224, status='HIT')], 'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734609978.34398, status='REVALIDATED')], 'm9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734609979.717727, status='REVALIDATED'), HostResponse(time=1734609981.0755992, status='HIT')], 'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734609985.2197719, status='REVALIDATED'), HostResponse(time=1734609986.671381, status='HIT'), HostResponse(time=1734609988.051358, status='HIT')]}}

    print(json.dumps(copy))

    copy = {'cdnrcblizmcdlwnddrko': {'m9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734609978.547582, status='REVALIDATED'), HostResponse(time=1734609981.264586, status='HIT'), HostResponse(time=1734609985.42264, status='HIT'), HostResponse(time=1734609988.3533802, status='HIT')], 'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734609979.919399, status='REVALIDATED'), HostResponse(time=1734609982.655073, status='HIT'), HostResponse(time=1734609986.876336, status='HIT'), HostResponse(time=1734609989.7206159, status='HIT')], 'm9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734609984.042739, status='REVALIDATED')]}, 'cdnr5t2qvpsnaaglie2c': {'m9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734609975.7002182, status='REVALIDATED'), HostResponse(time=1734609977.351656, status='HIT')], 'm9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734609981.46276, status='REVALIDATED'), HostResponse(time=1734609987.06851, status='HIT')], 'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734609982.857396, status='REVALIDATED'), HostResponse(time=1734609984.231827, status='HIT'), HostResponse(time=1734609985.620715, status='HIT'), HostResponse(time=1734609988.543952, status='HIT'), HostResponse(time=1734609989.911343, status='HIT'), HostResponse(time=1734609991.280736, status='HIT')]}, 'cdnrpnabfdp7u6drjaua': {'m9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734609974.328208, status='REVALIDATED'), HostResponse(time=1734609980.3021572, status='HIT'), HostResponse(time=1734609981.653877, status='HIT')], 'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734609975.916308, status='REVALIDATED'), HostResponse(time=1734609977.539412, status='HIT')], 'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734609983.0568829, status='REVALIDATED'), HostResponse(time=1734609985.8107688, status='HIT'), HostResponse(time=1734609990.100963, status='HIT'), HostResponse(time=1734609992.8972092, status='HIT')], 'm9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734609984.431162, status='REVALIDATED'), HostResponse(time=1734609988.736942, status='HIT')]}, 'cdnr7bbwrxhguo63wkpl': {'m9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734609974.5276768, status='REVALIDATED'), HostResponse(time=1734609979.1334138, status='HIT'), HostResponse(time=1734609983.2475772, status='HIT')], 'm9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734609976.2266681, status='REVALIDATED'), HostResponse(time=1734609977.726892, status='HIT'), HostResponse(time=1734609981.874933, status='HIT')], 'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734609984.636409, status='REVALIDATED'), HostResponse(time=1734609986.001812, status='HIT'), HostResponse(time=1734609988.928585, status='HIT'), HostResponse(time=1734609990.290024, status='HIT')], 'm9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734609987.462921, status='REVALIDATED'), HostResponse(time=1734609993.087923, status='HIT')]}, 'cdnrrausbqmlmhzq6ffp': {'m9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734609974.775959, status='REVALIDATED'), HostResponse(time=1734609979.323583, status='HIT'), HostResponse(time=1734609980.695578, status='HIT'), HostResponse(time=1734609982.064589, status='HIT')], 'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734609976.544598, status='REVALIDATED'), HostResponse(time=1734609984.8275578, status='HIT')], 'm9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734609983.4552078, status='REVALIDATED'), HostResponse(time=1734609986.2026591, status='HIT'), HostResponse(time=1734609990.4865391, status='HIT'), HostResponse(time=1734609993.277811, status='HIT')], 'm9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734609989.131944, status='REVALIDATED')]}, 'cdnrfvuvfped42dkmyrv': {'m9-srv01.yccdn.cloud.yandex.net': [HostResponse(time=1734609978.128871, status='REVALIDATED'), HostResponse(time=1734609985.01723, status='HIT')], 'm9-srv04.yccdn.cloud.yandex.net': [HostResponse(time=1734609982.265175, status='REVALIDATED')], 'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734609987.8555589, status='REVALIDATED'), HostResponse(time=1734609989.322738, status='HIT')]}, 'cdnrcqdphowdoxyxrufs': {'m9-srv02.yccdn.cloud.yandex.net': [HostResponse(time=1734609978.34398, status='REVALIDATED')], 'm9-srv03.yccdn.cloud.yandex.net': [HostResponse(time=1734609979.717727, status='REVALIDATED'), HostResponse(time=1734609981.0755992, status='HIT')], 'm9-srv05.yccdn.cloud.yandex.net': [HostResponse(time=1734609985.2197719, status='REVALIDATED'), HostResponse(time=1734609986.671381, status='HIT'), HostResponse(time=1734609988.051358, status='HIT')]}}


    print(json.dumps(copy))


