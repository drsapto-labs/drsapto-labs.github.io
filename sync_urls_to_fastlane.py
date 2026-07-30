#!/usr/bin/env python3
import json
import os
import sys

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(SCRIPT_DIR, "../Apps/owoa_registry.json")

def get_app_slug(app_id):
    """Convert app_id (snake_case) to URL friendly slug (hyphenated)"""
    return app_id.replace("_", "-")

def main():
    print("=== OWOA Fastlane URL Syncer ===")
    
    # Load Registry
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
    updated_count = 0
    
    for app in apps:
        app_id = app.get("id")
        status = app.get("status")
        
        # Skip apps without status or ID
        if not app_id or not status:
            continue
            
        app_slug = get_app_slug(app_id)
        
        # Construct target URLs
        support_url = f"https://drsapto-labs.github.io/{app_slug}/support"
        marketing_url = f"https://drsapto-labs.github.io/{app_slug}/"
        privacy_url = f"https://drsapto-labs.github.io/{app_slug}/privacy.html"
        
        # Search for fastlane metadata directory
        # Can be Apps/{app_id}/ios/fastlane/metadata/ or Apps/{app_id}/fastlane/metadata/
        paths_to_check = [
            os.path.join(SCRIPT_DIR, f"../Apps/{app_id}/ios/fastlane/metadata"),
            os.path.join(SCRIPT_DIR, f"../Apps/{app_id}/fastlane/metadata")
        ]
        
        metadata_dir = None
        for path in paths_to_check:
            if os.path.exists(path):
                metadata_dir = path
                break
                
        if not metadata_dir:
            # Skip if fastlane folder doesn't exist yet for this app
            continue
            
        print(f"\n[*] Syncing URLs for '{app_id}' -> {metadata_dir}")
        
        # Iterate over all locale directories (e.g., id, en-US)
        locales = [d for d in os.listdir(metadata_dir) if os.path.isdir(os.path.join(metadata_dir, d))]
        
        for locale in locales:
            locale_path = os.path.join(metadata_dir, locale)
            
            # Write support_url.txt
            support_file = os.path.join(locale_path, "support_url.txt")
            with open(support_file, 'w', encoding='utf-8') as f:
                f.write(support_url + "\n")
            print(f"   [+] support_url.txt -> {support_url}")
                
            # Write marketing_url.txt
            marketing_file = os.path.join(locale_path, "marketing_url.txt")
            with open(marketing_file, 'w', encoding='utf-8') as f:
                f.write(marketing_url + "\n")
            print(f"   [+] marketing_url.txt -> {marketing_url}")
                
            # Write privacy_url.txt (if required by custom deliver setup)
            privacy_file = os.path.join(locale_path, "privacy_url.txt")
            with open(privacy_file, 'w', encoding='utf-8') as f:
                f.write(privacy_url + "\n")
            print(f"   [+] privacy_url.txt -> {privacy_url}")
            
            updated_count += 1
            
    print(f"\n[+] URL Syncer completed successfully! Updated URLs across {updated_count} locales.")

if __name__ == "__main__":
    main()
