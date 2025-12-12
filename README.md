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
5.  **env file**: Create a file named `.env` in the same directory as the script. This file should export the `MNEMONIC` variable required by `ethdo`.
    ```bash
    # Example .env file content
    export MNEMONIC="your mnemonic phrase here"
    ```

## Usage

Run the script using `poetry run` with the path to your YAML file containing the validator keys:

```bash
poetry run python exit_validators.py --file validators.yaml
```

### Options

*   `--file`: (Required) Path to the YAML file with validator keys.
*   `--operator`: (Optional) Name of the operator to process keys for. If provided, only keys under this operator will be processed.
*   `--offline-prep-file`: (Optional) Path to `offline-preparation.json` to map pubkeys to validator indices. If provided, the script will use indices for exit commands.
*   `--env-file`: (Optional) Path to the environment file containing `MNEMONIC`. Defaults to `./.env`.
*   `--start-index`: (Optional) Index of the first key to process (0-based). Useful for batching.
*   `--limit`: (Optional) Maximum number of keys to process in this run. Useful for batching.
*   `--timeout`: (Optional) Timeout for the `ethdo` command (e.g., "40s", "2m"). Defaults to "40s".
*   `--no-wait`: (Optional) Skip waiting for and checking validator status after exit command.
*   `--sleep`: (Optional) Sleep time in seconds between keys. Defaults to 1.0s.
*   `--connection`: (Optional) Beacon node URL. Defaults to `https://lh-ne-gno-mainnet-shared-1-1.eu-central-5.gateway.fm`.
*   `--resume-from`: (Optional) Public key to resume processing from. The script will skip all keys before this one.

### Resuming

If the script is interrupted (Ctrl+C), it will print the last processed key. You can resume from that key using the `--resume-from` flag:

```bash
poetry run python exit_validators.py --file validators.yaml --resume-from 0xa159...
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
