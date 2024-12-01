import os
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, GdkPixbuf

class GameConfigWindow(Gtk.Dialog):
    def __init__(self, parent, game, icon_manager, callback):
        super().__init__(
            title=f"Configure {game.name}",
            transient_for=parent,
            modal=True,
            destroy_with_parent=True
        )
        
        self.game = game
        self.icon_manager = icon_manager
        self.callback = callback
        self.parent = parent
        
        # Get the app instance to access global settings
        self.app = parent.get_application()
        
        # Set window size
        self.set_default_size(500, -1)
        
        # Add CSS styling
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .settings-header {
                padding: 12px;
                border-bottom: 1px solid alpha(currentColor, 0.2);
                background: alpha(currentColor, 0.05);
            }
            .settings-title {
                font-size: 20px;
                font-weight: bold;
            }
            .settings-subtitle {
                font-size: 12px;
                opacity: 0.7;
            }
            .settings-group {
                margin-top: 6px;
                margin-bottom: 6px;
                padding: 12px;
                border-radius: 6px;
                background: alpha(currentColor, 0.03);
            }
            .settings-group-title {
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 6px;
            }
            .settings-item {
                padding: 6px;
                border-radius: 4px;
            }
            .settings-item:hover {
                background: alpha(currentColor, 0.05);
            }
            .settings-description {
                font-size: 12px;
                opacity: 0.7;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Create content area
        content = self.get_content_area()
        content.set_spacing(0)  # We'll handle spacing with CSS
        
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.add_css_class('settings-header')
        
        # Icon
        icon = Gtk.Image.new_from_icon_name('applications-games-symbolic')
        icon.set_pixel_size(32)
        header.append(icon)
        
        # Title section
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title = Gtk.Label(label=game.name)
        title.add_css_class('settings-title')
        title.set_halign(Gtk.Align.START)
        subtitle = Gtk.Label(label="Configure game-specific launch options (overrides global settings)")
        subtitle.add_css_class('settings-subtitle')
        subtitle.set_halign(Gtk.Align.START)
        title_box.append(title)
        title_box.append(subtitle)
        header.append(title_box)
        
        content.append(header)
        
        # Main content box with scrolling
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_propagate_natural_height(True)
        content.append(scrolled)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        scrolled.set_child(main_box)
        
        # Game Info group
        info_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        info_group.add_css_class('settings-group')
        
        info_title = Gtk.Label(label="Game Information")
        info_title.add_css_class('settings-group-title')
        info_title.set_halign(Gtk.Align.START)
        info_group.append(info_title)
        
        # Game name
        name_item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        name_item.add_css_class('settings-item')
        
        name_label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        name_label = Gtk.Label(label="Game Name")
        name_label.set_halign(Gtk.Align.START)
        name_desc = Gtk.Label(label="The name that will be displayed in the launcher")
        name_desc.add_css_class('settings-description')
        name_desc.set_halign(Gtk.Align.START)
        name_label_box.append(name_label)
        name_label_box.append(name_desc)
        name_item.append(name_label_box)
        
        self.name_entry = Gtk.Entry()
        self.name_entry.set_text(game.name)
        self.name_entry.set_hexpand(True)
        self.name_entry.add_css_class('settings-description')
        name_item.append(self.name_entry)
        
        info_group.append(name_item)
        
        # Game path
        path_item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        path_item.add_css_class('settings-item')
        
        path_label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        path_label = Gtk.Label(label="Game Path")
        path_label.set_halign(Gtk.Align.START)
        path_desc = Gtk.Label(label="Location of the game executable")
        path_desc.add_css_class('settings-description')
        path_desc.set_halign(Gtk.Align.START)
        path_label_box.append(path_label)
        path_label_box.append(path_desc)
        path_item.append(path_label_box)
        
        path_value = Gtk.Label(label=game.file_path)
        path_value.set_hexpand(True)
        path_value.set_halign(Gtk.Align.START)
        path_value.add_css_class('settings-description')
        path_item.append(path_value)
        
        info_group.append(path_item)
        
        main_box.append(info_group)
        
        # Launch Options group
        options_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        options_group.add_css_class('settings-group')
        
        options_title = Gtk.Label(label="Launch Options")
        options_title.add_css_class('settings-group-title')
        options_title.set_halign(Gtk.Align.START)
        options_group.append(options_title)
        
        # Get current flags
        current_flags = {}
        for game_config in self.get_transient_for().get_application().config['games']:
            if isinstance(game_config, dict) and game_config.get('path') == game.file_path:
                current_flags = game_config.get('flags', {})
                break
        
        # Gamemode toggle
        gamemode_item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        gamemode_item.add_css_class('settings-item')
        
        gamemode_label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        gamemode_label_box.set_hexpand(True)
        gamemode_label = Gtk.Label(label="Enable Gamemode")
        gamemode_label.set_halign(Gtk.Align.START)
        gamemode_desc = Gtk.Label(label="Optimize system performance while playing")
        gamemode_desc.add_css_class('settings-description')
        gamemode_desc.set_halign(Gtk.Align.START)
        gamemode_label_box.append(gamemode_label)
        gamemode_label_box.append(gamemode_desc)
        gamemode_item.append(gamemode_label_box)
        
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        switch_box.set_halign(Gtk.Align.END)
        self.gamemode_switch = Gtk.Switch()
        self.gamemode_switch.set_active(current_flags.get('gamemode', False))
        self.gamemode_switch.set_valign(Gtk.Align.CENTER)
        switch_box.append(self.gamemode_switch)
        gamemode_item.append(switch_box)
        
        options_group.append(gamemode_item)
        
        # MangoHud toggle
        mangohud_item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        mangohud_item.add_css_class('settings-item')
        
        mangohud_label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        mangohud_label_box.set_hexpand(True)
        mangohud_label = Gtk.Label(label="Enable MangoHud")
        mangohud_label.set_halign(Gtk.Align.START)
        mangohud_desc = Gtk.Label(label="Display performance metrics overlay")
        mangohud_desc.add_css_class('settings-description')
        mangohud_desc.set_halign(Gtk.Align.START)
        mangohud_label_box.append(mangohud_label)
        mangohud_label_box.append(mangohud_desc)
        mangohud_item.append(mangohud_label_box)
        
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        switch_box.set_halign(Gtk.Align.END)
        self.mangohud_switch = Gtk.Switch()
        self.mangohud_switch.set_active(current_flags.get('mangohud', False))
        self.mangohud_switch.set_valign(Gtk.Align.CENTER)
        switch_box.append(self.mangohud_switch)
        mangohud_item.append(switch_box)
        
        options_group.append(mangohud_item)
        
        # Fullscreen toggle
        fullscreen_item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        fullscreen_item.add_css_class('settings-item')
        
        fullscreen_label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        fullscreen_label_box.set_hexpand(True)
        fullscreen_label = Gtk.Label(label="Fullscreen")
        fullscreen_label.set_halign(Gtk.Align.START)
        fullscreen_desc = Gtk.Label(label="Run the game in fullscreen mode")
        fullscreen_desc.add_css_class('settings-description')
        fullscreen_desc.set_halign(Gtk.Align.START)
        fullscreen_label_box.append(fullscreen_label)
        fullscreen_label_box.append(fullscreen_desc)
        fullscreen_item.append(fullscreen_label_box)
        
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        switch_box.set_halign(Gtk.Align.END)
        self.fullscreen_switch = Gtk.Switch()
        self.fullscreen_switch.set_active(current_flags.get('fullscreen', False))
        self.fullscreen_switch.set_valign(Gtk.Align.CENTER)
        switch_box.append(self.fullscreen_switch)
        fullscreen_item.append(switch_box)
        
        options_group.append(fullscreen_item)
        
        # Virtual Desktop toggle and resolution
        virtual_desktop_main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        # Virtual Desktop toggle
        virtual_desktop_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        virtual_desktop_box.add_css_class('settings-item')
        
        virtual_desktop_label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        virtual_desktop_label_box.set_hexpand(True)
        virtual_desktop_label = Gtk.Label(label="Virtual Desktop")
        virtual_desktop_label.set_halign(Gtk.Align.START)
        virtual_desktop_desc = Gtk.Label(label="Run the game in a virtual desktop")
        virtual_desktop_desc.add_css_class('settings-description')
        virtual_desktop_desc.set_halign(Gtk.Align.START)
        virtual_desktop_label_box.append(virtual_desktop_label)
        virtual_desktop_label_box.append(virtual_desktop_desc)
        virtual_desktop_box.append(virtual_desktop_label_box)
        
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        switch_box.set_halign(Gtk.Align.END)
        self.virtual_desktop_switch = Gtk.Switch()
        self.virtual_desktop_switch.set_active(current_flags.get('virtual_desktop', False))
        self.virtual_desktop_switch.set_valign(Gtk.Align.CENTER)
        switch_box.append(self.virtual_desktop_switch)
        virtual_desktop_box.append(switch_box)
        
        virtual_desktop_main_box.append(virtual_desktop_box)
        
        # Virtual Desktop Resolution
        resolution_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        resolution_box.add_css_class('settings-item')
        resolution_box.set_margin_start(16)  # Indent resolution options
        
        # Width
        width_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        width_label = Gtk.Label(label="Width")
        width_label.set_halign(Gtk.Align.START)
        width_desc = Gtk.Label(label="Virtual desktop width")
        width_desc.add_css_class('settings-description')
        width_desc.set_halign(Gtk.Align.START)
        width_box.append(width_label)
        width_box.append(width_desc)
        self.virtual_desktop_width = Gtk.Entry()
        self.virtual_desktop_width.set_width_chars(6)
        self.virtual_desktop_width.set_text(str(current_flags.get('virtual_desktop_width', 1920)))
        self.virtual_desktop_width.add_css_class('settings-description')
        width_box.append(self.virtual_desktop_width)
        resolution_box.append(width_box)
        
        # Height
        height_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        height_label = Gtk.Label(label="Height")
        height_label.set_halign(Gtk.Align.START)
        height_desc = Gtk.Label(label="Virtual desktop height")
        height_desc.add_css_class('settings-description')
        height_desc.set_halign(Gtk.Align.START)
        height_box.append(height_label)
        height_box.append(height_desc)
        self.virtual_desktop_height = Gtk.Entry()
        self.virtual_desktop_height.set_width_chars(6)
        self.virtual_desktop_height.set_text(str(current_flags.get('virtual_desktop_height', 1080)))
        self.virtual_desktop_height.add_css_class('settings-description')
        height_box.append(self.virtual_desktop_height)
        resolution_box.append(height_box)
        
        virtual_desktop_main_box.append(resolution_box)
        
        # Update resolution fields sensitivity based on virtual desktop toggle
        def update_resolution_sensitivity(switch, _):
            resolution_box.set_sensitive(switch.get_active())
        self.virtual_desktop_switch.connect('notify::active', update_resolution_sensitivity)
        resolution_box.set_sensitive(self.virtual_desktop_switch.get_active())
        
        options_group.append(virtual_desktop_main_box)
        
        # Borderless toggle
        borderless_item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        borderless_item.add_css_class('settings-item')
        
        borderless_label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        borderless_label_box.set_hexpand(True)
        borderless_label = Gtk.Label(label="Borderless")
        borderless_label.set_halign(Gtk.Align.START)
        borderless_desc = Gtk.Label(label="Run the game in borderless mode")
        borderless_desc.add_css_class('settings-description')
        borderless_desc.set_halign(Gtk.Align.START)
        borderless_label_box.append(borderless_label)
        borderless_label_box.append(borderless_desc)
        borderless_item.append(borderless_label_box)
        
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        switch_box.set_halign(Gtk.Align.END)
        self.borderless_switch = Gtk.Switch()
        self.borderless_switch.set_active(current_flags.get('borderless', False))
        self.borderless_switch.set_valign(Gtk.Align.CENTER)
        switch_box.append(self.borderless_switch)
        borderless_item.append(switch_box)
        
        options_group.append(borderless_item)
        
        # Additional flags entry
        additional_item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        additional_item.add_css_class('settings-item')
        
        additional_label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        additional_label = Gtk.Label(label="Additional Flags")
        additional_label.set_halign(Gtk.Align.START)
        additional_desc = Gtk.Label(label="Additional flags to pass to the game")
        additional_desc.add_css_class('settings-description')
        additional_desc.set_halign(Gtk.Align.START)
        additional_label_box.append(additional_label)
        additional_label_box.append(additional_desc)
        additional_item.append(additional_label_box)
        
        self.additional_entry = Gtk.Entry()
        self.additional_entry.set_text(current_flags.get('additional_flags', ''))
        self.additional_entry.set_hexpand(True)
        self.additional_entry.add_css_class('settings-description')
        additional_item.append(self.additional_entry)
        
        options_group.append(additional_item)
        
        main_box.append(options_group)
        
        # Icon section
        icon_frame = Gtk.Frame()
        icon_frame.add_css_class("view")
        
        icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        icon_box.set_margin_start(12)
        icon_box.set_margin_end(12)
        icon_box.set_margin_top(12)
        icon_box.set_margin_bottom(12)
        
        # Current icon
        self.icon_image = Gtk.Picture()
        self.icon_image.set_size_request(64, 64)
        if game.icon and os.path.exists(game.icon):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(game.icon, 64, 64)
                self.icon_image.set_pixbuf(pixbuf)
            except Exception as e:
                print(f"Error loading icon preview: {e}")
        icon_box.append(self.icon_image)
        
        # Icon buttons box
        icon_buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        # Browse button
        browse_button = Gtk.Button(label="Browse Local Icon")
        browse_button.add_css_class("button")
        browse_button.connect('clicked', self.on_browse_clicked)
        icon_buttons_box.append(browse_button)
        
        # Remove button
        remove_button = Gtk.Button(label="Remove Icon")
        remove_button.add_css_class("button")
        remove_button.connect('clicked', self.on_remove_icon_clicked)
        icon_buttons_box.append(remove_button)
        
        icon_box.append(icon_buttons_box)
        
        # Search box
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self.search_entry = Gtk.Entry()
        self.search_entry.set_text(game.name)  # Set initial text to game name
        self.search_entry.set_placeholder_text("Search SteamGridDB for icons...")
        self.search_entry.set_hexpand(True)
        self.search_entry.add_css_class("entry")
        search_box.append(self.search_entry)
        
        search_button = Gtk.Button(label="Search")
        search_button.add_css_class("button")
        search_button.connect('clicked', self.on_search_clicked)
        search_box.append(search_button)
        
        icon_box.append(search_box)
        
        # Results list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(200)  # Limit the height of the icon grid
        scroll.set_propagate_natural_height(True)
        
        self.results_list = Gtk.ListBox()
        self.results_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.results_list.connect('row-selected', self.on_result_selected)
        scroll.set_child(self.results_list)
        
        # Initially hide the scroll window since there are no results
        scroll.set_visible(False)
        
        icon_box.append(scroll)
        
        # Store scroll window reference for later visibility control
        self.results_scroll = scroll
        
        icon_frame.set_child(icon_box)
        main_box.append(icon_frame)
        
        # Dialog buttons
        dialog_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        dialog_button_box.set_margin_start(12)
        dialog_button_box.set_margin_end(12)
        dialog_button_box.set_margin_top(12)
        dialog_button_box.set_margin_bottom(12)
        dialog_button_box.set_halign(Gtk.Align.END)
        
        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect('clicked', lambda b: self.response(Gtk.ResponseType.CANCEL))
        dialog_button_box.append(cancel_button)
        
        save_button = Gtk.Button(label="Save")
        save_button.add_css_class('suggested-action')
        save_button.connect('clicked', lambda b: self.response(Gtk.ResponseType.OK))
        dialog_button_box.append(save_button)
        
        content.append(dialog_button_box)
        
        self.connect('response', self.on_response)
        
        # Store selected icon info
        self.selected_icon_info = None
        
    def create_result_row(self, icon_info):
        """Create a row for search results"""
        row = Gtk.ListBoxRow()
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        
        # Icon preview
        def on_icon_loaded(pixbuf):
            if pixbuf:
                icon.set_pixbuf(pixbuf)
        
        icon = Gtk.Picture()
        icon.set_size_request(32, 32)
        self.icon_manager.get_icon(icon_info['name'], on_icon_loaded)
        box.append(icon)
        
        # Icon info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        info_box.set_hexpand(True)
        
        name = Gtk.Label(label=icon_info['name'])
        name.set_halign(Gtk.Align.START)
        name.add_css_class("heading")
        info_box.append(name)
        
        category = Gtk.Label(label=icon_info['category'])
        category.set_halign(Gtk.Align.START)
        category.add_css_class("dim-label")
        info_box.append(category)
        
        box.append(info_box)
        
        row.set_child(box)
        row.icon_info = icon_info
        return row
    
    def on_search_clicked(self, button):
        """Handle search button click"""
        query = self.search_entry.get_text()
        if not query:
            return
        
        # Show loading state
        self.search_entry.set_sensitive(False)
        button.set_sensitive(False)
        
        # Clear previous results
        while True:
            row = self.results_list.get_first_child()
            if row is None:
                break
            self.results_list.remove(row)
        
        # Hide results until we have some
        self.results_scroll.set_visible(False)
        
        def search_complete(icons):
            # Show results area now that we have results
            if icons:
                self.results_scroll.set_visible(True)
            
            # Add results
            for icon in icons:
                row = self.create_result_row(icon)
                self.results_list.append(row)
            
            # Reset UI state
            self.search_entry.set_sensitive(True)
            button.set_sensitive(True)
        
        # Start search
        self.icon_manager.search_icons(query, search_complete)
    
    def on_result_selected(self, list_box, row):
        """Handle search result selection"""
        if not row or not hasattr(row, 'icon_info'):
            return
        
        # Store selected icon info
        self.selected_icon_info = row.icon_info
        
        # Update icon preview
        def on_icon_loaded(pixbuf):
            if pixbuf:
                self.icon_image.set_pixbuf(pixbuf)
        
        if self.selected_icon_info.get('source') == 'steamgrid':
            self.icon_manager.get_icon(self.selected_icon_info.get('name'), on_icon_loaded)
        else:
            self.icon_manager.get_icon(self.selected_icon_info.get('filename'), on_icon_loaded)

    def on_browse_clicked(self, button):
        """Handle browse button click"""
        dialog = Gtk.FileChooserDialog(
            title="Choose Icon",
            transient_for=self.get_root(),
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Select", Gtk.ResponseType.OK)
        
        # Add file filters
        filter_images = Gtk.FileFilter()
        filter_images.set_name("Image files")
        filter_images.add_mime_type("image/png")
        filter_images.add_mime_type("image/jpeg")
        dialog.add_filter(filter_images)
        
        dialog.connect("response", self.on_browse_response)
        dialog.present()
    
    def on_browse_response(self, dialog, response):
        """Handle browse dialog response"""
        try:
            if response == Gtk.ResponseType.OK:
                file = dialog.get_file()
                if file:
                    file_path = file.get_path()
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file_path, 64, 64)
                        if pixbuf:
                            self.icon_image.set_pixbuf(pixbuf)
                            # Store selected icon info
                            self.selected_icon_info = {
                                'source': 'local',
                                'filename': file_path
                            }
                    except Exception as e:
                        print(f"Error loading selected icon: {e}")
        finally:
            dialog.destroy()

    def on_remove_icon_clicked(self, button):
        """Handle remove icon button click"""
        # Clear the icon preview
        self.icon_image.set_pixbuf(None)
        # Mark icon for removal
        self.selected_icon_info = {
            'source': 'remove',
            'filename': None
        }

    def get_desktop_file_path(self):
        """Get the desktop file path for this game"""
        desktop_dir = os.path.expanduser("~/.local/share/applications")
        safe_name = "".join(c for c in self.game.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return os.path.join(desktop_dir, f"umu-{safe_name}.desktop")

    def on_remove_desktop_clicked(self, button):
        """Remove desktop shortcut for the game"""
        try:
            desktop_file = self.get_desktop_file_path()
            
            if os.path.exists(desktop_file):
                os.remove(desktop_file)
                
                # Show success message
                dialog = Gtk.MessageDialog(
                    transient_for=self.get_root(),
                    modal=True,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text=f"Desktop shortcut has been removed for {self.game.name}"
                )
                dialog.connect("response", lambda d, r: d.destroy())
                dialog.present()
            else:
                # Show not found message
                dialog = Gtk.MessageDialog(
                    transient_for=self.get_root(),
                    modal=True,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text=f"No desktop shortcut found for {self.game.name}"
                )
                dialog.connect("response", lambda d, r: d.destroy())
                dialog.present()
                
        except Exception as e:
            # Show error message
            dialog = Gtk.MessageDialog(
                transient_for=self.get_root(),
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=f"Error removing shortcut: {str(e)}"
            )
            dialog.connect("response", lambda d, r: d.destroy())
            dialog.present()

    def on_create_desktop_clicked(self, button):
        """Create .desktop file for the game"""
        try:
            # Get the desktop directory path
            desktop_dir = os.path.expanduser("~/.local/share/applications")
            os.makedirs(desktop_dir, exist_ok=True)
            
            # Get desktop file path
            desktop_file = self.get_desktop_file_path()
            
            # Get the launcher path
            launcher_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
            
            # Create desktop entry content
            content = [
                "[Desktop Entry]",
                "Type=Application",
                f"Name={self.game.name}",
                f"Exec=python3 {launcher_path} --launch \"{self.game.file_path}\"",
                "Terminal=false",
                "Categories=Game;",
            ]
            
            # Add icon if available
            if self.game.icon and os.path.exists(self.game.icon):
                content.append(f"Icon={os.path.abspath(self.game.icon)}")
            
            # Write the desktop file
            with open(desktop_file, 'w') as f:
                f.write("\n".join(content))
            
            # Make it executable
            os.chmod(desktop_file, 0o755)
            
            # Show success message
            dialog = Gtk.MessageDialog(
                transient_for=self.get_root(),
                modal=True,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=f"Desktop shortcut has been created for {self.game.name}"
            )
            dialog.connect("response", lambda d, r: d.destroy())
            dialog.present()
            
        except Exception as e:
            # Show error message
            dialog = Gtk.MessageDialog(
                transient_for=self.get_root(),
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=f"Error creating shortcut: {str(e)}"
            )
            dialog.connect("response", lambda d, r: d.destroy())
            dialog.present()

    def on_response(self, dialog, response):
        """Handle dialog response"""
        try:
            if response == Gtk.ResponseType.OK:
                # Update game name
                new_name = self.name_entry.get_text().strip()
                if new_name:
                    self.game.name = new_name
                
                # Update icon if one was selected
                if hasattr(self, 'selected_icon_info') and self.selected_icon_info is not None:
                    game_dir = os.path.dirname(self.game.file_path)
                    icon_path = os.path.join(game_dir, "icon.png")
                    
                    source = self.selected_icon_info.get('source')
                    if source == 'remove':
                        # Remove the icon file if it exists
                        if self.game.icon and os.path.exists(self.game.icon):
                            try:
                                os.remove(self.game.icon)
                            except Exception as e:
                                print(f"Error removing icon file: {e}")
                        self.game.icon = None
                    elif source == 'steamgrid':
                        # For SteamGridDB icons, download and save
                        icon_url = self.selected_icon_info.get('url')
                        if icon_url and self.icon_manager.download_icon(icon_url, icon_path):
                            self.game.icon = icon_path
                    elif source == 'local':
                        # For local files, copy to game directory
                        try:
                            source_path = self.selected_icon_info.get('filename')
                            if source_path and os.path.exists(source_path):
                                # Convert to PNG and resize if needed
                                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(source_path, 64, 64)
                                pixbuf.savev(icon_path, "png", [], [])
                                self.game.icon = icon_path
                        except Exception as e:
                            print(f"Error saving icon: {e}")
                
                # Update game configuration
                found = False
                app = self.get_transient_for().get_application()
                for game_config in app.config['games']:
                    if isinstance(game_config, dict) and game_config.get('path') == self.game.file_path:
                        # Update existing configuration
                        game_config.update({
                            'name': self.game.name,
                            'icon': self.game.icon,
                            'flags': {
                                'gamemode': self.gamemode_switch.get_active(),
                                'mangohud': self.mangohud_switch.get_active(),
                                'fullscreen': self.fullscreen_switch.get_active(),
                                'virtual_desktop': self.virtual_desktop_switch.get_active(),
                                'virtual_desktop_width': int(self.virtual_desktop_width.get_text() or 1920),
                                'virtual_desktop_height': int(self.virtual_desktop_height.get_text() or 1080),
                                'borderless': self.borderless_switch.get_active(),
                                'additional_flags': self.additional_entry.get_text().strip()
                            }
                        })
                        found = True
                        break
                
                if not found:
                    # Add new configuration
                    app.config['games'].append({
                        'path': self.game.file_path,
                        'name': self.game.name,
                        'icon': self.game.icon,
                        'flags': {
                            'gamemode': self.gamemode_switch.get_active(),
                            'mangohud': self.mangohud_switch.get_active(),
                            'fullscreen': self.fullscreen_switch.get_active(),
                            'virtual_desktop': self.virtual_desktop_switch.get_active(),
                            'virtual_desktop_width': int(self.virtual_desktop_width.get_text() or 1920),
                            'virtual_desktop_height': int(self.virtual_desktop_height.get_text() or 1080),
                            'borderless': self.borderless_switch.get_active(),
                            'additional_flags': self.additional_entry.get_text().strip()
                        }
                    })
                
                # Save configuration immediately
                app.save_config()
                
                # Call the callback to refresh the game list
                if self.callback:
                    self.callback(self.game)
        except Exception as e:
            print(f"Error saving game configuration: {e}")
        finally:
            # Clear icon cache before closing
            self.icon_manager.clear_cache()
            dialog.destroy()