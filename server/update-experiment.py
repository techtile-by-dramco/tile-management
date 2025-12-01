import os
from utils.ansible_utils import get_target_hosts, run_playbook

# Some basic config
hosts = 'A06' # hosts (clients) to set up

# Rest of the configuration we obtain automatically
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)

#print("Project dir: ", project_dir) // should point to tile-management repo clone
print("Working on tile(s):", hosts)

#run_playbook(project_dir, playbook_path, inventory_path, extra_vars=None,
  #               hosts=None, mute_output=False, cleanup=True)