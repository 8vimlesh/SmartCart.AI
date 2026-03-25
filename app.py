from flask import Flask, jsonify, request
from flask_cors import CORS
from scraper import scrape_all
from database import (
    save_product, save_price, get_price_history,
    set_alert, check_alerts, get_all_tracked_products
)
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)


# ── Serve the frontend ──────────────────────
@app.route('/')
def index():
    return app.send_static_file('index.html')


# ── COMPARE: main search endpoint ──────────
@app.route('/api/compare')
def compare():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Query required'}), 400

    print(f"\n📦 /api/compare?q={query}")
    
    results = scrape_all(query)

    if not results:
        return jsonify({'error': 'No results found', 'query': query}), 404

    # Calculate MRP (highest price * 1.2 as estimate)
    prices = [r['price'] for r in results if r.get('price')]
    max_price = max(prices) if prices else 0
    mrp = int(max_price * 1.25)
    
    # Add discount to each result
    for r in results:
        if r.get('price') and mrp > 0:
            r['discount'] = max(0, round((1 - r['price'] / mrp) * 100))
        
        # Infer MRP per platform if available
        if not r.get('mrp') or r['mrp'] == r.get('price'):
            r['mrp'] = mrp

    # Best image and name from results
    best_image = next((r['image'] for r in results if r.get('image')), None)
    best_name  = next((r['name'] for r in results if r.get('name') and r['name'] != query), query)

    # Save to database
    try:
        save_product(best_name, 'Product', best_image)
        for r in results:
            save_price(best_name, r['platform'], r['price'], r.get('rating'), r.get('url'))
    except Exception as e:
        print(f"DB save error: {e}")  # non-fatal

    return jsonify({
        'query': query,
        'name': best_name,
        'image': best_image,
        'mrp': mrp,
        'platforms': results,
        'scraped_at': datetime.now().isoformat()
    })


# ── PRICE HISTORY ───────────────────────────
@app.route('/api/history')
def history():
    product = request.args.get('product', '').strip()
    platform = request.args.get('platform')
    days = int(request.args.get('days', 30))
    
    if not product:
        return jsonify({'error': 'product param required'}), 400
    
    records = get_price_history(product, platform, days)
    return jsonify({'product': product, 'history': records})


# ── SET ALERT ───────────────────────────────
@app.route('/api/alert', methods=['POST'])
def create_alert():
    data = request.json
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    
    product   = data.get('product')
    platform  = data.get('platform')
    threshold = data.get('threshold')
    email     = data.get('email')
    
    if not all([product, platform, threshold]):
        return jsonify({'error': 'product, platform, threshold required'}), 400
    
    set_alert(product, platform, threshold, email)
    return jsonify({'status': 'ok', 'message': f'Alert set for {product} on {platform} below ₹{threshold}'})


# ── TRACKED PRODUCTS ────────────────────────
@app.route('/api/products')
def products():
    return jsonify(get_all_tracked_products())


# ── HEALTH CHECK ────────────────────────────
@app.route('/api/health')
def health():
    return jsonify({
        'status': 'running',
        'time': datetime.now().isoformat()
    })
@app.route("/reviews")
def reviews_page():
    return send_from_directory("frontend", "reviews.html")

@app.route("/api/reviews", methods=["GET"])
def get_reviews_route():
    product = request.args.get("product", "").strip()
    if not product:
        return jsonify({"error": "product required"}), 400
    try:
        from database import get_reviews
        reviews = get_reviews(product)
        return jsonify({"product": product, "reviews": reviews})
    except:
        return jsonify({"product": product, "reviews": []}), 200

@app.route("/api/reviews", methods=["POST"])
def post_review():
    data = request.json or {}
    try:
        from database import save_review
        rid = save_review(data.get("product"), data.get("name"), data.get("rating"), data.get("title"), data.get("body"), data.get("platform"), data.get("verified", False), data.get("tags", []))
        return jsonify({"status": "ok", "id": rid})
    except Exception as e:
        return jsonify({"status": "ok", "id": "local"})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True') == 'True'
    print(f"\n🚀 SmartCart API running at http://localhost:{port}")
    print(f"   Frontend at  http://localhost:{port}/\n")
    app.run(debug=debug, port=port)