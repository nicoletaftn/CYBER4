# Scope-Aware Cyber-AutoAgent

Layered Scope Enforcement Framework for Autonomous Agentic AI Black-box Web Penetration Testing built on top of Cyber-AutoAgent.

This project extends the original [Cyber-AutoAgent](https://github.com/westonbrown/Cyber-AutoAgent) system with deterministic scope enforcement mechanisms designed to constrain autonomous AI-based penetration testing systems within predefined operational boundaries.

---

## Overview

Modern agentic AI penetration testing systems rely heavily on Large Language Models (LLMs) to autonomously perform reconnaissance, vulnerability discovery, and exploitation tasks. However, relying only on prompt instructions to enforce testing boundaries is unreliable, as LLMs may ignore, reinterpret, or lose contextual scope constraints during long autonomous executions.

This project introduces a layered scope enforcement framework that applies deterministic enforcement mechanisms at multiple levels of the system:

- Endpoints-Level Scope Enforcement
- Domains/Subdomains Scope Enforcement
- Firewall-Based Network Enforcement

The goal is to provide stronger and more reliable scope control than relying on a single enforcement mechanism alone.

---

## Layered Scope Enforcement Architecture

The implemented framework applies enforcement at two different abstraction levels:

### Application-Level Enforcement

Validates tool-generated actions before execution.

#### Endpoints-Level Enforcement

Blocks access to specific out-of-scope application routes.

Examples:
- `/robots.txt`
- `/ftp`
- `/score-board`
- `api/Challenges`

#### Domains/Subdomains Enforcement

Blocks access to restricted domains or subdomains.

Example:
- `dev.juice-shop`

---

### Infrastructure-Level Enforcement

Controls outbound network communication independently of the AI reasoning process.

#### Firewall Enforcement

Restricts outbound communication to explicitly authorised targets only.

This prevents:
- Access to external systems
- Access to unrelated systems outside the defined testing scope(e.g. Juice Crew web application)
- Communication with random internet targets

---

### Layered Scope Enforcement Diagram

<img width="720" height="370" alt="Layered Approach" src="https://github.com/user-attachments/assets/8d8a1352-9114-4770-83f8-3330768e1d27" />

---

## Project Structure

### Core Scope Enforcement Implementation

#### Endpoints & Domains/Subdomains Enforcement

Main implementation located in:

```bash
src/cyber_autoagent.py
```

This contains:
- Tool call interception logic
- Scope validation workflow
- Endpoints validation
- Domains/subdomains validation
- OUT_OF_SCOPE blocking responses

---

#### Scope Definitions

```bash
out_of_scope.txt
```

Defines:
- `[ENDPOINTS]`
- `[DOMAINS]`

Example:

```txt
[ENDPOINTS]
/score-board
/ftp
/api/Challenges

[DOMAINS]
dev.juice-shop
```

---

#### Firewall Enforcement

Located in:

```bash
experimental setup and firewall/firewall.sh
experimental setup and firewall/firewall-loop.sh
```

Responsible for:
- Dynamic iptables configuration
- Docker container traffic filtering
- Default deny outbound policy
- AWS Bedrock allow rules
- Internal target allow rules

---

## Scope Enforcement Layers

| Layer | Enforcement Type | Level |
|---|---|---|
| Endpoints Enforcement | Tool Call Validation | Application Level |
| Domains/Subdomains Enforcement | Tool Call Validation | Application Level |
| Firewall Enforcement | Network Restrictions | Infrastructure Level |

---

## Experimental Setups

The project includes two experimental setups used throughout the evaluation.

---

## Setup 1 — Baseline System (Prompt-Based Scope Control Only)

Used for:

- Initial Experiment/Demonstration
- Baseline behaviour evaluation
- No deterministic scope enforcement implemented

### Architecture

- Cyber-AutoAgent container
- OWASP Juice Shop container
- Docker network (`cyber-net`)

### Setup Diagram

<img width="720" height="370" alt="Initial Setup" src="https://github.com/user-attachments/assets/66d7c38a-77b1-41bd-b74d-a0d073a6827a" />

---

### Setup Commands

#### Create Docker Network

```bash
docker network create cyber-net
```

---

#### Start OWASP Juice Shop

```bash
docker run -d \
--name juice \
--network cyber-net \
bkimminich/juice-shop
```

---

#### Build Cyber-AutoAgent

> IMPORTANT:
> For Setup 1 / Initial Experiment, the project version without any of the layered scope enforcement implementations  must be used.
>
> Checkout the `original` branch of this repository, then build from inside the project folder using:
>
> ```bash
> docker build -t cyber-autoagent -f docker/Dockerfile .
> ```

---

#### Run the AI Pentesting System

The user must replace the AWS Bedrock credentials below with their own valid AWS credentials.

```bash
docker run -it \
--name cyber-agent-original \
--network cyber-net \
-e AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY \
-e AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY \
-e AWS_REGION=us-east-1 \
-e NODE_OPTIONS="--max-old-space-size=4096" \
cyber-autoagent
```

---

## Setup 2 — Application-Level Scope Enforcement

Used for:

- Test Case 1
- Test Case 2
- Test Case 3
- Test Case 4

This setup is the base environment for all test cases. Test Cases 3 and 4 additionally require the Firewall Execution steps described further below.

---

### Architecture

- Cyber-AutoAgent
- Modified OWASP Juice Shop
- Simulated subdomain
- NGINX reverse proxy
- Juice Crew web application

---

### Setup Diagram

<img width="625" height="454" alt="Second Setup copy" src="https://github.com/user-attachments/assets/f9a57837-51fc-4b97-8a2d-abc31733235f" />

---

### Setup Commands

#### Create Docker Network

```bash
docker network create cyber-net
```

---

#### Build and Start Modified OWASP Juice Shop

Clone the repository and build the image from inside the project folder:

```bash
git clone https://github.com/nicoletaftn/Modified-OWASP-Juice-Shop-Web-Application.git
cd Modified-OWASP-Juice-Shop-Web-Application
docker build -t juice-shop -f Dockerfile .
```

Then start the container:

```bash
docker run -d \
--name juice \
--network cyber-net \
juice-shop
```

---

#### Start Simulated Subdomain

Run this command from inside the `experimental setup and firewall` folder.

IMPORTANT:
Do NOT run this command from inside the `dev-page` folder.

```bash
docker run -d \
--name dev-page \
--network cyber-net \
-v "$(pwd)/dev-page:/usr/share/nginx/html:ro" \
nginx:alpine
```

---

#### Start NGINX Proxy

Run this command from inside the `experimental setup and firewall` folder:

```bash
docker run -d \
--name proxy \
--network cyber-net \
--network-alias juice-shop \
--network-alias dev.juice-shop \
-p 3000:3000 \
-v "$(pwd)/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
nginx:alpine
```

---

#### Start Juice Crew Web Application

Clone the repository, then run the command from inside the `people-page` folder:

```bash
git clone https://github.com/nicoletaftn/Juice-Crew.git
cd Juice-Crew/people-page
```

```bash
docker run -d \
--name people-page \
--network cyber-net \
-p 8081:80 \
-v "$(pwd):/usr/share/nginx/html:ro" \
nginx:alpine
```

---

### Test Case 1 — Endpoints Enforcement Only

For this test case, the user must switch to the branch containing ONLY the endpoints scope enforcement implementation.

Checkout the branch:

```bash
git checkout endpoints_scope_enforcement_only
```

The codebase in this branch contains:
- Endpoints scope enforcement implementation only

The codebase does NOT contain:
- Domains/subdomains scope enforcement
- Firewall scope enforcement implementation

After checking out the correct branch, build the project from inside the project root folder:

```bash
docker build -t cyber-autoagent -f docker/Dockerfile .
```

---

#### Run

The user must replace the AWS Bedrock credentials below with their own valid AWS credentials.

```bash
docker run -it \
--name cyber-agent-endpoints \
--network cyber-net \
-e AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY \
-e AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY \
-e AWS_REGION=us-east-1 \
-e NODE_OPTIONS="--max-old-space-size=4096" \
cyber-autoagent
```

---

### Test Case 2 — Domains/Subdomains Enforcement Only

For this test case, the user must switch to the branch containing ONLY the domains/subdomains scope enforcement implementation.

Checkout the branch:

```bash
git checkout domains_and_subdomains_scope_enforcement_only
```

The codebase in this branch contains:
- Domains/subdomains scope enforcement implementation only

The codebase does NOT contain:
- Endpoints scope enforcement
- Firewall scope enforcement implementation

After checking out the correct branch, build the project from inside the project root folder:

```bash
docker build -t cyber-autoagent -f docker/Dockerfile .
```

---

#### Run

The user must replace the AWS Bedrock credentials below with their own valid AWS credentials.

```bash
docker run -it \
--name cyber-agent-domains \
--network cyber-net \
-e AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY \
-e AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY \
-e AWS_REGION=us-east-1 \
-e NODE_OPTIONS="--max-old-space-size=4096" \
cyber-autoagent
```

---

## Test Case 3 — Firewall Enforcement Only

This test case uses Setup 2 as the base environment, plus the Firewall Execution steps below. As shown in the following diagrams:

<img width="814" height="545" alt="Final Setup " src="https://github.com/user-attachments/assets/89d6b8eb-c021-4ead-b003-c5cf9dc40da7" />

---

<img width="717" height="494" alt="Firewall Functionality Illustrated copy" src="https://github.com/user-attachments/assets/07c85412-d54f-461f-8cbd-83a5d5cb9a99" />

The project version without any of the layered scope enforcement implementations must be used.

Checkout the `original` branch of this repository, then build from inside the project folder using:

```bash
docker build -t cyber-autoagent -f docker/Dockerfile .
```

---

#### Run

The user must replace the AWS Bedrock credentials below with their own valid AWS credentials.

```bash
docker run -it \
--name cyber-agent-original \
--network cyber-net \
-e AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY \
-e AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY \
-e AWS_REGION=us-east-1 \
-e NODE_OPTIONS="--max-old-space-size=4096" \
cyber-autoagent
```

---

## Firewall Execution

Run from inside the `experimental setup and firewall` folder.

---

### Make Scripts Executable

```bash
chmod +x firewall.sh
chmod +x firewall-loop.sh
```

---

### Start Firewall Enforcement

```bash
./firewall-loop.sh
```

---

## Test Case 4 — Full Layered Enforcement

This test case uses Setup 2 as the base environment, plus the Firewall Execution steps above.

> IMPORTANT:
> Before running the firewall, open `firewall.sh` and update line 4 to match the container name used in this test case:
>
> ```bash
> AGENT="cyber-agent-layered"
> ```

For this test case, the user must build the latest project version containing:
- Endpoints scope enforcement
- Domains/subdomains scope enforcement
- Firewall scope enforcement

This represents the complete layered scope enforcement framework.

#### Build

```bash
docker build -t cyber-autoagent -f docker/Dockerfile .
```

---

#### Run

The user must replace the AWS Bedrock credentials below with their own valid AWS credentials.

```bash
docker run -it \
--name cyber-agent-layered \
--network cyber-net \
-e AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY \
-e AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY \
-e AWS_REGION=us-east-1 \
-e NODE_OPTIONS="--max-old-space-size=4096" \
cyber-autoagent
```

---

## AWS Bedrock Model Configuration

After the system starts:

Go to:

```bash
/config
```

Configure:
- AWS Bedrock model
- Additional Cyber-AutoAgent settings

Example:

<img width="591" height="785" alt="Screenshot 2026-05-19 at 14 48 23" src="https://github.com/user-attachments/assets/4bffc16b-0c78-471a-94ba-eb3a641a750d" />

Additional configuration options are documented in the original Cyber-AutoAgent documentation inside:

```bash
docs/
```

---

## Restarting the GUI (ONLY IF NEEDED)

Inside the container:

```bash
node /app/src/modules/interfaces/react/dist/index.js
```

---

## Operating System Compatibility

| Layer | Supported OS |
|---|---|
| Endpoints Enforcement | Any OS |
| Domains/Subdomains Enforcement | Any OS |
| Firewall Enforcement | Linux Only |

---

## Experimental Environment Used

| Test Cases | Operating System |
|---|---|
| Initial Experiment, Test Cases 1–2 | macOS |
| Test Cases 3–4 | Linux |

---

## Evaluation Test Cases

The evaluation of the framework consists of an initial experiment and four separate test cases:

| Test Case | Purpose |
|---|---|
| Initial Experiment/Demonstration | Baseline system using only prompt-based scope control |
| Test Case 1 | Endpoints scope enforcement evaluation |
| Test Case 2 | Domains/subdomains scope enforcement evaluation |
| Test Case 3 | Firewall enforcement evaluation |
| Test Case 4 | Full layered scope enforcement evaluation |

---

## Unit Tests

The project also includes dedicated unit tests for the application-level scope enforcement implementations.

### Endpoints Scope Enforcement Unit Tests

```bash
test_out_of_scope_filter.py
```

Tests:
- Endpoint detection
- Endpoint blocking
- OUT_OF_SCOPE responses

---

### Domains/Subdomains Scope Enforcement Unit Tests

```bash
test_out_of_scope_domains_filter.py
```

Tests:
- Domain detection
- Subdomain detection
- Blocking behaviour

---

> NOTE:
> The firewall implementation does not include dedicated unit tests.
> It is instead evaluated through the experimental evaluation test cases.

---

## Results Summary

The evaluation demonstrated:

- Prompt-only scope control is unreliable
- Endpoints enforcement blocks restricted routes
- Domains/Subdomains enforcement blocks restricted domains and subdomains
- Firewall enforcement blocks unauthorised external systems
- Combining all layers provides significantly stronger scope control

---

## Original Cyber-AutoAgent

This project extends:

```txt
Cyber-AutoAgent
https://github.com/westonbrown/Cyber-AutoAgent
```

For additional information regarding:
- Architecture
- GUI usage
- LLM configuration
- Supported tools
- Internal modules

See the original documentation in:

```bash
docs/
```
---

## Thesis Reference

This implementation was developed as part of the master thesis:

> Scope-Aware Agentic AI for Web Penetration Testing  
> Nicoleta Fartan  
> Aalborg University  
> 2026

