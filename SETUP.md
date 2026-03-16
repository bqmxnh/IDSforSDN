# IDS for SDN - Setup Guide

## 1. Setup OVS Switch (Switch VM)
Create the OVS bridge, attach physical ports, create two internal gateways, and point to the Ryu controller.

```bash
sudo ovs-vsctl --if-exists del-br br-s1
sudo ovs-vsctl add-br br-s1

sudo ovs-vsctl add-port br-s1 ens37
sudo ovs-vsctl add-port br-s1 ens38

sudo ovs-vsctl add-port br-s1 gw-vmnet1 -- set interface gw-vmnet1 type=internal
sudo ovs-vsctl add-port br-s1 gw-vmnet2 -- set interface gw-vmnet2 type=internal

sudo ip link set br-s1 up
sudo ip link set ens37 up
sudo ip link set ens38 up
sudo ip link set gw-vmnet1 up
sudo ip link set gw-vmnet2 up

sudo ip addr add 192.168.184.20/24 dev gw-vmnet1
sudo ip addr add 192.168.111.20/24 dev gw-vmnet2

sudo sysctl -w net.ipv4.ip_forward=1

sudo ovs-vsctl set-controller br-s1 tcp:192.168.111.12:6653
sudo ovs-vsctl set-fail-mode br-s1 standalone
sudo ovs-vsctl set bridge br-s1 protocols=OpenFlow13
```

Notes:
- `ens37` and `ens38` must match the actual interface names on your Switch VM.
- Enabling IP forwarding once is enough. You do not need to repeat it.
- Quick verification: `sudo ovs-vsctl show`.

## 2. Start Ryu Controller (Controller VM)
Run the Ryu router app and expose metrics for Prometheus scraping.

```bash
# Session 1: Ryu app
python controller/simple_l3_router.py

# Session 2: Exporter
python controller/ryu_exporter.py
```

If you run the exporter with Docker:

```bash
docker build -t "ryu_exporter:<version>" controller/
docker run --name ryu_exporter -d -p 9100:9100 ryu_exporter:<version>
```

Notes:
- If you run the Docker exporter, you do not need to also run `python controller/ryu_exporter.py`.
- Make sure port `9100` is reachable by Prometheus.

## 3. Configure IP Route
Force traffic through the OVS gateway instead of direct routing on default NIC routes.

### 3.1 On Switch VM
Delete network routes on `ens37` and `ens38` to avoid conflicts with OVS.

```bash
sudo ip route del 192.168.184.0/24 dev ens37
sudo ip route del 192.168.111.0/24 dev ens38
```

### 3.2 On Attacker and Victim
Set the default gateway to OVS (`192.168.184.20` and `192.168.111.20`).

```bash
# Attacker
sudo ip route del 192.168.184.0/24 dev ens37
sudo ip route add default via 192.168.184.20 dev ens37

# Victim
sudo ip route del 192.168.111.0/24 dev ens37
sudo ip route add default via 192.168.111.20 dev ens37
```

Notes:
- Check current routes with: `ip route`.
- If SSH is lost after route changes, use the VM console to recover.

## 4. Generate SYN Flood Traffic (Attacker)
Generate attack traffic to test IDS detection and monitoring.

```bash
sudo hping3 -c 10000 -d 120 -S -w 64 -p 21 --flood --rand-source 192.168.111.13
sudo hping3 -c 10000 -d 120 -S -w 64 -p 80 --flood --rand-source 192.168.111.13
```

Notes:
- Run only in an isolated lab/test network.
- You can replace `-p 21` and `-p 80` with other target ports.

## 5. Check Suricata Alert Log

```bash
sudo tail -f /var/log/suricata/fast.log
```

Notes:
- Look for `Possible DDoS attack` messages to confirm rule matches.

## 6. Configure Grafana Agent (Switch VM)

```bash
sudo nano /etc/grafana-agent/agent.yaml
sudo systemctl restart grafana-agent
```

Notes:
- After restart, verify service status with: `sudo systemctl status grafana-agent`.

## 7. Configure Suricata

### 7.1 Set Capture Interface

```bash
sudo nano /etc/suricata/suricata.yaml
```

In the `af_packet` section, set the interface to:

```yaml
af_packet:
  - interface: br-s1
```

### 7.2 Add Local Detection Rule

```bash
sudo nano /etc/suricata/rules/local.rules
```

Add this rule:

```text
alert tcp any any <> any any (msg:"Possible DDoS attack"; classtype:denial-of-service; sid:1001001; flags:PA;)
```

Validate and restart Suricata:

```bash
sudo suricata -T -c /etc/suricata/suricata.yaml -v
sudo systemctl restart suricata
```

Notes:
- Always run `suricata -T` before restart to catch syntax errors.
- If no alerts appear, re-check `br-s1`, routing, and attack traffic generation.
