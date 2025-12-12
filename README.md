# Ethereum Validator Exit Script

This script allows you to batch exit Ethereum validators using `ethdo`.

## Prerequisites

1.  **Python 3**: Ensure Python 3 is installed.
2.  **Poetry**: Ensure Poetry is installed for dependency management.
3.  **Dependencies**: Install required Python packages using Poetry:
    ```bash
    poetry install
    ```
4.  **ethdo**: Ensure `ethdo` is installed and available in your path.
5.  **env file** (only for YAML mode): Create a file named `.env` in the same directory as the script. This file should export the `MNEMONIC` variable required by `ethdo`.
    ```bash
    # Example .env file content
    export MNEMONIC="your mnemonic phrase here"
    ```
    **Note:** This is not required when using `--priv-keys-file` mode.

## Usage

The script supports two modes of operation:

### Mode 1: Using a YAML file with public keys

Run the script using `poetry run` with the path to your YAML file containing the validator keys:

```bash
poetry run python exit_validators.py --file validators.yaml
```

### Mode 2: Using a YAML file with private keys

Run the script using `poetry run` with the path to your YAML file containing private keys:

```bash
poetry run python exit_validators.py --priv-keys-file private_keys.txt
```

**Note:** You must specify either `--file` or `--priv-keys-file`, but not both.

### Options

*   `--file`: Path to the YAML file with validator keys. Required if `--priv-keys-file` is not specified.
*   `--priv-keys-file`: Path to the YAML file containing private keys (multiple documents). Required if `--file` is not specified. When using this mode:
    *   The `--env-file` and `--operator` flags are ignored
    *   The `--resume-from` flag is not supported (use `--start-index` instead)
    *   Status checking is skipped after exit commands
*   `--operator`: (Optional) Name of the operator to process keys for. If provided, only keys under this operator will be processed. Only applies to `--file` mode.
*   `--offline-prep-file`: (Optional) Path to `offline-preparation.json` to map pubkeys to validator indices. If provided, the script will use indices for exit commands. Only applies to `--file` mode.
*   `--env-file`: (Optional) Path to the environment file containing `MNEMONIC`. Defaults to `./.env`. Only applies to `--file` mode.
*   `--start-index`: (Optional) Index of the first key to process (0-based). Useful for batching.
*   `--limit`: (Optional) Maximum number of keys to process in this run. Useful for batching.
*   `--timeout`: (Optional) Timeout for the `ethdo` command (e.g., "40s", "2m"). Defaults to "40s".
*   `--no-wait`: (Optional) Skip waiting for and checking validator status after exit command.
*   `--sleep`: (Optional) Sleep time in seconds between keys. Defaults to 1.0s.
*   `--connection`: (Optional) Beacon node URL. Defaults to `https://lh-ne-gno-mainnet-shared-1-1.eu-central-5.gateway.fm`.
*   `--resume-from`: (Optional) Public key to resume processing from. The script will skip all keys before this one. Only applies to `--file` mode.

### Resuming

If the script is interrupted (Ctrl+C), it will print the last processed key.

**For YAML file mode (`--file`)**: You can resume from a specific public key using the `--resume-from` flag:

```bash
poetry run python exit_validators.py --file validators.yaml --resume-from 0xa159...
```

**For private keys mode (`--priv-keys-file`)**: You can resume from a specific index using the `--start-index` flag:

```bash
poetry run python exit_validators.py --priv-keys-file private_keys.txt --start-index 5
```

## YAML File Format

The YAML file should follow this structure:

```yaml
operators:
  - name: batch-1
    keys:
      - "0xa159..."
      - "0x8efe..."
```

## Private Keys File Format

The private keys file should be a YAML file containing multiple documents, each with a `privateKey` field:

```yaml
---
privateKey: 0x1234567890abcdef...
---
privateKey: 0xfedcba0987654321...
```

Each validator is represented as a separate YAML document (separated by `---`), with the private key specified in the `privateKey` field. The private key can be provided with or without quotes.
