"""
Utility functions and decorators
"""

import asyncio
import aiohttp
import hashlib
import time
import random
import string
from typing import Any, Callable, Optional, Dict, List, TypeVar, ParamSpec
from functools import wraps
from fake_useragent import UserAgent
from cachetools import TTLCache
import logging

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')

# Cache for extracted links (1 hour TTL)
link_cache = TTLCache(maxsize=1000, ttl=3600)


def retry_async(
    max_retries: int = 5,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Async retry decorator with exponential backoff"""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(current_delay + random.uniform(0, 1))
                        current_delay *= backoff
            
            logger.error(f"All {max_retries} attempts failed for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator


def retry_sync(
    max_retries: int = 5,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Sync retry decorator with exponential backoff"""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(current_delay + random.uniform(0, 1))
                        current_delay *= backoff
            
            logger.error(f"All {max_retries} attempts failed for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator


class HeaderGenerator:
    """Generate realistic browser headers"""
    
    def __init__(self):
        self.ua = UserAgent()
    
    def get_headers(self, referer: str = None) -> Dict[str, str]:
        headers = {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        if referer:
            headers["Referer"] = referer
        return headers
    
    def get_api_headers(self, referer: str = None) -> Dict[str, str]:
        headers = self.get_headers(referer)
        headers.update({
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        })
        return headers


header_gen = HeaderGenerator()


def generate_device_id() -> str:
    """Generate a random device ID"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))


def generate_bdstoken() -> str:
    """Generate a random bdstoken"""
    return hashlib.md5(str(time.time()).encode()).hexdigest()


def extract_json_from_html(html: str, variable_name: str) -> Optional[Dict]:
    """Extract JSON data embedded in HTML"""
    import re
    import json
    
    patterns = [
        rf'var\s+{variable_name}\s*=\s*(\{{.+?\}});',
        rf'{variable_name}\s*:\s*(\{{.+?\}}),',
        rf"'{variable_name}'\s*:\s*(\{{.+?\}}),",
        rf'"{variable_name}"\s*:\s*(\{{.+?\}}),',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    
    return None


def extract_all_json_from_html(html: str) -> List[Dict]:
    """Extract all JSON objects from HTML"""
    import re
    import json
    
    json_objects = []
    
    # Find all potential JSON objects
    pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(pattern, html)
    
    for match in matches:
        try:
            obj = json.loads(match)
            if isinstance(obj, dict):
                json_objects.append(obj)
        except json.JSONDecodeError:
            continue
    
    return json_objects


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    import re
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Limit length
    if len(filename) > 200:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:195] + ('.' + ext if ext else '')
    return filename


def format_file_size(size_bytes: int) -> str:
    """Format file size to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def get_cache_key(url: str) -> str:
    """Generate cache key from URL"""
    from mirrors import TeraboxMirrors
    share_id = TeraboxMirrors.extract_share_id(url)
    return share_id if share_id else hashlib.md5(url.encode()).hexdigest()


async def safe_request(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    **kwargs
) -> Optional[aiohttp.ClientResponse]:
    """Make a safe HTTP request with error handling"""
    try:
        async with session.request(method, url, **kwargs) as response:
            return response
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return None
