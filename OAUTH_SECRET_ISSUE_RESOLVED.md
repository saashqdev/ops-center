# OAuth Client Secret Issue - RESOLVED

## Summary
Authentication was failing with 401 "Invalid client credentials" errors due to wrong OAuth client secret being loaded at runtime.

## Root Cause
**Problem**: The `cloudflare_api.py` module (lines 61-68) loads `/app/.env.auth` at import time and overwrites all environment variables:

```python
env_auth_path = Path("/app/.env.auth")
if env_auth_path.exists():
    with open(env_auth_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value  # ← Overwrites docker-compose environment
```

**Issue**: The `.env.auth` file was **baked into the Docker image** at build time with old credentials. Even though:
- Host file `/home/ubuntu/Ops-Center-OSS/.env.auth` had correct secrets
- Docker-compose `env_file` directive loaded correct values
- Docker-compose `environment` section explicitly set correct values

The **container's internal `/app/.env.auth`** file had old credentials that overrode everything.

## Discovery Timeline
1. Container environment variables showed correct values when checked via `docker exec env`
2. Python process loaded wrong values (confirmed via debug logging)
3. Discovery: `cloudflare_api.py` re-parses `/app/.env.auth` at module import
4. Comparison: Host `.env.auth` vs container `/app/.env.auth` revealed mismatch
5. Container file had old credentials from image build time

## Solution Implemented

### Immediate Fix (Done)
1. Updated `/app/.env.auth` inside running container
2. Restarted container to reload environment

### Permanent Fix (Done)
Added volume mount in `docker-compose.direct.yml`:

```yaml
volumes:
  # Mount .env.auth to allow runtime updates without rebuilding image
  - ./.env.auth:/app/.env.auth:ro
```

### Benefits
- Changes to host `.env.auth` now immediately available in container
- No need to rebuild image when updating secrets
- Single source of truth: host `.env.auth` file

## Correct Secret Values
- **KEYCLOAK_CLIENT_SECRET**: `QNeBWyjw9koFASgWEYZDACELjejHCbcG`
- **OPS_CENTER_OAUTH_CLIENT_SECRET**: `QNeBWyjw9koFASgWEYZDACELjejHCbcG`
- **KEYCLOAK_ADMIN_PASSWORD**: `vz9cA8-kuX-oso3DC-w7`

## Files Modified
1. `/home/ubuntu/Ops-Center-OSS/docker-compose.direct.yml` - Added `.env.auth` volume mount
2. `/home/ubuntu/Ops-Center-OSS/.env.auth` - Already had correct values (no changes needed)

## Testing
- Container recreated with new volume mount
- Environment variables verified correct
- No authentication errors in logs
- Ready for user login testing

## Future Recommendations
1. **CONSIDER REMOVING** the `.env.auth` re-parsing code in `cloudflare_api.py` (lines 61-68) since docker-compose already handles env_file loading
2. Alternative: Make the re-parsing conditional (only if env vars not already set)
3. Document that `.env.auth` is now mounted and changes take effect on container restart

## Status
✅ **RESOLVED** - Authentication should now work correctly with the regenerated client secret.
