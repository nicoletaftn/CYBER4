#!/bin/bash
set -e

AGENT="cyber-agent-original"
CHAIN="AGENT-FW"

# Internal containers the AI IS allowed to access
TARGETS=("proxy")

# AWS services required for Bedrock
AWS_HOSTS=(
  "bedrock-runtime.us-east-1.amazonaws.com"
  "bedrock.us-east-1.amazonaws.com"
  "sts.amazonaws.com"
)

echo "[+] Getting AI container IP..."
AGENT_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$AGENT")

echo "[+] AI IP: $AGENT_IP"

# --------------------------------------------------
# Create/reset dedicated firewall chain
# --------------------------------------------------
sudo iptables -N $CHAIN 2>/dev/null || true
sudo iptables -F $CHAIN

# Remove old jump rule if already exists
sudo iptables -D DOCKER-USER -s "$AGENT_IP" -j $CHAIN 2>/dev/null || true

# Attach the firewall EARLY in Docker chain
sudo iptables -I DOCKER-USER 1 \
  -s "$AGENT_IP" \
  -j $CHAIN

# --------------------------------------------------
# 1. Allow established traffic
# --------------------------------------------------
sudo iptables -A $CHAIN \
  -m conntrack --ctstate ESTABLISHED,RELATED \
  -j ACCEPT

# --------------------------------------------------
# 2. Allow ONLY approved internal containers
# --------------------------------------------------
for TARGET in "${TARGETS[@]}"; do

  TARGET_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$TARGET")

  echo "  Allowing internal container: $TARGET ($TARGET_IP)"

  sudo iptables -A $CHAIN \
    -d "$TARGET_IP" \
    -j ACCEPT

done

# --------------------------------------------------
# 3. Allow DNS
# --------------------------------------------------
sudo iptables -A $CHAIN \
  -p udp --dport 53 \
  -j ACCEPT

sudo iptables -A $CHAIN \
  -p tcp --dport 53 \
  -j ACCEPT

# --------------------------------------------------
# 4. Allow ONLY AWS Bedrock HTTPS endpoints
# --------------------------------------------------
for HOST in "${AWS_HOSTS[@]}"; do

  echo "  Resolving AWS endpoint: $HOST"

  IPS=$(dig +short "$HOST" | grep -E '^[0-9.]+$' || true)

  for IP in $IPS; do

    echo "    Allowing AWS IP: $IP"

    sudo iptables -A $CHAIN \
      -d "$IP" \
      -p tcp --dport 443 \
      -j ACCEPT

  done
done

# --------------------------------------------------
# 5. Optional AWS metadata endpoint
# --------------------------------------------------
sudo iptables -A $CHAIN \
  -d 169.254.169.254 \
  -j ACCEPT

# --------------------------------------------------
# 6. DROP everything else
# --------------------------------------------------
sudo iptables -A $CHAIN -j DROP

echo
echo "[✓] Firewall applied successfully"
echo

echo "[+] DOCKER-USER chain"
sudo iptables -L DOCKER-USER -n --line-numbers

echo
echo "[+] AGENT-FW chain"
sudo iptables -L $CHAIN -v -n --line-numbers
