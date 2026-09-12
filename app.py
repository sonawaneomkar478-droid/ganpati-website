import os
import time
import base64
import datetime
import urllib.parse
import gzip
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
import re
import mimetypes
import db
import tempfile
from cloud_storage import get_cloud_config, delete_cloud_media, generate_video_poster_url, is_cloudinary_configured

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ganpati_bappa_morya_vargani_2026_secret_key'

def get_writable_upload_dir():
    local_dir = os.path.join(app.root_path, 'static', 'uploads')
    try:
        os.makedirs(local_dir, exist_ok=True)
        test_file = os.path.join(local_dir, '.write_test')
        with open(test_file, 'w') as f:
            f.write('ok')
        os.remove(test_file)
        return local_dir, True
    except Exception:
        tmp_dir = os.path.join(tempfile.gettempdir(), 'uploads')
        os.makedirs(tmp_dir, exist_ok=True)
        return tmp_dir, False

upload_folder_path, IS_LOCAL_WRITABLE = get_writable_upload_dir()
app.config['UPLOAD_FOLDER'] = upload_folder_path
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB max for video files

CORS(app)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'webm', 'mov', 'mkv', 'avi', 'heic'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

try:
    import threading
    threading.Thread(target=db.init_db, daemon=True).start()
except Exception as e:
    print(f"MongoDB Init Error: {e}")

ADMIN_MOBILE = "7756806580"

@app.context_processor
def inject_global_vars():
    try:
        return {'settings': db.get_settings()}
    except Exception:
        return {'settings': db.DEFAULT_SETTINGS}

@app.before_request
def before_request_time():
    request._start_time = time.time()

@app.route('/static/uploads/<path:filename>')
def serve_upload(filename):
    local_dir = os.path.join(app.root_path, 'static', 'uploads')
    local_path = os.path.join(local_dir, filename)
    target_dir = local_dir

    if not os.path.exists(local_path):
        tmp_dir = os.path.join(tempfile.gettempdir(), 'uploads')
        local_path = os.path.join(tmp_dir, filename)
        target_dir = tmp_dir

    if not os.path.exists(local_path):
        return "File not found", 404

    file_size = os.path.getsize(local_path)
    range_header = request.headers.get('Range', None)

    if not range_header:
        return send_from_directory(target_dir, filename)

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

    with open(local_path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)

    mime_type = mimetypes.guess_type(local_path)[0] or 'application/octet-stream'
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

# API: SERVE MEDIA DIRECTLY FROM MONGODB ATLAS GRIDFS (100% PERSISTENT & FAST)
@app.route('/api/media/<media_id>')
def serve_media_db(media_id):
    try:
        media_info = db.get_media_from_db(media_id)
        if not media_info:
            return "Media not found", 404
        grid_out, content_type, filename, file_size = media_info

        range_header = request.headers.get('Range', None)
        if not range_header:
            data = grid_out.read()
            resp = Response(data, 200, mimetype=content_type)
            resp.headers['Content-Length'] = str(file_size)
            resp.headers['Accept-Ranges'] = 'bytes'
            resp.headers['Cache-Control'] = 'public, max-age=86400, stale-while-revalidate=43200'
            return resp

        # HTTP Range Header Support (Crucial for Video Playback & Seeking on Mobile/Desktop)
        byte1, byte2 = 0, None
        m = re.search(r'bytes=(\d+)-(\d+)?', range_header)
        if m:
            g = m.groups()
            if g[0]:
                byte1 = int(g[0])
            if g[1]:
                byte2 = int(g[1])

        if byte2 is None:
            byte2 = min(file_size - 1, byte1 + 1024 * 1024 - 1)

        if byte1 >= file_size:
            return Response("Requested range not satisfiable", 416)

        length = byte2 - byte1 + 1
        grid_out.seek(byte1)
        data = grid_out.read(length)

        resp = Response(data, 206, mimetype=content_type, direct_passthrough=True)
        resp.headers['Content-Range'] = f'bytes {byte1}-{byte2}/{file_size}'
        resp.headers['Accept-Ranges'] = 'bytes'
        resp.headers['Content-Length'] = str(length)
        resp.headers['Cache-Control'] = 'public, max-age=86400, stale-while-revalidate=43200'
        return resp
    except Exception as e:
        print(f"Error serving media {media_id}: {e}")
        return "Internal server error", 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    static_dir = os.path.join(app.root_path, 'static')
    file_path = os.path.join(static_dir, filename)
    if os.path.exists(file_path):
        return send_from_directory(static_dir, filename)
    return "Static file not found", 404

@app.after_request
def add_header(response):
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        response.headers['Vary'] = 'Accept-Encoding'
    elif not request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # GZIP COMPRESSION FOR TEXT RESPONSES (>450 BYTES)
    accept_encoding = request.headers.get('Accept-Encoding', '')
    if 'gzip' in accept_encoding and 200 <= response.status_code < 300:
        if not response.direct_passthrough and not response.is_streamed:
            content_type = response.headers.get('Content-Type', '')
            if any(t in content_type for t in ['text/html', 'text/css', 'application/javascript', 'application/json', 'image/svg+xml']):
                data = response.get_data()
                if len(data) > 450:
                    compressed_data = gzip.compress(data, compresslevel=6)
                    response.set_data(compressed_data)
                    response.headers['Content-Encoding'] = 'gzip'
                    response.headers['Content-Length'] = len(compressed_data)
                    response.headers['Vary'] = 'Accept-Encoding'

    if hasattr(request, '_start_time'):
        duration = time.time() - request._start_time
        print(f"[PERF] {request.method} {request.path} -> {response.status_code} ({duration:.3f}s)")
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
                saved_s = save_uploaded_media(file, prefix="txn")
                if saved_s:
                    screenshot_url = saved_s

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

# API: ADD MANUAL VARGANI ENTRY (CASH / ONLINE)
@app.route('/api/vargani/manual', methods=['POST'])
def add_manual_vargani():
    try:
        data = request.get_json() or request.form
        name = data.get('name', '').strip()
        mobile = data.get('mobile', '').strip()
        address = data.get('address', '').strip()
        amount = data.get('amount', 0)
        payment_mode = (data.get('payment_mode', '') or 'Cash (रोख)').strip()
        transaction_id = data.get('transaction_id', '').strip()

        if not name or not amount:
            return jsonify({'success': False, 'message': 'नाव आणि रक्कम आवश्यक आहे.'}), 400

        if not transaction_id:
            if 'Cash' in payment_mode or 'रोख' in payment_mode:
                transaction_id = 'ADMIN-CASH'
            else:
                transaction_id = f"ADMIN-ONLINE-{int(time.time())}"

        vargani_data = {
            'name': name,
            'mobile': mobile,
            'address': address,
            'amount': amount,
            'payment_mode': payment_mode,
            'transaction_id': transaction_id,
            'status': 'Verified'
        }

        record = db.add_vargani(vargani_data)
        return jsonify({
            'success': True,
            'message': f'{payment_mode} वर्गणी यशस्वीरित्या नोंदवली गेली!',
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
def save_uploaded_media(file_obj, prefix="media"):
    if not file_obj or not file_obj.filename or not allowed_file(file_obj.filename):
        return None
    raw_name = file_obj.filename.rsplit('.', 1)[0] if '.' in file_obj.filename else "file"
    safe_name = secure_filename(raw_name) or "file"
    ext = file_obj.filename.rsplit('.', 1)[1].lower() if '.' in file_obj.filename else 'jpg'

    upload_dir, is_writable = get_writable_upload_dir()

    # Image Compression & High Quality Optimization (Pillow WebP)
    if ext in {'jpg', 'jpeg', 'png', 'webp', 'gif', 'heic'}:
        try:
            from PIL import Image, ImageOps
            import io

            file_obj.seek(0)
            img = Image.open(file_obj)
            img = ImageOps.exif_transpose(img)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format='WEBP', quality=82, optimize=True)
            compressed_data = buf.getvalue()

            # FIRST PRIORITY: Save compressed WebP directly into MongoDB Atlas GridFS
            media_id = db.save_media_to_db(compressed_data, filename=f"{safe_name}.webp", content_type="image/webp")
            if media_id:
                return f"/api/media/{media_id}"

            filename = f"{prefix}_{int(time.time())}_{safe_name}.webp"
            filepath = os.path.join(upload_dir, filename)

            try:
                with open(filepath, 'wb') as f:
                    f.write(compressed_data)
            except Exception as write_err:
                print(f"File write warning: {write_err}")

            return f"/static/uploads/{filename}"
        except Exception as p_err:
            print(f"Pillow image compression info: {p_err}")

    # Video & Other Media Files
    file_obj.seek(0)
    file_bytes = file_obj.read()
    mime_type = getattr(file_obj, 'mimetype', None) or (f"video/{ext}" if ext in {'mp4', 'mov', 'webm'} else "application/octet-stream")

    # FIRST PRIORITY: Save video binary directly into MongoDB Atlas GridFS
    media_id = db.save_media_to_db(file_bytes, filename=f"{safe_name}.{ext}", content_type=mime_type)
    if media_id:
        return f"/api/media/{media_id}"

    filename = f"{prefix}_{int(time.time())}_{safe_name}.{ext}"
    filepath = os.path.join(upload_dir, filename)
    
    try:
        with open(filepath, 'wb') as f:
            f.write(file_bytes)
    except Exception as v_err:
        print(f"Video write warning: {v_err}")

    return f"/static/uploads/{filename}"

# API: CLOUD STORAGE CONFIG
@app.route('/api/cloud-config', methods=['GET'])
def cloud_config():
    resp = jsonify({'success': True, 'config': get_cloud_config()})
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp

# API: ADD GALLERY ITEM DIRECTLY (FROM CLOUD OR URL)
@app.route('/api/gallery/add-item', methods=['POST'])
def add_gallery_item_direct():
    if 'user' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'अनधिकृत प्रवेश (Unauthorized Access)'}), 403

    try:
        data = request.get_json() or request.form
        title = data.get('title', 'गणेशोत्सव आठवणी').strip()
        year = str(data.get('year', '2025')).strip() or '2025'
        image_url = data.get('image_url', '').strip()
        media_type = data.get('type', 'photo')
        thumbnail_url = data.get('thumbnail_url', '').strip()
        public_id = data.get('public_id', '').strip()
        mime_type = data.get('mime_type', 'image/jpeg' if media_type == 'photo' else 'video/mp4')

        if not image_url:
            return jsonify({'success': False, 'message': 'मीडिया URL आवश्यक आहे.'}), 400

        item = db.add_gallery_item(title, image_url, media_type=media_type, year=year, mime_type=mime_type, thumbnail_url=thumbnail_url, public_id=public_id)
        resp = jsonify({'success': True, 'message': 'स्लाईडर मीडिया यशस्वीरित्या जोडला गेला!', 'item': item})
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp
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

        # Case 1: Video file uploaded
        if 'video_file' in request.files and request.files['video_file'].filename:
            file = request.files['video_file']
            saved_path = save_uploaded_media(file, prefix="vid")
            if saved_path:
                image_url = saved_path
                media_type = "video"
                mime_type = file.mimetype or "video/mp4"

        # Case 2: Photo file uploaded
        elif 'photo' in request.files and request.files['photo'].filename:
            file = request.files['photo']
            saved_path = save_uploaded_media(file, prefix="img")
            if saved_path:
                image_url = saved_path
                media_type = "photo"
                mime_type = file.mimetype or "image/jpeg"
                thumbnail_url = saved_path

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
        resp = jsonify({'success': True, 'message': 'स्लाईडर फोटो/व्हिडिओ यशस्वीरित्या जोडला गेला!', 'item': item})
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp
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
        resp = jsonify({
            'success': True,
            'message': 'स्लाईडर मीडियाचा क्रम (Sequence) यशस्वीरीत्या सेव्ह झाला!',
            'gallery': reordered
        })
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/gallery/delete/<item_id>', methods=['DELETE', 'POST'])
def delete_gallery_item(item_id):
    if 'user' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'अनधिकृत प्रवेश (Unauthorized Access)'}), 403

    try:
        db.delete_gallery_item(item_id)
        resp = jsonify({'success': True, 'message': 'स्लाईडर मीडिया कायमस्वरूपी डिलीट केला.'})
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp
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

            if 'qr_code' in request.files and request.files['qr_code'].filename:
                saved_qr = save_uploaded_media(request.files['qr_code'], prefix="qr")
                if saved_qr:
                    update_data['qr_code_url'] = saved_qr

            if 'entrance_photo' in request.files and request.files['entrance_photo'].filename:
                saved_ent = save_uploaded_media(request.files['entrance_photo'], prefix="entrance")
                if saved_ent:
                    update_data['entrance_photo_url'] = saved_ent

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

@app.route('/api/db-status')
def db_status():
    db_obj = db.get_db()
    is_mongo = db_obj is not None
    gallery_items = db.get_gallery()
    return jsonify({
        'database_type': 'MongoDB Atlas' if is_mongo else 'Local JSON Storage',
        'is_mongo_connected': is_mongo,
        'gallery_count': len(gallery_items),
        'items': [{'id': str(i.get('_id')), 'title': i.get('title'), 'type': i.get('type')} for i in gallery_items]
    }), 200, {'Cache-Control': 'no-cache, no-store, must-revalidate'}

@app.route('/ping')
@app.route('/health')
def ping():
    return "PONG", 200, {'Cache-Control': 'no-cache, no-store, must-revalidate'}

if __name__ == '__main__':
    print("Starting Ganpati Vargani Portal with Local Video Upload on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
