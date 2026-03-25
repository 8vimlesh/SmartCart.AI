from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'))
db = client[os.getenv('DB_NAME', 'smartcart')]

# Collections (like tables)
products_col    = db['products']
price_hist_col  = db['price_history']
alerts_col      = db['alerts']


def save_product(name, category, image_url):
    """Save or update a product in the database."""
    existing = products_col.find_one({'name': name})
    if existing:
        return str(existing['_id'])
    
    result = products_col.insert_one({
        'name': name,
        'category': category,
        'image': image_url,
        'created_at': datetime.now(),
        'last_updated': datetime.now()
    })
    return str(result.inserted_id)


def save_price(product_name, platform, price, rating=None, url=None):
    """Save a price snapshot to history."""
    if not price:
        return
    
    price_hist_col.insert_one({
        'product_name': product_name,
        'platform': platform,
        'price': price,
        'rating': rating,
        'url': url,
        'timestamp': datetime.now(),
        'date': datetime.now().strftime('%Y-%m-%d')
    })
    
    # Update last_updated on product
    products_col.update_one(
        {'name': product_name},
        {'$set': {'last_updated': datetime.now()}}
    )


def get_price_history(product_name, platform=None, days=30):
    """Get price history for a product."""
    query = {'product_name': product_name}
    if platform:
        query['platform'] = platform
    
    from datetime import timedelta
    since = datetime.now() - timedelta(days=days)
    query['timestamp'] = {'$gte': since}
    
    records = list(price_hist_col.find(
        query,
        {'_id': 0, 'platform': 1, 'price': 1, 'date': 1, 'timestamp': 1}
    ).sort('timestamp', 1))
    
    return records


def set_alert(product_name, platform, threshold_price, user_email=None):
    """Set a price alert."""
    # Remove old alert for same product+platform
    alerts_col.delete_many({
        'product_name': product_name,
        'platform': platform
    })
    
    alerts_col.insert_one({
        'product_name': product_name,
        'platform': platform,
        'threshold': threshold_price,
        'user_email': user_email,
        'triggered': False,
        'created_at': datetime.now()
    })


def check_alerts(product_name, platform, current_price):
    """Check if any alerts should be triggered."""
    alerts = list(alerts_col.find({
        'product_name': product_name,
        'platform': platform,
        'triggered': False
    }))
    
    triggered = []
    for alert in alerts:
        if current_price <= alert['threshold']:
            alerts_col.update_one(
                {'_id': alert['_id']},
                {'$set': {'triggered': True, 'triggered_at': datetime.now()}}
            )
            triggered.append(alert)
    
    return triggered


def get_all_tracked_products():
    """Get all products being tracked."""
    return list(products_col.find({}, {'_id': 0}))