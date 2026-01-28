#!/bin/bash
#
# Quick Test User Creation - Common Scenarios
#
# Provides quick commands for common test user scenarios
#

# Keycloak admin password (must match the actual Keycloak server password)
KEYCLOAK_ADMIN_PASSWORD="vz9cA8-kuX-oso3DC-w7"

echo "=========================================="
echo "  Quick Test User Creation"
echo "=========================================="
echo ""
echo "Choose a scenario:"
echo ""
echo "1. Basic trial user (default)"
echo "2. Professional user"
echo "3. Admin user (professional tier)"
echo "4. Multiple test users (5)"
echo "5. Custom user (manual input)"
echo ""
read -p "Select option (1-5): " choice

case $choice in
    1)
        echo "Creating basic trial user..."
        docker exec -e KEYCLOAK_ADMIN_PASSWORD="$KEYCLOAK_ADMIN_PASSWORD" ops-center-direct python3 /app/create_test_user.py \
            --email "trial-$(date +%Y%m%d-%H%M%S)@example.com" \
            --username "trial-user-$(date +%Y%m%d-%H%M%S)" \
            --tier trial
        ;;
    2)
        echo "Creating professional user..."
        docker exec -e KEYCLOAK_ADMIN_PASSWORD="$KEYCLOAK_ADMIN_PASSWORD" ops-center-direct python3 /app/create_test_user.py \
            --email "pro-$(date +%Y%m%d-%H%M%S)@example.com" \
            --username "pro-user-$(date +%Y%m%d-%H%M%S)" \
            --tier professional
        ;;
    3)
        echo "Creating admin user..."
        docker exec -e KEYCLOAK_ADMIN_PASSWORD="$KEYCLOAK_ADMIN_PASSWORD" ops-center-direct python3 /app/create_test_user.py \
            --email "admin-$(date +%Y%m%d-%H%M%S)@example.com" \
            --username "admin-$(date +%Y%m%d-%H%M%S)" \
            --tier professional \
            --role admin
        ;;
    4)
        echo "Creating 5 test users..."
        for i in {1..5}; do
            echo "Creating user $i/5..."
            docker exec -e KEYCLOAK_ADMIN_PASSWORD="$KEYCLOAK_ADMIN_PASSWORD" ops-center-direct python3 /app/create_test_user.py \
                --email "test${i}-$(date +%Y%m%d-%H%M%S)@example.com" \
                --username "testuser${i}-$(date +%Y%m%d-%H%M%S)" \
                --tier trial
            sleep 1
        done
        echo "All 5 users created!"
        ;;
    5)
        read -p "Email: " email
        read -p "Username: " username
        read -p "First Name: " firstname
        read -p "Last Name: " lastname
        read -p "Password [TestPassword123!]: " password
        password=${password:-TestPassword123!}
        read -p "Tier (trial/starter/professional/enterprise) [trial]: " tier
        tier=${tier:-trial}
        read -p "Role (optional, e.g., admin): " role
        
        CMD="docker exec -e KEYCLOAK_ADMIN_PASSWORD=\"$KEYCLOAK_ADMIN_PASSWORD\" ops-center-direct python3 /app/create_test_user.py --email \"$email\" --username \"$username\" --first-name \"$firstname\" --last-name \"$lastname\" --password \"$password\" --tier \"$tier\""
        
        if [ -n "$role" ]; then
            CMD="$CMD --role \"$role\""
        fi
        
        echo "Creating custom user..."
        eval $CMD
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Access user management at:"
echo "https://kubeworkz.io/admin/system/users"
echo "=========================================="
