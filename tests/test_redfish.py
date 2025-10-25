import subprocess
import pytest
import requests
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def session():
    s = requests.Session()

    s.headers.update({
        "User-Agent": "pytest-redfish/1.0",
        "Accept": "application/json"
    })

    def log_request(response, *args, **kwargs):
        logger.info(f"Request: {response.request.method} {response.request.url}")
        logger.info(f"Request headers: {response.request.headers}")
        if response.request.body:
            logger.info(f"Request body: {response.request.body}")
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {response.headers}")

    s.hooks['response'] = [log_request]

    yield s
    s.close()

@pytest.fixture
def base_url():
    return "https://localhost:2443"

@pytest.fixture
def credentials():
    return {"UserName": "root", "Password": "0penBmc"}

@pytest.fixture
def token(session, base_url, credentials):
    url = f"{base_url}/redfish/v1/SessionService/Sessions"
    headers = {"Content-Type": "application/json"}
    try:
        response = session.post(url, json=credentials, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        token = response.headers.get("X-Auth-Token")
        if not token:
            pytest.fail("Failed to get auth token")
        logger.info("Authentication successful, token acquired")
        return token
    except requests.RequestException as e:
        logger.error(f"Authentication request failed: {e}")
        pytest.fail(f"Authentication request failed: {e}")

def test_redfish_authentication(session, base_url, credentials):
    url = f"{base_url}/redfish/v1/SessionService/Sessions"
    headers = {"Content-Type": "application/json"}
    try:
        response = session.post(url, json=credentials, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        assert response.status_code in (200, 201), f"Unexpected status code: {response.status_code}"
        assert "X-Auth-Token" in response.headers, "No X-Auth-Token found in response headers"
        token = response.headers["X-Auth-Token"]
        assert token, "X-Auth-Token is empty"
        logger.info("Redfish authentication test passed")
    except requests.RequestException as e:
        logger.error(f"Redfish authentication request failed: {e}")
        pytest.fail(f"Redfish authentication request failed: {e}")

def test_get_system_info(session, base_url, token):
    url = f"{base_url}/redfish/v1/Systems/system"
    headers = {"X-Auth-Token": token}
    try:
        response = session.get(url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        assert response.status_code in (200, 201), f"Unexpected status code: {response.status_code}"
        data = response.json()
        assert "Status" in data, "No 'Status' field in response JSON"
        assert "PowerState" in data, "No 'PowerState' field in response JSON"
        logger.info("System info test passed")
    except requests.RequestException as e:
        logger.error(f"System info request failed: {e}")
        pytest.fail(f"System info request failed: {e}")

def test_power_on_off(session, base_url, token):
    reset_url = f"{base_url}/redfish/v1/Systems/system/Actions/ComputerSystem.Reset"
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }
    payload = {"ResetType": "On"}
    try:
        response = session.post(reset_url, json=payload, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        logger.info(f"Power reset command sent, status code: {response.status_code}")
        assert response.status_code in (202, 204), f"Unexpected status code: {response.status_code}"
    except requests.RequestException as e:
        logger.error(f"Power reset request failed: {e}")
        pytest.fail(f"Power reset request failed: {e}")

    status_url = f"{base_url}/redfish/v1/Systems/system"
    powerstate = None
    timeout = 30
    interval = 3

    start = time.time()
    while time.time() - start < timeout:
        try:
            status_response = session.get(status_url, headers={"X-Auth-Token": token}, verify=False, timeout=10)
            status_response.raise_for_status()
            data = status_response.json()
            powerstate = data.get("PowerState")
            logger.info(f"Current PowerState: {powerstate}")
            if powerstate == "On":
                break
        except requests.RequestException as e:
            logger.warning(f"Failed to get PowerState, retrying... {e}")
        time.sleep(interval)

    assert powerstate == "On", f"PowerState did not become 'On' within timeout, last value: {powerstate}"

def test_cpu_temperature(session, base_url, token):
    sensors_url = f"{base_url}/redfish/v1/Chassis/chassis/Sensors"
    headers = {"X-Auth-Token": token}
    try:
        response = session.get(sensors_url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        data = response.json()
        sensors = data.get('Members', [])
        cpu_temp = None
        for sensor in sensors:
            sensor_resp = session.get(sensor["@odata.id"], headers=headers, verify=False, timeout=5)
            sensor_resp.raise_for_status()
            sensor_data = sensor_resp.json()
            name = sensor_data.get("Name", "")
            if "CPU Temperature" in name or "Processor Temperature" in name:
                cpu_temp = sensor_data.get("ReadingCelsius")
                break

        if cpu_temp is None:
            logger.info("CPU temperature sensor not found, test considered successful")
            return
        else:
            assert 20 <= cpu_temp <= 85, f"CPU temperature out of normal range: {cpu_temp}°C"
        logger.info("CPU temperature test passed")
    except requests.RequestException as e:
        logger.error(f"CPU temperature request failed: {e}")
        pytest.fail(f"CPU temperature request failed: {e}")

def get_ipmi_cpu_temp():
    try:
        result = subprocess.run(["ipmitool", "sensor", "get", "CPU Temp"], capture_output=True, text=True, timeout=10)
        for line in result.stdout.splitlines():
            if "Sensor Reading" in line:
                parts = line.split(":")
                temp_str = parts[1].strip().split()[0]
                return float(temp_str)
    except Exception as e:
        pytest.fail(f"IPMI command failed: {e}")
    return None

def test_cpu_sensor_alignment(session, base_url, token):
    headers = {"X-Auth-Token": token}
    try:
        response = session.get(f"{base_url}/redfish/v1/Chassis/chassis/Sensors", headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        data = response.json()
        sensors = data.get('Members', [])

        cpu_temp_redfish = None
        for sensor in sensors:
            sensor_resp = session.get(sensor["@odata.id"], headers=headers, verify=False, timeout=5)
            sensor_resp.raise_for_status()
            sensor_data = sensor_resp.json()
            name = sensor_data.get("Name", "")
            if "CPU Temperature" in name or "Processor Temperature" in name:
                cpu_temp_redfish = sensor_data.get("ReadingCelsius")
                break

        ipmi_cpu_temp = get_ipmi_cpu_temp()

        if cpu_temp_redfish is None and ipmi_cpu_temp is None:
            logger.info("CPU temperature sensors not found in both Redfish and IPMI; test considered successful")
            return

        assert cpu_temp_redfish is not None, "CPU Temperature sensor not found in Redfish"
        assert ipmi_cpu_temp is not None, "CPU Temperature sensor not found in IPMI"

        tolerance = 5.0
        diff = abs(cpu_temp_redfish - ipmi_cpu_temp)

        assert diff <= tolerance, f"CPU temperature difference too large: Redfish={cpu_temp_redfish}, IPMI={ipmi_cpu_temp}"
        logger.info("CPU sensor alignment test passed")
    except requests.RequestException as e:
        logger.error(f"CPU sensor alignment request failed: {e}")
        pytest.fail(f"CPU sensor alignment request failed: {e}")
