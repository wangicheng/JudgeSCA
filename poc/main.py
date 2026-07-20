import argparse
from client import OJClient
from extractor import SideChannelExtractor

def main():
    parser = argparse.ArgumentParser(description="JudgeSCA: Online Judge Side-Channel Extractor PoC")
    parser.add_argument("--url", required=True, help="Base URL of the target Online Judge (e.g., http://localhost)")
    parser.add_argument("--user", required=True, help="Username for authentication")
    parser.add_argument("--password", required=True, help="Password for authentication")
    parser.add_argument("--problem", required=True, help="Target Problem ID to extract test cases from")
    
    args = parser.parse_args()
    
    print(f"[*] Initializing JudgeSCA for {args.url}")
    
    client = OJClient(args.url)
    if not client.login(args.user, args.password):
        print("[-] Exiting due to login failure.")
        return
        
    extractor = SideChannelExtractor(client, args.problem)
    
    # The linear regression calibration will be called automatically before extract_all
    extractor.extract_all()

if __name__ == "__main__":
    main()
