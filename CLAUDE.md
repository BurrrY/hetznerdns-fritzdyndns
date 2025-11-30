# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Dynamic DNS (DynDNS) service built with Flask that updates DNS A-records at Hetzner. The service exposes an HTTP endpoint that allows routers (specifically FritzBox) to update DNS records with their current IP address.

**Two versions exist:**
- `main.py` - Legacy version using old Hetzner DNS API (`dns.hetzner.com`)
- `mainV2.py` - **Current version** using new Hetzner Cloud API (`api.hetzner.cloud`)

## Key Architecture

### Single-File Application
Both applications are contained in single Python files with no modular structure. All functions are defined at module level with Flask as the web framework.

### API Integration

#### mainV2.py (Current - Hetzner Cloud API)
The application interacts with Hetzner Cloud API v1 endpoints at `https://api.hetzner.cloud/v1`:
- `GET /zones` - Retrieve all DNS zones
- `GET /zones/{id}/records` - Retrieve DNS records for a specific zone
- `POST /zones/{id}/records` - Create new DNS records
- `PUT /zones/{id}/records/{record_id}` - Update existing DNS records

Authentication uses `Authorization: Bearer {token}` header for all API requests.

#### main.py (Legacy - Old DNS API)
The old version interacts with Hetzner DNS API at `https://dns.hetzner.com/api/v1`:
- `GET /api/v1/zones` - Retrieve DNS zones
- `GET /api/v1/records` - Retrieve DNS records for a zone
- `POST /api/v1/records` - Create new DNS records
- `PUT /api/v1/records/{RecordID}` - Update existing DNS records

Authentication uses the `Auth-API-Token` header.

### Zone and Record Discovery (mainV2.py)
The new version implements intelligent zone discovery:
1. Fetches all zones once at the start of each request to minimize API calls
2. For each subdomain (e.g., `drop.bury.link`), searches through zones from most specific to least specific
3. Automatically determines the record name by stripping the zone suffix
   - `drop.bury.link` with zone `bury.link` → record name `drop`
   - `bury.link` with zone `bury.link` → record name `@` (apex record)

### Global State Management (main.py - Legacy)
The old version uses a global variable `all_records` to cache DNS records during a single update operation. This cache is cleared after each `/dyndns` request completes.

### Domain Name Processing (main.py - Legacy)
The old version handles two domain formats:
1. **Subdomain records** (e.g., `drop.bury.link`) - stored with subdomain name only
2. **Apex/A-records** (e.g., `bury.link`) - stored as `@` in Hetzner DNS

The `clean_domain` logic in `run_update()` normalizes domain names by:
- Stripping the zone suffix from fully qualified domain names
- Converting 2-part domains (apex records) to `@`

### Multi-Domain Updates
**mainV2.py:** Accepts comma-separated subdomains via the `subdomains` parameter. Each subdomain is processed independently.

**main.py (Legacy):** Supports comma-separated values in both `subdomain` and `zone` parameters. The `zone` parameter can encode extra subdomains after the first comma (e.g., `zone=bury.link,drop.bury.link`).

## Development Commands

### Setup
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Run Application

**Current version (mainV2.py):**
```bash
python mainV2.py
```

**Legacy version (main.py):**
```bash
python main.py
```

Both servers start on `0.0.0.0:5000`.

### API Endpoints

**mainV2.py (Current):**
```
GET /dyndns?subdomains=<subdomain1>,<subdomain2>&newip=<ip>&token=<api_token>
GET /health  # Health check endpoint
```

**main.py (Legacy):**
```
GET /dyndns?zone=<domain>&newip=<ip>&subdomain=<subdomain1>,<subdomain2>&token=<api_token>
```

### FritzBox Configuration
Configure FritzBox DynDNS settings to call:
```
http://192.168.178.13:5000/dyndns?subdomains=<username>&newip=<ipaddr>&token=<pass>
```
Where `<username>` is replaced with comma-separated subdomains by FritzBox.

### Docker

**Build Docker image:**
```bash
docker build -t dyndns .
```

**Run Docker container:**
```bash
docker run -d -p 5000:5000 --name dyndns dyndns
```

The Dockerfile copies `mainV2.py` as `main.py` and runs it on container startup.

### CI/CD

**GitHub Actions workflow** (`.github/workflows/docker-build.yml`):
- Triggers on push to main/master branch, tags, or manual workflow dispatch
- Builds multi-platform Docker images (linux/amd64, linux/arm64)
- Pushes to GitHub Container Registry (ghcr.io)
- Automatic tagging:
  - `latest` for default branch
  - Semantic version tags for releases (e.g., `v1.2.3`, `1.2`, `1`)
  - Branch names for branch pushes
  - PR numbers for pull requests
  - Git SHA for all builds

## Important Notes

### Hardcoded Credentials (main.py only)
The legacy `main.py` contains hardcoded API token and test data in the `main()` function (lines 200-204). This should never be committed to version control. **mainV2.py** does not contain hardcoded credentials.

### No Tests
There are no unit tests or test infrastructure in this codebase.

### Error Handling

**mainV2.py (Current):**
- Implements comprehensive logging at INFO level for all operations
- Returns proper HTTP status codes (200 for success, 400 for bad requests, 401 for auth failures, 207 for partial success)
- Validates all required parameters before processing
- Checks if IP already matches before making unnecessary API calls
- Returns detailed error messages to the caller

**main.py (Legacy):**
- Catches `requests.exceptions.RequestException` but does not propagate errors to the API caller
- All requests return "update done" regardless of success or failure
- Check console output for actual HTTP status codes and error messages

### Migration Notes
When migrating from old DNS Console to new Cloud API:
- API tokens are different between the two systems
- The old `dns.hetzner.com` API zones cannot be managed via the new Cloud API
- Zones must be migrated in the Hetzner Console before using mainV2.py
- The DNS API beta ended November 10, 2025; no new zones can be created in the old system
