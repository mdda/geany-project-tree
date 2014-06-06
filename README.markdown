# Project-Tree plugin for Geany

## Motivation

This plugin gives Geany sidebar a 'project-tree' view of your files.  

The project-tree view can be different from how they're laid out on disk : 
Personally, I prefer to keep a 'thematic' structure to a project - 
at the very least, it can be handy to keep files in an order not dictated by their sequence alphabetically.

![Screenshot](./img/geany-project-tree_screenshot-1.png?raw=true)

The plugin is also designed to keep separate state for different repository folders, with the state being stored locally, 
so that one can put it into version control, for instance.

I had previously contributed to a separate sidebar widget/app for SciTE, called SciTEpm (which is why this plugin
contains a loader for the xml files that SciTEpm saves).

## File Layout

For each actual project that you have (as distinct from what Geany calls projects), typically one would 
launch Geany from its root directory (where the .git directory is stored, for instance).

The project-tree plugin's files are stored in a '.geany' directory (it will confirm before writing anything to disk) :

 * .geany
   + project-tree-layout.ini
   + session.ini
   + [OPTIONAL: project-tree-layout_devel.ini]
   + [OPTIONAL: session_default.ini ] 
 * ... the rest of your files ...

Of these files:
 * 'project-tree-layout.ini' will be relatively static (once the project is in mainenance mode), so could well be put into version control
 * 'session.ini' is just a dump of open files, so is probably not sensible to put into version control
 * 'project-tree-layout_devel.ini' is read-only, for testing
 * 'session_default.ini' is used if session.ini doesn't exist - so could be used as a starter set of relevant files for newcomers
 
 
## Usage

The project-tree sidebar can be right-clicked, to get to :
 * 'Add this file', which adds the currently open document to the project-tree
 * 'Add group', which adds a new group heading
 * and other functions that should be obvious
 
It also allows drag-and-drop internally, so you can organize files & groups to your heart's content.

At the top of the sidebar is a quick menu, allowing you to Load/Save the Project-Tree layout, and current open files.

When loaded for the first time in a directory, it's immediately ready to use : It will ask whether to create the 
'.geany' folder if you need to save the tree or the session.


## Commentary

### INI files

The .ini files are standard form, while enabling the storing of the full tree structure.


### GTK drag-and-drop

This works within the Project-Tree sidepanel.  And it was really painful to do - 
particularly since (for instance) some drops should be disallowed :

 * anything onto a file
 * anything onto itself, or a descendent, etc

Hopefully, someone that gets caught with the same problems can avoid *days* of Googling, and have a look at the code here.


### Automagic Menubar Creation

The module contains code to 'instantly' create menus (and menubars) based upon annotated function names.  This looks 
rather kludgy, I know, but makes it very quick to add new features, etc.

For example, the following creates a File dropdown (ordering can be changed numerically) with a 'Load Project Tree' entry 
that's auto-linked to the function that requires it:

```python
def _menubar_0_File_0_Load_Project_Tree(self, data):
    """
    Loads the project tree specified by the user in the message box
    """
    print "_menubar_0_File_0_Load_Project_Tree"
    project_tree_layout_ini = self._prompt_for_ini_file("*tree*.ini")
    if project_tree_layout_ini:
        self._change_base_directory(os.path.dirname(os.path.dirname(project_tree_layout_ini))) # strip off .geany/XYZ.ini
        self._load_project_tree(self.treeview.get_model(), project_tree_layout_ini)
    return True
```

Annotation style for menubar callbacks :
 *  _menubar _{order#} _{heading-label} _{submenu-order#} _{submenu-label}

### Automagic Menu Creation

Similarly, for the right-click menu popup :

```python
def _popup_0_SEPARATOR(self, data): pass
    
def _popup_1_Add_Group(self, data):
    print "_popup_1_Add_Group"
    dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
                                    gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL,  "Add Group :")
    
    return True
```

Annotation style for menu callbacks (normally for popups) :
 * _popup _{order#} _{heading-label}
    


## Dependencies

This plugin depends on GeanyPy. See GeanyPy's documentation/website for information on installation.

On Fedora, for instance, installing GeanyPy is as simple as : 

``` bash
# yum install geany-plugins-geanypy python-devel

```

 
## Installation

First you need to know where GeanyPy stores its plugin directory - and that the path has been set up.

As a local user on Fedora, this is done simply by running ```geany```, and making sure that the geanypy plugin is installed.

Then :

```bash
cd {project-tree directory inside this repository}
ln -s `pwd`/project-tree ~/.config/geany/plugins/geanypy/plugins/
```

