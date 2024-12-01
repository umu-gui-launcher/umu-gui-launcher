import os
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk

class ConfigWindow(Gtk.Dialog):
    def __init__(self, parent, config, callback):
        super().__init__(
            title="Settings",
            transient_for=parent,
            modal=True,
            destroy_with_parent=True
        )
        
        self.config = config
        self.callback = callback
        
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
        icon = Gtk.Image.new_from_icon_name('preferences-system-symbolic')
        icon.set_pixel_size(32)
        header.append(icon)
        
        # Title section
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title = Gtk.Label(label="Settings")
        title.add_css_class('settings-title')
        title.set_halign(Gtk.Align.START)
        subtitle = Gtk.Label(label="Configure global launch options")
        subtitle.add_css_class('settings-subtitle')
        subtitle.set_halign(Gtk.Align.START)
        title_box.append(title)
        title_box.append(subtitle)
        header.append(title_box)
        
        content.append(header)
        
        # Main content box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        
        # Performance group
        perf_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        perf_group.add_css_class('settings-group')
        
        perf_title = Gtk.Label(label="Performance")
        perf_title.add_css_class('settings-group-title')
        perf_title.set_halign(Gtk.Align.START)
        perf_group.append(perf_title)
        
        self.flag_switches = {}
        
        # GameMode
        gamemode_box = self.create_setting_item(
            'gamemode',
            "GameMode",
            "Optimize system performance while gaming",
            config
        )
        perf_group.append(gamemode_box)
        
        # MangoHud
        mangohud_box = self.create_setting_item(
            'mangohud',
            "MangoHud",
            "Show performance overlay (FPS, CPU, GPU, etc.)",
            config
        )
        perf_group.append(mangohud_box)
        
        main_box.append(perf_group)
        
        # Display group
        display_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        display_group.add_css_class('settings-group')
        
        display_title = Gtk.Label(label="Display")
        display_title.add_css_class('settings-group-title')
        display_title.set_halign(Gtk.Align.START)
        display_group.append(display_title)
        
        # Fullscreen
        fullscreen_box = self.create_setting_item(
            'fullscreen',
            "Fullscreen",
            "Run games in fullscreen mode",
            config
        )
        display_group.append(fullscreen_box)
        
        # Borderless
        borderless_box = self.create_setting_item(
            'borderless',
            "Borderless Window",
            "Run games in borderless window mode",
            config
        )
        display_group.append(borderless_box)
        
        # Virtual Desktop
        virtual_desktop_box = self.create_setting_item(
            'virtual_desktop',
            "Virtual Desktop",
            "Run games in a virtual desktop window",
            config
        )
        display_group.append(virtual_desktop_box)
        
        main_box.append(display_group)
        
        # Advanced group
        advanced_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        advanced_group.add_css_class('settings-group')
        
        advanced_title = Gtk.Label(label="Advanced")
        advanced_title.add_css_class('settings-group-title')
        advanced_title.set_halign(Gtk.Align.START)
        advanced_group.append(advanced_title)
        
        # SteamGridDB API Key
        api_key_item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        api_key_item.add_css_class('settings-item')
        
        api_key_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        api_key_label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        api_key_label = Gtk.Label(label="SteamGridDB API Key")
        api_key_label.set_halign(Gtk.Align.START)
        api_key_desc = Gtk.Label(label="API key for fetching game artwork from SteamGridDB")
        api_key_desc.add_css_class('settings-description')
        api_key_desc.set_halign(Gtk.Align.START)
        api_key_label_box.append(api_key_label)
        api_key_label_box.append(api_key_desc)
        api_key_box.append(api_key_label_box)
        
        self.api_key_entry = Gtk.Entry()
        self.api_key_entry.set_text(config.get('steamgriddb_api_key', ''))
        self.api_key_entry.set_hexpand(True)
        api_key_box.append(self.api_key_entry)
        
        # Get API Key button
        get_key_button = Gtk.Button(label="Get API Key")
        get_key_button.connect('clicked', self.on_get_key_clicked)
        api_key_box.append(get_key_button)
        
        api_key_item.append(api_key_box)
        advanced_group.append(api_key_item)
        
        # Additional flags
        flags_item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        flags_item.add_css_class('settings-item')
        
        flags_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        flags_label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        flags_label = Gtk.Label(label="Additional Flags")
        flags_label.set_halign(Gtk.Align.START)
        flags_desc = Gtk.Label(label="Additional flags to pass to umu-run")
        flags_desc.add_css_class('settings-description')
        flags_desc.set_halign(Gtk.Align.START)
        flags_label_box.append(flags_label)
        flags_label_box.append(flags_desc)
        flags_box.append(flags_label_box)
        
        self.add_flags_entry = Gtk.Entry()
        self.add_flags_entry.set_text(config.get('flags', {}).get('additional_flags', ''))
        self.add_flags_entry.set_hexpand(True)
        flags_box.append(self.add_flags_entry)
        
        flags_item.append(flags_box)
        advanced_group.append(flags_item)
        
        main_box.append(advanced_group)
        
        content.append(main_box)
        
        # Add buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_margin_start(12)
        button_box.set_margin_end(12)
        button_box.set_margin_top(12)
        button_box.set_margin_bottom(12)
        button_box.set_halign(Gtk.Align.END)
        
        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect('clicked', lambda b: self.response(Gtk.ResponseType.CANCEL))
        button_box.append(cancel_button)
        
        save_button = Gtk.Button(label="Save")
        save_button.add_css_class('suggested-action')
        save_button.connect('clicked', lambda b: self.response(Gtk.ResponseType.OK))
        button_box.append(save_button)
        
        content.append(button_box)
        
        self.connect('response', self.on_response)
    
    def create_setting_item(self, flag_name, label_text, description, config):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.add_css_class('settings-item')
        
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        label = Gtk.Label(label=label_text)
        label.set_halign(Gtk.Align.START)
        switch_box.append(label)
        
        switch = Gtk.Switch()
        switch.set_halign(Gtk.Align.END)
        switch.set_hexpand(True)
        switch.set_active(config.get('flags', {}).get(flag_name, False))
        switch_box.append(switch)
        
        box.append(switch_box)
        
        desc = Gtk.Label(label=description)
        desc.add_css_class('settings-description')
        desc.set_halign(Gtk.Align.START)
        box.append(desc)
        
        self.flag_switches[flag_name] = switch
        return box
    
    def on_get_key_clicked(self, button):
        """Open SteamGridDB website to get API key"""
        import webbrowser
        webbrowser.open("https://www.steamgriddb.com/profile/preferences/api")
    
    def on_response(self, dialog, response):
        if response == Gtk.ResponseType.OK:
            # Update flags
            if 'flags' not in self.config:
                self.config['flags'] = {}
            
            for flag, switch in self.flag_switches.items():
                self.config['flags'][flag] = switch.get_active()
            
            # Update API key
            self.config['steamgriddb_api_key'] = self.api_key_entry.get_text().strip()
            
            # Update additional flags
            self.config['flags']['additional_flags'] = self.add_flags_entry.get_text().strip()
            
            # Get the app instance to save the config
            app = self.get_transient_for().get_application()
            
            # Update app's config with our changes
            app.config['flags'] = self.config['flags']
            app.config['steamgriddb_api_key'] = self.config['steamgriddb_api_key']
            
            # Save the configuration
            app.save_config()
            
            # Call callback if provided
            if self.callback:
                self.callback(self.config)
        
        self.destroy()
