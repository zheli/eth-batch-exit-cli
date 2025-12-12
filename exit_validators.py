import yaml
import argparse
import subprocess
import sys
import time
import requests
import signal
import os
import json

try:
    from py_ecc.bls import G2ProofOfPossession as bls
except ImportError:
    bls = None

# Global variable to track the current key being processed
current_key = None
current_index = 0
is_private_key_mode = False

def signal_handler(sig, frame):
    """Handles Ctrl+C interrupt to print the current key."""
    if is_private_key_mode:
        print(f"\n\n[!] Interrupted by user.")
        print(f"[!] Last processed private key index: {current_index}")
        print(f"[!] To resume, run the script with: --start-index {current_index}")
    elif current_key:
        print(f"\n\n[!] Interrupted by user.")
        print(f"[!] Last processed (or in-progress) key: {current_key}")
        print(f"[!] To resume, run the script with: --resume-from {current_key}")
    else:
        print("\n[!] Interrupted before processing any keys.")
    sys.exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

def load_keys(yaml_file, operator_name=None):
    """Loads validator keys from a YAML file, optionally filtering by operator."""
    try:
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error reading YAML file: {e}")
        sys.exit(1)
    
    keys = []
    if not data or 'operators' not in data:
        print("Invalid YAML format: 'operators' key missing.")
        return keys

    found_operator = False
    for operator in data.get('operators', []):
        # If an operator name is specified, skip others
        if operator_name and operator.get('name') != operator_name:
            continue
            
        if operator_name:
            found_operator = True
            
        # Handle potential missing 'keys' list or malformed entries
        op_keys = operator.get('keys', [])
        if op_keys:
            keys.extend(op_keys)
    
    if operator_name and not found_operator:
        print(f"Warning: Operator '{operator_name}' not found in YAML file.")
    
    return keys

def load_private_keys(txt_file):
    """Loads private keys from a text file with custom format."""
    keys = []
    try:
        with open(txt_file, 'r') as f:
            lines = f.readlines()
            
        # Parse the file: each validator entry is 4 lines, 3rd line has privateKey
        for line in lines:
            line = line.strip()
            if line.startswith('privateKey:'):
                # Extract the value after 'privateKey: '
                # Handle both quoted and unquoted values
                key_value = line.split(':', 1)[1].strip()
                # Remove quotes if present
                key_value = key_value.strip('"').strip("'")
                if key_value:
                    keys.append(key_value)
    except Exception as e:
        print(f"Error reading Private Key file: {e}")
        sys.exit(1)
    return keys

def derive_pubkey_from_privkey(private_key_hex):
    """Derives the BLS public key from a private key."""
    if not bls:
        return None
    
    try:
        # Remove 0x prefix if present
        if private_key_hex.startswith('0x'):
            private_key_hex = private_key_hex[2:]
        
        # Convert hex to int
        private_key_int = int(private_key_hex, 16)
        
        # Derive public key
        pubkey = bls.SkToPk(private_key_int)
        
        # Convert to hex string
        pubkey_hex = '0x' + pubkey.hex()
        
        return pubkey_hex
    except Exception as e:
        print(f"  [Warning] Could not derive pubkey from private key: {e}")
        return None

def load_validator_indices(json_file):
    """Loads validator indices from offline-preparation.json."""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        sys.exit(1)
    
    mapping = {}
    for v in data.get('validators', []):
        pubkey = v.get('pubkey')
        index = v.get('index')
        if pubkey and index is not None:
            # Normalize pubkey to lowercase for consistent lookup
            mapping[pubkey.lower()] = index
            
    return mapping

def check_status(validator_id, api_url):
    """Queries the Beacon API for the validator status."""
    # Endpoint: /eth/v1/beacon/states/{state_id}/validators/{validator_id}
    # validator_id can be pubkey or index
    # Note: If we are using private keys, we might not have the pubkey or index easily available 
    # unless we derive it, which is complex. 
    # For now, if validator_id is None (private key mode without derived ID), we skip check.
    if not validator_id:
        return None

    url = f"{api_url}/eth/v1/beacon/states/head/validators/{validator_id}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # The structure is usually data -> data -> status
            return data.get('data', {}).get('status')
        else:
            print(f"  [API Error] Status code {resp.status_code} for {validator_id}")
    except Exception as e:
        print(f"  [API Error] Exception checking status for {validator_id}: {e}")
    return None

def exit_validator(validator_ref, connection_url, env_file, timeout, is_private_key=False):
    """Runs the ethdo command to exit the validator."""
    
    if is_private_key:
        # Command for private key:
        # ethdo validator exit --connection ... --timeout ... --private-key={private_key}
        cmd = (
            f'ethdo validator exit '
            f'--connection {connection_url} '
            f'--timeout {timeout} '
            f'--private-key={validator_ref}'
        )
    else:
        # Command for mnemonic + validator ID:
        # source env && ethdo validator exit --connection ... --validator={validator_id} --mnemonic="$MNEMONIC"
        
        # Use absolute path for env file to avoid PATH search issues (sourcing /usr/bin/env)
        env_file_path = os.path.abspath(env_file)
        
        # We use /bin/bash to ensure 'source' works as expected.
        cmd = (
            f'source "{env_file_path}" && '
            f'ethdo validator exit '
            f'--connection {connection_url} '
            f'--timeout {timeout} '
            f'--validator={validator_ref} '
            f'--mnemonic="$MNEMONIC"'
        )
    
    # Hide private key in debug output
    debug_cmd = cmd
    if is_private_key:
        debug_cmd = cmd.replace(validator_ref, "******")
    
    print(f"  [Debug] Executing: {debug_cmd}")
    
    try:
        # Run the command in a shell
        # We use text=False to capture bytes, avoiding UnicodeDecodeError if the tool outputs non-UTF-8 chars
        process = subprocess.run(
            cmd, 
            shell=True, 
            executable='/bin/bash', 
            capture_output=True, 
            text=False
        )
        
        # Manually decode outputs
        process.stdout = process.stdout.decode('utf-8', errors='replace') if process.stdout else ""
        process.stderr = process.stderr.decode('utf-8', errors='replace') if process.stderr else ""
        
        return process
    except Exception as e:
        print(f"Error executing subprocess: {e}")
        return None

def main():
    global current_key, current_index, is_private_key_mode
    parser = argparse.ArgumentParser(description='Batch exit Ethereum validators.')
    parser.add_argument('--file', help='Path to the YAML file containing validator keys.')
    parser.add_argument('--priv-keys-file', help='Path to the text file containing private keys (YAML stream format).')
    parser.add_argument('--operator', help='Name of the operator to process keys for. If not specified, processes all keys.')
    parser.add_argument('--offline-prep-file', help='Path to offline-preparation.json to map pubkeys to indices.')
    parser.add_argument('--env-file', default='.env', help='Path to the environment file containing MNEMONIC. Defaults to "./.env".')
    parser.add_argument('--start-index', type=int, default=0, help='Index of the first key to process (0-based).')
    parser.add_argument('--limit', type=int, help='Maximum number of keys to process.')
    parser.add_argument('--resume-from', help='Public key to resume from. The script will start processing AT this key. (Not supported for private keys)')
    parser.add_argument('--connection', default='https://lh-ne-gno-mainnet-shared-1-1.eu-central-5.gateway.fm', help='Beacon node URL for connection.')
    parser.add_argument('--timeout', default='40s', help='Timeout for ethdo command. Defaults to "40s".')
    parser.add_argument('--no-wait', action='store_true', help='Skip waiting for and checking validator status after exit command.')
    parser.add_argument('--sleep', type=float, default=1.0, help='Sleep time in seconds between keys. Defaults to 1.0s.')
    
    args = parser.parse_args()
    
    if not args.file and not args.priv_keys_file:
        print("Error: You must specify either --file or --priv-keys-file.")
        sys.exit(1)
        
    if args.file and args.priv_keys_file:
        print("Error: Cannot specify both --file and --priv-keys-file.")
        sys.exit(1)

    # Check if 'env' file exists (only needed if NOT using private keys)
    if not args.priv_keys_file and not os.path.exists(args.env_file):
        print(f"Error: Env file '{args.env_file}' not found. Please create it or specify --env-file.")
        sys.exit(1)

    keys = []
    if args.priv_keys_file:
        print(f"Loading private keys from {args.priv_keys_file}...")
        if not os.path.exists(args.priv_keys_file):
            print(f"Error: File {args.priv_keys_file} not found.")
            sys.exit(1)
        keys = load_private_keys(args.priv_keys_file)
        is_private_key_mode = True
    else:
        print(f"Loading keys from {args.file}...")
        if not os.path.exists(args.file):
            print(f"Error: File {args.file} not found.")
            sys.exit(1)
        if args.operator:
            print(f"Filtering for operator: {args.operator}")
        keys = load_keys(args.file, args.operator)
        is_private_key_mode = False

    total_keys = len(keys)
    print(f"Found {total_keys} keys matching criteria.")

    # Load indices if provided (only for pubkey mode)
    pubkey_to_index = {}
    if not is_private_key_mode and args.offline_prep_file:
        if not os.path.exists(args.offline_prep_file):
             print(f"Error: File {args.offline_prep_file} not found.")
             sys.exit(1)
        print(f"Loading validator indices from {args.offline_prep_file}...")
        pubkey_to_index = load_validator_indices(args.offline_prep_file)
        print(f"Loaded {len(pubkey_to_index)} validator indices.")
    
    # Apply start-index
    if args.start_index > 0:
        if args.start_index >= total_keys:
            print(f"Error: Start index {args.start_index} is out of bounds (total keys: {total_keys}).")
            sys.exit(1)
        print(f"Starting from index {args.start_index}.")
        keys = keys[args.start_index:]

    # Apply limit
    if args.limit is not None:
        if args.limit <= 0:
            print("Error: Limit must be a positive integer.")
            sys.exit(1)
        print(f"Limiting execution to {args.limit} keys.")
        keys = keys[:args.limit]
        
    print(f"Will process {len(keys)} keys.")
    
    start_processing = False
    if not args.resume_from:
        start_processing = True
    
    for i, key in enumerate(keys):
        # Calculate absolute index
        current_index = args.start_index + i
        
        # Resume logic (only for pubkey mode)
        if not is_private_key_mode and not start_processing:
            if key == args.resume_from:
                start_processing = True
                print(f"Resuming from key: {key}")
            else:
                continue
        
        current_key = key
        
        validator_ref = key
        display_name = key
        derived_pubkey = None
        
        if is_private_key_mode:
            display_name = f"Private Key #{current_index}"
            validator_ref = key # key is the private key
            # Try to derive pubkey for debugging
            derived_pubkey = derive_pubkey_from_privkey(key)
            if derived_pubkey:
                display_name += f" (Pubkey: {derived_pubkey})"
        elif pubkey_to_index:
            # Normalize key from yaml
            idx = pubkey_to_index.get(key.lower())
            if idx:
                validator_ref = idx
                display_name = f"{key} (Index: {idx})"
            else:
                print(f"  Warning: Could not find index for {key}. Using pubkey.")
        
        print(f"\n[{i+1}/{len(keys)}] Processing validator: {display_name}")
        
        # 1. Exit Validator
        proc = exit_validator(validator_ref, args.connection, args.env_file, args.timeout, is_private_key=is_private_key_mode)
        
        if proc and proc.returncode == 0:
            print(f"  [Success] Exit command executed.")
            # Optional: Print stdout if needed, usually ethdo is quiet on success or prints tx hash
            if proc.stdout:
                print(f"  Output: {proc.stdout.strip()}")
        else:
            err_msg = proc.stderr.strip() if proc else "Unknown error"
            
            # Check if validator is already exiting or unknown
            if "active_exiting" in err_msg:
                print(f"  [Info] Validator is already in active_exiting state. Skipping.")
            elif "exited_unslashed" in err_msg:
                print(f"  [Info] Validator is already in exited_unslashed state. Skipping.")
            elif "unknown validator" in err_msg:
                print(f"  [Info] Unknown validator (may not exist or already exited). Skipping.")
            else:
                print(f"  [Failed] Exit command failed. Error: {err_msg}")
                print("  Exiting script immediately due to failure.")
                sys.exit(1)
        
        # 2. Check Status
        if not args.no_wait:
            if is_private_key_mode:
                # We can't check status easily with just private key unless we derive pubkey.
                # For now, we skip status check for private keys or warn user.
                print("  [Info] Skipping status check for private key mode (cannot derive pubkey easily).")
            else:
                print("  Checking status...")
                # Simple retry mechanism
                max_retries = 3
                for attempt in range(max_retries):
                    status = check_status(validator_ref, args.connection)
                    if status:
                        print(f"  Current Status: {status}")
                        if status in ['active_exiting', 'exited_unslashed', 'exited_slashed']:
                            break
                    
                    if attempt < max_retries - 1:
                        time.sleep(2) # Wait a bit before retry
        else:
            print("  Skipping status check.")
        
        # Small delay between validators to avoid rate limits if necessary
        if args.sleep > 0:
            time.sleep(args.sleep)

    print("\nAll keys processed.")

if __name__ == "__main__":
    main()
