import urllib.request
import urllib.error
import ssl
import time
import string
import itertools
from datetime import datetime
import concurrent.futures

ssl_ctx = ssl._create_unverified_context()

PLATFORMS = {
    "Telegram": "https://t.me/{}",
    "Instagram": "https://www.instagram.com/{}/",
    "GitHub": "https://github.com/{}",
    "TikTok": "https://www.tiktok.com/@{}",
    "Twitch": "https://www.twitch.tv/{}",
    "X": "https://x.com/{}",
    "Reddit": "https://www.reddit.com/user/{}",
    "YouTube": "https://www.youtube.com/@{}",
}

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def check_one(username):
    available_on = []
    for name, url_template in PLATFORMS.items():
        url = url_template.format(username)
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=5, context=ssl_ctx)
            if resp.getcode() != 200:
                available_on.append(name)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                available_on.append(name)
        except:
            pass
    return username, available_on

def main():
    print("=" * 60)
    print("فاحص الاسماء الثلاثية")
    print("=" * 60)
    
    choice = input("1- ثلاثي كامل\n2- ثلاثي بحرف معين\nاختر: ").strip()
    
    letters = string.ascii_lowercase
    
    if choice == "2":
        prefix = input("ادخل الحرف (a-z): ").strip().lower()
        if len(prefix) != 1:
            print("خطا: ادخل حرف واحد فقط")
            return
        combos = [prefix + "".join(p) for p in itertools.product(letters, repeat=2)]
    else:
        combos = ["".join(p) for p in itertools.product(letters, repeat=3)]
    
    total = len(combos)
    print(f"\nبدء الفحص... {total} اسم")
    print("=" * 60)
    
    available = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for i, (username, platforms) in enumerate(executor.map(check_one, combos), 1):
            if platforms:
                available.append((username, platforms))
                print(f"متاح: {username} -> {', '.join(platforms)}")
            if i % 500 == 0:
                print(f"-- تم {i}/{total} ({i*100//total}%) --")
    
    if available:
        filename = f"available_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w", encoding="utf-8-sig") as f:
            f.write(f"Available usernames - {datetime.now()}\n")
            f.write(f"Total: {len(available)}\n\n")
            for u, platforms in available:
                f.write(f"{u} -> {', '.join(platforms)}\n")
        print(f"\nDone! Saved to {filename} ({len(available)} names)")
    else:
        print("\nلم يتم العثور على اسماء متاحة")

if __name__ == "__main__":
    main()
