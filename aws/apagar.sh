#!/usr/bin/env bash
# Sesion 13 · Apagar y borrar TODO lo que crea desplegar_mcp.sh y comprobar que queda a cero. Ejecutar en CloudShell.
set -uo pipefail
ID=$(aws ec2 describe-instances --filters Name=tag:Name,Values=s13-mcp Name=instance-state-name,Values=pending,running,stopping,stopped \
  --query 'Reservations[].Instances[].InstanceId' --output text)
if [ -n "$ID" ]; then
  aws ec2 terminate-instances --instance-ids $ID > /dev/null
  aws ec2 wait instance-terminated --instance-ids $ID && echo "Instancia terminada (su disco se borra con ella)"
fi
SG=$(aws ec2 describe-security-groups --filters Name=group-name,Values=s13-mcp --query 'SecurityGroups[0].GroupId' --output text)
[ "$SG" != "None" ] && aws ec2 delete-security-group --group-id "$SG" && echo "Security group borrado"
aws ec2 delete-key-pair --key-name s13-clave 2>/dev/null && rm -f ~/s13-clave.pem && echo "Par de claves borrado"
echo "---- Comprobacion: todo a 0 ----"
echo "Instancias no terminadas: $(aws ec2 describe-instances --filters Name=instance-state-name,Values=pending,running,stopping,stopped --query 'length(Reservations[].Instances[])' --output text)"
echo "Discos EBS:               $(aws ec2 describe-volumes --query 'length(Volumes)' --output text)"
echo "IPs elasticas:            $(aws ec2 describe-addresses --query 'length(Addresses)' --output text)"
