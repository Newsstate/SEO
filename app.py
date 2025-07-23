
from flask import Flask, render_template, request, jsonify
import requests, json, re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

app = Flask(__name__)

def fetch_pagespeed_data(url):
    key = "YOUR_GOOGLE_PAGESPEED_API_KEY"  # Replace with your API key
    api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy=desktop&key={key}"
    try:
        r = requests.get(api_url)
        data = r.json()
        lighthouse = data.get('lighthouseResult', {})
        return {
            "performance_score": lighthouse.get("categories", {}).get("performance", {}).get("score", 0) * 100,
            "lcp": lighthouse.get("audits", {}).get("largest-contentful-paint", {}).get("displayValue", ""),
            "fcp": lighthouse.get("audits", {}).get("first-contentful-paint", {}).get("displayValue", ""),
            "cls": lighthouse.get("audits", {}).get("cumulative-layout-shift", {}).get("displayValue", ""),
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_ip_geolocation(ip=""):
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}")
        return r.json()
    except:
        return {}

def fetch_sitemap_and_robots(domain):
    sitemap_url = urljoin(domain, "/sitemap.xml")
    robots_url = urljoin(domain, "/robots.txt")
    try:
        sitemap = requests.get(sitemap_url).text[:500]
    except:
        sitemap = "Not accessible"
    try:
        robots = requests.get(robots_url).text[:500]
    except:
        robots = "Not accessible"
    return sitemap, robots

def seo_audit(url):
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    try:
        res = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'}, verify=True)
    except requests.exceptions.SSLError:
        res = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'}, verify=False)

    soup = BeautifulSoup(res.text, 'html.parser')
    domain = urlparse(url).netloc

    title = soup.title.string if soup.title else ''
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    description = meta_desc['content'] if meta_desc else ''
    meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
    keywords = meta_keywords['content'] if meta_keywords else ''
    canonical = soup.find('link', rel='canonical')
    canonical_href = canonical['href'] if canonical else ''
    canonical_status = "self" if canonical_href == url else "no"
    robots_tag = soup.find('meta', attrs={'name': 'robots'})
    robots_content = robots_tag['content'] if robots_tag else 'not set'
    lang = soup.html.get('lang') if soup.html else 'not set'
    published = soup.find(attrs={'property': 'article:published_time'})
    modified = soup.find(attrs={'property': 'article:modified_time'})
    pub_date = published['content'] if published else ''
    mod_date = modified['content'] if modified else ''
    author_tag = soup.find(attrs={'rel': 'author'})
    author_link = author_tag['href'] if author_tag else ''
    breadcrumb = bool(soup.find_all("nav", attrs={"aria-label": "breadcrumb"}))
    schemas = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string)
            if isinstance(data, list): schemas.extend(data)
            else: schemas.append(data)
        except:
            pass
    max_img_preview = 'no'
    if robots_tag and 'max-image-preview:large' in robots_tag.get('content', '').lower():
        max_img_preview = 'yes'

    external_links = soup.find_all('a', href=True)
    ext_total = 0
    ext_nofollow = 0
    for link in external_links:
        href = link['href']
        if href.startswith('http') and domain not in href:
            ext_total += 1
            rel = link.get('rel', [])
            if 'nofollow' in rel:
                ext_nofollow += 1

    broken_links = []
    for link in soup.find_all('a', href=True):
        href = urljoin(url, link['href'])
        try:
            r = requests.head(href, timeout=3)
            if r.status_code >= 400:
                broken_links.append(href)
        except:
            broken_links.append(href)

    return {
        "title": title,
        "description": description,
        "keywords": keywords,
        "canonical": canonical_href,
        "canonical_status": canonical_status,
        "robots": robots_content,
        "lang": lang,
        "published": pub_date,
        "modified": mod_date,
        "author": author_link,
        "breadcrumb": breadcrumb,
        "schema_count": len(schemas),
        "max_image_preview": max_img_preview,
        "external_links_total": ext_total,
        "external_links_nofollow": ext_nofollow,
        "broken_links": broken_links[:10]
    }
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    url = request.form['url']
    if not url.startswith('http'):
        url = 'https://' + url

    seo = seo_audit(url)
    speed = fetch_pagespeed_data(url)
    
    geo = fetch_ip_geolocation()
    sitemap, robots_txt = fetch_sitemap_and_robots(url)

    return jsonify({
        "seo": seo,
        "pagespeed": speed,
       
        "ip_geo": geo,
        "sitemap": sitemap,
        "robots_txt": robots_txt
    })

if __name__ == '__main__':
    app.run(debug=True)
