import logging
import time
from functools import wraps
from typing import Callable, Any, Dict, Optional
import uuid
import subprocess
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager


# need for requesting API several times with pause as API methods may be completed not instantly
def repeat_and_sleep(times_to_repeat: int = 3, sleep_duration: int = 1):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            logging.info(f'Processing function [{func}] for [{times_to_repeat}] '
                         f'times with [{sleep_duration}] second(s) sleep...')
            for i in range(times_to_repeat):
                logging.info(f'Attempt #{i+1}...')
                res = func(*args, **kwargs)
                if res is not None:
                    return res
                logging.info(f'...failed. Sleeping for {sleep_duration} second(s)...')
                time.sleep(sleep_duration)
            else:
                logging.error(f'failed to successfully complete func [{func}]')
                return None
        return wrapper
    return decorator

def make_random_8_symbols():
    return str(uuid.uuid4())[:8]

def make_query_string_from_args(args_dict: Dict[str, str]) -> str:
    return str.join('&', [f'{arg}={val}' for arg, val in args_dict.items()])

def ping(host: str, attempts: int = 1) -> Optional[subprocess.CompletedProcess]:
    param = '-n' if subprocess.run(['uname'], capture_output=True, text=True).stdout.strip() == 'Windows' else '-c'
    command = ['ping', param, str(attempts), host]
    try:
        res = subprocess.run(command, capture_output=True, text=True, check=True)
        return res
    except subprocess.CalledProcessError as e:
        return None

def http_get_request_through_ip_address(url: str, ip_address: str) -> Optional[requests.Response]:
    class HostHeaderHTTPAdapter(HTTPAdapter):
        def __init__(self, ip_address: str, *args, **kwargs):
            self.dest_ip = ip_address
            super().__init__(*args, **kwargs)

        def get_connection(self, url, proxies=None):
            # Подменяем хост в URL на целевой IP адрес
            conn = super().get_connection_with_tls_context(url.replace(self.dest_ip, ''), proxies)
            conn.poolmanager = PoolManager(10, **self.poolmanager.connection_pool_kw)
            return conn

        def send(self, request, *args, **kwargs):
            original_host = request.url.split('/')[2]
            request.url = request.url.replace(original_host, self.dest_ip)
            if 'Host' not in request.headers:
                request.headers['Host'] = original_host
            return super().send(request, *args, **kwargs)

    url = f'http://{url}'
    session = requests.Session()
    session.mount('http://', HostHeaderHTTPAdapter(ip_address))

    try:
        return session.get(url)
    except requests.RequestException as e:
        #TODO: implement exception processing
        ...