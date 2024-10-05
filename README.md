Role Name
=========

This Ansible Role will install packages and configure settings targeting DevSecOps activities.
Settings can be customized through variables. Take a look in the existing standards defined in
"defaults/main.yml" and overridden them in a Playbook.

This role will:
- Ensure desired repositories
- Ensure desired packages
- Customize VIM
- Populate some useful scripts

To install this role:  
```$ ansible-galaxy role install marcusburghardt.devsecops```

Requirements
------------

- python3

Role Variables
--------------

You can customize your environment in a very simple and centralized way editing some variables in:
- defaults/main.yml

In some rare cases, you may change some configuration to reflect your local environment in:
- vars/*.yml

Observe that the above variables could be set in your Playbook too, which is much more elegant. ;)  
Take a look in the Example Playbook section.

Dependencies
------------

None.

Example Playbook
----------------

This Playbook will prepare everything with the right variables.
For this example, lets call this Playbook file as "ansible_devsecops.yml":

---
- hosts: linux
  vars:
    - git_tasks:
      - { enabled: true,  name: 'configure_repos' }
      - { enabled: true,  name: 'install_packages' }
      - { enabled: true,  name: 'configure_vim' }
      - { enabled: true,  name: 'populate_scripts' }
  roles:
    - marcusburghardt.devsecops

Considering the inventory file is in the same folder and is called "hosts",
you can now run this command:  
```$ ansible-playbook -K -i hosts ansible_devsecops.yml```

License
-------

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Author Information
------------------

Marcus Burghardt
- https://buymeacoffee.com/marcusburghardt
- https://github.com/marcusburghardt/
- https://www.linkedin.com/in/marcusburghardt/
