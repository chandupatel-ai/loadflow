import requests
import json

BASE = "http://localhost:8000"

def p(label, r):
    print(f"\n--- {label} [{r.status_code}] ---")
    try:
        print(json.dumps(r.json(), indent=2)[:800])
    except Exception:
        
        print(r.text[:300])
# 1. Bootstrap a broker org + admin
r = requests.post(f"{BASE}/auth/bootstrap-org", json={
    "org_name": "Acme Brokerage", "org_type": "broker",
    "admin_email": "broker-admin@acme.com", "admin_password": "pass123", "admin_full_name": "Bea Broker"
})
p("bootstrap broker org", r)
broker_admin_token = r.json()["access_token"]
h_broker_admin = {"Authorization": f"Bearer {broker_admin_token}"}

# 2. Bootstrap a carrier org + admin
r = requests.post(f"{BASE}/auth/bootstrap-org", json={
    "org_name": "Speedy Carriers", "org_type": "carrier",
    "admin_email": "carrier-admin@speedy.com", "admin_password": "pass123", "admin_full_name": "Carl Carrier"
})
p("bootstrap carrier org", r)
carrier_admin_token = r.json()["access_token"]
h_carrier_admin = {"Authorization": f"Bearer {carrier_admin_token}"}

# 3. Broker admin creates a custom role "Dispatcher" (load.assign_carrier + rate.confirm)
r = requests.post(f"{BASE}/roles", json={
    "name": "Dispatcher", "permissions": ["load.assign_carrier", "rate.confirm", "load.update_status"]
}, headers=h_broker_admin)
p("create Dispatcher role", r)
dispatcher_role_id = r.json()["id"]

# 4. Broker admin invites staff with Dispatcher role (NOTE: no load.create!)
r = requests.post(f"{BASE}/roles/staff", json={
    "email": "dispatcher@acme.com", "password": "pass123", "full_name": "Dana Dispatcher",
    "role_id": dispatcher_role_id
}, headers=h_broker_admin)
p("invite dispatcher staff", r)

r = requests.post(f"{BASE}/auth/login", json={"email": "dispatcher@acme.com", "password": "pass123"})
dispatcher_token = r.json()["access_token"]
h_dispatcher = {"Authorization": f"Bearer {dispatcher_token}"}

# 5. TEST: dispatcher (no load.create) tries to create a load -> should be 403
r = requests.post(f"{BASE}/loads", json={
    "pickup_location": "Dallas, TX", "delivery_location": "Atlanta, GA", "commodity": "Electronics"
}, headers=h_dispatcher)
p("dispatcher tries load.create (should be 403)", r)
assert r.status_code == 403, "RBAC FAILED: dispatcher should not be able to create loads"

# 6. Broker admin (implicit full permissions) creates the load
r = requests.post(f"{BASE}/loads", json={
    "pickup_location": "Dallas, TX", "delivery_location": "Atlanta, GA", "commodity": "Electronics"
}, headers=h_broker_admin)
p("broker admin creates load", r)
load_id = r.json()["id"]

# 7. Carrier admin uploads compliance BUT with expired insurance -> should block progression
r = requests.put(f"{BASE}/compliance/me", json={
    "insurance_expiry": "2020-01-01T00:00:00", "mc_dot_authority_status": "active",
    "approved_equipment_types": ["dry_van"], "approved_commodity_types": ["general"]
}, headers=h_carrier_admin)
p("carrier sets EXPIRED compliance", r)

# 8. Dispatcher (has load.assign_carrier) assigns carrier to load -> should flag compliance
r = requests.get(f"{BASE}/dashboard/carriers", headers=h_broker_admin)
p("carrier directory", r)
carrier_org_id = r.json()[0]["org_id"]

r = requests.post(f"{BASE}/loads/{load_id}/assign-carrier", json={"carrier_org_id": carrier_org_id}, headers=h_dispatcher)
p("dispatcher assigns non-compliant carrier", r)
assert r.json()["compliance_flag"] == True, "Compliance flag should be True for expired insurance"
assert r.json()["status"] == "Posted", "Status should stay at Posted since compliance blocked progression"

# 9. TEST: object-level scoping - a shipper who ISN'T the shipper-of-record can't see the load
r = requests.post(f"{BASE}/auth/signup-shipper", json={"email": "other-shipper@x.com", "password": "pass123"})
other_shipper_token = r.json()["access_token"]
r = requests.get(f"{BASE}/loads/{load_id}", headers={"Authorization": f"Bearer {other_shipper_token}"})
p("unrelated shipper tries to view load (should be 403)", r)
assert r.status_code == 403, "RBAC FAILED: object-level scoping broken"

# 10. Fix compliance, re-assign, confirm rate, then try skipping ahead (should fail - forward-only)
r = requests.put(f"{BASE}/compliance/me", json={
    "insurance_expiry": "2030-01-01T00:00:00", "mc_dot_authority_status": "active",
    "approved_equipment_types": ["dry_van"], "approved_commodity_types": ["general"]
}, headers=h_carrier_admin)
p("carrier fixes compliance", r)

r = requests.post(f"{BASE}/loads/{load_id}/assign-carrier", json={"carrier_org_id": carrier_org_id}, headers=h_dispatcher)
p("dispatcher re-assigns compliant carrier", r)
assert r.json()["status"] == "Carrier Assigned"

r = requests.post(f"{BASE}/loads/{load_id}/rate-confirmations", json={"base_rate": 2000, "accessorials": 150}, headers=h_dispatcher)
p("dispatcher confirms rate v1", r)

r = requests.post(f"{BASE}/loads/{load_id}/status", json={"to_status": "Dispatched"}, headers=h_dispatcher)
p("try to SKIP from Carrier Assigned to Dispatched (should be 400, forward-only)", r)
assert r.status_code == 400

r = requests.post(f"{BASE}/loads/{load_id}/status", json={"to_status": "Rate Confirmed"}, headers=h_dispatcher)
p("move to Rate Confirmed (should succeed)", r)
assert r.status_code == 200

print("\n\n✅ ALL RBAC / STATE MACHINE / SCOPING TESTS PASSED")
