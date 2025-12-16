"""
Core Terabox video extraction logic with multiple methods
"""

import asyncio
import aiohttp
import httpx
import requests
import cloudscraper
import json
import re
import time
import hashlib
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse, parse_qs, quote
import logging

from config import config
from mirrors import TeraboxMirrors
from utils import (
    retry_async, retry_sync, header_gen, generate_device_id,
    generate_bdstoken, extract_json_from_html, extract_all_json_from_html,
    link_cache, get_cache_key, format_file_size
)

logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    """Video information dataclass"""
    title: str = ""
    thumbnail: str = ""
    duration: int = 0
    size: int = 0
    size_formatted: str = ""
    resolution: str = ""
    direct_link: str = ""
    download_link: str = ""
    stream_link: str = ""
    m3u8_link: str = ""
    file_id: str = ""
    share_id: str = ""
    uk: str = ""
    sign: str = ""
    timestamp: int = 0
    quality_options: Dict[str, str] = field(default_factory=dict)
    raw_data: Dict = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        return bool(self.direct_link or self.stream_link or self.m3u8_link or self.download_link)
    
    def get_best_link(self) -> str:
        """Get the best available playable link"""
        return self.stream_link or self.direct_link or self.m3u8_link or self.download_link
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "thumbnail": self.thumbnail,
            "duration": self.duration,
            "size": self.size,
            "size_formatted": self.size_formatted,
            "resolution": self.resolution,
            "direct_link": self.direct_link,
            "download_link": self.download_link,
            "stream_link": self.stream_link,
            "m3u8_link": self.m3u8_link,
            "quality_options": self.quality_options,
        }


class TeraboxExtractor:
    """Main extractor class with multiple extraction methods"""
    
    EXTRACTION_METHODS = [
        "method_api_v1",
        "method_api_v2", 
        "method_web_scraping",
        "method_cloudscraper",
        "method_mobile_api",
        "method_direct_parse",
        "method_alternative_api",
        "method_browser_emulation",
    ]
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        self.cookies: Dict[str, str] = {}
        self.device_id = generate_device_id()
        
    async def __aenter__(self):
        await self.init_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def init_session(self):
        """Initialize aiohttp session with proper settings"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=config.REQUEST_TIMEOUT)
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                ssl=False
            )
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                trust_env=True
            )
    
    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def extract(self, url: str) -> VideoInfo:
        """
        Main extraction method - tries all methods until success
        """
        await self.init_session()
        
        # Check cache first
        cache_key = get_cache_key(url)
        if cache_key in link_cache:
            logger.info(f"Cache hit for {cache_key}")
            return link_cache[cache_key]
        
        # Validate URL
        if not TeraboxMirrors.is_terabox_url(url):
            raise ValueError(f"Not a valid Terabox URL: {url}")
        
        # Normalize URL
        normalized_url = TeraboxMirrors.normalize_url(url)
        share_id = TeraboxMirrors.extract_share_id(url)
        
        if not share_id:
            raise ValueError(f"Could not extract share ID from URL: {url}")
        
        logger.info(f"Extracting video from: {url} (Share ID: {share_id})")
        
        # Try each method
        last_error = None
        for method_name in self.EXTRACTION_METHODS:
            try:
                logger.info(f"Trying {method_name}...")
                method = getattr(self, method_name)
                result = await method(normalized_url, share_id)
                
                if result and result.is_valid():
                    # Cache the result
                    link_cache[cache_key] = result
                    logger.info(f"Successfully extracted using {method_name}")
                    return result
                    
            except Exception as e:
                logger.warning(f"{method_name} failed: {str(e)}")
                last_error = e
                continue
        
        # If all methods fail, raise the last error
        raise Exception(f"All extraction methods failed. Last error: {last_error}")
    
    @retry_async(max_retries=3, delay=1.0)
    async def method_api_v1(self, url: str, share_id: str) -> VideoInfo:
        """Method 1: Standard API approach"""
        
        # Step 1: Get file list
        api_url = f"https://www.terabox.com/api/shorturlinfo"
        params = {
            "shorturl": share_id,
            "root": 1,
        }
        
        headers = header_gen.get_api_headers(url)
        
        async with self.session.get(api_url, params=params, headers=headers) as resp:
            if resp.status != 200:
                raise Exception(f"API returned status {resp.status}")
            
            data = await resp.json()
            
        if data.get("errno") != 0:
            raise Exception(f"API error: {data.get('errmsg', 'Unknown error')}")
        
        file_list = data.get("list", [])
        if not file_list:
            raise Exception("No files found in share")
        
        # Get the first video file
        video_file = None
        for file in file_list:
            if file.get("isdir") == 0:
                filename = file.get("server_filename", "").lower()
                if any(ext in filename for ext in ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']):
                    video_file = file
                    break
        
        if not video_file:
            video_file = file_list[0]  # Use first file if no video found
        
        # Step 2: Get download/stream link
        shareid = data.get("shareid")
        uk = data.get("uk")
        sign = data.get("sign")
        timestamp = data.get("timestamp")
        
        return await self._get_download_link(
            video_file, shareid, uk, sign, timestamp, share_id
        )
    
    @retry_async(max_retries=3, delay=1.0)
    async def method_api_v2(self, url: str, share_id: str) -> VideoInfo:
        """Method 2: Alternative API endpoint"""
        
        api_url = "https://www.terabox.com/share/list"
        params = {
            "app_id": "250528",
            "shorturl": share_id,
            "root": "1",
            "web": "1",
            "channel": "dubox",
            "clienttype": "0",
        }
        
        headers = header_gen.get_api_headers(url)
        headers["Cookie"] = f"ndus={generate_device_id()}"
        
        async with self.session.get(api_url, params=params, headers=headers) as resp:
            data = await resp.json()
        
        if data.get("errno") != 0:
            raise Exception(f"API v2 error: {data.get('errmsg')}")
        
        file_list = data.get("list", [])
        if not file_list:
            raise Exception("No files in response")
        
        video_file = self._find_video_in_list(file_list)
        
        shareid = data.get("share_id") or data.get("shareid")
        uk = data.get("uk")
        sign = data.get("sign")
        timestamp = data.get("timestamp")
        
        return await self._get_download_link(
            video_file, shareid, uk, sign, timestamp, share_id
        )
    
    @retry_async(max_retries=3, delay=1.0)
    async def method_web_scraping(self, url: str, share_id: str) -> VideoInfo:
        """Method 3: Web scraping approach"""
        
        headers = header_gen.get_headers(url)
        
        async with self.session.get(url, headers=headers) as resp:
            html = await resp.text()
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Try to find embedded data
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string:
                # Look for file data in script
                file_data = self._extract_file_data_from_script(script.string)
                if file_data:
                    return self._create_video_info_from_data(file_data, share_id)
        
        # Try to find video URL directly
        video_patterns = [
            r'"dlink"\s*:\s*"([^"]+)"',
            r'"downloadurl"\s*:\s*"([^"]+)"',
            r'"stream_url"\s*:\s*"([^"]+)"',
            r'"m3u8_url"\s*:\s*"([^"]+)"',
            r'https://[^"\']+\.m3u8[^"\'\s]*',
            r'https://[^"\']+/file/[^"\'\s]+',
        ]
        
        for pattern in video_patterns:
            matches = re.findall(pattern, html)
            if matches:
                link = matches[0].replace('\\/', '/')
                if link and 'http' in link:
                    info = VideoInfo(
                        title=self._extract_title_from_html(soup) or "Video",
                        direct_link=link,
                        share_id=share_id,
                    )
                    if info.is_valid():
                        return info
        
        raise Exception("Could not extract video from HTML")
    
    @retry_async(max_retries=3, delay=1.0)
    async def method_cloudscraper(self, url: str, share_id: str) -> VideoInfo:
        """Method 4: Using cloudscraper to bypass protection"""
        
        loop = asyncio.get_event_loop()
        
        # Run cloudscraper in executor
        def scrape():
            response = self.scraper.get(url)
            return response.text
        
        html = await loop.run_in_executor(None, scrape)
        
        # Extract data from HTML
        data = self._parse_html_for_video_data(html)
        
        if data:
            return self._create_video_info_from_data(data, share_id)
        
        raise Exception("Cloudscraper method failed")
    
    @retry_async(max_retries=3, delay=1.0)
    async def method_mobile_api(self, url: str, share_id: str) -> VideoInfo:
        """Method 5: Mobile API endpoint"""
        
        api_url = "https://www.terabox.com/api/shorturlinfo"
        params = {
            "shorturl": share_id,
            "root": "1",
            "app_id": "250528",
            "web": "1",
            "clienttype": "1",  # Mobile client
        }
        
        headers = header_gen.get_api_headers(url)
        headers["User-Agent"] = "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36"
        
        async with self.session.get(api_url, params=params, headers=headers) as resp:
            data = await resp.json()
        
        if data.get("errno") != 0:
            raise Exception(f"Mobile API error: {data.get('errmsg')}")
        
        file_list = data.get("list", [])
        if not file_list:
            raise Exception("No files in mobile API response")
        
        video_file = self._find_video_in_list(file_list)
        
        return await self._get_download_link(
            video_file,
            data.get("shareid"),
            data.get("uk"),
            data.get("sign"),
            data.get("timestamp"),
            share_id
        )
    
    @retry_async(max_retries=3, delay=1.0)
    async def method_direct_parse(self, url: str, share_id: str) -> VideoInfo:
        """Method 6: Direct URL parsing and construction"""
        
        # Try multiple domain variations
        domains = [
            "terabox.com",
            "teraboxapp.com",
            "1024tera.com",
        ]
        
        for domain in domains:
            try:
                api_url = f"https://www.{domain}/api/shorturlinfo"
                params = {"shorturl": share_id, "root": 1}
                headers = header_gen.get_api_headers(f"https://www.{domain}/s/{share_id}")
                
                async with self.session.get(api_url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("errno") == 0 and data.get("list"):
                            file_info = data["list"][0]
                            
                            # Try to construct direct link
                            dlink = file_info.get("dlink", "")
                            if dlink:
                                info = VideoInfo(
                                    title=file_info.get("server_filename", "Video"),
                                    size=file_info.get("size", 0),
                                    size_formatted=format_file_size(file_info.get("size", 0)),
                                    direct_link=dlink,
                                    thumbnail=file_info.get("thumbs", {}).get("url3", ""),
                                    share_id=share_id,
                                    raw_data=file_info,
                                )
                                return info
                                
            except Exception as e:
                continue
        
        raise Exception("Direct parse method failed for all domains")
    
    @retry_async(max_retries=3, delay=1.0)
    async def method_alternative_api(self, url: str, share_id: str) -> VideoInfo:
        """Method 7: Alternative API endpoints"""
        
        # Try filemoon-style extraction
        endpoints = [
            f"https://terabox.hnn.workers.dev/api/get-info?shorturl={share_id}",
            f"https://terabox.udayscriptsx.workers.dev/?url={url}",
            f"https://tera.instavideosave.com/?url={url}",
        ]
        
        for endpoint in endpoints:
            try:
                async with self.session.get(
                    endpoint,
                    headers=header_gen.get_api_headers(),
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Parse response based on structure
                        if isinstance(data, dict):
                            link = (
                                data.get("download_link") or
                                data.get("direct_link") or
                                data.get("dlink") or
                                data.get("url") or
                                data.get("data", {}).get("dlink")
                            )
                            
                            if link:
                                return VideoInfo(
                                    title=data.get("file_name") or data.get("title") or "Video",
                                    size=data.get("size", 0),
                                    size_formatted=format_file_size(data.get("size", 0)),
                                    direct_link=link,
                                    thumbnail=data.get("thumb") or data.get("thumbnail", ""),
                                    share_id=share_id,
                                    raw_data=data,
                                )
            except Exception as e:
                logger.debug(f"Alternative endpoint {endpoint} failed: {e}")
                continue
        
        raise Exception("All alternative API endpoints failed")
    
    @retry_async(max_retries=2, delay=2.0)
    async def method_browser_emulation(self, url: str, share_id: str) -> VideoInfo:
        """Method 8: Browser emulation using Playwright (last resort)"""
        
        if not config.USE_BROWSER_FALLBACK:
            raise Exception("Browser fallback disabled")
        
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=config.HEADLESS)
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=header_gen.get_headers()["User-Agent"]
                )
                page = await context.new_page()
                
                # Capture network requests
                captured_urls = []
                
                async def capture_request(request):
                    req_url = request.url
                    if any(ext in req_url for ext in ['.m3u8', '.mp4', 'download', 'stream']):
                        captured_urls.append(req_url)
                
                page.on("request", capture_request)
                
                await page.goto(url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(3)
                
                # Try to click play button if exists
                try:
                    await page.click('button[class*="play"], div[class*="play"], .vjs-play-control', timeout=5000)
                    await asyncio.sleep(2)
                except:
                    pass
                
                # Extract from page content
                content = await page.content()
                
                await browser.close()
                
                # Find video URLs
                for captured_url in captured_urls:
                    if 'http' in captured_url:
                        return VideoInfo(
                            title="Video",
                            direct_link=captured_url,
                            share_id=share_id,
                        )
                
                # Parse content for links
                video_data = self._parse_html_for_video_data(content)
                if video_data:
                    return self._create_video_info_from_data(video_data, share_id)
                
        except ImportError:
            logger.warning("Playwright not installed, skipping browser method")
        except Exception as e:
            logger.error(f"Browser emulation failed: {e}")
        
        raise Exception("Browser emulation failed")
    
    async def _get_download_link(
        self,
        file_info: Dict,
        shareid: str,
        uk: str,
        sign: str,
        timestamp: int,
        share_id: str
    ) -> VideoInfo:
        """Get the actual download/stream link for a file"""
        
        fs_id = file_info.get("fs_id")
        
        # Try to get download link
        api_url = "https://www.terabox.com/share/download"
        params = {
            "app_id": "250528",
            "channel": "dubox",
            "clienttype": "0",
            "web": "1",
            "shareid": shareid,
            "uk": uk,
            "sign": sign,
            "timestamp": timestamp,
            "fid_list": json.dumps([fs_id]),
            "primaryid": shareid,
        }
        
        headers = header_gen.get_api_headers(f"https://www.terabox.com/s/{share_id}")
        headers["Cookie"] = f"ndus={self.device_id}"
        
        async with self.session.get(api_url, params=params, headers=headers) as resp:
            data = await resp.json()
        
        dlink = ""
        if data.get("errno") == 0:
            dlink = data.get("dlink") or data.get("list", [{}])[0].get("dlink", "")
        
        # If no direct link, try the one in file_info
        if not dlink:
            dlink = file_info.get("dlink", "")
        
        # Construct VideoInfo
        return VideoInfo(
            title=file_info.get("server_filename", "Video"),
            size=file_info.get("size", 0),
            size_formatted=format_file_size(file_info.get("size", 0)),
            thumbnail=file_info.get("thumbs", {}).get("url3", ""),
            direct_link=dlink,
            download_link=dlink,
            file_id=str(fs_id),
            share_id=share_id,
            uk=str(uk),
            sign=sign,
            timestamp=timestamp,
            raw_data=file_info,
        )
    
    def _find_video_in_list(self, file_list: List[Dict]) -> Dict:
        """Find video file in a list of files"""
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
        
        for file in file_list:
            if file.get("isdir") == 0:
                filename = file.get("server_filename", "").lower()
                if any(filename.endswith(ext) for ext in video_extensions):
                    return file
        
        # Return first non-directory file if no video found
        for file in file_list:
            if file.get("isdir") == 0:
                return file
        
        return file_list[0] if file_list else {}
    
    def _extract_file_data_from_script(self, script_content: str) -> Optional[Dict]:
        """Extract file data from script content"""
        patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'locals\.data\s*=\s*({.+?});',
            r'yunData\.setData\(({.+?})\)',
            r'"file_list"\s*:\s*(\[.+?\])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, script_content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    return data
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _parse_html_for_video_data(self, html: str) -> Optional[Dict]:
        """Parse HTML content for video data"""
        
        # Try to find JSON data in HTML
        json_data = extract_all_json_from_html(html)
        
        for data in json_data:
            if self._is_valid_video_data(data):
                return data
        
        # Try regex patterns
        patterns = [
            (r'"dlink"\s*:\s*"([^"]+)"', "dlink"),
            (r'"downloadUrl"\s*:\s*"([^"]+)"', "download_link"),
            (r'"stream_url"\s*:\s*"([^"]+)"', "stream_link"),
        ]
        
        result = {}
        for pattern, key in patterns:
            match = re.search(pattern, html)
            if match:
                result[key] = match.group(1).replace('\\/', '/')
        
        if result:
            # Also try to get title and size
            title_match = re.search(r'"server_filename"\s*:\s*"([^"]+)"', html)
            if title_match:
                result["title"] = title_match.group(1)
            
            size_match = re.search(r'"size"\s*:\s*(\d+)', html)
            if size_match:
                result["size"] = int(size_match.group(1))
            
            return result
        
        return None
    
    def _is_valid_video_data(self, data: Dict) -> bool:
        """Check if data contains valid video information"""
        video_keys = ["dlink", "download_link", "stream_url", "m3u8_url", "downloadUrl"]
        return any(key in data for key in video_keys)
    
    def _create_video_info_from_data(self, data: Dict, share_id: str) -> VideoInfo:
        """Create VideoInfo from parsed data"""
        
        # Handle nested structures
        if "file_list" in data:
            file_data = data["file_list"][0] if data["file_list"] else {}
        elif "list" in data:
            file_data = data["list"][0] if data["list"] else {}
        else:
            file_data = data
        
        dlink = (
            file_data.get("dlink") or
            file_data.get("download_link") or
            file_data.get("downloadUrl") or
            ""
        ).replace('\\/', '/')
        
        stream = file_data.get("stream_url", "").replace('\\/', '/')
        m3u8 = file_data.get("m3u8_url", "").replace('\\/', '/')
        
        size = file_data.get("size", 0)
        
        return VideoInfo(
            title=file_data.get("server_filename") or file_data.get("title") or "Video",
            size=size,
            size_formatted=format_file_size(size),
            thumbnail=file_data.get("thumbs", {}).get("url3", ""),
            direct_link=dlink,
            download_link=dlink,
            stream_link=stream,
            m3u8_link=m3u8,
            share_id=share_id,
            raw_data=file_data,
        )
    
    def _extract_title_from_html(self, soup: BeautifulSoup) -> str:
        """Extract video title from HTML"""
        # Try various title sources
        title_selectors = [
            'title',
            'h1',
            '.file-name',
            '.filename',
            '[class*="title"]',
            'meta[property="og:title"]',
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    return element.get('content', '')
                return element.get_text(strip=True)
        
        return ""


# Singleton instance
extractor = TeraboxExtractor()


async def extract_video(url: str) -> VideoInfo:
    """Convenience function for video extraction"""
    async with TeraboxExtractor() as ext:
        return await ext.extract(url)
