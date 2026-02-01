#!/usr/bin/env python3
"""
Letterboxd Watchlist Streaming Checker - Fast Edition
"""

import requests
from bs4 import BeautifulSoup
import re
import os
import webbrowser
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
CACHE_FILE = os.path.join(SCRIPT_DIR, ".cache.json")
CACHE_HOURS = 6

# Default config (your settings)
DEFAULT_CONFIG = {
    "username": "mrbeeef",
    "services": ["Netflix", "Amazon Prime Video", "Hulu", "Max"],
    "name": "sophie"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_CONFIG

CONFIG = load_config()
LETTERBOXD_USERNAME = CONFIG.get("username", "mrbeeef")
USER_SERVICES = CONFIG.get("services", ["Netflix", "Amazon Prime Video", "Hulu", "Max"])
USER_NAME = CONFIG.get("name", "friend")


def load_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
                if datetime.fromisoformat(cache.get('timestamp', '2000-01-01')) > datetime.now() - timedelta(hours=CACHE_HOURS):
                    return cache.get('data')
    except:
        pass
    return None


def save_cache(data):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({'timestamp': datetime.now().isoformat(), 'data': data}, f)
    except:
        pass


def get_watchlist_films(username):
    films = []
    page = 1
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

    while True:
        url = f"https://letterboxd.com/{username}/watchlist/page/{page}/"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            break

        soup = BeautifulSoup(response.text, "html.parser")
        film_elements = soup.select("div[data-component-class='LazyPoster']")
        if not film_elements:
            break

        for el in film_elements:
            name = el.get("data-item-name", "")
            slug = el.get("data-item-slug", "")
            if name and slug:
                films.append({"name": name, "slug": slug})
        page += 1

    return films


def search_justwatch(film):
    """Search JustWatch for a single film."""
    search_query = re.sub(r'\s*\(\d{4}\)\s*$', '', film["name"]).strip()

    query = """
    query GetSearchTitles($searchTitlesFilter: TitleFilter!, $country: Country!, $language: Language!) {
        popularTitles(filter: $searchTitlesFilter, country: $country, first: 3) {
            edges {
                node {
                    content(country: $country, language: $language) {
                        title
                        originalReleaseYear
                        posterUrl
                    }
                    offers(country: $country, platform: WEB) {
                        monetizationType
                        standardWebURL
                        package { clearName }
                    }
                }
            }
        }
    }
    """

    try:
        response = requests.post(
            "https://apis.justwatch.com/graphql",
            json={"query": query, "variables": {
                "searchTitlesFilter": {"searchQuery": search_query, "objectTypes": ["MOVIE"]},
                "country": "US", "language": "en"
            }},
            headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"},
            timeout=8
        )

        if response.status_code != 200:
            return {**film, "services": {}, "poster_url": None}

        edges = response.json().get("data", {}).get("popularTitles", {}).get("edges", [])

        clean_name = search_query.lower()
        for edge in edges:
            node = edge.get("node", {})
            content = node.get("content", {})
            title = content.get("title", "").lower()

            if title == clean_name or clean_name in title or title in clean_name:
                offers = node.get("offers") or []
                services = {}
                for offer in offers:
                    if offer.get("monetizationType") == "FLATRATE":
                        svc = offer.get("package", {}).get("clearName", "")
                        url = offer.get("standardWebURL", "")
                        if svc and svc not in services:
                            services[svc] = url

                poster = content.get("posterUrl")
                if poster:
                    poster = f"https://images.justwatch.com{poster}".replace("{profile}", "s592")

                return {**film, "services": services, "poster_url": poster}

        return {**film, "services": {}, "poster_url": None}

    except:
        return {**film, "services": {}, "poster_url": None}


def check_all_films(films):
    """Check all films in parallel."""
    results = {"available": [], "unavailable": []}

    print(f"Checking {len(films)} films...", flush=True)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(search_justwatch, film): film for film in films}

        for future in as_completed(futures):
            film_data = future.result()

            # Check if on user's services
            matched_service = None
            stream_url = None
            for user_svc in USER_SERVICES:
                for jw_svc, url in film_data.get("services", {}).items():
                    if user_svc.lower() in jw_svc.lower() or jw_svc.lower() in user_svc.lower():
                        matched_service = user_svc
                        stream_url = url
                        break
                if matched_service:
                    break

            if matched_service:
                results["available"].append({
                    "name": film_data["name"],
                    "slug": film_data["slug"],
                    "service": matched_service,
                    "stream_url": stream_url,
                    "poster_url": film_data.get("poster_url")
                })
            else:
                other = list(film_data.get("services", {}).keys())[:2]
                results["unavailable"].append({
                    "name": film_data["name"],
                    "slug": film_data["slug"],
                    "other_services": other,
                    "poster_url": film_data.get("poster_url")
                })

    return results


def generate_html(results):
    available = results["available"]
    unavailable = results["unavailable"]

    # Group by service
    by_service = {"Max": [], "Netflix": [], "Amazon Prime Video": [], "Hulu": []}
    for film in available:
        svc = film["service"]
        if svc in by_service:
            by_service[svc].append(film)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>sophie's watchlist</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Graphik:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-dark: #14181c;
            --bg-darker: #0d1114;
            --bg-card: #242c34;
            --bg-hover: #2c3440;
            --border: #303840;
            --text: #9ab;
            --text-bright: #fff;
            --green: #00e054;
            --orange: #ff8000;
            --blue: #40bcf4;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Graphik', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-darker);
            color: var(--text);
            min-height: 100vh;
            font-size: 14px;
            line-height: 1.5;
        }}
        a {{ color: inherit; text-decoration: none; }}

        /* Header */
        .header {{
            background: var(--bg-dark);
            border-bottom: 1px solid var(--border);
            padding: 0 40px;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .header-inner {{
            max-width: 1200px;
            margin: 0 auto;
            height: 56px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .logo {{
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text-bright);
            font-weight: 600;
            font-size: 15px;
            letter-spacing: 0.5px;
        }}
        .logo-dots {{
            display: flex;
            gap: 2px;
        }}
        .logo-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }}
        .logo-dot:nth-child(1) {{ background: var(--orange); }}
        .logo-dot:nth-child(2) {{ background: var(--green); }}
        .logo-dot:nth-child(3) {{ background: var(--blue); }}
        .nav {{
            display: flex;
            gap: 24px;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }}
        .nav a {{
            color: var(--text);
            transition: color 0.15s;
        }}
        .nav a:hover, .nav a.active {{
            color: var(--text-bright);
        }}

        /* Hero */
        .hero {{
            background: linear-gradient(to bottom, var(--bg-dark), var(--bg-darker));
            padding: 50px 40px 60px;
            text-align: center;
            border-bottom: 1px solid var(--border);
        }}
        .hero h1 {{
            color: var(--text-bright);
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 8px;
            letter-spacing: -0.01em;
        }}
        .hero h1 span {{
            color: var(--green);
        }}
        .hero-sub {{
            color: var(--text);
            font-size: 15px;
        }}
        .hero-stats {{
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-top: 30px;
        }}
        .stat {{
            text-align: center;
        }}
        .stat-num {{
            font-size: 32px;
            font-weight: 600;
            color: var(--text-bright);
            line-height: 1;
        }}
        .stat-label {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            margin-top: 6px;
            color: var(--text);
        }}

        /* Main */
        .main {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px;
        }}

        /* Section */
        .section {{
            margin-bottom: 50px;
        }}
        .section-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border);
        }}
        .service-icon {{
            width: 28px;
            height: 28px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 12px;
            color: #fff;
        }}
        .service-icon.netflix {{ background: #e50914; }}
        .service-icon.max {{ background: #002be7; }}
        .service-icon.prime {{ background: #00a8e1; }}
        .service-icon.hulu {{ background: #1ce783; color: #000; }}
        .service-icon.none {{ background: var(--bg-card); color: var(--text); }}
        .section-title {{
            font-size: 16px;
            font-weight: 500;
            color: var(--text-bright);
            flex: 1;
        }}
        .section-count {{
            font-size: 12px;
            color: var(--text);
            background: var(--bg-card);
            padding: 3px 10px;
            border-radius: 10px;
        }}

        /* Poster Grid - Letterboxd style */
        .posters {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 8px;
        }}
        .poster-card {{
            position: relative;
            border-radius: 4px;
            overflow: hidden;
            background: var(--bg-card);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            cursor: pointer;
        }}
        .poster-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        }}
        .poster-card::before {{
            content: '';
            position: absolute;
            inset: 0;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 4px;
            pointer-events: none;
            z-index: 2;
        }}
        .poster-card:hover::before {{
            border-color: var(--green);
            box-shadow: inset 0 0 0 1px var(--green);
        }}
        .poster-img {{
            width: 100%;
            aspect-ratio: 2/3;
            object-fit: cover;
            display: block;
        }}
        .poster-placeholder {{
            width: 100%;
            aspect-ratio: 2/3;
            background: linear-gradient(135deg, var(--bg-card), var(--bg-hover));
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 16px;
            text-align: center;
            font-size: 12px;
            color: var(--text);
        }}
        .poster-overlay {{
            position: absolute;
            inset: 0;
            background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 60%);
            opacity: 0;
            transition: opacity 0.2s;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            padding: 12px;
        }}
        .poster-card:hover .poster-overlay {{
            opacity: 1;
        }}
        .poster-title {{
            font-size: 13px;
            font-weight: 500;
            color: #fff;
            line-height: 1.3;
        }}
        .poster-service {{
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-top: 4px;
            color: var(--green);
        }}

        /* Unavailable */
        .unavailable .poster-card {{
            opacity: 0.5;
        }}
        .unavailable .poster-card:hover {{
            opacity: 0.8;
        }}
        .unavailable .poster-card:hover::before {{
            border-color: var(--text);
            box-shadow: none;
        }}
        .unavailable .poster-service {{
            color: var(--text);
        }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 40px;
            color: var(--text);
            font-size: 12px;
            border-top: 1px solid var(--border);
            margin-top: 40px;
        }}
        .footer a {{
            color: var(--green);
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <div class="logo">
                <div class="logo-dots">
                    <div class="logo-dot"></div>
                    <div class="logo-dot"></div>
                    <div class="logo-dot"></div>
                </div>
                {USER_NAME}'s watchlist
            </div>
            <nav class="nav">
                <a href="https://letterboxd.com/mrbeeef/watchlist/" target="_blank">Full List</a>
                <a href="https://letterboxd.com/mrbeeef/" target="_blank">Profile</a>
            </nav>
        </div>
    </header>

    <div class="hero">
        <h1>What's streaming <span>tonight</span>?</h1>
        <p class="hero-sub">Your Letterboxd watchlist, filtered by your services</p>
        <div class="hero-stats">
            <div class="stat">
                <div class="stat-num">{len(available)}</div>
                <div class="stat-label">Ready to watch</div>
            </div>
            <div class="stat">
                <div class="stat-num">{len(available) + len(unavailable)}</div>
                <div class="stat-label">In watchlist</div>
            </div>
        </div>
    </div>

    <main class="main">
"""

    service_config = [
        ("Max", "max", "M"),
        ("Netflix", "netflix", "N"),
        ("Amazon Prime Video", "prime", "P"),
        ("Hulu", "hulu", "H"),
    ]

    for svc_name, css_class, letter in service_config:
        films = by_service.get(svc_name, [])
        if not films:
            continue

        display_name = "Prime Video" if svc_name == "Amazon Prime Video" else svc_name

        html += f"""
        <section class="section">
            <div class="section-header">
                <div class="service-icon {css_class}">{letter}</div>
                <span class="section-title">{display_name}</span>
                <span class="section-count">{len(films)} film{"s" if len(films) != 1 else ""}</span>
            </div>
            <div class="posters">
"""
        for film in films:
            title = re.sub(r'\s*\(\d{4}\)\s*$', '', film["name"])
            url = film.get("stream_url") or f"https://letterboxd.com/film/{film['slug']}/"
            poster = film.get("poster_url")

            if poster:
                img_html = f'<img class="poster-img" src="{poster}" alt="{title}" loading="lazy">'
            else:
                img_html = f'<div class="poster-placeholder">{title}</div>'

            html += f"""                <a href="{url}" target="_blank" class="poster-card">
                    {img_html}
                    <div class="poster-overlay">
                        <div class="poster-title">{title}</div>
                        <div class="poster-service">Watch on {display_name}</div>
                    </div>
                </a>
"""
        html += """            </div>
        </section>
"""

    # Unavailable section
    if unavailable:
        html += f"""
        <section class="section unavailable">
            <div class="section-header">
                <div class="service-icon none">—</div>
                <span class="section-title">Not on your services</span>
                <span class="section-count">{len(unavailable)} films</span>
            </div>
            <div class="posters">
"""
        for film in unavailable:
            title = re.sub(r'\s*\(\d{4}\)\s*$', '', film["name"])
            url = f"https://letterboxd.com/film/{film['slug']}/"
            poster = film.get("poster_url")
            other = ", ".join(film.get("other_services", [])) if film.get("other_services") else "Not streaming"

            if poster:
                img_html = f'<img class="poster-img" src="{poster}" alt="{title}" loading="lazy">'
            else:
                img_html = f'<div class="poster-placeholder">{title}</div>'

            html += f"""                <a href="{url}" target="_blank" class="poster-card">
                    {img_html}
                    <div class="poster-overlay">
                        <div class="poster-title">{title}</div>
                        <div class="poster-service">{other}</div>
                    </div>
                </a>
"""
        html += """            </div>
        </section>
"""

    html += """    </main>

    <footer class="footer">
        Data from <a href="https://www.justwatch.com/" target="_blank">JustWatch</a>
    </footer>
</body>
</html>
"""
    return html


def main():
    # Try cache first
    cached = load_cache()
    if cached:
        print("Using cached results (less than 6 hours old)")
        results = cached
    else:
        print(f"Fetching watchlist for {LETTERBOXD_USERNAME}...")
        films = get_watchlist_films(LETTERBOXD_USERNAME)

        if not films:
            print("No films found.")
            return

        results = check_all_films(films)
        save_cache(results)
        print("Done!")

    html = generate_html(results)

    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.html")
    with open(html_path, "w") as f:
        f.write(html)

    webbrowser.open(f"file://{html_path}")


if __name__ == "__main__":
    main()
