# DynDNS for Hetzner Cloud

A Dynamic DNS service built with Flask that updates DNS A-records at Hetzner Cloud. Designed to work with FritzBox routers but compatible with any DynDNS client.

## Features

- Updates DNS A-records automatically when your IP changes
- Supports multiple subdomains in a single request
- Intelligent zone discovery - automatically finds the right zone for each subdomain
- Handles both subdomains and apex records
- Comprehensive logging for troubleshooting
- Proper error handling with meaningful HTTP status codes
- Health check endpoint for monitoring

## Requirements

- Python 3.7+
- Hetzner Cloud account with DNS zones configured
- Hetzner Cloud API token

## Installation

### Using Docker (Recommended)

```bash
docker pull ghcr.io/YOUR_USERNAME/dyndns:latest

docker run -d \
  -p 5000:5000 \
  --name dyndns \
  ghcr.io/YOUR_USERNAME/dyndns:latest
```

### Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/dynDNS.git
cd dynDNS
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. Run the application:
```bash
python mainV2.py
```

The server will start on `0.0.0.0:5000`.

## Usage

### API Endpoint

```
GET /dyndns?subdomains=<subdomain1>,<subdomain2>&newip=<ip>&token=<api_token>
```

**Parameters:**
- `subdomains`: Comma-separated list of fully qualified domain names (e.g., `home.example.com,vpn.example.com`)
- `newip`: The new IP address to set
- `token`: Your Hetzner Cloud API token

**Example:**
```bash
curl "http://localhost:5000/dyndns?subdomains=home.example.com&newip=203.0.113.42&token=YOUR_API_TOKEN"
```

### Health Check

```
GET /health
```

Returns `OK` if the service is running.

## FritzBox Configuration

1. Log into your FritzBox web interface
2. Go to **Internet → Permit Access → DynDNS**
3. Configure with the following settings:
   - **Update URL:** `http://YOUR_SERVER_IP:5000/dyndns?subdomains=<username>&newip=<ipaddr>&token=<pass>`
   - **Domain Name:** Your domain (e.g., `home.example.com`)
   - **Username:** Your comma-separated list of subdomains
   - **Password:** Your Hetzner Cloud API token

## Configuration

### Hetzner Cloud API Token

Generate an API token in the Hetzner Cloud Console:
1. Go to **Security → API Tokens**
2. Click **Generate API Token**
3. Give it a name and select **Read & Write** permissions
4. Copy the token (you won't be able to see it again)

### DNS Zones

Make sure your DNS zones are configured in Hetzner Cloud:
1. Go to **DNS** in the Hetzner Cloud Console
2. Add your domains as DNS zones
3. Update your domain registrar to use Hetzner's nameservers

## How It Works

1. FritzBox (or another DynDNS client) sends a request with the new IP address
2. The service fetches all DNS zones from Hetzner Cloud
3. For each subdomain:
   - Finds the matching DNS zone (e.g., `example.com` for `home.example.com`)
   - Determines the record name (e.g., `home` for subdomain, `@` for apex)
   - Checks if an A record already exists
   - Creates a new record or updates the existing one with the new IP
4. Returns success or error status

## Development

### Project Structure

- `mainV2.py` - Current implementation using Hetzner Cloud API
- `main.py` - Legacy implementation using old Hetzner DNS API
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container build configuration
- `CLAUDE.md` - Documentation for Claude Code

### Running Tests

Currently, there are no automated tests in this project.

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Migration from Old DNS API

If you're migrating from the old Hetzner DNS Console:

- API tokens are different between the two systems
- Zones must be migrated in the Hetzner Console first
- Update your endpoint URL to use `mainV2.py`
- Change authentication from `Auth-API-Token` to `Bearer` token

## Troubleshooting

### Check the logs

The application logs all operations at INFO level. Look for error messages that indicate:
- Authentication failures (HTTP 401)
- Zone not found
- API rate limiting
- Network issues

### Common Issues

**"No zone found for subdomain"**
- Make sure the DNS zone exists in Hetzner Cloud
- Check that the domain name is correctly formatted

**"Failed to authenticate"**
- Verify your API token is correct and has Read & Write permissions
- Check that you're using a Cloud API token, not a DNS API token

**FritzBox shows "Update failed"**
- Check the logs on the DynDNS server
- Verify the server is reachable from FritzBox
- Ensure the token is passed correctly in the URL

## License

This project is provided as-is without any specific license.

## Acknowledgments

- Built for use with [Hetzner Cloud](https://www.hetzner.com/cloud)
- Designed for [FritzBox](https://en.avm.de/products/fritzbox/) routers
