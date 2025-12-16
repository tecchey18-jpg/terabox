"""
ALL Known Terabox mirrors, subdomains, and related sites
Last Updated: 2024
"""

from typing import List, Dict, Pattern, Set
import re


class TeraboxMirrors:
    """Comprehensive list of all Terabox domains and mirrors"""
    
    # ========== PRIMARY DOMAINS ==========
    PRIMARY_DOMAINS: List[str] = [
        "terabox.com",
        "teraboxapp.com",
        "1024tera.com",
        "terabox.app",
        "terabox.tech",
        "terabox.fun",
    ]
    
    # ========== OFFICIAL MIRRORS ==========
    OFFICIAL_MIRRORS: List[str] = [
        "gcloud.live",
        "dubox.com",
        "pan.baidu.com",
    ]
    
    # ========== LINK SHORTENER / SHARE SITES ==========
    LINK_SITES: List[str] = [
        "teraboxlink.com",
        "teraboxlinks.site",      # ← Added!
        "terasharelink.com",
        "teralink.me",
        "teraboxshare.com",
        "terafileshare.com",
        "teraboxdownload.com",
        "teradl.com",
        "tera-link.com",
        "terabox.link",
        "teraboxurl.com",
    ]
    
    # ========== MIRROR SITES ==========
    MIRROR_DOMAINS: List[str] = [
        "mirrobox.com",
        "nephobox.com",
        "4funbox.com",
        "1024terabox.com",
        "freeterabox.com",
        "momerybox.com",
        "tibibox.com",
        "xhobox.com",
        "happybox.org",
        "boxtera.net",
        "teracloud.me",
        "cloudtera.net",
    ]
    
    # ========== ALTERNATIVE / REGIONAL DOMAINS ==========
    ALTERNATIVE_DOMAINS: List[str] = [
        "terabox.co",
        "terabox.net",
        "terabox.org",
        "terabox.io",
        "terabox.cloud",
        "terabox.me",
        "teraboxcdn.com",
        "terabox-cdn.com",
        "tera-box.com",
        "tera.box",
    ]
    
    # ========== DOWNLOAD / API DOMAINS ==========
    API_DOMAINS: List[str] = [
        "d.terabox.com",
        "dl.teraboxapp.com",
        "data.teraboxapp.com",
        "www.terabox.com",
        "www.teraboxapp.com",
        "www.1024tera.com",
        "api.terabox.com",
        "m.terabox.com",
        "pan.terabox.com",
        "c.terabox.com",
        "d2.terabox.com",
        "d3.terabox.com",
    ]
    
    # ========== THIRD PARTY EXTRACTORS ==========
    THIRD_PARTY_EXTRACTORS: List[str] = [
        "teradownloader.com",
        "terabox.hnn.workers.dev",
        "teraboxvideodownloader.com",
        "savetera.com",
        "terasave.com",
        "tera.instavideosave.com",
        "teraboxplayer.com",
        "terabox-dl.com",
    ]
    
    # ========== SUBDOMAIN PATTERNS ==========
    SUBDOMAIN_PATTERNS: List[str] = [
        r"[\w-]+\.terabox\.com",
        r"[\w-]+\.teraboxapp\.com",
        r"[\w-]+\.1024tera\.com",
        r"[\w-]+\.dubox\.com",
        r"[\w-]+\.gcloud\.live",
        r"[\w-]+\.teraboxlinks\.site",
    ]
    
    # ========== URL PATTERNS FOR EXTRACTION ==========
    URL_PATTERNS: List[Pattern] = [
        # Standard share links: /s/xxxxx
        re.compile(
            r'https?://(?:www\.)?(?:[\w-]+\.)?('
            r'terabox|teraboxapp|1024tera|dubox|mirrobox|nephobox|4funbox|'
            r'freeterabox|teraboxshare|momerybox|tibibox|xhobox|gcloud|'
            r'teraboxlink|teraboxlinks|terasharelink|terafileshare|'
            r'1024terabox|happybox|boxtera|teracloud|cloudtera'
            r')\.(?:com|app|live|tech|fun|site|me|net|org|link)/s/([a-zA-Z0-9_-]+)',
            re.IGNORECASE
        ),
        
        # Short links without /s/
        re.compile(
            r'https?://(?:www\.)?(?:[\w-]+\.)?(?:terabox|teraboxapp|1024tera)'
            r'\.(?:com|app)/([a-zA-Z0-9_-]{8,})',
            re.IGNORECASE
        ),
        
        # Web/wap share links with surl parameter
        re.compile(
            r'https?://(?:www\.)?(?:[\w-]+\.)?(?:terabox|teraboxapp|1024tera|dubox)'
            r'\.(?:com|app)/(?:web|wap)/share/(?:init|link|filelist)\?surl=([a-zA-Z0-9_-]+)',
            re.IGNORECASE
        ),
        
        # Direct file links
        re.compile(
            r'https?://(?:[\w-]+\.)?(?:terabox|teraboxapp|1024tera)'
            r'\.(?:com|app)/file/([a-zA-Z0-9_-]+)',
            re.IGNORECASE
        ),
        
        # Share with shareid parameter
        re.compile(
            r'https?://[^\s]+[?&]shareid=([a-zA-Z0-9_-]+)',
            re.IGNORECASE
        ),
        
        # Share with surl parameter (anywhere in URL)
        re.compile(
            r'https?://[^\s]+[?&]surl=([a-zA-Z0-9_-]+)',
            re.IGNORECASE
        ),
        
        # teraboxlinks.site specific pattern
        re.compile(
            r'https?://(?:www\.)?teraboxlinks\.site/(?:s/)?([a-zA-Z0-9_-]+)',
            re.IGNORECASE
        ),
    ]
    
    # ========== API ENDPOINTS ==========
    API_ENDPOINTS: Dict[str, Dict[str, str]] = {
        "terabox.com": {
            "base": "https://www.terabox.com",
            "api": "https://www.terabox.com/api",
            "share": "https://www.terabox.com/share",
        },
        "teraboxapp.com": {
            "base": "https://www.teraboxapp.com",
            "api": "https://www.teraboxapp.com/api",
            "share": "https://www.teraboxapp.com/share",
        },
        "1024tera.com": {
            "base": "https://www.1024tera.com",
            "api": "https://www.1024tera.com/api",
            "share": "https://www.1024tera.com/share",
        },
        "dubox.com": {
            "base": "https://www.dubox.com",
            "api": "https://www.dubox.com/api",
            "share": "https://www.dubox.com/share",
        },
        "gcloud.live": {
            "base": "https://www.gcloud.live",
            "api": "https://www.gcloud.live/api",
            "share": "https://www.gcloud.live/share",
        },
        "teraboxlinks.site": {
            "base": "https://teraboxlinks.site",
            "api": "https://teraboxlinks.site/api",
            "share": "https://teraboxlinks.site",
        },
    }
    
    # ========== DOMAIN MAPPING (redirect domains to main API) ==========
    DOMAIN_MAPPING: Dict[str, str] = {
        # Map mirror domains to their API equivalent
        "mirrobox.com": "terabox.com",
        "nephobox.com": "terabox.com",
        "4funbox.com": "terabox.com",
        "freeterabox.com": "terabox.com",
        "momerybox.com": "terabox.com",
        "tibibox.com": "terabox.com",
        "xhobox.com": "terabox.com",
        "1024terabox.com": "1024tera.com",
        "teraboxlinks.site": "terabox.com",
        "teraboxlink.com": "terabox.com",
        "terasharelink.com": "terabox.com",
        "teraboxshare.com": "terabox.com",
        "terafileshare.com": "terabox.com",
    }

    @classmethod
    def get_all_domains(cls) -> List[str]:
        """Get all known domains"""
        all_domains = set()
        all_domains.update(cls.PRIMARY_DOMAINS)
        all_domains.update(cls.OFFICIAL_MIRRORS)
        all_domains.update(cls.LINK_SITES)
        all_domains.update(cls.MIRROR_DOMAINS)
        all_domains.update(cls.ALTERNATIVE_DOMAINS)
        all_domains.update(cls.API_DOMAINS)
        all_domains.update(cls.THIRD_PARTY_EXTRACTORS)
        return list(all_domains)
    
    @classmethod
    def get_all_domains_pattern(cls) -> str:
        """Get regex pattern matching all domains"""
        domains = cls.get_all_domains()
        # Escape dots and create pattern
        escaped = [d.replace('.', r'\.') for d in domains]
        return '|'.join(escaped)
    
    @classmethod
    def is_terabox_url(cls, url: str) -> bool:
        """Check if URL is from any Terabox domain"""
        if not url:
            return False
            
        url_lower = url.lower()
        
        # Check against all known domains
        for domain in cls.get_all_domains():
            if domain.lower() in url_lower:
                return True
        
        # Check subdomain patterns
        for pattern in cls.SUBDOMAIN_PATTERNS:
            if re.search(pattern, url_lower):
                return True
        
        # Check for common Terabox URL patterns
        terabox_indicators = [
            '/s/',
            'surl=',
            'shareid=',
            'terabox',
            'tera',
            'dubox',
        ]
        
        if any(indicator in url_lower for indicator in terabox_indicators):
            # Additional validation
            if re.search(r'https?://[^\s]+', url):
                return True
        
        return False
    
    @classmethod
    def extract_share_id(cls, url: str) -> str | None:
        """Extract share ID from any Terabox URL format"""
        if not url:
            return None
        
        # Try each URL pattern
        for pattern in cls.URL_PATTERNS:
            match = pattern.search(url)
            if match:
                # Get the last captured group (share ID)
                groups = match.groups()
                share_id = groups[-1] if groups else None
                if share_id and len(share_id) >= 4:
                    return share_id
        
        # Fallback: try to extract from query parameters
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Check various parameter names
            param_names = ['surl', 'shareid', 'share_id', 'id', 'fid', 's']
            for param in param_names:
                if param in params and params[param]:
                    return params[param][0]
            
            # Try to extract from path
            path_parts = parsed.path.strip('/').split('/')
            
            # Check for /s/xxxxx pattern
            if 's' in path_parts:
                s_index = path_parts.index('s')
                if s_index + 1 < len(path_parts):
                    return path_parts[s_index + 1]
            
            # Get the last path segment if it looks like a share ID
            for part in reversed(path_parts):
                if len(part) >= 6 and re.match(r'^[a-zA-Z0-9_-]+$', part):
                    return part
                    
        except Exception:
            pass
        
        return None
    
    @classmethod
    def normalize_url(cls, url: str) -> str:
        """Normalize URL to standard format"""
        share_id = cls.extract_share_id(url)
        if share_id:
            # Determine which API to use based on original URL
            api_domain = cls.get_api_domain(url)
            return f"https://www.{api_domain}/s/{share_id}"
        return url
    
    @classmethod
    def get_api_domain(cls, url: str) -> str:
        """Get the appropriate API domain for a URL"""
        url_lower = url.lower()
        
        # Check if URL contains a known domain
        for domain, mapped_domain in cls.DOMAIN_MAPPING.items():
            if domain in url_lower:
                return mapped_domain
        
        # Check primary domains
        for domain in cls.PRIMARY_DOMAINS:
            if domain in url_lower:
                return domain
        
        # Default to terabox.com
        return "terabox.com"
    
    @classmethod
    def get_api_endpoints(cls, url: str) -> Dict[str, str]:
        """Get API endpoints for a URL"""
        domain = cls.get_api_domain(url)
        
        if domain in cls.API_ENDPOINTS:
            return cls.API_ENDPOINTS[domain]
        
        # Default endpoints
        return {
            "base": f"https://www.{domain}",
            "api": f"https://www.{domain}/api",
            "share": f"https://www.{domain}/share",
        }
    
    @classmethod
    def get_alternative_urls(cls, share_id: str) -> List[str]:
        """Get list of alternative URLs to try for a share ID"""
        urls = []
        
        # Primary domains first
        for domain in cls.PRIMARY_DOMAINS[:3]:
            urls.append(f"https://www.{domain}/s/{share_id}")
        
        # Then official mirrors
        for domain in cls.OFFICIAL_MIRRORS[:2]:
            urls.append(f"https://www.{domain}/s/{share_id}")
        
        return urls
    
    @classmethod
    def get_all_api_urls(cls, share_id: str) -> List[Dict[str, str]]:
        """Get all possible API URLs for extraction"""
        api_urls = []
        
        domains_to_try = [
            "terabox.com",
            "teraboxapp.com", 
            "1024tera.com",
            "dubox.com",
            "gcloud.live",
        ]
        
        for domain in domains_to_try:
            api_urls.append({
                "domain": domain,
                "shorturlinfo": f"https://www.{domain}/api/shorturlinfo?shorturl={share_id}&root=1",
                "list": f"https://www.{domain}/share/list?shorturl={share_id}&root=1",
                "page": f"https://www.{domain}/s/{share_id}",
            })
        
        return api_urls


# ========== QUICK ACCESS FUNCTIONS ==========

def is_terabox_url(url: str) -> bool:
    """Quick check if URL is Terabox"""
    return TeraboxMirrors.is_terabox_url(url)


def extract_share_id(url: str) -> str | None:
    """Quick extract share ID"""
    return TeraboxMirrors.extract_share_id(url)


def normalize_url(url: str) -> str:
    """Quick normalize URL"""
    return TeraboxMirrors.normalize_url(url)


def get_all_domains() -> List[str]:
    """Get all domains"""
    return TeraboxMirrors.get_all_domains()


# ========== PRINT ALL DOMAINS (for reference) ==========

if __name__ == "__main__":
    print("=" * 60)
    print("ALL KNOWN TERABOX DOMAINS")
    print("=" * 60)
    
    all_domains = TeraboxMirrors.get_all_domains()
    print(f"\nTotal domains: {len(all_domains)}\n")
    
    print("Primary Domains:")
    for d in TeraboxMirrors.PRIMARY_DOMAINS:
        print(f"  • {d}")
    
    print("\nLink/Share Sites:")
    for d in TeraboxMirrors.LINK_SITES:
        print(f"  • {d}")
    
    print("\nMirror Domains:")
    for d in TeraboxMirrors.MIRROR_DOMAINS:
        print(f"  • {d}")
    
    print("\nAlternative Domains:")
    for d in TeraboxMirrors.ALTERNATIVE_DOMAINS:
        print(f"  • {d}")
    
    print("\n" + "=" * 60)
    
    # Test URL extraction
    test_urls = [
        "https://teraboxlinks.site/s/1abc123def",
        "https://www.terabox.com/s/1xyz789",
        "https://1024tera.com/wap/share/link?surl=abc123",
        "https://mirrobox.com/s/test123",
    ]
    
    print("\nTEST URL EXTRACTION:")
    for url in test_urls:
        is_valid = TeraboxMirrors.is_terabox_url(url)
        share_id = TeraboxMirrors.extract_share_id(url)
        print(f"\nURL: {url}")
        print(f"  Valid: {is_valid}")
        print(f"  Share ID: {share_id}")
