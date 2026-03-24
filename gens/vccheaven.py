from colorama import init, Fore, Style
import requests
import random
import string
import time
import re
import threading
from queue import Queue

init(autoreset=True)

BASE_URL = "https://dashboard.vccheaven.com"
SUCCESS_FILE = "vccheaven_accounts.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8",
    "Accept-Encoding": None,
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

def load_proxies(filename="proxy.txt"):
    try:
        with open(filename, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        return proxies
    except:
        return []

def get_session_with_proxy(proxy_string):
    session = requests.Session()

    if proxy_string:
        try:
            proxy_dict = {
                'http': f'socks5://{proxy_string}',
                'https': f'socks5://{proxy_string}'
            }
            session.proxies.update(proxy_dict)
        except:
            pass

    return session

def generate_username():
    length = random.randint(10, 14)
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def generate_password():
    length = random.randint(12, 16)
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choice(chars) for _ in range(length))

def create_temp_email(proxy=None):
    session = get_session_with_proxy(proxy)
    payload = {"min_name_length": 10, "max_name_length": 10}
    response = session.post("https://api.internal.temp-mail.io/api/v3/email/new", json=payload)
    data = response.json()
    email = data["email"]
    print(f"{Fore.GREEN}[+] Temp email created: {email}")
    return email

def get_csrf_and_cookie(proxy=None):
    session = get_session_with_proxy(proxy)

    try:
        response = session.get(f"{BASE_URL}/index.php", headers=HEADERS, allow_redirects=False)

        if response.status_code == 302:
            location = response.headers.get('Location', '')
            if 'login' in location:
                response = session.get(f"{BASE_URL}{location}", headers=HEADERS, allow_redirects=False)

        csrf_match = re.search(r'name="csrf_token"\s*value="([^"]+)"', response.text)

        if not csrf_match:
            csrf_match = re.search(r'csrf_token["\']\s*value=["\']([^"\']+)["\']', response.text)

        if csrf_match:
            csrf_token = csrf_match.group(1)
        else:
            return None, None, None

        cookies = session.cookies.get_dict()
        dashboard_cookie = cookies.get("dashboard")

        if not dashboard_cookie:
            for key in cookies:
                if 'dashboard' in key.lower():
                    dashboard_cookie = cookies[key]
                    break

        return csrf_token, dashboard_cookie, session

    except Exception as e:
        return None, None, None

def register_account(email, session, csrf_token, dashboard_cookie, thread_id):
    username = generate_username()
    password = generate_password()
    fullname = "Hugh Janice" # you can change this to whatever you want, doesnt really matter

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0",
        "Accept": "*/*",
        "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/index.php",
        "Content-Type": "application/x-www-form-urlencoded",
        "Sec-Ch-Ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Microsoft Edge";v="146"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }

    cookies = {}
    if dashboard_cookie:
        cookies["dashboard"] = dashboard_cookie

    data = {
        "csrf_token": csrf_token,
        "fullname": fullname,
        "username": username,
        "email": email,
        "password": password,
        "passwordConfirmation": password,
        "signup": ""
    }

    try:
        response = session.post(f"{BASE_URL}/forms/signup.php", data=data, headers=headers, cookies=cookies, allow_redirects=False)

        if response.status_code == 200:
            print(f"{Fore.LIGHTBLUE_EX}[Thread {thread_id}] [+] Registration successful! {email}:{password}")

            with open(SUCCESS_FILE, 'a') as f:
                f.write(f"{email}:{password}\n")
            return True

        return False

    except Exception as e:
        print(f"{Fore.RED}[Thread {thread_id}] [-] Error: {e}")
        return False

def create_account_with_proxy(proxy, thread_id):
    try:
        csrf_token, dashboard_cookie, session = get_csrf_and_cookie(proxy)

        if not csrf_token:
            print(f"{Fore.RED}[Thread {thread_id}] [-] Failed to get CSRF token")
            return False

        email = create_temp_email(proxy)

        if register_account(email, session, csrf_token, dashboard_cookie, thread_id):
            return True

        return False

    except Exception as e:
        print(f"{Fore.RED}[Thread {thread_id}] [-] Error: {e}")
        return False

def worker(thread_id, queue, results, use_proxies, proxies):
    while True:
        try:
            task = queue.get_nowait()
        except:
            break

        if use_proxies and proxies:
            proxy = random.choice(proxies)
            print(f"{Fore.MAGENTA}[Thread {thread_id}] [*] Using proxy: {proxy}")
            success = create_account_with_proxy(proxy, thread_id)
        else:
            success = create_account_with_proxy(None, thread_id)

        if success:
            results.append(1)

        queue.task_done()
        time.sleep(random.uniform(2, 4))

def main():
    accounts = int(input(f"{Fore.CYAN}[?] How many accounts to create: "))
    threads = int(input(f"{Fore.CYAN}[?] How many threads to use: "))

    use_proxies = input(f"{Fore.CYAN}[?] Use proxies? (y/n): ").lower().strip()

    proxies = []
    if use_proxies == 'y':
        proxies = load_proxies()
        if proxies:
            print(f"{Fore.GREEN}[+] Loaded {len(proxies)} proxies")
        else:
            print(f"{Fore.RED}[-] No proxies found in proxy.txt")
            print(f"{Fore.YELLOW}[!] Continuing without proxies...")
            use_proxies = 'n'

    queue = Queue()
    for i in range(accounts):
        queue.put(i)

    results = []
    thread_list = []

    print(f"{Fore.CYAN}[*] Starting {threads} threads to create {accounts} accounts...")

    for i in range(threads):
        t = threading.Thread(target=worker, args=(i+1, queue, results, use_proxies, proxies))
        t.start()
        thread_list.append(t)
        time.sleep(0.1)

    for t in thread_list:
        t.join()

    print(f"\n{Fore.GREEN}[+] Done! Created {len(results)}/{accounts} accounts")
    print(f"{Fore.GREEN}[+] Accounts saved to {SUCCESS_FILE}")

if __name__ == "__main__":
    main()
