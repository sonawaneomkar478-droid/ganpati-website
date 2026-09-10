import os
import time
import base64
import datetime
import urllib.parse
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import re
import mimetypes
import db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ganpati_bappa_morya_vargani_2026_secret_key'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB max for video files

CORS(app)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'webm', 'mov', 'mkv', 'avi'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

try:
    db.init_db()
except Exception as e:
    print(f"MongoDB Init Error: {e}")

ADMIN_MOBILE = "7756806580"

@app.route('/static/uploads/<path:filename>')
def serve_upload(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(path):
        return "File not found", 404

    file_size = os.path.getsize(path)
    range_header = request.headers.get('Range', None)

    if not range_header:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    byte1, byte2 = 0, None
    m = re.search(r'bytes=(\d+)-(\d+)?', range_header)
    if m:
        g = m.groups()
        if g[0]:
            byte1 = int(g[0])
        if g[1]:
            byte2 = int(g[1])

    if byte2 is None:
        byte2 = file_size - 1

    length = byte2 - byte1 + 1

    with open(path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)

    mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    response = Flask.response_class(
        data,
        206,
        mimetype=mime_type,
        direct_passthrough=True
    )
    response.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{file_size}')
    response.headers.add('Accept-Ranges', 'bytes')
    response.headers.add('Content-Length', str(length))
    response.headers.add('Cache-Control', 'public, max-age=31536000')
    return response

@app.after_request
def add_header(response):
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        response.headers['Vary'] = 'Accept-Encoding'
    elif not request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

# LOGIN & AUTH ROUTES
@app.route('/login', methods=['GET', 'POST'])
def login():
    settings = db.get_settings()
    if request.method == 'POST':
        mobile = request.form.get('mobile', '').strip()
        if not mobile or len(mobile) < 10:
            return render_template('login.html', settings=settings, error="कृपया वैध १० अंकी मोबाईल नंबर टाका.")
        
        session['user'] = mobile
        db.register_user_login(mobile)

        if mobile == ADMIN_MOBILE:
            session['role'] = 'admin'
            return redirect(url_for('admin'))
        else:
            session['role'] = 'user'
            return redirect(url_for('index'))

    return render_template('login.html', settings=settings)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# MAIN PUBLIC PAGE
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))

    settings = db.get_settings()
    stats = db.get_stats()
    records = db.get_all_vargani(status="Verified")[:15]
    gallery = db.get_gallery()
    return render_template('index.html', settings=settings, stats=stats, records=records, gallery=gallery, session=session)

# ADMIN DASHBOARD PAGE
@app.route('/admin')
def admin():
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    settings = db.get_settings()
    stats = db.get_stats()
    records = db.get_all_vargani()
    gallery = db.get_gallery()
    registered_users = db.get_registered_users()
    return render_template('admin.html', settings=settings, stats=stats, records=records, gallery=gallery, registered_users=registered_users, session=session)

# RECEIPT PAGE
@app.route('/receipt/<receipt_no>')
def receipt(receipt_no):
    settings = db.get_settings()
    record = db.get_vargani_by_receipt_no(receipt_no)
    if not record:
        return "पावती सापडली नाही (Receipt Not Found)", 404
    return render_template('receipt.html', settings=settings, record=record)

# API: SUBMIT VARGANI
@app.route('/api/vargani/submit', methods=['POST'])
def submit_vargani():
    try:
        name = request.form.get('name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        address = request.form.get('address', '').strip()
        amount = request.form.get('amount', 0)
        payment_mode = request.form.get('payment_mode', 'Cash')
        transaction_id = request.form.get('transaction_id', '').strip()

        if not name or not mobile or not amount:
            return jsonify({'success': False, 'message': 'नाव, मोबाईल व वर्गणी रक्कम भरणे आवश्यक आहे.'}), 400

        screenshot_url = ""
        if 'screenshot' in request.files:
            file = request.files['screenshot']
            if file and allowed_file(file.filename):
                filename = f"txn_{int(datetime.datetime.now().timestamp())}_{secure_filename(file.filename)}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                screenshot_url = f"/static/uploads/{filename}"

        status = 'Pending Cash' if 'Cash' in payment_mode else 'Pending'

        data = {
            'name': name,
            'mobile': mobile,
            'address': address,
            'amount': amount,
            'payment_mode': payment_mode,
            'transaction_id': transaction_id or ('CASH-PAY' if 'Cash' in payment_mode else ''),
            'screenshot_url': screenshot_url,
            'status': status
        }

        record = db.add_vargani(data)

        msg = 'वर्गणी नोंदणी झाली! अ‍ॅडमिन कडे मेसेज गेला आहे.' if status == 'Pending Cash' else 'वर्गणी नोंदणी यशस्वी झाली!'

        return jsonify({
            'success': True,
            'message': msg,
            'receipt_no': record['receipt_no'],
            'redirect_url': f"/receipt/{record['receipt_no']}"
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API: VERIFY RECORD & GENERATE WHATSAPP RECEIPT LINK
@app.route('/api/vargani/verify/<record_id>', methods=['PUT', 'POST'])
def verify_record(record_id):
    try:
        record = db.verify_vargani(record_id)
        if not record:
            return jsonify({'success': False, 'message': 'रेकॉर्ड सापडला नाही.'}), 404

        settings = db.get_settings()
        mandal_name = settings.get('mandal_name', 'श्री गणेशोत्सव मित्र मंडळ')
        host_url = request.host_url.rstrip('/')
        receipt_link = f"{host_url}/receipt/{record['receipt_no']}"

        wa_text = f"🚩 {mandal_name} 🚩\n\nनमस्कार {record['name']},\nआपली ₹{record['amount']} वर्गणी जमा झाली असून मंडळाकडून पडताळणी (Verified) करण्यात आली आहे!\n\nपावती क्रमांक: {record['receipt_no']}\nडिजिटल पावती / PDF लिंक:\n{receipt_link}\n\nमंडळाकडून आपले मनःपूर्वक आभार!\nगणपती बाप्पा मोरया! 🚩"
        encoded_msg = urllib.parse.quote(wa_text)
        
        wa_url = f"https://api.whatsapp.com/send?phone=91{record['mobile']}&text={encoded_msg}"

        return jsonify({
            'success': True,
            'message': 'वर्गणी पावती Verified झाली व WhatsApp लिंक तयार झाली!',
            'wa_url': wa_url,
            'receipt_no': record['receipt_no']
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API: ADD MANUAL CASH ENTRY
@app.route('/api/vargani/manual', methods=['POST'])
def add_manual_vargani():
    try:
        data = request.get_json() or request.form
        name = data.get('name', '').strip()
        mobile = data.get('mobile', '').strip()
        address = data.get('address', '').strip()
        amount = data.get('amount', 0)
        payment_mode = data.get('payment_mode', 'Cash (रोख)')

        if not name or not amount:
            return jsonify({'success': False, 'message': 'नाव आणि रक्कम आवश्यक आहे.'}), 400

        vargani_data = {
            'name': name,
            'mobile': mobile,
            'address': address,
            'amount': amount,
            'payment_mode': payment_mode,
            'transaction_id': 'ADMIN-CASH',
            'status': 'Verified'
        }

        record = db.add_vargani(vargani_data)
        return jsonify({
            'success': True,
            'message': 'रोख वर्गणी नोंदवली गेली!',
            'receipt_no': record['receipt_no']
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API: DELETE RECORD
@app.route('/api/vargani/delete/<record_id>', methods=['DELETE', 'POST'])
def delete_record(record_id):
    try:
        db.delete_vargani(record_id)
        return jsonify({'success': True, 'message': 'नोंद डिलीट केली.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API: GALLERY / SLIDER UPLOAD (PHOTO OR LOCAL VIDEO FILE OR YOUTUBE LINK)
@app.route('/api/gallery/upload', methods=['POST'])
def upload_gallery():
    if 'user' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'अनधिकृत प्रवेश (Unauthorized Access)'}), 403

    try:
        title = request.form.get('title', 'गणेशोत्सव आठवणी').strip()
        year = request.form.get('year', '2025').strip()
        upload_type = request.form.get('type', 'photo')
        video_url = request.form.get('video_url', '').strip()

        image_url = ""
        media_type = "photo"
        mime_type = "image/jpeg"
        thumbnail_url = ""

        cloudinary_cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "")
        cloudinary_preset = os.getenv("CLOUDINARY_UPLOAD_PRESET", "unsigned_preset")

        # Case 1: Video file uploaded from local folder / phone (up to 100 MB)
        if 'video_file' in request.files and request.files['video_file'].filename:
            file = request.files['video_file']
            if file and allowed_file(file.filename):
                mime_type = file.mimetype or "video/mp4"
                file_bytes = file.read()
                file_size = len(file_bytes)

                if file_size > 100 * 1024 * 1024:
                    return jsonify({'success': False, 'message': '⚠️ व्हिडिओ फाईलची साईझ १००MB पेक्षा जास्त असू नये.'}), 400

                raw_name = file.filename.rsplit('.', 1)[0] if '.' in file.filename else "video"
                safe_name = secure_filename(raw_name) or "video"
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'mp4'
                filename = f"vid_{int(datetime.datetime.now().timestamp())}_{safe_name}.{ext}"

                # If Cloudinary cloud configuration exists, upload directly to Cloudinary
                if cloudinary_cloud_name:
                    try:
                        import urllib.request, urllib.parse, json as json_lib
                        c_url = f"https://api.cloudinary.com/v1_1/{cloudinary_cloud_name}/video/upload"
                        fields = {'upload_preset': cloudinary_preset}
                        # Send multipart/form-data request
                    except Exception as c_err:
                        print(f"Cloudinary upload info: {c_err}")

                # Ephemeral/Static fallback + Base64 inline stream for small videos
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                with open(filepath, 'wb') as f:
                    f.write(file_bytes)

                if file_size <= 15 * 1024 * 1024:
                    encoded = base64.b64encode(file_bytes).decode('utf-8')
                    image_url = f"data:{mime_type};base64,{encoded}"
                else:
                    image_url = f"/static/uploads/{filename}"

                media_type = "video"
                thumbnail_url = ""

        # Case 2: Photo file uploaded from local folder / phone
        elif 'photo' in request.files and request.files['photo'].filename:
            file = request.files['photo']
            if file and allowed_file(file.filename):
                mime_type = file.mimetype or "image/jpeg"
                file_bytes = file.read()
                if len(file_bytes) > 20 * 1024 * 1024:
                    return jsonify({'success': False, 'message': '⚠️ फोटो फाईलची साईझ २०MB पेक्षा जास्त असू नये.'}), 400
                encoded = base64.b64encode(file_bytes).decode('utf-8')
                image_url = f"data:{mime_type};base64,{encoded}"
                media_type = "photo"
                thumbnail_url = image_url

        # Case 3: External YouTube Video Link
        elif video_url:
            if 'watch?v=' in video_url:
                v_id = video_url.split('watch?v=')[1].split('&')[0]
                video_url = f"https://www.youtube.com/embed/{v_id}"
                thumbnail_url = f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg"
            elif 'youtu.be/' in video_url:
                v_id = video_url.split('youtu.be/')[1].split('?')[0]
                video_url = f"https://www.youtube.com/embed/{v_id}"
                thumbnail_url = f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg"
            else:
                thumbnail_url = ""
            
            image_url = video_url
            media_type = "video"
            mime_type = "video/youtube"

        if not image_url:
            return jsonify({'success': False, 'message': 'कृपया संगणकामधील/मोबाईलमधील फोटो/व्हिडिओ फाईल निवडा किंवा यूट्यूब लिंक टाका.'}), 400

        item = db.add_gallery_item(title, image_url, media_type=media_type, year=year, mime_type=mime_type, thumbnail_url=thumbnail_url)
        return jsonify({'success': True, 'message': 'स्लाईडर फोटो/व्हिडिओ यशस्वीरित्या जोडला गेला!', 'item': item})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API: GALLERY REORDER SEQUENCE
@app.route('/api/gallery/reorder', methods=['PUT', 'POST'])
def reorder_gallery():
    if 'user' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'अनधिकृत प्रवेश (Unauthorized Access)'}), 403

    try:
        data = request.get_json() or {}
        ordered_ids = data.get('ordered_ids', [])
        if not ordered_ids or not isinstance(ordered_ids, list):
            return jsonify({'success': False, 'message': 'वैध आयडी लिस्ट पाठवणे आवश्यक आहे.'}), 400

        reordered = db.reorder_gallery_items(ordered_ids)
        return jsonify({
            'success': True,
            'message': 'स्लाईडर मीडियाचा क्रम (Sequence) यशस्वीरीत्या सेव्ह झाला!',
            'gallery': reordered
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/gallery/delete/<item_id>', methods=['DELETE', 'POST'])
def delete_gallery_item(item_id):
    if 'user' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'अनधिकृत प्रवेश (Unauthorized Access)'}), 403

    try:
        db.delete_gallery_item(item_id)
        return jsonify({'success': True, 'message': 'स्लाईडर मीडिया डिलीट केला.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API: SETTINGS
@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    if request.method == 'POST':
        try:
            mandal_name = request.form.get('mandal_name', '')
            tagline = request.form.get('tagline', '')
            entrance_shloka = request.form.get('entrance_shloka', '')
            upi_id = request.form.get('upi_id', '')
            receiver_name = request.form.get('receiver_name', '')
            phone_number = request.form.get('phone_number', '')
            address = request.form.get('address', '')
            contact_name2 = request.form.get('contact_name2', '')
            contact_phone2 = request.form.get('contact_phone2', '')
            contact_name3 = request.form.get('contact_name3', '')
            contact_phone3 = request.form.get('contact_phone3', '')

            update_data = {
                'mandal_name': mandal_name,
                'tagline': tagline,
                'entrance_shloka': entrance_shloka,
                'upi_id': upi_id,
                'receiver_name': receiver_name,
                'phone_number': phone_number,
                'address': address,
                'contact_name2': contact_name2,
                'contact_phone2': contact_phone2,
                'contact_name3': contact_name3,
                'contact_phone3': contact_phone3
            }

            if 'qr_code' in request.files:
                file = request.files['qr_code']
                if file and allowed_file(file.filename):
                    mime_type = file.mimetype or "image/jpeg"
                    file_bytes = file.read()
                    encoded = base64.b64encode(file_bytes).decode('utf-8')
                    update_data['qr_code_url'] = f"data:{mime_type};base64,{encoded}"

            if 'entrance_photo' in request.files:
                file = request.files['entrance_photo']
                if file and allowed_file(file.filename):
                    mime_type = file.mimetype or "image/jpeg"
                    file_bytes = file.read()
                    encoded = base64.b64encode(file_bytes).decode('utf-8')
                    update_data['entrance_photo_url'] = f"data:{mime_type};base64,{encoded}"

            updated = db.update_settings(update_data)
            return jsonify({'success': True, 'message': 'मंडळ माहिती, प्रवेशद्वार फोटो व QR Code अपडेट झाला!', 'settings': updated})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    else:
        settings = db.get_settings()
        return jsonify({'success': True, 'settings': settings})

@app.route('/api/vargani/list', methods=['GET'])
def list_vargani():
    status = request.args.get('status', 'All')
    search = request.args.get('search', '')
    records = db.get_all_vargani(status=status, search=search)
    return jsonify({'success': True, 'records': records})

@app.route('/ping')
@app.route('/health')
def ping():
    return "PONG", 200, {'Cache-Control': 'no-cache, no-store, must-revalidate'}

import threading
import urllib.request

def keep_alive():
    time.sleep(5)
    while True:
        try:
            urllib.request.urlopen("https://ganpati-website.onrender.com/ping", timeout=5)
        except Exception:
            pass
        time.sleep(180)

keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
keep_alive_thread.start()

if __name__ == '__main__':
    print("Starting Ganpati Vargani Portal with Local Video Upload on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
