import json
import socket
import sys
import time

import requests


def is_port_open():
    print("\nTesting if port 5000 is open...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        result = sock.connect_ex(("127.0.0.1", 5000))
        if result == 0:
            print("Port 5000 is open")
            return True
        else:
            print(f"Port 5000 is not open (error code: {result})")
            return False
    finally:
        sock.close()


def make_request(url, method="GET", data=None):
    print(f"\nMaking {method} request to {url}")
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        else:  # POST
            response = requests.post(url, json=data, timeout=5)

        print(f"Status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response body: {response.text}")

        return response.json() if response.text else None
    except requests.exceptions.Timeout:
        print("Request timed out after 5 seconds")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None


def single_endpoint_test(url, method="GET", data=None):
    print(f"\nTesting endpoint: {url}")
    start_time = time.time()
    result = make_request(url, method, data)
    end_time = time.time()

    print(f"Request took {end_time - start_time:.2f} seconds")
    if result is not None:
        print(f"Success! Response: {json.dumps(result, indent=2)}")
        return True
    else:
        print("Failed to get response")
        return False


def test_endpoints():
    base_url = "http://127.0.0.1:5000"

    endpoints = [
        {"url": f"{base_url}/", "method": "GET"},
        {"url": f"{base_url}/api/test", "method": "GET"},
        {"url": f"{base_url}/api/strategies", "method": "GET"},
        {
            "url": f"{base_url}/api/simulate",
            "method": "POST",
            "data": {
                "strategy_type": "SPY_POWER_CASHFLOW",
                "config": {"SYMBOL": "SPY", "OPTION_TYPE": "call"},
                "start_date": "2024-01-01",
                "end_date": "2024-01-03",
                "initial_balance": 10000.0,
            },
        },
    ]

    results = []
    for endpoint in endpoints:
        success = single_endpoint_test(
            endpoint["url"],
            endpoint.get("method", "GET"),
            endpoint.get("data"),
        )
        results.append(success)

    print("\nTest Summary:")
    for endpoint, success in zip(endpoints, results):
        status = "✓ Passed" if success else "✗ Failed"
        print(f"{status} - {endpoint['method']} {endpoint['url']}")


if __name__ == "__main__":
    print("Starting connection tests...")
    print(f"Python version: {sys.version}")

    if is_port_open():
        test_endpoints()
    else:
        print("Skipping endpoint tests since port is not open")
