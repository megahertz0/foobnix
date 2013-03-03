#-*- coding: utf-8 -*-
'''
Created on Dec 20, 2010

@author: zavlab1
'''

import gtk
import thread
import gobject
import logging
import threading

from foobnix.fc.fc import FC
from foobnix.util import const
from foobnix.fc.fc_cache import FCache
from foobnix.helpers.menu import Popup
from foobnix.regui.state import LoadSave
from foobnix.util.key_utils import is_key
from foobnix.util.m3u_utils import m3u_writer
from foobnix.regui.model.signal import FControl
from foobnix.util.string_utils import crop_string
from foobnix.regui.model import FModel, FTreeModel
from foobnix.helpers.dialog_entry import FileSavingDialog
from foobnix.regui.treeview.playlist_tree import PlaylistTreeControl
from foobnix.util.file_utils import get_file_path_from_dnd_dropped_uri
from foobnix.helpers.my_widgets import tab_close_button, notetab_label,\
    ImageButton
from foobnix.util.mouse_utils import is_double_left_click, is_double_middle_click, \
    is_middle_click, is_rigth_click
from foobnix.regui.treeview.navigation_tree import NavigationTreeControl


class TabGeneral(gtk.Notebook, FControl, LoadSave):
    def __init__(self, controls):
        gtk.Notebook.__init__(self)
        FControl.__init__(self, controls)
        self.controls = controls
        self.set_properties("tab-expand", True)
        self.set_scrollable(True)
        self.save_lock = threading.Lock()
        self.connect("page-reordered", self.reorder_callback)
        add_button = ImageButton(gtk.STOCK_ADD, func=self.on_add_button_click, size=gtk.ICON_SIZE_BUTTON)
        add_button.show()
        self.set_action_widget(add_button, gtk.PACK_START)
        self.default_angle = 0
        self.navig = False if isinstance(self, NoteTabControl) else True
        
    def to_eventbox(self, widget, tab_child):
        event = gtk.EventBox()
        event.add(widget)
        event.set_visible_window(False)
        event.connect("button-press-event", self.on_button_press, tab_child)
        event = self.tab_menu_creator(event, tab_child)
        event.show_all()
        return event
    
    def on_add_button_click(self):
        '''abstract method'''
        pass
    
    def button(self, tab_child):
        if FC().tab_close_element == "button":
            return tab_close_button(func=self.on_delete_tab, arg=tab_child)
        elif FC().tab_close_element == "label":
            return notetab_label(func=self.on_delete_tab, arg=tab_child, angle=90)
    
    def create_notebook_content(self, beans=None, optimization=False):
        if not self.navig:
            treeview = PlaylistTreeControl(self.controls)
        else:
            treeview = NavigationTreeControl(self.controls)
         
        if beans: 
            if optimization:
                treeview.simple_append_all(beans)
            else:
                treeview.append_all(beans)
        return treeview
    
    def create_notebook_tab(self, treeview):
        treeview.scroll.show_all()
        return  treeview.scroll
    
    def get_full_tab_name(self, tab):
        tab_content = tab.get_child()
        return tab_content.full_name
    
    def set_full_tab_name(self, tab, name):
        tab_content = tab.get_child()
        tab_content.full_name = name
        
    def get_text_label_from_tab(self, tab, need_box_lenth=False):
        eventbox = self.get_tab_label(tab)
        box = eventbox.get_child()
        box_lenth = len(box.get_children())
        
        if type(box.get_children()[0]) == gtk.Label:
            label_object = box.get_children()[0]
        else: 
            label_object = box.get_children()[1]
            
        text_of_label = label_object.get_label()
        if need_box_lenth:
            return text_of_label, box_lenth
        else: return text_of_label
    
    def rename_tab(self, tab, new_full_name, name_list=None):
        try:
            logging.info("encoding of tab name is " + new_full_name)
            new_full_name = unicode(new_full_name) #convert from any encoding in ascii
            logging.info("encoding finished " + new_full_name)
        except:
            logging.warn("problem of encoding definition for tab name is occured")
        self.set_full_tab_name(tab, new_full_name)
        new_label_text = crop_string(new_full_name, FC().len_of_tab)
        self.get_tab_label(tab).activate()
        tab.get_child().label.set_text(new_label_text + ' ')
        if name_list:
            n = self.page_num(tab)
            name_list[n] = new_label_text
        self.on_save_tabs()
                
    def on_rename_tab(self, tab, angle=0, name_list=None):
               
        old_name = self.get_full_tab_name(tab)
        
        window = gtk.Window()
        window.set_decorated(False)
        window.set_position(gtk.WIN_POS_MOUSE)
        window.set_border_width(5)
        entry = gtk.Entry()
        entry.set_text(old_name)
        entry.show()
        
        def on_key_press(window, e):
            if is_key(e, 'Escape'):
                window.hide()
                entry.set_text(old_name)
            elif is_key(e, 'Return'):
                window.hide()
                new_full_name = entry.get_text()
                if new_full_name:
                    self.rename_tab(tab, new_full_name, name_list)
        
        def on_focus_out(window, e):
            window.hide()
            entry.set_text(old_name)
            
        window.connect("key_press_event", on_key_press)
        window.connect("focus-out-event", on_focus_out)
        window.add(entry)
        window.show_all()
        
    def crop_all_tab_names(self):
        number_of_tabs = self.get_n_pages()
        if number_of_tabs > 0:
            min = 1 if self.navig else 0
            for page in xrange(number_of_tabs - 1, min, -1):
                tab = self.get_nth_page(page)
                self.rename_tab(tab, tab.get_child().full_name)
    
    def append_tab(self, name=_("Empty tab"), beans=None, optimization=False):
        def task():
            self._append_tab(name, beans, optimization)
        gobject.idle_add(task)
        
        
    def _append_tab(self, full_name=_("Empty tab"), beans=None, optimization=False):
        logging.info("append new tab")
        self.last_notebook_page = full_name
        try:
            logging.info("encoding of tab name is " + full_name)
            full_name = unicode(full_name) #convert from any encoding in ascii
            logging.info("encoding finished " + full_name)
        except:
            logging.warn("problem of encoding definition for tab name is occured")
        
        visible_name = crop_string(full_name, FC().len_of_tab)
        
        tab_content = self.create_notebook_content(beans, optimization)
        tab_content.label.set_angle(self.default_angle)
        tab = self.create_notebook_tab(tab_content)
        if self.navig:
            tab_content.label.set_angle(90)
       
        tab_content.full_name = full_name
        
        """label"""
        if visible_name.endswith(" "):
            tab_content.label.set_text(visible_name)
        else:
            tab_content.label.set_text(visible_name + " ")
        tab_content.label.show()    
        
        if FC().tab_position == "left" or self.navig:
            """container Vertical Tab"""
            box = gtk.VBox(False, 0)
            box.show()
            if FC().tab_close_element:
                box.pack_start(self.button(tab), False, False, 0)
            box.pack_end(tab_content.label, False, False, 0)
        else: 
            """container Horizontal Tab"""
            box = gtk.HBox(False, 0)
            box.show()
            if FC().tab_close_element:
                box.pack_end(self.button(tab), False, False, 0)
            box.pack_start(tab_content.label, False, False, 0)
            
        eventbox = self.to_eventbox(box, tab)
                        
        """append tab"""
        self.prepend_page(tab, eventbox)
        
        self.set_tab_reorderable(tab, True)
        
        self.show_all()
        self.set_current_page(0) #only after show_all()
        if not self.navig:
            if self.get_n_pages() > FC().count_of_tabs:
                self.remove_page(self.get_n_pages() - 1)

    def on_delete_tab(self, child):
        n = self.page_num(child)
        if self.get_n_pages() == 1:
            return
        self.remove_page(n)
        if self.navig:
            del FCache().tab_names[n]
            del FCache().music_paths[n]
            del FCache().cache_music_tree_beans[n]
        self.on_save_tabs()
            
    def get_current_tree(self):
        n = self.get_current_page()
        tab_child = self.get_nth_page(n)
        if tab_child:
            return tab_child.get_child()
    
    def on_save_tabs(self):
        def task():
            self.save_lock.acquire()
            try:
                self.save_tabs()
                FCache().save()
            finally:
                if self.save_lock.locked():
                    self.save_lock.release()
        try:
            threading.Thread(target=task, args=()).start()
        except Exception, e:
            print "Exception: %s" % str(e)
    
TARGET_TYPE_URI_LIST = 80
dnd_list = [('text/uri-list', 0, TARGET_TYPE_URI_LIST)]


class NoteTabControl(TabGeneral):
    def __init__(self, controls):
        TabGeneral.__init__(self, controls)
                
        self.last_notebook_page = ""
        self.active_tree = None
        self.set_show_border(True)
        self.stop_handling = False
        self.loaded = False
                
        self.connect("button-press-event", self.on_button_press) 
        self.connect('drag-data-received', self.on_system_drag_data_received)
        self.connect('switch-page', self.equalize_columns_size)
        
        self.drag_dest_set(gtk.DEST_DEFAULT_MOTION | gtk.DEST_DEFAULT_DROP, dnd_list, gtk.gdk.ACTION_MOVE | gtk.gdk.ACTION_COPY) #@UndefinedVariable
        
        if not FCache().cache_pl_tab_contents:
            self.append_tab()
    
    def reorder_callback(self, notebook, child, new_page_num):
        self.on_save_tabs()
        
    def on_system_drag_data_received(self, widget, context, x, y, selection, target_type, timestamp):
        if target_type == TARGET_TYPE_URI_LIST:
            uri = selection.data.strip('\r\n\x00')
            uri_splitted = uri.split() # we may have more than one file dropped
            paths = []
            for uri in uri_splitted:
                path = get_file_path_from_dnd_dropped_uri(uri)
                paths.append(path)
            
            self.controls.check_for_media(paths)
                    
    def on_button_press(self, w, e, tab_content=None):
        """there were two problems in the handler:
        1. when you click on eventbox, appears extra the signal from the notebook
        2. when double-clicking, the first click is handled"""
        
        if type(w) == gtk.EventBox: 
            self.stop_handling = True
            #add delay in the background

            def start_handling():
                self.stop_handling = False
            threading.Timer(0.3, start_handling).start()
        
        #Get rid of the parasitic signal    
        if self.stop_handling and type(w) != gtk.EventBox: 
            return
        
        #handling of double middle click
        if is_double_middle_click(e) and type(w) == gtk.EventBox:
            #this variable helps to ignore first click, when double-clicking
            self.val = False
            self.on_rename_tab(tab_content)
                    
        #handling of middle click    
        elif is_middle_click(e):
            self.val = True
            
            def midclick():
                if self.val:
                    if type(w) == gtk.EventBox:
                        n = self.page_num(tab_content)
                        self.remove_page(n)
                    else:
                        self.empty_tab()
            #add delay in the background
            #for check (is second click or not)
            threading.Timer(0.5, midclick).start()
                        
        #to show context menu       
        elif is_rigth_click(e):
            if type(w) == gtk.EventBox:
                w.menu.show_all()
                w.menu.popup(None, None, None, e.button, e.time)    

    def tab_menu_creator(self, widget, tab_child):   
        widget.menu = Popup()
        widget.menu.add_item(_("Rename tab"), "", lambda: self.on_rename_tab(tab_child, self.default_angle), None)
        widget.menu.add_item(_("Save playlist as"), gtk.STOCK_SAVE_AS, lambda: self.on_save_playlist(tab_child))
        widget.menu.add_item(_("Close tab"), gtk.STOCK_CLOSE, lambda: self.on_delete_tab(tab_child), None)
        widget.show()
        return widget   
        
    def create_plus_tab(self):
        if self.get_n_pages() > 1:
            self.remove_page(self.page_num(self.plus_tab_child))
        append_label = notetab_label(func=self.empty_tab, arg=None, angle=0, symbol="+")
        self.plus_tab_child = notetab_label(func=self.empty_tab, arg=None, angle=0, symbol="Click me")
        self.prepend_page(self.plus_tab_child, append_label)
      
    def on_add_button_click(self):
        self._append_tab()
        
    def set_tab_left(self):
        logging.info("Set tabs Left")
        self.set_tab_pos(gtk.POS_LEFT)
        self.default_angle = 90
        self.set_show_tabs(True)
        for page in xrange(self.get_n_pages() - 1, 0, -1):
            tab = self.get_nth_page(page)
            vbox = gtk.VBox()
            label = tab.get_child().label
            label.set_angle(self.default_angle)
            
            old_box = label.get_parent()
            old_box.remove(label)
            
            if FC().tab_close_element:
                vbox.pack_start(self.button(tab), False, False, 0)
            vbox.pack_end(label, False, False, 0)
            vbox.set_child_visible(True)
            vbox.show_all()
            event = self.to_eventbox(vbox, tab)
            self.set_tab_label(tab, event)
            
    def set_tab_top(self):
        logging.info("Set tabs top")
        self.set_tab_pos(gtk.POS_TOP)
        self.default_angle = 0
        self.set_show_tabs(True)
        for page in xrange(self.get_n_pages() - 1, 0, -1):
            tab = self.get_nth_page(page)
            hbox = gtk.HBox()
            label = tab.get_child().label
            label.set_angle(self.default_angle)
            
            old_box = label.get_parent()
            old_box.remove(label)
            
            if FC().tab_close_element:
                hbox.pack_end(self.button(tab), False, False, 0)
            hbox.pack_start(label, False, False, 0)
            hbox.set_child_visible(True)
            hbox.show_all()
            event = self.to_eventbox(hbox, tab)
            self.set_tab_label(tab, event)
        
    def set_tab_no(self):
        logging.info("Set tabs no")
        self.set_show_tabs(False)

    def on_save_playlist(self, tab_child):
        name = self.get_text_label_from_tab(tab_child)
        current_name = name.strip() + ".m3u"
        tree = tab_child.get_child()

        def func(filename, folder):
            beans = tree.get_all_beans()
            if beans:
                paths = []
                for bean in beans:
                    if bean.is_file:
                        if not bean.path or bean.path.startswith("http://"):
                            paths.append("##" + bean.text)
                        else:
                            paths.append(bean.path)

            else:
                logging.warning(_("It's need not empty playlist"))
            m3u_writer(filename, folder, paths)
        
        FileSavingDialog(_("Choose folder to save playlist"), func, current_folder=FCache().last_music_path, current_name = current_name) 

    def on_load(self):
        if FC().tab_position == "no": 
            self.set_tab_no()
        elif FC().tab_position == "left": 
            self.set_tab_left()
        else: 
            self.set_tab_top()

        for page in xrange(0, len(FCache().cache_pl_tab_contents)):
            if FCache().cache_pl_tab_contents[page] == []:
                self._append_tab(FCache().tab_pl_names[page])
                continue
            self._append_tab(FCache().tab_pl_names[page])
            model_len = len(FTreeModel().__dict__)
            cache_len = len(FCache().cache_pl_tab_contents[page][0])
            
            for row in FCache().cache_pl_tab_contents[page]:
                if model_len > cache_len:
                    for i in xrange(abs(model_len - cache_len)):                        
                        row.append((None, None))
                elif model_len < cache_len:
                    for i in xrange(abs(model_len - cache_len)):                        
                        del row[-1]

                self.get_current_tree().model.append(None, row)

        self.set_current_page(FC().pl_selected_tab)
        self.loaded = True
            
    def on_save(self):
        pass
    
    def save_tabs(self):
        number_music_tabs = self.get_n_pages()
        FCache().cache_pl_tab_contents = []
        FCache().tab_pl_names = []
        if number_music_tabs > 0:
            for tab_number in xrange(self.get_n_pages() - 1, -1, -1):
                self.save_nth_tab(tab_number)

    def save_nth_tab(self, tab_number):
        tab = self.get_nth_page(tab_number)
        pl_tree = tab.get_child()
        FCache().cache_pl_tab_contents.append([list(row) for row in pl_tree.model])
        FCache().tab_pl_names.append(self.get_full_tab_name(tab))
        for i, column in enumerate(pl_tree.get_columns()):
            FC().columns[column.key][1] = i
            if column.get_width() > 1: #to avoid recording of zero width in config
                FC().columns[column.key][2] = column.get_width()

    def on_quit(self):
        self.on_save_tabs()

    def equalize_columns_size(self, notebook, page_pointer, page_num):
        if self.loaded: #because the "switch-page" event is fired after every tab's addtion
            FC().pl_selected_tab = page_num
        try:
            old_pl_tree_columns = self.get_current_tree().get_columns()
            new_pl_tree_columns = self.get_nth_page(page_num).get_child().get_columns()
            for old_pl_tree_column, new_pl_tree_column in zip(old_pl_tree_columns, new_pl_tree_columns):
                gobject.idle_add(new_pl_tree_column.set_fixed_width,old_pl_tree_column.get_width())
        except AttributeError:
            pass
    
    def empty_tab(self, *a):
        self.append_tab("Foobnix", [])
    
    def append_all(self, beans):
        self.get_current_tree().append_all(beans)
    
    def next(self):
        bean = self.get_current_tree().next()
        return bean

    def prev(self):
        bean = self.get_current_tree().prev()
        return bean
    
    def set_playlist_tree(self):
        self.get_current_tree().set_playlist_tree()

    def set_playlist_plain(self):
        self.get_current_tree().set_playlist_plain()
