import os
import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "vargani_db")

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
    "address": "गणेश चौक, मुख्य रस्ता, पुणे",
    "updated_at": datetime.datetime.now()
}

SAMPLE_GALLERY = [
    {
        "_id": "1",
        "title": "गणेशोत्सव विसर्जन मिरवणूक व्हिडिओ २०२६",
        "image_url": "/static/uploads/vid_1788933034_WhatsApp_Video_2026-09-09_at_11.15.45_AM.mp4",
        "type": "video",
        "year": "2026"
    },
    {
        "_id": "2",
        "title": "मागील वर्षातील भव्य श्री गणेश विसर्जन सोहळा २०२५",
        "image_url": "https://images.unsplash.com/photo-1601058268499-e52658b8bb88?auto=format&fit=crop&w=1200&q=80",
        "type": "photo",
        "year": "2025"
    },
    {
        "_id": "3",
        "title": "श्रींची आकर्षक आरास व महापूजा",
        "image_url": "https://images.unsplash.com/photo-1620766182966-c6eb5ed2b788?auto=format&fit=crop&w=1200&q=80",
        "type": "photo",
        "year": "2025"
    }
]

def get_db():
    if "mongodb+srv" in MONGO_URI or ("mongodb://" in MONGO_URI and "localhost" not in MONGO_URI):
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000,
            tls=True,
            tlsAllowInvalidCertificates=True
        )
    else:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    return client[DB_NAME]

def init_db():
    try:
        db = get_db()
        if db.settings.count_documents({}) == 0:
            db.settings.insert_one(DEFAULT_SETTINGS.copy())

        if db.gallery.count_documents({}) == 0:
            db.gallery.insert_many(SAMPLE_GALLERY.copy())

        print("Database re-initialized with Gallery & Admin settings successfully!")
    except Exception as e:
        print(f"MongoDB Init Warning (using defaults): {e}")

def generate_receipt_no():
    try:
        db = get_db()
        count = db.vargani_records.count_documents({}) + 1
        receipt_no = f"VRG-2026-{count:04d}"
        while db.vargani_records.find_one({"receipt_no": receipt_no}):
            count += 1
            receipt_no = f"VRG-2026-{count:04d}"
        return receipt_no
    except Exception:
        import random
        return f"VRG-2026-{random.randint(1000, 9999)}"

def add_vargani(data):
    record = {
        "receipt_no": generate_receipt_no(),
        "name": data.get("name", "").strip(),
        "mobile": data.get("mobile", "").strip(),
        "address": data.get("address", "").strip(),
        "amount": int(data.get("amount", 0)),
        "payment_mode": data.get("payment_mode", "Cash"),
        "transaction_id": data.get("transaction_id", "").strip(),
        "status": data.get("status", "Pending"),
        "screenshot_url": data.get("screenshot_url", ""),
        "created_at": datetime.datetime.now(),
        "verified_at": datetime.datetime.now() if data.get("status") == "Verified" else None
    }
    try:
        db = get_db()
        result = db.vargani_records.insert_one(record)
        record["_id"] = str(result.inserted_id)
    except Exception as e:
        print(f"Database write error: {e}")
        record["_id"] = "offline_id"
    return record

def get_all_vargani(status=None, search=None):
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
        records = list(db.vargani_records.find(query).sort("created_at", -1))
        for r in records:
            r["_id"] = str(r["_id"])
            if isinstance(r.get("created_at"), datetime.datetime):
                r["created_at_str"] = r["created_at"].strftime("%d-%m-%Y %I:%M %p")
            else:
                r["created_at_str"] = ""
        return records
    except Exception as e:
        print(f"MongoDB read error: {e}")
        return []

def get_vargani_by_id(record_id):
    try:
        db = get_db()
        r = db.vargani_records.find_one({"_id": ObjectId(record_id)})
        if r:
            r["_id"] = str(r["_id"])
            r["created_at_str"] = r["created_at"].strftime("%d-%m-%Y %I:%M %p") if isinstance(r.get("created_at"), datetime.datetime) else ""
        return r
    except Exception:
        return None

def get_vargani_by_receipt_no(receipt_no):
    try:
        db = get_db()
        r = db.vargani_records.find_one({"receipt_no": receipt_no})
        if r:
            r["_id"] = str(r["_id"])
            r["created_at_str"] = r["created_at"].strftime("%d-%m-%Y %I:%M %p") if isinstance(r.get("created_at"), datetime.datetime) else ""
        return r
    except Exception:
        return None

def verify_vargani(record_id):
    try:
        db = get_db()
        r = db.vargani_records.find_one({"_id": ObjectId(record_id)})
        if r:
            db.vargani_records.update_one(
                {"_id": ObjectId(record_id)},
                {"$set": {"status": "Verified", "verified_at": datetime.datetime.now()}}
            )
            r["status"] = "Verified"
            return r
    except Exception as e:
        print(f"Verify error: {e}")
    return None

def delete_vargani(record_id):
    try:
        db = get_db()
        db.vargani_records.delete_one({"_id": ObjectId(record_id)})
        return True
    except Exception:
        return False

def get_stats():
    try:
        db = get_db()
        records = list(db.vargani_records.find({}))
        total_collected = sum(r.get("amount", 0) for r in records if r.get("status") == "Verified")
        pending_amount = sum(r.get("amount", 0) for r in records if r.get("status") in ["Pending", "Pending Cash"])
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
    except Exception:
        return {
            "total_collected": 0,
            "pending_amount": 0,
            "total_donors": 0,
            "verified_count": 0,
            "pending_count": 0,
            "cash_pending_count": 0
        }

def get_gallery():
    try:
        db = get_db()
        items = list(db.gallery.find({}).sort("created_at", -1))
        for item in items:
            item["_id"] = str(item["_id"])
        return items
    except Exception:
        return SAMPLE_GALLERY

def add_gallery_item(title, image_url, media_type="photo", year="2025"):
    item = {
        "title": title.strip(),
        "image_url": image_url.strip(),
        "type": media_type,
        "year": year,
        "created_at": datetime.datetime.now()
    }
    try:
        db = get_db()
        res = db.gallery.insert_one(item)
        item["_id"] = str(res.inserted_id)
    except Exception:
        item["_id"] = "sample_id"
    return item

def delete_gallery_item(item_id):
    try:
        db = get_db()
        db.gallery.delete_one({"_id": ObjectId(item_id)})
        return True
    except Exception:
        return False

def get_settings():
    try:
        db = get_db()
        settings = db.settings.find_one({})
        if settings:
            settings["_id"] = str(settings["_id"])
            if "contact_name2" not in settings: settings["contact_name2"] = "वर्गणी व पावती प्रमुख"
            if "contact_phone2" not in settings: settings["contact_phone2"] = "9876543210"
            if "contact_name3" not in settings: settings["contact_name3"] = "खजिनदार (Treasurer)"
            if "contact_phone3" not in settings: settings["contact_phone3"] = "9822114455"
            if "entrance_shloka" not in settings: settings["entrance_shloka"] = "🚩 ॐ गं गणपतये नमः 🚩"
            if "entrance_photo_url" not in settings or not settings["entrance_photo_url"] or "photo-1567157577867" in settings.get("entrance_photo_url", ""):
                settings["entrance_photo_url"] = "https://images.unsplash.com/photo-1601058268499-e52658b8bb88?auto=format&fit=crop&w=1200&q=80"
            if "qr_code_url" not in settings or not settings["qr_code_url"]:
                settings["qr_code_url"] = "/static/images/default_qr.png"
            return settings
    except Exception as e:
        print(f"MongoDB settings read error: {e}")
    return DEFAULT_SETTINGS.copy()

def update_settings(data):
    try:
        db = get_db()
        data["updated_at"] = datetime.datetime.now()
        db.settings.update_one({}, {"$set": data}, upsert=True)
    except Exception as e:
        print(f"MongoDB settings update error: {e}")
    return get_settings()
