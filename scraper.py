import os
import re
import time
import random

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

PLATFORM_MAP = {
    "amazon":    ["amazon.in", "amazon.com"],
    "flipkart":  ["flipkart.com"],
    "myntra":    ["myntra.com"],
    "ajio":      ["ajio.com"],
    "meesho":    ["meesho.com"],
    "snapdeal":  ["snapdeal.com"],
    "nykaa":     ["nykaa.com"],
    "croma":     ["croma.com"],
    "tatacliq":  ["tatacliq.com"],
    "reliance":  ["reliancedigital.in"],
    "jiomart":   ["jiomart.com"],
    "shopclues": ["shopclues.com"],
}

PLATFORM_INFO = {
    "amazon":    {"name": "Amazon",    "freeShip": True,  "offers": ["5% cashback on HDFC", "No-cost EMI"]},
    "flipkart":  {"name": "Flipkart",  "freeShip": True,  "offers": ["No-cost EMI", "Exchange offer"]},
    "myntra":    {"name": "Myntra",    "freeShip": True,  "offers": ["30-day easy returns"]},
    "ajio":      {"name": "Ajio",      "freeShip": True,  "offers": ["Extra 10% off AJIO coupons"]},
    "meesho":    {"name": "Meesho",    "freeShip": False, "offers": ["Cash on delivery"]},
    "snapdeal":  {"name": "Snapdeal",  "freeShip": False, "offers": []},
    "nykaa":     {"name": "Nykaa",     "freeShip": True,  "offers": ["Extra 10% off first order"]},
    "croma":     {"name": "Croma",     "freeShip": True,  "offers": ["Authorized service support"]},
    "tatacliq":  {"name": "Tata CLiQ", "freeShip": True,  "offers": ["Authentic products guaranteed"]},
    "reliance":  {"name": "Reliance",  "freeShip": True,  "offers": ["EMI on all cards"]},
    "jiomart":   {"name": "JioMart",   "freeShip": True,  "offers": ["JioCoin rewards"]},
    "shopclues": {"name": "ShopClues", "freeShip": False, "offers": []},
}


def parse_price(text):
    """Extract integer price from strings like Rs.24,999 or 24999.00"""
    if not text:
        return None
    cleaned = re.sub(r"[^\d]", "", str(text))
    if cleaned and 2 <= len(cleaned) <= 8:
        return int(cleaned)
    return None


def detect_platform(url, source=""):
    """Detect which platform a URL or source name belongs to."""
    url_lower    = (url    or "").lower()
    source_lower = (source or "").lower()
    for platform, domains in PLATFORM_MAP.items():
        for domain in domains:
            if domain in url_lower:
                return platform
    # Try matching source name
    for platform in PLATFORM_MAP:
        if platform in source_lower:
            return platform
    return "other"


def calc_discount(price, mrp):
    """Calculate discount percentage."""
    if not price or not mrp or mrp <= price:
        return 0
    return max(0, round((1 - price / mrp) * 100))


def scrape_all(query):
    print(f"\n{'='*50}")
    print(f"Searching: '{query}'")
    print(f"{'='*50}")

    if not SERPAPI_KEY:
        print("ERROR: SERPAPI_KEY not set in .env file")
        return []

    try:
        from serpapi import GoogleSearch
    except ImportError:
        print("ERROR: Run  pip install google-search-results")
        return []

    # ── Search 1: Google Shopping ──────────────────
    shopping_items = []
    try:
        print("  Searching Google Shopping...")
        params = {
            "engine":  "google_shopping",
            "q":       query,
            "gl":      "in",
            "hl":      "en",
            "num":     20,
            "api_key": SERPAPI_KEY,
        }
        res = GoogleSearch(params).get_dict()
        shopping_items = res.get("shopping_results", [])
        print(f"  Found {len(shopping_items)} shopping results")
    except Exception as e:
        print(f"  Shopping search error: {e}")

    # ── Search 2: Google main (more platforms) ─────
    inline_items = []
    if len(shopping_items) < 4:
        try:
            print("  Searching Google main...")
            params2 = {
                "engine":  "google",
                "q":       f"buy {query} online India price",
                "gl":      "in",
                "hl":      "en",
                "api_key": SERPAPI_KEY,
            }
            res2 = GoogleSearch(params2).get_dict()
            inline_items = (
                res2.get("shopping_results", []) +
                res2.get("inline_shopping_results", [])
            )
            print(f"  Found {len(inline_items)} inline results")
        except Exception as e:
            print(f"  Inline search error: {e}")

    all_items = shopping_items + inline_items

    if not all_items:
        print("  No results found from any source")
        return []

    # ── Process results ────────────────────────────
    platform_data = {}
    best_image    = None
    best_name     = query

    for item in all_items:
        try:
            # Extract price
            price = None
            if item.get("extracted_price"):
                try:
                    price = int(float(item["extracted_price"]))
                except Exception:
                    pass
            if not price:
                price = parse_price(str(item.get("price", "")))
            if not price or price < 10:
                continue

            # Detect platform from URL and source
            link     = item.get("link") or item.get("product_link") or ""
            source   = item.get("source") or item.get("seller") or ""
            platform = detect_platform(link, source)

            # If unknown platform, use source name as key
            if platform == "other":
                if source:
                    platform = re.sub(r"[^a-z0-9]", "", source.lower())[:12]
                if not platform:
                    continue

            # Extract name and image
            name  = item.get("title") or item.get("name") or query
            image = item.get("thumbnail") or item.get("image")

            if image and not best_image:
                best_image = image
            if name and name != query:
                best_name = name

            # Keep only cheapest price per platform
            if platform not in platform_data or price < platform_data[platform]["price"]:
                pinfo = PLATFORM_INFO.get(platform, {
                    "name":     source or platform.title(),
                    "freeShip": False,
                    "offers":   [],
                })

                rating = None
                try:
                    raw = item.get("rating") or item.get("store_rating")
                    if raw:
                        rating = float(raw) or None
                except Exception:
                    pass

                reviews = 0
                try:
                    raw = item.get("reviews") or item.get("store_reviews") or "0"
                    reviews = int(re.sub(r"[^\d]", "", str(raw))) or 0
                except Exception:
                    pass

                platform_data[platform] = {
                    "platform": platform,
                    "name":     name[:120],
                    "price":    price,
                    "mrp":      price,
                    "discount": 0,
                    "rating":   rating,
                    "reviews":  reviews,
                    "image":    image,
                    "url":      link,
                    "freeShip": pinfo["freeShip"],
                    "emi":      f"Rs.{price//24:,}/mo" if price > 10000 else None,
                    "offers":   pinfo["offers"],
                }

        except Exception as e:
            print(f"  Item error: {e}")
            continue

    if not platform_data:
        print("  Could not match any results to known platforms")
        return []

    # ── Calculate MRP and discounts ────────────────
    all_prices = [d["price"] for d in platform_data.values()]
    mrp        = int(max(all_prices) * 1.20)

    results = []
    for data in platform_data.values():
        data["mrp"]      = mrp
        data["discount"] = calc_discount(data["price"], mrp)
        if not data["image"] and best_image:
            data["image"] = best_image
        results.append(data)

    results.sort(key=lambda x: x["price"])

    print(f"\n  Found prices on {len(results)} platform(s):")
    for r in results:
        print(f"    {r['platform']:<14} Rs.{r['price']:>8,}   {r['discount']}% off   {r['url'][:50]}")
    print()

    return results


# ── Run directly to test ───────────────────────────
if __name__ == "__main__":
    q = input("Product to search: ").strip() or "Samsung Galaxy S24"
    results = scrape_all(q)
    if not results:
        print("\nNo results. Check your SERPAPI_KEY in .env")
    else:
        print(f"\nSuccess! Found {len(results)} results.")