# olifan_scraper.py
import asyncio
import json
import os
import re
import time
from urllib.parse import urljoin, urlparse
from typing import List 

import aiohttp
from bs4 import BeautifulSoup
from urllib import robotparser
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# 🚀 IMPORTS POUR L'OCR
import pytesseract
from PIL import Image
# -----------------------------

# 🚩 CONFIGURATION TESSERACT 🚩
# ⚠️ REMPLACEZ CE CHEMIN PAR LE CHEMIN D'ACCÈS RÉEL
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe" 
try:
    # Définit le chemin pour pytesseract
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    print(f"Tesseract path set to: {TESSERACT_PATH}")
except Exception:
    print("WARNING: Failed to set Tesseract path. OCR will likely fail.")
# ----------------------------------------------------------------------

# ---------- Config ----------
USER_AGENT = "OlifanCrawlerBot/1.0 (+https://olifan.com)"
MAX_PAGES = 200  # Reduced for Olifan site
MAX_CONCURRENT_DOWNLOADS = 6
IMAGE_DOWNLOAD_TIMEOUT = 20
OUTPUT_JSON = "olifan_scraped_data.json" 
IMAGES_DIR = "olifan_images"
# ----------------------------

# 🚀 FONCTION OCR
def extract_ocr_text(image_path: str) -> str:
    """
    Tente d'extraire le texte de l'image spécifiée par le chemin d'accès.
    """
    try:
        # Ouvre le fichier depuis le disque
        img = Image.open(image_path)
        
        # Exécute l'OCR
        ocr_result = pytesseract.image_to_string(img, lang='fra').strip()  # French language
        
        return ocr_result
        
    except pytesseract.TesseractNotFoundError:
        print(f"\n[OCR ERROR] Tesseract introuvable. Installez Tesseract ou corrigez TESSERACT_PATH.")
        return ""
    except Exception:
        # Gère les fichiers corrompus ou d'autres erreurs
        return ""

# FONCTION PRÉCÉDEMMENT AJOUTÉE: Extraction du contenu principal (Boilerplate Removal)
def extract_main_content_from_text(text: str) -> str:
    """Nettoie le texte en retirant les éléments de boilerplate (headers, footers, navigation)."""
    if len(text) > 1000:
        lines = text.split('\n')
        cleaned_lines = [line for line in lines if len(line.strip()) > 40 or line.strip() == '']
        cleaned_text = '\n'.join(cleaned_lines).strip()
        
        if len(cleaned_text) > 200:
            return cleaned_text
    
    return text

# Normalize domains
def normalize_domain(url_or_netloc: str) -> str:
    if not url_or_netloc:
        return ""
    if "://" in url_or_netloc:
        netloc = urlparse(url_or_netloc).netloc.lower()
    else:
        netloc = url_or_netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc

# Safe folder names
def slugify_url(url: str) -> str:
    u = url.replace("://", "_").replace("/", "_").strip("_")
    u = re.sub(r"[^A-Za-z0-9_\-\.]", "_", u)
    return u[:200]

# Cleaning functions (pre-processing markdown)
def clean_markdown_empty_images(md: str) -> str:
    md = re.sub(r'!\s*\[\s*\]\s*\(\s*\)', ' ', md)
    md = re.sub(r'!\s*\[.*?\]\s*\(\s*\)', ' ', md)
    md = re.sub(r'!\s*!?\s*\]\(\s*\)', ' ', md)
    return md

def clean_text_bulk(text: str) -> str:
    if not text:
        return ""
    text = clean_markdown_empty_images(text)
    text = re.sub(r'\[([^\]]{1,200}?)\]\((?:[^)]*?)\)', r'\1', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'https?://\S+', ' ', text)

    # Olifan-specific menu words in French
    menu_words = [
        r"\bAccueil\b", r"\bÀ propos\b", r"\bServices\b",
        r"\bContact\b", r"\bBlog\b", r"\bActualités\b",
        r"\bNos solutions\b", r"\bExpertise\b", r"\bRéférences\b",
        r"\bCarrières\b", r"\bMentions légales\b", r"\bPolitique\b"
    ]
    text = re.sub("|".join(menu_words), " ", text, flags=re.IGNORECASE)
    text = re.sub(r'[*•#>\-]{2,}', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# Robots.txt check
def is_allowed_by_robots(base_url: str, user_agent: str, test_url: str) -> bool:
    try:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, test_url)
    except Exception:
        return True

# Async downloader
async def download_image(session, url, dest_path, sem):
    async with sem:
        try:
            async with session.get(url, timeout=IMAGE_DOWNLOAD_TIMEOUT) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    with open(dest_path, "wb") as f:
                        f.write(content)
                    return True
        except Exception:
            return False
    return False

# Extract and filter image URLs
async def extract_image_urls_from_html(base_url: str, html: str):
    soup = BeautifulSoup(html or "", "html.parser")
    imgs = soup.find_all("img")

    urls = []
    for img in imgs:
        src = img.get("src") or img.get("data-src") or img.get("data-lazy")
        if not src:
            continue
        full = urljoin(base_url, src)
        if full.startswith("//"):
            full = "https:" + full
        urls.append(full)

    # Remove duplicates
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)

    # Filters: only real images
    final = []
    for u in out:
        low = u.lower()
        # Only keep real image formats
        if not any(low.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]):
            continue
        # Skip icons, favicons, SVGs, placeholders
        if "icon" in low or "favicon" in low or "logo" in low:
            continue
        if ".svg" in low:
            continue
        if "placeholder" in low or "blank" in low:
            continue
        final.append(u)

    return final

# Main crawl function for Olifan
async def crawl_olifan_site():
    base_url = "https://olifangroup.com"  # Olifan Group website
    
    normalized_domain = normalize_domain(base_url)
    print(f"Starting crawl for domain: {normalized_domain}")

    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    async with AsyncWebCrawler(config=browser_config) as crawler:

        print(f"🔍 Crawling main page: {base_url}")
        main_result = await crawler.arun(url=base_url, config=run_config)

        if not main_result.success:
            print("Failed to crawl main page:", main_result.error_message)
            return

        # Get internal links from main page
        raw_internal = main_result.links.get("internal", []) or []
        print(f"Found {len(raw_internal)} internal link entries on main page.")

        to_crawl = []
        for entry in raw_internal:
            href = entry.get("href") if isinstance(entry, dict) else entry
            if not href:
                continue

            full = urljoin(base_url, href)
            if full.startswith("//"):
                full = "https:" + full

            if normalize_domain(full) != normalized_domain:
                continue
            if not is_allowed_by_robots(base_url, USER_AGENT, full):
                continue

            to_crawl.append(full)

        # Add common Olifan Group pages manually
        additional_pages = [
            "https://olifangroup.com/services",
            "https://olifangroup.com/a-propos",
            "https://olifangroup.com/contact",
            "https://olifangroup.com/expertise",
            "https://olifangroup.com/solutions",
            "https://olifangroup.com/references"
        ]
        
        for page in additional_pages:
            if page not in to_crawl:
                to_crawl.append(page)

        # dedupe and limit
        seen = set()
        filtered = []
        for u in to_crawl:
            if u not in seen:
                seen.add(u)
                filtered.append(u)
            if len(filtered) >= MAX_PAGES:
                break

        print(f"📌 Pages to crawl: {len(filtered)}")

        # crawl pages in chunks
        chunk_size = 20  # Smaller chunks for better reliability
        results = []
        for i in range(0, len(filtered), chunk_size):
            chunk = filtered[i:i + chunk_size]
            print(f"⏳ Crawling chunk {i//chunk_size + 1} ({len(chunk)} pages)...")
            chunk_results = await crawler.arun_many(urls=chunk, config=run_config)
            results.extend(chunk_results)
            time.sleep(1)  # Be respectful to the server

    os.makedirs(IMAGES_DIR, exist_ok=True)
    scraped = []
    sem = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

    async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session:

        for res in results:
            if not res or not res.success:
                continue

            page_url = res.url
            raw_md = res.markdown or ""
            raw_html = getattr(res, "html", "") or ""

            # 1. Nettoyage standard et suppression du boilerplate
            cleaned_md = clean_text_bulk(raw_md)
            cleaned_md = clean_markdown_empty_images(cleaned_md)
            cleaned_md = re.sub(r'\s+', ' ', cleaned_md).strip()
            final_text = extract_main_content_from_text(cleaned_md)

            # Extract images and download them
            image_urls = await extract_image_urls_from_html(page_url, raw_html)
            saved_images = []

            if image_urls:
                page_slug = slugify_url(page_url)
                save_folder = os.path.join(IMAGES_DIR, page_slug)
                os.makedirs(save_folder, exist_ok=True)

                tasks = []
                for img_url in image_urls:
                    fname = img_url.split("/")[-1].split("?")[0]
                    safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', fname)[:180]
                    dest = os.path.join(save_folder, safe_name)

                    if os.path.exists(dest):
                        saved_images.append(dest)
                        continue

                    tasks.append(download_image(session, img_url, dest, sem))

                if tasks:
                    results_downloads = await asyncio.gather(*tasks, return_exceptions=True)
                    for idx, ok in enumerate(results_downloads):
                        if ok:
                            fname = image_urls[idx].split("/")[-1].split("?")[0]
                            safe = re.sub(r'[^A-Za-z0-9._-]', '_', fname)[:180]
                            saved_images.append(os.path.join(save_folder, safe))

            # 3. Exécuter l'OCR sur les images téléchargées
            image_texts = []
            for img_path in saved_images:
                ocr_result = extract_ocr_text(img_path)
                image_texts.append(ocr_result)
            
            # Conservation uniquement des images pour lesquelles l'OCR a réussi à extraire du texte
            final_image_data = [(saved_images[i], image_texts[i]) for i in range(len(saved_images)) if image_texts[i]]
            
            # Mise à jour des listes pour le JSON
            final_saved_images = [path for path, text in final_image_data]
            final_image_texts = [text for path, text in final_image_data]
            
            print(f"   -> OCR: {len(final_image_texts)} image(s) avec du texte scrapé.")

            scraped.append({
                "url": page_url,
                "title": getattr(res, "title", "") or "",
                "text": final_text, 
                "image_count": len(final_saved_images), 
                "image_files": final_saved_images, 
                "image_texts": final_image_texts,
            })

            print(f"✅ {page_url} (images: {len(final_saved_images)})")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(scraped, f, ensure_ascii=False, indent=2)

    print(f"\n✨ Saved {len(scraped)} pages to {OUTPUT_JSON}")
    print(f"Images saved under {IMAGES_DIR}/<page_slug>/")

if __name__ == "__main__":
    asyncio.run(crawl_olifan_site())