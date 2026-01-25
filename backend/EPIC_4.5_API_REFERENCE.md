# Epic 4.5: Organization Branding API Reference

## Overview
The Organization Branding API allows organizations to customize their branding with tier-based feature limits.

**Base URL**: `/api/v1/organizations/{org_id}/branding`

## Authentication
All endpoints require a valid session token cookie.

## Endpoints

### 1. Get Tier Limits
Get branding feature limits for the organization's subscription tier.

```http
GET /api/v1/organizations/{org_id}/branding/limits/
```

**Response Example:**
```json
{
    "tier_code": "professional",
    "max_logo_size_mb": 5.0,
    "max_assets": 10,
    "custom_colors": true,
    "custom_fonts": true,
    "custom_domain": true,
    "custom_email_branding": true,
    "remove_powered_by": false,
    "custom_login_page": true,
    "custom_css": false,
    "api_white_label": false
}
```

### 2. Create Organization Branding
Create branding configuration for an organization.

```http
POST /api/v1/organizations/{org_id}/branding/
```

**Request Body:**
```json
{
    "org_id": "my-org-123",
    "org_name": "My Organization",
    "colors": {
        "primary_color": "#3B82F6",
        "secondary_color": "#10B981",
        "accent_color": "#F59E0B",
        "text_color": "#1F2937",
        "background_color": "#FFFFFF"
    },
    "typography": {
        "font_family": "Inter",
        "heading_font": "Poppins"
    },
    "company_info": {
        "company_name": "Acme Corporation",
        "tagline": "Innovation at Scale",
        "description": "Leading provider of enterprise solutions",
        "support_email": "support@acme.com",
        "support_phone": "+1-555-0100"
    },
    "social_links": {
        "twitter_url": "https://twitter.com/acme",
        "linkedin_url": "https://linkedin.com/company/acme",
        "github_url": "https://github.com/acme",
        "discord_url": "https://discord.gg/acme"
    },
    "custom_domain": {
        "custom_domain": "app.acme.com",
        "domain_verified": false,
        "ssl_enabled": false
    },
    "email_branding": {
        "email_from_name": "Acme Support",
        "email_from_address": "noreply@acme.com",
        "email_logo_url": "/uploads/branding/acme-email-logo.png",
        "email_footer_text": "© 2026 Acme Corp. All rights reserved."
    },
    "features": {
        "custom_logo_enabled": true,
        "custom_colors_enabled": true,
        "custom_domain_enabled": true,
        "custom_email_enabled": true,
        "white_label_enabled": false
    },
    "custom_terms_text": "Custom terms and conditions...",
    "custom_privacy_text": "Custom privacy policy..."
}
```

**Response:** Returns the created branding configuration (see response schema below).

### 3. Get Organization Branding
Retrieve the branding configuration for an organization.

```http
GET /api/v1/organizations/{org_id}/branding/
```

**Response Example:**
```json
{
    "id": 1,
    "org_id": "my-org-123",
    "org_name": "My Organization",
    "tier_code": "professional",
    "logo_url": "/uploads/branding/my-org-123_logo_abc123.png",
    "logo_dark_url": "/uploads/branding/my-org-123_logo_dark_def456.png",
    "favicon_url": "/uploads/branding/my-org-123_favicon_ghi789.png",
    "background_image_url": null,
    "primary_color": "#3B82F6",
    "secondary_color": "#10B981",
    "accent_color": "#F59E0B",
    "text_color": "#1F2937",
    "background_color": "#FFFFFF",
    "font_family": "Inter",
    "heading_font": "Poppins",
    "company_name": "Acme Corporation",
    "tagline": "Innovation at Scale",
    "description": "Leading provider of enterprise solutions",
    "support_email": "support@acme.com",
    "support_phone": "+1-555-0100",
    "twitter_url": "https://twitter.com/acme",
    "linkedin_url": "https://linkedin.com/company/acme",
    "github_url": "https://github.com/acme",
    "discord_url": "https://discord.gg/acme",
    "custom_domain": "app.acme.com",
    "custom_domain_verified": true,
    "custom_domain_ssl_enabled": true,
    "custom_terms_text": "Custom terms...",
    "custom_privacy_text": "Custom privacy...",
    "email_from_name": "Acme Support",
    "email_from_address": "noreply@acme.com",
    "email_logo_url": "/uploads/branding/acme-email-logo.png",
    "email_footer_text": "© 2026 Acme Corp.",
    "custom_logo_enabled": true,
    "custom_colors_enabled": true,
    "custom_domain_enabled": true,
    "custom_email_enabled": true,
    "white_label_enabled": false,
    "created_at": "2026-01-25T20:00:00Z",
    "updated_at": "2026-01-25T21:30:00Z"
}
```

### 4. Update Organization Branding
Update specific fields in the branding configuration.

```http
PUT /api/v1/organizations/{org_id}/branding/
```

**Request Body (partial updates allowed):**
```json
{
    "colors": {
        "primary_color": "#8B5CF6"
    },
    "company_info": {
        "tagline": "Building the Future"
    }
}
```

**Response:** Returns the updated branding configuration.

### 5. Delete Organization Branding
Remove all branding configuration for an organization.

```http
DELETE /api/v1/organizations/{org_id}/branding/
```

**Response:**
```json
{
    "message": "Organization branding deleted successfully"
}
```

### 6. Upload Branding Asset
Upload a branding asset (logo, favicon, etc.).

```http
POST /api/v1/organizations/{org_id}/branding/assets/upload/
Content-Type: multipart/form-data
```

**Form Data:**
- `asset_type` (string): Type of asset - "logo", "logo_dark", "favicon", or "background"
- `file` (file): The image file to upload

**Allowed File Types:**
- image/png
- image/jpeg
- image/svg+xml
- image/webp

**Size Limits (tier-based):**
- Trial: 1MB
- Starter: 2MB
- Professional: 5MB
- Enterprise: 10MB
- VIP Founder: 10MB

**Response:**
```json
{
    "id": 1,
    "org_id": "my-org-123",
    "asset_type": "logo",
    "asset_url": "/uploads/branding/my-org-123_logo_abc123.png",
    "file_name": "company-logo.png",
    "file_size": 245760,
    "mime_type": "image/png",
    "uploaded_at": "2026-01-25T21:30:00Z"
}
```

### 7. List Branding Assets
Get all uploaded assets for an organization.

```http
GET /api/v1/organizations/{org_id}/branding/assets/
```

**Response:**
```json
[
    {
        "id": 1,
        "org_id": "my-org-123",
        "asset_type": "logo",
        "asset_url": "/uploads/branding/my-org-123_logo_abc123.png",
        "file_name": "company-logo.png",
        "file_size": 245760,
        "mime_type": "image/png",
        "uploaded_at": "2026-01-25T21:30:00Z"
    }
]
```

### 8. Delete Branding Asset
Remove a specific branding asset.

```http
DELETE /api/v1/organizations/{org_id}/branding/assets/{asset_id}/
```

**Response:**
```json
{
    "message": "Asset deleted successfully"
}
```

### 9. Get Audit Log
Retrieve branding change history for compliance.

```http
GET /api/v1/organizations/{org_id}/branding/audit-log/?limit=100
```

**Query Parameters:**
- `limit` (integer, default: 100): Maximum number of log entries to return

**Response:**
```json
[
    {
        "id": 1,
        "org_id": "my-org-123",
        "action": "create",
        "changes": {"message": "Organization branding created"},
        "performed_by": "1",
        "ip_address": null,
        "user_agent": null,
        "created_at": "2026-01-25T20:00:00Z"
    },
    {
        "id": 2,
        "org_id": "my-org-123",
        "action": "update",
        "changes": {"primary_color": "#8B5CF6", "tagline": "Building the Future"},
        "performed_by": "1",
        "ip_address": null,
        "user_agent": null,
        "created_at": "2026-01-25T21:30:00Z"
    }
]
```

## Tier-Based Limits

| Feature | Trial | Starter | Professional | Enterprise | VIP Founder |
|---------|-------|---------|--------------|------------|-------------|
| Max Logo Size | 1MB | 2MB | 5MB | 10MB | 10MB |
| Max Assets | 2 | 5 | 10 | 20 | 50 |
| Custom Colors | ❌ | ✅ | ✅ | ✅ | ✅ |
| Custom Fonts | ❌ | ❌ | ✅ | ✅ | ✅ |
| Custom Domain | ❌ | ❌ | ✅ | ✅ | ✅ |
| Email Branding | ❌ | ❌ | ✅ | ✅ | ✅ |
| Remove Powered By | ❌ | ❌ | ❌ | ✅ | ✅ |
| Custom Login Page | ❌ | ❌ | ✅ | ✅ | ✅ |
| Custom CSS | ❌ | ❌ | ❌ | ❌ | ❌ |
| API White Label | ❌ | ❌ | ❌ | ❌ | ❌ |

## Error Responses

### 400 Bad Request
```json
{
    "detail": "Invalid file type. Allowed: image/png, image/jpeg, image/svg+xml, image/webp"
}
```

### 401 Unauthorized
```json
{
    "detail": "Not authenticated"
}
```

### 404 Not Found
```json
{
    "detail": "Organization branding not found"
}
```

### 500 Internal Server Error
```json
{
    "detail": "Internal Server Error"
}
```

## Color Format
All color values must be valid 6-digit hex colors (e.g., `#3B82F6`).

## Database Schema

### organization_branding Table
Stores the main branding configuration for each organization.

### branding_assets Table
Tracks uploaded branding assets (logos, favicons, etc.).

### branding_tier_limits Table
Defines feature limits for each subscription tier.

### branding_audit_log Table
Records all branding changes for compliance and auditing.

## Example cURL Commands

```bash
# Get tier limits
curl "http://localhost:8084/api/v1/organizations/my-org/branding/limits/" \
  -H "Cookie: session_token=xyz"

# Create branding
curl -X POST "http://localhost:8084/api/v1/organizations/my-org/branding/" \
  -H "Cookie: session_token=xyz" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "my-org",
    "org_name": "My Organization",
    "colors": {"primary_color": "#3B82F6"}
  }'

# Update branding
curl -X PUT "http://localhost:8084/api/v1/organizations/my-org/branding/" \
  -H "Cookie: session_token=xyz" \
  -H "Content-Type: application/json" \
  -d '{
    "colors": {"primary_color": "#8B5CF6"}
  }'

# Upload logo
curl -X POST "http://localhost:8084/api/v1/organizations/my-org/branding/assets/upload/" \
  -H "Cookie: session_token=xyz" \
  -F "asset_type=logo" \
  -F "file=@/path/to/logo.png"
```

## Next Steps

1. **UI Implementation**: Build React component for branding management
2. **File Upload**: Implement drag-and-drop logo/favicon uploader
3. **Custom Domain**: Add DNS verification workflow
4. **Email Templates**: Apply branding to email notifications
5. **Preview Mode**: Real-time branding preview

---

**Epic 4.5 Status**: Backend API Complete ✅
**Test Coverage**: All CRUD operations passing ✅
**Database**: Schema deployed ✅
