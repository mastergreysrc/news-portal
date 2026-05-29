"""URL normalization — strip tracking params, unify forms."""

import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

# Params to strip from URLs
TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'ref', 'source', 'fbclid', 'gclid', 'gclsrc', 'dclid',
    'mc_cid', 'mc_eid', 'igshid', 'si', 's', 'wpsrc',
}

def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication: lowercase host, strip tracking params, remove fragment."""
    if not url:
        return ""
    
    parsed = urlparse(url.strip())
    
    # Lowercase scheme + host
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    
    # Strip www. prefix
    if netloc.startswith('www.'):
        netloc = netloc[4:]
    
    # Strip tracking params from query string
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=False)
        clean_params = {
            k: v for k, v in params.items()
            if k.lower() not in TRACKING_PARAMS
        }
        query = urlencode(clean_params, doseq=True)
    else:
        query = ''
    
    # Rebuild: no fragment, trailing slash normalized
    path = parsed.path.rstrip('/') or '/'
    
    return urlunparse((scheme, netloc, path, parsed.params, query, ''))
