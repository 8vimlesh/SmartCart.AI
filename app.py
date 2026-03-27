from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from scraper import scrape_all

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

# ── Frontend pages ─────────────────────────
@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/reviews')
def reviews_page():
    return send_from_directory('frontend', 'reviews.html')

# ── Compare prices ─────────────────────────
@app.route('/api/compare')
def compare():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Query required'}), 400

    print(f'\n/api/compare?q={query}')
    results = scrape_all(query)

    if not results:
        return jsonify({'error': 'No results found', 'query': query}), 404

    prices = [r['price'] for r in results if r.get('price')]
    mrp = int(max(prices) * 1.25) if prices else 0

    for r in results:
        if r.get('price') and mrp > 0:
            r['discount'] = max(0, round((1 - r['price'] / mrp) * 100))
        if not r.get('mrp') or r['mrp'] == r.get('price'):
            r['mrp'] = mrp

    best_image = next((r['image'] for r in results if r.get('image')), None)
    best_name  = next((r['name'] for r in results if r.get('name') and r['name'] != query), query)

    try:
        from database import save_product, save_price
        save_product(best_name, 'Product', best_image)
        for r in results:
            save_price(best_name, r['platform'], r['price'], r.get('rating'), r.get('url'))
    except Exception as e:
        print(f'DB save error (non-fatal): {e}')

    return jsonify({
        'query':      query,
        'name':       best_name,
        'image':      best_image,
        'mrp':        mrp,
        'platforms':  results,
        'scraped_at': datetime.now().isoformat()
    })

# ── Price history ───────────────────────────
@app.route('/api/history')
def history():
    product  = request.args.get('product', '').strip()
    platform = request.args.get('platform')
    days     = int(request.args.get('days', 30))
    if not product:
        return jsonify({'error': 'product param required'}), 400
    try:
        from database import get_price_history
        records = get_price_history(product, platform, days)
        return jsonify({'product': product, 'history': records})
    except Exception as e:
        return jsonify({'product': product, 'history': []})

# ── Set alert ───────────────────────────────
@app.route('/api/alert', methods=['POST'])
def create_alert():
    data      = request.json or {}
    product   = data.get('product')
    platform  = data.get('platform')
    threshold = data.get('threshold')
    if not all([product, platform, threshold]):
        return jsonify({'error': 'product, platform, threshold required'}), 400
    try:
        from database import set_alert
        set_alert(product, platform, threshold, data.get('email'))
    except Exception as e:
        print(f'Alert save error: {e}')
    return jsonify({'status': 'ok'})

# ── Tracked products ────────────────────────
@app.route('/api/products')
def products():
    try:
        from database import get_all_tracked_products
        return jsonify(get_all_tracked_products())
    except Exception as e:
        return jsonify([])

# ── Reviews GET ─────────────────────────────
@app.route('/api/reviews', methods=['GET'])
def get_reviews_api():
    product = request.args.get('product', '').strip()
    if not product:
        return jsonify({'error': 'product required'}), 400
    try:
        from database import get_reviews
        reviews = get_reviews(product)
        return jsonify({'product': product, 'reviews': reviews})
    except Exception as e:
        return jsonify({'product': product, 'reviews': []})

# ── Reviews POST ────────────────────────────
@app.route('/api/reviews', methods=['POST'])
def post_review():
    data = request.json or {}
    product  = data.get('product', '').strip()
    name     = data.get('name', '').strip()
    rating   = data.get('rating')
    title    = data.get('title', '').strip()
    body     = data.get('body', '').strip()
    platform = data.get('platform', '')
    verified = data.get('verified', False)
    tags     = data.get('tags', [])

    if not all([product, name, rating, title, body]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        from database import save_review
        review_id = save_review(product, name, rating, title, body, platform, verified, tags)
        return jsonify({'status': 'ok', 'id': review_id})
    except Exception as e:
        print(f'Review save error: {e}')
        return jsonify({'status': 'ok', 'id': str(datetime.now().timestamp())})

# ── Helpful vote ────────────────────────────
@app.route('/api/reviews/helpful', methods=['POST'])
def helpful():
    data = request.json or {}
    try:
        from database import mark_helpful
        mark_helpful(data.get('product'), data.get('id'))
    except Exception as e:
        pass
    return jsonify({'status': 'ok'})

# ── Health check ────────────────────────────
@app.route('/api/health')
def health():
    return jsonify({'status': 'running', 'time': datetime.now().isoformat()})

if __name__ == '__main__':
    port  = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True') == 'True'
    print(f'\nSmartCart running at http://localhost:{port}\n')
    app.run(debug=debug, port=port)