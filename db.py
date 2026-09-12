import os
import json
import datetime
import tempfile
import time
from pymongo import MongoClient
import gridfs
from bson.objectid import ObjectId
from cloud_storage import delete_cloud_media, generate_video_poster_url

MONGO_URI = (
    os.getenv("MONGO_URI") or 
    os.getenv("MONGODB_URI") or 
    os.getenv("MONGO_URL") or 
    os.getenv("DATABASE_URL") or 
    "mongodb://localhost:27017/"
)
DB_NAME = os.getenv("DB_NAME", "vargani_db")
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data_store.json')

_CACHE = {}
_CACHE_TTL = 10  # 10 seconds TTL for fast updates
_MONGO_CHECK_FAILED_UNTIL = 0

def get_cached(key):
    if key in _CACHE:
        val, ts = _CACHE[key]
        if datetime.datetime.now().timestamp() - ts < _CACHE_TTL:
            return val
    return None

def set_cached(key, val):
    _CACHE[key] = (val, datetime.datetime.now().timestamp())

def invalidate_cache(key=None):
    if key:
        _CACHE.pop(key, None)
    else:
        _CACHE.clear()

DEFAULT_SETTINGS = {
    "mandal_name": "श्री गणेशोत्सव मित्र मंडळ, पुणे",
    "tagline": "वर्गणी संकलन व ऑनलाईन डिजिटल पावती प्रणाली २०२६",
    "entrance_shloka": "🚩 ॐ गं गणपतये नमः 🚩",
    "entrance_photo_url": "https://images.unsplash.com/photo-1601058268499-e52658b8bb88?auto=format&fit=crop&w=1200&q=80",
    "upi_id": "mandalganpati@upi",
    "receiver_name": "Shri Ganeshotsav Mandal",
    "phone_number": "7756806580",
    "admin_mobile": "7756806580",
    "contact_name2": "वर्गणी व पावती प्रमुख",
    "contact_phone2": "9876543210",
    "contact_name3": "खजिनदार (Treasurer)",
    "contact_phone3": "9822114455",
    "qr_code_url": "/static/uploads/qr_1788865307_WhatsApp_Image_2026-08-19_at_1.11.21_PM.jpeg",
    "address": "गणेश चौक, मुख्य रस्ता, पुणे"
}

DEFAULT_GALLERY = []

def amount_to_marathi_words(amount):
    try:
        num = int(amount)
    except Exception:
        return f"{amount} रुपये फक्त"

    if num <= 0:
        return "शून्य रुपये"

    units = {
        0: "", 1: "एक", 2: "दोन", 3: "तीन", 4: "चार", 5: "पाच", 6: "सहा", 7: "सात", 8: "आठ", 9: "नऊ", 10: "दहा",
        11: "अकरा", 12: "बारा", 13: "तेरा", 14: "चौदा", 15: "पंधरा", 16: "सोळा", 17: "सतरा", 18: "अठरा", 19: "एकोणीस", 20: "वीस",
        21: "एकवीस", 22: "बावीस", 23: "तेवीस", 24: "चोवीस", 25: "पंचवीस", 26: "सव्वीस", 27: "सत्तावीस", 28: "अठ्ठावीस", 29: "एकोणतीस", 30: "तीस",
        31: "एकतीस", 32: "बत्तीस", 33: "तेत्तीस", 34: "चौतीस", 35: "तीसपाच", 36: "छत्तीस", 37: "सदतीस", 38: "अडतीस", 39: "एकोणचाळीस", 40: "चाळीस",
        41: "एकचाळीस", 42: "बेचाळीस", 43: "त्र्याचाळीस", 44: "चौचाळीस", 45: "पंचेचाळीस", 46: "सेचाळीस", 47: "सत्ताचाळीस", 48: "अठ्ठाचाळीस", 49: "एकोणपन्नास", 50: "पन्नास",
        51: "एकपन्नास", 52: "बावन्न", 53: "त्रिपन्न", 54: "चौपन्न", 55: "पंचावन्न", 56: "छप्पन्न", 57: "सत्तावन्न", 58: "अठ्ठावन्न", 59: "एकोणसाठ", 60: "साठ",
        61: "एकसाठ", 62: "बासाठ", 63: "त्रैसाठ", 64: "चौसाठ", 65: "पासष्ठ", 66: "सहासाठ", 67: "सतसाठ", 68: "अडसाठ", 69: "एकोणसत्तर", 70: "सत्तर",
        71: "एकहत्तर", 72: "बाहत्तर", 73: "त्र्याहत्तर", 74: "चौहत्तर", 75: "पंचहत्तर", 76: "शहात्तर", 77: "सतहत्तर", 78: "अठ्ठहत्तर", 79: "एकोणऐंशी", 80: "ऐंशी",
        81: "एकऐंशी", 82: "ब्याऐंशी", 83: "त्र्याऐंशी", 84: "चौऱ्याऐंशी", 85: "पंच्याऐंशी", 86: "शहाऐंशी", 87: "सत्त्याऐंशी", 88: "अठ्ठ्याऐंशी", 89: "एकोणनव्वद", 90: "नव्वद",
        91: "एकनव्वद", 92: "ब्यानव्वद", 93: "त्र्यानव्वद", 94: "चौऱ्यानव्वद", 95: "पंच्यानव्वद", 96: "शहानव्वद", 97: "सत्त्यानव्वद", 98: "अठ्ठ्यानव्वद", 99: "नव्व्यानव्वद"
    }

    def convert_below_thousand(n):
        if n == 0:
            return ""
        if n < 100:
            return units.get(n, str(n))
        h = n // 100
        rem = n % 100
        h_str = "एकशे" if h == 1 else f"{units.get(h, '')}शे"
        rem_str = units.get(rem, str(rem)) if rem > 0 else ""
        return f"{h_str} {rem_str}".strip()

    parts = []
    lakh = num // 100000
    num %= 100000
    if lakh > 0:
        parts.append(f"{convert_below_thousand(lakh)} लाख")

    thousand = num // 1000
    num %= 1000
    if thousand > 0:
        parts.append(f"{convert_below_thousand(thousand)} हजार")

    if num > 0:
        parts.append(convert_below_thousand(num))

    result = " ".join(parts).strip()
    return f"{result} रुपये फक्त"

import threading
import subprocess

_sync_lock = threading.Lock()

def _bg_github_sync():
    if not _sync_lock.acquire(blocking=False):
        return
    try:
        subprocess.run(["git", "add", DATA_FILE], capture_output=True)
        res = subprocess.run(["git", "commit", "-m", "Auto-sync persistent data_store.json updates"], capture_output=True, text=True)
        if "nothing to commit" not in res.stdout and "no changes added" not in res.stdout:
            subprocess.run(["git", "push", "origin", "main"], capture_output=True)
            print("✅ Auto-synced data_store.json to GitHub repository!")
    except Exception as e:
        print(f"Git auto-sync info: {e}")
    finally:
        _sync_lock.release()

def trigger_github_sync():
    if os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID") or os.getenv("VERCEL") or os.getenv("VERCEL_ENV") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return
    t = threading.Thread(target=_bg_github_sync, daemon=True)
    t.start()

def get_target_data_file():
    local_file = os.path.join(os.path.dirname(__file__), 'data_store.json')
    tmp_file = os.path.join(tempfile.gettempdir(), 'data_store.json')

    try:
        if os.path.exists(local_file):
            with open(local_file, 'a', encoding='utf-8'):
                pass
            return local_file
    except (OSError, IOError):
        pass

    if not os.path.exists(tmp_file) and os.path.exists(local_file):
        try:
            with open(local_file, 'r', encoding='utf-8') as rf:
                content = rf.read()
            with open(tmp_file, 'w', encoding='utf-8') as wf:
                wf.write(content)
        except Exception as copy_err:
            print(f"Copy data_store.json to tmp warning: {copy_err}")

    return tmp_file if os.path.exists(tmp_file) or not os.path.exists(local_file) else local_file

def load_json_data():
    target_file = get_target_data_file()
    if os.path.exists(target_file):
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data and isinstance(data, dict):
                    return data
        except Exception as e:
            print(f"Error reading {target_file}: {e}")

    local_file = os.path.join(os.path.dirname(__file__), 'data_store.json')
    if os.path.exists(local_file):
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data and isinstance(data, dict):
                    return data
        except Exception as e:
            print(f"Error reading local data_store.json: {e}")

    init_data = {
        "settings": DEFAULT_SETTINGS.copy(),
        "gallery": DEFAULT_GALLERY.copy(),
        "vargani_records": []
    }
    save_json_data(init_data)
    return init_data

def save_json_data(data):
    target_file = get_target_data_file()
    try:
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        if target_file == os.path.join(os.path.dirname(__file__), 'data_store.json'):
            trigger_github_sync()
    except Exception as e:
        print(f"Error saving data_store.json: {e}")

_CLIENT = None
_DB_INITIALIZED = False

def get_db():
    global _CLIENT, _MONGO_CHECK_FAILED_UNTIL
    # On Vercel / serverless without remote URI, avoid localhost connection attempts completely
    if (os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")) and ("localhost" in MONGO_URI or "127.0.0.1" in MONGO_URI):
        return None

    if time.time() < _MONGO_CHECK_FAILED_UNTIL:
        return None

    if _CLIENT is None:
        try:
            if "mongodb+srv" in MONGO_URI or ("mongodb://" in MONGO_URI and "localhost" not in MONGO_URI):
                _CLIENT = MongoClient(
                    MONGO_URI,
                    serverSelectionTimeoutMS=6000,
                    connectTimeoutMS=6000,
                    socketTimeoutMS=10000,
                    maxPoolSize=10,
                    minPoolSize=0,
                    tls=True,
                    tlsAllowInvalidCertificates=True,
                    retryWrites=True
                )
            else:
                _CLIENT = MongoClient(MONGO_URI, serverSelectionTimeoutMS=500, connectTimeoutMS=500)
        except Exception as e:
            _MONGO_CHECK_FAILED_UNTIL = time.time() + 5
            print(f"MongoClient init exception: {e}")
            return None
    try:
        return _CLIENT[DB_NAME]
    except Exception as e:
        _MONGO_CHECK_FAILED_UNTIL = time.time() + 5
        print(f"MongoDB DB access exception: {e}")
        return None

def get_gridfs():
    db = get_db()
    if db is None:
        return None
    try:
        return gridfs.GridFS(db)
    except Exception as e:
        print(f"GridFS init exception: {e}")
        return None

def save_media_to_db(data_bytes, filename="media.webp", content_type="image/webp"):
    """
    Saves media binary directly into MongoDB Atlas.
    Dual-Tier:
      1. GridFS for large media/streaming
      2. Fallback to db.media_store BSON collection
    Returns media_id string or None.
    """
    try:
        fs = get_gridfs()
        if fs is not None:
            file_id = fs.put(data_bytes, filename=filename, content_type=content_type)
            print(f"💾 Successfully saved media to MongoDB GridFS with id: {file_id}")
            return str(file_id)
    except Exception as e:
        print(f"GridFS save warning: {e}")

    # Fallback to direct BSON binary storage in db.media_store
    try:
        db_conn = get_db()
        if db_conn is not None:
            doc = {
                "filename": filename,
                "content_type": content_type,
                "data": data_bytes,
                "length": len(data_bytes),
                "created_at": datetime.datetime.now()
            }
            res = db_conn.media_store.insert_one(doc)
            print(f"💾 Successfully saved media to MongoDB media_store with id: {res.inserted_id}")
            return str(res.inserted_id)
    except Exception as d_err:
        print(f"media_store save warning: {d_err}")

    return None

def get_media_from_db(media_id):
    """
    Retrieves media from MongoDB Atlas GridFS or fallback db.media_store.
    Returns (readable_stream_or_obj, content_type, filename, length) or None.
    """
    media_id_str = str(media_id).strip()
    try:
        fs = get_gridfs()
        if fs is not None and len(media_id_str) == 24:
            obj_id = ObjectId(media_id_str)
            if fs.exists(obj_id):
                grid_out = fs.get(obj_id)
                content_type = getattr(grid_out, 'content_type', None) or 'application/octet-stream'
                filename = getattr(grid_out, 'filename', None) or 'file'
                length = grid_out.length
                return grid_out, content_type, filename, length
    except Exception as e:
        pass

    # Fallback lookup in db.media_store
    try:
        db_conn = get_db()
        if db_conn is not None:
            doc = None
            if len(media_id_str) == 24:
                try:
                    doc = db_conn.media_store.find_one({"_id": ObjectId(media_id_str)})
                except Exception:
                    pass
            if not doc:
                doc = db_conn.media_store.find_one({"_id": media_id_str})
            if doc and "data" in doc:
                import io
                bio = io.BytesIO(doc["data"])
                return bio, doc.get("content_type", "image/webp"), doc.get("filename", "file"), doc.get("length", len(doc["data"]))
    except Exception as m_err:
        print(f"media_store read warning: {m_err}")

    return None

def delete_media_from_db(media_id):
    """
    Permanently deletes media binary from MongoDB Atlas GridFS and db.media_store.
    """
    media_id_str = str(media_id).strip()
    deleted = False
    try:
        fs = get_gridfs()
        if fs is not None and len(media_id_str) == 24:
            obj_id = ObjectId(media_id_str)
            if fs.exists(obj_id):
                fs.delete(obj_id)
                deleted = True
    except Exception:
        pass

    try:
        db_conn = get_db()
        if db_conn is not None:
            if len(media_id_str) == 24:
                try:
                    db_conn.media_store.delete_one({"_id": ObjectId(media_id_str)})
                    deleted = True
                except Exception:
                    pass
            db_conn.media_store.delete_one({"_id": media_id_str})
    except Exception:
        pass

    return deleted

def _create_indexes_async():
    try:
        db = get_db()
        if db is not None:
            db.gallery.create_index([("display_order", 1)])
            db.gallery.create_index([("created_at", -1)])
            db.vargani_records.create_index([("created_at", -1)])
            db.vargani_records.create_index([("receipt_no", 1)])
    except Exception as idx_err:
        pass

def init_db():
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return
    _DB_INITIALIZED = True
    
    local_data = load_json_data()
    try:
        db = get_db()
        if db is not None:
            if db.settings.find_one({}) is None:
                db.settings.insert_one(local_data.get("settings", DEFAULT_SETTINGS.copy()))
            t = threading.Thread(target=_create_indexes_async, daemon=True)
            t.start()
            print("Database initialized successfully!")
    except Exception as e:
        print(f"MongoDB Init Info: {e}")

def generate_receipt_no():
    records = get_all_vargani()
    count = len(records) + 1
    receipt_no = f"VRG-2026-{count:04d}"
    existing_nos = {r.get("receipt_no") for r in records}
    while receipt_no in existing_nos:
        count += 1
        receipt_no = f"VRG-2026-{count:04d}"
    return receipt_no

def add_vargani(data):
    rec_id = f"rec_{int(datetime.datetime.now().timestamp())}"
    now_str = datetime.datetime.now().strftime("%d-%m-%Y %I:%M %p")
    record = {
        "_id": rec_id,
        "receipt_no": generate_receipt_no(),
        "name": data.get("name", "").strip(),
        "mobile": data.get("mobile", "").strip(),
        "address": data.get("address", "").strip(),
        "amount": int(data.get("amount", 0)),
        "payment_mode": data.get("payment_mode", "Cash"),
        "transaction_id": data.get("transaction_id", "").strip(),
        "status": data.get("status", "Pending"),
        "screenshot_url": data.get("screenshot_url", ""),
        "created_at_str": now_str,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        db = get_db()
        db_rec = record.copy()
        db_rec["_id"] = ObjectId()
        res = db.vargani_records.insert_one(db_rec)
        record["_id"] = str(res.inserted_id)
    except Exception as e:
        print(f"MongoDB record insert fail: {e}")

    local_data = load_json_data()
    v_recs = local_data.get("vargani_records", [])
    v_recs.insert(0, record)
    local_data["vargani_records"] = v_recs
    save_json_data(local_data)
    invalidate_cache()

    return record

def get_all_vargani(status=None, search=None):
    cached_key = f"vargani_{status}_{search}"
    cached_res = get_cached(cached_key)
    if cached_res is not None:
        return cached_res

    # Fast-path: derive status filter from cached all-records if available
    if status and not search:
        all_cached = get_cached("vargani_None_None")
        if all_cached is not None:
            filtered = [r for r in all_cached if r.get("status") == status] if status != "All" else list(all_cached)
            set_cached(cached_key, filtered)
            return filtered

    records = []
    try:
        db = get_db()
        query = {}
        if status and status != "All":
            query["status"] = status
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"mobile": {"$regex": search, "$options": "i"}},
                {"receipt_no": {"$regex": search, "$options": "i"}},
                {"transaction_id": {"$regex": search, "$options": "i"}}
            ]
        m_recs = list(db.vargani_records.find(query).sort("created_at", -1))
        for r in m_recs:
            r["_id"] = str(r["_id"])
            if isinstance(r.get("created_at"), datetime.datetime):
                r["created_at_str"] = r["created_at"].strftime("%d-%m-%Y %I:%M %p")
            records.append(r)
    except Exception as e:
        print(f"MongoDB read all vargani fail: {e}")

    if not records:
        local_data = load_json_data()
        records = local_data.get("vargani_records", [])
        if status and status != "All":
            records = [r for r in records if r.get("status") == status]
        if search:
            s = search.lower()
            records = [r for r in records if s in r.get("name", "").lower() or s in r.get("mobile", "").lower() or s in r.get("receipt_no", "").lower()]

    # Guarantee strict reverse-chronological sorting (Latest donation at the VERY TOP #1)
    records.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    set_cached(cached_key, records)
    return records

def get_vargani_by_receipt_no(receipt_no):
    records = get_all_vargani()
    for r in records:
        if r.get("receipt_no") == receipt_no or str(r.get("_id")) == str(receipt_no):
            r["name"] = r.get("name") or "वर्गणीदार भाविक"
            r["mobile"] = r.get("mobile") or "नमुद नाही"
            r["address"] = r.get("address") or "नमुद नाही"
            r["amount"] = r.get("amount", 0)
            r["amount_in_words"] = amount_to_marathi_words(r.get("amount", 0))
            r["payment_mode"] = r.get("payment_mode") or "Cash"
            r["transaction_id"] = r.get("transaction_id") or ("रोख जमा (Cash)" if "Cash" in r.get("payment_mode", "") else "नमुद नाही")
            return r
    return None

def verify_vargani(record_id):
    try:
        db = get_db()
        if len(record_id) == 24:
            db.vargani_records.update_one({"_id": ObjectId(record_id)}, {"$set": {"status": "Verified"}})
        else:
            db.vargani_records.update_one({"_id": record_id}, {"$set": {"status": "Verified"}})
    except Exception as e:
        print(f"MongoDB verify error: {e}")

    local_data = load_json_data()
    recs = local_data.get("vargani_records", [])
    updated_rec = None
    for r in recs:
        if str(r.get("_id")) == str(record_id) or r.get("receipt_no") == record_id:
            r["status"] = "Verified"
            updated_rec = r
            break
    save_json_data(local_data)
    
    if not updated_rec:
        updated_rec = get_vargani_by_receipt_no(record_id)
        if updated_rec:
            updated_rec["status"] = "Verified"
    invalidate_cache()
    return updated_rec

def delete_vargani(record_id):
    try:
        db = get_db()
        if len(record_id) == 24:
            db.vargani_records.delete_one({"_id": ObjectId(record_id)})
        else:
            db.vargani_records.delete_one({"_id": record_id})
    except Exception as e:
        print(f"MongoDB delete record error: {e}")

    local_data = load_json_data()
    recs = local_data.get("vargani_records", [])
    new_recs = [r for r in recs if str(r.get("_id")) != str(record_id) and r.get("receipt_no") != record_id]
    local_data["vargani_records"] = new_recs
    save_json_data(local_data)
    invalidate_cache()
    return True

def get_stats():
    cached_res = get_cached("stats")
    if cached_res is not None:
        return cached_res
    records = get_all_vargani()
    total_collected = sum(int(r.get("amount", 0)) for r in records if r.get("status") == "Verified")
    pending_amount = sum(int(r.get("amount", 0)) for r in records if r.get("status") in ["Pending", "Pending Cash"])
    total_donors = len(records)
    verified_count = len([r for r in records if r.get("status") == "Verified"])
    pending_count = len([r for r in records if r.get("status") in ["Pending", "Pending Cash"]])
    cash_pending_count = len([r for r in records if r.get("status") == "Pending Cash"])
    res = {
        "total_collected": total_collected,
        "pending_amount": pending_amount,
        "total_donors": total_donors,
        "verified_count": verified_count,
        "pending_count": pending_count,
        "cash_pending_count": cash_pending_count
    }
    set_cached("stats", res)
    return res

import re

def to_youtube_embed_url(url):
    if not url:
        return url
    url_str = str(url).strip()
    if 'youtube.com' not in url_str and 'youtu.be' not in url_str:
        return url_str

    m = re.search(r'(?:v=|\/shorts\/|\/embed\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', url_str)
    if m:
        video_id = m.group(1)
        return f"https://www.youtube.com/embed/{video_id}?playsinline=1&rel=0&enablejsapi=1"
    return url_str

def get_gallery():
    cached_res = get_cached("gallery")
    if cached_res is not None:
        return cached_res
    
    items = []
    mongo_ok = False
    try:
        db = get_db()
        if db is not None:
            items = list(db.gallery.find({}))
            for item in items:
                item["_id"] = str(item["_id"])
            mongo_ok = True
    except Exception as e:
        print(f"MongoDB get_gallery info: {e}")

    if not mongo_ok:
        local_data = load_json_data()
        items = local_data.get("gallery", [])
        if not items and not local_data.get("gallery_user_modified"):
            items = DEFAULT_GALLERY.copy()

    valid_items = []
    for idx, item in enumerate(items):
        if not item or not isinstance(item, dict):
            continue
        img_url = str(item.get("image_url", "")).strip()
        if not img_url:
            continue

        # SANITIZATION: Eliminate giant inline Base64 (>5000 chars) that bloat payloads
        if img_url.startswith("data:") and len(img_url) > 5000:
            continue

        # Check static uploads existence ONLY when running locally (not on Vercel/serverless)
        if img_url.startswith("/static/uploads/") and not img_url.startswith("data:"):
            filename = img_url.replace("/static/uploads/", "")
            local_dir = os.path.join(os.path.dirname(__file__), "static", "uploads")
            tmp_dir = os.path.join(tempfile.gettempdir(), "uploads")
            
            local_exists = os.path.exists(os.path.join(local_dir, filename))
            tmp_exists = os.path.exists(os.path.join(tmp_dir, filename))
            
            if not local_exists and not tmp_exists and not (os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")):
                continue

        # Filter out broken unsplash test URLs
        if "photo-1567157577867" in img_url or "photo-1609102026400" in img_url:
            continue

        if "youtube.com" in img_url or "youtu.be" in img_url:
            img_url = to_youtube_embed_url(img_url)
            item["image_url"] = img_url
            item["type"] = "video"
            if not item.get("thumbnail_url"):
                item["thumbnail_url"] = generate_video_poster_url(img_url)
        elif item.get("type") == "video" and not item.get("thumbnail_url"):
            item["thumbnail_url"] = generate_video_poster_url(img_url)

        if "display_order" not in item or item["display_order"] is None:
            item["display_order"] = idx + 1
        if "type" not in item:
            item["type"] = "photo"
        valid_items.append(item)

    valid_items.sort(key=lambda x: (int(x.get("display_order", 9999)), str(x.get("created_at", ""))))
    set_cached("gallery", valid_items)
    return valid_items

def add_gallery_item(title, image_url, media_type="photo", year="2025", mime_type="image/jpeg", thumbnail_url="", public_id=""):
    item_id = f"item_{int(datetime.datetime.now().timestamp())}"
    
    if media_type == "video" and not thumbnail_url:
        thumbnail_url = generate_video_poster_url(image_url)

    item = {
        "_id": item_id,
        "title": title.strip(),
        "image_url": image_url.strip(),
        "type": media_type,
        "mime_type": mime_type,
        "thumbnail_url": thumbnail_url.strip() if thumbnail_url else image_url.strip(),
        "public_id": public_id.strip() if public_id else "",
        "year": str(year).strip() or "2025",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        db = get_db()
        if db is not None:
            db_item = item.copy()
            db_item["_id"] = ObjectId()
            res = db.gallery.insert_one(db_item)
            item["_id"] = str(res.inserted_id)
    except Exception as e:
        print(f"MongoDB add_gallery_item error: {e}")

    local_data = load_json_data()
    gallery = local_data.get("gallery", [])
    gallery.insert(0, item)
    for idx, g in enumerate(gallery):
        g["display_order"] = idx + 1
    local_data["gallery"] = gallery
    local_data["gallery_user_modified"] = True
    save_json_data(local_data)
    invalidate_cache()

    return item

def reorder_gallery_items(ordered_ids):
    if not isinstance(ordered_ids, list):
        return False

    existing_items = get_gallery()
    items_by_id = {str(item["_id"]): item for item in existing_items}
    
    reordered_list = []
    order_counter = 1

    for item_id in ordered_ids:
        s_id = str(item_id)
        if s_id in items_by_id:
            item = items_by_id[s_id]
            item["display_order"] = order_counter
            reordered_list.append(item)
            del items_by_id[s_id]
            order_counter += 1

    for item in items_by_id.values():
        item["display_order"] = order_counter
        reordered_list.append(item)
        order_counter += 1

    try:
        db = get_db()
        if db is not None:
            for item in reordered_list:
                g_id = str(item.get("_id", "")).strip()
                if len(g_id) == 24:
                    try:
                        db.gallery.update_one({"_id": ObjectId(g_id)}, {"$set": {"display_order": item["display_order"]}})
                    except Exception:
                        pass
                db.gallery.update_one({"_id": g_id}, {"$set": {"display_order": item["display_order"]}})
    except Exception as e:
        print(f"MongoDB reorder error: {e}")

    local_data = load_json_data()
    local_data["gallery"] = reordered_list
    local_data["gallery_user_modified"] = True
    save_json_data(local_data)
    invalidate_cache()
    
    return reordered_list

def delete_gallery_item(item_id):
    """
    PERMANENT DELETION:
    1. Removes media from Cloudinary (if cloud-hosted).
    2. Physically unlinks file & thumbnail from disk (if locally stored).
    3. Deletes record from MongoDB and data_store.json.
    4. Re-indexes display_order so sequence never breaks.
    5. Invalidates cache immediately.
    """
    item_id_str = str(item_id).strip()

    # Find the target item directly in MongoDB Atlas or cached gallery to retrieve its URLs
    target_item = None
    try:
        db_conn = get_db()
        if db_conn is not None:
            if len(item_id_str) == 24:
                target_item = db_conn.gallery.find_one({"_id": ObjectId(item_id_str)})
            if not target_item:
                target_item = db_conn.gallery.find_one({"_id": item_id_str})
    except Exception as e:
        print(f"MongoDB target_item lookup error: {e}")

    if not target_item:
        existing_items = get_gallery()
        target_item = next((item for item in existing_items if str(item.get("_id")).strip() == item_id_str), None)

    if target_item:
        img_url = target_item.get("image_url", "")
        thumb_url = target_item.get("thumbnail_url", "")
        pub_id = target_item.get("public_id", "")
        m_type = target_item.get("type", "photo")
        res_type = "video" if m_type == "video" else "image"

        # 1. Cloud Deletion (Cloudinary)
        if pub_id or "res.cloudinary.com" in img_url:
            target_to_delete = pub_id if pub_id else img_url
            try:
                delete_cloud_media(target_to_delete, resource_type=res_type)
            except Exception as c_err:
                print(f"Cloud delete error: {c_err}")

        # 1.5 GridFS Deletion (MongoDB Atlas)
        for media_link in [img_url, thumb_url]:
            if media_link and "/api/media/" in media_link:
                try:
                    m_id = media_link.split("/api/media/")[1].split("?")[0].split("/")[0].strip()
                    if len(m_id) == 24:
                        delete_media_from_db(m_id)
                except Exception as g_err:
                    print(f"GridFS delete warning: {g_err}")

        # 2. Local Disk Physical Unlink
        for media_link in [img_url, thumb_url]:
            if media_link and media_link.startswith("/static/uploads/"):
                fname = os.path.basename(media_link)
                for folder in [
                    os.path.join(os.path.dirname(__file__), "static", "uploads"),
                    os.path.join(tempfile.gettempdir(), "uploads")
                ]:
                    fpath = os.path.join(folder, fname)
                    if os.path.exists(fpath):
                        try:
                            os.remove(fpath)
                            print(f"🗑️ Physically deleted file from disk: {fpath}")
                        except Exception as rm_err:
                            print(f"Warning unlinking file {fpath}: {rm_err}")

    # 3. Database Deletion (MongoDB)
    try:
        db = get_db()
        if db is not None:
            if len(item_id_str) == 24:
                try:
                    db.gallery.delete_one({"_id": ObjectId(item_id_str)})
                except Exception:
                    pass
            db.gallery.delete_one({"_id": item_id_str})
    except Exception as e:
        print(f"MongoDB delete_gallery_item error: {e}")

    # 4. JSON Storage Deletion
    local_data = load_json_data()
    gallery = local_data.get("gallery", [])
    new_gallery = [g for g in gallery if str(g.get("_id")).strip() != item_id_str]
    
    # 5. Re-index Display Orders
    for idx, item in enumerate(new_gallery):
        item["display_order"] = idx + 1
        try:
            db = get_db()
            if db is not None:
                g_id = str(item.get("_id", "")).strip()
                if len(g_id) == 24:
                    try:
                        db.gallery.update_one({"_id": ObjectId(g_id)}, {"$set": {"display_order": idx + 1}})
                    except Exception:
                        pass
                db.gallery.update_one({"_id": g_id}, {"$set": {"display_order": idx + 1}})
        except Exception:
            pass

    local_data["gallery"] = new_gallery
    local_data["gallery_user_modified"] = True
    save_json_data(local_data)
    invalidate_cache()
    return True

def get_settings():
    cached_res = get_cached("settings")
    if cached_res is not None:
        return cached_res

    settings = None
    try:
        db = get_db()
        settings = db.settings.find_one({})
        if settings:
            settings["_id"] = str(settings["_id"])
            if not settings.get("mandal_name"): settings["mandal_name"] = DEFAULT_SETTINGS["mandal_name"]
            if not settings.get("tagline"): settings["tagline"] = DEFAULT_SETTINGS["tagline"]
            if not settings.get("contact_name2"): settings["contact_name2"] = "वर्गणी व पावती प्रमुख"
            if not settings.get("contact_phone2"): settings["contact_phone2"] = "9876543210"
            if not settings.get("contact_name3"): settings["contact_name3"] = "खजिनदार (Treasurer)"
            if not settings.get("contact_phone3"): settings["contact_phone3"] = "9822114455"
            if not settings.get("entrance_shloka"): settings["entrance_shloka"] = "🚩 ॐ गं गणपतये नमः 🚩"
            
            # SANITIZE: Remove bloated inline base64 string (>10,000 chars) to prevent 6.5MB HTML payload
            photo_url = str(settings.get("entrance_photo_url", "")).strip()
            if len(photo_url) > 10000 or "photo-1567157577867" in photo_url or not photo_url:
                settings["entrance_photo_url"] = DEFAULT_SETTINGS["entrance_photo_url"]
                try:
                    db.settings.update_one({}, {"$set": {"entrance_photo_url": DEFAULT_SETTINGS["entrance_photo_url"]}})
                except Exception:
                    pass
            if "qr_code_url" not in settings or not settings["qr_code_url"]:
                settings["qr_code_url"] = "/static/images/default_qr.png"
    except Exception as e:
        print(f"MongoDB get_settings error: {e}")

    if not settings:
        local_data = load_json_data()
        settings = local_data.get("settings", DEFAULT_SETTINGS.copy())
        if not settings.get("mandal_name"): settings["mandal_name"] = DEFAULT_SETTINGS["mandal_name"]
        if not settings.get("tagline"): settings["tagline"] = DEFAULT_SETTINGS["tagline"]
        photo_url = str(settings.get("entrance_photo_url", "")).strip()
        if len(photo_url) > 10000 or "photo-1567157577867" in photo_url or not photo_url:
            settings["entrance_photo_url"] = DEFAULT_SETTINGS["entrance_photo_url"]

    set_cached("settings", settings)
    return settings

def update_settings(data):
    try:
        db = get_db()
        data["updated_at"] = datetime.datetime.now()
        db.settings.update_one({}, {"$set": data}, upsert=True)
    except Exception as e:
        print(f"MongoDB update_settings error: {e}")

    local_data = load_json_data()
    st = local_data.get("settings", DEFAULT_SETTINGS.copy())
    st.update(data)
    st["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    local_data["settings"] = st
    save_json_data(local_data)
    invalidate_cache()

    return get_settings()

def register_user_login(mobile):
    mobile = str(mobile).strip()
    if not mobile or len(mobile) < 10:
        return
    now_str = datetime.datetime.now().strftime("%d-%m-%Y %I:%M %p")
    user_entry = {
        "mobile": mobile,
        "last_login": now_str
    }
    
    try:
        db = get_db()
        db.users.update_one({"mobile": mobile}, {"$set": user_entry}, upsert=True)
    except Exception as e:
        print(f"MongoDB user register info: {e}")

    local_data = load_json_data()
    users = local_data.get("users", [])
    existing = False
    for u in users:
        if u.get("mobile") == mobile:
            u["last_login"] = now_str
            existing = True
            break
    if not existing:
        users.append(user_entry)
    local_data["users"] = users
    save_json_data(local_data)

def get_registered_users():
    unique_users = {}
    
    v_records = get_all_vargani()
    for r in v_records:
        m = r.get("mobile", "").strip()
        if m and len(m) >= 10:
            name = r.get("name", "वर्गणीदार")
            unique_users[m] = {"mobile": m, "name": name, "source": "वर्गणीदार"}

    try:
        db = get_db()
        db_users = list(db.users.find({}))
        for u in db_users:
            m = u.get("mobile", "").strip()
            if m and len(m) >= 10:
                if m not in unique_users:
                    unique_users[m] = {"mobile": m, "name": u.get("name", "भाविक"), "source": "लॉगिन भाविक"}
    except Exception as e:
        print(f"MongoDB get_registered_users info: {e}")

    local_data = load_json_data()
    local_users = local_data.get("users", [])
    for u in local_users:
        m = u.get("mobile", "").strip()
        if m and len(m) >= 10:
            if m not in unique_users:
                unique_users[m] = {"mobile": m, "name": u.get("name", "भाविक"), "source": "लॉगिन भाविक"}

    return list(unique_users.values())
