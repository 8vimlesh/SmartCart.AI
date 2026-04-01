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

# ─────────────────────────────────────────────
# PLATFORM CONFIG
# ─────────────────────────────────────────────
PLATFORMS = {
    "amazon":   {
        "name": "Amazon",
        "domains": ["amazon.in", "amazon.com", "amzn"],
        "keywords": ["amazon"],
        "color": "#FF9900",
        "freeShip": True,
        "offers": ["5% cashback on HDFC cards", "No-cost EMI available"],
        "url": "https://amazon.in"
    },
    "flipkart": {
        "name": "Flipkart",
        "domains": ["flipkart.com", "fkrt"],
        "keywords": ["flipkart"],
        "color": "#2874F0",
        "freeShip": True,
        "offers": ["No-cost EMI", "Exchange offer available"],
        "url": "https://flipkart.com"
    },
    "myntra": {
        "name": "Myntra",
        "domains": ["myntra.com"],
        "keywords": ["myntra"],
        "color": "#FF3F6C",
        "freeShip": True,
        "offers": ["30-day easy returns"],
        "url": "https://myntra.com"
    },
    "ajio": {
        "name": "Ajio",
        "domains": ["ajio.com"],
        "keywords": ["ajio"],
        "color": "#E91E8C",
        "freeShip": True,
        "offers": ["Extra 10% off with AJIO coupons"],
        "url": "https://ajio.com"
    },
    "meesho": {
        "name": "Meesho",
        "domains": ["meesho.com"],
        "keywords": ["meesho"],
        "color": "#9c27b0",
        "freeShip": False,
        "offers": ["Cash on delivery available"],
        "url": "https://meesho.com"
    },
    "snapdeal": {
        "name": "Snapdeal",
        "domains": ["snapdeal.com"],
        "keywords": ["snapdeal"],
        "color": "#cc0033",
        "freeShip": False,
        "offers": [],
        "url": "https://snapdeal.com"
    },
    "nykaa": {
        "name": "Nykaa",
        "domains": ["nykaa.com", "nykaabeauty"],
        "keywords": ["nykaa"],
        "color": "#fc2779",
        "freeShip": True,
        "offers": ["Extra 10% off on first order"],
        "url": "https://nykaa.com"
    },
    "croma": {
        "name": "Croma",
        "domains": ["croma.com"],
        "keywords": ["croma"],
        "color": "#0066cc",
        "freeShip": True,
        "offers": ["Authorized service support"],
        "url": "https://croma.com"
    },
    "tatacliq": {
        "name": "Tata CLiQ",
        "domains": ["tatacliq.com", "tata cliq"],
        "keywords": ["tatacliq", "tata cliq"],
        "color": "#6b21a8",
        "freeShip": True,
        "offers": ["Authentic products guaranteed"],
        "url": "https://tatacliq.com"
    },
    "reliancedigital": {
        "name": "Reliance Digital",
        "domains": ["reliancedigital.in"],
        "keywords": ["reliance digital", "reliancedigital"],
        "color": "#0ea5e9",
        "freeShip": True,
        "offers": ["EMI on all cards"],
        "url": "https://reliancedigital.in"
    },
    "vijaysales": {
        "name": "Vijay Sales",
        "domains": ["vijaysales.com"],
        "keywords": ["vijay sales"],
        "color": "#dc2626",
        "freeShip": True,
        "offers": [],
        "url": "https://vijaysales.com"
    },
}


# ─────────────────────────────────────────────
# DETECT PLATFORM FROM URL + SOURCE TEXT
# ─────────────────────────────────────────────
def detect_platform(url="", source=""):
    url_l    = (url    or "").lower().strip()
    source_l = (source or "").lower().strip()
    combined = url_l + " " + source_l

    for pkey, pinfo in PLATFORMS.items():
        # check domains in URL
        for domain in pinfo["domains"]:
            if domain in url_l:
                return pkey
        # check keywords in source name
        for kw in pinfo["keywords"]:
            if kw in source_l:
                return pkey

    return None


# ─────────────────────────────────────────────
# PARSE PRICE FROM VARIOUS FORMATS
# ─────────────────────────────────────────────
def parse_price(raw):
    if raw is None:
        return None

    # already a number
    if isinstance(raw, (int, float)):
        val = int(raw)
        if 10 <= val <= 10_000_000:
            return val
        return None

    text = str(raw).strip()

    # SerpAPI sometimes gives extracted_price as clean float string
    try:
        val = int(float(text))
        if 10 <= val <= 10_000_000:
            return val
    except (ValueError, TypeError):
        pass

    # Remove currency symbols and commas, then extract digits
    cleaned = re.sub(r"[₹$€£,\s]", "", text)
    # Handle ranges like "₹999 – ₹1,499" — take the lower
    parts = re.split(r"[-–—]", cleaned)
    for part in parts:
        digits = re.sub(r"[^\d]", "", part)
        if digits and 2 <= len(digits) <= 8:
            val = int(digits)
            if 10 <= val <= 10_000_000:
                return val

    return None


# ─────────────────────────────────────────────
# BUILD RESULT DICT
# ─────────────────────────────────────────────
def build_result(platform_key, name, price, url, image, source_name,
                 rating=None, reviews=0, discount=0, mrp=None):

    pinfo = PLATFORMS.get(platform_key, {
        "name": source_name or platform_key.title(),
        "freeShip": False,
        "offers": [],
        "url": url or "#",
    })

    emi = None
    if price and price > 10000:
        emi = f"₹{price // 24:,}/mo"

    return {
        "platform": platform_key,
        "name":     (name or "").strip()[:120],
        "price":    price,
        "mrp":      mrp or price,
        "discount": discount,
        "rating":   rating,
        "reviews":  int(reviews) if reviews else 0,
        "image":    image,
        "url":      url or pinfo.get("url", "#"),
        "freeShip": pinfo.get("freeShip", False),
        "emi":      emi,
        "offers":   pinfo.get("offers", []),
    }


# ─────────────────────────────────────────────
# SEARCH STRATEGY 1: Google Shopping tab
# ─────────────────────────────────────────────
def search_shopping(query):
    print(f"  [Shopping] Searching: {query}")
    try:
        from serpapi import GoogleSearch
        params = {
            "engine":   "google_shopping",
            "q":        query,
            "gl":       "in",
            "hl":       "en",
            "num":      40,
            "api_key":  SERPAPI_KEY,
        }
        results = GoogleSearch(params).get_dict()
        items   = results.get("shopping_results", [])
        print(f"  [Shopping] Got {len(items)} results")
        return items
    except Exception as e:
        print(f"  [Shopping] Error: {e}")
        return []


# ─────────────────────────────────────────────
# SEARCH STRATEGY 2: Google main search
# Gets inline shopping results + organic links
# ─────────────────────────────────────────────
def search_google(query):
    print(f"  [Google] Searching: {query}")
    try:
        from serpapi import GoogleSearch
        params = {
            "engine":  "google",
            "q":       f"buy {query} price India site:amazon.in OR site:flipkart.com OR site:myntra.com OR site:ajio.com OR site:meesho.com",
            "gl":      "in",
            "hl":      "en",
            "num":     10,
            "api_key": SERPAPI_KEY,
        }
        results  = GoogleSearch(params).get_dict()
        shopping = results.get("shopping_results", [])
        inline   = results.get("inline_shopping_results", [])
        ads      = results.get("ads", [])
        organic  = results.get("organic_results", [])

        all_items = shopping + inline + ads

        # Extract price from organic results too
        for org in organic[:5]:
            link  = org.get("link", "")
            pf    = detect_platform(link, org.get("source", ""))
            if not pf:
                continue
            # Try to find price in snippet
            snippet = org.get("snippet", "") + " " + org.get("title", "")
            price_match = re.search(r"₹\s?([\d,]+)", snippet)
            if price_match:
                price = parse_price(price_match.group(1))
                if price:
                    all_items.append({
                        "title":           org.get("title", query),
                        "link":            link,
                        "source":          org.get("source", ""),
                        "extracted_price": price,
                        "thumbnail":       org.get("thumbnail"),
                    })

        print(f"  [Google] Got {len(all_items)} items")
        return all_items
    except Exception as e:
        print(f"  [Google] Error: {e}")
        return []


# ─────────────────────────────────────────────
# SEARCH STRATEGY 3: Platform-specific searches
# Searches each major platform individually
# ─────────────────────────────────────────────
def search_platform_specific(query, platform_key):
    pinfo = PLATFORMS.get(platform_key)
    if not pinfo:
        return []

    domain = pinfo["domains"][0]
    print(f"  [{pinfo['name']}] Specific search: {query}")

    try:
        from serpapi import GoogleSearch
        params = {
            "engine":  "google_shopping",
            "q":       query,
            "gl":      "in",
            "hl":      "en",
            "num":     5,
            "api_key": SERPAPI_KEY,
        }
        results = GoogleSearch(params).get_dict()
        items   = results.get("shopping_results", [])

        # Filter to only this platform
        filtered = [
            item for item in items
            if detect_platform(
                item.get("link", "") or item.get("product_link", ""),
                item.get("source", "") or item.get("seller", "")
            ) == platform_key
        ]
        print(f"  [{pinfo['name']}] Found {len(filtered)} platform-specific results")
        return filtered
    except Exception as e:
        print(f"  [{pinfo['name']}] Error: {e}")
        return []


# ─────────────────────────────────────────────
# PROCESS ALL RAW ITEMS → platform_data dict
# ─────────────────────────────────────────────
def process_items(all_items):
    platform_data = {}  # platform_key -> result (keep cheapest)
    best_image    = None
    best_name     = ""

    for item in all_items:
        try:
            # ── Extract price ──────────────────────
            price = None

            # Try extracted_price first (most reliable)
            if item.get("extracted_price") is not None:
                price = parse_price(item["extracted_price"])

            # Fallback to price string
            if not price and item.get("price"):
                price = parse_price(item["price"])

            # Try product_price
            if not price and item.get("product_price"):
                price = parse_price(item["product_price"])

            if not price:
                continue

            # ── Detect platform ──────────────────────
            url    = item.get("link") or item.get("product_link") or item.get("url") or ""
            source = (
                item.get("source") or
                item.get("seller") or
                item.get("store")  or
                ""
            )
            pkey = detect_platform(url, source)

            if not pkey:
                # Try harder — check all text fields
                all_text = (url + " " + source + " " + str(item.get("title",""))).lower()
                for k, pinfo in PLATFORMS.items():
                    if any(kw in all_text for kw in pinfo["keywords"]):
                        pkey = k
                        break

            if not pkey:
                continue  # truly unknown platform, skip

            # ── Extract other fields ──────────────────
            name  = item.get("title") or item.get("name") or ""
            image = (
                item.get("thumbnail") or
                item.get("image")     or
                item.get("product_photo") or
                None
            )

            # Extract rating
            rating = None
            for rkey in ["rating", "store_rating", "product_star_rating"]:
                if item.get(rkey):
                    try:
                        rating = float(item[rkey])
                        if 0 < rating <= 5:
                            break
                        rating = None
                    except (ValueError, TypeError):
                        pass

            # Extract review count
            reviews = 0
            for revkey in ["reviews", "store_reviews", "product_num_ratings"]:
                if item.get(revkey):
                    try:
                        raw = str(item[revkey]).replace(",","").replace("+","")
                        if "k" in raw.lower():
                            reviews = int(float(raw.lower().replace("k","")) * 1000)
                        else:
                            r = re.sub(r"[^\d]", "", raw)
                            if r:
                                reviews = int(r)
                        if reviews > 0:
                            break
                    except Exception:
                        pass

            # ── Track best image & name ───────────────
            if image and not best_image:
                best_image = image
            if name and len(name) > len(best_name):
                best_name = name

            # ── Keep most relevant (first) per platform ────────────
            if pkey not in platform_data:
                platform_data[pkey] = build_result(
                    pkey, name, price, url, image, source,
                    rating=rating, reviews=reviews
                )

        except Exception as e:
            print(f"    Item processing error: {e}")
            continue

    return platform_data, best_image, best_name


# ─────────────────────────────────────────────
# FINALIZE: compute MRP + discounts
# ─────────────────────────────────────────────
def finalize(platform_data, best_image):
    if not platform_data:
        return []

    prices  = [d["price"] for d in platform_data.values() if d.get("price")]
    max_p   = max(prices)
    mrp     = int(max_p * 1.22)  # estimate MRP

    results = []
    for pkey, data in platform_data.items():
        data["mrp"]      = mrp
        data["discount"] = max(0, round((1 - data["price"] / mrp) * 100))
        if not data.get("image") and best_image:
            data["image"] = best_image
        results.append(data)

    results.sort(key=lambda x: x["price"])
    return results


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────
def scrape_all(query):
    print(f"\n{'='*55}")
    print(f"  SmartCart searching: '{query}'")
    print(f"{'='*55}")

    if not SERPAPI_KEY:
        print("  ERROR: SERPAPI_KEY not set in .env")
        return []

    # ── Strategy 1: Google Shopping ──────────────
    all_items = search_shopping(query)

    # ── Strategy 2: If few results, try Google main ──
    if len(all_items) < 4:
        print("  Few results — trying Google main search…")
        all_items += search_google(query)

    # ── Process all items ─────────────────────────
    platform_data, best_image, best_name = process_items(all_items)

    # ── Strategy 3: If key platforms missing, search them directly ──
    key_platforms = ["amazon", "flipkart"]
    missing = [p for p in key_platforms if p not in platform_data]

    if missing and len(all_items) > 0:
        print(f"  Missing platforms: {missing} — trying targeted search…")
        for pkey in missing:
            extra = search_platform_specific(query, pkey)
            if extra:
                extra_data, extra_img, extra_name = process_items(extra)
                for k, v in extra_data.items():
                    if k not in platform_data:
                        platform_data[k] = v
                if not best_image and extra_img:
                    best_image = extra_img

    # ── Retry with simplified query if still empty ──
    if not platform_data:
        # Try first 2-3 words of query
        words  = query.split()
        short  = " ".join(words[:min(3, len(words))])
        if short != query:
            print(f"  No results — retrying with shorter query: '{short}'")
            retry_items = search_shopping(short)
            if retry_items:
                platform_data, best_image, best_name = process_items(retry_items)

    if not platform_data:
        print(f"  No results found for: '{query}'")
        return []

    # ── Finalize ──────────────────────────────────
    results = finalize(platform_data, best_image)

    # ── Summary ───────────────────────────────────
    print(f"\n  Results for '{query}':")
    for r in results:
        pname = PLATFORMS.get(r["platform"], {}).get("name", r["platform"])
        print(f"    {pname:<16}  ₹{r['price']:>9,}   {r['discount']}% off")
    print(f"\n  Total: {len(results)} platforms found")
    print(f"{'='*55}\n")

    return results


# ─────────────────────────────────────────────
# TEST — run directly: python scraper.py
# ─────────────────────────────────────────────
if __name__ == "__main__":
    q = input("Product to search: ").strip()
    if not q:
        q = "boAt Airdopes 141"

    if not SERPAPI_KEY:
        print("\nERROR: Add SERPAPI_KEY to your .env file first")
        print("  SERPAPI_KEY=your_key_here")
        exit(1)

    results = scrape_all(q)

    if results:
        print(f"\n{'='*55}")
        print(f"  FINAL RESULTS — {len(results)} platforms")
        print(f"{'='*55}")
        for r in results:
            print(f"\n  Platform : {r['platform']}")
            print(f"  Name     : {r['name'][:60]}")
            print(f"  Price    : ₹{r['price']:,}")
            print(f"  Discount : {r['discount']}%")
            print(f"  Rating   : {r['rating']}")
            print(f"  URL      : {r['url'][:60]}")
    else:
        print("\nNo results found. Check SERPAPI_KEY and try again.")