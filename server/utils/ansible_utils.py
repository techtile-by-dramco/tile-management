import os
import shutil
import ansible_runner
import json
from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager
from ansible.vars.manager import VariableManager


# Disable noisy Ansible warnings (safe subset)
def disable_ansible_warnings():
    os.environ["ANSIBLE_INVENTORY_UNPARSED_WARNING"] = "False"
    os.environ["ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED"] = "False"
    os.environ["ANSIBLE_DEPRECATION_WARNINGS"] = "False"
    os.environ["ANSIBLE_INVALID_TASK_ATTRIBUTE_FAILED"] = "False"
    os.environ["ANSIBLE_HOSTS_WARNING"] = "False"


def get_target_hosts(inventory_path, limit=None, suppress_warnings=True):
    """
    Returns a list of ansible.inventory.host.Host objects targeted
    by an inventory (optionally filtered by limit/group/hostname).

    Args:
        inventory_path (str): path to hosts.yaml
        limit (str): host/group pattern ("A05", "edge-nodes", etc.)
        suppress_warnings (bool): disable warnings automatically

    Returns:
        list[Host]: result of InventoryManager.get_hosts()
    """

    if suppress_warnings:
        disable_ansible_warnings()

    loader = DataLoader()
    inventory = InventoryManager(loader=loader, sources=[inventory_path])
    variable_manager = VariableManager(loader=loader, inventory=inventory)

    if limit:
        inventory.subset(limit)

    return inventory.get_hosts()

def run_playbook(project_dir, playbook_path, inventory_path, extra_vars=None,
                 hosts=None, mute_output=False, cleanup=True):
    """
    Wrapper to run an Ansible playbook using ansible-runner.

    Args:
        project_dir (str): Base directory for ansible-runner
        playbook_path (str): Path to playbook, relative or absolute
        inventory_path (str): Path to inventory file
        extra_vars (dict or str): Extra variables for the playbook
        hosts (str): Limit to specific hosts
        mute_output (bool): If True, do not print task stdout
    Returns:
        ansible_runner.Runner: The runner object
    Raises:
        RuntimeError: if the playbook returns a non-zero return code
    """
    # Normalize extra_vars
    if extra_vars is None:
        extra_vars = {}
    elif isinstance(extra_vars, str):
        try:
            extra_vars = json.loads(extra_vars)
        except json.JSONDecodeError:
            raise ValueError("extra_vars string must be valid JSON")

    try:
        r = ansible_runner.run(
            private_data_dir=project_dir,
            playbook=playbook_path,
            inventory=inventory_path,
            extravars=extra_vars,
            limit=hosts
        )

        if not mute_output:
            print("Status:", r.status)
            print("Return code:", r.rc)
            for event in r.events:
                if 'stdout' in event:
                    print(event['stdout'])

        if r.rc != 0:
            raise RuntimeError(f"Ansible playbook failed with return code {r.rc}")

    except FileNotFoundError as e:
        print(f"File not found: {e}")
        raise
    except RuntimeError as e:
        print(f"Runtime error: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise
    finally:
        if cleanup:
            # cleanup directories created by ansible-runner
            shutil.rmtree(os.path.join(project_dir, "artifacts"), ignore_errors=True)
            shutil.rmtree(os.path.join(project_dir, "env"), ignore_errors=True)

        return r