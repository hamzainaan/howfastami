#!/usr/bin/env python3

import sys
import os
import re
import time
import json
import socket
import struct
import unicodedata
import urllib.request
import urllib.error
import threading
import statistics
import ssl

C_RESET  = "\033[0m"
C_BOLD   = "\033[1m"
C_DIM    = "\033[2m"
C_ORANGE = "\033[38;2;246;130;31m"
C_CYAN   = "\033[38;2;52;152;219m"
C_GREEN  = "\033[38;2;46;204;113m"
C_YELLOW = "\033[38;2;241;196;15m"
C_RED    = "\033[38;2;231;76;60m"
C_GRAY   = "\033[90m"
C_WHITE  = "\033[97m"

SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

CF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Referer": "https://speed.cloudflare.com/",
    "Origin": "https://speed.cloudflare.com",
    "Accept": "*/*"
}

SSL_CTX = ssl.create_default_context()
ANSI_REGEX = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

def hide_cursor(): sys.stdout.write("\033[?25l"); sys.stdout.flush()
def show_cursor(): sys.stdout.write("\033[?25h"); sys.stdout.flush()
def clear_line(): sys.stdout.write("\033[2K\r"); sys.stdout.flush()

def visible_width(s):
    clean = ANSI_REGEX.sub('', s)
    width = 0
    for char in clean:
        w = unicodedata.east_asian_width(char)
        width += 2 if w in ('F', 'W') else 1
    return width

def box_divider(title="", inner_width=68, style="mid"):
    left_ch  = {"top": "╭", "mid": "├", "bot": "╰"}[style]
    right_ch = {"top": "╮", "mid": "┤", "bot": "╯"}[style]
    
    if not title:
        return f"{C_ORANGE}{left_ch}{'─' * inner_width}{right_ch}{C_RESET}"
    
    prefix = f"─ {title} "
    vis_len = visible_width(prefix)
    dashes = max(0, inner_width - vis_len)
    return f"{C_ORANGE}{left_ch}{prefix}{'─' * dashes}{right_ch}{C_RESET}"

def box_row(content="", inner_width=68):
    content_area = inner_width - 2
    vis_len = visible_width(content)
    pad = max(0, content_area - vis_len)
    return f"{C_ORANGE}│{C_RESET} {content}{' ' * pad} {C_ORANGE}│{C_RESET}"

def make_bar(percent, length=18):
    percent = max(0.0, min(1.0, percent))
    filled = int(length * percent)
    empty = length - filled
    return f"{C_ORANGE}{'━' * filled}{C_GRAY}{'━' * empty}{C_RESET}"

def sanitize_colo(colo_raw):
    iata = "ANY"
    city = ""
    if isinstance(colo_raw, list) and len(colo_raw) > 0:
        colo_raw = colo_raw[0]
    if isinstance(colo_raw, dict):
        iata = colo_raw.get("iata", "ANY")
        city = colo_raw.get("city", "")
    elif isinstance(colo_raw, str):
        iata = colo_raw

    pop_names = {
    "IST": "Istanbul",
    "SAW": "Istanbul Sabiha Gokcen",
    "ESB": "Ankara",
    "ADB": "Izmir",
    "AYT": "Antalya",

    "AMS": "Amsterdam", "ARN": "Stockholm", "ATH": "Athens", "BCN": "Barcelona",
    "BEG": "Belgrade", "BER": "Berlin", "BFS": "Belfast", "BGO": "Bergen",
    "BHX": "Birmingham", "BLQ": "Bologna", "BOD": "Bordeaux", "BRU": "Brussels",
    "BTS": "Bratislava", "BUD": "Budapest", "CDG": "Paris", "CHQ": "Chania",
    "CLJ": "Cluj-Napoca", "CPH": "Copenhagen", "CRL": "Charleroi", "CWL": "Cardiff",
    "DUB": "Dublin", "DUS": "Dusseldorf", "EDI": "Edinburgh", "FCO": "Rome",
    "FRA": "Frankfurt", "GLA": "Glasgow", "GOT": "Gothenburg", "GVA": "Geneva",
    "HAM": "Hamburg", "HEL": "Helsinki", "HER": "Heraklion", "KBP": "Kyiv",
    "KIV": "Chisinau", "KTW": "Katowice", "LCA": "Larnaca", "LED": "St. Petersburg",
    "LHR": "London", "LIS": "Lisbon", "LJU": "Ljubljana", "LUX": "Luxembourg",
    "LYS": "Lyon", "MAD": "Madrid", "MAN": "Manchester", "MRS": "Marseille",
    "MSQ": "Minsk", "MUC": "Munich", "MXP": "Milan", "NAP": "Naples",
    "NCE": "Nice", "NCL": "Newcastle", "OPO": "Porto", "ORK": "Cork",
    "OSL": "Oslo", "OTP": "Bucharest", "PMO": "Palermo", "POZ": "Poznan",
    "PRG": "Prague", "RHO": "Rhodes", "RIX": "Riga", "RZE": "Rzeszow",
    "SKG": "Thessaloniki", "SOF": "Sofia", "STR": "Stuttgart", "SVG": "Stavanger",
    "SVQ": "Seville", "SXB": "Strasbourg", "TLL": "Tallinn", "TLS": "Toulouse",
    "TRD": "Trondheim", "TSR": "Timisoara", "VCE": "Venice", "VIE": "Vienna",
    "VLC": "Valencia", "VNO": "Vilnius", "VRN": "Verona", "WAW": "Warsaw",
    "WRO": "Wroclaw", "ZAG": "Zagreb", "ZRH": "Zurich",

    "AMM": "Amman", "BAH": "Manama", "BEY": "Beirut", "BGW": "Baghdad",
    "BSR": "Basra", "DMM": "Dammam", "DOH": "Doha", "DXB": "Dubai",
    "EBL": "Erbil", "EVN": "Yerevan", "GYD": "Baku", "ISU": "Sulaymaniyah",
    "JED": "Jeddah", "KWI": "Kuwait City", "MCT": "Muscat", "MED": "Medina",
    "NJF": "Najaf", "RUH": "Riyadh", "TBS": "Tbilisi", "TLV": "Tel Aviv",
    "XNH": "Nasiriyah", "ZDM": "Ramallah",

    "ABQ": "Albuquerque", "ANC": "Anchorage", "ATL": "Atlanta", "AUS": "Austin",
    "BDL": "Hartford", "BGR": "Bangor", "BHM": "Birmingham (AL)", "BNA": "Nashville",
    "BOS": "Boston", "BTR": "Baton Rouge", "BUF": "Buffalo", "BWI": "Baltimore",
    "CLE": "Cleveland", "CLT": "Charlotte", "CMH": "Columbus", "COS": "Colorado Springs",
    "CVG": "Cincinnati", "DEN": "Denver", "DFW": "Dallas", "DSM": "Des Moines",
    "DTW": "Detroit", "EWR": "Newark", "GEG": "Spokane", "GSO": "Greensboro",
    "GSP": "Greenville", "HNL": "Honolulu", "IAD": "Washington D.C.", "IAH": "Houston",
    "IND": "Indianapolis", "JAX": "Jacksonville", "JFK": "New York", "LAS": "Las Vegas",
    "LAX": "Los Angeles", "LGA": "New York", "LIT": "Little Rock", "MCI": "Kansas City",
    "MCO": "Orlando", "MEM": "Memphis", "MFE": "McAllen", "MGM": "Montgomery",
    "MIA": "Miami", "MKE": "Milwaukee", "MSP": "Minneapolis", "MSY": "New Orleans",
    "OAK": "Oakland", "OKC": "Oklahoma City", "OMA": "Omaha", "ORD": "Chicago",
    "ORF": "Norfolk", "PDX": "Portland", "PHL": "Philadelphia", "PHX": "Phoenix",
    "PIT": "Pittsburgh", "RDU": "Raleigh", "RIC": "Richmond", "RNO": "Reno",
    "SAN": "San Diego", "SAT": "San Antonio", "SDF": "Louisville", "SEA": "Seattle",
    "SFO": "San Francisco", "SJC": "San Jose", "SLC": "Salt Lake City", "SMF": "Sacramento",
    "STL": "St. Louis", "TPA": "Tampa", "TUL": "Tulsa", "YEG": "Edmonton",
    "YHZ": "Halifax", "YOW": "Ottawa", "YQB": "Quebec", "YUL": "Montreal",
    "YVR": "Vancouver", "YWG": "Winnipeg", "YYC": "Calgary", "YYZ": "Toronto",

    "ACX": "Xingyi", "AIP": "Jalandhar", "AKX": "Aktobe", "ALA": "Almaty",
    "AMD": "Ahmedabad", "AQG": "Anqing", "AVA": "Anshun", "BBI": "Bhubaneswar",
    "BHY": "Beihai", "BKK": "Bangkok", "BLR": "Bangalore", "BOM": "Mumbai",
    "BPE": "Qinhuangdao", "CCU": "Kolkata", "CEB": "Cebu", "CGO": "Zhengzhou",
    "CGQ": "Changchun", "CGY": "Cagayan de Oro", "COK": "Kochi", "CSX": "Changsha",
    "CTU": "Chengdu", "DAC": "Dhaka", "DAD": "Da Nang", "DEL": "New Delhi",
    "FOC": "Fuzhou", "FUK": "Fukuoka", "FUO": "Foshan", "GAU": "Guwahati",
    "HAK": "Haikou", "HAN": "Hanoi", "HET": "Hohhot", "HGH": "Hangzhou",
    "HKG": "Hong Kong", "HND": "Tokyo (Haneda)", "HYD": "Hyderabad", "ICN": "Seoul",
    "ISB": "Islamabad", "ITM": "Osaka", "IXC": "Chandigarh", "JHB": "Johor Bahru",
    "JKT": "Jakarta", "KHI": "Karachi", "KIX": "Osaka (Kansai)", "KTM": "Kathmandu",
    "KUL": "Kuala Lumpur", "KWE": "Guiyang", "LHE": "Lahore", "MAA": "Chennai",
    "MDL": "Mandalay", "MFM": "Macau", "MLE": "Male", "MNL": "Manila",
    "NAG": "Nagpur", "NKG": "Nanjing", "NNG": "Nanning", "NQZ": "Astana",
    "NRT": "Tokyo (Narita)", "NTG": "Nantong", "OKA": "Okinawa", "PAT": "Patna",
    "PEN": "Penang", "PNH": "Phnom Penh", "PKX": "Beijing", "RGN": "Yangon",
    "SGN": "Ho Chi Minh", "SHA": "Shanghai", "SHE": "Shenyang", "SIN": "Singapore",
    "SJW": "Shijiazhuang", "SZX": "Shenzhen", "TAO": "Qingdao", "TAS": "Tashkent",
    "TNA": "Jinan", "TPE": "Taipei", "ULN": "Ulaanbaatar", "URC": "Urumqi",
    "VTE": "Vientiane", "WUH": "Wuhan", "XIY": "Xi'an", "XMN": "Xiamen",

    "ARI": "Arica", "ARU": "Aracatuba", "ASU": "Asuncion", "BAQ": "Barranquilla",
    "BEL": "Belem", "BGI": "Bridgetown", "BNU": "Blumenau", "BOG": "Bogota",
    "BSB": "Brasilia", "BZE": "Belize City", "CAU": "Caruaru", "CFB": "Cabo Frio",
    "CFC": "Cacador", "CGB": "Cuiaba", "CLO": "Cali", "CNF": "Belo Horizonte",
    "CPO": "Copiapo", "CUR": "Curacao", "CWB": "Curitiba", "EZE": "Buenos Aires",
    "FLN": "Florianopolis", "FOR": "Fortaleza", "GDL": "Guadalajara", "GEO": "Georgetown",
    "GIG": "Rio de Janeiro", "GND": "St. George's", "GRU": "Sao Paulo", "GUA": "Guatemala City",
    "GYE": "Guayaquil", "GYN": "Goiania", "IGG": "Iquique", "JOI": "Joinville",
    "KIN": "Kingston", "LIM": "Lima", "MAO": "Manaus", "MDE": "Medellin",
    "MEX": "Mexico City", "MVD": "Montevideo", "NAT": "Natal", "NVT": "Navegantes",
    "PAP": "Port-au-Prince", "PBM": "Paramaribo", "POA": "Porto Alegre", "PTY": "Panama City",
    "QRO": "Queretaro", "QWJ": "Americana", "RAO": "Ribeirao Preto", "REC": "Recife",
    "SAL": "San Salvador", "SAP": "San Pedro Sula", "SCL": "Santiago", "SDQ": "Santo Domingo",
    "SJK": "Sao Jose dos Campos", "SJP": "Sao Jose do Rio Preto", "SJU": "San Juan",
    "SSA": "Salvador", "STI": "Santiago (DR)", "TGU": "Tegucigalpa", "UIO": "Quito",
    "VIX": "Vitoria", "VVI": "Santa Cruz", "XAP": "Chapeco",

    "AAE": "Annaba", "ABJ": "Abidjan", "ACC": "Accra", "ADD": "Addis Ababa",
    "ALG": "Algiers", "ASK": "Yamoussoukro", "CPT": "Cape Town", "DKR": "Dakar",
    "DUR": "Durban", "EBB": "Entebbe", "GBE": "Gaborone", "HRE": "Harare",
    "JNB": "Johannesburg", "KGL": "Kigali", "LAD": "Luanda", "LOS": "Lagos",
    "MBA": "Mombasa", "MPM": "Maputo", "MRU": "Port Louis", "NBO": "Nairobi",
    "ORN": "Oran", "ROB": "Monrovia", "RUN": "Saint-Denis", "TNR": "Antananarivo",
    "TUN": "Tunis", "WDH": "Windhoek",

    "ADL": "Adelaide", "AKL": "Auckland", "BNE": "Brisbane", "CBR": "Canberra",
    "CHC": "Christchurch", "DRW": "Darwin", "GUM": "Guam", "HBA": "Hobart",
    "MEL": "Melbourne", "NOU": "Noumea", "PER": "Perth", "PPT": "Papeete",
    "SYD": "Sydney", "VLI": "Port Vila", "WLG": "Wellington"
    }

    city_name = pop_names.get(iata, city if city else iata)
    return f"{city_name} ({iata})" if city_name != iata else iata

def measure_stun(host="stun.cloudflare.com", port=3478, count=30):
    latencies = []
    lost = 0
    magic = 0x2112A442
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.5)

    try:
        dest_ip = socket.gethostbyname(host)
    except Exception:
        dest_ip = "162.159.200.1"

    for _ in range(count):
        trans_id = os.urandom(12)
        pkt = struct.pack("!HHI12s", 0x0001, 0, magic, trans_id)
        t_start = time.perf_counter()
        try:
            sock.sendto(pkt, (dest_ip, port))
            data, _ = sock.recvfrom(1024)
            rtt = (time.perf_counter() - t_start) * 1000.0
            latencies.append(rtt)
        except (socket.timeout, OSError):
            lost += 1
        time.sleep(0.02)

    sock.close()
    loss_pct = (lost / count) * 100.0
    avg_lat = statistics.mean(latencies) if latencies else 0.0
    min_lat = min(latencies) if latencies else 0.0
    return {"loss_pct": loss_pct, "avg_rtt": avg_lat, "min_rtt": min_lat}

def fetch_meta():
    meta = {}
    try:
        url = "https://speed.cloudflare.com/meta"
        req = urllib.request.Request(url, headers=CF_HEADERS)
        with urllib.request.urlopen(req, timeout=4, context=SSL_CTX) as res:
            meta = json.loads(res.read().decode())
    except Exception:
        pass

    if not meta or not meta.get("clientIp"):
        try:
            req = urllib.request.Request("https://1.1.1.1/cdn-cgi/trace", headers={"User-Agent": "curl/7.88.1"})
            with urllib.request.urlopen(req, timeout=4, context=SSL_CTX) as res:
                lines = res.read().decode().splitlines()
                trace_dict = dict(line.split("=", 1) for line in lines if "=" in line)
                meta["clientIp"] = trace_dict.get("ip", "Unknown")
                meta["colo"] = trace_dict.get("colo", "ANY")
                meta["country"] = trace_dict.get("loc", "TR")
        except Exception:
            pass

    country = meta.get("country", "")
    if country in ("TR", "Turkey"):
        country = "Turkey"

    return {
        "clientIp": meta.get("clientIp", "Unknown"),
        "isp": meta.get("asOrganization", f"AS{meta.get('asn', '')}").strip(),
        "asn": str(meta.get("asn", "")),
        "colo": sanitize_colo(meta.get("colo", "ANY")),
        "city": meta.get("city", "Unknown"),
        "country": country
    }

def single_probe():
    url = "https://speed.cloudflare.com/__down?bytes=0"
    req = urllib.request.Request(url, headers=CF_HEADERS)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=3, context=SSL_CTX) as res:
            res.read()
            return (time.perf_counter() - t0) * 1000.0
    except Exception:
        return None

def measure_unloaded(samples=12, callback=None):
    results = []
    for i in range(samples):
        lat = single_probe()
        if lat is not None:
            results.append(lat)
        if callback:
            callback(i + 1, samples)
        time.sleep(0.04)

    if not results:
        return 0.0, 0.0, 0.0

    avg_l = statistics.mean(results)
    min_l = min(results)
    jitter = statistics.mean([abs(results[j] - results[j-1]) for j in range(1, len(results))]) if len(results) > 1 else 0.0
    return min_l, avg_l, jitter

class SpeedEngine:
    def __init__(self):
        self.bytes_transferred = 0
        self.stop_event = threading.Event()
        self.loaded_latencies = []
        self.lock = threading.Lock()

    def _probe_worker(self):
        while not self.stop_event.is_set():
            lat = single_probe()
            if lat is not None:
                with self.lock:
                    self.loaded_latencies.append(lat)
            time.sleep(0.2)

    def test_download(self, duration=8, threads=5):
        self.bytes_transferred = 0
        self.stop_event.clear()
        self.loaded_latencies = []
        url = "https://speed.cloudflare.com/__down?bytes=15000000"

        def worker():
            buf = 65536
            while not self.stop_event.is_set():
                try:
                    req = urllib.request.Request(url, headers=CF_HEADERS)
                    with urllib.request.urlopen(req, timeout=4, context=SSL_CTX) as resp:
                        while not self.stop_event.is_set():
                            chunk = resp.read(buf)
                            if not chunk:
                                break
                            with self.lock:
                                self.bytes_transferred += len(chunk)
                except Exception:
                    time.sleep(0.05)

        t_probe = threading.Thread(target=self._probe_worker, daemon=True)
        t_probe.start()
        workers = [threading.Thread(target=worker, daemon=True) for _ in range(threads)]
        for w in workers: w.start()

        t0 = time.perf_counter()
        while True:
            elapsed = time.perf_counter() - t0
            if elapsed >= duration:
                break
            with self.lock:
                mbps = (self.bytes_transferred * 8) / (elapsed * 1_000_000) if elapsed > 0 else 0
            yield elapsed, duration, mbps
            time.sleep(0.08)

        self.stop_event.set()
        for w in workers: w.join(timeout=0.2)
        t_probe.join(timeout=0.2)
        total_time = time.perf_counter() - t0
        return (self.bytes_transferred * 8) / (total_time * 1_000_000)

    def test_upload(self, duration=8, threads=4):
        self.bytes_transferred = 0
        self.stop_event.clear()
        self.loaded_latencies = []
        url = "https://speed.cloudflare.com/__up"
        chunk_data = b"0" * (512 * 1024)

        def worker():
            while not self.stop_event.is_set():
                try:
                    up_hdrs = dict(CF_HEADERS)
                    up_hdrs["Content-Type"] = "application/octet-stream"
                    req = urllib.request.Request(url, data=chunk_data, headers=up_hdrs)
                    with urllib.request.urlopen(req, timeout=4, context=SSL_CTX) as resp:
                        resp.read()
                        with self.lock:
                            self.bytes_transferred += len(chunk_data)
                except Exception:
                    time.sleep(0.05)

        t_probe = threading.Thread(target=self._probe_worker, daemon=True)
        t_probe.start()
        workers = [threading.Thread(target=worker, daemon=True) for _ in range(threads)]
        for w in workers: w.start()

        t0 = time.perf_counter()
        while True:
            elapsed = time.perf_counter() - t0
            if elapsed >= duration:
                break
            with self.lock:
                mbps = (self.bytes_transferred * 8) / (elapsed * 1_000_000) if elapsed > 0 else 0
            yield elapsed, duration, mbps
            time.sleep(0.08)

        self.stop_event.set()
        for w in workers: w.join(timeout=0.2)
        t_probe.join(timeout=0.2)
        total_time = time.perf_counter() - t0
        return (self.bytes_transferred * 8) / (total_time * 1_000_000)

def evaluate_bufferbloat(unloaded, down_loaded, up_loaded):
    worst_loaded = max(down_loaded, up_loaded)
    delta = max(0, worst_loaded - unloaded)
    
    if delta <= 8:
        return "A+", C_GREEN, "Excellent", "Latency barely increases under heavy download load."
    elif delta <= 25:
        return "A", C_GREEN, "Very Good", "Minimal latency increase under heavy load."
    elif delta <= 50:
        return "B", C_CYAN, "Good", "Slight delay may be noticed in competitive gaming."
    elif delta <= 100:
        return "C", C_YELLOW, "Fair", "Latency spikes under load; voice/video calls may degrade."
    elif delta <= 200:
        return "D", C_RED, "Poor", "Gaming and video streams will freeze during downloads."
    else:
        return "F", C_RED, "Critical", f"Ping spikes by +{int(delta)} ms on download; SQM recommended."

def main():
    hide_cursor()
    try:
        os.system("clear" if os.name == "posix" else "cls")

        BOX_WIDTH = 68

        banner = f"""
{C_ORANGE}  How Fast Am I? {C_RESET}{C_DIM}• Simple Broadband Test Tool{C_RESET}
{C_GRAY}{'─' * (BOX_WIDTH + 2)}{C_RESET}"""
        print(banner)

        # 1. Metadata
        sys.stdout.write(f"  {C_ORANGE}⠋{C_RESET} Detecting client and nearest Cloudflare edge...")
        sys.stdout.flush()
        meta = fetch_meta()
        clear_line()

        isp_display = meta['isp']
        if len(isp_display) > 36:
            isp_display = isp_display[:34] + ".."

        print(f"  {C_WHITE}Client:{C_RESET}      {C_CYAN}{meta['clientIp']}{C_RESET} {C_GRAY}•{C_RESET} {isp_display} {C_GRAY}(AS{meta['asn']}){C_RESET}")
        print(f"  {C_WHITE}Route:{C_RESET}       {meta['city']}, {meta['country']} {C_GRAY}➔ {C_RESET} Cloudflare {C_ORANGE}{C_BOLD}{meta['colo']}{C_RESET}")
        print(f"{C_GRAY}{'─' * (BOX_WIDTH + 2)}{C_RESET}")

        sys.stdout.write(f"  {C_ORANGE}⠋{C_RESET} Measuring STUN UDP response & packet loss...")
        sys.stdout.flush()
        stun = measure_stun()
        clear_line()

        spin_idx = 0
        def ping_cb(cur, total):
            nonlocal spin_idx
            sp = SPINNER[spin_idx % len(SPINNER)]
            spin_idx += 1
            sys.stdout.write(f"\r  {C_ORANGE}{sp}{C_RESET} Measuring idle response time (Ping & Jitter)... [{cur}/{total}]")
            sys.stdout.flush()

        min_lat, avg_lat, jitter = measure_unloaded(samples=10, callback=ping_cb)
        clear_line()

        engine = SpeedEngine()
        spin_idx = 0
        down_gen = engine.test_download(duration=8, threads=5)
        for elapsed, total, cur_speed in down_gen:
            sp = SPINNER[spin_idx % len(SPINNER)]
            spin_idx += 1
            bar = make_bar(elapsed / total)
            sys.stdout.write(f"\r  {C_ORANGE}{sp}{C_RESET} Downloading   {bar} {C_GREEN}{C_BOLD}{cur_speed:7.1f} Mbps{C_RESET} {C_GRAY}[{elapsed:.0f}s]{C_RESET}")
            sys.stdout.flush()

        final_down = (engine.bytes_transferred * 8) / (8.0 * 1_000_000)
        avg_down_loaded = statistics.mean(engine.loaded_latencies) if engine.loaded_latencies else avg_lat
        clear_line()

        spin_idx = 0
        up_gen = engine.test_upload(duration=8, threads=4)
        for elapsed, total, cur_speed in up_gen:
            sp = SPINNER[spin_idx % len(SPINNER)]
            spin_idx += 1
            bar = make_bar(elapsed / total)
            sys.stdout.write(f"\r  {C_ORANGE}{sp}{C_RESET} Uploading     {bar} {C_CYAN}{C_BOLD}{cur_speed:7.1f} Mbps{C_RESET} {C_GRAY}[{elapsed:.0f}s]{C_RESET}")
            sys.stdout.flush()

        final_up = (engine.bytes_transferred * 8) / (8.0 * 1_000_000)
        avg_up_loaded = statistics.mean(engine.loaded_latencies) if engine.loaded_latencies else avg_lat
        clear_line()

        grade, grade_col, grade_title, grade_desc = evaluate_bufferbloat(avg_lat, avg_down_loaded, avg_up_loaded)
        loss_str = f"{stun['loss_pct']:.1f}%"
        loss_col = C_GREEN if stun['loss_pct'] == 0 else C_RED

        def row(txt=""): return box_row(txt, BOX_WIDTH)

        output_lines = [
            box_divider("BROADBAND CAPACITY", BOX_WIDTH, style="top"),
            row(""),
            row(f"  {C_GRAY}Download:{C_RESET}             {C_GREEN}{C_BOLD}{final_down:8.2f} Mbps{C_RESET}"),
            row(f"  {C_GRAY}Upload:{C_RESET}               {C_CYAN}{C_BOLD}{final_up:8.2f} Mbps{C_RESET}"),
            row(""),
            box_divider("LATENCY & STABILITY", BOX_WIDTH, style="mid"),
            row(""),
            row(f"  {C_GRAY}Unloaded Latency:{C_RESET}     {C_WHITE}{avg_lat:5.1f} ms{C_RESET}  {C_GRAY}(Min: {min_lat:.1f} ms, Jitter: ±{jitter:.1f} ms){C_RESET}"),
            row(f"  {C_GRAY}STUN (UDP) RTT:{C_RESET}       {C_WHITE}{stun['avg_rtt']:5.1f} ms{C_RESET}"),
            row(f"  {C_GRAY}Packet Loss:{C_RESET}          {loss_col}{loss_str:<6}{C_RESET}  {C_GRAY}(0% = Zero loss){C_RESET}"),
            row(""),
            box_divider("BUFFERBLOAT (LOAD IMPACT)", BOX_WIDTH, style="mid"),
            row(""),
            row(f"  {C_GRAY}Loaded (Download):{C_RESET}    {C_WHITE}{avg_down_loaded:5.1f} ms{C_RESET}  {C_GRAY}(Delta: +{max(0, avg_down_loaded-avg_lat):.0f} ms){C_RESET}"),
            row(f"  {C_GRAY}Loaded (Upload):{C_RESET}      {C_WHITE}{avg_up_loaded:5.1f} ms{C_RESET}  {C_GRAY}(Delta: +{max(0, avg_up_loaded-avg_lat):.0f} ms){C_RESET}"),
            row(""),
            row(f"  {C_GRAY}Quality Grade:{C_RESET}        {grade_col}{C_BOLD}[ {grade} - {grade_title} ]{C_RESET}"),
            row(f"  {C_DIM}↳ {grade_desc}{C_RESET}"),
            box_divider("", BOX_WIDTH, style="bot")
        ]

        print("\n" + "\n".join(output_lines) + "\n")

    except KeyboardInterrupt:
        clear_line()
        print(f"\n{C_RED}✖ Test cancelled by user.{C_RESET}\n")
    finally:
        show_cursor()

if __name__ == "__main__":
    main()