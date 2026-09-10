import os
import json
import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "vargani_db")
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data_store.json')

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
    "qr_code_url": "/static/images/default_qr.png",
    "address": "गणेश चौक, मुख्य रस्ता, पुणे"
}

DEFAULT_GALLERY = [
    {
        "_id": "default_1",
        "title": "मागील वर्षातील भव्य श्री गणेश विसर्जन सोहळा २०२५",
        "image_url": "https://images.unsplash.com/photo-1601058268499-e52658b8bb88?auto=format&fit=crop&w=600&q=60",
        "type": "photo",
        "display_order": 1,
        "year": "2025"
    },
    {
        "_id": "default_2",
        "title": "श्रींची आकर्षक आरास व महापूजा",
        "image_url": "https://images.unsplash.com/photo-1620766182966-c6eb5ed2b788?auto=format&fit=crop&w=600&q=60",
        "type": "photo",
        "display_order": 2,
        "year": "2025"
    }
]

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
    t = threading.Thread(target=_bg_github_sync, daemon=True)
    t.start()

def load_json_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data and isinstance(data, dict):
                    return data
        except Exception as e:
            print(f"Error reading data_store.json: {e}")
    
    init_data = {
        "settings": DEFAULT_SETTINGS.copy(),
        "gallery": DEFAULT_GALLERY.copy(),
        "vargani_records": []
    }
    save_json_data(init_data)
    return init_data

def save_json_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        trigger_github_sync()
    except Exception as e:
        print(f"Error saving data_store.json: {e}")

def get_db():
    if "mongodb+srv" in MONGO_URI or ("mongodb://" in MONGO_URI and "localhost" not in MONGO_URI):
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=4000,
            tls=True,
            tlsAllowInvalidCertificates=True
        )
    else:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=200)
    return client[DB_NAME]

def init_db():
    local_data = load_json_data()
    try:
        db = get_db()
        if db.settings.count_documents({}) == 0:
            db.settings.insert_one(local_data.get("settings", DEFAULT_SETTINGS.copy()))
        try:
            db.gallery.create_index([("display_order", 1)])
            db.gallery.create_index([("created_at", -1)])
            db.vargani_records.create_index([("created_at", -1)])
            db.vargani_records.create_index([("receipt_no", 1)])
        except Exception as idx_err:
            print(f"MongoDB Index Info: {idx_err}")
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

    return record

def get_all_vargani(status=None, search=None):
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
        if records:
            return records
    except Exception as e:
        print(f"MongoDB read all vargani fail: {e}")

    local_data = load_json_data()
    records = local_data.get("vargani_records", [])
    if status and status != "All":
        records = [r for r in records if r.get("status") == status]
    if search:
        s = search.lower()
        records = [r for r in records if s in r.get("name", "").lower() or s in r.get("mobile", "").lower() or s in r.get("receipt_no", "").lower()]
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
    return True

def get_stats():
    records = get_all_vargani()
    total_collected = sum(int(r.get("amount", 0)) for r in records if r.get("status") == "Verified")
    pending_amount = sum(int(r.get("amount", 0)) for r in records if r.get("status") in ["Pending", "Pending Cash"])
    total_donors = len(records)
    verified_count = len([r for r in records if r.get("status") == "Verified"])
    pending_count = len([r for r in records if r.get("status") in ["Pending", "Pending Cash"]])
    cash_pending_count = len([r for r in records if r.get("status") == "Pending Cash"])
    return {
        "total_collected": total_collected,
        "pending_amount": pending_amount,
        "total_donors": total_donors,
        "verified_count": verified_count,
        "pending_count": pending_count,
        "cash_pending_count": cash_pending_count
    }

def get_gallery():
    items = []
    try:
        db = get_db()
        items = list(db.gallery.find({}))
        for item in items:
            item["_id"] = str(item["_id"])
    except Exception as e:
        print(f"MongoDB get_gallery info: {e}")
    
    if not items:
        local_data = load_json_data()
        items = local_data.get("gallery", [])

    valid_items = []
    for idx, item in enumerate(items):
        img_url = item.get("image_url", "").strip()
        if not img_url:
            continue
        # Filter out non-existent local upload files
        if img_url.startswith("/static/uploads/"):
            filename = img_url.replace("/static/uploads/", "")
            upload_dir = os.path.join(os.path.dirname(__file__), "static", "uploads")
            if not os.path.exists(os.path.join(upload_dir, filename)):
                continue
        # Filter out broken unsplash test URLs
        if "photo-1567157577867" in img_url or "photo-1609102026400" in img_url:
            continue

        if "display_order" not in item or item["display_order"] is None:
            item["display_order"] = idx + 1
        if "type" not in item:
            item["type"] = "photo"
        valid_items.append(item)

    if not valid_items:
        valid_items = DEFAULT_GALLERY.copy()

    valid_items.sort(key=lambda x: (int(x.get("display_order", 9999)), str(x.get("created_at", ""))))
    return valid_items

def add_gallery_item(title, image_url, media_type="photo", year="2026", mime_type=None, thumbnail_url=None):
    existing_items = get_gallery()
    max_order = max([int(i.get("display_order", 0)) for i in existing_items], default=0)
    new_order = max_order + 1

    item_id = f"item_{int(datetime.datetime.now().timestamp())}"
    item = {
        "_id": item_id,
        "title": title.strip(),
        "image_url": image_url.strip(),
        "type": media_type,
        "mime_type": mime_type or ("video/mp4" if media_type == "video" else "image/jpeg"),
        "thumbnail_url": thumbnail_url or (image_url if media_type == "photo" else ""),
        "display_order": new_order,
        "year": year,
        "is_active": True,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        db = get_db()
        db_item = item.copy()
        db_item["_id"] = ObjectId()
        res = db.gallery.insert_one(db_item)
        item["_id"] = str(res.inserted_id)
    except Exception as e:
        print(f"MongoDB add_gallery_item error: {e}")

    local_data = load_json_data()
    gallery = local_data.get("gallery", [])
    gallery.append(item)
    local_data["gallery"] = gallery
    save_json_data(local_data)

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
        for item in reordered_list:
            item_id = item["_id"]
            new_order = item["display_order"]
            if len(item_id) == 24:
                try:
                    db.gallery.update_one({"_id": ObjectId(item_id)}, {"$set": {"display_order": new_order}})
                except Exception:
                    pass
            db.gallery.update_one({"_id": item_id}, {"$set": {"display_order": new_order}})
    except Exception as e:
        print(f"MongoDB reorder error: {e}")

    local_data = load_json_data()
    local_data["gallery"] = reordered_list
    save_json_data(local_data)
    
    return reordered_list

def delete_gallery_item(item_id):
    try:
        db = get_db()
        if len(item_id) == 24:
            try:
                db.gallery.delete_one({"_id": ObjectId(item_id)})
            except Exception:
                pass
        db.gallery.delete_one({"_id": item_id})
    except Exception as e:
        print(f"MongoDB delete_gallery_item error: {e}")

    local_data = load_json_data()
    gallery = local_data.get("gallery", [])
    new_gallery = [g for g in gallery if str(g.get("_id")) != str(item_id)]
    
    for idx, item in enumerate(new_gallery):
        item["display_order"] = idx + 1
        try:
            db = get_db()
            g_id = str(item.get("_id", ""))
            if len(g_id) == 24:
                try:
                    db.gallery.update_one({"_id": ObjectId(g_id)}, {"$set": {"display_order": idx + 1}})
                except Exception:
                    pass
            db.gallery.update_one({"_id": g_id}, {"$set": {"display_order": idx + 1}})
        except Exception:
            pass

    local_data["gallery"] = new_gallery
    save_json_data(local_data)
    return True

def get_settings():
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
            if "entrance_photo_url" not in settings or not settings["entrance_photo_url"] or "photo-1567157577867" in settings.get("entrance_photo_url", ""):
                settings["entrance_photo_url"] = "https://images.unsplash.com/photo-1601058268499-e52658b8bb88?auto=format&fit=crop&w=1200&q=80"
            if "qr_code_url" not in settings or not settings["qr_code_url"]:
                settings["qr_code_url"] = "/static/images/default_qr.png"
            return settings
    except Exception as e:
        print(f"MongoDB get_settings error: {e}")

    local_data = load_json_data()
    st = local_data.get("settings", DEFAULT_SETTINGS.copy())
    if not st.get("mandal_name"): st["mandal_name"] = DEFAULT_SETTINGS["mandal_name"]
    if not st.get("tagline"): st["tagline"] = DEFAULT_SETTINGS["tagline"]
    if "entrance_photo_url" not in st or not st["entrance_photo_url"] or "photo-1567157577867" in st.get("entrance_photo_url", ""):
        st["entrance_photo_url"] = "https://images.unsplash.com/photo-1601058268499-e52658b8bb88?auto=format&fit=crop&w=1200&q=80"
    return st

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
