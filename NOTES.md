# 1. Setup OvsSwitch (Switch VM)
```
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

sysctl -w net.ipv4.ip_forward=1 #Forwarding IP 
```

# 2. Start Ryu Controller (Controller VM)
```
# Run Ryu script on 1 session
python controller/simple_l3_router.py

# On the other session, run Ryu exporter
python controller/ryu_exporter.py
# Or run Ryu Exporter with Docker Container
docker build -t "ryu_exporter:<version>" controller/
docker run --name ryu_exporter -d -p 9100:9100 ryu_exporter:<version>
```

# 3. Config IP Route
- Delete ens37,38 ip route on Switch VM -> change to using OVSSwitch Gateway
```
sudo ip route del 192.168.184.0/24 dev ens37
sudo ip route del 192.168.111.0/24 dev ens38
```
-  Attacker and Victim needs to change default ip route to OvsSwitch's Gateway in order to send requests to OvsSwitch
```
# Attacker
sudo ip route del 192.168.184.0/24 dev ens37
sudo ip route add default via 192.168.184.20 dev ens37 

# Victim
sudo ip route del 192.168.111.0/24 dev ens37
sudo ip route add default via 192.168.111.20 dev ens37 
```


# 4. Attacking
```
sudo hping3 -c 10000 -d 120 -S -w 64 -p 21 --flood --rand-source 192.168.111.13
sudo hping3 -c 10000 -d 120 -S -w 64 -p 80 --flood --rand-source 192.168.111.13
```
# 5. Check Alert logs Suricata
```
sudo tail -f /var/log/suricata/fast.log
```
# 6. Config Grafana Agent on Switch
```
sudo nano /etc/grafana-agent/agent.yaml
sudo systemctl restart grafana-agent
```
# 7. Edit Suricata.yaml
## 7.1. Set  interface
```
sudo nano /etc/suricata/suricata.yaml
af_packet
	interface: br-s1
```
## 7.2 Add rule
```
sudo nano /etc/suricata/rules/local.rules
alert tcp any any <> any any (msg:"Possible DDoS attack"; classtype:denial-of-service; sid:1001001; flags:PA;)
sudo suricata -T -c /etc/suricata/suricata.yaml -v
sudo systemctl restart suricata
```
