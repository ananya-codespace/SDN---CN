# SDN - CN
# SDN-Based Access Control Whitelist
**Course:** Computer Networks Lab  
**Project Type:** SDN Mininet Simulation (Orange Problem #11)

## Project Overview
This project implements a security-focused SDN (Software-Defined Networking) controller using the POX framework. The primary goal is to enforce a network access policy where only "authorized" devices can communicate, while all "unauthorized" traffic is blocked and logged.

## Problem Statement
Implement an SDN controller that:
1. Maintains a **Whitelist** of authorized MAC addresses (h1 and h2).
2. Intercepts all incoming packets via the `PacketIn` handler.
3. Automatically drops packets originating from unauthorized MAC addresses (h3 and h4).
4. Installs specific **Match-Action** flow rules on the Open vSwitch for authorized traffic to minimize controller overhead.

## Setup and Execution

### 1. Prerequisites
Ensure you have Mininet and POX installed in your Ubuntu/WSL environment.

### 2. Running the Controller
Place `access_control.py` in the `pox/ext` directory and run:
```bash
python3 pox.py log.level --DEBUG ext.access_control

### 3. Launching the Network
In a separate terminal, start the Mininet topology with the `--mac` flag to ensure sequential MAC addresses:
```bash
sudo mn --topo single,4 --controller remote,ip=127.0.0.1,port=6633 --mac
![Launching the network](./screenshots/initial_test.png)

## Results & Validation

### Connectivity Testing
* **h1 -> h2 (Authorized):** Communication is successful with 0% packet loss.
![Ping Success](./screenshots/allowed_test.png)

* **h3 -> h4 (Unauthorized):** Communication is blocked; results in 100% packet loss.
![Ping Blocked](./screenshots/blocked_test.png)

* **pingall:** Demonstrates that only the h1-h2 pair is reachable.
![Pingall](./screenshots/pingall.png)

### Flow Table Verification
By running `dpctl dump-flows` on the switch, we observe that the controller successfully installs flow entries that match the whitelisted MAC addresses.
![Flow Table](./screenshots/flow_table.png)