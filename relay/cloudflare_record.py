import json
import urllib.request

HOST = "rendezvous.metaspn.network"
IP = "5.161.247.95"
ZONE = "metaspn.network"

def token():
    for line in open("/root/.cf_env", encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("Cloudflare token not found")

def request(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request("https://api.cloudflare.com/client/v4" + path, data=data, method=method, headers={"Authorization": "Bearer " + token(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.status, json.loads(response.read().decode())

status, zones = request("GET", "/zones?name=" + ZONE)
assert status == 200 and zones.get("success") and zones["result"], zones
zone_id = zones["result"][0]["id"]
status, existing = request("GET", f"/zones/{zone_id}/dns_records?type=A&name={HOST}")
assert status == 200 and existing.get("success"), existing
record = {"type": "A", "name": HOST, "content": IP, "ttl": 120, "proxied": False}
if existing["result"]:
    record_id = existing["result"][0]["id"]
    status, result = request("PUT", f"/zones/{zone_id}/dns_records/{record_id}", record)
    action = "updated"
else:
    status, result = request("POST", f"/zones/{zone_id}/dns_records", record)
    action = "created"
assert status in (200, 201) and result.get("success"), result
read_status, readback = request("GET", f"/zones/{zone_id}/dns_records?type=A&name={HOST}")
assert read_status == 200 and readback.get("success") and readback["result"], readback
item = readback["result"][0]
assert item["name"] == HOST and item["content"] == IP and item["proxied"] is False
print(json.dumps({"action": action, "name": item["name"], "content": item["content"], "proxied": item["proxied"], "ttl": item["ttl"]}, sort_keys=True))
