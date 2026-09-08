# How Fast Am I?

A standalone CLI utility to benchmark network throughput, round-trip latency, UDP packet loss, and bufferbloat against Cloudflare edge infrastructure.

Written in standard Python 3. No external packages, no `pip`, zero dependencies.

---

## Overview

Most modern speed test utilities pull megabytes of bloatware or rely on browser engines. `howfastami` is a single-file script that relies strictly on the Python standard library (`urllib`, `socket`, `threading`, `struct`).

It measures:
- Raw download and upload bandwidth via concurrent HTTP streams.
- Unloaded TCP round-trip time (RTT) and jitter.
- UDP latency and packet loss via direct STUN binding requests (RFC 5389).
- Bufferbloat (loaded latency delta during transfer saturation) with an A+ to F grade.

---

## Requirements

- Python 3.6+
- Linux, BSD, or macOS
- Outbound access to TCP 443 (HTTPS) and UDP 3478 (STUN)

---

## Installation

### System-wide (recommended)

Download directly to your `$PATH` (`/usr/local/bin`):

```sh
sudo curl -fsSL https://raw.githubusercontent.com/hamzainaan/howfastami/main/speed.py -o /usr/local/bin/howfastami && sudo chmod +x /usr/local/bin/howfastami
```

Run it:

```sh
howfastami
```

### Run without installing

Pipe directly into your Python interpreter:

```sh
curl -fsSL https://raw.githubusercontent.com/hamzainaan/howfastami/main/speed.py | python3
```

---

## Sample Output

```text
  How Fast Am I? • Simple Broadband Test Tool
──────────────────────────────────────────────────────────────────────
  Client:      198.51.100.24 • Example ISP (AS12345)
  Route:       Frankfurt, Germany ➔ Cloudflare Frankfurt (FRA)
──────────────────────────────────────────────────────────────────────

╭─ BROADBAND CAPACITY ────────────────────────────────────────────────╮
│                                                                    │
│   Download:             248.50 Mbps                                │
│   Upload:                52.10 Mbps                                │
│                                                                    │
├─ LATENCY & STABILITY ───────────────────────────────────────────────┤
│                                                                    │
│   Unloaded Latency:       11.4 ms  (Min: 10.2 ms, Jitter: ±0.6 ms) │
│   STUN (UDP) RTT:         11.8 ms                                  │
│   Packet Loss:            0.0%     (0% = Zero loss)                │
│                                                                    │
├─ BUFFERBLOAT (LOAD IMPACT) ─────────────────────────────────────────┤
│                                                                    │
│   Loaded (Download):      15.2 ms  (Delta: +4 ms)                  │
│   Loaded (Upload):        18.1 ms  (Delta: +7 ms)                  │
│                                                                    │
│   Quality Grade:          [ A+ - Excellent ]                       │
│   ↳ Latency barely increases under heavy download load.            │
╰────────────────────────────────────────────────────────────────────╯
```

---

## How It Works

1. **Routing & Edge Discovery:** Queries Cloudflare metadata endpoints (`/meta` or `/cdn-cgi/trace`) to resolve the client IP, autonomous system number (ASN), and the serving airport PoP code.
2. **STUN Analysis:** Crafts raw binary STUN binding request packets (`0x0001`, magic cookie `0x2112A442`) over UDP to `stun.cloudflare.com:3478` to evaluate real datagram drop rates.
3. **Throughput Testing:** Spawns concurrent worker threads across 8-second execution windows:
   - **Download:** Concurrent chunked reads from `/__down`.
   - **Upload:** Repeated binary payloads to `/__up`.
4. **Bufferbloat Measurement:** A background thread measures zero-byte latency probes concurrently while saturation threads run at full capacity. The delta ($\Delta = \text{RTT}_{\text{loaded}} - \text{RTT}_{\text{idle}}$) determines the grade.

---

## Uninstall

```sh
sudo rm -f /usr/local/bin/howfastami
```

---

## License

MIT. Inspect the code, fork it, or modify it as needed.
