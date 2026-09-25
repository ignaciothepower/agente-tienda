#!/usr/bin/env bash
# Sesion 13 · Paso 7: desplegar en AWS la pieza que usa el agente, el servidor MCP de la tienda (S12).
# Se ejecuta en AWS CloudShell (usa tu sesion de la consola: sin access keys). Es el desplegar.sh de la S12
# recortado: sin S3 ni presupuesto (la alerta de 5 USD de la S12 sigue activa).
# El "cerebro" (LangGraph + llama3.1) se queda en tu portatil: una t3.micro (1 GB de RAM) no puede con un LLM.
set -euo pipefail

PORTATIL_IP=${PORTATIL_IP:?"Pon la IP publica de tu portatil: export PORTATIL_IP=... (curl -s checkip.amazonaws.com EN TU PORTATIL)"}
MIIP=$(curl -s https://checkip.amazonaws.com)   # IP de esta CloudShell (para el SSH)

VPC=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
# Cortafuegos: SSH solo desde CloudShell y el 8000 solo desde tu portatil. Nada de 0.0.0.0/0
SG=$(aws ec2 create-security-group --group-name s13-mcp --vpc-id "$VPC" \
  --description "S13: SSH desde CloudShell, 8000 desde el portatil" --query GroupId --output text)
aws ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port 22   --cidr "$MIIP/32" > /dev/null
aws ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port 8000 --cidr "$PORTATIL_IP/32" > /dev/null
aws ec2 create-key-pair --key-name s13-clave --query KeyMaterial --output text > ~/s13-clave.pem
chmod 400 ~/s13-clave.pem
AMI=$(aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
  --query Parameter.Value --output text)
ID=$(aws ec2 run-instances --image-id "$AMI" --instance-type t3.micro --key-name s13-clave \
  --security-group-ids "$SG" --metadata-options HttpTokens=required \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=s13-mcp}]' \
  --query 'Instances[0].InstanceId' --output text)
aws ec2 wait instance-running --instance-ids "$ID"
IP=$(aws ec2 describe-instances --instance-ids "$ID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "Instancia $ID en $IP"
sleep 20
S="ssh -i $HOME/s13-clave.pem -o StrictHostKeyChecking=accept-new ec2-user@$IP"

# La misma imagen Docker de la S12, construida desde el repositorio publico del servidor
$S "sudo dnf install -y -q docker git && sudo systemctl enable --now docker"
$S "git clone -q https://github.com/ignaciothepower/mcp-server-ci.git && cd mcp-server-ci && sudo docker build -q -t mcp-server ."
$S "sudo docker run -d --name mcp --restart unless-stopped -p 8000:8000 mcp-server && sleep 4 && curl -s localhost:8000/salud"
echo
echo "EN TU PORTATIL, en el .env del agente:  MCP_URL=http://$IP:8000"
echo "Cuando acabes:  bash aws/apagar.sh"
