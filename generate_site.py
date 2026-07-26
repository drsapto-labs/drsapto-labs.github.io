#!/usr/bin/env python3
import json
import os
import sys

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(SCRIPT_DIR, "../Apps/owoa_registry.json")
OUTPUT_HTML_PATH = os.path.join(SCRIPT_DIR, "index.html")

def get_privacy_url(app_id):
    """Normalize privacy page names to match current filenames."""
    if app_id == "obstetric_calculator":
        return "obstetric-calculator-privacy.html"
    elif app_id == "time_later":
        return "timelater-privacy.html"
    elif app_id == "udasiap":
        return "udasiap-privacy.html"
    else:
        return f"{app_id.replace('_', '-')}-privacy.html"

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
        
        # Skip apps without a website status (they are not meant for the public landing page)
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
            
        # Verify app logo file exists
        logo_path = os.path.join(SCRIPT_DIR, web_logo)
        if not os.path.exists(logo_path):
            print(f"[-] Error in app '{app_id}': App logo file '{logo_path}' does not exist!")
            errors += 1
            continue
            
        # Verify package format
        if not package_name.startswith("com.drsaptolabs."):
            print(f"[-] Warning in app '{app_id}': Package name '{package_name}' does not follow 'com.drsaptolabs.*' standard")
            
        # Verify iOS ID if featured/released on iOS
        if app_id == "obstetric_calculator":
            ios_app_id = app.get("ios_app_id")
            if not ios_app_id or not ios_app_id.isdigit():
                print(f"[-] Error in app '{app_id}': Missing or invalid 'ios_app_id' ({ios_app_id})")
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
    
    # 4. Generate HTML Content
    featured_html = ""
    if featured_app:
        features_html = ""
        for feat in featured_app.get("features", []):
            features_html += f"""                        <div class="feature-pill">
                            <i class="fa-solid {feat['icon']}"></i>
                            <span>{feat['text']}</span>
                        </div>\n"""
                        
        privacy_url = get_privacy_url(featured_app["id"])
        
        featured_html = f"""        <!-- Aplikasi Unggulan: {featured_app['web_name']} -->
        <section class="featured-section" id="featured-app">
            <div class="featured-grid">
                <div class="featured-details">
                    <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 20px;">
                        <img src="{featured_app['web_logo']}" alt="{featured_app['web_name']} Logo" style="width: 72px; height: 72px; border-radius: 16px; border: 1px solid var(--border-color); box-shadow: 0 8px 16px rgba(0,0,0,0.3);">
                        <div>
                            <h3 class="gradient-text" style="margin-bottom: 2px; font-size: 1.8rem;">{featured_app['web_name']}</h3>
                            <p style="color: var(--primary-light); font-size: 0.95rem; font-weight: 600;">Kalkulator Usia Kehamilan & Pertumbuhan Janin</p>
                        </div>
                    </div>
                    
                    <p class="featured-desc">{featured_app['web_description']}</p>
                    
                    <div class="features-list">
{features_html}                    </div>

                    <div class="download-buttons">
                        <!-- App Store Link -->
                        <a href="https://apps.apple.com/app/id{featured_app['ios_app_id']}" class="store-btn" target="_blank">
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

                        <!-- Kebijakan Privasi -->
                        <a href="{privacy_url}" class="privacy-btn">
                            <i class="fa-solid fa-user-shield" style="margin-right: 8px;"></i>Kebijakan Privasi
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
                                <li class="carousel-slide"><img src="images/obstetric_calculator/slide_01.png" alt="Dr. Sapto ObstetriCalc Screenshot 1"></li>
                                <li class="carousel-slide"><img src="images/obstetric_calculator/slide_02.png" alt="Dr. Sapto ObstetriCalc Screenshot 2"></li>
                                <li class="carousel-slide"><img src="images/obstetric_calculator/slide_03.png" alt="Dr. Sapto ObstetriCalc Screenshot 3"></li>
                                <li class="carousel-slide"><img src="images/obstetric_calculator/slide_04.png" alt="Dr. Sapto ObstetriCalc Screenshot 4"></li>
                                <li class="carousel-slide"><img src="images/obstetric_calculator/slide_05.png" alt="Dr. Sapto ObstetriCalc Screenshot 5"></li>
                                <li class="carousel-slide"><img src="images/obstetric_calculator/slide_06.png" alt="Dr. Sapto ObstetriCalc Screenshot 6"></li>
                            </ul>
                        </div>
                        <button class="carousel-control-btn carousel-next-btn" id="nextBtn" aria-label="Slide berikutnya">
                            <i class="fa-solid fa-chevron-right"></i>
                        </button>
                        <div class="carousel-indicators" id="carouselIndicators">
                            <button class="carousel-dot active"></button>
                            <button class="carousel-dot"></button>
                            <button class="carousel-dot"></button>
                            <button class="carousel-dot"></button>
                            <button class="carousel-dot"></button>
                            <button class="carousel-dot"></button>
                        </div>
                    </div>
                </div>
            </div>
        </section>"""

    # Generate Grid for Other Apps
    grid_html = ""
    for app in other_apps:
        status = app["status"]
        privacy_url = get_privacy_url(app["id"])
        
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
            actions_html = f"""                    <a href="https://play.google.com/store/apps/details?id={app['package_name']}" class="app-card-btn" target="_blank">
                        <i class="fa-brands fa-google-play"></i> Google Play
                    </a>
                    <a href="{privacy_url}" class="app-card-btn app-card-btn-secondary">
                        Kebijakan Privasi
                    </a>"""
        elif status == "in_review":
            actions_html = f"""                    <button class="app-card-btn app-card-btn-disabled" onclick="alert('Google Play Store Link: Sedang dalam proses review oleh Google!')">
                        <i class="fa-solid fa-hourglass-half"></i> Menunggu Review
                    </button>
                    <a href="{privacy_url}" class="app-card-btn app-card-btn-secondary">
                        Kebijakan Privasi
                    </a>"""
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

    # 5. Full HTML Template
    full_html = f"""<!DOCTYPE html>
<html lang="id">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dr. Sapto Labs - Solusi Aplikasi Kesehatan & Produktivitas</title>
    <!-- SEO Meta Tags -->
    <meta name="description" content="Inisiatif teknologi dr. Sapto Sutardi menghadirkan asisten klinis presisi & kalkulator obstetri offline serta aplikasi penunjang produktivitas.">
    <meta name="keywords" content="obstetri, kalkulator, usia kehamilan, hpl, hpht, hadlock, intergrowth, dr sapto, medis, puskesmas, lombok">
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="styles.css">
    <!-- FontAwesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>

<body>

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
                            href="https://lombokdev.github.io/" target="_blank"
                            style="color: var(--primary-light); text-decoration: none; font-weight: 600;">Lombok Dev</a>,
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
            
            let currentIndex = 0;
            const slideCount = slides.length;

            const updateCarousel = (index) => {{
                // Batasi index
                if (index < 0) index = slideCount - 1;
                if (index >= slideCount) index = 0;
                
                currentIndex = index;
                
                // Geser track
                track.style.transform = `translateX(-${{currentIndex * 100}}%)`;
                
                // Update indikator dot
                dots.forEach((dot, idx) => {{
                    if (idx === currentIndex) {{
                        dot.classList.add('active');
                    }} else {{
                        dot.classList.remove('active');
                    }}
                }});
            }};

            // Event Listeners
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

            // Auto-play (opsional, setiap 5 detik)
            let autoPlayInterval = setInterval(() => {{
                updateCarousel(currentIndex + 1);
            }}, 5000);

            // Berhentikan auto-play jika di-hover atau di-klik manual
            const container = document.querySelector('.carousel-container');
            container.addEventListener('mouseenter', () => {{
                clearInterval(autoPlayInterval);
            }});
            container.addEventListener('mouseleave', () => {{
                autoPlayInterval = setInterval(() => {{
                    updateCarousel(currentIndex + 1);
                }}, 5000);
            }});
        }});
    </script>
</body>

</html>
"""

    # 6. Write File
    try:
        with open(OUTPUT_HTML_PATH, 'w') as f:
            f.write(full_html)
        print(f"[+] Successfully compiled and wrote static site to '{OUTPUT_HTML_PATH}'!")
    except Exception as e:
        print(f"[-] Error writing HTML file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
