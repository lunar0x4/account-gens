import requests
import random
import string
import time
import json
import threading
import hashlib
from queue import Queue
from colorama import init, Fore
import concurrent.futures

init(autoreset=True)


class Alpha3dGenerator: # i modified a non-working one so thats why its labelled "alpha3d" instead of "piclumen"
    def __init__(self):
        self.successful = 0
        self.unsuccessful = 0
        self.total_to_generate = 0
        self.proxies = []
        self.working_proxies = []
        self.proxy_queues = []
        self.failed_proxies = []
        self.lock = threading.Lock()
        self.running = True
        self.load_proxies()

    def load_proxies(self):
        try:
            with open("proxy.txt", "r") as f:
                self.proxies = [line.strip() for line in f if line.strip()]

            if not self.proxies:
                print(f"{Fore.RED}proxy.txt is empty!")
                exit(1)

            print(f"{Fore.YELLOW}loaded {len(self.proxies)} proxies, testing...")
            self.test_proxies()
        except FileNotFoundError:
            print(f"{Fore.RED}proxy.txt not found!")
            exit(1)

    def test_proxy(self, proxy):
        try:
            proxy_parts = proxy.split(":")
            session = requests.Session()
            session.proxies = {
                "http": f"socks5://{proxy_parts[0]}:{proxy_parts[1]}",
                "https": f"socks5://{proxy_parts[0]}:{proxy_parts[1]}",
            }
            session.get("https://www.google.com", timeout=3)
            return proxy
        except:
            return None

    def test_proxies(self):
        working = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = {executor.submit(self.test_proxy, proxy): proxy for proxy in self.proxies}

            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                result = future.result()
                if result:
                    working.append(result)

        self.working_proxies = working
        print()

        if not self.working_proxies:
            print(f"{Fore.RED}no working proxies found!")
            exit(1)

        print(f"{Fore.GREEN}{len(self.working_proxies)}/{len(self.proxies)} proxies working")

    def setup_proxy_queues(self, thread_count):
        for i in range(thread_count):
            queue = Queue()
            proxy_index = i % len(self.working_proxies)
            queue.put(self.working_proxies[proxy_index])
            self.proxy_queues.append(queue)

    def get_proxy_session(self, thread_id):
        queue = self.proxy_queues[thread_id % len(self.proxy_queues)]
        proxy = queue.get()
        session = requests.Session()
        proxy_parts = proxy.split(":")
        session.proxies = {
            "http": f"socks5://{proxy_parts[0]}:{proxy_parts[1]}",
            "https": f"socks5://{proxy_parts[0]}:{proxy_parts[1]}",
        }
        return session, proxy, queue

    def remove_failed_proxy(self, proxy, queue):
        with self.lock:
            if proxy not in self.failed_proxies:
                self.failed_proxies.append(proxy)
                if proxy in self.working_proxies:
                    self.working_proxies.remove(proxy)
                print(f"{Fore.RED}[-] proxy {proxy} failed, removed from working list")

        if queue and self.working_proxies:
            new_proxy = random.choice(self.working_proxies)
            queue.put(new_proxy)
            return True
        return False

    def return_proxy(self, queue, proxy):
        if proxy not in self.failed_proxies:
            queue.put(proxy)

    def random_string(self, length, chars=string.ascii_lowercase + string.digits):
        return "".join(random.choice(chars) for _ in range(length))

    def create_temp_email(self, session):
        try:
            resp = session.post(
                "https://api.internal.temp-mail.io/api/v3/email/new",
                json={"min_name_length": 10, "max_name_length": 10},
                timeout=10,
            )
            email = resp.json()["email"]
            print(f"{Fore.MAGENTA}[*] generating account with {email}")
            return email
        except:
            return None

    def send_code(self, session, email):
        try:
            resp = session.post(
                "https://api.piclumen.com/api/user/register-send-code",
                data={"account": email},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == 0:
                    return True
            return False
        except:
            return False

    def get_verification_code(self, session, email):
        for _ in range(10):
            try:
                resp = session.get(
                    f"https://api.internal.temp-mail.io/api/v3/email/{email}/messages",
                    timeout=10,
                )
                messages = resp.json()
                if messages:
                    subject = messages[0].get("subject", "")
                    import re
                    match = re.search(r'(\d{4})', subject)
                    if match:
                        return match.group(1)
            except:
                pass
            time.sleep(5)
        return None

    def register(self, session, email, code):
        password = self.random_string(8)
        hashed = hashlib.md5(password.encode()).hexdigest()
        try:
            resp = session.post(
                "https://api.piclumen.com/api/user/register",
                json={
                    "account": email,
                    "password": hashed, # required to pass MD5 check
                    "validateCode": code,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == 0:
                    with self.lock:
                        with open("piclumen_accs.txt", "a") as f:
                            f.write(f"{email}:{password}\n")
                        print(f"{Fore.BLUE}[+] account made: {email}:{password}")
                    return True
        except:
            pass
        return False

    def generate_account(self, thread_id):
        with self.lock:
            if self.successful + self.unsuccessful >= self.total_to_generate:
                return False

        session, proxy, queue = self.get_proxy_session(thread_id)

        try:
            email = self.create_temp_email(session)
            if not email:
                with self.lock:
                    self.unsuccessful += 1
                self.remove_failed_proxy(proxy, queue)
                return True

            if not self.send_code(session, email):
                with self.lock:
                    self.unsuccessful += 1
                self.remove_failed_proxy(proxy, queue)
                return True

            code = self.get_verification_code(session, email)
            if not code:
                with self.lock:
                    self.unsuccessful += 1
                self.remove_failed_proxy(proxy, queue)
                return True

            if self.register(session, email, code):
                with self.lock:
                    self.successful += 1
                self.return_proxy(queue, proxy)
                return True
            else:
                with self.lock:
                    self.unsuccessful += 1
                self.remove_failed_proxy(proxy, queue)
                return True

        except:
            with self.lock:
                self.unsuccessful += 1
            self.remove_failed_proxy(proxy, queue)
            return True

    def worker(self, thread_id):
        while self.running:
            if not self.generate_account(thread_id):
                break

    def start(self):
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"{Fore.CYAN}piclumen.com account generator")
        print(f"{Fore.CYAN}{'='*50}")

        while True:
            try:
                self.total_to_generate = int(input(f"{Fore.YELLOW}how many accounts to generate? {Fore.WHITE}"))
                break
            except:
                print(f"{Fore.RED}invalid number!")

        while True:
            try:
                threads = int(input(f"{Fore.YELLOW}how many threads to use? {Fore.WHITE}"))
                break
            except:
                print(f"{Fore.RED}invalid number!")

        self.setup_proxy_queues(threads)

        print(f"\n{Fore.GREEN}starting generation...")
        print(f"{Fore.CYAN}using {len(self.working_proxies)} proxies across {threads} threads")
        print(f"{Fore.CYAN}{'='*50}\n")

        workers = []
        for i in range(threads):
            t = threading.Thread(target=self.worker, args=(i,))
            t.daemon = True
            t.start()
            workers.append(t)

        try:
            while (self.successful + self.unsuccessful) < self.total_to_generate:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}stopping...")

        self.running = False
        for t in workers:
            t.join(timeout=1)

        print(f"\n\n{Fore.CYAN}{'='*50}")
        print(f"{Fore.GREEN}complete! {self.successful} accounts created")
        print(f"{Fore.RED}{self.unsuccessful} failed")
        print(f"{Fore.CYAN}{'='*50}")


if __name__ == "__main__":
    generator = Alpha3dGenerator()
    generator.start()
