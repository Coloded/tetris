"""One-shot country lookup; raw IPs and provider credentials are not persisted."""
import ipaddress
import json
import os
from pathlib import Path
import httpx

COUNTRIES=json.loads((Path(__file__).resolve().parents[1]/'public/countries.json').read_text())
IPINFO_TOKEN=os.environ.get('IPINFO_TOKEN','')

def client_ip(request):
    # Uvicorn runs with --no-proxy-headers; only our local Nginx can set this.
    host=request.client.host if request.client else ''
    if host in ('127.0.0.1','::1'):
        host=request.headers.get('x-real-ip','')
    try:
        ip=ipaddress.ip_address(host)
        if isinstance(ip,ipaddress.IPv6Address) and ip.ipv4_mapped: ip=ip.ipv4_mapped
        return str(ip) if ip.is_global else None
    except ValueError:
        return None

def country_for_ip(ip):
    if not ip or not IPINFO_TOKEN: return None
    try:
        # Header authentication avoids putting the provider token in the URL.
        response=httpx.get(f'https://api.ipinfo.io/lite/{ip}',
                           headers={'Authorization':f'Bearer {IPINFO_TOKEN}'},timeout=3)
        response.raise_for_status()
        code=response.json().get('country_code')
        return code if isinstance(code,str) and code in COUNTRIES else None
    except (httpx.HTTPError,ValueError,AttributeError):
        return None
