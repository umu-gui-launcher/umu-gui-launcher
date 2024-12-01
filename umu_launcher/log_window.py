import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Gdk, Gio
import os

class LogWindow(Gtk.Window):
    def __init__(self, parent, width=600, height=300, position='bottom'):
        """
        Initialize the log window
        
        Args:
            parent: Parent window
            width: Window width in pixels
            height: Window height in pixels
            position: Window position ('bottom', 'right', 'left')
        """
        super().__init__(
            transient_for=parent,
            modal=False,
            decorated=False
        )
        
        # Store configuration
        self.window_width = width
        self.window_height = height
        self.window_position = position
        
        # Set window properties
        self.set_default_size(width, height)
        self.set_resizable(False)
        
        # Create main box
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.main_box.set_margin_start(12)
        self.main_box.set_margin_end(12)
        self.main_box.set_margin_top(12)
        self.main_box.set_margin_bottom(12)
        
        # Add header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        # Make header draggable
        drag_area = Gtk.WindowHandle()
        drag_area.set_child(header_box)
        self.main_box.append(drag_area)
        
        # Add title
        self.title_label = Gtk.Label(label="Game Log")
        self.title_label.add_css_class("title")
        header_box.append(self.title_label)
        
        # Add spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header_box.append(spacer)
        
        # Add minimize button
        minimize_button = Gtk.Button()
        minimize_button.set_icon_name("go-down-symbolic")
        minimize_button.connect("clicked", self.on_minimize_clicked)
        header_box.append(minimize_button)
        
        # Add scrolled window for log
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        
        # Add text view for log
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_monospace(True)
        self.text_buffer = self.text_view.get_buffer()
        
        scrolled.set_child(self.text_view)
        self.main_box.append(scrolled)
        
        self.set_child(self.main_box)
        
        # Add CSS styling based on position
        border_radius = "12px"
        if position == 'right':
            border_css = """
                window {
                    background-color: @theme_bg_color;
                    border-top: 1px solid @borders;
                    border-left: 1px solid @borders;
                    border-bottom: 1px solid @borders;
                    border-top-left-radius: %s;
                    border-bottom-left-radius: %s;
                }
                .title {
                    font-weight: bold;
                    font-size: 16px;
                }
            """ % (border_radius, border_radius)
        elif position == 'left':
            border_css = """
                window {
                    background-color: @theme_bg_color;
                    border-top: 1px solid @borders;
                    border-right: 1px solid @borders;
                    border-bottom: 1px solid @borders;
                    border-top-right-radius: %s;
                    border-bottom-right-radius: %s;
                }
                .title {
                    font-weight: bold;
                    font-size: 16px;
                }
            """ % (border_radius, border_radius)
        else:  # bottom
            border_css = """
                window {
                    background-color: @theme_bg_color;
                    border-top: 1px solid @borders;
                    border-left: 1px solid @borders;
                    border-right: 1px solid @borders;
                    border-top-left-radius: %s;
                    border-top-right-radius: %s;
                }
                .title {
                    font-weight: bold;
                    font-size: 16px;
                }
            """ % (border_radius, border_radius)
        
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(border_css.encode())
        
        self.get_style_context().add_provider(
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Initialize state
        self.is_minimized = True
        self.animation_duration = 250  # ms
        self.animation_start_time = 0
        
        # Set up window positioning
        self.set_hide_on_close(True)
    
    def get_parent_bounds(self):
        """Get parent window bounds"""
        parent = self.get_transient_for()
        if not parent:
            return None
            
        native = parent.get_native()
        if not native:
            return None
            
        bounds = native.get_bounds()
        if not bounds:
            return None
            
        return bounds
    
    def show_with_animation(self):
        """Show the window with a slide animation"""
        if not self.is_visible():
            # Get parent bounds
            bounds = self.get_parent_bounds()
            if not bounds:
                return
            
            # Calculate initial position
            if self.window_position == 'right':
                x = bounds.width
                y = (bounds.height - self.window_height) // 2
            elif self.window_position == 'left':
                x = -self.window_width
                y = (bounds.height - self.window_height) // 2
            else:  # bottom
                x = (bounds.width - self.window_width) // 2
                y = bounds.height
            
            # Set initial position and show window
            self.set_default_size(self.window_width, 0)
            
            # Position relative to parent
            self.set_transient_for(self.get_transient_for())
            self.present()
            
            # Start animation
            self.is_minimized = False
            self.animation_start_time = GLib.get_monotonic_time()
            self.add_tick_callback(self.animate_show)
    
    def hide_with_animation(self):
        """Hide the window with a slide animation"""
        if self.is_visible():
            # Start animation
            self.is_minimized = True
            self.animation_start_time = GLib.get_monotonic_time()
            self.add_tick_callback(self.animate_hide)
    
    def animate_show(self, widget, frame_clock):
        """Animate showing the window"""
        now = GLib.get_monotonic_time()
        progress = min(1.0, (now - self.animation_start_time) / (self.animation_duration * 1000))
        
        if progress < 1.0:
            if self.window_position in ('left', 'right'):
                width = int(self.window_width * progress)
                self.set_default_size(width, self.window_height)
            else:  # bottom
                height = int(self.window_height * progress)
                self.set_default_size(self.window_width, height)
            return True
        else:
            self.set_default_size(self.window_width, self.window_height)
            return False
    
    def animate_hide(self, widget, frame_clock):
        """Animate hiding the window"""
        now = GLib.get_monotonic_time()
        progress = min(1.0, (now - self.animation_start_time) / (self.animation_duration * 1000))
        
        if progress < 1.0:
            if self.window_position in ('left', 'right'):
                width = int(self.window_width * (1 - progress))
                self.set_default_size(width, self.window_height)
            else:  # bottom
                height = int(self.window_height * (1 - progress))
                self.set_default_size(self.window_width, height)
            return True
        else:
            self.hide()
            return False
    
    def on_minimize_clicked(self, button):
        """Handle minimize button click"""
        self.hide_with_animation()
    
    def append_text(self, text):
        """Append text to the log"""
        end_iter = self.text_buffer.get_end_iter()
        self.text_buffer.insert(end_iter, text)
        # Scroll to bottom
        mark = self.text_buffer.create_mark(None, end_iter, False)
        self.text_view.scroll_mark_onscreen(mark)
        self.text_buffer.delete_mark(mark)
