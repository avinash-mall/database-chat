#!/bin/bash
# LDAP User Setup Script
# This script initializes the LDAP server with users and groups from ldap_setup.ldif
# Run this after starting the containers with: docker-compose up -d

set -e

LDAP_CONTAINER="ldap"
LDAP_ADMIN_DN="cn=admin,dc=vanna,dc=ai"
LDAP_ADMIN_PASSWORD="${LDAP_ADMIN_PASSWORD:-Vanna123}"
LDIF_FILE="ldap_setup.ldif"
MAX_RETRIES=30
RETRY_DELAY=2

echo "==================================================="
echo "LDAP User Setup Script"
echo "==================================================="

# Wait for LDAP container to be ready
echo "Waiting for LDAP container to be ready..."
for i in $(seq 1 $MAX_RETRIES); do
    if docker exec $LDAP_CONTAINER ldapsearch -x -H ldap://localhost -b "dc=vanna,dc=ai" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(objectClass=*)" > /dev/null 2>&1; then
        echo "LDAP server is ready!"
        break
    fi
    if [ $i -eq $MAX_RETRIES ]; then
        echo "ERROR: LDAP server did not become ready in time"
        exit 1
    fi
    echo "  Attempt $i/$MAX_RETRIES - waiting ${RETRY_DELAY}s..."
    sleep $RETRY_DELAY
done

# Check if users already exist
echo "Checking if users already exist..."
if docker exec $LDAP_CONTAINER ldapsearch -x -H ldap://localhost -b "dc=vanna,dc=ai" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(cn=avinash)" 2>/dev/null | grep -q "cn: avinash"; then
    echo "Users already exist in LDAP. Skipping import."
    echo "To re-import, first delete existing entries or recreate volumes with: docker-compose down -v"
    exit 0
fi

# Copy LDIF file to container
echo "Copying $LDIF_FILE to container..."
docker cp "$LDIF_FILE" "$LDAP_CONTAINER:/tmp/ldap_setup.ldif"

# Import LDIF
echo "Importing LDAP entries..."
docker exec $LDAP_CONTAINER ldapadd -x -H ldap://localhost -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" -f /tmp/ldap_setup.ldif

echo ""
echo "==================================================="
echo "LDAP setup complete!"
echo "==================================================="
echo ""
echo "Users created:"
docker exec $LDAP_CONTAINER ldapsearch -x -H ldap://localhost -b "ou=users,dc=vanna,dc=ai" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(objectClass=inetOrgPerson)" cn mail 2>/dev/null | grep -E "^(dn:|cn:|mail:)" || echo "  (none found)"
echo ""
echo "Groups created:"
docker exec $LDAP_CONTAINER ldapsearch -x -H ldap://localhost -b "ou=groups,dc=vanna,dc=ai" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(objectClass=groupOfNames)" cn 2>/dev/null | grep -E "^(dn:|cn:)" || echo "  (none found)"
