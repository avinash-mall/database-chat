#!/bin/bash
# LDAP User Setup Script
# This script initializes/updates the LDAP server with users and groups from ldap_setup.ldif
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

# Copy LDIF file to container
echo "Copying $LDIF_FILE to container..."
docker cp "$LDIF_FILE" "$LDAP_CONTAINER:/tmp/ldap_setup.ldif"

echo ""
echo "Processing LDAP entries..."
echo "---------------------------------------------------"

# Initialize counters
ADDED=0
SKIPPED=0
FAILED=0

# Process LDIF file - split by blank lines and process each entry
current_entry=""
current_dn=""

process_entry() {
    local entry="$1"
    local dn="$2"
    
    if [ -z "$dn" ]; then
        return
    fi
    
    # Check if entry already exists
    if docker exec $LDAP_CONTAINER ldapsearch -x -H ldap://localhost -b "$dn" -s base -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(objectClass=*)" 2>/dev/null | grep -q "^dn: "; then
        echo "  [SKIP] $dn (already exists)"
        SKIPPED=$((SKIPPED + 1))
    else
        # Create temp file with entry
        echo "$entry" > /tmp/single_entry.ldif
        docker cp /tmp/single_entry.ldif "$LDAP_CONTAINER:/tmp/single_entry.ldif"
        rm -f /tmp/single_entry.ldif
        
        # Try to add the entry
        if docker exec $LDAP_CONTAINER ldapadd -x -H ldap://localhost -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" -f /tmp/single_entry.ldif 2>/dev/null; then
            echo "  [ADD]  $dn"
            ADDED=$((ADDED + 1))
        else
            echo "  [FAIL] $dn"
            FAILED=$((FAILED + 1))
        fi
    fi
}

# Read LDIF file and process entries
while IFS= read -r line || [ -n "$line" ]; do
    if [ -z "$line" ]; then
        # Blank line - process accumulated entry
        if [ -n "$current_entry" ]; then
            process_entry "$current_entry" "$current_dn"
            current_entry=""
            current_dn=""
        fi
    else
        # Accumulate entry
        if [ -z "$current_entry" ]; then
            current_entry="$line"
        else
            current_entry="$current_entry
$line"
        fi
        # Extract DN
        if echo "$line" | grep -q "^dn: "; then
            current_dn=$(echo "$line" | sed 's/^dn: //')
        fi
    fi
done < "$LDIF_FILE"

# Process last entry if file doesn't end with blank line
if [ -n "$current_entry" ]; then
    process_entry "$current_entry" "$current_dn"
fi

echo "---------------------------------------------------"
echo ""
echo "==================================================="
echo "LDAP setup complete!"
echo "==================================================="
echo ""
echo "Summary: Added=$ADDED, Skipped=$SKIPPED, Failed=$FAILED"
echo ""
echo "Current users:"
docker exec $LDAP_CONTAINER ldapsearch -x -H ldap://localhost -b "ou=users,dc=vanna,dc=ai" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(objectClass=inetOrgPerson)" cn mail 2>/dev/null | grep -E "^(dn:|cn:|mail:)" || echo "  (none found)"
echo ""
echo "Current groups:"
docker exec $LDAP_CONTAINER ldapsearch -x -H ldap://localhost -b "ou=groups,dc=vanna,dc=ai" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(objectClass=groupOfNames)" cn 2>/dev/null | grep -E "^(dn:|cn:)" || echo "  (none found)"
