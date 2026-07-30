#!/usr/bin/env python3
import json
import os
import sys
import shutil
from PIL import Image

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(SCRIPT_DIR, "../Apps/owoa_registry.json")
OUTPUT_HTML_PATH = os.path.join(SCRIPT_DIR, "index.html")

# Category color configurations (Brand-Adaptive Accent Themes)
THEMES = {
    "Medical": {
        "primary": "#0d9488",        # teal
        "primary_light": "#14b8a6",
        "primary_dark": "#0f766e",
        "glow": "rgba(13, 148, 136, 0.15)",
        "gradient": "linear-gradient(135deg, #0d9488 0%, #14b8a6 100%)"
    },
    "Photography": {
        "primary": "#ea580c",        # orange
        "primary_light": "#f97316",
        "primary_dark": "#c2410c",
        "glow": "rgba(249, 115, 22, 0.15)",
        "gradient": "linear-gradient(135deg, #ea580c 0%, #f97316 100%)"
    },
    "Productivity": {
        "primary": "#2563eb",        # blue
        "primary_light": "#3b82f6",
        "primary_dark": "#1d4ed8",
        "glow": "rgba(59, 130, 246, 0.15)",
        "gradient": "linear-gradient(135deg, #2563eb 0%, #3b82f6 100%)"
    },
    "Kids": {
        "primary": "#db2777",        # pink/purple
        "primary_light": "#ec4899",
        "primary_dark": "#be185d",
        "glow": "rgba(236, 72, 153, 0.15)",
        "gradient": "linear-gradient(135deg, #db2777 0%, #ec4899 100%)"
    },
    "General": {
        "primary": "#0f766e",        # dark teal
        "primary_light": "#0d9488",
        "primary_dark": "#115e59",
        "glow": "rgba(13, 148, 136, 0.15)",
        "gradient": "linear-gradient(135deg, #0f766e 0%, #0d9488 100%)"
    }
}

def get_theme(category):
    return THEMES.get(category, THEMES["General"])

def get_app_slug(app_id):
    """Convert app_id (snake_case) to URL friendly slug (hyphenated)"""
    return app_id.replace("_", "-")

def process_screenshots(app_id, app_slug):
    """Find, resize, and compress screenshots from fastlane to landing page images folder."""
    src_dir = os.path.join(SCRIPT_DIR, f"../Apps/{app_id}/fastlane/screenshots/id")
    if not os.path.exists(src_dir):
        src_dir = os.path.join(SCRIPT_DIR, f"../Apps/{app_id}/fastlane/screenshots/en-US")
        
    if not os.path.exists(src_dir):
        # Check if local screenshots folder already exists in the website directory
        local_img_dir = os.path.join(SCRIPT_DIR, f"images/{app_slug}")
        if os.path.exists(local_img_dir):
            slides = [f"images/{app_slug}/{f}" for f in sorted(os.listdir(local_img_dir)) if f.startswith("slide_")]
            if slides:
                return slides
        return []

    # Output directory
    dest_dir = os.path.join(SCRIPT_DIR, f"images/{app_slug}")
    os.makedirs(dest_dir, exist_ok=True)

    # Find the best screenshots (6.7-inch, 6.5-inch, 5.5-inch or general)
    all_files = os.listdir(src_dir)
    screens = []
    
    # Priority sizes
    priorities = ["6.7", "6.5", "5.5", "ipad", ".png"]
    chosen_size = None
    
    for size in priorities:
        matches = [f for f in all_files if size in f and f.startswith("slide_")]
        if matches:
            chosen_size = size
            screens = sorted(matches)
            break
            
    if not screens:
        # Fallback to any slide_ files
        screens = sorted([f for f in all_files if f.startswith("slide_")])

    if not screens:
        return []

    processed_relative_paths = []
    print(f"[*] Processing {len(screens)} screenshots for '{app_slug}' (size match: {chosen_size})...")
    
    for idx, screen_file in enumerate(screens):
        src_file_path = os.path.join(src_dir, screen_file)
        dest_filename = f"slide_{idx+1:02d}.jpg"
        dest_file_path = os.path.join(dest_dir, dest_filename)
        
        # Incremental compiler: check if destination exists and is newer than source file
        if os.path.exists(dest_file_path):
            src_mtime = os.path.getmtime(src_file_path)
            dest_mtime = os.path.getmtime(dest_file_path)
            if dest_mtime > src_mtime:
                # Validate that existing file is not corrupted/empty (min 30 KB)
                if os.path.getsize(dest_file_path) >= 30000:
                    processed_relative_paths.append(f"images/{app_slug}/{dest_filename}")
                    continue
        
        try:
            with Image.open(src_file_path) as img:
                # Resize keeping aspect ratio (max width 450px for fast loading web display)
                max_width = 450
                if img.width > max_width:
                    ratio = max_width / float(img.width)
                    new_height = int(float(img.height) * float(ratio))
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert to RGB and save as optimized JPG
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(dest_file_path, "JPEG", quality=85)
                
            # Quality assurance: verify output file size is not empty or too small (min 30 KB)
            file_size = os.path.getsize(dest_file_path)
            if file_size < 30000:
                raise ValueError(f"Compressed file size is too small ({file_size} bytes). Quality check failed.")
                
            processed_relative_paths.append(f"images/{app_slug}/{dest_filename}")
        except Exception as e:
            print(f"[-] Error: Failed to process screenshot '{screen_file}': {e}", file=sys.stderr)
            raise e # Reraise to trigger a compile failure
            
    return processed_relative_paths

def get_privacy_content(app):
    """Generate dynamic content for the privacy policy based on app category."""
    name = app["web_name"]
    category = app.get("category", "General")
    
    intro = f"Selamat datang di <strong>{name}</strong>. Kebijakan Privasi ini dirancang untuk menjelaskan bagaimana data Anda dikelola saat menggunakan layanan aplikasi kami."
    
    data_use = ""
    permissions = ""
    
    if category == "Medical":
        data_use = f"Di <strong>DR SAPTO LABS</strong>, kami sangat menghargai privasi dan kerahasiaan medis Anda. <strong>Aplikasi ini tidak mengumpulkan, tidak menyimpan, dan tidak membagikan data klinis, identitas pasien, hasil pengukuran medis, atau riwayat kalkulasi apa pun ke server eksternal kami maupun pihak ketiga.</strong><br><br>Seluruh perhitungan dilakukan secara 100% lokal offline di perangkat Anda."
        permissions = f"Aplikasi {name} dirancang secara minimalis:<br><ul><li><strong>Tidak memerlukan akses GPS / Lokasi.</strong></li><li><strong>Tidak memerlukan akses Kamera atau Galeri.</strong></li><li><strong>Tidak memerlukan koneksi internet untuk kalkulasi utama.</strong></li></ul>"
    elif category == "Photography":
        data_use = f"Di <strong>DR SAPTO LABS</strong>, kami memahami pentingnya privasi foto-foto Anda. <strong>Aplikasi ini memproses semua manipulasi gambar, pembuatan kolase, dan editing EXIF secara lokal di perangkat Anda. Foto-foto Anda tidak pernah diunggah, dikirim, atau disimpan di server kami.</strong>"
        permissions = f"Aplikasi {name} memerlukan izin berikut agar dapat berfungsi:<br><ul><li><strong>Akses Galeri/Foto (Storage Permission)</strong>: Untuk memilih foto yang akan diedit/digabungkan dan menyimpan hasilnya kembali ke galeri Anda.</li><li><strong>Kamera (Opsional)</strong>: Jika Anda memilih untuk mengambil foto langsung di dalam aplikasi.</li><li><strong>Tidak memerlukan pendaftaran akun</strong> atau informasi pribadi lainnya.</li></ul>"
    elif category == "Productivity":
        data_use = f"Aplikasi <strong>{name}</strong> berfokus pada produktivitas Anda. Semua data pengaturan, riwayat fokus, atau catatan tersimpan secara aman di dalam penyimpanan lokal perangkat Anda (*SharedPreferences* atau database lokal). Kami tidak mengumpulkan statistik aktivitas Anda ke server eksternal."
        permissions = f"Aplikasi {name} dirancang mandiri:<br><ul><li><strong>Tidak memerlukan izin sensitif</strong> seperti lokasi atau kontak.</li><li><strong>Bekerja sepenuhnya offline</strong> tanpa perlu koneksi internet aktif.</li></ul>"
    else:
        data_use = f"Kami berkomitmen untuk menjaga privasi Anda. Aplikasi <strong>{name}</strong> bekerja secara lokal di perangkat Anda. Kami tidak mengumpulkan, menyimpan, atau membagikan informasi pribadi atau data penggunaan Anda kepada pihak ketiga mana pun."
        permissions = f"Aplikasi ini bekerja secara mandiri dan offline tanpa memerlukan izin sistem yang sensitif, kecuali jika secara eksplisit diminta dan disetujui untuk fitur khusus aplikasi."

    return {
        "intro": intro,
        "data_use": data_use,
        "permissions": permissions
    }

def generate_header_js_snippet():
    """Script to inject immediately after <body> tag to prevent theme flash."""
    return """<script>
        (function() {
            const theme = localStorage.getItem('theme');
            if (theme === 'light') {
                document.body.classList.add('light-mode');
            }
        })();
    </script>"""

def generate_theme_switcher_button():
    return """<button id="themeToggle" class="theme-toggle-btn" aria-label="Toggle Theme">
        <i class="fa-solid fa-moon"></i>
    </button>"""

def generate_theme_switcher_js():
    return """
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const themeToggleBtn = document.getElementById('themeToggle');
            const themeToggleIcon = themeToggleBtn.querySelector('i');
            
            // Sync icon state with current class on body
            if (document.body.classList.contains('light-mode')) {
                themeToggleIcon.classList.replace('fa-moon', 'fa-sun');
            } else {
                themeToggleIcon.classList.replace('fa-sun', 'fa-moon');
            }
            
            themeToggleBtn.addEventListener('click', () => {
                document.body.classList.toggle('light-mode');
                let theme = 'dark';
                if (document.body.classList.contains('light-mode')) {
                    theme = 'light';
                    themeToggleIcon.classList.replace('fa-moon', 'fa-sun');
                } else {
                    themeToggleIcon.classList.replace('fa-sun', 'fa-moon');
                }
                localStorage.setItem('theme', theme);
            });
        });
    </script>
    """

def main():
    print("=== OWOA Landing Page Compiler & QA Validator ===")
    
    # 1. Load Registry
    if not os.path.exists(REGISTRY_PATH):
        print(f"[-] Error: Registry file not found at {REGISTRY_PATH}", file=sys.stderr)
        sys.exit(1)
        
    try:
        with open(REGISTRY_PATH, 'r') as f:
            registry = json.load(f)
    except Exception as e:
        print(f"[-] Error parsing JSON registry: {e}", file=sys.stderr)
        sys.exit(1)
        
    apps = registry.get("apps", [])
    
    # 2. QA Validation
    print("[*] Running QA checks on registry data...")
    validated_apps = []
    errors = 0
    
    for app in apps:
        app_id = app.get("id")
        status = app.get("status")
        
        # Skip apps without status
        if not status:
            continue
            
        name = app.get("name")
        package_name = app.get("package_name")
        web_logo = app.get("web_logo")
        web_description = app.get("web_description")
        
        # Check basic required fields
        if not app_id:
            print("[-] Error: App is missing 'id'")
            errors += 1
            continue
        if not name:
            print(f"[-] Error in app '{app_id}': Missing 'name'")
            errors += 1
            continue
        if not package_name:
            print(f"[-] Error in app '{app_id}': Missing 'package_name'")
            errors += 1
            continue
        if not web_logo:
            print(f"[-] Error in app '{app_id}': Missing 'web_logo'")
            errors += 1
            continue
        if not web_description:
            print(f"[-] Error in app '{app_id}': Missing 'web_description'")
            errors += 1
            continue
            
        # Verify app logo file exists (either in website images or in app resources)
        logo_path = os.path.join(SCRIPT_DIR, web_logo)
        if not os.path.exists(logo_path):
            print(f"[-] Error in app '{app_id}': App logo file '{logo_path}' does not exist!")
            errors += 1
            continue
            
        validated_apps.append(app)
        print(f"[+] App '{app_id}' passed QA checks ({status})")
        
    if errors > 0:
        print(f"\n[-] QA Validation Failed with {errors} error(s). Aborting generation.", file=sys.stderr)
        sys.exit(1)
        
    print(f"[+] QA Validation Successful! {len(validated_apps)} apps ready for compilation.")
    
    # 3. Categorize Apps
    featured_app = None
    other_apps = []
    
    for app in validated_apps:
        if app["status"] == "featured":
            featured_app = app
        else:
            other_apps.append(app)
            
    # Sort other apps: released first, then in_review, then migration
    status_order = {"released": 0, "in_review": 1, "migration": 2}
    other_apps.sort(key=lambda x: status_order.get(x["status"], 99))
    
    # 4. Process screenshots for all released/featured apps
    app_screenshots = {}
    for app in validated_apps:
        app_id = app["id"]
        app_slug = get_app_slug(app_id)
        screens = process_screenshots(app_id, app_slug)
        app_screenshots[app_id] = screens
    
    # 5. Generate Home index.html
    featured_html = ""
    if featured_app:
        features_html = ""
        for feat in featured_app.get("features", []):
            features_html += f"""                        <div class="feature-pill">
                            <i class="fa-solid {feat['icon']}"></i>
                            <span>{feat['text']}</span>
                        </div>\n"""
                        
        app_slug = get_app_slug(featured_app["id"])
        
        # Download/App Store buttons
        ios_id = featured_app.get("ios_app_id")
        ios_link = f"https://apps.apple.com/app/id{ios_id}" if ios_id else "#"
        
        # Carousel Slides
        slides = app_screenshots.get(featured_app["id"], [])
        slides_html = ""
        dots_html = ""
        for idx, slide_path in enumerate(slides):
            slides_html += f'<li class="carousel-slide"><img src="{slide_path}" alt="{featured_app["web_name"]} Slide {idx+1}"></li>\n'
            dots_html += f'<button class="carousel-dot {"active" if idx == 0 else ""}"></button>\n'
            
        # Fallback if no slides
        if not slides:
            slides_html = f'<li class="carousel-slide" style="display:flex; align-items:center; justify-content:center; background:#1e293b; color:#fff; aspect-ratio:9/19.5;"><div style="text-align:center;"><i class="fa-solid fa-mobile-screen" style="font-size:4rem; margin-bottom:15px; opacity:0.3;"></i><p>Tampilan Aplikasi</p></div></li>'
            dots_html = '<button class="carousel-dot active"></button>'
            
        featured_html = f"""        <!-- Aplikasi Unggulan: {featured_app['web_name']} -->
        <section class="featured-section" id="featured-app">
            <div class="featured-grid">
                <div class="featured-details">
                    <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 20px;">
                        <img src="{featured_app['web_logo']}" alt="{featured_app['web_name']} Logo" style="width: 72px; height: 72px; border-radius: 16px; border: 1px solid var(--border-color); box-shadow: 0 8px 16px rgba(0,0,0,0.3);">
                        <div>
                            <h3 class="gradient-text" style="margin-bottom: 2px; font-size: 1.8rem;">{featured_app['web_name']}</h3>
                            <p style="color: var(--primary-light); font-size: 0.95rem; font-weight: 600;">{featured_app.get("category", "Medical")}</p>
                        </div>
                    </div>
                    
                    <p class="featured-desc">{featured_app['web_description']}</p>
                    
                    <div class="features-list">
{features_html}                    </div>

                    <div class="download-buttons">
                        <!-- App Store Link -->
                        <a href="{ios_link}" class="store-btn" target="_blank" {"style='opacity:0.5; pointer-events:none;'" if not ios_id else ""}>
                            <i class="fa-brands fa-apple"></i>
                            <div class="store-btn-text">
                                <span class="store-btn-subtitle">Download on the</span>
                                <span class="store-btn-title">App Store</span>
                            </div>
                        </a>
                        
                        <!-- Google Play Link -->
                        <a href="https://play.google.com/store/apps/details?id={featured_app['package_name']}" class="store-btn store-btn-orange" target="_blank">
                            <i class="fa-brands fa-google-play"></i>
                            <div class="store-btn-text">
                                <span class="store-btn-subtitle">GET IT ON</span>
                                <span class="store-btn-title">Google Play</span>
                            </div>
                        </a>

                        <!-- Sub-landing Pages Links -->
                        <a href="{app_slug}/" class="privacy-btn">
                            <i class="fa-solid fa-circle-info" style="margin-right: 8px;"></i>Detail Aplikasi
                        </a>
                    </div>
                </div>

                <!-- Screenshots Carousel -->
                <div class="featured-media">
                    <div class="carousel-container">
                        <button class="carousel-control-btn carousel-prev-btn" id="prevBtn" aria-label="Slide sebelumnya">
                            <i class="fa-solid fa-chevron-left"></i>
                        </button>
                        <div class="carousel-track-container">
                            <ul class="carousel-track" id="carouselTrack">
                                {slides_html}                            </ul>
                        </div>
                        <button class="carousel-control-btn carousel-next-btn" id="nextBtn" aria-label="Slide berikutnya">
                            <i class="fa-solid fa-chevron-right"></i>
                        </button>
                        <div class="carousel-indicators" id="carouselIndicators">
                            {dots_html}                        </div>
                    </div>
                </div>
            </div>
        </section>"""

    # Generate Grid for Other Apps
    grid_html = ""
    for app in other_apps:
        status = app["status"]
        app_slug = get_app_slug(app["id"])
        
        # Tag style & label
        if status == "released":
            tag_class = "app-card-tag app-card-tag-featured"
            tag_label = "Rilis"
        elif status == "in_review":
            tag_class = "app-card-tag"
            tag_label = "Segera Hadir"
        else: # migration
            tag_class = "app-card-tag app-card-tag-migration"
            tag_label = "Migrasi"
            
        # Action Buttons based on Status
        actions_html = ""
        if status == "released":
            actions_html = f"""                    <a href="{app_slug}/" class="app-card-btn">
                        <i class="fa-solid fa-circle-info"></i> Info & Unduh
                    </a>
                    <a href="{app_slug}/privacy.html" class="app-card-btn app-card-btn-secondary">
                        Kebijakan Privasi
                    </a>"""
        elif status == "in_review":
            actions_html = f"""                    <a href="{app_slug}/" class="app-card-btn app-card-btn-secondary">
                        <i class="fa-solid fa-clock"></i> Detail Rencana
                    </a>
                    <button class="app-card-btn app-card-btn-disabled" onclick="alert('Aplikasi sedang dalam proses review di Google Play / App Store!')">
                        <i class="fa-solid fa-hourglass-half"></i> Menunggu Review
                    </button>"""
        else: # migration
            actions_html = f"""                    <button class="app-card-btn app-card-btn-disabled" disabled>
                        <i class="fa-solid fa-toolbox"></i> Proses Migrasi
                    </button>"""
                    
        grid_html += f"""            <!-- App Card: {app['web_name']} -->
            <div class="app-card">
                <span class="{tag_class}">{tag_label}</span>
                <div class="app-card-content">
                    <img src="{app['web_logo']}" alt="{app['web_name']} Logo" class="app-logo">
                    <h3>{app['web_name']}</h3>
                    <p>{app['web_description']}</p>
                </div>
                <div class="app-card-actions">
{actions_html}
                </div>
            </div>\n\n"""

    home_html = f"""<!DOCTYPE html>
<html lang="id">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dr. Sapto Labs - Solusi Aplikasi Kesehatan & Produktivitas</title>
    <!-- SEO Meta Tags -->
    <meta name="description" content="Inisiatif teknologi dr. Sapto Sutardi menghadirkan asisten klinis presisi & kalkulator obstetri offline serta aplikasi penunjang produktivitas.">
    <meta name="keywords" content="obstetri, kalkulator, usia kehamilan, hpl, hpht, hadlock, intergrowth, dr sapto, medis, puskesmas, lombok">
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="styles.css">
    <!-- FontAwesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>

<body>
    {generate_header_js_snippet()}
    {generate_theme_switcher_button()}

    <header>
        <h1>DR SAPTO LABS</h1>
        <p>Praktisi Medis. Inovator Digital</p>
    </header>

    <div class="container">
        <!-- Bagian Profil (About Me) -->
        <section class="profile-section" id="profile">
            <div class="profile-content">
                <div class="profile-text">
                    <h2>Tentang Inisiatif Ini</h2>
                    <p>Halo, saya <strong>dr. Sapto Sutardi</strong>. Sebagai seorang dokter yang bertugas di salah satu
                        Puskesmas di Kab. Lombok Barat, saya melihat langsung bagaimana teknologi dapat menjembatani
                        kesenjangan dalam pelayanan kesehatan maupun meningkatkan produktivitas sehari-hari.</p>
                    <p>Perjalanan saya sebagai programmer lepas sejak tahun 2009—melintasi era JavaME, Kotlin, hingga
                        kini berlabuh di Flutter—serta aktif di komunitas teknologi <a
                            href="https://lombokdev.github.io/" target="_blank">Lombok Dev</a>,
                        menjadi latar belakang terbentuknya <strong>DR SAPTO LABS</strong> sebagai ruang menyalurkan
                        ide, riset, dan inovasi digital saya.</p>
                </div>
                <div class="profile-badges">
                    <div class="badge-item">
                        <i class="fa-solid fa-award"></i>
                        <span>Juara 1 Tenaga Kesehatan Teladan Nasional, 2019</span>
                    </div>
                    <div class="badge-item">
                        <i class="fa-solid fa-star"></i>
                        <span>Juara 1 Top 10 Inovator Terbaik SiNovik NTB, 2019</span>
                    </div>
                    <div class="badge-item">
                        <i class="fa-solid fa-lightbulb"></i>
                        <span>Top 99 Inovator KemenpanRB, 2020</span>
                    </div>
                    <div class="badge-item">
                        <i class="fa-solid fa-file-medical"></i>
                        <span>Surveior Akreditasi Puskesmas & Klinik, 2023 - Sekarang</span>
                    </div>
                    <div class="badge-item">
                        <i class="fa-solid fa-code"></i>
                        <span>Programmer Android & Flutter</span>
                    </div>
                </div>
            </div>
        </section>

{featured_html}

        <h2 class="section-title">Aplikasi Lainnya</h2>

        <div class="apps-grid">
{grid_html}        </div>
    </div>

    <footer>
        <p>&copy; 2026 DR SAPTO LABS. Dibuat dengan <i class="fa-solid fa-heart footer-heart"></i> di Lombok, Indonesia.</p>
        <p>Hubungi: <a href="mailto:drsapto.labs@gmail.com">drsapto.labs@gmail.com</a></p>
    </footer>

    <!-- JavaScript untuk Screenshot Carousel -->
    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            const track = document.getElementById('carouselTrack');
            const prevBtn = document.getElementById('prevBtn');
            const nextBtn = document.getElementById('nextBtn');
            const dots = document.querySelectorAll('.carousel-dot');
            const slides = document.querySelectorAll('.carousel-slide');
            
            if (!track || !prevBtn || !nextBtn || slides.length <= 1) return;
            
            let currentIndex = 0;
            const slideCount = slides.length;

            const updateCarousel = (index) => {{
                if (index < 0) index = slideCount - 1;
                if (index >= slideCount) index = 0;
                
                currentIndex = index;
                track.style.transform = `translateX(-${{currentIndex * 100}}%)`;
                
                dots.forEach((dot, idx) => {{
                    if (idx === currentIndex) {{
                        dot.classList.add('active');
                    }} else {{
                        dot.classList.remove('active');
                    }}
                }});
            }};

            prevBtn.addEventListener('click', () => {{
                updateCarousel(currentIndex - 1);
            }});

            nextBtn.addEventListener('click', () => {{
                updateCarousel(currentIndex + 1);
            }});

            dots.forEach((dot, idx) => {{
                dot.addEventListener('click', () => {{
                    updateCarousel(idx);
                }});
            }});

            let autoPlayInterval = setInterval(() => {{
                updateCarousel(currentIndex + 1);
            }}, 5000);

            const container = document.querySelector('.carousel-container');
            if (container) {{
                container.addEventListener('mouseenter', () => {{
                    clearInterval(autoPlayInterval);
                }});
                container.addEventListener('mouseleave', () => {{
                    autoPlayInterval = setInterval(() => {{
                        updateCarousel(currentIndex + 1);
                    }}, 5000);
                }});
            }}
        }});
    </script>
    {generate_theme_switcher_js()}
</body>

</html>
"""

    # Write Home HTML
    try:
        with open(OUTPUT_HTML_PATH, 'w') as f:
            f.write(home_html)
        print(f"[+] Successfully compiled and wrote main portal page to '{OUTPUT_HTML_PATH}'")
    except Exception as e:
        print(f"[-] Error writing HTML file: {e}", file=sys.stderr)
        sys.exit(1)

    # 6. Generate Subfolders for each app (excluding migration or apps with null status)
    print("[*] Generating subfolders for specific apps...")
    for app in validated_apps:
        app_id = app["id"]
        app_slug = get_app_slug(app_id)
        app_dir = os.path.join(SCRIPT_DIR, app_slug)
        os.makedirs(app_dir, exist_ok=True)
        
        # Accent Theme variables injection
        theme = get_theme(app.get("category", "General"))
        theme_style = f"""    <style>
        :root {{
            --primary: {theme['primary']};
            --primary-light: {theme['primary_light']};
            --primary-dark: {theme['primary_dark']};
            --teal-glow: {theme['glow']};
        }}
        
        .accent-gradient-bg {{
            background: {theme['gradient']};
        }}
    </style>"""
        
        # 6.1 Compile app specific index.html (App Marketing Page)
        features_html = ""
        for feat in app.get("features", []):
            features_html += f"""                <div class="feature-pill">
                    <i class="fa-solid {feat['icon']}"></i>
                    <span>{feat['text']}</span>
                </div>\n"""
        if not features_html:
            features_html = """                <div class="feature-pill">
                    <i class="fa-solid fa-check"></i>
                    <span>Bekerja 100% offline & aman</span>
                </div>"""

        # App Store / Google Play Buttons
        status = app["status"]
        ios_id = app.get("ios_app_id")
        ios_link = f"https://apps.apple.com/app/id{ios_id}" if ios_id else "#"
        package_name = app["package_name"]
        
        download_buttons_html = ""
        if status == "released":
            download_buttons_html = f"""
                <a href="{ios_link}" class="store-btn" target="_blank" {"style='opacity:0.5; pointer-events:none;'" if not ios_id else ""}>
                    <i class="fa-brands fa-apple"></i>
                    <div class="store-btn-text">
                        <span class="store-btn-subtitle">Download on the</span>
                        <span class="store-btn-title">App Store</span>
                    </div>
                </a>
                
                <a href="https://play.google.com/store/apps/details?id={package_name}" class="store-btn store-btn-orange" target="_blank">
                    <i class="fa-brands fa-google-play"></i>
                    <div class="store-btn-text">
                        <span class="store-btn-subtitle">GET IT ON</span>
                        <span class="store-btn-title">Google Play</span>
                    </div>
                </a>
            """
        elif status == "in_review":
            download_buttons_html = f"""
                <button class="store-btn" style="opacity:0.6; cursor:not-allowed;" onclick="alert('Proses Review di App Store sedang berjalan!')">
                    <i class="fa-solid fa-hourglass-half"></i>
                    <div class="store-btn-text">
                        <span class="store-btn-subtitle">App Store</span>
                        <span class="store-btn-title">Menunggu Review</span>
                    </div>
                </button>
                
                <button class="store-btn store-btn-orange" style="opacity:0.6; cursor:not-allowed;" onclick="alert('Proses Review di Google Play Store sedang berjalan!')">
                    <i class="fa-solid fa-hourglass-half"></i>
                    <div class="store-btn-text">
                        <span class="store-btn-subtitle">Google Play</span>
                        <span class="store-btn-title">Menunggu Review</span>
                    </div>
                </button>
            """
        else:
            download_buttons_html = """
                <button class="store-btn" style="opacity:0.5; cursor:not-allowed;" disabled>
                    <i class="fa-solid fa-toolbox"></i>
                    <div class="store-btn-text">
                        <span class="store-btn-subtitle">Ecosystem</span>
                        <span class="store-btn-title">Proses Migrasi</span>
                    </div>
                </button>
            """
            
        # Carousel Slides
        slides = app_screenshots.get(app_id, [])
        slides_html = ""
        dots_html = ""
        for idx, slide_path in enumerate(slides):
            # Resolve relative path for subpages (which are inside a folder, so they need to prepend ../)
            slides_html += f'<li class="carousel-slide"><img src="../{slide_path}" alt="{app["web_name"]} Slide {idx+1}"></li>\n'
            dots_html += f'<button class="carousel-dot {"active" if idx == 0 else ""}"></button>\n'
            
        # Fallback if no slides
        carousel_visible_style = ""
        if not slides:
            # We hide the carousel column and let the details card span full-width on individual pages if no screenshots exist
            carousel_visible_style = "display: none;"
            
        # Back URL
        back_url = "../index.html"
        logo_path = f"../{app['web_logo']}"
        
        # Build individual index page content
        app_index_html = f"""<!DOCTYPE html>
<html lang="id">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{app['web_name']} - Dr. Sapto Labs</title>
    <!-- SEO Meta Tags -->
    <meta name="description" content="{app['web_description']}">
    <meta name="keywords" content="{', '.join(app.get('tags', []))}, dr sapto labs">
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="../styles.css">
    <!-- FontAwesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    {theme_style}
</head>

<body>
    {generate_header_js_snippet()}
    {generate_theme_switcher_button()}

    <header>
        <a href="{back_url}" style="position: absolute; left: 20px; top: 20px; color: var(--text-primary); text-decoration: none; font-weight: 600; display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-arrow-left"></i> <span>Kembali ke Labs</span>
        </a>
        <h1>{app['web_name'].upper()}</h1>
        <p>{app.get("category", "General")} Utility App</p>
    </header>

    <div class="container">
        <section class="featured-section">
            <div class="featured-grid" style="grid-template-columns: { '1.2fr 1fr' if slides else '1fr' };">
                <div class="featured-details">
                    <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 20px;">
                        <img src="{logo_path}" alt="{app['web_name']} Logo" style="width: 80px; height: 80px; border-radius: 16px; border: 1px solid var(--border-color); box-shadow: 0 8px 16px rgba(0,0,0,0.3);">
                        <div>
                            <h3 class="gradient-text" style="margin-bottom: 2px; font-size: 2rem;">{app['web_name']}</h3>
                            <p style="color: var(--primary-light); font-size: 0.95rem; font-weight: 600;">Paket ID: {package_name}</p>
                        </div>
                    </div>
                    
                    <p class="featured-desc">{app['web_description']}</p>
                    
                    <h4 style="margin-bottom: 15px; font-size: 1.1rem; color: var(--text-primary);">Fitur Utama:</h4>
                    <div class="features-list">
{features_html}                    </div>

                    <div class="download-buttons">
                        {download_buttons_html}
                    </div>
                    
                    <div style="margin-top: 30px; display: flex; gap: 15px; flex-wrap: wrap;">
                        <a href="support.html" class="privacy-btn">
                            <i class="fa-solid fa-headset" style="margin-right: 8px;"></i>Dukungan Pelanggan (Support)
                        </a>
                        <a href="privacy.html" class="privacy-btn">
                            <i class="fa-solid fa-user-shield" style="margin-right: 8px;"></i>Kebijakan Privasi
                        </a>
                    </div>
                </div>

                <!-- Screenshots Carousel -->
                <div class="featured-media" style="{carousel_visible_style}">
                    <div class="carousel-container">
                        <button class="carousel-control-btn carousel-prev-btn" id="prevBtn" aria-label="Slide sebelumnya">
                            <i class="fa-solid fa-chevron-left"></i>
                        </button>
                        <div class="carousel-track-container">
                            <ul class="carousel-track" id="carouselTrack">
                                {slides_html}                            </ul>
                        </div>
                        <button class="carousel-control-btn carousel-next-btn" id="nextBtn" aria-label="Slide berikutnya">
                            <i class="fa-solid fa-chevron-right"></i>
                        </button>
                        <div class="carousel-indicators" id="carouselIndicators">
                            {dots_html}                        </div>
                    </div>
                </div>
            </div>
        </section>
    </div>

    <footer>
        <p>&copy; 2026 DR SAPTO LABS. Dibuat dengan <i class="fa-solid fa-heart footer-heart"></i> di Lombok, Indonesia.</p>
        <p>Hubungi: <a href="mailto:drsapto.labs@gmail.com">drsapto.labs@gmail.com</a></p>
    </footer>

    <!-- JavaScript untuk Screenshot Carousel -->
    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            const track = document.getElementById('carouselTrack');
            const prevBtn = document.getElementById('prevBtn');
            const nextBtn = document.getElementById('nextBtn');
            const dots = document.querySelectorAll('.carousel-dot');
            const slides = document.querySelectorAll('.carousel-slide');
            
            if (!track || !prevBtn || !nextBtn || slides.length <= 1) return;
            
            let currentIndex = 0;
            const slideCount = slides.length;

            const updateCarousel = (index) => {{
                if (index < 0) index = slideCount - 1;
                if (index >= slideCount) index = 0;
                
                currentIndex = index;
                track.style.transform = `translateX(-${{currentIndex * 100}}%)`;
                
                dots.forEach((dot, idx) => {{
                    if (idx === currentIndex) {{
                        dot.classList.add('active');
                    }} else {{
                        dot.classList.remove('active');
                    }}
                }});
            }};

            prevBtn.addEventListener('click', () => {{
                updateCarousel(currentIndex - 1);
            }});

            nextBtn.addEventListener('click', () => {{
                updateCarousel(currentIndex + 1);
            }});

            dots.forEach((dot, idx) => {{
                dot.addEventListener('click', () => {{
                    updateCarousel(idx);
                }});
            }});

            let autoPlayInterval = setInterval(() => {{
                updateCarousel(currentIndex + 1);
            }}, 5000);

            const container = document.querySelector('.carousel-container');
            if (container) {{
                container.addEventListener('mouseenter', () => {{
                    clearInterval(autoPlayInterval);
                }});
                container.addEventListener('mouseleave', () => {{
                    autoPlayInterval = setInterval(() => {{
                        updateCarousel(currentIndex + 1);
                    }}, 5000);
                }});
            }}
        }});
    </script>
    {generate_theme_switcher_js()}
</body>

</html>
"""
        with open(os.path.join(app_dir, "index.html"), 'w') as f:
            f.write(app_index_html)
            
        # 6.2 Compile support.html (Dukungan / Support Desk Page)
        app_support_html = f"""<!DOCTYPE html>
<html lang="id">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dukungan Pelanggan - {app['web_name']}</title>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="../styles.css">
    <!-- FontAwesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    {theme_style}
    <style>
        .form-group {{
            margin-bottom: 20px;
            width: 100%;
            text-align: left;
        }}
        .form-group label {{
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: var(--text-primary);
        }}
        .form-control {{
            width: 100%;
            padding: 12px 16px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-primary);
            font-family: inherit;
            font-size: 1rem;
            transition: all 0.3s ease;
        }}
        .form-control:focus {{
            outline: none;
            border-color: var(--primary-light);
            box-shadow: 0 0 10px var(--teal-glow);
            background: rgba(255, 255, 255, 0.08);
        }}
        body.light-mode .form-control {{
            background: rgba(15, 23, 42, 0.02);
            color: var(--text-primary);
        }}
        body.light-mode .form-control:focus {{
            background: rgba(255, 255, 255, 1);
        }}
    </style>
</head>

<body>
    {generate_header_js_snippet()}
    {generate_theme_switcher_button()}

    <header>
        <a href="index.html" style="position: absolute; left: 20px; top: 20px; color: var(--text-primary); text-decoration: none; font-weight: 600; display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-arrow-left"></i> <span>Kembali</span>
        </a>
        <h1>DUKUNGAN PELANGGAN</h1>
        <p>{app['web_name']}</p>
    </header>

    <div class="container" style="max-width: 700px;">
        <section class="profile-section" style="padding: 40px; text-align: center;">
            <i class="fa-solid fa-headset" style="font-size: 3rem; color: var(--primary-light); margin-bottom: 20px;"></i>
            <h2 style="margin-bottom: 10px;">Hubungi Kami</h2>
            <p style="color: var(--text-secondary); margin-bottom: 30px;">
                Mengalami kendala atau memiliki saran? Isi formulir di bawah ini untuk mengirimkan email dukungan ke tim pengembang <strong>dr. Sapto Labs</strong>.
            </p>
            
            <form id="supportForm" onsubmit="handleSupportSubmit(event)">
                <div class="form-group">
                    <label for="name">Nama Lengkap</label>
                    <input type="text" id="name" class="form-control" placeholder="Masukkan nama Anda" required>
                </div>
                
                <div class="form-group">
                    <label for="email">Alamat Email</label>
                    <input type="email" id="email" class="form-control" placeholder="Masukkan email Anda" required>
                </div>

                <div class="form-group">
                    <label for="subject">Subjek Masalah</label>
                    <input type="text" id="subject" class="form-control" value="Dukungan: {app['web_name']}" required>
                </div>
                
                <div class="form-group">
                    <label for="message">Pesan / Detail Kendala</label>
                    <textarea id="message" class="form-control" rows="6" placeholder="Jelaskan masalah atau masukan Anda di sini..." required></textarea>
                </div>
                
                <button type="submit" class="app-card-btn" style="width: 100%; padding: 14px; font-size: 1rem;">
                    <i class="fa-solid fa-paper-plane"></i> Kirim Pertanyaan Dukungan
                </button>
            </form>
        </section>
        
        <section class="profile-section" style="padding: 30px; margin-top: 30px;">
            <h3 style="margin-bottom: 15px;"><i class="fa-solid fa-circle-question" style="color: var(--primary-light); margin-right: 10px;"></i>Pertanyaan Umum (FAQ)</h3>
            <div style="display: flex; flex-direction: column; gap: 20px; text-align: left;">
                <div>
                    <h5 style="margin-bottom: 5px; font-weight: 600; color: var(--text-primary);">Apakah aplikasi ini memerlukan koneksi internet?</h5>
                    <p style="color: var(--text-secondary); font-size: 0.95rem; margin-bottom: 0;">Tidak. Aplikasi ini dirancang agar bekerja 100% offline secara lokal di perangkat Anda demi kenyamanan dan perlindungan data yang maksimal.</p>
                </div>
                <hr style="border: 0; border-top: 1px solid var(--border-color);">
                <div>
                    <h5 style="margin-bottom: 5px; font-weight: 600; color: var(--text-primary);">Bagaimana cara memperbarui aplikasi?</h5>
                    <p style="color: var(--text-secondary); font-size: 0.95rem; margin-bottom: 0;">Anda dapat memeriksa dan mengunduh pembaruan terbaru secara resmi langsung melalui toko aplikasi Google Play Store atau Apple App Store.</p>
                </div>
            </div>
        </section>
    </div>

    <footer>
        <p>&copy; 2026 DR SAPTO LABS. Dibuat dengan <i class="fa-solid fa-heart footer-heart"></i> di Lombok, Indonesia.</p>
        <p>Hubungi: <a href="mailto:drsapto.labs@gmail.com">drsapto.labs@gmail.com</a></p>
    </footer>

    <script>
        function handleSupportSubmit(e) {{
            e.preventDefault();
            const name = document.getElementById('name').value;
            const email = document.getElementById('email').value;
            const subject = document.getElementById('subject').value;
            const message = document.getElementById('message').value;
            
            const emailBody = `Nama: ${{name}}\\nEmail Pengirim: ${{email}}\\n\\nDetail Pesan:\\n${{message}}`;
            const mailtoUrl = `mailto:drsapto.labs@gmail.com?subject=${{encodeURIComponent(subject)}}&body=${{encodeURIComponent(emailBody)}}`;
            
            // Open user's email client
            window.location.href = mailtoUrl;
        }}
    </script>
    {generate_theme_switcher_js()}
</body>

</html>
"""
        with open(os.path.join(app_dir, "support.html"), 'w') as f:
            f.write(app_support_html)
            
        # 6.3 Compile privacy.html (Kebijakan Privasi Page)
        privacy_data = get_privacy_content(app)
        app_privacy_html = f"""<!DOCTYPE html>
<html lang="id">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kebijakan Privasi - {app['web_name']}</title>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="../styles.css">
    <!-- FontAwesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    {theme_style}
    <style>
        .privacy-content-card h2 {{
            color: var(--text-primary);
            font-size: 1.4rem;
            margin-top: 30px;
            margin-bottom: 12px;
            font-weight: 600;
        }}
        .privacy-content-card p, .privacy-content-card li {{
            color: var(--text-secondary);
            font-size: 1.05rem;
            line-height: 1.7;
        }}
        .privacy-content-card ul {{
            margin-left: 20px;
            margin-bottom: 20px;
        }}
        .privacy-content-card li {{
            margin-bottom: 8px;
        }}
        .highlight {{
            color: var(--primary-light);
            font-weight: 600;
        }}
    </style>
</head>

<body>
    {generate_header_js_snippet()}
    {generate_theme_switcher_button()}

    <header>
        <a href="index.html" style="position: absolute; left: 20px; top: 20px; color: var(--text-primary); text-decoration: none; font-weight: 600; display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-arrow-left"></i> <span>Kembali</span>
        </a>
        <h1>KEBIJAKAN PRIVASI</h1>
        <p>{app['web_name']}</p>
    </header>

    <div class="container" style="max-width: 800px;">
        <section class="profile-section privacy-content-card" style="text-align: left; padding: 40px;">
            <h2 style="margin-top: 0; border-bottom: 2px solid var(--border-color); padding-bottom: 15px; font-size: 1.8rem;">Kebijakan Privasi</h2>
            <p style="font-size: 0.9rem; opacity: 0.7; margin-bottom: 25px;">Terakhir diperbarui: 30 Juli 2026</p>
            
            <p>{privacy_data['intro']}</p>
            
            <h2>1. Pengumpulan dan Penggunaan Data</h2>
            <p>{privacy_data['data_use']}</p>
            
            <h2>2. Izin Perangkat (Permissions)</h2>
            <p>{privacy_data['permissions']}</p>
            
            <h2>3. Layanan Pihak Ketiga</h2>
            <p>
                Aplikasi ini sepenuhnya bersih dan mandiri. Kami tidak menanamkan SDK analitik, pelacakan iklan, atau integrasi pihak ketiga eksternal yang dapat merekam aktivitas penggunaan Anda.
            </p>
            
            <h2>4. Retensi Data</h2>
            <p>
                Karena kami tidak memiliki server penampung dan tidak pernah mengumpulkan data Anda, kami tidak memiliki data penggunaan Anda untuk dihapus atau disimpan di cloud. Semua status atau riwayat sesi akan segera terhapus saat RAM perangkat dibersihkan oleh sistem operasi, kecuali data setelan tersimpan lokal yang dapat Anda bersihkan secara manual melalui pengaturan aplikasi.
            </p>
            
            <h2>5. Keamanan</h2>
            <p>
                Dengan memproses data secara lokal dan offline, risiko kebocoran data akibat serangan peretasan database eksternal dapat diminimalisir secara total. Keamanan data pada perangkat bergantung sepenuhnya pada sistem keamanan fisik dan enkripsi bawaan perangkat yang Anda gunakan.
            </p>
            
            <h2>6. Perubahan Kebijakan Privasi</h2>
            <p>
                Kami dapat memperbarui Kebijakan Privasi ini sewaktu-waktu. Setiap pembaruan kebijakan baru akan dipublikasikan langsung di halaman situs web ini.
            </p>
            
            <h2>7. Hubungi Kami</h2>
            <p>
                Jika Anda memiliki pertanyaan mengenai Kebijakan Privasi ini, silakan hubungi kami melalui email di: <strong>drsapto.labs@gmail.com</strong>.
            </p>
        </section>
    </div>

    <footer>
        <p>&copy; 2026 DR SAPTO LABS. Dibuat dengan <i class="fa-solid fa-heart footer-heart"></i> di Lombok, Indonesia.</p>
        <p>Hubungi: <a href="mailto:drsapto.labs@gmail.com">drsapto.labs@gmail.com</a></p>
    </footer>
    {generate_theme_switcher_js()}
</body>

</html>
"""
        with open(os.path.join(app_dir, "privacy.html"), 'w') as f:
            f.write(app_privacy_html)
            
        print(f"[+] Subpage compiled successfully for app: '{app_id}' -> /{app_slug}/")

    # 7. Auditing & QA Verifications (Anti False-Positive)
    print("\n[*] Starting post-compilation QA Audits...")
    audit_errors = 0
    
    # 7.1 Verify Main Index file
    if not os.path.exists(OUTPUT_HTML_PATH):
        print("[-] Audit Error: Main index.html was not created!")
        audit_errors += 1
    else:
        with open(OUTPUT_HTML_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
            if "DR SAPTO LABS" not in content or "themeToggle" not in content:
                print("[-] Audit Error: Main index.html structure is invalid or missing key features!")
                audit_errors += 1
                
    # 7.2 Verify each subpage
    for app in validated_apps:
        app_id = app["id"]
        app_slug = get_app_slug(app_id)
        app_dir = os.path.join(SCRIPT_DIR, app_slug)
        
        required_files = ["index.html", "support.html", "privacy.html"]
        for req_file in required_files:
            file_path = os.path.join(app_dir, req_file)
            if not os.path.exists(file_path):
                print(f"[-] Audit Error: Required file '{req_file}' is missing in subfolder /{app_slug}/")
                audit_errors += 1
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
                # Check for empty title
                if "<title></title>" in html_content or "<title> - " in html_content:
                    print(f"[-] Audit Error: Title tag is empty or malformed in /{app_slug}/{req_file}")
                    audit_errors += 1
                    
                # Check for unreplaced formatting templates
                placeholders = ["{package_name}", "{web_name}", "{web_logo}", "{web_description}"]
                for placeholder in placeholders:
                    if placeholder in html_content:
                        print(f"[-] Audit Error: Unreplaced placeholder '{placeholder}' found in /{app_slug}/{req_file}")
                        audit_errors += 1
                        
                # Verify that images references exist
                if req_file == "index.html":
                    logo_relative = app['web_logo']
                    logo_abs = os.path.join(SCRIPT_DIR, logo_relative)
                    if not os.path.exists(logo_abs):
                        print(f"[-] Audit Error: Referenced logo image '{logo_relative}' does not exist on disk!")
                        audit_errors += 1
                        
    if audit_errors > 0:
        print(f"\n[-] QA Auditing Failed with {audit_errors} error(s). Aborting build!", file=sys.stderr)
        sys.exit(1)
        
    print("[+] All QA Audits passed successfully! No empty placeholders or broken paths found.")
    print("\n[+] Web compilation completed successfully! All pages are up to date.")

if __name__ == "__main__":
    main()
