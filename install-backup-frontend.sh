#!/bin/bash
# Install Backup Management Frontend Components
# This script copies the backup frontend components to your React app

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend/src/components"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "📦 Installing Backup Management Frontend..."
echo ""

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${YELLOW}⚠️  Frontend directory not found at $FRONTEND_DIR${NC}"
    echo "Creating directory..."
    mkdir -p "$FRONTEND_DIR"
fi

# Check if files exist
if [ ! -f "$FRONTEND_DIR/BackupDashboard.js" ]; then
    echo -e "${YELLOW}⚠️  Backup frontend components not found${NC}"
    echo "Please ensure the following files exist in frontend/src/components/:"
    echo "  - BackupDashboard.js"
    echo "  - BackupManager.js"
    echo "  - BackupSettings.js"
    exit 1
fi

# Check npm dependencies
echo "📦 Checking npm dependencies..."
cd "$SCRIPT_DIR/frontend"

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo -e "${YELLOW}⚠️  package.json not found${NC}"
    exit 1
fi

# Install dependencies if needed
DEPS_NEEDED=false

if ! npm list @mui/material > /dev/null 2>&1; then
    DEPS_NEEDED=true
fi

if ! npm list @mui/icons-material > /dev/null 2>&1; then
    DEPS_NEEDED=true
fi

if ! npm list date-fns > /dev/null 2>&1; then
    DEPS_NEEDED=true
fi

if [ "$DEPS_NEEDED" = true ]; then
    echo "📥 Installing required dependencies..."
    npm install @mui/material @mui/icons-material date-fns
else
    echo -e "${GREEN}✅ All dependencies already installed${NC}"
fi

# Create a sample route configuration
echo ""
echo "📝 To add the Backup Dashboard to your app, add this to your router:"
echo ""
cat << 'EOF'
import BackupDashboard from './components/BackupDashboard';

// In your routes:
<Route path="/admin/backups" element={<BackupDashboard />} />
EOF

echo ""
echo "📝 And add this to your navigation menu:"
echo ""
cat << 'EOF'
import { Backup as BackupIcon } from '@mui/icons-material';

// In your navigation:
<MenuItem onClick={() => navigate('/admin/backups')}>
  <ListItemIcon>
    <BackupIcon />
  </ListItemIcon>
  <ListItemText primary="Backups" />
</MenuItem>
EOF

echo ""
echo -e "${GREEN}✅ Backup Management Frontend components are ready!${NC}"
echo ""
echo "Next steps:"
echo "1. Add the route to your React router (see above)"
echo "2. Add menu item to your navigation (see above)"
echo "3. Ensure backend backup API is running at /api/backups"
echo "4. Configure rclone for cloud storage (optional)"
echo ""
echo "📚 Documentation: BACKUP_FRONTEND_GUIDE.md"
echo ""
