import os, sys

import gtk, glib, gobject
import geany

import ConfigParser
import re

class ProjectTree(geany.Plugin):
    __plugin_name__ = "Project Tree"
    __plugin_version__ = "0.1"
    __plugin_description__ = "(Yet Another) Alternative to treeview and project view"
    __plugin_author__ = "Martin Andrews <martin@redcatlabs.com>"

    config_base_directory = None  # This will be guessed initially
    config_base_directory_is_guess = True
    config_sub_directory  = ".geany"
    
    config_tree_layout_file           = "project-tree-layout.ini"
    config_tree_layout_file_readonly  = "project-tree-layout_devel.ini"
    config_session_file               = "session.ini"
    config_session_file_initial       = "session_default.ini"
    
    widget_destroy_stack = []
    
    def __init__(self):
        self.clipboard=gtk.clipboard_get()

        if True:  ## Set up the pop-up menu
            self.menu_popup = _create_menu_from_annotated_callbacks(self, '_popup')
            self.widget_destroy_stack.extend([self.menu_popup, ])

        if True:  ## Set up the side-bar
            #setup treeview and treestore model
            treemodel = gtk.TreeStore(*TreeViewRow.TYPES)
            treeview = gtk.TreeView(treemodel)
            treeview.get_selection().set_mode(gtk.SELECTION_SINGLE)
            treeview.set_headers_visible(False)
            
            ## http://python.6.x6.nabble.com/Treeview-drag-drop-chap14-td1939736.html
            targets = [
                ('GTK_TREE_MODEL_ROW', gtk.TARGET_SAME_WIDGET, 0),
                #('GEANY-TAB', gtk.TARGET_SAME_APP, 1),
            ]

            ## http://www.pygtk.org/pygtk2tutorial/sec-TreeViewDragAndDrop.html
            #treeview.enable_model_drag_source(gtk.gdk.BUTTON1_MASK, targets, gtk.gdk.ACTION_MOVE)
            treeview.drag_source_set(gtk.gdk.BUTTON1_MASK, targets, gtk.gdk.ACTION_MOVE)
            treeview.connect("drag_data_get",      self._drag_data_get)
            #treeview.connect('drag_data_delete',   self._drag_data_delete)
            
            #treeview.enable_model_drag_dest(                        targets, gtk.gdk.ACTION_MOVE) #ACTION_DEFAULT
            treeview.drag_dest_set(gtk.DEST_DEFAULT_HIGHLIGHT | gtk.DEST_DEFAULT_DROP, targets, gtk.gdk.ACTION_MOVE) 
            treeview.connect('drag_motion',        self._drag_motion)
            #treeview.connect('drag_drop',          self._drag_drop)
            treeview.connect("drag_data_received", self._drag_data_received)
            
            ## Clicking actions
            treeview.connect('row-activated', self.treeview_row_activated)
            #self.treeview.connect('select-cursor-row', self.treeview_select_cursor_row)
            #self.treeview.connect("row-expanded", self.treeview_row_expanded)
            
            ## Popup actions
            treeview.connect('button_press_event', self.treeview_button_press_event)
            
            text_renderer= gtk.CellRendererText()
            column0=gtk.TreeViewColumn("Tree Layout Options", text_renderer, text=0)

            treeview.append_column(column0)
            treeview.show()
            
            #put treeview in a scrolled window so we can move up and down with a scrollbar
            self.scrolledwindow=gtk.ScrolledWindow()
            self.scrolledwindow.add(treeview)
            self.scrolledwindow.show()
            
            self.treeview = treeview

        if True:
            self.menu_bar = _create_menubar_from_annotated_callbacks(class_with_menu_callbacks = self) 
            
        if True:
            box = gtk.VBox(False, 0)
            box.pack_start(self.menu_bar, expand=False, fill=False, padding=2)
            box.pack_end(self.scrolledwindow, expand=True, fill=True, padding=2)
            box.show()
            
            label = gtk.Label("ProjectTree")
            geany.main_widgets.sidebar_notebook.append_page(box, label)

            # keep track of widgets to destroy in plugin_cleanup()
            self.widget_destroy_stack.extend([box, label, ])


        if True:  ## Load in configuration
            ## Apparently, get_current document not loaded at the time plugin is starting
            #doc=geany.document.get_current()
            #if doc is not None:
            #    print("geany launch document: %s" % (doc.real_path, ))
            
            ## Apparently, this isn't necessarily a sensible value
            #print("geany.general_prefs.default_open_path=%s" % (geany.general_prefs.default_open_path, ))
            
            ## Attempt to see .geany directory here
            if self.config_base_directory_is_guess:
                #print("os.getcwd()=%s" % (os.getcwd(),))  # For geany opened from StartMenu == ~ (home directory)
                directory = os.getcwd()
                self.config_base_directory = directory
                
                if self._geany_subdir_exists():
                    print("Base directory FOUND (is_guess=FALSE) = %s" % (self.config_base_directory,))
                    self.config_base_directory_is_guess = False 
                else:
                    # Let's do this LAZILY : We'll set everything up upon save
                    print("Base directory NOT FOUND (is_guess=TRUE) - let's see whether the user even needs it")
                    self.config_base_directory_is_guess = True
            
            if not self.config_base_directory_is_guess:
                ## Load project-tree ini
                project_tree_layout_ini = None
                for f in [self.config_tree_layout_file, self.config_tree_layout_file_readonly]:
                    file = os.path.join(self.config_base_directory, self.config_sub_directory, f)
                    if os.path.isfile(file):
                        project_tree_layout_ini = file
                        break
                    
                if project_tree_layout_ini is not None:
                    self._load_project_tree(self.treeview.get_model(), project_tree_layout_ini)

                ## Load session_files ini
                session_files_ini = None
                for f in [self.config_session_file, self.config_session_file_initial]:
                    file = os.path.join(self.config_base_directory, self.config_sub_directory, f)
                    if os.path.isfile(file):
                        session_files_ini = file
                        break
                
                if session_files_ini is not None:
                    self._load_session_files(session_files_ini)
                
        #geany.signals.connect('document-open', self.on_document_open)
        geany.signals.connect('document-close', self._document_close)
        
        ### Does not happen
        #geany.signals.connect('project-close', self._project_close)
                

    def cleanup(self):
        print("cleanup")
        # destroy top level widgets to remove them from the UI/memory
        for widget in self.widget_destroy_stack:
            widget.destroy()
            
    def _document_close(self, doc, data):
        print("_document_close")
        return True # Geany should continue doing its job
            
    #def _project_close(self):
    #    print("_project_close")
    #    return True # Geany should continue doing its job
            
            
    #############  project-tree ini file functions START #############  

    def _load_project_tree(self, model, config_file):
        with open(config_file, 'r') as fin:
            config = ConfigParser.SafeConfigParser()
            config.readfp(fin)
            #print("Sections", config.sections())
            
            def _load_project_tree_branch(section, parent):
                ## Create a nice dictionary of stuff from this section - each integer(sorted) can contain several entries
                key_matcher = re.compile("(\d+)-?(\S*)")
                d=dict()
                for k,v in config.items(section):
                    #print("('%s', '%s')" % (k, v))
                    m = key_matcher.match(k)
                    if m:
                        order = int(m.group(1))
                        if order not in d:
                            d[order]=dict()
                        d[order][m.group(2)] = v
                    
                for k,vd in sorted(d.iteritems()):  # Here, vd is dictionary of data about each 'k' item
                    if '' in vd: # This is a file (the default ending)
                        ## Just add the file to the tree where we are
                        iter = model.append(parent, TreeViewRowFile(vd[''], label=vd.get('label', None)).row)
                        # No need to store this 'iter' - can easily append after
                        
                    else:  # This is something special
                        if 'group' in vd:
                            group = vd['group']
                            ## Add the group to the tree, and recursively go after that section...
                            iter = model.append(parent, TreeViewRowGroup(group, label=vd.get('label', None)).row)
                            ### Descend with parent=iter
                            _load_project_tree_branch(section+'/'+group, iter)
            
            if config.has_section('.'):
                #print("Found Root!")
                model.clear()
                _load_project_tree_branch('.', None)
                            

    def _save_project_tree(self, model, config_file):
        config = ConfigParser.SafeConfigParser()

        def _save_project_tree_branch(section, iter):
            config.add_section(section)
            i, finished = 10, False
            while iter:
                row = model[iter]
                actual = row[TreeViewRow.COL_RAWTEXT]
                if row[TreeViewRow.COL_TYPE] == TreeViewRow.TYPE_FILE:
                    config.set(section, "%d" % (i,), actual)
                else:
                    config.set(section, "%d-group" % (i,), actual)
                    iter_branch = model.iter_children(iter)
                    _save_project_tree_branch(section+'/'+actual, iter_branch)
                
                i += 10 # Give room for manual insertion in ini file
                iter = model.iter_next(iter)

        ## Now walk along the whole 'model', creating groups = sections, and files as we go
        _save_project_tree_branch('.', model.get_iter_root())
        
        with open(config_file, 'w') as fout:
            config.write(fout)


    def _change_base_directory(self, new_config_base_directory): ## Implicit side-effects for config_base_directory and config_base_directory_is_guess
        old_config_base_directory = self.config_base_directory 
        if True or old_config_base_directory != new_config_base_directory: 
            ## Go through project-tree files, rebasing them
            # walk along the whole 'model', rebasing all the branches too
            model = self.treeview.get_model()
            
            def _change_base_directory_branch(iter):
                while iter:
                    row = model[iter]
                    actual = row[TreeViewRow.COL_RAWTEXT]
                    if row[TreeViewRow.COL_TYPE] == TreeViewRow.TYPE_FILE:
                        TreeViewRowFile.rebase(row, old_config_base_directory, new_config_base_directory)
                    else:
                        iter_branch = model.iter_children(iter)
                        _change_base_directory_branch(iter_branch)
                    iter = model.iter_next(iter)
            
            _change_base_directory_branch(model.get_iter_root())
            
        ## All done - safe to declare new allegances
        self.config_base_directory = new_config_base_directory
        self.config_base_directory_is_guess = False

    def _add_docs_to_selected(self, docs):
        model, iter = self.treeview.get_selection().get_selected() # iter = None if nothing selected
        for doc in docs:
            print("Document filename= ", doc.file_name)
            file = doc.file_name 
            if file is not None: 
                print("self.config_base_directory = %s" % (self.config_base_directory,))
                print("os.path.dirname(file) = %s" % (os.path.dirname(file),))
                #file_relative = os.path.join(
                #                          os.path.relpath(os.path.dirname(file), self.config_base_directory),
                #                          os.path.basename(file)
                #                        )
                file_relative = os.path.relpath(file, self.config_base_directory)
                print("file_relative = %s" % (file_relative,))

                if iter is None or model[iter][TreeViewRow.COL_TYPE] == TreeViewRow.TYPE_GROUP:
                    print("  iter is a Group, add as child")
                    model.insert_after( parent=iter, sibling=None, row=TreeViewRowFile(file_relative).row)
                else:
                    print("  iter is a File, add as sibling")
                    model.insert_after( parent=model.iter_parent(iter), sibling=iter, row=TreeViewRowFile(file_relative).row)

    #############  project-tree ini file functions END #############  
                    
    #############  project-tree from SciTEpm file functions START #############  

    def _load_project_tree_from_scitepm(self, model, config_file):
        import xml.etree.ElementTree as ET
        tree = ET.parse(config_file)
        root = tree.getroot()
        if root is not None: 
            print("Found SciTEpm Root!")
            model.clear()
            self._load_project_tree_from_scitepm_branch(model, root, None)
                            
    def _load_project_tree_from_scitepm_branch(self, model, root, parent):
        for n in root:  
            if n.tag == 'file':  # This is a file
                ## Just add the file to the tree where we are
                iter = model.append(parent, TreeViewRowFile(n.text, label=None).row)
                # No need to store this 'iter' - can easily append after
                
            else: 
                if n.tag == 'group':
                    group = n.attrib.get('name')
                    ## Add the group to the tree, and recursively go after that section...
                    iter = model.append(parent, TreeViewRowGroup(group, label=None).row)
                    ### Descend with parent=iter
                    self._load_project_tree_from_scitepm_branch(model, n, iter)
                    
    #############  project-tree from SciTEpm file functions END #############  

    #############  session-files ini functions START #############  

    def _load_session_files(self, config_file):
        with open(config_file, 'r') as fin:
            config = ConfigParser.SafeConfigParser()
            config.readfp(fin)
            #print("Sections", config.sections())
            
            open_files_section = "open-files"
            if config.has_section(open_files_section):
                key_matcher = re.compile("(\d+)-?(\S*)")
                d=dict()
                for k,v in config.items(open_files_section):  ## Need to sort these numerically
                    #print("('%s', '%s')" % (k, v))
                    m = key_matcher.match(k)
                    if m:
                        order = int(m.group(1))
                        if order not in d:
                            d[order]=dict()
                        d[order][m.group(2)] = v
                line_matcher = re.compile("(.*?)\:([\d\.]+)$")
                for k,vd in sorted(d.iteritems()):  # Here, vd is dictionary of data about each 'k' item
                    if '' in vd: # This is a file (the default type of item)
                        file_relative = vd['']
                        at_line = 1
                        m = line_matcher.match(file_relative)
                        if m:  # This only matches if there's a line number there
                            file_relative = m.group(1)
                            at_line = int(m.group(2))
                        print("LOADING : file_relative:line = %s:%d" % (file_relative, at_line,))
                        filepath = os.path.join(self.config_base_directory, file_relative)
                        doc = geany.document.open_file(filepath)
                        #doc.editor.goto_pos(at_line)
                        
    
    def _save_session_files(self, config_file):
        config = ConfigParser.SafeConfigParser()
        
        open_files_section = "open-files"
        config.add_section(open_files_section)
        i = 0
        #for doc in geany.document.get_documents_list(): # This appears to be in an arbitrary order
        while True:       
            doc=geany.document.get_from_page(i)
            if doc is None:  # Finished list the document tabs
                break
            file = doc.file_name 
            if file is not None: 
                file_relative = os.path.relpath(file, self.config_base_directory)
                at_line = 1
                scroll_pct = doc.editor.scroll_percent
                print("SAVING : file_relative:line=pct = %s:%d=%.2f" % (file_relative, at_line, scroll_pct))
                config.set(open_files_section, "%d" % (i*10,), "%s:%d" % (file_relative, at_line))
            i += 1

        with open(config_file, 'w') as fout:
            config.write(fout)
        
    #############  session-files ini functions END #############  
    

    #############  file load/save dialogs START #############  
    
    def _geany_subdir_exists(self):
        return os.path.isdir(os.path.join(self.config_base_directory, self.config_sub_directory, ))

    def _prompt_for_geany_directory(self, start_dir, sub_dir, create=True):
        dir = None
        is_guess = True
        
        entry = gtk.Entry()
        entry.set_text(start_dir)
        prompt = geany.ui_utils.path_box_new(None, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, entry)

        dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
                                        gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL, 
                                        "Base Path for Project-Tree configuration directory '%s'" % (sub_dir,))
        dialog.vbox.pack_end(prompt, True, True, 0)
        dialog.show_all()
        
        response = dialog.run()
        path = entry.get_text()
        dialog.hide_all()
        if response == gtk.RESPONSE_OK:
            if len(path)>0:
                dir=path
                is_guess = False
        
        if dir and create: 
            directory_geany = os.path.join(dir, sub_dir)
            if not os.path.isdir(directory_geany):
                os.makedirs( directory_geany )
            if not os.path.isdir(directory_geany):
                dir=None
        
        return dir, is_guess

    def _prompt_for_ini_file(self, type):
        start_dir = os.getcwd()  # Base guess
        if self.config_base_directory is not None:
            start_dir = os.path.join(self.config_base_directory, self.config_sub_directory, )
 
        entry = gtk.Entry()
        entry.set_text(os.path.join(start_dir, "*")) # Moves into the directory
        prompt = geany.ui_utils.path_box_new(None, gtk.FILE_CHOOSER_ACTION_OPEN, entry)

        dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
                                        gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL, 
                                        "Open project-tree %s file" % (type,))
        dialog.vbox.pack_end(prompt, True, True, 0)
        dialog.show_all()
        
        response = dialog.run()
        project_tree_layout_ini = entry.get_text()
        dialog.hide_all()
        if response == gtk.RESPONSE_OK:
            if os.path.isfile(project_tree_layout_ini):
                return project_tree_layout_ini
        return None

    #############  file load/save dialogs END #############  
    
    #############  menubar functions START #############  
                    
    ## Annotation style for menubar callbacks :
    # _menubar _{order#} _{heading-label} _{submenu-order#} _{submenu-label}
    
    def _menubar_0_File_3_Load_Project_Tree(self, data):
        """
        Loads the project tree specified by the user in the message box
        """
        print("_menubar__File__Load_Project_Tree")
        project_tree_layout_ini = self._prompt_for_ini_file("*tree*.ini")
        if project_tree_layout_ini:
            self._change_base_directory(os.path.dirname(os.path.dirname(project_tree_layout_ini))) # strip off .geany/XYZ.ini
            self._load_project_tree(self.treeview.get_model(), project_tree_layout_ini)
        return True
        
    def _menubar_0_File_4_Import_Project_Tree_from_SciTEpm(self, data):
        """
        Imports the project tree from the scitepm.xml file specified by the user in the message box
        """
        print("_menubar__File__Load_Project_Tree_from_SciTEpm")
        project_tree_layout_scitepm = self._prompt_for_ini_file("scitepm.xml")
        if project_tree_layout_scitepm:
            self._change_base_directory(os.path.dirname(project_tree_layout_scitepm)) # strip off XYZ.xml
            self._load_project_tree_from_scitepm(self.treeview.get_model(), project_tree_layout_scitepm)
        return True
        
    def _menubar_0_File_0_Save_Project_Tree(self, data):
        print("_menubar__File__Save_Project_Tree")
        if self.config_base_directory_is_guess:
            new_config_base_directory, self.config_base_directory_is_guess = self._prompt_for_geany_directory(self.config_base_directory, self.config_sub_directory)
            if not self.config_base_directory_is_guess:
                self._change_base_directory(new_config_base_directory)
        if not self.config_base_directory_is_guess:
            model = self.treeview.get_model()
            project_tree_layout_ini = os.path.join(self.config_base_directory, self.config_sub_directory, self.config_tree_layout_file)
            self._save_project_tree(model, project_tree_layout_ini)
        return True
        
    def _menubar_0_File_2_SEPARATOR(self): pass
    
    def _menubar_0_File_5_SEPARATOR(self): pass
    
    def _menubar_0_File_6_Load_Session(self, data):
        print("_menubar__File__Load_Session")
        session_files_ini = self._prompt_for_ini_file("*session*.ini")
        if session_files_ini:
            self._change_base_directory(os.path.dirname(os.path.dirname(session_files_ini))) # strip off .geany/XYZ-session.ini
            self._load_session_files(session_files_ini)
        return True
        
    def _menubar_0_File_1_Save_Session(self, data):
        print("_menubar__File__Save_Session")
        if self.config_base_directory_is_guess:
            new_config_base_directory, self.config_base_directory_is_guess = self._prompt_for_geany_directory(self.config_base_directory, self.config_sub_directory)
            if not self.config_base_directory_is_guess:
                self._change_base_directory(new_config_base_directory)
        if not self.config_base_directory_is_guess:
            session_files_ini = os.path.join(self.config_base_directory, self.config_sub_directory, self.config_session_file)
            self._save_session_files(session_files_ini)
        return True
        
    def _menubar_1_Search_0_Find_in_Project_Files(self, data):
        print("_menubar__Search__Find_in_Project_Files")
        return True
        
    #############  menubar functions END #############  
        
    #############  popup functions START #############  
    
    ## Annotation style for menu callbacks (normally for popups) :
    # _popup _{order#} _{heading-label}
    
    def _popup_0_SEPARATOR(self, data): pass
        
    def _popup_4_Add_Group(self, data):
        print("_popup__Add_Group")
        dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
                                        gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL,  "Add Group :")
        prompt = gtk.Entry()
        dialog.vbox.pack_end(prompt, True, True, 0)
        if True : # Make 'enter' click on Ok
            dialog.set_default_response(gtk.RESPONSE_OK)
            prompt.set_activates_default(True)
        dialog.show_all()
        
        response = dialog.run()
        group = prompt.get_text()
        dialog.hide_all()
        
        if response == gtk.RESPONSE_OK and len(group)>0:
            print("Adding Group : '%s'" % (group,))
            model, iter = self.treeview.get_selection().get_selected() # iter = None if nothing selected
            model.insert_after( parent=None, sibling=iter, row=TreeViewRowGroup(group).row)
        return True
    
    def _popup_1_Add_Current_File(self, data):
        print("_popup__Add_Current_File")
        doc = geany.document.get_current()
        if doc is not None:
            self._add_docs_to_selected([doc])
        return True
        
    def _popup_2_Add_Open_Files(self, data):
        print("_popup__Add_Open_Files")
        docs = geany.document.get_documents_list()
        self._add_docs_to_selected(docs)
        return True
        
    def _popup_3_SEPARATOR(self, data): pass
    
    def _popup_5_SEPARATOR(self, data): pass
    
    def _popup_6_Rename(self, data):
        print("_popup__Rename")
        model, iter = self.treeview.get_selection().get_selected() # iter = None if nothing selected
        if iter is None : return True
        text_current = model[iter][TreeViewRow.COL_RAWTEXT]
        
        dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
                                        gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL,  "Rename :")
        prompt = gtk.Entry()
        prompt.set_text(text_current)
        dialog.vbox.pack_end(prompt, True, True, 0)
        if True : # Make 'enter' click on Ok
            dialog.set_default_response(gtk.RESPONSE_OK)
            prompt.set_activates_default(True)
        dialog.show_all()
        
        response = dialog.run()
        text = prompt.get_text()
        dialog.hide_all()
        
        if response == gtk.RESPONSE_OK and len(text)>0:
            print("Renaming: '%s' to '%s'" % (text_current, text, ))
            if model[iter][TreeViewRow.COL_TYPE] == TreeViewRow.TYPE_FILE:
                row = TreeViewRowFile(text).row
            else:
                row = TreeViewRowGroup(text).row
            model[iter] = row
        return True
        
    def _popup_7_Remove(self, data):
        print("_popup__Remove")
        model, iter = self.treeview.get_selection().get_selected() # iter = None if nothing selected
        if iter is None : return True
            
        ## ARE YOU SURE?
        text_current = model[iter][TreeViewRow.COL_RAWTEXT]
        dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
                                        gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO,  
                                        "Remove '%s' from list?" % (text_current,))
        response = dialog.run()
        dialog.hide_all()
        if response == gtk.RESPONSE_YES:
            print("Deleting: '%s'" % (text_current,  ))
            model.remove(iter)
        return True
        
    ### Popup click handler ###
    
    def treeview_button_press_event(self, treeview, event):
        print("treeview_menu event.button=%d" % (event.button,))
        if event.button == 3:  # Right click
            path_at_pos = treeview.get_path_at_pos(int(event.x), int(event.y))
            if path_at_pos:
                path, col, dx, dy = path_at_pos
                treeview.set_cursor(path) # Move the selection under clicker
            
            ## See: https://developer.gnome.org/pygtk/stable/class-gtkmenu.html#method-gtkmenu--popup
            self.menu_popup.popup(None,None,None, event.button, event.time)
            return True
        return False
    #############  popup functions END #############  

    def treeview_row_activated(self, treeview, path, col):
        print("Activated Tree-Path (double-clicked) ", path)
        model = treeview.get_model()
        iter = model.get_iter(path)
        row = model[iter]
        if row[TreeViewRow.COL_TYPE] == TreeViewRow.TYPE_GROUP: # This is a group : double-clicked
            print("Group ", row[TreeViewRow.COL_RAWTEXT])
            if treeview.row_expanded(path):
                treeview.collapse_row(path)
            else:
                treeview.expand_row(path, False)
        else:                                   # This is a file : double-clicked
            f = row[TreeViewRow.COL_RAWTEXT]  # This is a relative path
            print("OPEN FILE     ", f)
            filepath = os.path.join(self.config_base_directory, f)
            geany.document.open_file(filepath)
        
    #############  Drag-n-Drop START #############  

    ## DnD Source Signals
    def _drag_data_get(self, treeview, drag_context, selection_data, info, eventtime):
        print("drag_data_get")
        
        treeselection = treeview.get_selection()
        model, iter = treeselection.get_selected()
        path = model.get_path(iter)
        
        print("drag_data_get path=", path)
        ## http://www.pygtk.org/pygtk2reference/class-gtkselectiondata.html
        # This is implicitly in 'GTK_TREE_MODEL_ROW' format
        success = selection_data.tree_set_row_drag_data(model, path)
        #print("SENT OK" if success else "FAILED TO SEND")
        
        #context.drag_abort(eventtime)  ## This does nothing??
        print("drag_data_get_END")

    def _drag_data_delete(self, treeview, drag_context):
        print("_drag_data_delete")
        if drag_context.is_source and drag_context.action == gtk.gdk.ACTION_MOVE:
            print("_drag_data_delete - Relevant")
            print("     drag_context ", drag_context)
            selection = drag_context.drag_get_selection()
            print("     drag_context selection=", selection)
            
            #treeview.get_model().remove(sel)
            # For some reason this gets called twice.
            #map(treeview.get_model().remove, treeview.__iters)
            #treeview.get_model().remove
            #treeview.__iters = []
            return False


    ## DnD Destination Signals
    def _drag_motion(self, treeview, drag_context, x, y, eventtime):
        #print("drag_motion")
        ## This shows up the target location during the drag
        try:
            treeview.set_drag_dest_row(*treeview.get_dest_row_at_pos(x, y))
        except TypeError:
            treeview.set_drag_dest_row(len(treeview.get_model()) - 1, gtk.TREE_VIEW_DROP_AFTER)

        ## This makes it look like a MOVE
        drag_context.drag_status(gtk.gdk.ACTION_MOVE, eventtime)
        return True # i.e. this has been handled

    #### See : http://www.pygtk.org/pygtk2tutorial/ch-DragAndDrop.html
    #def _drag_drop(self, treeview, drag_context, x, y, eventtime):
    #    print("drag_drop")
    #    return True
        
    def _drag_data_received(self, treeview, drag_context, x, y, selection_data, info, eventtime):
        print("drag_data_received_data data-type = ", selection_data.get_data_type(), eventtime)
        
        if selection_data.get_data_type() == 'GTK_TREE_MODEL_ROW':
            ### Need to handle movement of trees, for instance...
            ### LOOK AT : http://www.daa.com.au/pipermail/pygtk/2003-November/006320.html
            
            print('  GTK_TREE_MODEL_ROW', eventtime)
            #model, data = selection.tree_get_row_drag_data()  ## This worked on a data basis
            model, source_iter = treeview.get_selection().get_selected()
            drop_info = treeview.get_dest_row_at_pos(x, y)
            deny = False
            if drop_info:
                target_path, drop_position = drop_info 
                target_iter = model.get_iter(target_path)
                source_path = model.get_path(source_iter)
                
                #if (drop_position == gtk.TREE_VIEW_DROP_INTO_OR_BEFORE or drop_position == gtk.TREE_VIEW_DROP_INTO_OR_AFTER):
                print("  source_path = ", source_path)
                print("  target_path = ", target_path)
                print("  drop_info = ", drop_info)
                print("  action = ", drag_context.action)
                
                
                if (drop_position == gtk.TREE_VIEW_DROP_INTO_OR_BEFORE or drop_position == gtk.TREE_VIEW_DROP_INTO_OR_AFTER):
                    # This is dropping into something else
                    row_type, = model.get(target_iter, TreeViewRow.COL_TYPE)
                    print("      Target being dropped INTO something : ", row_type)
                    if row_type == TreeViewRow.TYPE_FILE:
                        # Can't drop anything into a file
                        print("      Target being dropped INTO is a file!")
                        deny = True
                        
                if model.is_ancestor(source_iter, target_iter):
                    print("      Dropped into Ancestor")
                    deny = True
                    
                if source_path == target_path:
                    print("      Dropped onto self")
                    deny = True
                    
            else:
                print("  not dropped onto an existing row before/after position")
                ### This should be an allowed action : Drop into the blank space after the current rows
                drop_position = gtk.TREE_VIEW_DROP_INTO_OR_AFTER
                target_iter = None
                
            if deny:
                pass
                print("          DENY action")
                #drag_context.drag_abort(eventtime)  #SEGFAULT
                #drag_context.drag_status(0, eventtime)
                #drag_context.finish(False, False, eventtime)
                
                ###  This should really deny the operation...
                #print("  drag_context.drop_reply(False, eventtime)")
                #drag_context.drop_reply(False, eventtime)
                #return False
            else:
                ## This is a recursive copy, so that groups get transferred whole
                _treeview_copy_row(treeview, model, source_iter, target_iter, drop_position)
                
                ## Really should use the 'delete' signal, but very poorly documented
                model.remove(source_iter)
                drag_context.finish(True, False, eventtime)

        else:
            print("  Not GTK_TREE_MODEL_ROW -- no context.finish()")

    #############  Drag-n-Drop END #############  

## See : http://www.daa.com.au/pipermail/pygtk/2003-November/006320.html
def _treeview_expand_to_path(treeview, path):
    """Expand row at path, expanding any ancestors as needed.

    This function is provided by gtk+ >=2.2, but it is not yet wrapped
    by pygtk 2.0.0."""
    for i in range(len(path)):
        treeview.expand_row(path[:i+1], open_all=False)
        
## See : http://www.daa.com.au/pipermail/pygtk/2003-November/006320.html
def _treeview_copy_row(treeview, model, source, target, drop_position):
    """Copy tree model rows from treeiter source into, before or after treeiter target.

    All children of the source row are also copied and the
    expanded/collapsed status of each row is maintained."""

    source_row = model[source]
    if drop_position == gtk.TREE_VIEW_DROP_INTO_OR_BEFORE:
        new = model.prepend(parent=target, row=source_row)
    elif drop_position == gtk.TREE_VIEW_DROP_INTO_OR_AFTER:
        new = model.append(parent=target, row=source_row)
    elif drop_position == gtk.TREE_VIEW_DROP_BEFORE:
        new = model.insert_before( parent=None, sibling=target, row=source_row)
    elif drop_position == gtk.TREE_VIEW_DROP_AFTER:
        new = model.insert_after( parent=None, sibling=target, row=source_row)

    # Copy any children of the source row.
    for n in range(model.iter_n_children(source)):
        child = model.iter_nth_child(source, n)
        _treeview_copy_row(treeview, model, child, new, gtk.TREE_VIEW_DROP_INTO_OR_BEFORE)

    # If the source row is expanded, expand the newly copied row
    # also.  We must add at least one child before we can expand,
    # so we expand here after the children have been copied.
    source_is_expanded = treeview.row_expanded(model.get_path(source))
    if source_is_expanded:
        _treeview_expand_to_path(treeview, model.get_path(new))




def _create_menubar_from_annotated_callbacks(class_with_menu_callbacks):
    """
    This is a nasty little function that looks through the class, and builds the menubar from 
    the specifically formed methods of the class, and links it all up as menus, submenus and callbacks ...
    Maybe there's a nicer way to do this using decorators
    """
    
    ## Sample annotated method :  _menubar_0_File_0_LoadSession
    attrib_matcher = re.compile("_menubar_(\d+)_(\S+)_(\d+)_(.+)")
    menubar_headers, menu_current_title = [], ""
    for k in sorted(dir(class_with_menu_callbacks)):
        #print("Attr: ",k)
        m = attrib_matcher.match(k)
        if m:
            if m.group(2) != menu_current_title:
                menu_current_title = m.group(2)
                menubar_headers.append(dict(label=menu_current_title, submenu=[], ))
            label = m.group(4).replace('_',' ')
            menubar_headers[-1]['submenu'].append(dict( label=label, fn=k, ))
    #print(menubar_headers)
    
    menu_bar = gtk.MenuBar()
    for menubar_header in menubar_headers:
        menu = gtk.Menu()    # Don't need to show menus
        menu_item = gtk.MenuItem(menubar_header['label'])
        
        # Create the submenu items
        for submenu_item in menubar_header['submenu']:
            if submenu_item['label'] == 'SEPARATOR':
                item = gtk.SeparatorMenuItem()
            else:
                item = gtk.MenuItem(submenu_item['label'])
                item.connect_object("activate", getattr(class_with_menu_callbacks, submenu_item['fn']), submenu_item['fn'])
            menu.append(item)
            item.show()
    
        menu_item.set_submenu(menu)
        menu_item.show()
        
        menu_bar.append(menu_item)
    menu_bar.show()
    return menu_bar
    

def _create_menu_from_annotated_callbacks(class_with_menu_callbacks, prefix = '_popup'):
    """
    This is a nasty little function that looks through the class, and builds the menu from 
    the specifically formed methods of the class, and links it all up as items and callbacks ...
    Maybe there's a nicer way to do this using decorators
    """
    
    ## Sample annotated method :  _popup_0_AddCurrentFile
    attrib_matcher = re.compile(prefix+"_(\d+)_(.+)")
    menu_headers=[]
    for k in sorted(dir(class_with_menu_callbacks)):
        #print("Attr: ",k)
        m = attrib_matcher.match(k)
        if m:
            label = m.group(2).replace('_',' ')
            menu_headers.append(dict( label=label, fn=k, ))
    #print(menu_headers)
    
    menu = gtk.Menu()
    for menu_header in menu_headers:
        if menu_header['label'] == 'SEPARATOR':
            item = gtk.SeparatorMenuItem()
        else:
            item = gtk.MenuItem(menu_header['label'])
            item.connect_object("activate", getattr(class_with_menu_callbacks, menu_header['fn']), menu_header['fn'])
        item.show()
        menu.append(item)
    
    menu.show()
    return menu    

#############  treeview row helper class START #############  
class TreeViewRow:
    # These are the defined column numbers for the data fields
    COL_LABEL   =0
    COL_RAWTEXT =1 
    COL_TYPE    =2
    # These are the Types referred to in the column COL_TYPE
    TYPE_FILE   =0
    TYPE_GROUP  =1
    # These are the type definitions, for creating the viewtable itself
    TYPES = (gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT)
    
    # This is the contents of a row (for easy construction)
    row = ( None, None, None )
    
    ## Sufficient to use model[iter] directly, as long as accesses use the above COL_ constants
    #def __init__(self): return 
    #def from_model(self, model, iter):
    #    #print("model = ", model)
    #    #print("iter = ", iter)
    #    #(label, actual, type,) = model.get(iter, self.TREEVIEW_VISIBLE_TEXT_COL, self.TREEVIEW_HIDDEN_TEXT_COL, self.TREEVIEW_HIDDEN_TYPE_COL)
    #    #self.row = model.get(iter, self.COL_LABEL, self.COL_RAWTEXT, self.COL_TYPE)
    #    self.row = model[iter]

class TreeViewRowFile(TreeViewRow):
    def __init__(self, filename, label=None):
        vis = label if label else os.path.basename(filename)
        self.row = ( vis, filename, TreeViewRow.TYPE_FILE )
    @staticmethod
    def rebase(row, current_dir, new_dir):
        file = row[TreeViewRow.COL_RAWTEXT]
        filepath = os.path.join(current_dir, file)
        rebased  = os.path.relpath(file, new_dir)
        row[TreeViewRow.COL_RAWTEXT] = rebased
        print("Rebased TreeViewRowFile( %s -> %s )" % (file, rebased,))

class TreeViewRowGroup(TreeViewRow):
    def __init__(self, group, label=None):
        vis = label if label else group
        self.row = ( vis, group, TreeViewRow.TYPE_GROUP )
