import os
import json
import time
import hashlib
import urllib.request
import urllib.parse
import mimetypes

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")
CLOUDINARY_UPLOAD_PRESET = os.getenv("CLOUDINARY_UPLOAD_PRESET", "ganpati_mandal")

cloudinary_url = os.getenv("CLOUDINARY_URL", "")
if cloudinary_url and "@" in cloudinary_url:
    try:
        clean_url = cloudinary_url.replace("cloudinary://", "")
        parts = clean_url.split("@")
        keys = parts[0].split(":")
        CLOUDINARY_API_KEY = keys[0]
        CLOUDINARY_API_SECRET = keys[1]
        CLOUDINARY_CLOUD_NAME = parts[1]
    except Exception as e:
        print(f"Cloudinary URL parse info: {e}")

def is_cloudinary_configured():
    return bool(CLOUDINARY_CLOUD_NAME and (CLOUDINARY_API_KEY or CLOUDINARY_UPLOAD_PRESET))

def get_cloud_config():
    return {
        "is_configured": is_cloudinary_configured(),
        "cloud_name": CLOUDINARY_CLOUD_NAME,
        "upload_preset": CLOUDINARY_UPLOAD_PRESET
    }

def delete_cloud_media(public_id_or_url, resource_type="image"):
    """
    Permanently delete asset from Cloudinary storage & CDN cache.
    """
    if not is_cloudinary_configured() or not CLOUDINARY_API_KEY or not CLOUDINARY_API_SECRET:
        return False

    public_id = public_id_or_url
    if "res.cloudinary.com" in public_id_or_url:
        try:
            # Extract public_id from Cloudinary URL
            # Example: https://res.cloudinary.com/cloud/image/upload/v12345/ganpati/abc.webp
            parts = public_id_or_url.split("/upload/")
            if len(parts) > 1:
                sub = parts[1]
                # Remove version tag if present e.g. v1234567/
                if sub.startswith("v") and "/" in sub:
                    sub = sub.split("/", 1)[1]
                public_id = sub.rsplit(".", 1)[0]
        except Exception as ex:
            print(f"Error parsing public_id from URL: {ex}")

    if not public_id:
        return False

    try:
        timestamp = int(time.time())
        to_sign = f"public_id={public_id}&timestamp={timestamp}{CLOUDINARY_API_SECRET}"
        signature = hashlib.sha1(to_sign.encode('utf-8')).hexdigest()

        url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/{resource_type}/destroy"
        data = urllib.parse.urlencode({
            "public_id": public_id,
            "timestamp": timestamp,
            "api_key": CLOUDINARY_API_KEY,
            "signature": signature,
            "invalidate": "true"
        }).encode('utf-8')

        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            res_json = json.loads(resp.read().decode('utf-8'))
            print(f"Cloudinary destroy response for {public_id}: {res_json}")
            return res_json.get("result") in ["ok", "not found"]
    except Exception as e:
        print(f"Cloudinary deletion error: {e}")
        return False

def generate_video_poster_url(video_url):
    """
    Generate optimized video poster preview from Cloudinary or YouTube.
    """
    if not video_url:
        return ""
    if "youtube.com" in video_url or "youtu.be" in video_url:
        import re
        m = re.search(r'(?:v=|\/shorts\/|\/embed\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', video_url)
        if m:
            return f"https://img.youtube.com/vi/{m.group(1)}/hqdefault.jpg"
    elif "res.cloudinary.com" in video_url and "/video/upload/" in video_url:
        # Convert video upload URL to jpg poster preview
        poster_url = video_url.replace("/video/upload/", "/video/upload/so_0,w_800,c_limit,q_auto,f_jpg/")
        return poster_url.rsplit(".", 1)[0] + ".jpg"
    return ""
