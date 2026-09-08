import os
import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "vargani_db")

def get_db():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]

def init_db():
    db = get_db()
    # Check if settings exist, else create default
    if db.settings.count_documents({}) == 0:
        default_settings = {
            "mandal_name": "श्री गणेशोत्सव मित्र मंडळ, पुणे",
            "tagline": "वर्गणी संकलन व ऑनलाईन डिजिटल पावती प्रणाली २०२६",
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
        db.settings.insert_one(default_settings)

    # Seed Slider Gallery if empty
    if db.gallery.count_documents({}) == 0:
        sample_gallery = [
            {
                "title": "मागील वर्षातील भव्य श्री गणेश विसर्जन सोहळा २०२५",
                "image_url": "https://images.unsplash.com/photo-1601058268499-e52658b8bb88?auto=format&fit=crop&w=1200&q=80",
                "type": "photo",
                "year": "2025",
                "created_at": datetime.datetime.now()
            },
            {
                "title": "श्रींची आकर्षक आरास व महापूजा",
                "image_url": "https://images.unsplash.com/photo-1567157577867-05ccb1388e66?auto=format&fit=crop&w=1200&q=80",
                "type": "photo",
                "year": "2025",
                "created_at": datetime.datetime.now()
            },
            {
                "title": "महाआरती व प्रसाद वाटप कार्यक्रम",
                "image_url": "https://images.unsplash.com/photo-1609102026400-349f257a3e35?auto=format&fit=crop&w=1200&q=80",
                "type": "photo",
                "year": "2024",
                "created_at": datetime.datetime.now()
            }
        ]
        db.gallery.insert_many(sample_gallery)

    # Seed sample vargani records if empty
    if db.vargani_records.count_documents({}) == 0:
        sample_records = [
            {
                "receipt_no": "VRG-2026-0001",
                "name": "श्री. राहुल आनंद शिंदे",
                "mobile": "9822114455",
                "address": "सुखकर्ता निवास, पुणे",
                "amount": 501,
                "payment_mode": "UPI / Online",
                "transaction_id": "UPI/423190875412",
                "status": "Verified",
                "screenshot_url": "",
                "created_at": datetime.datetime.now() - datetime.timedelta(days=2),
                "verified_at": datetime.datetime.now() - datetime.timedelta(days=2)
            },
            {
                "receipt_no": "VRG-2026-0002",
                "name": "सौ. सुनीता दीपक पाटील",
                "mobile": "9890123456",
                "address": "माऊली सदन, पुणे",
                "amount": 1001,
                "payment_mode": "Cash (रोख जमा)",
                "transaction_id": "CASH-ENTRY",
                "status": "Verified",
                "screenshot_url": "",
                "created_at": datetime.datetime.now() - datetime.timedelta(days=1),
                "verified_at": datetime.datetime.now() - datetime.timedelta(days=1)
            }
        ]
        db.vargani_records.insert_many(sample_records)
    print("Database re-initialized with Gallery & Admin settings successfully!")

def generate_receipt_no():
    db = get_db()
    count = db.vargani_records.count_documents({}) + 1
    receipt_no = f"VRG-2026-{count:04d}"
    while db.vargani_records.find_one({"receipt_no": receipt_no}):
        count += 1
        receipt_no = f"VRG-2026-{count:04d}"
    return receipt_no

def add_vargani(data):
    db = get_db()
    record = {
        "receipt_no": generate_receipt_no(),
        "name": data.get("name", "").strip(),
        "mobile": data.get("mobile", "").strip(),
        "address": data.get("address", "").strip(),
        "amount": int(data.get("amount", 0)),
        "payment_mode": data.get("payment_mode", "Cash"),
        "transaction_id": data.get("transaction_id", "").strip(),
        "status": data.get("status", "Pending"),  # Pending, Pending Cash, Verified
        "screenshot_url": data.get("screenshot_url", ""),
        "created_at": datetime.datetime.now(),
        "verified_at": datetime.datetime.now() if data.get("status") == "Verified" else None
    }
    result = db.vargani_records.insert_one(record)
    record["_id"] = str(result.inserted_id)
    return record

def get_all_vargani(status=None, search=None):
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

def get_vargani_by_id(record_id):
    db = get_db()
    try:
        r = db.vargani_records.find_one({"_id": ObjectId(record_id)})
        if r:
            r["_id"] = str(r["_id"])
            r["created_at_str"] = r["created_at"].strftime("%d-%m-%Y %I:%M %p") if isinstance(r.get("created_at"), datetime.datetime) else ""
        return r
    except Exception:
        return None

def get_vargani_by_receipt_no(receipt_no):
    db = get_db()
    r = db.vargani_records.find_one({"receipt_no": receipt_no})
    if r:
        r["_id"] = str(r["_id"])
        r["created_at_str"] = r["created_at"].strftime("%d-%m-%Y %I:%M %p") if isinstance(r.get("created_at"), datetime.datetime) else ""
    return r

def verify_vargani(record_id):
    db = get_db()
    r = db.vargani_records.find_one({"_id": ObjectId(record_id)})
    if r:
        db.vargani_records.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": {"status": "Verified", "verified_at": datetime.datetime.now()}}
        )
        return r
    return None

def delete_vargani(record_id):
    db = get_db()
    db.vargani_records.delete_one({"_id": ObjectId(record_id)})
    return True

def get_stats():
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

# Gallery & Video Slider functions
def get_gallery():
    db = get_db()
    items = list(db.gallery.find({}).sort("created_at", -1))
    for item in items:
        item["_id"] = str(item["_id"])
    return items

def add_gallery_item(title, image_url, media_type="photo", year="2025"):
    db = get_db()
    item = {
        "title": title.strip(),
        "image_url": image_url.strip(),
        "type": media_type,
        "year": year,
        "created_at": datetime.datetime.now()
    }
    res = db.gallery.insert_one(item)
    item["_id"] = str(res.inserted_id)
    return item

def delete_gallery_item(item_id):
    db = get_db()
    db.gallery.delete_one({"_id": ObjectId(item_id)})
    return True

def get_settings():
    db = get_db()
    settings = db.settings.find_one({})
    if settings:
        settings["_id"] = str(settings["_id"])
        if "contact_name2" not in settings: settings["contact_name2"] = "वर्गणी व पावती प्रमुख"
        if "contact_phone2" not in settings: settings["contact_phone2"] = "9876543210"
        if "contact_name3" not in settings: settings["contact_name3"] = "खजिनदार (Treasurer)"
        if "contact_phone3" not in settings: settings["contact_phone3"] = "9822114455"
        if "qr_code_url" not in settings or not settings["qr_code_url"]:
            settings["qr_code_url"] = "/static/images/default_qr.png"
    return settings or {}

def update_settings(data):
    db = get_db()
    data["updated_at"] = datetime.datetime.now()
    db.settings.update_one({}, {"$set": data}, upsert=True)
    return get_settings()
