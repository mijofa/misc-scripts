#!/bin/bash

# This just puts a menu item in for each VScode workspace I use regularly.

# This is kinda silly to have a script, but I expect to rerun it every now and then.
# And I'll kinda want it on multiple different systems, so script was the quickest answer.
# NOTE: I considered having a separate git repo of .code-workspace files, but I still couldn't get that into my menu


# ~/vcs/{abrahall.id.au,cyber/prisonpc,PI/ichris-sync,PI/ansible-playbooks,misc-scripts}
for project_path in "$@" ; do
    project="${project_path/\/home\/mike\/vcs\//}"
    project_shortcut="code-${project//\//_}.desktop"
    if [ -f "${project_path}/.vscode/mijofa-shortcut-icon.png" ] ; then
        project_icon="${project_path}/.vscode/mijofa-shortcut-icon.png"
    else
        project_icon="vscode"
    fi
    sed -e '/^\[Desktop Action/,$d' \
        -e '/^Actions=/d' \
        -e '/^GenericName=/d' \
        -e '/^Categories=/ s/=.*$/=X-mijofa-code-projects;/' \
        -e '/^Name=/ s/=.*$/='"${project//\//\\/}"'/' \
        -e '/^Comment=/ s/=.*$/='"${project_path//\//\\/}"'/' \
        -e '/^Exec=/ s/%F/"'"${project_path//\//\\/}"'"/g' \
        -e '/^Icon=/ s/=.*$/='"${project_icon//\//\\/}"'/' \
        /usr/share/applications/code.desktop >~/.local/share/applications/"$project_shortcut"
done

printf >~/.local/share/desktop-directories/code-projects.directory '%s\n' \
       "[Desktop Entry]" \
       "Version=1.0" \
       "Type=Directory" \
       "Name=Code projects" \
       "Icon=vscode" \

printf >~/.config/menus/applications-merged/code-projects.menu '%s\n'  \
       "<Menu>" \
       "    <Name>Applications</Name>" \
       "    <Menu>" \
       "        <Name>Code Projects</Name>" \
       "        <Directory>code-projects.directory</Directory>" \
       "        <Include>" \
       "            <Category>X-mijofa-code-projects</Category>" \
       "        </Include>" \
       "    </Menu>" \
       "</Menu>"
