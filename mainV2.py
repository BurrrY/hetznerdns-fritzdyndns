"""
DynDNS Service for FritzBox using Hetzner Cloud API
Endpoint: http://192.168.178.13:5000/dyndns?subdomains=<subdomains>&newip=<ipaddr>&token=<pass>
"""

from flask import Flask, request
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Hetzner Cloud API base URL
API_BASE_URL = "https://api.hetzner.cloud/v1"


def get_all_zones(token):
    """
    Get all DNS zones from Hetzner Cloud API.
    """
    logger.info("Fetching all zones...")

    try:
        response = requests.get(
            f"{API_BASE_URL}/zones",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )

        if response.status_code != 200:
            logger.error(f"Failed to get zones: HTTP {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None

        data = response.json()
        zones = data.get('zones', [])

        logger.info(f"Found {len(zones)} zones")
        for zone in zones:
            logger.debug(f"Zone: {zone['name']} (ID: {zone['id']})")

        return zones

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request failed: {str(e)}")
        return None


def find_zone_for_subdomain(zones, subdomain):
    """
    Find the zone that contains the given subdomain.
    For example, for 'drop.bury.link', it will find zone 'bury.link'.
    Returns: (zone, record_name)
    """
    logger.info(f"Finding zone for subdomain: {subdomain}")

    if not zones:
        return None, None

    # Split subdomain into parts
    parts = subdomain.split('.')

    # Try to match zone from most specific to least specific
    # e.g., for 'a.b.example.com', try 'b.example.com', then 'example.com'
    for i in range(len(parts)):
        potential_zone = '.'.join(parts[i:])
        for zone in zones:
            if zone['name'] == potential_zone:
                record_name = '.'.join(parts[:i]) if i > 0 else '@'
                logger.info(f"Found zone: {zone['name']} (ID: {zone['id']}), record_name: {record_name}")
                return zone, record_name

    logger.warning(f"No zone found for subdomain: {subdomain}")
    return None, None


def get_zone_records(zone_id, token):
    """
    Get all DNS records for a specific zone.
    """
    logger.info(f"Fetching records for zone ID: {zone_id}")

    try:
        response = requests.get(
            f"{API_BASE_URL}/zones/{zone_id}/rrsets",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )

        if response.status_code != 200:
            logger.error(f"Failed to get records: HTTP {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None

        data = response.json()
        records = data.get('rrsets', [])

        logger.info(f"Found {len(records)} records in zone")
        return records

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request failed: {str(e)}")
        return None


def find_a_record(records, record_name):
    """
    Find an A record with the given name.
    Special case: '*' (wildcard) is stored as '@' in the API.
    """
    if not records:
        return None

    # Special case: wildcard '*' is stored as '@' in the API
    search_name =  record_name

    for record in records:
        if record.get('name') == search_name and record.get('type') == 'A':
            logger.info(f"Found existing A record: {record_name} -> {record.get('value')}")
            return record

    logger.info(f"No existing A record found for: {record_name}")
    return None


def create_record(zone_id, record_name, ip, ttl, token):

    logger.info(f"Creating A record: {record_name} -> {ip}")

    # Special case: wildcard '*' must be sent as '@' to the API
    api_record_name = record_name

    try:
        response = requests.post(
            f"{API_BASE_URL}/zones/{zone_id}/rrsets",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "records": [
                    {
                        "value": ip
                    }
                ],
                "name": api_record_name,
                "type": "A",
                "ttl": ttl
            }
        )

        if response.status_code == 201:
            logger.info(f"Successfully created record: {record_name}")
            return True
        else:
            logger.error(f"Failed to create record: HTTP {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request failed: {str(e)}")
        return False


def update_record(zone_id, record, token):
    """
    Update an existing DNS A record.
    Special case: '*' (wildcard) must be sent as '@' to the API.
    """
    logger.info(f"Updating A record ID {record['id']}: {record['name']} -> {record['records'][0]['value']}")

    # Special case: wildcard '*' must be sent as '@' to the API
    api_record_name = record['name']

    try:
        response = requests.post(
            f"{API_BASE_URL}/zones/{zone_id}/rrsets/{api_record_name}/A/actions/set_records",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"records": record['records']}
        )

        if response.status_code == 201:
            logger.info(f"Successfully updated record: {record['name']}")
            return True
        else:
            logger.error(f"Failed to update record: HTTP {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request failed: {str(e)}")
        return False


def update_dns_record(zones, subdomain, new_ip, token):
    """
    Update or create an A record for the given subdomain with the new IP.
    """
    logger.info(f"Processing subdomain: {subdomain}")

    # Find the appropriate zone
    zone, record_name = find_zone_for_subdomain(zones, subdomain)

    if zone is None:
        logger.error(f"Cannot update {subdomain}: No matching zone found")
        return False

    zone_id = zone['id']

    # Get all records for this zone
    records = get_zone_records(zone_id, token)

    if records is None:
        logger.error(f"Failed to fetch records for zone {zone['name']}")
        return False

    # Find existing A record
    existing_record = find_a_record(records, record_name)

    # TTL of 300 seconds (5 minutes) for dynamic DNS
    ttl = 300

    if existing_record:
        # Check if IP is already correct
        records = existing_record.get('records', [])
        if len(records) == 1 and records[0].get('value') == new_ip:
            logger.info(f"Record {subdomain} already has IP {new_ip}, no update needed")
            return True

        existing_record['records'][0]['value'] = new_ip
        existing_record['protection']['change'] = True
        # Update existing record
        return update_record(
            zone_id,
            existing_record,
            token
        )
    else:
        # Create new record
        return create_record(
            zone_id,
            record_name,
            new_ip,
            ttl,
            token
        )


@app.route('/dyndns', methods=['GET'])
def dyndns_update():
    """
    FritzBox DynDNS endpoint.
    Expected parameters:
    - subdomains: comma-separated list of subdomains to update
    - newip: the new IP address from FritzBox
    - token: Hetzner API token
    """
    # Get parameters
    subdomains_param = request.args.get('subdomains')
    new_ip = request.args.get('newip')
    token = request.args.get('token')

    # Validate parameters
    if not subdomains_param:
        logger.error("Missing 'subdomains' parameter")
        return "Error: Missing 'subdomains' parameter", 400

    if not new_ip:
        logger.error("Missing 'newip' parameter")
        return "Error: Missing 'newip' parameter", 400

    if not token:
        logger.error("Missing 'token' parameter")
        return "Error: Missing 'token' parameter", 400

    logger.info(f"DynDNS update request - IP: {new_ip}, Subdomains: {subdomains_param}")

    # Parse comma-separated subdomains
    subdomains = [s.strip() for s in subdomains_param.split(',') if s.strip()]

    if not subdomains:
        logger.error("No valid subdomains provided")
        return "Error: No valid subdomains provided", 400

    # Get all zones once (to avoid repeated API calls)
    zones = get_all_zones(token)

    if zones is None:
        logger.error("Failed to fetch zones from Hetzner API")
        return "Error: Failed to authenticate or fetch zones", 401

    # Update each subdomain
    results = []
    for subdomain in subdomains:
        success = update_dns_record(zones, subdomain, new_ip, token)
        results.append({
            'subdomain': subdomain,
            'success': success
        })

    # Check if all updates succeeded
    all_success = all(r['success'] for r in results)

    if all_success:
        logger.info("All DNS records updated successfully")
        return "OK: All DNS records updated successfully", 200
    else:
        failed = [r['subdomain'] for r in results if not r['success']]
        logger.warning(f"Some updates failed: {failed}")
        return f"Partial success: Failed to update {', '.join(failed)}", 207


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    """
    return "OK", 200


def main():
    """
    Start the Flask server.
    """
    logger.info("Starting DynDNS server on 0.0.0.0:5000")
    logger.info("Endpoint: /dyndns?zone=<username>&newip=<ipaddr>&subdomain=<domain>&token=<pass>")
    app.run(host="0.0.0.0", port=5000)


if __name__ == '__main__':
    main()