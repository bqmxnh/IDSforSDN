# UIT Project - NT541 - IDS on Software-Defined Network
## System Architecture:
![Architecuture](img/architecture.png)
## IP Addresses:
| Tên máy | Interface | Địa chỉ IP |
| :--- | :--- | :--- |
| Switch VM | VMNet 2, VMNet 1 | VMNet 2: 192.168.111.10/24 <br> VMNet 1: 192.168.184.10/24 |
| Management VM | VMNet 2 | VMNet 2: 192.168.111.11/24 |
| Controller VM | VMNet 2 | VMNet 2: 192.168.111.12/24 |
| Victim VM | VMNet 2 | VMNet 2: 192.168.111.13/24 |
| Attacker | VMNet 1 | 192.168.184.11 |
## Notes for this project: [Note](NOTES.md)
## Workflow
### DDoS Attack
```mermaid
sequenceDiagram
    participant A as Attacker (hping3)
    participant S as OVS Switch
    participant C as Ryu Controller
    participant I as Suricata IDS
    participant V as Victim

    Note over A: Bắt đầu tấn công SYN Flood
    loop Hàng ngàn packets/giây
        A->>S: Gửi TCP SYN (Src IP ngẫu nhiên)
        
        par Xử lý SDN
            S->>C: Packet-In (Gói tin mới)
            C->>S: Packet-Out + FlowMod (Cài luật)
            Note right of C: CPU Controller tăng vọt (Quá tải)
        and Xử lý IDS
            S->>I: Mirror/Copy Traffic
            I->>I: Khớp luật (Signature Match)
            I-->>Log: Ghi log "Possible DDoS attack"
        end
        
        S->>V: Chuyển tiếp gói tin (Nếu không bị drop)
    end
```


## Result:
- Created a SDN Architecture with OVSSwitch and Ryu Controller
![SDN](img/ovsctl.png)

- Monitoring System with Prometheus, Grafana, Loki
![Grafana](img/grafana_1.jpg)
![Grafana](img/grafana_2.jpg)
![Log](img/log_1.jpg)
![Log](img/log_2.jpg)

- Successfully detected DDoS attack with Suricata
![DDoS](img/ddos_detection.png)