import requests
import json
import time

class OJClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36'
        })
        self.csrf_token = None

    def _get_csrf_token(self):
        """Fetch CSRF token from the platform."""
        try:
            # First request to an API endpoint to get the initial cookies (including csrf token)
            # We use /api/profile instead of / to avoid frontend browser-support checks.
            r = self.session.get(f"{self.base_url}/api/profile")
            
            # The CSRF token is usually in the cookies for QDUOJ
            if 'csrftoken' in self.session.cookies:
                self.csrf_token = self.session.cookies['csrftoken']
                self.session.headers.update({'X-CSRFToken': self.csrf_token})
                return True
            return False
        except Exception as e:
            print(f"Error fetching CSRF token: {e}")
            return False

    def login(self, username, password):
        """Login to QDUOJ."""
        print(f"[*] Attempting to login as '{username}'...")
        if not self._get_csrf_token():
            print("[-] Failed to get initial CSRF token.")

        login_url = f"{self.base_url}/api/login"
        payload = {
            "username": username,
            "password": password
        }
        
        try:
            r = self.session.post(login_url, json=payload)
            r.raise_for_status()
            data = r.json()
            
            if data.get("error") is None:
                print(f"[+] Successfully logged in as {username}.")
                # Update CSRF token after login since it might change
                if 'csrftoken' in self.session.cookies:
                    self.csrf_token = self.session.cookies['csrftoken']
                    self.session.headers.update({'X-CSRFToken': self.csrf_token})
                return True
            else:
                print(f"[-] Login failed: {data.get('data')}")
                return False
        except Exception as e:
            print(f"[-] Error during login: {e}")
            return False

    def submit(self, problem_id, code, language="C++"):
        """Submit code to a problem."""
        language_mapping = {
            "C": "C",
            "C++": "C++",
            "Java": "Java",
            "Python2": "Python2",
            "Python3": "Python3",
        }
        
        submit_url = f"{self.base_url}/api/submission"
        payload = {
            "problem_id": problem_id,
            "language": language_mapping.get(language, "C++"),
            "code": code
        }

        while True:
            try:
                r = self.session.post(submit_url, json=payload)
                r.raise_for_status()
                data = r.json()
                
                if data.get("error") is None:
                    submission_id = data["data"]["submission_id"]
                    return submission_id
                else:
                    error_msg = data.get("error")
                    data_msg = data.get("data")
                    if "Please wait" in str(data_msg):
                        print(f"[!] Rate limited: {data_msg}. Waiting 2 seconds...")
                        time.sleep(2)
                        continue
                    else:
                        print(f"[-] Submission failed: {error_msg} - {data_msg}")
                        return None
            except Exception as e:
                print(f"[-] Error during submission: {e}")
                return None

    def get_result(self, submission_id, timeout=30):
        """Poll for the result of a submission."""
        result_url = f"{self.base_url}/api/submission?id={submission_id}"
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                r = self.session.get(result_url)
                r.raise_for_status()
                data = r.json()
                
                if data.get("error") is None:
                    sub_data = data["data"]
                    status = sub_data.get("result")
                    
                    # In QDUOJ: 6 = Pending, 7 = Judging, 9 = Pending Rejudge
                    if status not in [6, 7, 9]:
                        return sub_data
                else:
                    print(f"[-] Error fetching result: {data.get('data')}")
                    return None
            except Exception as e:
                print(f"[-] Error polling result: {e}")
                
            time.sleep(1) # Poll every second
            
        print("[-] Timeout waiting for submission result.")
        return None
