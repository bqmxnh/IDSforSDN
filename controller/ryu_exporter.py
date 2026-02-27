from prometheus_client import start_http_server, Gauge
import requests
import time

# URL REST API của Ryu (chỉnh lại nếu khác)
RYU_URL = "http://127.0.0.1:8080"

# Khởi tạo metrics
flow_bytes = Gauge('ryu_flow_bytes', 'Bytes per flow', ['dpid', 'src', 'dst', 'out_port'])
flow_packets = Gauge('ryu_flow_packets', 'Packets per flow', ['dpid', 'src', 'dst', 'out_port'])
port_rx_bytes = Gauge('ryu_port_rx_bytes', 'Received bytes per port', ['dpid', 'port'])
port_tx_bytes = Gauge('ryu_port_tx_bytes', 'Transmitted bytes per port', ['dpid', 'port'])

def get_json(url):
    """Gửi request HTTP GET và parse JSON"""
    try:
        res = requests.get(url, timeout=3)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"[!] Error fetching {url}: {e}")
        return {}

def get_switches():
    """Lấy danh sách DPID của các switch"""
    switches = get_json(f"{RYU_URL}/stats/switches")
    if isinstance(switches, list):
        return switches
    return []

def collect_flow_stats(dpid):
    """Thu thập flow stats của từng switch"""
    stats = get_json(f"{RYU_URL}/stats/flow/{dpid}")
    for sw, flows in stats.items():
        for f in flows:
            match = f.get('match', {})
            src = match.get('ipv4_src', 'unknown')
            dst = match.get('ipv4_dst', 'unknown')
            actions = f.get('actions', [])
            out_port = str(actions[0]) if actions else 'none'
            flow_bytes.labels(sw, src, dst, out_port).set(f.get('byte_count', 0))
            flow_packets.labels(sw, src, dst, out_port).set(f.get('packet_count', 0))

def collect_port_stats(dpid):
    """Thu thập port stats của từng switch"""
    stats = get_json(f"{RYU_URL}/stats/port/{dpid}")
    for sw, ports in stats.items():
        for p in ports:
            port_no = str(p.get('port_no'))
            rx = p.get('rx_bytes', 0)
            tx = p.get('tx_bytes', 0)
            port_rx_bytes.labels(sw, port_no).set(rx)
            port_tx_bytes.labels(sw, port_no).set(tx)

if __name__ == "__main__":
    print("Starting Ryu Prometheus Exporter on port 9100...")
    start_http_server(9100)
    while True:
        dpid_list = get_switches()
        for dpid in dpid_list:
            collect_flow_stats(dpid)
            collect_port_stats(dpid)
        time.sleep(5)

