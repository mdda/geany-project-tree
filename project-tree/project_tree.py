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

    config_base_directory = None
    config_sub_directory         = ".geany"
    
    config_tree_layout_file           = "project-tree-layout.ini"
    config_tree_layout_file_readonly  = "project-tree-layout_devel.ini"
    config_session_file               = "session.ini"
    config_session_file_initial       = "session_default.ini"
    
    TREEVIEW_VISIBLE_TEXT_COL = 0
    TREEVIEW_HIDDEN_TEXT_COL = 1
    TREEVIEW_HIDDEN_TYPE_COL = 2  
    
    TREEVIEW_ROW_TYPE_FILE = 0
    TREEVIEW_ROW_TYPE_GROUP = 1

    widget_destroy_stack = []
    
    def __init__(self):
        self.clipboard=gtk.clipboard_get()

        if True:  ## Set up the pop-up menu
            self.menu_popup = _create_menu_from_annotated_callbacks(self, '_popup')
            self.widget_destroy_stack.extend([self.menu_popup, ])

        if True:  ## Set up a reusable, generic question/answer dialog box and a confirmation box
            self.dialog_confirm = gtk.MessageDialog(None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, None)
            
            self.dialog_input   = gtk.MessageDialog(None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK,     None)
            self.dialog_input_entry = gtk.Entry()
            
            hbox = gtk.HBox()
            hbox.pack_start(gtk.Label("Name:"), False, 5, 5)
            hbox.pack_end(self.dialog_input_entry)
            self.dialog_input.vbox.pack_end(hbox, True, True, 0)
        
            self.widget_destroy_stack.extend([self.dialog_input, self.dialog_confirm, ])
            
        if True:  ## Set up the side-bar
            treemodel = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT)
            #setup treeview and treestore model
            #self.treemodel.connect("cursor-changed", self.populate_treeview)
            
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
            
            #~ fontT = pango.FontDescription("serif light Oblique 8")
            #~ fontO = pango.FontDescription("serif bold 8")
            #~ treeView.cell[2].set_property('font-desc', fontT)
            #~ treeView.cell[3].set_property('font-desc', fontO)

            pix_renderer = gtk.CellRendererPixbuf()
            text_renderer= gtk.CellRendererText()

            column0=gtk.TreeViewColumn("Tree Layout Options", text_renderer, text=0)
            #column0.set_title('Icons & Text')
            ## This is for setting an icon - which we won't be showing anyway
            #column0.set_cell_data_func(pix_renderer, self.render_icon_remote)
            
            #column0.pack_start(text_renderer, False)
            #column0.set_resizable(False)

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
            #homogeneous = False, spacing = 0
            box = gtk.VBox(False, 0)
            ##expand, fill, padding
            box.pack_start(self.menu_bar, expand=False, fill=False, padding=2)
            box.pack_end(self.scrolledwindow, expand=True, fill=True, padding=2)
            box.show()
            
            label = gtk.Label("ProjectTree")
            
            geany.main_widgets.sidebar_notebook.append_page(box, label)
            #geany.main_widgets.message_window_notebook.append_page(self.database.gui, labelMYSQL)
            #self.browser.browser_tab = geany.main_widgets.message_window_notebook.append_page(self.browser.gui, labelBrowser)
            #geany.main_widgets.message_window_notebook.append_page(self.sftp.gui, labelSFTP)

            # keep track of widgets to destroy in plugin_cleanup()
            self.widget_destroy_stack.extend([box, label, ])


        if True:  ## Load in configuration
            ## Apparently, get_current document not loaded at the time plugin is starting
            #doc=geany.document.get_current()
            #if doc is not None:
            #    print "geany launch document: %s" % (doc.real_path, )
            
            ## Apparently, this isn't necessarily a sensible value
            #print "geany.general_prefs.default_open_path=%s" % (geany.general_prefs.default_open_path, )
            
            ## Attempt to see .geany directory here
            if self.config_base_directory is None:
                #print "os.getcwd()=%s" % (os.getcwd(),)
                directory = os.getcwd()
                directory_geany = os.path.join(directory, self.config_sub_directory, )
                if os.path.isdir(directory_geany):
                    self.config_base_directory=directory
                else:
                    ## recurse, search for .git, etc
                    # ...
                    ## Finally : prompt for base directory for .geany file
                    
                    pass
            
            if self.config_base_directory is not None:
                project_tree_layout_ini = None
                for f in [self.config_tree_layout_file, self.config_tree_layout_file_readonly]:
                    file = os.path.join(self.config_base_directory, self.config_sub_directory, f)
                    if os.path.isfile(file):
                        project_tree_layout_ini = file
                        break
                    
                if project_tree_layout_ini is not None:
                    self._load_project_tree(self.treeview.get_model(), project_tree_layout_ini)
                
                ## Load in session information
                ## TODO
                pass


    #############  project-tree ini file functions START #############  

    def _load_project_tree(self, model, config_file):
        with open(config_file, 'r') as fin:
            config = ConfigParser.SafeConfigParser()
            config.readfp(fin)
            #print "Sections", config.sections()
            if config.has_section('.'):
                #print "Found Root!"
                model.clear()
                self._load_project_tree_branch(model, config, '.', None)
                
                            
    def _load_project_tree_branch(self, model, config, section, parent):
        ## Create a nice dictionary of stuff from this section - each integer(sorted) can contain several entries
        key_matcher = re.compile("(\d+)-?(\S*)")
        d=dict()
        for k,v in config.items(section):
            #print "('%s', '%s')" % (k, v)
            m = key_matcher.match(k)
            if m:
                order = int(m.group(1))
                if order not in d:
                    d[order]=dict()
                d[order][m.group(2)] = v
            
        for k,vd in sorted(d.iteritems()):  # Here, vd is dictionary of data about each 'k' item
            if '' in vd: # This is a file (the default ending)
                f = vd['']
                #print "Got a file: %s" % (f,)
                label = vd.get('label', os.path.basename(f))
                ## Just add the file to the tree where we are
                iter = model.append(parent, (label, f, self.TREEVIEW_ROW_TYPE_FILE))  # (TREEVIEW_VISIBLE_TEXT_COL, TREEVIEW_HIDDEN_TEXT_COL, TREEVIEW_ROW_TYPE_FILE)
                # No need to store this 'iter' - can easily append after
                
            else:  # This is something special
                if 'group' in vd:
                    g = vd['group']
                    #print "Got a group : %s" % (g,)
                    label = vd.get('label', g)
                    ## Add the group to the tree, and recursively go after that section...
                    iter = model.append(parent, (g, g, self.TREEVIEW_ROW_TYPE_GROUP))  # (TREEVIEW_VISIBLE_TEXT_COL, TREEVIEW_HIDDEN_TEXT_COL)
                    ### Descend with parent=iter
                    self._load_project_tree_branch(model, config, section+'/'+g, iter)
                    
    def _save_project_tree(self, model, config_file):
        config = ConfigParser.SafeConfigParser()
        
        ## Now walk along the whole 'model', creating groups = sections, and files as we go
        iter_root = model.get_iter_root()
        self._save_project_tree_branch(model, config, '.', iter_root)
        
        with open(config_file, 'w') as fout:
            config.write(fout)
            
    def _save_project_tree_branch(self, model, config, section, iter):
        config.add_section(section)
        i, finished = 10, False
        while iter:
            (label, actual, type,) = model.get(iter, self.TREEVIEW_VISIBLE_TEXT_COL, self.TREEVIEW_HIDDEN_TEXT_COL, self.TREEVIEW_HIDDEN_TYPE_COL)
            if type == self.TREEVIEW_ROW_TYPE_FILE:
                config.set(section, "%d" % (i,), actual)
            else:
                config.set(section, "%d-group" % (i,), actual)
                iter_branch = model.iter_children(iter)
                self._save_project_tree_branch(model, config, section+'/'+actual, iter_branch)
            
            i += 10 # Give room for manual insertion in ini file
            iter = model.iter_next(iter)
        
    #############  project-tree ini file functions END #############  
                    
    #############  menubar functions START #############  
                    
    ## Annotation style for menubar callbacks :
    # _menubar _{order#} _{heading-label} _{submenu-order#} _{submenu-label}
    
    def _menubar_0_File_0_Save_Project_Tree(self, data):
        print "_menubar_0_File_0_Save_Project_Tree"
        model = self.treeview.get_model()
        project_tree_layout_ini = os.path.join(self.config_base_directory, self.config_sub_directory, self.config_tree_layout_file)
        self._save_project_tree(model, project_tree_layout_ini)
        return True
        
    def _menubar_0_File_4_SEPARATOR(self): pass
    
    def _menubar_0_File_5_Load_Session(self, data):
        print "_menubar_0_File_5_Load_Session"
        return True
        
    def _menubar_0_File_6_Save_Session(self, data):
        print "_menubar_0_File_6_Save_Session"
        return True
        
    def _menubar_1_Search_0_Find_in_Project_Files(self, data):
        print "_menubar_1_Search_0_Find_in_Project_Files"
        return True
        
    #############  menubar functions END #############  
        
    #############  popup functions START #############  
    
    ## Annotation style for menu callbacks (normally for popups) :
    # _popup _{order#} _{heading-label}
    
    def _popup_0_SEPARATOR(self, data): pass
        
    def _popup_1_Add_Group(self, data):
        print "_popup_1_Add_Group"
        return True
    
    def _popup_2_Add_Current_File(self, data):
        print "_popup_2_Add_Current_File"
        return True
        
    def _popup_4_SEPARATOR(self, data): pass
    
    def _popup_5_Rename(self, data):
        print "_popup_5_Rename"
        return True
    def _popup_6_Delete(self, data):
        print "_popup_6_Delete"
        return True
        
    ### Popup click handler ###
    
    def treeview_button_press_event(self, treeview, event):
        print "treeview_menu event.button=%d" % (event.button,)
        if event.button == 3:  # Right click
            path_at_pos = treeview.get_path_at_pos(int(event.x), int(event.y))
            if path_at_pos:
                path, col, dx, dy = path_at_pos
                treeview.set_cursor(path) # Move the selection under clicker
            else: 
                ## This is not hovering over something
                path = None
            
            ## See: https://developer.gnome.org/pygtk/stable/class-gtkmenu.html#method-gtkmenu--popup
            #self.menu_popup.show()
            self.menu_popup.popup(None,None,None, event.button, event.time, data=path)
            return True
        return False
    #############  popup functions END #############  
        
    def tree_add_group(self, *args):
        print "tree_add_group"
        
        self.dialog_input_entry.set_text('')
        self.dialog_input.set_markup('Add Group name:')
        self.dialog_input.show_all()
        response = self.dialog_input.run()
        group = self.dialog_input_entry.get_text()
        self.dialog_input.hide_all()
        if response == gtk.RESPONSE_OK and len(group)>0:
            print "Adding Group : '%s'" % (group,)
            #if not os.path.isdir(self.selected_fullpath):
            #    print newfilename
            #    shutil.copyfile(self.selected_fullpath, newfilename)
            #    geany.document.open_file(newfilename)
        """
        self.dialog_input_entry.set_text(self.selected_filename)
        self.dialog_input.set_markup('Rename File/Folder')
        self.dialog_input.show_all()
        response = self.dialog_input.run()
        newfilename = self.selected_filepath + self.dialog_input_entry.get_text()
        self.dialog_input.hide_all()
        print 'from ' + str(self.selected_fullpath)
        print 'to ' + str(newfilename)
        if not os.path.exists(newfilename):
            print os.rename(self.selected_fullpath, newfilename)
        """


    def tree_add_current_file(self, *args):
        print "tree_add_current_file"
        
        
    ### TODO : Prompt for .geany path
    def menu_empty_action_test(self, *args):
        entry = gtk.Entry()
        entry.set_text(os.getcwd())
        prompt = geany.ui_utils.path_box_new(None, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, entry)

        dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
                                    gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL, 
                                    "Base Path for Project-Tree configuration directory")
        dialog.vbox.pack_end(prompt, True, True, 0)
        dialog.show_all()
        
        response = dialog.run()
        path = entry.get_text()
        dialog.hide_all()
        if response == gtk.RESPONSE_OK:
            if len(path)>0:
                print "RETVAL_OK = " + path
            else:
                print "Too Short"
        else:
            print "RETVAL ignored"
            
            

    #############  Drag-n-Drop START #############  

    ## DnD Source Signals
    def _drag_data_get(self, treeview, drag_context, selection_data, info, eventtime):
        print "drag_data_get"
        
        treeselection = treeview.get_selection()
        model, iter = treeselection.get_selected()
        path = model.get_path(iter)
        
        print "drag_data_get path=", path
        ## http://www.pygtk.org/pygtk2reference/class-gtkselectiondata.html
        # This is implicitly in 'GTK_TREE_MODEL_ROW' format
        success = selection_data.tree_set_row_drag_data(model, path)
        #print "SENT OK" if success else "FAILED TO SEND"
        
        #context.drag_abort(eventtime)  ## This does nothing??
        print "drag_data_get_END"

    def _drag_data_delete(self, treeview, drag_context):
        print "_drag_data_delete"
        if drag_context.is_source and drag_context.action == gtk.gdk.ACTION_MOVE:
            print "_drag_data_delete - Relevant"
            print "     drag_context ", drag_context
            selection = drag_context.drag_get_selection()
            print "     drag_context selection=", selection
            
            #treeview.get_model().remove(sel)
            # For some reason this gets called twice.
            #map(treeview.get_model().remove, treeview.__iters)
            #treeview.get_model().remove
            #treeview.__iters = []
            return False


    ## DnD Destination Signals
    def _drag_motion(self, treeview, drag_context, x, y, eventtime):
        #print "drag_motion"
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
    #    print "drag_drop"
    #    return True
        
    def _drag_data_received(self, treeview, drag_context, x, y, selection_data, info, eventtime):
        print "drag_data_received_data data-type = ", selection_data.get_data_type(), eventtime
        
        if selection_data.get_data_type() == 'GTK_TREE_MODEL_ROW':
            ### Need to handle movement of trees, for instance...
            ### LOOK AT : http://www.daa.com.au/pipermail/pygtk/2003-November/006320.html
            
            print '  GTK_TREE_MODEL_ROW', eventtime
            #model, data = selection.tree_get_row_drag_data()  ## This worked on a data basis
            model, source_iter = treeview.get_selection().get_selected()
            drop_info = treeview.get_dest_row_at_pos(x, y)
            if drop_info:
                target_path, drop_position = drop_info 
                target_iter = model.get_iter(target_path)
                source_path = model.get_path(source_iter)
                
                #if (drop_position == gtk.TREE_VIEW_DROP_INTO_OR_BEFORE or drop_position == gtk.TREE_VIEW_DROP_INTO_OR_AFTER):
                print "  source_path = ", source_path
                print "  target_path = ", target_path
                print "  drop_info = ", drop_info
                print "  action = ", drag_context.action 
                
                deny = False
                
                if (drop_position == gtk.TREE_VIEW_DROP_INTO_OR_BEFORE or drop_position == gtk.TREE_VIEW_DROP_INTO_OR_AFTER):
                    # This is dropping into something else
                    row_type, = model.get(target_iter, self.TREEVIEW_HIDDEN_TYPE_COL)
                    print "      Target being dropped INTO something", row_type
                    if row_type == self.TREEVIEW_ROW_TYPE_FILE:
                        # Can't drop anything into a file
                        print "      Target being dropped INTO is a file!"
                        deny = True
                        
                if model.is_ancestor(source_iter, target_iter):
                    print "      Dropped into Ancestor"
                    deny = True
                    
                if source_path == target_path:
                    print "      Dropped onto self"
                    deny = True
                    
                if deny:
                    pass
                    print "          DENY action"
                    #drag_context.drag_abort(eventtime)  #SEGFAULT
                    #drag_context.drag_status(0, eventtime)
                    #drag_context.finish(False, False, eventtime)
                    
                    ###  This should really deny the operation...
                    #print "  drag_context.drop_reply(False, eventtime)"
                    #drag_context.drop_reply(False, eventtime)
                    #return False
                    
                else:
                    ## This is a recursive copy, so that groups get transferred whole
                    _treeview_copy_row(treeview, model, source_iter, target_iter, drop_position)
                    
                    ## Really should use the 'delete' signal, but very poorly documented
                    model.remove(source_iter)
                    drag_context.finish(True, False, eventtime)
                    
            else:
                print "  no drop"
        else:
            print "  Not GTK_TREE_MODEL_ROW -- no context.finish()"

    #############  Drag-n-Drop END #############  

    def treeview_row_activated(self, treeview, path, col):
        print "Activated Tree-Path (double-clicked) ", path
        model = treeview.get_model()
        iter = model.get_iter(path)
        row = model.get(iter, self.TREEVIEW_HIDDEN_TYPE_COL, self.TREEVIEW_HIDDEN_TEXT_COL) 
        if row[0] == self.TREEVIEW_ROW_TYPE_GROUP: # This is a group : double-clicked
            #row = self.treemodel.get(iter, self.TREEVIEW_HIDDEN_TEXT_COL) 
            print "Group ", row[1]
            if treeview.row_expanded(path):
                treeview.collapse_row(path)
            else:
                treeview.expand_row(path, False)
        else:                                   # This is a file : double-clicked
            #row = self.treemodel.get(iter, self.TREEVIEW_HIDDEN_TEXT_COL) 
            file = row[1]
            print "OPEN FILE     ", file
            filepath = os.path.join(self.config_base_directory, file)
            geany.document.open_file(filepath)
        
        
    """
    def treeview_select_cursor_row(self, tv, treepath, tvcolumn):
        pass
    """
        
    """
    def treeview_row_expanded(self, treeview, iter, path):
        #self.populate_treeview_children(iter, clear=False)
        print 'expanded treeview row'
        pass #Don't really care
    """


    """
    def render_icon_remote(self, tvcolumn, cell, model, iter):
        stock = model.get_value(iter, 0)
        pb = self.treeview.render_icon(stock, gtk.ICON_SIZE_MENU, None)
        cell.set_property('pixbuf', pb)
        return

    def load_project_config(self, path):
        pass

    def treeview_remove_children(self, parent_treeiter):
        print 'treeview_remove_children count before ' + str(self.treemodel.iter_n_children(parent_treeiter))
        if parent_treeiter is not None:
            treeiter=self.treemodel.iter_children(parent_treeiter)
            while treeiter:
                #print str(self.treemodel.get_value(treeiter, 0))+ ' remove child'
                self.treemodel.remove(treeiter)
                treeiter = self.treemodel.iter_next(treeiter)
        print 'treeview_remove_children count after ' + str(self.treemodel.iter_n_children(parent_treeiter))

    def treeview_get_children(self, parent_treeiter):
        children = []
        if parent_treeiter is not None:
            treeiter=self.treemodel.iter_children(parent_treeiter)
            while treeiter:
                children.append(treeiter)
                treeiter = self.treemodel.iter_next(treeiter)
        return children

    def treeview_print_children(self, parent_treeiter):
        print "\t"+str(self.treemodel.get_value(parent_treeiter, 0))
        if parent_treeiter is not None:
            treeiter=self.treemodel.iter_children(parent_treeiter)
            while treeiter:
                print "\t\t"+str(self.treemodel.get_value(treeiter, 0))
                treeiter = self.treemodel.iter_next(treeiter)

    def populate_treeview_children(self, parent, clear=True, match=None):
        #print 'populate_treeview_children '+str(parent)
        remove_treeiter = self.treeview_get_children(parent)

        path = self.treemodel.get_path(parent)
        if not path:
            return None

        filepath=self.get_treeview_path(path)+os.sep

        for filename in self.listdir_sort(filepath):
            path=filepath+filename
            if not self.is_allowed_file(filename):
                continue
            treeiter = self.append_treeview(self.treemodel, parent, filename, os.path.isdir(path))

            #list files under current path and populate folders, so we get expand markers
            if os.path.isdir(path):
                for filename3 in self.listdir_sort(path):
                    path+=filename3
                    if self.is_allowed_file(filename3):
                        self.append_treeview(self.treemodel, treeiter, filename3, os.path.isdir(path))

            if filename == self.selected_filename:
                treeselection = self.treeview.get_selection()
                treeselection.select_path(self.treemodel.get_path(treeiter))
                self.treeview.scroll_to_cell(self.treemodel.get_path(treeiter))

        for treeiter in remove_treeiter:
            if treeiter:
                self.treemodel.remove(treeiter)

    def populate_treeview(self,path=None):
        self.treemodel.clear()
        for path in self.root_folders:
            filename = os.path.dirname(path)
            treeview_node = self.append_treeview(self.treemodel, None, path)
            self.append_treeview_children(treeview_node, path)

    def append_treeview(self,model,parent,name,icon=1):
        myiter=model.insert_after(parent,None)
        #model.append_values(gtk.STOCK_FILE,name)
        #model.set_value(myiter,0,name)
        #print dir(model)
        #model.set_property('pixbuf', gtk.STOCK_DIRECTORY)
        #model.set_property('text', 'test')
        if icon==True:
            model.set_value(myiter,0,gtk.STOCK_DIRECTORY)
        else:
             model.set_value(myiter,0,gtk.STOCK_FILE)
        model.set_value(myiter,0,name)
        return myiter
    """
    
    """
    def fake_menu(self,*args):
        pass

    def show_configure(self):
       pass

    def count_spaces(self,line,count=1):
        result=''
        if line[count]==' ':
            count+=1
            result+=' '
        return result

    def get_treeview_path(self, path):
        treemodel = self.treemodel
        filepath = os.sep
        for item in range(1,len(path)+1):
            node = treemodel.get_iter(path[0:item])
            filepath += treemodel.get_value(node,0).strip(os.sep)+os.sep
        return filepath.rstrip(os.sep)

    def open_documents(self):
        for document in geany.document.get_documents_list():
            print document.file_name

    def document_changed(self, signal, document):
        print "document changed to "+str(document.file_name)
        self.update_selected_document(document.file_name)
        self.treeview.collapse_all()
        folders = []
        for root in self.root_folders:
            if document.file_name.startswith(root):
                path=document.file_name[len(root):].strip(os.sep)
                folders=[root.rstrip(os.sep)]
                for f in path.split(os.sep):
                    folders.append(f)

        count = 0
        treeiter=self.treemodel.iter_children(None)
        while treeiter:
            if folders[count]==self.treemodel.get_value(treeiter,0).rstrip(os.sep):
                #if we manage to expand the row then lets highlight the relevant file
                expandpath=self.treemodel.get_path(treeiter)
                self.treeview.expand_row(expandpath, False)
                treeiter=self.treemodel.iter_children(treeiter)
                count += 1
            else:
                treeiter = self.treemodel.iter_next(treeiter)

    #TODO expand as we match, populate children will then populate this list
    def append_treeview_children(self, parent, filepath, match=None):
        print '**** append_treeview_children ' + str(filepath) +' match = '+str(match) + ' '+ str(self.treemodel.get_value(parent, 0))
        matched_iter=None
        self.treeview_remove_children(parent)

        if os.path.isdir(filepath):
            for filename2 in self.listdir_sort(filepath):
                path=filepath+filename2
                if self.is_allowed_file(filename2):
                    treeiter = self.append_treeview(self.treemodel, parent, filename2, os.path.isdir(path))
                    if os.path.isdir(path):
                        for filename3 in self.listdir_sort(path):
                            path+=filename3
                            if self.is_allowed_file(filename3):
                                self.append_treeview(self.treemodel, treeiter, filename3, os.path.isdir(path))
                    if filename2 == match:
                        matched_iter = treeiter
        return matched_iter

    def is_allowed_file(self, filename):
        if any(filename.endswith(x) for x in (self.cfg.exclude_list)):
            return False
        return True

    def listdir_sort(self, path):
        files=[]
        directories=[]
        filelist=os.listdir(path)
        filelist.sort()
        for filename in reversed(filelist):
            if os.path.isfile(path+filename):
                files.append(filename)
            else:
                directories.append(filename)
        return files + directories


    def remove_child_nodes(self, node):
        treeiter=self.treemodel.iter_children(node)
        while self.treemodel.iter_is_valid(treeiter):
            self.treemodel.remove(treeiter)

    def remove_missing_children(self, node, value):
        treeiter=self.treemodel.iter_children(node)
        while self.treemodel.iter_is_valid(treeiter):
            if treemodel.get_value(treeiter, 0)!=value:
                self.treemodel.remove(treeiter)

    def update_selected_document(self, path):
        print '*** update_selected_document'
        if os.path.isdir(path):
            self.selected_filename = None
            self.selected_filepath = path
            self.selected_fullpath = path
        else:
            self.selected_filepath, self.selected_filename = os.path.split(path)
            self.selected_fullpath = path

        project_changed=False
        for root in self.root_folders:
            if path.startswith(root):
                folder = path[len(root):].split(os.sep)[0]
                if self.selected_project_folder != root+folder:
                    project_changed=True
                self.selected_project_folder = root+folder
                print 'project folder == ' +str(self.selected_project_folder)

    def folder_close_children(self, *args):
        if self.selected_filepath is None:
            return False

        for document in geany.document.get_documents_list():
            if document.file_name.startswith(self.selected_filepath):
                document.close()

    def file_create(self, *args):
        if self.selected_filepath is None:
            return False

        self.dialog_input_entry.set_text('')
        self.dialog_input.set_markup('Create File')
        self.dialog_input.show_all()
        response = self.dialog_input.run()
        newfilename = self.selected_filepath + os.sep + self.dialog_input_entry.get_text()
        self.dialog_input.hide_all()
        if response == gtk.RESPONSE_OK:
            with open(newfilename, 'w') as f:
                data = f.write('')
            geany.document.open_file(newfilename)


    def file_duplicate(self, *args):
        if self.selected_filename is None or self.selected_filepath is None:
            return False
        print self.selected_fullpath
        self.dialog_input_entry.set_text('')
        self.dialog_input.set_markup('Duplicate file')
        self.dialog_input.show_all()
        response = self.dialog_input.run()
        newfilename = self.selected_filepath + os.sep + self.dialog_input_entry.get_text()
        self.dialog_input.hide_all()
        if response == gtk.RESPONSE_OK:
            print 'response ok'
            if not os.path.isdir(self.selected_fullpath):
                print newfilename
                shutil.copyfile(self.selected_fullpath, newfilename)
                geany.document.open_file(newfilename)



    def file_rename(self, *args):
        if self.selected_filename is None or self.selected_filepath is None:
            return False

        self.dialog_input_entry.set_text(self.selected_filename)
        self.dialog_input.set_markup('Rename File/Folder')
        self.dialog_input.show_all()
        response = self.dialog_input.run()
        newfilename = self.selected_filepath + self.dialog_input_entry.get_text()
        self.dialog_input.hide_all()
        print 'from ' + str(self.selected_fullpath)
        print 'to ' + str(newfilename)
        if not os.path.exists(newfilename):
            print os.rename(self.selected_fullpath, newfilename)

    def file_remove(self, *args):
        print 'file_remove '+str(self.selected_fullpath)
        if not os.path.exists(self.selected_fullpath):
            return None
        if self.selected_filename is None or self.selected_filepath is None:
            return None
        self.dialog_confirm.set_markup('Remove File/Folder')
        self.dialog_confirm.show_all()
        response = self.dialog_confirm.run()
        self.dialog_confirm.hide_all()

        if response == gtk.RESPONSE_YES:
            print "unlinking "+str(self.selected_fullpath)
            print os.unlink(self.selected_fullpath)
            path = self.treemodel.get_path(self.selected_treeiter)
            parent = self.treemodel.get_iter(path[0:-1])
            self.populate_treeview_children(parent)
        print 'file_remove finished'

    def file_search(self, *args):
        print 'file_remove '+str(self.selected_fullpath)
        if not os.path.exists(self.selected_fullpath):
            return None
        geany.search.show_find_in_files_dialog(self.selected_fullpath)

    def project_configure(self, *args):
        self.configuration.load_config(self.selected_project_folder)
        print "loading configuration from "+self.selected_project_folder
        self.configuration.config.show()

    def show_configure(self):
        self.cfg.show()
        cfg = plugin_config(self.plugin_root)
        #xml = gtk.Builder()
        #xml.add_from_file(self.plugin_root+os.sep+'config.glade')
        #self.gui_config = {}
        #self.gui_config['window'] = xml.get_object('geanyprojectconfig')
        #self.gui_config['window'].show()


    """
    
    def cleanup(self):
        # destroy top level widgets to remove them from the UI/memory
        for widget in self.widget_destroy_stack:
            widget.destroy()


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
        #print "Attr: ",k
        m = attrib_matcher.match(k)
        if m:
            if m.group(2) != menu_current_title:
                menu_current_title = m.group(2)
                menubar_headers.append(dict(label=menu_current_title, submenu=[], ))
            label = m.group(4).replace('_',' ')
            menubar_headers[-1]['submenu'].append(dict( label=label, fn=k, ))
    #print menubar_headers
    
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
        #print "Attr: ",k
        m = attrib_matcher.match(k)
        if m:
            label = m.group(2).replace('_',' ')
            menu_headers.append(dict( label=label, fn=k, ))
    print menu_headers
    
    menu = gtk.Menu()
    for menu_header in menu_headers:
        menu = gtk.Menu()    # Don't need to show menus
        if menu_header['label'] == 'SEPARATOR':
            item = gtk.SeparatorMenuItem()
        else:
            item = gtk.MenuItem(menu_header['label'])
            item.connect_object("activate", getattr(class_with_menu_callbacks, menu_header['fn']), menu_header['fn'])
        item.show()
        menu.append(item)
    
    menu.show()
    return menu    


class xxx_plugin_config:
    folders = [os.path.expanduser('~/')]
    exclude_list = ('.pyc','~','.git','.svn','.bzr')

    config_path=os.path.join(geany.app.configdir, "plugins", "projects.conf")
    config_defaults={}
    config_defaults['exclude']=','.join(exclude_list)
    config_defaults['folders']=os.path.expanduser('~/')

    treeview_selected = None
    def __init__(self, path):
        xml = gtk.Builder()
        xml.add_from_file(path+os.sep+'config.glade')
        self.gui_config = {}
        self.gui_config['window'] = xml.get_object('geanyprojectconfig')

        self.gui_config['addlocation'] = xml.get_object('cfgaddlocation')
        self.gui_config['addlocation'].connect('activate', self.add_location)
        self.gui_config['addlocation'].connect('clicked', self.add_location)

        self.gui_config['locations'] = xml.get_object('cfglocations')
        self.gui_config['locations'].connect('row-activated', self.location_selection)
        self.gui_config['locations'].connect('button_press_event', self.show_menu)
        self.gui_config['locationslist'] = gtk.ListStore(str)
        self.gui_config['locations'].set_model(self.gui_config['locationslist'])

        column = gtk.TreeViewColumn("Locations")
        self.gui_config['locations'].append_column(column)

        cell = gtk.CellRendererText()
        column.pack_start(cell, False)
        column.add_attribute(cell, "text", 0)

        self.gui_config['selectlocations'] = xml.get_object('folderchooserdialog')
        #self.gui_config['selectlocations'].connect('activate', self.add_location)

        self.gui_config['saveconfig'] = xml.get_object('btnSaveConfig')
        self.gui_config['saveconfig'].connect('clicked', self.save_config)

        self.gui_config['excludeextension'] = xml.get_object('inputexcludeextensions')

        self.menu = gtk.Menu()
        self.menu_item = gtk.MenuItem("Remove Path")
        self.menu_item.connect("activate", self.remove_location)
        self.menu.append(self.menu_item)

        self.load_config()
        for folder in self.cfg.get('OPTIONS', 'folders').split('|'):
            self.gui_config['locationslist'].append([folder])


    def show(self):
        self.gui_config['window'].show()

    def show_menu(self, *args):
        self.menu.show()
        self.menu_item.show()
        self.menu.popup(None,None,None,1,0)

    def location_selection(self, tv, treepath, tvcolumn):
        treeiter = self.gui_config['locationslist'].get_iter(treepath)
        print 'location selection'
        print self.gui_config['locationslist'].get_value(treeiter, 0)

    def add_location(self, *args):
        self.gui_config['selectlocations'].show()
        response = self.gui_config['selectlocations'].run()
        filepath = self.gui_config['selectlocations'].get_filename()

        #if response == gtk.RESPONSE_OK:
        if filepath is not None:
            if os.path.isdir(filepath):
                self.folders.append(filepath)
                self.gui_config['locationslist'].append([filepath])
        self.gui_config['selectlocations'].hide()
        print self.folders

    def remove_location(self, *args):
        treeselection = self.gui_config['locations'].get_selection()
        (model, treeiter) = treeselection.get_selected()
        remove_value = self.gui_config['locationslist'].get_value(treeiter, 0)
        self.gui_config['locationslist'].remove(treeiter)
        for pos in xrange(0,len(self.folders)-1):
            if remove_value ==self.folders[pos]:
                del self.folders[pos]

    def load_config(self):
        self.cfg = SafeConfigParser(self.config_defaults)
        self.cfg.read(self.config_path)

        if not self.cfg.has_section('OPTIONS'):
            self.cfg.add_section('OPTIONS')
        print self.cfg.get('OPTIONS', 'exclude')
        self.exclude_list = self.cfg.get('OPTIONS', 'exclude').split(',')
        print self.exclude_list 
        self.folders = self.cfg.get('OPTIONS', 'folders').split('|')
        
        self.gui_config['excludeextension'].set_text(','.join(self.exclude_list))
        
        self.save_config()

    def save_config(self, *args):
        """
        snippets folder changed lets store the new location
        """
        print self.gui_config['excludeextension'].get_text()
        self.exclude_list = self.gui_config['excludeextension'].get_text().split(',')
        
        print self.folders
        exclude_setting=','.join(self.exclude_list)
        print exclude_setting
        self.cfg.set('OPTIONS', 'exclude', exclude_setting)
        self.cfg.set('OPTIONS', 'folders', '|'.join(self.folders))
        self.cfg.write(open(self.config_path, 'w'))

        self.gui_config['window'].hide()

