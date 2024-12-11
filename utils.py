import logging
import time
from functools import wraps
from typing import Callable, Any, Dict
import uuid

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

