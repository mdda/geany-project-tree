import os, sys
import re
import shutil
import gtk, glib
import gobject
import geany

import ConfigParser
from datetime import datetime

sys.path.append(os.path.dirname(__file__))

#from config.loader import config_handler

#class plugin_config:
#    pass

class ProjectTree(geany.Plugin):
    __plugin_name__ = "Project Tree"
    __plugin_version__ = "0.1"
    __plugin_description__ = "(Yet Another) Alternative to treeview and project view"
    __plugin_author__ = "Martin Andrews <martin@redcatlabs.com>"

    plugin_root = os.path.dirname(__file__)
    widget_destroy_stack = []
    
    config_base_directory = None
    config_sub_directory = ".geany"
    
    config_project_file  = "project.ini"
    config_project_file_readonly = "project_sample.ini"
    config_session_file  = "session.ini"
    config_session_file_initial  = "session_default.ini"

    #use this to decide what items to show in the menu when right clicking
    #current_treedepth=0
    #root_folders=[]
    #root_folders=['/var/www/',os.path.expanduser('~/')+'Ubuntu One/python/']

    #selected_filename = None
    #selected_fullpath = None
    #selected_filepath = None
    #selected_treeiter = None
    #selected_project_folder = None

    #configuration = config_handler(geany.general_prefs.default_open_path)
    #database = mysql_handler(geany.general_prefs.default_open_path)
    #browser = browser_handler()
    #remote_files = sftp_handler(geany.general_prefs.default_open_path)

    #cfg = plugin_config(plugin_root)
    #root_folders = cfg.folders

    def __init__(self):
        self.clipboard=gtk.clipboard_get()

        if True:  ## Set up the pop-up menus
            ## Click menu : empty space : AddGroup, AddCurrentFile
            self.menu_empty_fill()
            
            ## Right-Click menu : file  : AddGroup, AddCurrentFile, RemoveFile
            self.menu_file_fill()
            
            ## Right-Click menu : group : AddGroup, RemoveGroup, RenameGroup, AddCurrentFile
            self.menu_group_fill()
            
            self.widget_destroy_stack.extend([self.menu_empty, self.menu_file, self.menu_group, ])

        if True:  ## Set up a reusable, generic question/answer dialog box
            # gtk.BUTTONS_YES_NO
            self.dialog_confirm = gtk.MessageDialog(None,gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,gtk.MESSAGE_QUESTION,gtk.BUTTONS_YES_NO,None)
            self.dialog_input   = gtk.MessageDialog(None,gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,gtk.MESSAGE_QUESTION,gtk.BUTTONS_OK,None)
            self.dialog_input_entry = gtk.Entry()
            
            hbox = gtk.HBox()
            hbox.pack_start(gtk.Label("Name:"), False, 5, 5)
            hbox.pack_end(self.dialog_input_entry)
            self.dialog_input.vbox.pack_end(hbox, True, True, 0)
        
            self.widget_destroy_stack.extend([self.dialog_input, ])
            
        if True:  ## Set up the side-bar
            self.treemodel = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
            #setup treeview and treestore model
            #self.treemodel.connect("cursor-changed", self.populate_treeview)
            
            self.treeview = gtk.TreeView(self.treemodel)

            self.treeview.connect('row-activated', self.on_selection)
            self.treeview.connect("row-expanded", self.on_expand_treeview)
            self.treeview.connect('button_press_event', self.treeview_menu)
            #self.treeview.set_headers_visible(True)
            self.treeview.set_headers_visible(False)

            #~ fontT = pango.FontDescription("serif light Oblique 8")
            #~ fontO = pango.FontDescription("serif bold 8")
            #~ treeView.cell[2].set_property('font-desc', fontT)
            #~ treeView.cell[3].set_property('font-desc', fontO)

            #column1.pack_start(text_renderer, False)
            #column1.set_resizable(False)

            pix_renderer = gtk.CellRendererPixbuf()
            text_renderer= gtk.CellRendererText()

            column1=gtk.TreeViewColumn("Tree Layout Options", text_renderer, text=0)
            #column1.set_title('Icons & Text')
            ## This is for setting an icon - which we won't be showing anyway
            #column1.set_cell_data_func(pix_renderer, self.render_icon_remote)

            #column1.add_attribute(pix_renderer, 'pixbuf', 0)
            #column1.set_attributes(pix_renderer, text=0)
            #column1.pack_start(pix_renderer, True)

            ## Unnecessary?
            #column1.add_attribute(text_renderer, 'text', 0)
            #column1.set_attributes(text_renderer, text=0)
            #column1.pack_start(text_renderer, True)

            #column2=gtk.TreeViewColumn("Project List",pix_renderer,text=1)
            #column2.set_resizable(True)
            #column2.pack_start(pix_renderer,True)

            self.treeview.append_column(column1)
            #self.treeview.append_column(column2)
            self.treeview.show()

            #put treeview in a scrolled window so we can move up and down with a scrollbar
            self.scrolledwindow=gtk.ScrolledWindow()
            self.scrolledwindow.add(self.treeview)
            self.scrolledwindow.show()

            #homogeneous = False, spacing = 0
            box = gtk.VBox(False, 0)
            ##expand, fill, padding
            box.pack_start(self.scrolledwindow, True, True, 0)
            box.show()
            
            label = gtk.Label("ProjectTree")
            
            geany.main_widgets.sidebar_notebook.append_page(box, label)
            #geany.main_widgets.message_window_notebook.append_page(self.database.gui, labelMYSQL)
            #self.browser.browser_tab = geany.main_widgets.message_window_notebook.append_page(self.browser.gui, labelBrowser)
            #geany.main_widgets.message_window_notebook.append_page(self.sftp.gui, labelSFTP)

            # keep track of widgets to destroy in plugin_cleanup()
            self.widget_destroy_stack.extend([box, label, ])

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
            ## Load in self.config_project_file_readonly
            project_config_ini = os.path.join(self.config_base_directory, self.config_sub_directory, self.config_project_file_readonly)
            self._load_project_tree(project_config_ini)
            
            ## Load in session information
            ## TODO
            pass
        
        geany.signals.connect('document-activate', self.document_changed)
        #self.detector=detect()
        
        
    def _load_project_tree(self, config_file):
        with open(config_file) as fin:
            config = ConfigParser.SafeConfigParser()
            config.readfp(fin)
            #print "Sections", config.sections()
            if config.has_section('.'):
                print "Got Root!"
                self.treemodel.clear()
                self._load_project_tree_branch(config, '.', None)
                
                            
    def _load_project_tree_branch(self, config, section, parent):
        ## Create a nice dictionary of stuff from this section - each integer(sorted) can contain several entries
        key_matcher = re.compile("(\d+)-?(\S*)")
        d=dict()
        for k,v in config.items(section):
            print "('%s', '%s')" % (k, v)
            m = key_matcher.match(k)
            if m:
                order = int(m.group(1))
                if order not in d:
                    d[order]=dict()
                d[order][m.group(2)] = v
            
        for k,vd in sorted(d.iteritems()):  # Here, vd is dictionary of data about each 'k' item
            if '' in vd: # This is a file (the default ending)
                print "Got a file"
                f = vd['']
                ## Add the file to the tree
                #iter = self.treemodel.insert_after(None,None)
                #self.treemodel.set_value(iter, 0, os.path.basename(f))
                #self.treemodel.set_value(iter, 1, f)
                
                iter = self.treemodel.append(parent, (os.path.basename(f), f))
                # No need to store this 'iter' - can easily append after
                
            else:  # This is something special
                if 'group' in vd:
                    g = vd['group']
                    print "Got a group : %s" % (g,)
                    ## Add the  group to the tree, and recursively go after that section...
                    iter = self.treemodel.append(parent, (g, g))
                    ### Descend with parent=iter
                    self._load_project_tree_branch(config, section+'/'+g, iter)
                    
        

    def _menu_item_add_connected(self, menu, title, action):
        menu_item = gtk.MenuItem(title)
        menu_item.connect("activate", action)
        menu_item.show()
        menu.append(menu_item)
    
    def menu_empty_fill(self):
        ## Right-Click menu : empty space : AddGroup, AddCurrentFile
        menu = gtk.Menu()
        self._menu_item_add_connected(menu, "TEST", self.menu_empty_action_test)
        self._menu_item_add_connected(menu, "Add Group", self.tree_add_group)
        self._menu_item_add_connected(menu, "Add Current File", self.tree_add_current_file)
        self.menu_empty = menu

    def menu_file_fill(self):
        ## Right-Click menu : file  : AddGroup, AddCurrentFile, RemoveFile
        menu = gtk.Menu()
        
        self.menu_file = menu
        
    def menu_group_fill(self):
        ## Right-Click menu : group : AddGroup, RemoveGroup, RenameGroup, AddCurrentFile
        menu = gtk.Menu()
        
        self.menu_group = menu


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

    """
    def menu_project(self):
        self.popup_project_menu=[]

        menu_item = gtk.MenuItem("Find in Files")
        menu_item.connect("activate", self.file_search)
        self.popup_project_menu.append(menu_item)

        menu_item = gtk.MenuItem("Close Child Documents")
        menu_item.connect("activate", self.folder_close_children)
        self.popup_project_menu.append(menu_item)

        menu_item = gtk.MenuItem("Project Config")
        menu_item.connect("activate", self.project_configure)
        self.popup_project_menu.append(menu_item)

        menu_item = gtk.MenuItem("Reload List")
        menu_item.connect("activate", self.fake_menu)
        self.popup_project_menu.append(menu_item)

        menu_item = gtk.MenuItem("Create File")
        menu_item.connect("activate", self.file_create)
        self.popup_project_menu.append(menu_item)

        menu_item = gtk.MenuItem("Create Directory")
        menu_item.connect("activate", self.fake_menu)
        self.popup_project_menu.append(menu_item)

        for item in self.popup_project_menu:
            self.menu.append(item)

    def menu_folders(self):
        self.popup_folder_menu=[]

        menu_item = gtk.MenuItem("Find in Files")
        menu_item.connect("activate", self.file_search)
        self.popup_folder_menu.append(menu_item)

        menu_item = gtk.MenuItem("Reload List")
        menu_item.connect("activate", self.fake_menu)
        self.popup_folder_menu.append(menu_item)

        menu_item = gtk.MenuItem("Create File")
        menu_item.connect("activate", self.file_create)
        self.popup_folder_menu.append(menu_item)

        menu_item = gtk.MenuItem("Close Child Documents")
        menu_item.connect("activate", self.folder_close_children)
        self.popup_folder_menu.append(menu_item)

        menu_item = gtk.MenuItem("Create Directory")
        menu_item.connect("activate", self.fake_menu)
        self.popup_folder_menu.append(menu_item)

        for item in self.popup_folder_menu:
            self.menu.append(item)

    def menu_files(self):
        self.popup_file_menu=[]
        menu_item = gtk.MenuItem("Remove file")
        menu_item.connect("activate", self.file_remove)
        self.popup_file_menu.append(menu_item)

        menu_item = gtk.MenuItem("Duplicate File")
        menu_item.connect("activate", self.file_duplicate)
        self.popup_file_menu.append(menu_item)

        menu_item = gtk.MenuItem("Rename File")
        menu_item.connect("activate", self.file_rename)
        self.popup_file_menu.append(menu_item)

        for item in self.popup_file_menu:
            self.menu.append(item)
    """
    
    #show hide menu items dependent on treeview selection depth
    def show_popup_menu(self, filepath, path=()):
        depth = len(path)
        self.update_selected_document(filepath)
        #self.selected_treeiter = self.treemodel.get_iter(path)

        for item in self.popup_project_menu:
            item.hide()

        for item in self.popup_folder_menu:
            item.hide()

        for item in self.popup_file_menu:
            item.hide()
            
        self.menu.show()
        self.menu.popup(None,None,None,1,0)
        if depth==1:
            print 'menu 1'
            for item in self.popup_project_menu:
                item.show()
            return None

        if depth==2:
            print 'menu 2'
            for item in self.popup_project_menu:
                item.show()
            return None

        if os.path.isdir(filepath):
            print 'folder menu '
            for item in self.popup_folder_menu:
                print item
                item.show()
        else:
            print 'file menu '
            for item in self.popup_file_menu:
                item.show()
                
        return None



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

    #treeview menu also grab selected item values / path
    def treeview_menu(self, tv, event):
        subpath=[]
        #print "event.button=%d" % (event.button,)
        
        #get current treeview selection
        treemodel=tv.get_model()
        tree_selection=tv.get_selection()
        treestore, path = tree_selection.get_selected_rows()
        
        if event.button == 3:  # Right click
            #print "len(path)=%d" % (len(path),)
            if len(path)>0:  # Something actually clicked on
                filepath = self.get_treeview_path(path[0])
                self.show_popup_menu(filepath, path[0])
            else:
                # Empty space clicked on : Don't care which button
                #self.show_popup_menu('asdasd', 'tyrtrtyy')
                print "Popup menu_empty"
                self.menu_empty.show()
                self.menu_empty.popup(None,None,None,1,0)

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

    def on_selection(self, tv, treepath, tvcolumn):
        filepath = self.get_treeview_path(treepath)
        if not os.path.isdir(filepath):
            geany.document.open_file(filepath)
        print 'activated'

    def get_treeview_path(self, path):
        treemodel = self.treemodel
        filepath = os.sep
        for item in range(1,len(path)+1):
            node = treemodel.get_iter(path[0:item])
            filepath += treemodel.get_value(node,0).strip(os.sep)+os.sep
        return filepath.rstrip(os.sep)

    def on_expand_treeview(self, tv, treeiter, treepath):
        self.populate_treeview_children(treeiter, clear=False)

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
        """ Wooo        
        self.configuration.load_config(self.selected_project_folder)


        if self.configuration.connections.get('development', None):
            print self.configuration.config_site_address
            print self.configuration.connections['development']['url-address']
            if project_changed==True:
                self.browser.open_url(self.configuration.connections['development']['url-address'])
            else:
                self.browser.reload_url()
        """

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


    def cleanup(self):
        # destroy top level widgets to remove them from the UI/memory
        for widget in self.widget_destroy_stack:
            widget.destroy()



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

