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

#### Endpoint-Level Enforcement

Blocks access to specific out-of-scope application routes.

Examples:
- `/contact`
- `/about`
- `/ftp`
- `/robots.txt`

#### Domain/Subdomain Enforcement

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
- Access to unrelated vulnerable applications
- Communication with random internet targets

---

### Layered Scope Enforcement Diagram

<img width="720" height="370" alt="Layered Approach" src="https://github.com/user-attachments/assets/8d8a1352-9114-4770-83f8-3330768e1d27" />

---

## Project Structure

### Core Scope Enforcement Implementation

#### Endpoint & Domain/Subdomain Enforcement

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
/contact
/ftp
/robots.txt

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

The project includes three experimental setups used throughout the evaluation.

---

## Setup 1 — Baseline System (Prompt-Based Enforcement Only)

Used for:

- Test Case 1
- Baseline behaviour evaluation
- No deterministic scope enforcement

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
> For Setup 1 / Test Case 1, the original Cyber-AutoAgent project must be used without any of the layered scope enforcement implementations from this repository.
>
> Clone the original project from:
>
> https://github.com/westonbrown/Cyber-AutoAgent
>
> Then build the original version from inside the original Cyber-AutoAgent project folder using:
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

- Test Case 2
- Test Case 3

This setup evaluates:
- Endpoints scope enforcement
- Domains/subdomains scope enforcement

Each mechanism is tested independently.

---

### Architecture

- Cyber-AutoAgent
- OWASP Juice Shop
- Simulated subdomain
- NGINX reverse proxy

---

### Setup Diagram

<img width="720" height="370" alt="Second Setup" src="https://github.com/user-attachments/assets/795fd255-195a-4ffc-bfa0-121727f81034" />

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

### Test Case 2 — Endpoint Enforcement Only

For this test case, the user must switch to the branch containing ONLY the endpoint scope enforcement implementation.

Checkout the branch:

```bash
git checkout endpoints_scope_enforcement_only
```

The codebase in this branch contains:
- Endpoint scope enforcement implementation only

The codebase does NOT contain:
- Domain/subdomain scope enforcement
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

### Test Case 3 — Domain/Subdomain Enforcement Only

For this test case, the user must switch to the branch containing ONLY the domain/subdomain scope enforcement implementation.

Checkout the branch:

```bash
git checkout domains_and_subdomains_scope_enforcement_only
```

The codebase in this branch contains:
- Domains/subdomains scope enforcement implementation only

The codebase does NOT contain:
- Endpoint scope enforcement
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

## Setup 3 — Firewall & Layered Enforcement

Used for:

- Test Case 4
- Test Case 5

This setup evaluates:
- Firewall enforcement individually
- Full layered scope enforcement framework

---

### Setup Diagram

<img width="720" height="400" alt="Final Setup" src="https://github.com/user-attachments/assets/071ac62f-04b5-4a35-af98-45912785c401" />

---

## Setup Commands

### Create Docker Network

```bash
docker network create cyber-net
```

---

### Start OWASP Juice Shop

```bash
docker run -d \
--name juice \
--network cyber-net \
bkimminich/juice-shop
```

---

### Start Simulated Subdomain

Run this command from inside the `experimental setup and firewall` folder:

```bash
docker run -d \
--name dev-page \
--network cyber-net \
-v "$(pwd)/dev-page:/usr/share/nginx/html:ro" \
nginx:alpine
```

---

### Start NGINX Proxy

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

## DVPWA Setup

Clone:

```bash
https://github.com/anxolerd/dvpwa
```

Replace the docker compose file with:

```yaml
version: "3.3"

services:
  postgres:
    build:
      context: .
      dockerfile: Dockerfile.db
    ports:
      - "5432:5432"
    networks:
      cyber-net:
        aliases:
          - postgres

  redis:
    image: redis:alpine
    networks:
      cyber-net:
        aliases:
          - redis

  sqli:
    build:
      context: .
      dockerfile: Dockerfile.app
    depends_on:
      - postgres
      - redis
    ports:
      - "8080:8080"
    command: >
      wait-for postgres:5432 -- python run.py
    networks:
      cyber-net:
        aliases:
          - sqli

networks:
  cyber-net:
    external: true
```

---

### Start DVPWA

Run from inside the DVPWA main project folder.

```bash
docker compose up --build
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

## Test Case 4 — Firewall Enforcement Only

For this test case, the original Cyber-AutoAgent project must be used without any of the layered scope enforcement implementations from this repository.

Clone the original project from:

https://github.com/westonbrown/Cyber-AutoAgent

Then build the original version from inside the original Cyber-AutoAgent project folder using:

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

## Test Case 5 — Full Layered Enforcement

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

## AWS Bedrock Configuration

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
| Test Cases 1–3 | macOS |
| Test Cases 4–5 | Linux |

---

## Evaluation Test Cases

The evaluation of the framework consists of five separate test cases:

| Test Case | Purpose |
|---|---|
| Test Case 1 | Baseline system using only prompt-based enforcement |
| Test Case 2 | Endpoints scope enforcement evaluation |
| Test Case 3 | Domains/subdomains scope enforcement evaluation |
| Test Case 4 | Firewall enforcement evaluation |
| Test Case 5 | Full layered scope enforcement evaluation |

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

- Prompt-only enforcement is unreliable
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

