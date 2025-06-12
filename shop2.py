# Standard library imports
import os
import math
import copy
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Tkinter imports
import tkinter as tk
from tkinter import messagebox, filedialog, colorchooser

# CustomTkinter for modern UI
import customtkinter as ctk

# Data structure helpers
from dataclasses import dataclass, field

# PDF and export functionality
from reportlab.pdfgen import canvas as reportlab_canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

# Image processing (for export functions)
from PIL import Image
import cairosvg

# Only import these when needed in specific functions:
# import pyscreenshot
# import tempfile
# import webbrowser

@dataclass
class Dimension:
    feet: int
    inches: int

@dataclass
class Panel:
    id: int
    x: float
    width: float
    actual_width: Dimension
    height: Dimension
    color: str
    actual_width_fraction: str = "0"  # Optional parameters at the end
    height_fraction: str = "0"
    border_color: str = "red"  # Default border color
    floor_mounted: bool = True  # Whether the panel is mounted on the floor
    height_offset: Dimension = None  # Height offset from floor if not floor mounted
    height_offset_fraction: str = "0"  # Fraction for height offset    
    
@dataclass
class WallObject:
    """Class representing an object placed on the wall (e.g., TV, artwork)"""
    id: int
    name: str
    width: Dimension
    height: Dimension
    x_position: float  # X position in percentage of wall width
    y_position: float  # Y position in percentage of wall height
    affected_panels: List[int]  # List of panel IDs that this object affects
    width_fraction: str = "0"
    height_fraction: str = "0"
    color: str = "#AAAAAA"  # Default gray color
    border_color: str = "black"
    border_width: int = 2
    show_border: bool = True
    alignment: str = "Center"  # "Center", "Left Edge", or "Right Edge"
    h_position_feet: int = 0
    h_position_inches: int = 0
    h_position_fraction: str = "0"
    use_exact_position: bool = False  # If True, use exact measurements instead of alignment
    # New fields for reference points
    v_reference: str = "Top Edge"  # Options: "Top Edge", "Center", "Bottom Edge"
    h_reference: str = "Left Edge"  # Options: "Left Edge", "Center", "Right Edge"

@dataclass
class AnnotationCircle:
    """Class representing an annotation circle with text"""
    id: int
    x: float  # X position on canvas
    y: float  # Y position on canvas
    radius: int = 20  # Default radius in pixels
    text: str = ""  # Text inside the circle
    color: str = "#FFFFFF"  # Background color
    border_color: str = "#000000"  # Border color
    text_color: str = "#000000"  # Text color
    border_width: int = 2
    line_to_x: float = None  # Optional line endpoint X
    line_to_y: float = None  # Optional line endpoint Y
    font_size: int = 10
    font_family: str = "Arial"
    line_color: str = "#000000"
    line_width: int = 1
    line_style: str = ""  # Can be "" for solid or "dash" for dashed
    canvas_id: int = None  # To store the canvas circle ID for updates/moves


@dataclass
class Wall:
    id: int
    name: str
    dimensions: dict
    panels: List[Panel] = field(default_factory=list)
    baseboard_enabled: bool = False
    baseboard_height: float = 4
    baseboard_fraction: str = "0"
    panel_color: str = "#FFFFFF"
    panel_border_color: str = "red"
    wall_objects: List[WallObject] = field(default_factory=list)
    custom_panel_widths: dict = field(default_factory=dict)
    split_panels: dict = field(default_factory=dict)
    selected_panels: List[int] = field(default_factory=list)
    annotation_circles: List[AnnotationCircle] = field(default_factory=list)
    next_object_id: int = 1
    next_annotation_id: int = 1
    
    # Panel configuration
    panel_dimensions: dict = field(default_factory=dict)  # Empty dict instead of preset values
    use_equal_panels: bool = False
    panel_count: int = 2
    use_center_panels: bool = False
    center_panel_count: int = 4
    floor_mounted: bool = True
    height_offset: Optional[Dimension] = None
    height_offset_fraction: str = "0"
    
    # Display settings
    show_dimensions: bool = True
    show_object_distances: bool = False
    show_horizontal_distances: bool = False
    distance_reference: str = "Wall Top"
    custom_name: str = "Panel"

class PDFExporter:
    def __init__(self, canvas_widget, summary_text):
        self.canvas_widget = canvas_widget
        self.summary_text = summary_text

    def convert_coords(self, x, y, width, height, scale, offset_x, offset_y):
        """Convert canvas coordinates to PDF coordinates"""
        return (x * scale + offset_x, y * scale + offset_y)

    def convert_color(self, color):
        """Convert Tkinter color to ReportLab color"""
        if not color or color == '':
            return colors.black
        
        try:
            # Handle hex colors
            if color.startswith('#'):
                r = int(color[1:3], 16) / 255
                g = int(color[3:5], 16) / 255
                b = int(color[5:7], 16) / 255
                return (r, g, b)
            # Handle system colors or named colors
            elif color == 'SystemButtonText':
                return colors.black
            elif color == 'gray':
                return colors.gray
            elif color == 'red':
                return colors.red
            else:
                return colors.black
        except:
            return colors.black

    def create_pdf(self, project_name, location, date_str, output_path):
        # Create PDF in landscape orientation
        width, height = letter
        c = reportlab_canvas.Canvas(output_path, pagesize=(height, width))
        
        # Draw black border around entire page
        c.setStrokeColor(colors.black)
        c.setLineWidth(1)
        c.rect(10, 10, height-20, width-20)
        
        # Add header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(30, width - 40, "Wallcovering Calculator")
        
        # Add project details
        c.setFont("Helvetica", 12)
        c.drawString(30, width - 70, f"Project: {project_name}")
        c.drawString(30, width - 90, f"Location: {location}")
        c.drawString(30, width - 110, f"Date: {date_str}")
        
        # Add line separator
        c.line(30, width - 120, height - 30, width - 120)

        # Get canvas content and dimensions
        canvas_width = self.canvas_widget.winfo_width()
        canvas_height = self.canvas_widget.winfo_height()
        
        # Calculate scaling and positioning
        margin = 30
        available_width = height - (2 * margin)
        available_height = width - 150  # Space for header and margin
        
        # Calculate scale while maintaining aspect ratio
        scale_x = available_width / canvas_width
        scale_y = available_height / canvas_height
        scale = min(scale_x, scale_y)
        
        # Calculate centering offsets
        offset_x = margin + (available_width - (canvas_width * scale)) / 2
        offset_y = margin

        # Get all canvas items
        canvas_items = self.canvas_widget.find_all()
        
        for item in canvas_items:
            item_type = self.canvas_widget.type(item)
            coords = self.canvas_widget.coords(item)
            config = {key: self.canvas_widget.itemcget(item, key) 
                     for key in self.canvas_widget.itemconfig(item)}
            
            # Set colors and line properties
            fill_color = self.convert_color(config.get('fill', ''))
            outline_color = self.convert_color(config.get('outline', ''))
            
            if fill_color:
                c.setFillColor(fill_color)
            if outline_color:
                c.setStrokeColor(outline_color)
            
            # Convert line width
            if 'width' in config:
                try:
                    line_width = float(config['width'])
                    c.setLineWidth(line_width)
                except ValueError:
                    c.setLineWidth(1)

            if item_type == 'rectangle':
                x1, y1, x2, y2 = coords
                x1, y1 = self.convert_coords(x1, canvas_height - y1, canvas_width, canvas_height, scale, offset_x, offset_y)
                x2, y2 = self.convert_coords(x2, canvas_height - y2, canvas_width, canvas_height, scale, offset_x, offset_y)
                
                # Draw rectangle with proper fill and stroke
                if fill_color:
                    c.rect(x1, y1, x2-x1, y2-y1, stroke=1, fill=1)
                else:
                    c.rect(x1, y1, x2-x1, y2-y1, stroke=1, fill=0)
                
            elif item_type == 'line':
                x1, y1, x2, y2 = coords
                x1, y1 = self.convert_coords(x1, canvas_height - y1, canvas_width, canvas_height, scale, offset_x, offset_y)
                x2, y2 = self.convert_coords(x2, canvas_height - y2, canvas_width, canvas_height, scale, offset_x, offset_y)
                
                if 'dash' in config and config['dash']:
                    try:
                        dash_pattern = [int(x) for x in config['dash'].split()]
                        c.setDash(dash_pattern)
                    except:
                        c.setDash([])
                c.line(x1, y1, x2, y2)
                c.setDash() # Reset dash pattern
                
            elif item_type == 'text':
                x1, y1 = coords
                text = config.get('text', '')
                font = config.get('font', '').split()
                font_size = int(font[1]) if len(font) > 1 else 12
                
                x1, y1 = self.convert_coords(x1, canvas_height - y1, canvas_width, canvas_height, scale, offset_x, offset_y)
                
                c.setFont('Helvetica', font_size)
                c.setFillColor(colors.black)  # Ensure text is always black
                    
                # Handle text anchor
                anchor = config.get('anchor', 'nw')
                if anchor == 's':
                    y1 += font_size
                elif anchor == 'n':
                    y1 -= font_size
                
                c.drawString(x1, y1, text)

        c.save()
        return True

    def svg_to_pdf(self, svg_path, pdf_path, dpi=300):
        """Convert SVG to PDF with high resolution."""
        cairosvg.svg2pdf(file_obj=open(svg_path, "rb"), write_to=pdf_path, dpi=dpi)

    def canvas_to_svg(self, canvas_widget, output_path, project_name, location, date):
        """Convert Tkinter canvas to an SVG file without arrows."""
        # Set canvas dimensions and scaling
        width = canvas_widget.winfo_width()
        height = canvas_widget.winfo_height()
        scale = 1.0  # Adjust this scale if needed

        # Swap width and height for landscape orientation
        svg_width, svg_height = height, width

        # Start SVG content with a border
        svg_content = f'''
        <svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}">
            <rect x="10" y="10" width="{svg_width - 20}" height="{svg_height - 20}" stroke="black" fill="none" stroke-width="1"/>
        '''

        # Add project details
        svg_content += f'''
            <text x="30" y="40" font-size="10" fill="black" font-family="Arial">SHOP DRAWING</text>
            <text x="30" y="60" font-size="8" fill="black" font-family="Arial">Project: {project_name}</text>
            <text x="30" y="70" font-size="8" fill="black" font-family="Arial">Location: {location}</text>
            <text x="30" y="80" font-size="8" fill="black" font-family="Arial">Date: {date}</text>
        '''

        # Loop through all canvas items
        for item in canvas_widget.find_all():
            item_type = canvas_widget.type(item)
            coords = [c * scale for c in canvas_widget.coords(item)]  # Apply scaling
            config = {key: canvas_widget.itemcget(item, key) for key in canvas_widget.itemconfig(item)}

            if item_type == "rectangle":
                x1, y1, x2, y2 = coords
                fill = config.get('fill', 'none')
                outline = config.get('outline', 'black')
                stroke_width = config.get('width', '1')
                svg_content += f'<rect x="{x1}" y="{y1}" width="{x2 - x1}" height="{y2 - y1}" fill="{fill}" stroke="{outline}" stroke-width="{stroke_width}" />\n'

            elif item_type == "line":
                x1, y1, x2, y2 = coords
                stroke = config.get('fill', 'black')
                stroke_width = config.get('width', '1')
                dash = config.get('dash', None)
                dash_style = f'stroke-dasharray="{dash}"' if dash else ''
                svg_content += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{stroke_width}" {dash_style} />\n'

            elif item_type == "text":
                x1, y1 = coords
                text = config.get('text', '')
                fill = config.get('fill', 'black')
                font_size = 12 * scale  # Adjust font size for scaling
                svg_content += f'<text x="{x1}" y="{y1}" fill="{fill}" font-size="{font_size}" font-family="Arial">{text}</text>\n'

        svg_content += '</svg>'

        # Write SVG content to file
        with open(output_path, "w") as f:
            f.write(svg_content)





    
class WallcoveringCalculatorUI(ctk.CTk):
    def __init__(self):
        # Add calculation control flags
        self.calculation_in_progress = False
        self.pending_calculation = False
        super().__init__()

        self.title("Wallcovering Calculator")
        self.geometry("1400x900")

        # Initialize calculator
        self.wall_dimensions = {"width": Dimension(8, 0), "height": Dimension(10, 0)}
        self.panel_dimensions = {"width": Dimension(4, 0), "height": Dimension(10, 0)}
        self.use_equal_panels = False
        self.panel_count = 2
        self.use_baseboard = False
        self.baseboard_height = 4
        self.panel_color = "#FFFFFF"
        self.baseboard_var = tk.BooleanVar(value=False)
        self.panel_border_color = "red"  # Default panel border color
        # self.setup_variable_traces()
        # Initialize object-related variables
        self.selected_panels = []  # List of selected panel IDs
        self.wall_objects = []     # List of WallObject instances
        self.next_object_id = 1    # ID counter for wall objects
        self.selection_mode = False  # If True, clicks will select panels

        # Initialize annotation system
        self.annotation_circles = []
        self.next_annotation_id = 1
        self.annotation_mode = False
        self.moving_annotation = False
        self.current_annotation = None
        self.line_drawing = False
        self.annotation_line_start = None
        self.summary_refresh_requested = False
        # Initialize panel customization tracking
        self.custom_panel_widths = {}  # Make sure to initialize this
        self.split_panels = {}         # And this
        self.current_active_wall_id = None
        self.switching_walls = False

        # Create the UI
        self.create_tabbed_interface_with_annotations()
        
        # Create walls tab interface
        self.create_walls_tab_interface()
        
        # Initialize the annotation system
        self.initialize_annotation_system()

    def manual_add_circle(self, x, y):
        """Add an annotation circle using UI settings"""
        print(f"ADD CIRCLE: x={x}, y={y}")
        try:
            # Get properties from UI controls
            text = self.annotation_text_var.get()
            radius = int(self.annotation_size_var.get())
            font_size = int(self.annotation_font_size_var.get())
            
            # Create circle with UI settings
            circle = AnnotationCircle(
                id=self.next_annotation_id,
                x=x,
                y=y,
                radius=radius,
                text=text,
                color=self.annotation_color_preview["background"],
                border_color=self.annotation_border_preview["background"],
                text_color=self.annotation_text_color_preview["background"],
                border_width=2,
                font_size=font_size,
                line_color=self.annotation_line_color_preview["background"],
                line_width=int(self.annotation_line_width_var.get()),
                line_style="dash" if self.annotation_line_style_var.get() == "Dashed" else ""
            )
            
            # Add to list and increment ID
            self.annotation_circles.append(circle)
            self.next_annotation_id += 1
            self.current_annotation = circle
            
            # Auto-increment the text if it's a number
            if text.isdigit():
                next_num = int(text) + 1
                self.annotation_text_var.set(str(next_num))
            
            # Update the current annotation
            self.current_annotation = circle
            
            # Redraw
            self.calculate()
        except Exception as e:
            print(f"ERROR in add_annotation_circle: {e}")
            import traceback
            traceback.print_exc()
        
    def create_scrollable_frame(self, parent):
        """Create a scrollable frame with CustomTkinter styling"""
        container = ctk.CTkFrame(parent)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create canvas for scrolling (using dark mode compatible bg color)
        canvas = tk.Canvas(container, highlightthickness=0, bg='#2B2B2B')
        scrollbar = ctk.CTkScrollbar(container, orientation="vertical", command=canvas.yview)
        
        # Create the frame that will contain all widgets
        scrollable_frame = ctk.CTkFrame(canvas)
        
        # Configure canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        canvas_frame = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Configure scrolling
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def configure_canvas_width(event):
            canvas.itemconfig(canvas_frame, width=event.width)
        
        scrollable_frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", configure_canvas_width)
        
        # Add mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        return scrollable_frame

    def create_wall_panel_controls(self, parent):
        """Create wall and panel dimension controls"""
        # Define fraction options at the beginning of the method
        fraction_options = ["0", "1/16", "1/8", "3/16", "1/4", "5/16", "3/8", "7/16", 
                          "1/2", "9/16", "5/8", "11/16", "3/4", "13/16", "7/8", "15/16"]
        
        # Wall dimensions section
        wall_section = ctk.CTkFrame(parent)
        wall_section.pack(pady=10, fill=tk.X)
        
        ctk.CTkLabel(wall_section, text="Wall Dimensions", font=("Arial", 14, "bold")).pack(pady=5)
        
        self.create_dimension_inputs(wall_section, "Width", "wall_width")
        self.create_dimension_inputs(wall_section, "Height", "wall_height")
        
        # Panel dimensions section
        panel_section = ctk.CTkFrame(parent)
        panel_section.pack(pady=10, fill=tk.X)
        
        ctk.CTkLabel(panel_section, text="Panel Dimensions", font=("Arial", 14, "bold")).pack(pady=5)
        
        self.create_dimension_inputs(panel_section, "Width", "panel_width")
        self.create_dimension_inputs(panel_section, "Height", "panel_height")
        
        # Panel Color section
        color_section = ctk.CTkFrame(parent)
        color_section.pack(pady=10, fill=tk.X)
        
        ctk.CTkLabel(color_section, text="Panel Color", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Panel fill color
        fill_color_frame = ctk.CTkFrame(color_section)
        fill_color_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(fill_color_frame, text="Fill Color:").pack(side=tk.LEFT, padx=5)
        self.color_preview = tk.Canvas(fill_color_frame, width=30, height=30, bg=self.panel_color)
        self.color_preview.pack(side=tk.LEFT, padx=5)
        
        color_picker_button = ctk.CTkButton(
            fill_color_frame,
            text="Choose Fill Color",
            command=self.choose_color
        )
        color_picker_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Panel border color
        border_color_frame = ctk.CTkFrame(color_section)
        border_color_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(border_color_frame, text="Border Color:").pack(side=tk.LEFT, padx=5)
        self.border_color_preview = tk.Canvas(border_color_frame, width=30, height=30, bg="red")
        self.border_color_preview.pack(side=tk.LEFT, padx=5)
        
        border_color_picker_button = ctk.CTkButton(
            border_color_frame,
            text="Choose Border Color",
            command=self.choose_border_color
        )
        border_color_picker_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Panel Options section
        options_section = ctk.CTkFrame(parent)
        options_section.pack(pady=10, fill=tk.X)
        
        ctk.CTkLabel(options_section, text="Panel Options", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Custom panel name
        name_frame = ctk.CTkFrame(options_section)
        name_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(name_frame, text="Custom Panel Name:").pack(side=tk.LEFT, padx=5)
        self.custom_name_var = tk.StringVar(value="Panel")
        custom_name_entry = ctk.CTkEntry(name_frame, textvariable=self.custom_name_var, width=200)
        custom_name_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Checkboxes for options
        checkbox_frame = ctk.CTkFrame(options_section)
        checkbox_frame.pack(fill=tk.X, pady=5)
        
        # Left column of checkboxes
        left_check_frame = ctk.CTkFrame(checkbox_frame)
        left_check_frame.pack(side=tk.LEFT, fill=tk.Y, expand=True)

                # Floor mounted toggle
        self.floor_mounted_var = tk.BooleanVar(value=True)
        floor_mounted_cb = ctk.CTkCheckBox(
            left_check_frame,
            text="Mount Panels on Floor",
            variable=self.floor_mounted_var,
            command=self.on_floor_mounted_change
        )
        floor_mounted_cb.pack(pady=5, anchor="w")

        
        self.show_dimensions_var = tk.BooleanVar(value=True)
        show_dimensions_cb = ctk.CTkCheckBox(
            left_check_frame,
            text="Show Dimensions",
            variable=self.show_dimensions_var,
            command=self.calculate
        )
        show_dimensions_cb.pack(pady=5, anchor="w")
        
        self.equal_panels_var = tk.BooleanVar()
        equal_panels_cb = ctk.CTkCheckBox(
            left_check_frame,
            text="Use Equal Panels",
            variable=self.equal_panels_var,
            command=self.on_equal_panels_change
        )
        equal_panels_cb.pack(pady=5, anchor="w")
        
        self.center_panels_var = tk.BooleanVar(value=False)
        center_panels_cb = ctk.CTkCheckBox(
            left_check_frame,
            text="Center Equal Panels",
            variable=self.center_panels_var,
            command=self.on_center_panels_change
        )
        center_panels_cb.pack(pady=5, anchor="w")

        # Right column of checkboxes
        right_check_frame = ctk.CTkFrame(checkbox_frame)
        right_check_frame.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        
        self.baseboard_var = tk.BooleanVar(value=False)
        baseboard_cb = ctk.CTkCheckBox(
            right_check_frame,
            text="Use Baseboard",
            variable=self.baseboard_var,
            command=self.on_baseboard_change
        )
        baseboard_cb.pack(pady=5, anchor="w")
        
        self.show_object_distances_var = tk.BooleanVar(value=False)
        show_object_distances_cb = ctk.CTkCheckBox(
            right_check_frame,
            text="Show Object Distances",
            variable=self.show_object_distances_var,
            command=self.calculate
        )
        show_object_distances_cb.pack(pady=5, anchor="w")
        
        # Add new dropdown for distance reference - with fixed callback
        distance_ref_frame = ctk.CTkFrame(right_check_frame)
        distance_ref_frame.pack(pady=2, fill=tk.X)
        
        ctk.CTkLabel(distance_ref_frame, text="Distance Reference:").pack(side=tk.LEFT, padx=5)
        self.distance_reference_var = tk.StringVar(value="Wall Top")
        distance_ref_dropdown = ctk.CTkOptionMenu(
            distance_ref_frame,
            variable=self.distance_reference_var,
            values=["Wall Top", "Panel Top"],
            width=100,
            command=self.on_distance_reference_change  # Use a wrapper function instead
        )
        distance_ref_dropdown.pack(side=tk.LEFT, padx=5)
        
        self.show_horizontal_distances_var = tk.BooleanVar(value=False)
        show_horizontal_distances_cb = ctk.CTkCheckBox(
            right_check_frame,
            text="Horizontal Object Distances",
            variable=self.show_horizontal_distances_var,
            command=self.calculate
        )
        show_horizontal_distances_cb.pack(pady=5, anchor="w")
        
        # Panel count frame - initially hidden
        self.panel_count_frame = ctk.CTkFrame(options_section)
        # Don't pack yet - will be shown/hidden based on checkbox state
        
        ctk.CTkLabel(self.panel_count_frame, text="Panel Count:").pack(side=tk.LEFT, padx=5)
        self.panel_count_var = tk.StringVar(value="2")
        panel_count_entry = ctk.CTkEntry(self.panel_count_frame, textvariable=self.panel_count_var, width=50)
        panel_count_entry.pack(side=tk.LEFT, padx=5)
        
        # Center panel inputs - initially hidden
        self.center_panel_inputs = ctk.CTkFrame(options_section)
        # Don't pack yet - will be shown/hidden based on checkbox state
        
        ctk.CTkLabel(self.center_panel_inputs, text="Number of Center Panels:").pack(side=tk.LEFT, padx=5)
        self.center_panel_count_var = tk.StringVar(value="4")
        center_panel_entry = ctk.CTkEntry(
            self.center_panel_inputs,
            textvariable=self.center_panel_count_var,
            width=50
        )
        center_panel_entry.pack(side=tk.LEFT, padx=5)

        # Start seam position section
        self.start_seam_frame = ctk.CTkFrame(options_section)
        # Don't pack yet - will be shown/hidden based on checkbox state

        ctk.CTkLabel(self.start_seam_frame, text="Start Seam At:").pack(side=tk.LEFT, padx=5)

        self.start_seam_feet_var = tk.StringVar(value="0")
        start_seam_feet_entry = ctk.CTkEntry(self.start_seam_frame, textvariable=self.start_seam_feet_var, width=50)
        start_seam_feet_entry.pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(self.start_seam_frame, text="feet").pack(side=tk.LEFT)

        self.start_seam_inches_var = tk.StringVar(value="0")
        start_seam_inches_entry = ctk.CTkEntry(self.start_seam_frame, textvariable=self.start_seam_inches_var, width=50)
        start_seam_inches_entry.pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(self.start_seam_frame, text="inches").pack(side=tk.LEFT)

        # Add fraction dropdown for start seam
        ctk.CTkLabel(self.start_seam_frame, text="+").pack(side=tk.LEFT, padx=2)
        self.start_seam_fraction_var = tk.StringVar(value="0")
        start_seam_fraction_dropdown = ctk.CTkOptionMenu(
            self.start_seam_frame,
            variable=self.start_seam_fraction_var,
            values=fraction_options,
            width=70
        )
        start_seam_fraction_dropdown.pack(side=tk.LEFT, padx=5)

        # Add checkbox for start seam mode (add this with the other checkboxes)
        self.use_start_seam_var = tk.BooleanVar(value=False)
        start_seam_cb = ctk.CTkCheckBox(
            right_check_frame,  # Add to the right column with other checkboxes
            text="Start Seam at Position",
            variable=self.use_start_seam_var,
            command=self.on_start_seam_change
        )
        start_seam_cb.pack(pady=5, anchor="w")

        # Height offset frame - initially hidden
        self.height_offset_frame = ctk.CTkFrame(options_section)
        # Don't pack yet - will be shown/hidden based on checkbox state

        ctk.CTkLabel(self.height_offset_frame, text="Height from Floor:").pack(side=tk.LEFT, padx=5)
        self.height_offset_feet_var = tk.StringVar(value="0")
        height_offset_feet_entry = ctk.CTkEntry(self.height_offset_frame, textvariable=self.height_offset_feet_var, width=50)
        height_offset_feet_entry.pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(self.height_offset_frame, text="feet").pack(side=tk.LEFT)

        self.height_offset_inches_var = tk.StringVar(value="0")
        height_offset_inches_entry = ctk.CTkEntry(self.height_offset_frame, textvariable=self.height_offset_inches_var, width=50)
        height_offset_inches_entry.pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(self.height_offset_frame, text="inches").pack(side=tk.LEFT)

        # Add fraction dropdown for height offset
        ctk.CTkLabel(self.height_offset_frame, text="+").pack(side=tk.LEFT, padx=2)
        self.height_offset_fraction_var = tk.StringVar(value="0")
        height_offset_fraction_dropdown = ctk.CTkOptionMenu(
            self.height_offset_frame,
            variable=self.height_offset_fraction_var,
            values=fraction_options,
            width=70
        )
        height_offset_fraction_dropdown.pack(side=tk.LEFT, padx=5)

                
        # Baseboard frame - initially hidden
        self.baseboard_frame = ctk.CTkFrame(options_section)
        # Don't pack yet - will be shown/hidden based on checkbox state
        
        ctk.CTkLabel(self.baseboard_frame, text="Baseboard Height:").pack(side=tk.LEFT, padx=5)
        self.baseboard_height_var = tk.StringVar(value="4")
        baseboard_entry = ctk.CTkEntry(self.baseboard_frame, textvariable=self.baseboard_height_var, width=50)
        baseboard_entry.pack(side=tk.LEFT, padx=5)
        
        ctk.CTkLabel(self.baseboard_frame, text="inches").pack(side=tk.LEFT)
        
        # Add fraction dropdown for baseboard
        ctk.CTkLabel(self.baseboard_frame, text="+").pack(side=tk.LEFT, padx=2)
        self.baseboard_fraction_var = tk.StringVar(value="0")
        baseboard_fraction_dropdown = ctk.CTkOptionMenu(
            self.baseboard_frame,
            variable=self.baseboard_fraction_var,
            values=fraction_options,
            width=70
        )
        baseboard_fraction_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = ctk.CTkFrame(parent)
        button_frame.pack(pady=10, fill=tk.X)
        
        calculate_btn = ctk.CTkButton(
            button_frame,
            text="Calculate",
            command=self.calculate,
            fg_color="#1E88E5",
            hover_color="#1565C0"
        )
        calculate_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        reset_btn = ctk.CTkButton(
            button_frame,
            text="Reset",
            command=self.reset_form,
            fg_color="#757575",
            hover_color="#616161"
        )
        reset_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

    # The issue is that while the UI elements are created, references to display them are missing
    # Here's the fix for the create_object_controls method

    def on_distance_reference_change(self, value):
        """Handle change in distance reference dropdown - wrapper for calculate"""
        # The value parameter receives the dropdown selection
        # We can use it if needed, but for now we just call calculate
        self.calculate()  # Call calculate without passing the value


    def create_object_controls(self, parent):
        """Create object controls for the Objects tab"""
        # Panel selection section
        selection_section = ctk.CTkFrame(parent)
        selection_section.pack(pady=10, fill=tk.X)
        
        ctk.CTkLabel(selection_section, text="Panel Selection", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Selection mode toggle
        self.selection_mode_var = tk.BooleanVar(value=False)
        selection_mode_cb = ctk.CTkCheckBox(
            selection_section,
            text="Enable Panel Selection Mode",
            variable=self.selection_mode_var,
            command=self.toggle_selection_mode
        )
        selection_mode_cb.pack(pady=5, anchor="w")
        
        # Selected panels display
        selected_panels_frame = ctk.CTkFrame(selection_section)
        selected_panels_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(selected_panels_frame, text="Selected Panels:").pack(side=tk.LEFT, padx=5)
        self.selected_panels_label = ctk.CTkLabel(selected_panels_frame, text="None")
        self.selected_panels_label.pack(side=tk.LEFT, padx=5)
        
        # Clear selection button
        clear_selection_btn = ctk.CTkButton(
            selection_section,
            text="Clear Selection",
            command=self.clear_panel_selection
        )
        clear_selection_btn.pack(pady=5, fill=tk.X)
        
        # Split panel button
        split_btn = ctk.CTkButton(
            selection_section,
            text="Split Selected Panel into Two Equal Panels",
            command=self.split_selected_panel
        )
        split_btn.pack(pady=5, fill=tk.X)
        
        # Object properties section
        object_section = ctk.CTkFrame(parent)
        object_section.pack(pady=10, fill=tk.X)
        
        ctk.CTkLabel(object_section, text="Object Properties", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Object name
        name_frame = ctk.CTkFrame(object_section)
        name_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(name_frame, text="Object Name:").pack(side=tk.LEFT, padx=5)
        self.object_name_var = tk.StringVar(value="TV")
        name_entry = ctk.CTkEntry(name_frame, textvariable=self.object_name_var, width=200)
        name_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Object dimensions
        dimensions_label = ctk.CTkLabel(object_section, text="Object Dimensions:")
        dimensions_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Width
        self.create_dimension_inputs(object_section, "Width", "object_width")
        
        # Height
        self.create_dimension_inputs(object_section, "Height", "object_height")
        
        # After creating vertical position inputs, add reference point selection
        self.vertical_pos_frame = ctk.CTkFrame(object_section)
        self.vertical_pos_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(self.vertical_pos_frame, text="Vertical Position:").pack(side=tk.LEFT, padx=5)
        
        # Feet input for vertical position
        self.object_y_feet_var = tk.StringVar(value="0")
        feet_entry = ctk.CTkEntry(self.vertical_pos_frame, textvariable=self.object_y_feet_var, width=40)
        feet_entry.pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(self.vertical_pos_frame, text="feet").pack(side=tk.LEFT)
        
        # Inches input
        self.object_y_inches_var = tk.StringVar(value="0")
        inches_entry = ctk.CTkEntry(self.vertical_pos_frame, textvariable=self.object_y_inches_var, width=40)
        inches_entry.pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(self.vertical_pos_frame, text="inches").pack(side=tk.LEFT)
        
        # Fraction dropdown
        ctk.CTkLabel(self.vertical_pos_frame, text="+").pack(side=tk.LEFT, padx=2)
        self.object_y_fraction_var = tk.StringVar(value="0")
        fraction_options = ["0", "1/16", "1/8", "3/16", "1/4", "5/16", "3/8", "7/16", 
                          "1/2", "9/16", "5/8", "11/16", "3/4", "13/16", "7/8", "15/16"]
        fraction_dropdown = ctk.CTkOptionMenu(
            self.vertical_pos_frame,
            variable=self.object_y_fraction_var,
            values=fraction_options,
            width=70
        )
        fraction_dropdown.pack(side=tk.LEFT, padx=2)
        
        # New: Add vertical reference point selection
        v_ref_frame = ctk.CTkFrame(object_section)
        v_ref_frame.pack(pady=2, fill=tk.X)
        
        ctk.CTkLabel(v_ref_frame, text="Vertical Reference:").pack(side=tk.LEFT, padx=5)
        self.v_reference_var = tk.StringVar(value="Top Edge")
        v_ref_dropdown = ctk.CTkOptionMenu(
            v_ref_frame,
            variable=self.v_reference_var,
            values=["Top Edge", "Center", "Bottom Edge"],
            width=120
        )
        v_ref_dropdown.pack(side=tk.LEFT, padx=5)
        
        # New: Add reference origin selection
        v_origin_frame = ctk.CTkFrame(object_section)
        v_origin_frame.pack(pady=2, fill=tk.X)
        
        ctk.CTkLabel(v_origin_frame, text="Measure From:").pack(side=tk.LEFT, padx=5)
        self.v_origin_var = tk.StringVar(value="Wall Top")
        v_origin_dropdown = ctk.CTkOptionMenu(
            v_origin_frame,
            variable=self.v_origin_var,
            values=["Wall Top", "Panel Top"],
            width=120
        )
        v_origin_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Help text for vertical position
        vertical_help = ctk.CTkLabel(
            v_origin_frame,
            text="(measures distance from selected point)",
            font=("Arial", 10)
        )
        vertical_help.pack(side=tk.LEFT, padx=10)




        
        # Modify horizontal position frame to include reference points
        horizontal_pos_frame = ctk.CTkFrame(object_section)
        horizontal_pos_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(horizontal_pos_frame, text="Horizontal Position:").pack(side=tk.LEFT, padx=5)
        
        # Checkbox to enable exact horizontal positioning
        self.use_exact_h_position_var = tk.BooleanVar(value=False)
        h_position_toggle = ctk.CTkCheckBox(
            horizontal_pos_frame,
            text="Use Exact Position",
            variable=self.use_exact_h_position_var,
            command=self.toggle_horizontal_position_mode
        )
        h_position_toggle.pack(side=tk.LEFT, padx=5)
        
        # Create a subframe for the horizontal position inputs
        self.h_position_inputs = ctk.CTkFrame(object_section)
        
        # Feet input
        self.object_h_feet_var = tk.StringVar(value="0")
        feet_entry = ctk.CTkEntry(self.h_position_inputs, textvariable=self.object_h_feet_var, width=40)
        feet_entry.pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(self.h_position_inputs, text="feet").pack(side=tk.LEFT)
        
        # Inches input
        self.object_h_inches_var = tk.StringVar(value="0")
        inches_entry = ctk.CTkEntry(self.h_position_inputs, textvariable=self.object_h_inches_var, width=40)
        inches_entry.pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(self.h_position_inputs, text="inches").pack(side=tk.LEFT)
        
        # Fraction dropdown
        ctk.CTkLabel(self.h_position_inputs, text="+").pack(side=tk.LEFT, padx=2)
        self.object_h_fraction_var = tk.StringVar(value="0")
        fraction_dropdown = ctk.CTkOptionMenu(
            self.h_position_inputs,
            variable=self.object_h_fraction_var,
            values=fraction_options,
            width=70
        )
        fraction_dropdown.pack(side=tk.LEFT, padx=2)
        
        # Help text
        h_position_help = ctk.CTkLabel(
            self.h_position_inputs,
            text="(from the left edge of the wall)",
            font=("Arial", 10)
        )
        h_position_help.pack(side=tk.LEFT, padx=10)
            # New: Add horizontal reference point selection when exact positioning is used
        h_ref_frame = ctk.CTkFrame(object_section)
        h_ref_frame.pack(pady=2, fill=tk.X)
        self.h_ref_frame = h_ref_frame
        
        ctk.CTkLabel(h_ref_frame, text="Horizontal Reference:").pack(side=tk.LEFT, padx=5)
        self.h_reference_var = tk.StringVar(value="Left Edge")
        h_ref_dropdown = ctk.CTkOptionMenu(
            h_ref_frame,
            variable=self.h_reference_var,
            values=["Left Edge", "Center", "Right Edge"],
            width=120
        )
        h_ref_dropdown.pack(side=tk.LEFT, padx=5)
            # Initially hide horizontal reference if not using exact positioning
        h_ref_frame.pack_forget()
        
        # Initially hide horizontal inputs - they'll be shown when checkbox is checked
        # Note: Do not pack h_position_inputs here
        
        # Create alignment frame
        self.alignment_frame = ctk.CTkFrame(object_section)
        self.alignment_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(self.alignment_frame, text="Alignment:").pack(side=tk.LEFT, padx=5)
        
        self.object_alignment_var = tk.StringVar(value="Center")
        alignment_options = ["Center", "Left Edge", "Right Edge"]
        alignment_dropdown = ctk.CTkOptionMenu(
            self.alignment_frame,
            variable=self.object_alignment_var,
            values=alignment_options,
            width=150
        )
        alignment_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Help/info button with tooltip
        info_button = ctk.CTkButton(
            self.alignment_frame,
            text="?",
            width=25,
            command=self.show_alignment_info
        )
        info_button.pack(side=tk.LEFT, padx=5)
        
        # Object color
        color_frame = ctk.CTkFrame(object_section)
        color_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(color_frame, text="Fill Color:").pack(side=tk.LEFT, padx=5)
        
        self.object_color_preview = tk.Canvas(color_frame, width=30, height=30, bg="#AAAAAA")
        self.object_color_preview.pack(side=tk.LEFT, padx=5)
        
        color_picker_button = ctk.CTkButton(
            color_frame,
            text="Choose Fill Color",
            command=self.choose_object_color
        )
        color_picker_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Object border color
        border_color_frame = ctk.CTkFrame(object_section)
        border_color_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(border_color_frame, text="Border Color:").pack(side=tk.LEFT, padx=5)
        
        self.object_border_color_preview = tk.Canvas(border_color_frame, width=30, height=30, bg="black")
        self.object_border_color_preview.pack(side=tk.LEFT, padx=5)
        
        border_color_picker_button = ctk.CTkButton(
            border_color_frame,
            text="Choose Border Color",
            command=self.choose_object_border_color
        )
        border_color_picker_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Border width
        border_width_frame = ctk.CTkFrame(object_section)
        border_width_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(border_width_frame, text="Border Width:").pack(side=tk.LEFT, padx=5)
        
        self.object_border_width_var = tk.StringVar(value="2")
        border_width_entry = ctk.CTkEntry(border_width_frame, textvariable=self.object_border_width_var, width=50)
        border_width_entry.pack(side=tk.LEFT, padx=5)
        
        # Show border option
        self.object_border_var = tk.BooleanVar(value=True)
        border_toggle = ctk.CTkCheckBox(
            object_section,
            text="Show Object Border",
            variable=self.object_border_var
        )
        border_toggle.pack(pady=5, anchor="w")
        
        # Add object and remove object buttons
        button_frame = ctk.CTkFrame(object_section)
        button_frame.pack(pady=10, fill=tk.X)
        
        add_object_btn = ctk.CTkButton(
            button_frame,
            text="Add Object to Selected Panels",
            command=self.add_wall_object,
            fg_color="#1E88E5",
            hover_color="#1565C0"
        )
        add_object_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        remove_objects_btn = ctk.CTkButton(
            button_frame,
            text="Remove All Objects",
            command=self.remove_all_objects,
            fg_color="#E53935",
            hover_color="#C62828"
        )
        remove_objects_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)


    def initialize_annotation_system(self):
        """Initialize the annotation circle system"""
        # Store annotation circles
        self.annotation_circles = []
        self.next_annotation_id = 1
        
        # Track current mode
        self.annotation_mode = False
        self.moving_annotation = False
        self.current_annotation = None
        self.line_drawing = False
        self.annotation_line_start = None
        
        # Bind mouse events for annotation interactions
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        # Add right-click context menu for annotations
        self.canvas.bind("<ButtonPress-3>", self.on_annotation_right_click)

    def create_annotation_controls(self, parent):
        """Create annotation controls for the Annotations tab"""
        # Annotation mode section
        annotation_section = ctk.CTkFrame(parent)
        annotation_section.pack(pady=10, fill=tk.X)
        
        ctk.CTkLabel(annotation_section, text="Annotation Circles", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Annotation mode toggle
        self.annotation_mode_var = tk.BooleanVar(value=False)
        annotation_mode_cb = ctk.CTkCheckBox(
            annotation_section,
            text="Enable Annotation Mode",
            variable=self.annotation_mode_var,
            command=self.toggle_annotation_mode
        )
        annotation_mode_cb.pack(pady=5, anchor="w")
        
        # In create_annotation_controls method:
        self.line_drawing_var = tk.BooleanVar(value=False)
        line_drawing_cb = ctk.CTkCheckBox(
            annotation_section,
            text="Connect Circle with Line",
            variable=self.line_drawing_var,
            command=lambda: print(f"Line drawing set to: {self.line_drawing_var.get()}")  # Debug callback
        )
        line_drawing_cb.pack(pady=5, anchor="w")
        
        # Annotation properties section
        properties_section = ctk.CTkFrame(parent)
        properties_section.pack(pady=10, fill=tk.X)
        
        ctk.CTkLabel(properties_section, text="Annotation Properties", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Annotation text
        text_frame = ctk.CTkFrame(properties_section)
        text_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(text_frame, text="Text:").pack(side=tk.LEFT, padx=5)
        self.annotation_text_var = tk.StringVar(value="1")
        text_entry = ctk.CTkEntry(text_frame, textvariable=self.annotation_text_var, width=200)
        text_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Circle size
        size_frame = ctk.CTkFrame(properties_section)
        size_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(size_frame, text="Circle Size:").pack(side=tk.LEFT, padx=5)
        self.annotation_size_var = tk.StringVar(value="20")
        size_entry = ctk.CTkEntry(size_frame, textvariable=self.annotation_size_var, width=50)
        size_entry.pack(side=tk.LEFT, padx=5)
        
        # Circle colors
        color_frame = ctk.CTkFrame(properties_section)
        color_frame.pack(pady=5, fill=tk.X)
        
        # Fill color
        ctk.CTkLabel(color_frame, text="Fill:").pack(side=tk.LEFT, padx=5)
        self.annotation_color_preview = tk.Canvas(color_frame, width=20, height=20, bg="#FFFFFF")
        self.annotation_color_preview.pack(side=tk.LEFT, padx=5)
        
        fill_color_btn = ctk.CTkButton(
            color_frame,
            text="Fill Color",
            command=self.choose_annotation_color,
            width=80
        )
        fill_color_btn.pack(side=tk.LEFT, padx=5)
        
        # Border color
        ctk.CTkLabel(color_frame, text="Border:").pack(side=tk.LEFT, padx=5)
        self.annotation_border_preview = tk.Canvas(color_frame, width=20, height=20, bg="#000000")
        self.annotation_border_preview.pack(side=tk.LEFT, padx=5)
        
        border_color_btn = ctk.CTkButton(
            color_frame,
            text="Border Color",
            command=self.choose_annotation_border_color,
            width=80
        )
        border_color_btn.pack(side=tk.LEFT, padx=5)
        
        # Text color
        text_color_frame = ctk.CTkFrame(properties_section)
        text_color_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(text_color_frame, text="Text:").pack(side=tk.LEFT, padx=5)
        self.annotation_text_color_preview = tk.Canvas(text_color_frame, width=20, height=20, bg="#000000")
        self.annotation_text_color_preview.pack(side=tk.LEFT, padx=5)
        
        text_color_btn = ctk.CTkButton(
            text_color_frame,
            text="Text Color",
            command=self.choose_annotation_text_color,
            width=80
        )
        text_color_btn.pack(side=tk.LEFT, padx=5)
        
        # Font size
        ctk.CTkLabel(text_color_frame, text="Font Size:").pack(side=tk.LEFT, padx=5)
        self.annotation_font_size_var = tk.StringVar(value="10")
        font_size_entry = ctk.CTkEntry(text_color_frame, textvariable=self.annotation_font_size_var, width=50)
        font_size_entry.pack(side=tk.LEFT, padx=5)
        
        # Line properties
        line_frame = ctk.CTkFrame(properties_section)
        line_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(line_frame, text="Line:").pack(side=tk.LEFT, padx=5)
        self.annotation_line_color_preview = tk.Canvas(line_frame, width=20, height=20, bg="#000000")
        self.annotation_line_color_preview.pack(side=tk.LEFT, padx=5)
        
        line_color_btn = ctk.CTkButton(
            line_frame,
            text="Line Color",
            command=self.choose_annotation_line_color,
            width=80
        )
        line_color_btn.pack(side=tk.LEFT, padx=5)
        
        ctk.CTkLabel(line_frame, text="Width:").pack(side=tk.LEFT, padx=5)
        self.annotation_line_width_var = tk.StringVar(value="1")
        line_width_entry = ctk.CTkEntry(line_frame, textvariable=self.annotation_line_width_var, width=50)
        line_width_entry.pack(side=tk.LEFT, padx=5)
        
        # Line style option
        style_frame = ctk.CTkFrame(properties_section)
        style_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(style_frame, text="Line Style:").pack(side=tk.LEFT, padx=5)
        self.annotation_line_style_var = tk.StringVar(value="Solid")
        style_dropdown = ctk.CTkOptionMenu(
            style_frame,
            variable=self.annotation_line_style_var,
            values=["Solid", "Dashed"],
            width=150
        )
        style_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = ctk.CTkFrame(parent)
        button_frame.pack(pady=10, fill=tk.X)
        
        clear_annotations_btn = ctk.CTkButton(
            button_frame,
            text="Remove All Annotations",
            command=self.remove_all_annotations,
            fg_color="#E53935",
            hover_color="#C62828"
        )
        clear_annotations_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # Add help text
        help_text = (
            "Click to place annotation circles. "
            "Drag to move them. "
            "Right-click for options."
        )
        help_label = ctk.CTkLabel(parent, text=help_text, wraplength=400)
        help_label.pack(pady=10)

        test_btn = ctk.CTkButton(
            parent,
            text="Manual Add Circle",
            command=lambda: self.manual_add_circle(200, 200)
        )
        test_btn.pack(pady=10)

    def toggle_annotation_mode(self):
        """Toggle annotation mode on/off"""
        self.annotation_mode = self.annotation_mode_var.get()
        print(f"Annotation mode set to: {self.annotation_mode}")
        
        # If enabling annotation mode, disable panel selection mode
        if self.annotation_mode and hasattr(self, 'selection_mode_var'):
            self.selection_mode_var.set(False)
            self.selection_mode = False
        
        # Set appropriate cursor
        cursor = "crosshair" if self.annotation_mode else ""
        self.canvas.config(cursor=cursor)
        
        # Update the UI to reflect the mode change
        self.calculate()

    # Add this new debug method
    def debug_line_drawing_state(self):
        """Print the current state of line drawing variables"""
        print(f"Line drawing enabled: {self.line_drawing_var.get()}")
        print(f"Current annotation: {self.current_annotation is not None}")
        print(f"Line drawing active: {self.line_drawing}")
        print(f"Line start annotation: {self.annotation_line_start}")
        if self.current_annotation:
            print(f"Current annotation id: {self.current_annotation.id}, pos: ({self.current_annotation.x}, {self.current_annotation.y})")

    def choose_annotation_color(self):
        """Choose color for annotation fill"""
        color = colorchooser.askcolor(color=self.annotation_color_preview["background"], title="Choose Annotation Fill Color")
        if color[1]:
            self.annotation_color_preview.configure(bg=color[1])

    def choose_annotation_border_color(self):
        """Choose color for annotation border"""
        color = colorchooser.askcolor(color=self.annotation_border_preview["background"], title="Choose Annotation Border Color")
        if color[1]:
            self.annotation_border_preview.configure(bg=color[1])

    def choose_annotation_text_color(self):
        """Choose color for annotation text"""
        color = colorchooser.askcolor(color=self.annotation_text_color_preview["background"], title="Choose Annotation Text Color")
        if color[1]:
            self.annotation_text_color_preview.configure(bg=color[1])
    def on_floor_mounted_change(self):
        """Handle floor mounted checkbox change"""
        if self.floor_mounted_var.get():
            # Panels are floor mounted, hide height offset controls
            if hasattr(self, 'height_offset_frame'):
                self.height_offset_frame.pack_forget()
        else:
            # Panels are not floor mounted, show height offset controls
            if hasattr(self, 'height_offset_frame'):
                # Check if baseboard frame exists and is packed
                # Instead of trying to pack relative to baseboard_frame, just pack it
                # directly in the options_section
                for widget in self.tab_wall.winfo_children():
                    if isinstance(widget, ctk.CTkFrame):
                        for child in widget.winfo_children():
                            if child == self.height_offset_frame:
                                # Already packed
                                return
                
                # Find the options_section frame
                for widget in self.wall_frame.winfo_children():
                    if isinstance(widget, ctk.CTkFrame) and len(widget.winfo_children()) > 0:
                        if isinstance(widget.winfo_children()[0], ctk.CTkLabel) and \
                           "Panel Options" in widget.winfo_children()[0].cget("text"):
                            # This is the options section
                            self.height_offset_frame.pack(in_=widget, pady=5, fill=tk.X, before=self.baseboard_frame if self.use_baseboard else None)
                            break
                
        # Recalculate and redraw
        self.calculate()


    def choose_annotation_line_color(self):
        """Choose color for annotation line"""
        color = colorchooser.askcolor(color=self.annotation_line_color_preview["background"], title="Choose Annotation Line Color")
        if color[1]:
            self.annotation_line_color_preview.configure(bg=color[1])

    def on_canvas_click(self, event):
        print(f"CLICK: x={event.x}, y={event.y}, annotation_mode={self.annotation_mode}")
        
        if self.annotation_mode:
            print("  Annotation mode branch activated")
            annotation = self.find_annotation_at_position(event.x, event.y)
            print(f"  Found existing annotation: {annotation is not None}")
            
            if annotation:
                print("  Found existing annotation, starting move")
                self.moving_annotation = True
                self.current_annotation = annotation
                return
            
            print(f"  Checking line drawing: {self.line_drawing_var.get()}")
            print(f"  Current annotation: {self.current_annotation is not None}")
            if self.line_drawing_var.get() and self.current_annotation:
                print("  Starting line drawing")
                self.line_drawing = True
                self.annotation_line_start = self.current_annotation
                return
            
            print("  About to add annotation circle")
            self.add_annotation_circle(event.x, event.y)
            print("  After adding annotation circle")
        elif self.selection_mode:
            # Your existing panel selection code
            print("  Selection mode branch")
            # Rest of your code
        else:
            print("  Neither annotation nor selection mode active")

    def on_start_seam_change(self):
        """Handle start seam checkbox change"""
        if self.use_start_seam_var.get():
            self.start_seam_frame.pack(pady=5, fill=tk.X)
            # Turn off other panel modes
            self.equal_panels_var.set(False)
            self.center_panels_var.set(False)
            if hasattr(self, 'panel_count_frame'):
                self.panel_count_frame.pack_forget()
            if hasattr(self, 'center_panel_inputs'):
                self.center_panel_inputs.pack_forget()
        else:
            self.start_seam_frame.pack_forget()
        self.calculate()

    def calculate_start_seam_panels(self, wall_width_inches_total, panel_height_dim, panel_height_frac, 
                                   floor_mounted, height_offset_dim, height_offset_fraction):
        """Calculate panels with a start seam at specified position"""
        
        # Get start seam position in inches
        start_seam_feet = self.safe_int_conversion(self.start_seam_feet_var.get(), 0)
        start_seam_inches = self.safe_int_conversion(self.start_seam_inches_var.get(), 0) 
        start_seam_fraction = self.start_seam_fraction_var.get()
        
        start_seam_position_inches = self.convert_to_inches(
            start_seam_feet, start_seam_inches, start_seam_fraction
        )
        
        # Validate start seam position
        if start_seam_position_inches <= 0 or start_seam_position_inches >= wall_width_inches_total:
            # If invalid position, fall back to equal panels
            return self.calculate_equal_panels_fallback(wall_width_inches_total, panel_height_dim, 
                                                       panel_height_frac, floor_mounted, height_offset_dim, 
                                                       height_offset_fraction)
        
        # Calculate left and right sections
        left_width = start_seam_position_inches
        right_width = wall_width_inches_total - start_seam_position_inches
        
        # Get standard panel width
        panel_width_inches = self.convert_to_inches(
            self.panel_dimensions["width"].feet,
            self.panel_dimensions["width"].inches,
            self.panel_dimensions.get("width_fraction", "0")
        )
        
        if panel_width_inches <= 0:
            panel_width_inches = 48  # Default 4 feet
        
        panels = []
        current_x_inches = 0
        panel_id = 1
        
        # Calculate left side panels
        if left_width > 0:
            # How many full panels fit in the left section?
            left_full_panels = int(left_width // panel_width_inches)
            left_remainder = left_width % panel_width_inches
            
            if left_full_panels == 0:
                # Just one panel for the entire left section
                left_panel_width = left_width
                left_dim, left_frac = self.convert_to_feet_inches_fraction(left_panel_width)
                
                panels.append(Panel(
                    id=panel_id,
                    x=(current_x_inches / wall_width_inches_total * 100),
                    width=(left_panel_width / wall_width_inches_total * 100),
                    actual_width=left_dim,
                    actual_width_fraction=left_frac,
                    height=panel_height_dim,
                    height_fraction=panel_height_frac,
                    color=self.panel_color,
                    border_color=self.panel_border_color,
                    floor_mounted=floor_mounted,
                    height_offset=height_offset_dim if not floor_mounted else None,
                    height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                ))
                panel_id += 1
                current_x_inches += left_panel_width
                
            else:
                # Multiple panels on left side
                if left_remainder > 0:
                    # Distribute the remainder equally among all left panels
                    adjusted_left_width = left_width / (left_full_panels + 1)
                    left_panel_count = left_full_panels + 1
                else:
                    # Perfect fit
                    adjusted_left_width = panel_width_inches
                    left_panel_count = left_full_panels
                
                # Create left panels
                for i in range(left_panel_count):
                    left_dim, left_frac = self.convert_to_feet_inches_fraction(adjusted_left_width)
                    
                    panels.append(Panel(
                        id=panel_id,
                        x=(current_x_inches / wall_width_inches_total * 100),
                        width=(adjusted_left_width / wall_width_inches_total * 100),
                        actual_width=left_dim,
                        actual_width_fraction=left_frac,
                        height=panel_height_dim,
                        height_fraction=panel_height_frac,
                        color=self.panel_color,
                        border_color=self.panel_border_color,
                        floor_mounted=floor_mounted,
                        height_offset=height_offset_dim if not floor_mounted else None,
                        height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                    ))
                    panel_id += 1
                    current_x_inches += adjusted_left_width
        
        # Calculate right side panels (similar logic)
        if right_width > 0:
            right_full_panels = int(right_width // panel_width_inches)
            right_remainder = right_width % panel_width_inches
            
            if right_full_panels == 0:
                # Just one panel for the entire right section
                right_panel_width = right_width
                right_dim, right_frac = self.convert_to_feet_inches_fraction(right_panel_width)
                
                panels.append(Panel(
                    id=panel_id,
                    x=(current_x_inches / wall_width_inches_total * 100),
                    width=(right_panel_width / wall_width_inches_total * 100),
                    actual_width=right_dim,
                    actual_width_fraction=right_frac,
                    height=panel_height_dim,
                    height_fraction=panel_height_frac,
                    color=self.panel_color,
                    border_color=self.panel_border_color,
                    floor_mounted=floor_mounted,
                    height_offset=height_offset_dim if not floor_mounted else None,
                    height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                ))
                
            else:
                # Multiple panels on right side
                if right_remainder > 0:
                    # Distribute the remainder equally among all right panels
                    adjusted_right_width = right_width / (right_full_panels + 1)
                    right_panel_count = right_full_panels + 1
                else:
                    # Perfect fit
                    adjusted_right_width = panel_width_inches
                    right_panel_count = right_full_panels
                
                # Create right panels
                for i in range(right_panel_count):
                    right_dim, right_frac = self.convert_to_feet_inches_fraction(adjusted_right_width)
                    
                    panels.append(Panel(
                        id=panel_id,
                        x=(current_x_inches / wall_width_inches_total * 100),
                        width=(adjusted_right_width / wall_width_inches_total * 100),
                        actual_width=right_dim,
                        actual_width_fraction=right_frac,
                        height=panel_height_dim,
                        height_fraction=panel_height_frac,
                        color=self.panel_color,
                        border_color=self.panel_border_color,
                        floor_mounted=floor_mounted,
                        height_offset=height_offset_dim if not floor_mounted else None,
                        height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                    ))
                    panel_id += 1
                    current_x_inches += adjusted_right_width
        
        return panels

    def calculate_equal_panels_fallback(self, wall_width_inches_total, panel_height_dim, panel_height_frac,
                                       floor_mounted, height_offset_dim, height_offset_fraction):
        """Fallback to equal panels if start seam calculation fails"""
        # Simple 2-panel fallback
        panel_width = wall_width_inches_total / 2
        panel_dim, panel_frac = self.convert_to_feet_inches_fraction(panel_width)
        
        panels = []
        for i in range(2):
            panels.append(Panel(
                id=i+1,
                x=(i * 50),  # 0% and 50%
                width=50,    # 50% each
                actual_width=panel_dim,
                actual_width_fraction=panel_frac,
                height=panel_height_dim,
                height_fraction=panel_height_frac,
                color=self.panel_color,
                border_color=self.panel_border_color,
                floor_mounted=floor_mounted,
                height_offset=height_offset_dim if not floor_mounted else None,
                height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
            ))
        
        return panels


    def on_canvas_drag(self, event):
        """Handle mouse drag on canvas"""
        if self.annotation_mode:
            if self.moving_annotation and self.current_annotation:
                # Move the annotation to the new position
                self.current_annotation.x = event.x
                self.current_annotation.y = event.y
                
                # Update the drawing
                self.calculate()
            elif self.line_drawing and self.annotation_line_start:
                print(f"Updating line endpoint to ({event.x}, {event.y})")
                # Update the line endpoint
                self.annotation_line_start.line_to_x = event.x
                self.annotation_line_start.line_to_y = event.y
                
                # Update the drawing
                self.calculate()

    def on_canvas_release(self, event):
        """Handle mouse release on canvas"""
        if self.annotation_mode:
            if self.moving_annotation:
                # Stop moving the annotation
                self.moving_annotation = False
                
            if self.line_drawing:
                print(f"Finalizing line at ({event.x}, {event.y})")
                # Check if we released over another annotation
                target = self.find_annotation_at_position(event.x, event.y)
                
                if target and target != self.annotation_line_start:
                    print(f"Connected to annotation {target.id}")
                    # Connect to this annotation instead of arbitrary point
                    self.annotation_line_start.line_to_x = target.x
                    self.annotation_line_start.line_to_y = target.y
                else:
                    # Keep the current line endpoint
                    self.annotation_line_start.line_to_x = event.x
                    self.annotation_line_start.line_to_y = event.y
                
                # Reset line drawing state
                self.line_drawing = False
                self.annotation_line_start = None
                
                # Update the drawing
                self.calculate()

    def on_annotation_right_click(self, event):
        """Handle right-click on annotations for context menu"""
        if not self.annotation_mode:
            return
        
        # Check if clicked on an annotation
        annotation = self.find_annotation_at_position(event.x, event.y)
        if not annotation:
            return
        
        # Store the current annotation
        self.current_annotation = annotation
        
        # Create context menu
        context_menu = tk.Menu(self.canvas, tearoff=0)
        context_menu.add_command(label="Edit Text", command=self.edit_annotation_text)
        context_menu.add_command(label="Change Size", command=self.edit_annotation_size)
        context_menu.add_command(label="Remove Line", command=lambda: self.remove_annotation_line(annotation))
        context_menu.add_separator()
        context_menu.add_command(label="Delete Annotation", command=lambda: self.delete_annotation(annotation))
        
        # Display context menu
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def find_annotation_at_position(self, x, y):
        """Find an annotation circle at the given position"""
        for circle in self.annotation_circles:
            # Check if position is within the circle
            distance = math.sqrt((circle.x - x) ** 2 + (circle.y - y) ** 2)
            if distance <= circle.radius:
                return circle
        return None

    def add_annotation_circle(self, x, y):
        print(f"ADD CIRCLE: Starting at ({x}, {y})")
        try:
            # Create a simple annotation circle with fixed values
            circle = AnnotationCircle(
                id=self.next_annotation_id,
                x=x,
                y=y,
                radius=20,
                text="1",
                color="#FFFFFF",
                border_color="#000000",
                text_color="#000000",
                border_width=2,
                font_size=10,
                line_color="#000000",
                line_width=1,
                line_style=""
            )
            
            print(f"  Circle created with id={circle.id}")
            self.annotation_circles.append(circle)
            print(f"  Total circles now: {len(self.annotation_circles)}")
            self.next_annotation_id += 1
            
            # Call calculate to update display
            print("  Calling calculate")
            self.calculate()
            print("  After calculate")
        except Exception as e:
            print(f"ADD CIRCLE ERROR: {e}")
            import traceback
            traceback.print_exc()

    def edit_annotation_text(self):
        """Edit the text of the current annotation"""
        if not self.current_annotation:
            return
        
        # Create dialog for text input
        dialog = ctk.CTkInputDialog(
            text="Enter new annotation text:",
            title="Edit Annotation Text"
        )
        
        new_text = dialog.get_input()
        if new_text is not None:  # None if canceled
            self.current_annotation.text = new_text
            self.calculate()

    def edit_annotation_size(self):
        """Edit the size (radius) of the current annotation"""
        if not self.current_annotation:
            return
        
        # Create dialog for size input
        dialog = ctk.CTkInputDialog(
            text="Enter new circle size (radius):",
            title="Edit Annotation Size"
        )
        
        new_size = dialog.get_input()
        if new_size is not None:
            try:
                self.current_annotation.radius = int(new_size)
                self.calculate()
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number for the size")

    def remove_annotation_line(self, annotation):
        """Remove the line from an annotation"""
        if not annotation:
            return
        
        annotation.line_to_x = None
        annotation.line_to_y = None
        self.calculate()

    def delete_annotation(self, annotation):
        """Delete an annotation from the canvas"""
        if not annotation:
            return
        
        self.annotation_circles.remove(annotation)
        
        # If this was the current annotation, clear it
        if self.current_annotation == annotation:
            self.current_annotation = None
        
        self.calculate()

    def remove_all_annotations(self):
        """Remove all annotations from the canvas"""
        if not self.annotation_circles:
            return
        
        if messagebox.askyesno("Confirm", "Remove all annotations?"):
            self.annotation_circles = []
            self.current_annotation = None
            self.calculate()

    def draw_annotations(self):
        """Draw all annotation circles on the canvas"""
        print(f"DRAW: {len(self.annotation_circles)} circles to draw")
        
        for circle in self.annotation_circles:
            print(f"  Drawing circle: id={circle.id}, pos=({circle.x}, {circle.y})")
            
            # Draw connecting line if present
            if circle.line_to_x is not None and circle.line_to_y is not None:
                print(f"  Drawing line from ({circle.x}, {circle.y}) to ({circle.line_to_x}, {circle.line_to_y})")
                # Determine line dash pattern if needed
                dash = (4, 2) if circle.line_style == "dash" else None
                
                # Draw line
                self.canvas.create_line(
                    circle.x, circle.y,
                    circle.line_to_x, circle.line_to_y,
                    fill=circle.line_color,
                    width=circle.line_width,
                    dash=dash,
                    arrow=tk.LAST  # Add arrowhead at the end of the line
                )
            
            # Draw circle
            circle_id = self.canvas.create_oval(
                circle.x - circle.radius, circle.y - circle.radius,
                circle.x + circle.radius, circle.y + circle.radius,
                fill=circle.color,
                outline=circle.border_color,
                width=circle.border_width
            )
            
            # Store canvas ID for future reference
            circle.canvas_id = circle_id
            
            # Draw text in circle
            self.canvas.create_text(
                circle.x, circle.y,
                text=circle.text,
                fill=circle.text_color,
                font=(circle.font_family, circle.font_size, "bold")
            )
            
            print(f"  Circle {circle.id} drawn on canvas")

    # Modify the draw_wall method to include drawing annotations
    def draw_wall_with_annotations(self, panels: List[Panel]):
        print("DRAW_WALL_WITH_ANNOTATIONS: Starting")
        # First call the original method
        self.draw_wall(panels)
        
        # Then draw annotations on top
        print(f"  Now drawing {len(self.annotation_circles)} annotations")
        self.draw_annotations()
        print("DRAW_WALL_WITH_ANNOTATIONS: Completed")

    # Modify the calculate method to use the updated drawing function
    def calculate_with_annotations(self):
        panels = self.calculate_panels()
        self.draw_wall_with_annotations(panels)
        
        # The rest of the original calculate method content
        summary = []
        summary.append(f"Wall dimensions: {self.format_dimension(self.wall_dimensions['width'], self.wall_dimensions.get('width_fraction', '0'))} × "
                     f"{self.format_dimension(self.wall_dimensions['height'], self.wall_dimensions.get('height_fraction', '0'))}")
        
        if self.use_baseboard:
            baseboard_height_inches = self.baseboard_height
            baseboard_fraction = "0"
            
            if hasattr(self, 'baseboard_fraction_var'):
                baseboard_fraction = self.baseboard_fraction_var.get()
                baseboard_height_inches += self.fraction_to_decimal(baseboard_fraction)
                
            baseboard_dim, baseboard_frac = self.convert_to_feet_inches_fraction(baseboard_height_inches)
            summary.append(f"Baseboard height: {self.format_dimension(baseboard_dim, baseboard_frac)}")
            
            usable_height_inches = self.convert_to_inches(
                self.wall_dimensions['height'].feet, 
                self.wall_dimensions['height'].inches,
                self.wall_dimensions.get('height_fraction', '0')
            ) - baseboard_height_inches
            
            usable_height_dim, usable_height_frac = self.convert_to_feet_inches_fraction(usable_height_inches)
            summary.append(f"Usable height: {self.format_dimension(usable_height_dim, usable_height_frac)}")

        summary.append(f"\nNumber of panels: {len(panels)}")
        summary.append(f"Panel color: {self.panel_color}")
        
        for i, panel in enumerate(panels, 1):
            summary.append(f"\nPanel {i}:")
            summary.append(f"  Width: {self.format_dimension(panel.actual_width, panel.actual_width_fraction)}")
            summary.append(f"  Height: {self.format_dimension(panel.height, panel.height_fraction)}")
            summary.append(f"  Position: {panel.x:.1f}% from left")

        # Add annotation summary
        if self.annotation_circles:
            summary.append(f"\nAnnotations: {len(self.annotation_circles)}")

        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert("1.0", "\n".join(summary))

    # Update the create_tabbed_interface method to include annotations tab
    def create_tabbed_interface_with_annotations(self):
        """Create a two-column layout with tabs on left, canvas on right"""
        # Create main container frame
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create left and right columns
        left_frame = ctk.CTkFrame(self.main_container, width=460)  # Fixed width for controls
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_frame.pack_propagate(False)  # Prevent shrinking
        
        right_frame = ctk.CTkFrame(self.main_container)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add tabs to the left frame
        self.tab_view = ctk.CTkTabview(left_frame)
        self.tab_view.pack(fill=tk.BOTH, expand=True)
        
        # Add tabs for different sections
        self.tab_wall = self.tab_view.add("Wall & Panels")
        self.tab_objects = self.tab_view.add("Objects")
        self.tab_annotations = self.tab_view.add("Annotations")
        self.tab_export = self.tab_view.add("Export")
        self.tab_advanced = self.tab_view.add("Advanced")
        self.tab_summary = self.tab_view.add("Summary")
        self.tab_about = self.tab_view.add("About")
        
        # Create scrollable frames for each tab
        self.wall_frame = self.create_scrollable_frame(self.tab_wall)
        self.objects_frame = self.create_scrollable_frame(self.tab_objects)
        self.annotations_frame = self.create_scrollable_frame(self.tab_annotations)
        self.summary_frame = self.create_scrollable_frame(self.tab_summary)  # Create frame for summary tab
        self.export_frame = self.create_scrollable_frame(self.tab_export)
        self.advanced_frame = self.create_scrollable_frame(self.tab_advanced)
        self.about_frame = self.create_scrollable_frame(self.tab_about)
        
        # Create canvas in right frame
        self.canvas_frame = ctk.CTkFrame(right_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Create summary text in the Summary tab instead of at the bottom of right frame
        self.summary_text = ctk.CTkTextbox(self.summary_frame, height=600)  # Increased height for better viewing
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Populate the tabs with their respective controls
        self.create_wall_panel_controls(self.wall_frame)
        self.create_object_controls(self.objects_frame)
        self.create_annotation_controls(self.annotations_frame)
        self.create_export_controls(self.export_frame)
        self.create_advanced_controls(self.advanced_frame)
        self.create_summary_controls(self.summary_frame) 
        self.create_about_controls(self.about_frame)
        
        # Initialize annotation system
        self.initialize_annotation_system()

    def create_summary_controls(self, parent):
        """Create controls for the Summary tab"""
        # Create a frame for actions/settings related to summary
        control_frame = ctk.CTkFrame(parent)
        control_frame.pack(fill=tk.X, padx=10, pady=(0, 10), before=self.summary_text)
        
        # Add refresh button
        refresh_btn = ctk.CTkButton(
            control_frame,
            text="Refresh Summary",
            command=self.calculate,
            fg_color="#1E88E5",
            hover_color="#1565C0"
        )
        refresh_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Add copy to clipboard button
        copy_btn = ctk.CTkButton(
            control_frame,
            text="Copy to Clipboard",
            command=self.copy_summary_to_clipboard,
            fg_color="#757575",
            hover_color="#616161"
        )
        copy_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Add heading above the summary text
        heading_label = ctk.CTkLabel(
            parent,
            text="Panel Summary",
            font=("Arial", 16, "bold")
        )
        heading_label.pack(before=self.summary_text, pady=(0, 5))

    # Add the copy summary to clipboard method
    def copy_summary_to_clipboard(self):
        """Copy the summary text to clipboard"""
        # This method is called when the Copy to Clipboard button is clicked
        self.clipboard_clear()
        self.clipboard_append(self.summary_text.get("1.0", tk.END))
        
        # Show a small temporary label indication that copying was successful
        success_label = ctk.CTkLabel(
            self.summary_frame,
            text="Copied to clipboard!",
            fg_color="#4CAF50",
            text_color="white",
            corner_radius=8,
            padx=10,
            pady=5
        )
        success_label.pack(pady=10)
        
        # Auto-hide the success message after 2 seconds
        self.after(2000, success_label.destroy)

    # Fix the toggle_horizontal_position_mode function to properly show/hide UI elements
    def toggle_horizontal_position_mode(self):
        """Toggle between alignment and exact horizontal positioning"""
        if self.use_exact_h_position_var.get():
            # Using exact positioning - show position inputs, hide alignment
            self.h_position_inputs.pack(pady=5, fill=tk.X, after=self.vertical_pos_frame)
            self.alignment_frame.pack_forget()
        else:
            # Using alignment - hide position inputs, show alignment
            self.h_position_inputs.pack_forget()
            self.alignment_frame.pack(pady=5, fill=tk.X, after=self.vertical_pos_frame)
            
    def show_alignment_info(self):
        """Show information about alignment options"""
        info_text = (
            "Alignment Options:\n\n"
            "Center: Places the object centered between the leftmost and rightmost selected panels.\n\n"
            "Left Edge: Aligns the left edge of the object with the left edge of the leftmost selected panel.\n\n"
            "Right Edge: Aligns the right edge of the object with the right edge of the rightmost selected panel.\n\n"
            "This is especially useful when placing objects wider than a single panel."
        )
        messagebox.showinfo("Object Alignment Help", info_text)
    def create_export_controls(self, parent):
        """Create export controls for the Export tab"""
        # Project details section
        details_section = ctk.CTkFrame(parent)
        details_section.pack(pady=10, fill=tk.X)
        
        ctk.CTkLabel(details_section, text="Project Details", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Project name
        project_frame = ctk.CTkFrame(details_section)
        project_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(project_frame, text="Project Name:").pack(side=tk.LEFT, padx=5)
        self.project_name_var = tk.StringVar()
        project_entry = ctk.CTkEntry(project_frame, textvariable=self.project_name_var)
        project_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Date
        date_frame = ctk.CTkFrame(details_section)
        date_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(date_frame, text="Date:").pack(side=tk.LEFT, padx=5)
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        date_entry = ctk.CTkEntry(date_frame, textvariable=self.date_var)
        date_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Export options section
        export_section = ctk.CTkFrame(parent)
        export_section.pack(pady=10, fill=tk.X)
        
        ctk.CTkLabel(export_section, text="Export Options", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Format selection
        format_frame = ctk.CTkFrame(export_section)
        format_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(format_frame, text="Format:").pack(side=tk.LEFT, padx=5)
        
        self.export_format_var = tk.StringVar(value="EPS (Vector Format)")
        export_options = [
            "TIFF (Ultra-HD Print Quality)", 
            "PNG (Ultra-HD Quality)", 
            "JPEG (High Quality)",
            "SVG (Vector Format)", 
            "PDF (Document Format)", 
            "EPS (Vector Format)"
        ]

        format_dropdown = ctk.CTkOptionMenu(
            format_frame,
            variable=self.export_format_var,
            values=export_options,
            width=250
        )
        format_dropdown.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Quality level
        quality_frame = ctk.CTkFrame(export_section)
        quality_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(quality_frame, text="Quality Level:").pack(side=tk.LEFT, padx=5)
        
        self.quality_level_var = tk.StringVar(value="Ultra-HD (6x)")
        quality_options = ["Standard (2x)", "High (4x)", "Ultra-HD (6x)", "Maximum (8x)"]
        
        quality_dropdown = ctk.CTkOptionMenu(
            quality_frame,
            variable=self.quality_level_var,
            values=quality_options,
            width=150
        )
        quality_dropdown.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Export button
        export_btn = ctk.CTkButton(
            export_section,
            text="Export",
            command=self.export_selected_format,
            fg_color="#1E88E5",
            hover_color="#1565C0",
            height=40
        )
        export_btn.pack(pady=15, fill=tk.X)

        export_horizontal_btn = ctk.CTkButton(
            export_section,
            text="Export All Walls (Horizontal Layout)",
            command=self.export_all_walls_horizontal,
            fg_color="#1E88E5",
            hover_color="#1565C0",
            height=40
        )
        export_horizontal_btn.pack(pady=10, fill=tk.X)
    def create_walls_tab_interface(self):
        """Create a tab interface for multiple walls"""
        # Create a frame for wall tabs at the top of the canvas area
        # In the create_walls_tab_interface method
        self.walls_tab_frame = ctk.CTkFrame(self.canvas_frame, height=100)  # Set your desired height here
        self.walls_tab_frame.pack(fill=tk.X, side=tk.TOP)
        self.walls_tab_frame.pack_propagate(False)  #         # Add wall tabs view - set a minimum width to ensure tabs are visible
        self.walls_tabview = ctk.CTkTabview(self.walls_tab_frame, width=400)  # Wider tabview
        self.walls_tabview.pack(fill=tk.X)
        
        # Initialize tracking variables
        self.walls = []
        self.current_wall_id = 1
        self.current_active_wall_id = None
        self.switching_walls = False
        
        # Add initial wall
        initial_wall = self.add_wall("Wall 1")
        self.current_active_wall_id = initial_wall.id
        
        # Add a "+" tab for adding new walls
        self.add_wall_tab = self.walls_tabview.add("+")
        add_wall_button = ctk.CTkButton(
            self.add_wall_tab, 
            text="Add New Wall", 
            command=self.add_new_wall
        )
        add_wall_button.pack(pady=10)
        
        # Configure tab change event
        self.walls_tabview.configure(command=self.on_wall_tab_change)
        
        # Force selection of the first wall tab
        self.walls_tabview.set("Wall 1")
        
        # Make all tabs visible

        self.walls_tabview._segmented_button.configure(dynamic_resizing=True)
        
        # Make sure data is properly initialized
        self.update_wall_status()



    def add_wall(self, name="New Wall", width_feet=8, width_inches=0, height_feet=10, height_inches=0):
        # Create with custom dimensions
        wall = Wall(
            id=self.current_wall_id,
            name=name,
            dimensions={
                "width": Dimension(width_feet, width_inches),
                "width_fraction": "0",
                "height": Dimension(height_feet, height_inches),
                "height_fraction": "0"
            }
        )
        
        # Add to walls list
        self.walls.append(wall)
        
        # Create tab for this wall
        tab = self.walls_tabview.add(name)
        tab.wall_id = self.current_wall_id  # Store ID in tab for reference
        
        # Add wall control buttons
        controls_frame = ctk.CTkFrame(tab)
        controls_frame.pack(fill=tk.X, pady=5)
        
        # Rename button
        rename_btn = ctk.CTkButton(
            controls_frame,
            text="Rename Wall",
            command=lambda id=self.current_wall_id: self.rename_wall(id)
        )
        rename_btn.pack(side=tk.LEFT, padx=5)
        
        # Delete button
        delete_btn = ctk.CTkButton(
            controls_frame,
            text="Delete Wall",
            fg_color="#E53935",
            hover_color="#C62828",
            command=lambda id=self.current_wall_id: self.delete_wall(id)
        )
        delete_btn.pack(side=tk.LEFT, padx=5)
        
        # Duplicate button
        duplicate_btn = ctk.CTkButton(
            controls_frame,
            text="Duplicate Wall",
            command=lambda id=self.current_wall_id: self.duplicate_wall(id)
        )
        duplicate_btn.pack(side=tk.LEFT, padx=5)
        
        # Store the new wall's ID before incrementing
        new_wall_id = self.current_wall_id
        
        # Increment ID counter
        self.current_wall_id += 1
        
        # Select this tab
        self.walls_tabview.set(name)
        
        return wall


    def add_new_wall(self):
        """Add a new wall when the + tab is clicked"""
        # Create a unique name for the new wall
        new_wall_name = f"Wall {len(self.walls) + 1}"
        
        # Create the new wall with default dimensions and proper initialization
        new_wall = Wall(
            id=self.current_wall_id,
            name=new_wall_name,
            dimensions={
                "width": Dimension(8, 0),
                "width_fraction": "0",
                "height": Dimension(10, 0),
                "height_fraction": "0"
            },
            panel_dimensions={
                "width": Dimension(4, 0),
                "width_fraction": "0",
                "height": Dimension(10, 0),
                "height_fraction": "0"
            }
        )
        
        # Add to walls list
        self.walls.append(new_wall)
        
        # Create tab for this wall
        tab = self.walls_tabview.add(new_wall_name)
        tab.wall_id = self.current_wall_id  # Store ID in tab for reference
        
        # Add wall control buttons
        controls_frame = ctk.CTkFrame(tab)
        controls_frame.pack(fill=tk.X, pady=5)
        
        # Rename button
        rename_btn = ctk.CTkButton(
            controls_frame,
            text="Rename Wall",
            command=lambda id=self.current_wall_id: self.rename_wall(id)
        )
        rename_btn.pack(side=tk.LEFT, padx=5)
        
        # Delete button
        delete_btn = ctk.CTkButton(
            controls_frame,
            text="Delete Wall",
            fg_color="#E53935",
            hover_color="#C62828",
            command=lambda id=self.current_wall_id: self.delete_wall(id)
        )
        delete_btn.pack(side=tk.LEFT, padx=5)
        
        # Duplicate button
        duplicate_btn = ctk.CTkButton(
            controls_frame,
            text="Duplicate Wall",
            command=lambda id=self.current_wall_id: self.duplicate_wall(id)
        )
        duplicate_btn.pack(side=tk.LEFT, padx=5)
        
        # Store the new wall's ID before incrementing
        new_wall_id = self.current_wall_id
        
        # Increment ID counter
        self.current_wall_id += 1
        
        # CRITICAL: Update the current_active_wall_id to the new wall's ID
        self.current_active_wall_id = new_wall_id
        
        # Explicitly update UI with the new wall's dimensions
        self.wall_width_feet_var.set(str(new_wall.dimensions["width"].feet))
        self.wall_width_inches_var.set(str(new_wall.dimensions["width"].inches))
        self.wall_width_fraction_var.set(new_wall.dimensions.get("width_fraction", "0"))
        
        self.wall_height_feet_var.set(str(new_wall.dimensions["height"].feet))
        self.wall_height_inches_var.set(str(new_wall.dimensions["height"].inches))
        self.wall_height_fraction_var.set(new_wall.dimensions.get("height_fraction", "0"))
        
        # Also update panel dimensions
        if hasattr(new_wall, 'panel_dimensions'):
            pd = new_wall.panel_dimensions
            self.panel_width_feet_var.set(str(pd["width"].feet))
            self.panel_width_inches_var.set(str(pd["width"].inches))
            self.panel_width_fraction_var.set(pd.get("width_fraction", "0"))
            
            self.panel_height_feet_var.set(str(pd["height"].feet))
            self.panel_height_inches_var.set(str(pd["height"].inches))
            self.panel_height_fraction_var.set(pd.get("height_fraction", "0"))
        
        # CRITICAL: Initialize other properties to defaults for the new wall
        self.use_equal_panels = False
        self.equal_panels_var.set(False)
        self.panel_count = 2
        self.panel_count_var.set("2")
        self.use_center_panels = False
        self.center_panels_var.set(False)
        self.center_panel_count = 4
        self.center_panel_count_var.set("4")
        self.use_baseboard = False
        self.baseboard_var.set(False)
        self.baseboard_height = 4
        self.baseboard_height_var.set("4")
        self.panel_color = "#FFFFFF"
        self.panel_border_color = "red"
        
        # Reset custom panel widths and objects for the new wall
        self.custom_panel_widths = {}
        self.split_panels = {}
        self.wall_objects = []
        self.selected_panels = []
        self.annotation_circles = []
        self.next_object_id = 1
        self.next_annotation_id = 1
        
        # Update UI visuals
        if hasattr(self, 'color_preview'):
            self.color_preview.configure(bg=self.panel_color)
        if hasattr(self, 'border_color_preview'):
            self.border_color_preview.configure(bg=self.panel_border_color)
        
        # Set the new tab as active
        self.walls_tabview.set(new_wall_name)
        
        # Update wall status
        self.update_wall_status()
        
        # Force a redraw
        self.switching_walls = False
        self.calculate()
        
        print(f"Created new wall: {new_wall_name} (ID: {new_wall_id})")
        
        return new_wall


    def rename_wall(self, wall_id):
        """Rename the specified wall"""
        # Find the wall
        wall = next((w for w in self.walls if w.id == wall_id), None)
        if not wall:
            return
        
        # Get new name from user
        dialog = ctk.CTkInputDialog(
            text="Enter new wall name:",
            title="Rename Wall"
        )
        new_name = dialog.get_input()
        
        if new_name and new_name.strip():
            old_name = wall.name
            wall.name = new_name.strip()
            
            # Find the current tab name
            old_tab_name = None
            for tab_name in self.walls_tabview._tab_dict:
                if tab_name != "+" and hasattr(self.walls_tabview._tab_dict[tab_name], 'wall_id'):
                    if self.walls_tabview._tab_dict[tab_name].wall_id == wall_id:
                        old_tab_name = tab_name
                        break
            
            if old_tab_name:
                # Add new tab with updated name
                new_tab = self.walls_tabview.add(new_name)
                new_tab.wall_id = wall_id
                
                # Instead of moving widgets, recreate them in the new tab
                controls_frame = ctk.CTkFrame(new_tab)
                controls_frame.pack(fill=tk.X, pady=5)
                
                # Recreate buttons in the new tab
                rename_btn = ctk.CTkButton(
                    controls_frame,
                    text="Rename Wall",
                    command=lambda id=wall_id: self.rename_wall(id)
                )
                rename_btn.pack(side=tk.LEFT, padx=5)
                
                delete_btn = ctk.CTkButton(
                    controls_frame,
                    text="Delete Wall",
                    fg_color="#E53935",
                    hover_color="#C62828",
                    command=lambda id=wall_id: self.delete_wall(id)
                )
                delete_btn.pack(side=tk.LEFT, padx=5)
                
                duplicate_btn = ctk.CTkButton(
                    controls_frame,
                    text="Duplicate Wall",
                    command=lambda id=wall_id: self.duplicate_wall(id)
                )
                duplicate_btn.pack(side=tk.LEFT, padx=5)
                
                # Select new tab
                self.walls_tabview.set(new_name)
                
                # Remove old tab
                self.walls_tabview.delete(old_tab_name)

    def delete_wall(self, wall_id):
        """Delete the specified wall"""
        # Confirm deletion
        if len(self.walls) <= 1:
            messagebox.showerror("Error", "Cannot delete the only wall. Create a new wall first.")
            return
            
        if not messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this wall?"):
            return
        
        # Find the wall
        wall_index = None
        for i, wall in enumerate(self.walls):
            if wall.id == wall_id:
                wall_index = i
                break
        
        if wall_index is None:
            return
        
        # Find the tab name
        tab_to_delete = None
        for tab_name in self.walls_tabview._tab_dict:
            if tab_name != "+" and hasattr(self.walls_tabview._tab_dict[tab_name], 'wall_id'):
                if self.walls_tabview._tab_dict[tab_name].wall_id == wall_id:
                    tab_to_delete = tab_name
                    break
        
        # Delete the wall
        del self.walls[wall_index]
        
        # Delete the tab
        if tab_to_delete:
            self.walls_tabview.delete(tab_to_delete)
        
        # Select another tab
        if self.walls:
            next_tab = next(tab for tab in self.walls_tabview._tab_dict if tab != "+")
            self.walls_tabview.set(next_tab)
            
            # Load that wall's data
            self.load_current_wall_data()

    def duplicate_wall(self, wall_id):
        """Create a duplicate of the specified wall"""
        # Find the wall
        source_wall = next((w for w in self.walls if w.id == wall_id), None)
        if not source_wall:
            return
        
        # Create new name
        new_name = f"{source_wall.name} Copy"
        
        # Create new wall as a deep copy of the source
        import copy
        new_wall = copy.deepcopy(source_wall)
        new_wall.id = self.current_wall_id
        new_wall.name = new_name
        
        # Add to walls list
        self.walls.append(new_wall)
        
        # Create tab for this wall
        tab = self.walls_tabview.add(new_name)
        tab.wall_id = self.current_wall_id  # Store ID in tab for reference
        
        # Add wall control buttons
        controls_frame = ctk.CTkFrame(tab)
        controls_frame.pack(fill=tk.X, pady=5)
        
        # Rename button
        rename_btn = ctk.CTkButton(
            controls_frame,
            text="Rename Wall",
            command=lambda id=self.current_wall_id: self.rename_wall(id)
        )
        rename_btn.pack(side=tk.LEFT, padx=5)
        
        # Delete button
        delete_btn = ctk.CTkButton(
            controls_frame,
            text="Delete Wall",
            fg_color="#E53935",
            hover_color="#C62828",
            command=lambda id=self.current_wall_id: self.delete_wall(id)
        )
        delete_btn.pack(side=tk.LEFT, padx=5)
        
        # Duplicate button
        duplicate_btn = ctk.CTkButton(
            controls_frame,
            text="Duplicate Wall",
            command=lambda id=self.current_wall_id: self.duplicate_wall(id)
        )
        duplicate_btn.pack(side=tk.LEFT, padx=5)
        
        # Increment ID counter
        self.current_wall_id += 1
        
        # Select this tab
        self.walls_tabview.set(new_name)
        
        # Update UI to show this wall
        
        self.load_current_wall_data()

        
    def export_all_walls_horizontal(self):
        """Export all walls to a single page with walls arranged horizontally with balanced padding
        and only showing wall dimensions, baseboard height, and number of panels."""
        # Validate project details
        if not self.project_name_var.get().strip():
            messagebox.showerror("Error", "Please enter a project name")
            return

        # Only EPS format since that works best
        format_type = "eps"
        extension = ".eps"
        
        # Get save location for the file
        file_name = f"{self.project_name_var.get().replace(' ', '-')}-AllWalls-{self.date_var.get()}{extension}"
        save_path = filedialog.asksaveasfilename(
            defaultextension=extension,
            initialfile=file_name,
            filetypes=[("EPS files", "*.eps")]
        )
        
        if not save_path:
            return
        
        try:
            # Remember the current active wall ID and state to restore it later
            original_wall_id = self.current_active_wall_id
            
            # Store original baseboard state
            original_baseboard_enabled = self.baseboard_var.get()
            original_use_baseboard = self.use_baseboard
            
            # CRITICAL FIX: Make a deep copy of all walls with their current state
            # We'll modify these for processing but keep the originals intact
            import copy
            working_walls = copy.deepcopy(self.walls)
            
            # Show progress dialog
            progress_window = ctk.CTkToplevel(self)
            progress_window.title("Exporting Walls")
            progress_window.geometry("400x150")
            progress_window.transient(self)
            progress_window.grab_set()
            
            progress_label = ctk.CTkLabel(progress_window, text=f"Creating horizontal layout of all walls...")
            progress_label.pack(pady=10)
            
            progress_bar = ctk.CTkProgressBar(progress_window)
            progress_bar.pack(pady=10, padx=20, fill=tk.X)
            progress_bar.set(0)
            
            status_label = ctk.CTkLabel(progress_window, text="Preparing layout...")
            status_label.pack(pady=10)
            
            # Update progress window
            self.update()
            
            # First determine the total layout size needed
            import tempfile
            import os
            import re
            import time
            
            # Create a temporary directory to store individual wall renderings
            temp_dir = tempfile.mkdtemp()
            wall_renders = []
            
            # Process all walls - CRITICAL: Make sure we're including ALL walls
            processed_wall_count = 0
            
            # CRITICAL: First, check each wall's current state and make sure it's recorded
            # This ensures we use the wall's CURRENT state rather than the saved state
            for i, wall in enumerate(working_walls):
                print(f"Checking wall {i+1}: {wall.name} (ID: {wall.id})")
                
                # Find the tab for this wall to check its current state
                tab_name = None
                for tab in self.walls_tabview._tab_dict:
                    if tab != "+" and hasattr(self.walls_tabview._tab_dict[tab], 'wall_id'):
                        if self.walls_tabview._tab_dict[tab].wall_id == wall.id:
                            tab_name = tab
                            break
                
                if tab_name:
                    # Temporarily switch to this wall just to check its current state
                    old_switching = self.switching_walls
                    self.switching_walls = True
                    self.walls_tabview.set(tab_name)
                    self.update()
                    
                    # Check if this is the currently displayed wall
                    is_current_wall = (self.current_active_wall_id == wall.id)
                    
                    if is_current_wall:
                        # If this is the currently displayed wall, get its state from the UI
                        # because the UI represents the latest user changes
                        current_baseboard_state = self.baseboard_var.get()
                        print(f"  Current wall - using UI state: baseboard_enabled={current_baseboard_state}")
                        wall.baseboard_enabled = current_baseboard_state
                    else:
                        # For other walls, we rely on the saved state in the wall object
                        print(f"  Non-current wall - using saved state: baseboard_enabled={wall.baseboard_enabled}")
                    
                    # Go back to switching mode
                    self.switching_walls = old_switching
            
            # CRITICAL: Now process each wall
            for i, wall in enumerate(working_walls):
                progress = (i) / (len(working_walls) * 2)  # First half of progress is layout prep
                progress_bar.set(progress)
                status_label.configure(text=f"Processing wall {i+1}/{len(working_walls)}: {wall.name}")
                self.update()
                
                # Debug print to track wall processing
                print(f"Processing wall {i+1}: {wall.name} (ID: {wall.id})")
                print(f"  Wall baseboard_enabled: {wall.baseboard_enabled}")
                
                # Find the tab for this wall
                tab_name = None
                for tab in self.walls_tabview._tab_dict:
                    if tab != "+" and hasattr(self.walls_tabview._tab_dict[tab], 'wall_id'):
                        if self.walls_tabview._tab_dict[tab].wall_id == wall.id:
                            tab_name = tab
                            break
                            
                if not tab_name:
                    print(f"Could not find tab for wall {wall.name}, skipping")
                    continue
                    
                # Switch to this wall to render it
                old_switching = self.switching_walls
                self.switching_walls = True
                
                # Switch to this wall's tab and load its data
                self.walls_tabview.set(tab_name)
                self.current_active_wall_id = wall.id
                self.load_current_wall_data()
                
                # CRITICAL OVERRIDE: Force the baseboard state to match our working copy
                # This ensures we use the most up-to-date state for each wall
                self.baseboard_var.set(wall.baseboard_enabled)
                self.use_baseboard = wall.baseboard_enabled
                
                # Update UI to match the forced state
                if wall.baseboard_enabled:
                    if hasattr(self, 'baseboard_frame') and self.baseboard_frame.winfo_exists():
                        self.baseboard_frame.pack(pady=5, fill=tk.X)
                else:
                    if hasattr(self, 'baseboard_frame') and self.baseboard_frame.winfo_exists():
                        self.baseboard_frame.pack_forget()
                
                # Force UI update to reflect the changes
                self.update()
                print(f"  After override: self.baseboard_var={self.baseboard_var.get()}, self.use_baseboard={self.use_baseboard}")
                
                # Now calculate layout
                self.switching_walls = False
                self.calculate()
                
                # Allow time for rendering to complete
                self.update()
                time.sleep(0.5)  # Short delay to ensure rendering is complete
                
                # Debug verify the state just before capture
                print(f"  Before capture: self.baseboard_var={self.baseboard_var.get()}, self.use_baseboard={self.use_baseboard}")
                
                # Create temporary EPS file for this wall
                temp_eps_path = os.path.join(temp_dir, f"wall_{i+1}.eps")
                
                # DIRECT CAPTURE: Use the direct canvas postscript method for EPS export
                ps_data = self.canvas.postscript(
                    colormode='color',
                    pagewidth=self.canvas.winfo_width(),
                    pageheight=self.canvas.winfo_height(),
                    x=0, y=0,
                    width=self.canvas.winfo_width(),
                    height=self.canvas.winfo_height()
                )
                
                # Write to the temporary EPS file
                with open(temp_eps_path, 'w') as f:
                    f.write(ps_data)
                
                # Get canvas dimensions
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                
                # Extract summary information for this wall
                wall_summary = {}
                wall_summary['name'] = wall.name
                
                # Wall dimensions - formatted as width x height
                wall_width_dim = self.format_dimension(wall.dimensions["width"], wall.dimensions.get("width_fraction", "0"))
                wall_height_dim = self.format_dimension(wall.dimensions["height"], wall.dimensions.get("height_fraction", "0"))
                wall_summary['dimensions'] = f"{wall_width_dim} x {wall_height_dim}"
                
                # Baseboard height if enabled
                if wall.baseboard_enabled:
                    baseboard_height_inches = wall.baseboard_height
                    if hasattr(wall, 'baseboard_fraction'):
                        baseboard_fraction = wall.baseboard_fraction
                        baseboard_height_inches += self.fraction_to_decimal(baseboard_fraction)
                    baseboard_dim, baseboard_frac = self.convert_to_feet_inches_fraction(baseboard_height_inches)
                    wall_summary['baseboard'] = self.format_dimension(baseboard_dim, baseboard_frac)
                else:
                    wall_summary['baseboard'] = "None"
                
                # Number of panels
                wall_summary['panel_count'] = len(wall.panels)
                
                # Store info about this wall render with the working state
                wall_renders.append({
                    'name': wall.name,
                    'width': canvas_width,
                    'height': canvas_height,
                    'eps_file': temp_eps_path,
                    'has_baseboard': wall.baseboard_enabled,
                    'summary': wall_summary  # Add the summary info to the wall render data
                })
                
                processed_wall_count += 1
                print(f"Successfully processed wall {wall.name} - Total: {processed_wall_count}")
                
                # Reset flag
                self.switching_walls = old_switching
            
            # Check if we processed all walls
            if processed_wall_count != len(working_walls):
                print(f"WARNING: Only processed {processed_wall_count} out of {len(working_walls)} walls")
            
            # Now determine optimal layout with improved spacing
            wall_padding = 150
            top_margin = 150  # Increased top margin to make room for summary info
            side_margin = 120
            bottom_margin = 100
            
            # Determine max height and total width with padding
            max_height = max([wall['height'] for wall in wall_renders]) if wall_renders else 0
            
            # Calculate total width WITH padding between walls
            total_width = sum([wall['width'] for wall in wall_renders])
            
            # Add padding between walls (number of walls minus 1)
            if len(wall_renders) > 1:
                total_width += (len(wall_renders) - 1) * wall_padding
            
            # Calculate layout dimensions with enhanced margins
            layout_width = total_width + (side_margin * 2)
            layout_height = max_height + top_margin + bottom_margin
            
            # Create a single EPS combining all individual EPS files
            progress_bar.set(0.9)
            status_label.configure(text="Creating final EPS file...")
            self.update()
            
            # Create a new PostScript file with required headers
            combined_eps_path = os.path.join(temp_dir, "combined_walls.eps")
            
            with open(combined_eps_path, 'w') as eps_file:
                # Write EPS header
                eps_file.write(f"%!PS-Adobe-3.0 EPSF-3.0\n")
                eps_file.write(f"%%BoundingBox: 0 0 {int(layout_width)} {int(layout_height)}\n")
                eps_file.write(f"%%Pages: 1\n")
                eps_file.write(f"%%EndComments\n\n")
                
                # Add project header text - moved to the left corner with more spacing
                eps_file.write("/Helvetica-Bold findfont 14 scalefont setfont\n")
                eps_file.write(f"{side_margin / 2} {layout_height - 20} moveto\n")
                eps_file.write(f"(Project: {self.project_name_var.get()}) show\n\n")
                
                eps_file.write("/Helvetica findfont 12 scalefont setfont\n")
                eps_file.write(f"{side_margin / 2} {layout_height - 40} moveto\n")
                eps_file.write(f"(Date: {self.date_var.get()}) show\n\n")
                
                # Place each wall's EPS content
                current_x = side_margin
                for i, wall_info in enumerate(wall_renders):
                    # Get the EPS file path
                    wall_eps_path = wall_info['eps_file']
                    
                    # Get summary info
                    summary = wall_info['summary']
                    
                    # Add wall name at the top center of each wall, far enough above the wall
                    eps_file.write("/Helvetica-Bold findfont 14 scalefont setfont\n")
                    name_x = current_x + (wall_info['width'] / 2)
                    eps_file.write(f"{name_x} {top_margin - 30} moveto\n")
                    eps_file.write(f"({wall_info['name']}) dup stringwidth pop 2 div neg 0 rmoveto show\n\n")
                    
                    # Add summary information below the name, but still above the wall
                    eps_file.write("/Helvetica findfont 10 scalefont setfont\n")
                    
                    # Arrange summary info in a compact box to the right of each wall
                    info_x = current_x + 10
                    info_y = top_margin - 50 # Start position for info, above the wall
                    
                    # Wall dimensions
                    eps_file.write(f"{info_x} {info_y} moveto\n")
                    eps_file.write(f"(Dimensions: {summary['dimensions']}) show\n\n")
                    
                    # Baseboard
                    baseboard_text = summary['baseboard']
                    if baseboard_text != "None":
                        # Ensure baseboard measurement has the dash as well
                        baseboard_text = baseboard_text.replace("' ", "'-")
                    eps_file.write(f"{info_x} {info_y - 15} moveto\n")
                    eps_file.write(f"(Baseboard: {baseboard_text}) show\n\n")
                    
                    # Panel count
                    eps_file.write(f"{info_x} {info_y - 30} moveto\n")
                    eps_file.write(f"(Panels: {summary['panel_count']}) show\n\n")
                    
                    # Include the wall EPS content with proper positioning
                    eps_file.write(f"gsave\n")
                    eps_file.write(f"{current_x} {top_margin} translate\n")
                    
                    # Include EPS content
                    if os.path.exists(wall_eps_path):
                        try:
                            with open(wall_eps_path, 'r') as wall_eps:
                                # Skip the EPS header
                                for line in wall_eps:
                                    if line.startswith("%%EndComments"):
                                        break
                                
                                # Now read the actual EPS content
                                eps_content = wall_eps.read()
                                eps_file.write(eps_content)
                        except Exception as e:
                            print(f"Error including EPS content: {str(e)}")
                            # Try reopening the file and reading all content
                            try:
                                with open(wall_eps_path, 'r') as wall_eps:
                                    wall_eps.seek(0)
                                    eps_content = wall_eps.read()
                                    eps_file.write(eps_content)
                            except Exception as e2:
                                print(f"Failed again: {str(e2)}")
                    
                    eps_file.write(f"grestore\n\n")
                    
                    # Move to next wall position
                    current_x += wall_info['width'] + wall_padding
                
                # End the EPS file
                eps_file.write("%%EOF\n")
            
            # Copy to final destination
            import shutil
            shutil.copy2(combined_eps_path, save_path)
            
            # Check if the EPS file was created successfully
            success = os.path.exists(save_path) and os.path.getsize(save_path) > 0
            
            # Clean up temporary files
            progress_bar.set(1.0)
            status_label.configure(text="Cleaning up...")
            self.update()
            
            try:
                # Clean up temporary directory
                if success:
                    shutil.rmtree(temp_dir)
            except:
                pass
            
            # Close progress window
            progress_bar.set(1.0)
            status_label.configure(text="Export complete!")
            self.update()
            progress_window.after(1000, progress_window.destroy)
            
            # Restore the original wall
            self.switching_walls = True
            for wall in self.walls:
                if wall.id == original_wall_id:
                    tab_name = wall.name
                    self.walls_tabview.set(tab_name)
                    break
            self.current_active_wall_id = original_wall_id
            
            # Restore original baseboard state
            self.baseboard_var.set(original_baseboard_enabled)
            self.use_baseboard = original_use_baseboard
            
            # Load the original data without saving
            self.load_current_wall_data()
            self.switching_walls = False
            self.calculate()
            
            if success:
                messagebox.showinfo("Success", f"All walls exported to EPS with balanced padding: {save_path}")
            else:
                messagebox.showerror("Error", "Failed to create EPS file")
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export all walls: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Close progress window if it exists
            if 'progress_window' in locals():
                progress_window.destroy()
        
        # Restore UI state if needed
        self.switching_walls = False
        self.calculate()


    
    def on_wall_tab_change(self):
        """Handle tab change event"""
        try:
            # Set flag to indicate we're switching walls
            self.switching_walls = True
            
            # Get the current tab
            current_tab = self.walls_tabview.get()
            print(f"Changed to tab: {current_tab}")
            
            # Save data from the current wall before switching
            if self.current_active_wall_id is not None:
                old_wall = None
                for wall in self.walls:
                    if wall.id == self.current_active_wall_id:
                        old_wall = wall
                        break
                        
                if old_wall:
                    print(f"Saving data from: {old_wall.name}")
                    self.save_current_wall_data()
            
            # If the "+" tab is selected, add a new wall
            if current_tab == "+":
                print("Adding new wall...")
                new_wall = self.add_new_wall()
                # Don't return here - the new wall becomes the current wall
            else:
                # Load data for the selected wall
                print(f"Loading wall data for {current_tab}")
                
                # Find the wall object for the selected tab
                new_wall = None
                for wall in self.walls:
                    if wall.name == current_tab:
                        new_wall = wall
                        break
                
                if not new_wall:
                    print(f"Error: Could not find wall for tab {current_tab}")
                    self.switching_walls = False
                    return
                
                # Important: Store the new active wall ID
                self.current_active_wall_id = new_wall.id
                
                # Load the wall data
                self.load_current_wall_data()
            
            # Update window title and wall status header
            self.title(f"Wallcovering Calculator - {current_tab}")
            self.update_wall_status()
            
            # Clear the switching flag and force a redraw
            self.switching_walls = False
            self.calculate()
            
        except Exception as e:
            print(f"Error during tab change: {e}")
            import traceback
            traceback.print_exc()
            self.switching_walls = False  # Reset flag in case of error
    def update_wall_status(self):
        """Update status to show current wall info"""
        current_wall = self.get_current_wall()
        if not current_wall:
            return
        
        # If we don't have a status label yet, create one
        if not hasattr(self, 'wall_status_label'):
            self.wall_status_label = ctk.CTkLabel(
                self.canvas_frame,
                text="",
                corner_radius=0,
                fg_color="white",
                text_color="black",
                width=200,
                height=25
            )
            self.wall_status_label.place(x=10, y=10)
        
        # Update the label text
        print(f"Updating wall status header to: {current_wall.name} (ID: {current_wall.id})")
        self.wall_status_label.configure(text=f"Active: {current_wall.name}")
        
        # Force the label to be on top of everything else
        self.wall_status_label.lift()
        
        # Update the bottom tab display if it exists
        if hasattr(self, 'bottom_tab_frame'):
            # Update which tab is selected
            for button in self.bottom_tab_frame.winfo_children():
                if isinstance(button, ctk.CTkButton) and button.cget("text") == current_wall.name:
                    button.configure(fg_color="#1E88E5")  # Highlight the active tab
                else:
                    button.configure(fg_color="#757575")  # Reset other tabs
    def get_current_wall(self):
        """Get the currently active wall object by ID first, then by tab if necessary"""
        if hasattr(self, 'current_active_wall_id') and self.current_active_wall_id is not None:
            # Look for wall by ID first (more reliable)
            for wall in self.walls:
                if wall.id == self.current_active_wall_id:
                    return wall
                    
        # Fallback to finding by tab name
        current_tab = self.walls_tabview.get()
        
        # If "+" tab, return None
        if current_tab == "+":
            return None
        
        # Find wall by tab name
        for wall in self.walls:
            if wall.name == current_tab:
                # Update the active wall ID for future reference
                if hasattr(self, 'current_active_wall_id'):
                    self.current_active_wall_id = wall.id
                return wall
        
        return None
    def force_save_current_wall(self):
        """Explicitly save the current wall's state"""
        current_wall = self.get_current_wall()
        if not current_wall:
            return
            
        print(f"Force saving wall: {current_wall.name}")
        
        # Direct dimension save is most critical
        current_wall.dimensions = {
            "width": Dimension(
                self.safe_int_conversion(self.wall_width_feet_var.get(), 0),
                self.safe_int_conversion(self.wall_width_inches_var.get(), 0)
            ),
            "width_fraction": self.wall_width_fraction_var.get(),
            "height": Dimension(
                self.safe_int_conversion(self.wall_height_feet_var.get(), 0),
                self.safe_int_conversion(self.wall_height_inches_var.get(), 0)
            ),
            "height_fraction": self.wall_height_fraction_var.get()
        }
        
        # Also save panel dimensions
        current_wall.panel_dimensions = {
            "width": Dimension(
                self.safe_int_conversion(self.panel_width_feet_var.get(), 0),
                self.safe_int_conversion(self.panel_width_inches_var.get(), 0)
            ),
            "width_fraction": self.panel_width_fraction_var.get(),
            "height": Dimension(
                self.safe_int_conversion(self.panel_height_feet_var.get(), 0),
                self.safe_int_conversion(self.panel_height_inches_var.get(), 0)
            ),
            "height_fraction": self.panel_height_fraction_var.get()
        }
        
        # Save the complete state (optional)
        self.save_current_wall_data()
    def setup_variable_traces(self):
        """Set up variable traces to prevent excessive calculations"""
        
        # Use a delay timer for dimension changes
        def delayed_calculate(*args):
            if hasattr(self, '_calc_timer'):
                self.after_cancel(self._calc_timer)
            self._calc_timer = self.after(200, self.calculate)  # 200ms delay
        
        # Trace dimension variables with delay
        self.wall_width_feet_var.trace_add("write", delayed_calculate)
        self.wall_width_inches_var.trace_add("write", delayed_calculate)
        self.wall_height_feet_var.trace_add("write", delayed_calculate)
        self.wall_height_inches_var.trace_add("write", delayed_calculate)        
    def load_current_wall_data(self):
        """Optimized wall data loading with calculation prevention"""
        current_wall = self.get_current_wall()
        if not current_wall:
            return
        
        print(f"LOAD: Loading wall: {current_wall.name} (ID: {current_wall.id}) with height {current_wall.dimensions['height'].feet}'{current_wall.dimensions['height'].inches}\"")
        
        # Temporarily prevent calculations during loading
        old_calc_flag = getattr(self, 'calculation_in_progress', False)
        self.calculation_in_progress = True
        
        try:
            # Update UI elements with current wall data
            self.wall_width_feet_var.set(str(current_wall.dimensions["width"].feet))
            self.wall_width_inches_var.set(str(current_wall.dimensions["width"].inches))
            self.wall_width_fraction_var.set(current_wall.dimensions.get("width_fraction", "0"))
            
            self.wall_height_feet_var.set(str(current_wall.dimensions["height"].feet))
            self.wall_height_inches_var.set(str(current_wall.dimensions["height"].inches))
            self.wall_height_fraction_var.set(current_wall.dimensions.get("height_fraction", "0"))
            
            # Update panel dimensions
            if hasattr(current_wall, 'panel_dimensions'):
                pd = current_wall.panel_dimensions
                self.panel_width_feet_var.set(str(pd["width"].feet))
                self.panel_width_inches_var.set(str(pd["width"].inches))
                self.panel_width_fraction_var.set(pd.get("width_fraction", "0"))
                
                self.panel_height_feet_var.set(str(pd["height"].feet))
                self.panel_height_inches_var.set(str(pd["height"].inches))
                self.panel_height_fraction_var.set(pd.get("height_fraction", "0"))
            
            # Load all other properties...
            self.equal_panels_var.set(current_wall.use_equal_panels)
            self.panel_count_var.set(str(current_wall.panel_count))
            self.center_panels_var.set(current_wall.use_center_panels)
            self.center_panel_count_var.set(str(current_wall.center_panel_count))
            
            # Load colors
            self.panel_color = current_wall.panel_color
            self.panel_border_color = current_wall.panel_border_color
            if hasattr(self, 'color_preview'):
                self.color_preview.configure(bg=self.panel_color)
            if hasattr(self, 'border_color_preview'):
                self.border_color_preview.configure(bg=self.panel_border_color)
            
            # Load other settings...
            if hasattr(self, 'show_dimensions_var'):
                self.show_dimensions_var.set(current_wall.show_dimensions)
            if hasattr(current_wall, 'show_object_distances') and hasattr(self, 'show_object_distances_var'):
                self.show_object_distances_var.set(current_wall.show_object_distances)
            
            # CRITICAL: Load baseboard settings LAST and update UI accordingly
            print(f"  Loading baseboard state: {current_wall.baseboard_enabled}")
            self.baseboard_var.set(current_wall.baseboard_enabled)
            self.use_baseboard = current_wall.baseboard_enabled
            self.baseboard_height = current_wall.baseboard_height
            self.baseboard_height_var.set(str(current_wall.baseboard_height))
            
            # Update UI visibility for baseboard
            if current_wall.baseboard_enabled:
                if hasattr(self, 'baseboard_frame'):
                    self.baseboard_frame.pack(pady=5, fill=tk.X)
            else:
                if hasattr(self, 'baseboard_frame'):
                    self.baseboard_frame.pack_forget()
            
            # Load complex objects
            import copy
            self.custom_panel_widths = copy.deepcopy(current_wall.custom_panel_widths)
            self.split_panels = copy.deepcopy(current_wall.split_panels)
            self.wall_objects = copy.deepcopy(current_wall.wall_objects)
            self.selected_panels = current_wall.selected_panels.copy()
            self.annotation_circles = copy.deepcopy(current_wall.annotation_circles)
            
            print(f"LOAD: Completed loading {current_wall.name}")
            
        finally:
            # Restore calculation flag
            self.calculation_in_progress = old_calc_flag
        
        # Force a single calculation after loading is complete
        self.after_idle(self.calculate)

    def update_ui_visibility(self):
        """Update UI element visibility based on current settings"""
        print(f"Updating UI visibility - baseboard_var: {self.baseboard_var.get()}")
        
        # Show/hide baseboard frame
        if self.baseboard_var.get():
            if hasattr(self, 'baseboard_frame') and self.baseboard_frame.winfo_exists():
                print("  Showing baseboard frame")
                # Force the widget to be packed if it exists
                self.baseboard_frame.pack(pady=5, fill=tk.X)
        else:
            if hasattr(self, 'baseboard_frame') and self.baseboard_frame.winfo_exists():
                print("  Hiding baseboard frame")
                self.baseboard_frame.pack_forget()
        
        # Show/hide floor mounting related controls
        if hasattr(self, 'floor_mounted_var') and not self.floor_mounted_var.get():
            if hasattr(self, 'height_offset_frame'):
                for widget in self.wall_frame.winfo_children():
                    if isinstance(widget, ctk.CTkFrame) and hasattr(widget, 'winfo_children') and len(widget.winfo_children()) > 0:
                        first_child = widget.winfo_children()[0]
                        if hasattr(first_child, 'cget') and first_child.cget("text") == "Panel Options":
                            self.height_offset_frame.pack(in_=widget, pady=5, fill=tk.X)
                            break
        else:
            if hasattr(self, 'height_offset_frame'):
                self.height_offset_frame.pack_forget()
        
        # Show/hide panel layout controls
        if self.equal_panels_var.get():
            if hasattr(self, 'panel_count_frame'):
                self.panel_count_frame.pack(pady=5)
            if hasattr(self, 'center_panel_inputs'):
                self.center_panel_inputs.pack_forget()
        else:
            if hasattr(self, 'panel_count_frame'):
                self.panel_count_frame.pack_forget()
        
        if self.center_panels_var.get():
            if hasattr(self, 'center_panel_inputs'):
                self.center_panel_inputs.pack(pady=5)
            if hasattr(self, 'panel_count_frame'):
                self.panel_count_frame.pack_forget()
        else:
            if hasattr(self, 'center_panel_inputs'):
                self.center_panel_inputs.pack_forget()
                
        # Force update UI to show changes immediately
        self.update()
        

    def save_current_wall_data(self):
        """Save current UI data to the current wall object"""
        current_wall = self.get_current_wall()
        if not current_wall:
            return
        
        print(f"Saving data for wall: {current_wall.name} (ID: {current_wall.id})")
        print(f"  Current baseboard state: UI={self.baseboard_var.get()}, wall={current_wall.baseboard_enabled}")
        
        # Save wall dimensions - explicitly get values from UI variables
        current_wall.dimensions = {
            "width": Dimension(
                self.safe_int_conversion(self.wall_width_feet_var.get(), 0),
                self.safe_int_conversion(self.wall_width_inches_var.get(), 0)
            ),
            "width_fraction": self.wall_width_fraction_var.get(),
            "height": Dimension(
                self.safe_int_conversion(self.wall_height_feet_var.get(), 0),
                self.safe_int_conversion(self.wall_height_inches_var.get(), 0)
            ),
            "height_fraction": self.wall_height_fraction_var.get()
        }
        
        # Save panel dimensions
        current_wall.panel_dimensions = {
            "width": Dimension(
                self.safe_int_conversion(self.panel_width_feet_var.get(), 0),
                self.safe_int_conversion(self.panel_width_inches_var.get(), 0)
            ),
            "width_fraction": self.panel_width_fraction_var.get(),
            "height": Dimension(
                self.safe_int_conversion(self.panel_height_feet_var.get(), 0),
                self.safe_int_conversion(self.panel_height_inches_var.get(), 0)
            ),
            "height_fraction": self.panel_height_fraction_var.get()
        }
        
        # Save panel options
        current_wall.use_equal_panels = self.equal_panels_var.get()
        current_wall.panel_count = self.safe_int_conversion(self.panel_count_var.get(), 2)
        current_wall.use_center_panels = self.center_panels_var.get()
        current_wall.center_panel_count = self.safe_int_conversion(self.center_panel_count_var.get(), 4)
        
        # Save baseboard settings - CRITICAL: Use UI state directly and log it
        current_wall.baseboard_enabled = self.baseboard_var.get()
        current_wall.baseboard_height = self.safe_int_conversion(self.baseboard_height_var.get(), 4)
        if hasattr(self, 'baseboard_fraction_var'):
            current_wall.baseboard_fraction = self.baseboard_fraction_var.get()
        
        print(f"  After save: wall.baseboard_enabled={current_wall.baseboard_enabled}")
        
        # Save floor mounting settings
        current_wall.floor_mounted = self.floor_mounted_var.get()
        
        # Save height offset for non-floor mounted panels
        if hasattr(self, 'floor_mounted_var') and not self.floor_mounted_var.get() and hasattr(self, 'height_offset_feet_var'):
            current_wall.height_offset = Dimension(
                self.safe_int_conversion(self.height_offset_feet_var.get(), 0),
                self.safe_int_conversion(self.height_offset_inches_var.get(), 0)
            )
            if hasattr(self, 'height_offset_fraction_var'):
                current_wall.height_offset_fraction = self.height_offset_fraction_var.get()
        else:
            # Ensure height_offset is set to None if floor mounted
            current_wall.height_offset = None
            current_wall.height_offset_fraction = "0"
        
        # Save colors
        current_wall.panel_color = self.panel_color
        current_wall.panel_border_color = self.panel_border_color
        
        # Save display settings
        current_wall.show_dimensions = self.show_dimensions_var.get()
        if hasattr(self, 'show_object_distances_var'):
            current_wall.show_object_distances = self.show_object_distances_var.get()
        if hasattr(self, 'show_horizontal_distances_var'):
            current_wall.show_horizontal_distances = self.show_horizontal_distances_var.get()
        if hasattr(self, 'distance_reference_var'):
            current_wall.distance_reference = self.distance_reference_var.get()
        
        # Save custom name
        if hasattr(self, 'custom_name_var'):
            current_wall.custom_name = self.custom_name_var.get()
        
        # *** KEY FIX: Calculate and save current panels ***
        current_panels = self.calculate_panels()
        import copy
        current_wall.panels = copy.deepcopy(current_panels)
        
        # Save panel configurations 
        current_wall.custom_panel_widths = copy.deepcopy(self.custom_panel_widths) if hasattr(self, 'custom_panel_widths') else {}
        current_wall.split_panels = copy.deepcopy(self.split_panels) if hasattr(self, 'split_panels') else {}
        current_wall.wall_objects = copy.deepcopy(self.wall_objects) if hasattr(self, 'wall_objects') else []
        current_wall.selected_panels = self.selected_panels.copy() if hasattr(self, 'selected_panels') else []
        current_wall.annotation_circles = copy.deepcopy(self.annotation_circles) if hasattr(self, 'annotation_circles') else []
        
        # Save ID counters
        current_wall.next_object_id = self.next_object_id if hasattr(self, 'next_object_id') else 1
        current_wall.next_annotation_id = self.next_annotation_id if hasattr(self, 'next_annotation_id') else 1
        
        print(f"Wall {current_wall.name} saved with {len(current_wall.panels)} panels and height {current_wall.dimensions['height'].feet}'{current_wall.dimensions['height'].inches}\"")
        print(f"  Final baseboard state: {current_wall.baseboard_enabled}")

    
    def toggle_horizontal_position_mode(self):
        """Toggle between alignment and exact horizontal positioning"""
        if self.use_exact_h_position_var.get():
            # Using exact positioning - show position inputs and references, hide alignment
            self.h_position_inputs.pack(pady=5, fill=tk.X, after=self.vertical_pos_frame)
            self.h_ref_frame.pack(pady=2, fill=tk.X, after=self.h_position_inputs)
            self.alignment_frame.pack_forget()
        else:
            # Using alignment - hide position inputs and references, show alignment
            self.h_position_inputs.pack_forget()
            self.h_ref_frame.pack_forget()
            self.alignment_frame.pack(pady=5, fill=tk.X, after=self.vertical_pos_frame)

    def create_advanced_controls(self, parent):
        """Create advanced controls for the Advanced tab"""
        # Panel width adjustment section
        adjustment_section = ctk.CTkFrame(parent)
        adjustment_section.pack(pady=10, fill=tk.X)
        
        ctk.CTkLabel(adjustment_section, text="Panel Width Adjustments", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Panel ID selection
        id_frame = ctk.CTkFrame(adjustment_section)
        id_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(id_frame, text="Panel ID:").pack(side=tk.LEFT, padx=5)
        self.adjust_panel_id_var = tk.StringVar(value="1")
        id_entry = ctk.CTkEntry(id_frame, textvariable=self.adjust_panel_id_var, width=50)
        id_entry.pack(side=tk.LEFT, padx=5)
        
        # Width input
        width_frame = ctk.CTkFrame(adjustment_section)
        width_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(width_frame, text="Width:").pack(side=tk.LEFT, padx=5)
        
        # Feet
        self.adjust_width_feet_var = tk.StringVar(value="0")
        feet_entry = ctk.CTkEntry(width_frame, textvariable=self.adjust_width_feet_var, width=50)
        feet_entry.pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(width_frame, text="feet").pack(side=tk.LEFT)
        
        # Inches
        self.adjust_width_inches_var = tk.StringVar(value="0")
        inches_entry = ctk.CTkEntry(width_frame, textvariable=self.adjust_width_inches_var, width=50)
        inches_entry.pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(width_frame, text="inches").pack(side=tk.LEFT)
        
        # Fraction
        ctk.CTkLabel(width_frame, text="+").pack(side=tk.LEFT, padx=2)
        self.adjust_width_fraction_var = tk.StringVar(value="0")
        fraction_options = ["0", "1/16", "1/8", "3/16", "1/4", "5/16", "3/8", "7/16", 
                          "1/2", "9/16", "5/8", "11/16", "3/4", "13/16", "7/8", "15/16"]
        
        fraction_dropdown = ctk.CTkOptionMenu(
            width_frame,
            variable=self.adjust_width_fraction_var,
            values=fraction_options,
            width=70
        )
        fraction_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Adjustment buttons
        button_frame = ctk.CTkFrame(adjustment_section)
        button_frame.pack(pady=5, fill=tk.X)
        
        apply_btn = ctk.CTkButton(
            button_frame, 
            text="Apply Width Adjustment",
            command=self.apply_panel_width_adjustment,
            fg_color="#1E88E5",
            hover_color="#1565C0"
        )
        apply_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        reset_btn = ctk.CTkButton(
            button_frame,
            text="Reset All Adjustments",
            command=self.reset_panel_adjustments,
            fg_color="#757575",
            hover_color="#616161"
        )
        reset_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Add any other advanced options here
        # ...


    def create_export_frame(self):
        export_frame = ctk.CTkFrame(self.input_frame)
        export_frame.pack(pady=10, padx=10, fill=tk.X)
        
        ctk.CTkLabel(export_frame, text="Export Details").pack()
        
        # Project name input
        project_frame = ctk.CTkFrame(export_frame)
        project_frame.pack(pady=5, fill=tk.X)
        ctk.CTkLabel(project_frame, text="Project Name:").pack(side=tk.LEFT)
        self.project_name_var = tk.StringVar()
        project_entry = ctk.CTkEntry(project_frame, textvariable=self.project_name_var)
        project_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        
        # Date input
        date_frame = ctk.CTkFrame(export_frame)
        date_frame.pack(pady=5, fill=tk.X)
        ctk.CTkLabel(date_frame, text="Date:").pack(side=tk.LEFT)
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        date_entry = ctk.CTkEntry(date_frame, textvariable=self.date_var)
        date_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Export dropdown and button
        export_options_frame = ctk.CTkFrame(export_frame)
        export_options_frame.pack(pady=5, fill=tk.X)
        
        # Export format dropdown with improved options
        ctk.CTkLabel(export_options_frame, text="Format:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.export_format_var = tk.StringVar(value="TIFF (Ultra-HD Print Quality)")
        export_options = [
            "TIFF (Ultra-HD Print Quality)", 
            "PNG (Ultra-HD Quality)", 
            "JPEG (High Quality)",
            "SVG (Vector Format)", 
            "PDF (Document Format)", 
            "EPS (Vector Format)"
        ]
        
        export_dropdown = ctk.CTkOptionMenu(
            export_options_frame,
            variable=self.export_format_var,
            values=export_options,
            width=200
        )
        export_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Advanced options section
        advanced_frame = ctk.CTkFrame(export_frame)
        advanced_frame.pack(pady=5, fill=tk.X)
        
        # Scale factor option (how much to enlarge)
        scale_frame = ctk.CTkFrame(advanced_frame)
        scale_frame.pack(pady=2, fill=tk.X)
        ctk.CTkLabel(scale_frame, text="Quality Level:").pack(side=tk.LEFT, padx=5)
        
        self.quality_level_var = tk.StringVar(value="Ultra-HD (6x)")
        quality_options = ["Standard (2x)", "High (4x)", "Ultra-HD (6x)", "Maximum (8x)"]
        quality_dropdown = ctk.CTkOptionMenu(
            scale_frame,
            variable=self.quality_level_var,
            values=quality_options,
            width=120
        )
        quality_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Export button
        export_btn = ctk.CTkButton(
            export_options_frame,
            text="Export",
            command=self.export_selected_format,
            fg_color="#1E88E5",
            hover_color="#1565C0",
            width=100
        )
        export_btn.pack(side=tk.LEFT, padx=10)

        
    def export_selected_format(self):
        """Export in the format selected from the dropdown with enhanced quality"""
        format_choice = self.export_format_var.get()
        
        # Validate project name
        if not self.project_name_var.get().strip():
            messagebox.showerror("Error", "Please enter a project name")
            return
        
        # Get the quality level from dropdown if it exists
        quality_level = "Ultra-HD (6x)"
        if hasattr(self, 'quality_level_var'):
            quality_level = self.quality_level_var.get()
        
        # Parse the scale factor from the quality level
        scale_factor = 6  # Default to 6x for Ultra-HD
        if "2x" in quality_level:
            scale_factor = 2
        elif "4x" in quality_level:
            scale_factor = 4
        elif "6x" in quality_level:
            scale_factor = 6
        elif "8x" in quality_level:
            scale_factor = 8
        
        # Call the appropriate export function based on selection
        try:
            if "PDF" in format_choice:
                self.export_enhanced_pdf()
            elif "SVG" in format_choice:
                self.export_enhanced_svg()
            elif "EPS" in format_choice:
                self.export_enhanced_eps()
            elif "PNG" in format_choice or "TIFF" in format_choice or "JPEG" in format_choice:
                self.export_high_res_via_svg(format_choice.split()[0].lower(), scale_factor)
            else:
                messagebox.showerror("Error", "Invalid export format selected")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
 




    def choose_border_color(self):
        """Open color picker and update the panel border color"""
        color = colorchooser.askcolor(color=self.border_color_preview["background"], title="Choose Panel Border Color")
        if color[1]:  # color is ((R, G, B), hex_color)
            self.panel_border_color = color[1]
            self.border_color_preview.configure(bg=self.panel_border_color)
            self.calculate()



    def export_image(self, format_type):
        """Export image in specified format"""
        # Get save location
        file_name = f"{self.project_name_var.get().replace(' ', '-')}-{self.date_var.get()}.{format_type}"
        save_path = filedialog.asksaveasfilename(
            defaultextension=f".{format_type}",
            initialfile=file_name,
            filetypes=[(f"{format_type.upper()} files", f"*.{format_type}")]
        )

        if not save_path:
            return
            
        try:
            # Use our high quality image export function
            # Save the original path
            self.current_export_path = save_path
            # Call the export function
            self.export_high_quality_image()
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during image export: {str(e)}")

    def create_tabbed_interface(self):
        """Create a two-column layout with tabs on left, canvas on right"""
        # Create main container frame
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create left and right columns
        left_frame = ctk.CTkFrame(self.main_container, width=460)  # Fixed width for controls
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_frame.pack_propagate(False)  # Prevent shrinking
        
        right_frame = ctk.CTkFrame(self.main_container)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add tabs to the left frame
        self.tab_view = ctk.CTkTabview(left_frame)
        self.tab_view.pack(fill=tk.BOTH, expand=True)
        
        # Add tabs for different sections
        self.tab_wall = self.tab_view.add("Wall & Panels")
        self.tab_objects = self.tab_view.add("Objects")
        self.tab_export = self.tab_view.add("Export")
        self.tab_advanced = self.tab_view.add("Advanced")
        self.tab_about = self.tab_view.add("About")  # Add new About tab
        
        # Create scrollable frames for each tab
        self.wall_frame = self.create_scrollable_frame(self.tab_wall)
        self.objects_frame = self.create_scrollable_frame(self.tab_objects)
        self.export_frame = self.create_scrollable_frame(self.tab_export)
        self.advanced_frame = self.create_scrollable_frame(self.tab_advanced)
        self.about_frame = self.create_scrollable_frame(self.tab_about) 
        
        # Create canvas in right frame
        self.canvas_frame = ctk.CTkFrame(right_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.canvas = tk.Canvas(self.canvas_frame, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Add summary text at the bottom of right frame
        self.summary_frame = ctk.CTkFrame(right_frame)
        self.summary_frame.pack(fill=tk.X)
        
        self.summary_text = ctk.CTkTextbox(self.summary_frame, height=100)
        self.summary_text.pack(fill=tk.BOTH, expand=True)
        
        # Populate the tabs with their respective controls
        self.create_wall_panel_controls(self.wall_frame)
        self.create_object_controls(self.objects_frame)
        self.create_export_controls(self.export_frame)
        self.create_advanced_controls(self.advanced_frame)
        self.create_about_controls(self.about_frame)
        
    def export_ultra_quality(self):
        """Export canvas at ultra-high resolution using direct rendering instead of screenshots"""
        try:
            from PIL import Image, ImageEnhance, ImageFilter
            import os
            import tempfile
        except ImportError:
            messagebox.showerror("Error", "Required libraries missing. Please install with:\npip install pillow")
            return

        # Get save location
        file_name = f"{self.project_name_var.get().replace(' ', '-')}-{self.date_var.get()}.tiff"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".tiff",
            initialfile=file_name,
            filetypes=[
                ("TIFF (Ultra-HD Print Quality)", "*.tiff"), 
                ("PNG (Ultra-HD Quality)", "*.png"),
                ("JPEG (High Quality)", "*.jpg")
            ]
        )

        if not save_path:
            return

        try:
            # Make sure canvas is fully updated
            self.update()
            self.after(300)  # Longer delay for complete rendering
            
            # Create a temporary file for the PostScript output
            with tempfile.NamedTemporaryFile(suffix='.eps', delete=False) as temp_file:
                temp_path = temp_file.name
                
            # Get the canvas's PostScript representation
            ps_data = self.canvas.postscript(
                colormode='color',
                pagewidth=self.canvas.winfo_width(),
                pageheight=self.canvas.winfo_height(),
                x=0, y=0,
                width=self.canvas.winfo_width(),
                height=self.canvas.winfo_height()
            )
            
            # Write the PostScript data to the temporary file
            with open(temp_path, 'w') as f:
                f.write(ps_data)
                
            # Convert EPS to PIL Image (requires Ghostscript to be installed)
            try:
                img = Image.open(temp_path)
                
                # Calculate super-resolution scaling (6x)
                scale_factor = 6
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                img = img.resize((canvas_width * scale_factor, canvas_height * scale_factor), 
                               resample=Image.LANCZOS)
                
                # Apply a series of advanced image enhancements
                
                # 1. Edge-preserving smoothing to reduce noise while keeping sharp edges
                img = img.filter(ImageFilter.SMOOTH_MORE)
                
                # 2. Apply unsharp mask to sharpen edges
                img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=250, threshold=3))
                
                # 3. Enhance details
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(2.5)
                
                # 4. Improve contrast
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.4)
                
                # 5. Slightly boost color saturation
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(1.2)
                
                # Set ultra-high DPI for printing
                dpi = (1200, 1200)
                
                # Save with optimal format-specific settings
                if save_path.lower().endswith('.jpg') or save_path.lower().endswith('.jpeg'):
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(save_path, 'JPEG', quality=100, dpi=dpi, optimize=True)
                    
                elif save_path.lower().endswith('.tiff'):
                    # Best settings for TIFF - using LZW compression for lossless results
                    img.save(save_path, 'TIFF', compression='tiff_lzw', dpi=dpi)
                    
                else:  # Default to PNG
                    # Use maximum compression level for PNG
                    img.save(save_path, 'PNG', dpi=dpi, compress_level=9)
                    
                messagebox.showinfo("Success", "Canvas exported at ultra-high resolution with advanced processing!")
                
                # Automatically open the image file after saving
                try:
                    if os.name == 'nt':  # Windows
                        os.startfile(save_path)
                    elif os.name == 'posix':  # macOS and Linux
                        if os.uname().sysname == 'Darwin':  # macOS
                            os.system(f'open "{save_path}"')
                        else:  # Linux
                            os.system(f'xdg-open "{save_path}"')
                except:
                    pass  # Silently ignore if we can't open the file
                    
            except Exception as eps_error:
                # If EPS conversion fails, try direct rendering method
                messagebox.showwarning("Notice", 
                                      f"EPS conversion failed: {str(eps_error)}\nFalling back to vector-based rendering.")
                
                # Use direct vector rendering as a fallback
                self.export_direct_vector()
                
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during export: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Try one last fallback method
            try:
                messagebox.showinfo("Notice", "Trying alternative export method...")
                self.export_direct_vector()
            except:
                pass
                
        finally:
            # Clean up the temporary file
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    def export_high_resolution_image(self):
        """Export the wall drawing as a high-resolution image using direct rendering"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import os
            import tempfile
        except ImportError as e:
            messagebox.showerror("Error", f"Required library missing: {str(e)}. Please install with pip.")
            return

        # Get save location with options
        file_name = f"{self.project_name_var.get().replace(' ', '-')}-{self.date_var.get()}.tiff"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".tiff",
            initialfile=file_name,
            filetypes=[
                ("TIFF files (High Resolution)", "*.tiff"), 
                ("PNG files (High Resolution)", "*.png"), 
                ("JPEG files (High Resolution)", "*.jpg")
            ]
        )

        if not save_path:
            return

        try:
            # Make sure canvas is fully updated
            self.update()
            
            # Get original canvas dimensions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Calculate a high-resolution scale factor (6x for maximum quality)
            scale_factor = 6
            target_width = canvas_width * scale_factor
            target_height = canvas_height * scale_factor
            
            # Create a temporary EPS file (best vector format from Tkinter)
            with tempfile.NamedTemporaryFile(suffix='.eps', delete=False) as temp_eps:
                temp_eps_path = temp_eps.name
                
            # Generate a high-quality EPS file
            ps_data = self.canvas.postscript(
                colormode='color',
                pagewidth=canvas_width,
                pageheight=canvas_height,
                x=0, y=0,
                width=canvas_width,
                height=canvas_height
            )
            
            with open(temp_eps_path, 'w') as f:
                f.write(ps_data)
                
            # Use Pillow to convert EPS to high-resolution raster
            # First, need to install Ghostscript for EPS handling
            try:
                from PIL import EpsImagePlugin
                img = Image.open(temp_eps_path)
                
                # Set the target DPI for high resolution
                dpi = 600
                
                # Resize to the target dimensions
                img = img.resize((target_width, target_height), Image.LANCZOS)
                
                # Save in the appropriate format with high quality
                if save_path.lower().endswith('.jpg') or save_path.lower().endswith('.jpeg'):
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(save_path, 'JPEG', quality=95, dpi=(dpi, dpi))
                    
                elif save_path.lower().endswith('.tiff'):
                    img.save(save_path, 'TIFF', compression='tiff_lzw', dpi=(dpi, dpi))
                    
                else:  # Default to PNG
                    img.save(save_path, 'PNG', dpi=(dpi, dpi))
                    
                messagebox.showinfo("Success", f"High-resolution image exported successfully at {dpi} DPI!")
                
            except Exception as eps_error:
                # If EPS conversion fails, fall back to a direct canvas grab method
                messagebox.showwarning("Notice", f"EPS conversion unsuccessful: {str(eps_error)}\nFalling back to direct rendering method.")
                
                # Create a high-resolution image using direct canvas rendering
                # Use pyscreenshot for better quality screenshot if available
                try:
                    import pyscreenshot as ImageGrab
                except ImportError:
                    # Fall back to PIL's ImageGrab if pyscreenshot is not available
                    from PIL import ImageGrab
                
                # Get the canvas coordinates on screen
                canvas_x = self.canvas.winfo_rootx()
                canvas_y = self.canvas.winfo_rooty()
                
                # Grab the canvas region
                img = ImageGrab.grab(bbox=(canvas_x, canvas_y, 
                                           canvas_x + canvas_width, 
                                           canvas_y + canvas_height))
                
                # Resize to high resolution
                img = img.resize((target_width, target_height), Image.LANCZOS)
                
                # Set DPI for high-quality printing
                dpi = 300
                
                # Save with appropriate format
                if save_path.lower().endswith('.jpg') or save_path.lower().endswith('.jpeg'):
                    img.save(save_path, 'JPEG', quality=95, dpi=(dpi, dpi))
                    
                elif save_path.lower().endswith('.tiff'):
                    img.save(save_path, 'TIFF', compression='tiff_lzw', dpi=(dpi, dpi))
                    
                else:  # Default to PNG
                    img.save(save_path, 'PNG', dpi=(dpi, dpi))
                    
                messagebox.showinfo("Success", f"Image exported successfully at {dpi} DPI using direct rendering!")
                
            # Clean up temporary files
            if os.path.exists(temp_eps_path):
                try:
                    os.remove(temp_eps_path)
                except:
                    pass
                    
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during image export: {str(e)}")
            import traceback
            traceback.print_exc()  # Print stack trace for debugging
            
            # Clean up temp file if it exists
            if 'temp_eps_path' in locals() and os.path.exists(temp_eps_path):
                try:
                    os.remove(temp_eps_path)
                except:
                    pass
            
    def export_vector_based_image(self):
        """Export the wall drawing as a vector-based SVG first, then convert to high-resolution raster"""
        try:
            import os
            import tempfile
            from PIL import Image
            import cairosvg  # You may need to install this with pip install cairosvg
        except ImportError as e:
            messagebox.showerror("Error", f"Required library missing: {str(e)}. Please install with pip.")
            return

        # Get save location with better format options
        file_name = f"{self.project_name_var.get().replace(' ', '-')}-{self.date_var.get()}.tiff"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".tiff",
            initialfile=file_name,
            filetypes=[
                ("TIFF files (Vector Quality)", "*.tiff"), 
                ("PNG files (Vector Quality)", "*.png"), 
                ("JPEG files (Vector Quality)", "*.jpg"),
                ("SVG files (Vector Original)", "*.svg")
            ]
        )

        if not save_path:
            return

        try:
            # Create a temporary SVG file
            with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as temp_svg:
                temp_svg_path = temp_svg.name
            
            # First, export to SVG using our improved SVG export method
            # Save to the temporary SVG path
            old_asksaveasfilename = filedialog.asksaveasfilename
            filedialog.asksaveasfilename = lambda **kwargs: temp_svg_path
            self.export_svg_enhanced()  # This uses your existing method to create a clean SVG
            filedialog.asksaveasfilename = old_asksaveasfilename
            
            # If user wants SVG directly, just copy the temp file to destination
            if save_path.lower().endswith('.svg'):
                import shutil
                shutil.copy2(temp_svg_path, save_path)
                os.remove(temp_svg_path)
                messagebox.showinfo("Success", "Vector SVG exported successfully!")
                return
                
            # For raster formats, convert SVG to high-res image
            # Calculate appropriate DPI based on wall dimensions for exceptional detail
            # Higher DPI for smaller walls, lower for larger walls, but always high quality
            wall_width_inches = self.convert_to_inches(
                self.wall_dimensions["width"].feet,
                self.wall_dimensions["width"].inches,
                self.wall_dimensions.get("width_fraction", "0")
            )
            
            # Base DPI on wall width - smaller walls get higher DPI for more detail
            if wall_width_inches <= 48:  # 4 feet or less
                dpi = 1200
            elif wall_width_inches <= 96:  # 8 feet or less
                dpi = 900
            elif wall_width_inches <= 144:  # 12 feet or less
                dpi = 600
            else:  # Larger walls
                dpi = 450
                
            # Convert the SVG to the requested format using cairosvg
            if save_path.lower().endswith('.jpg') or save_path.lower().endswith('.jpeg'):
                # For JPEG, we convert to PNG first then to JPEG to maintain quality
                temp_png = temp_svg_path + '.png'
                cairosvg.svg2png(url=temp_svg_path, write_to=temp_png, dpi=dpi)
                
                # Convert PNG to JPEG with PIL for maximum quality
                img = Image.open(temp_png)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(save_path, 'JPEG', quality=100, dpi=(dpi, dpi))
                os.remove(temp_png)
                
            elif save_path.lower().endswith('.tiff'):
                # For TIFF, direct conversion works well with cairosvg
                cairosvg.svg2png(url=temp_svg_path, write_to=temp_svg_path + '.png', dpi=dpi)
                
                # Convert PNG to TIFF with PIL for maximum quality
                img = Image.open(temp_svg_path + '.png')
                img.save(save_path, 'TIFF', compression='tiff_lzw', dpi=(dpi, dpi))
                os.remove(temp_svg_path + '.png')
                
            else:  # Default to PNG
                cairosvg.svg2png(url=temp_svg_path, write_to=save_path, dpi=dpi)
            
            # Clean up the temporary file
            os.remove(temp_svg_path)
            
            messagebox.showinfo("Success", f"Vector-based image exported successfully at {dpi} DPI!")
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during vector export: {str(e)}")
            import traceback
            traceback.print_exc()  # Print stack trace for debugging
            
            # Clean up temp file if it exists
            if os.path.exists(temp_svg_path):
                try:
                    os.remove(temp_svg_path)
                except:
                    pass
    def create_about_controls(self, parent):
        """Create content for the About tab"""
        # Main about frame
        about_section = ctk.CTkFrame(parent)
        about_section.pack(pady=20, fill=tk.X)
        
        # App title
        app_title = ctk.CTkLabel(
            about_section, 
            text="Wallcovering Calculator", 
            font=("Arial", 20, "bold")
        )
        app_title.pack(pady=(20, 5))
        
        # Version
        version_label = ctk.CTkLabel(
            about_section,
            text="Version 1.0",
            font=("Arial", 14)
        )
        version_label.pack(pady=(0, 20))
        
        # Developer section
        dev_section = ctk.CTkFrame(about_section)
        dev_section.pack(pady=10, padx=20, fill=tk.X)
        
        dev_title = ctk.CTkLabel(
            dev_section,
            text="Developer",
            font=("Arial", 16, "bold")
        )
        dev_title.pack(pady=(10, 5))
        
        # Developer name
        name_label = ctk.CTkLabel(
            dev_section,
            text="John Ortega",
            font=("Arial", 14)
        )
        name_label.pack(pady=5)
        
        # Contact info
        email_label = ctk.CTkLabel(
            dev_section,
            text="johnortega@gmail.com",
            font=("Arial", 14)
        )
        email_label.pack(pady=2)
        
        phone_label = ctk.CTkLabel(
            dev_section,
            text="408-960-3207",
            font=("Arial", 14)
        )
        phone_label.pack(pady=(2, 10))
        
        # Description section
        desc_section = ctk.CTkFrame(about_section)
        desc_section.pack(pady=10, padx=20, fill=tk.X)
        
        desc_title = ctk.CTkLabel(
            desc_section,
            text="Description",
            font=("Arial", 16, "bold")
        )
        desc_title.pack(pady=(10, 5))
        
        description_text = """
The Shop Drawing App is a professional tool for designing and
planning wall panel layouts. It simplifies the creation of
accurate shop drawings, ensuring seamless installation
with precise measurements and customizable configurations.

       Features include:
        • Custom panel dimensions and arrangements
        • Object placement (TVs, artwork, etc.)
        • Baseboard integration
        • High-quality exports in multiple formats
        • Precise measurements with fraction support
        """
        
        desc_label = ctk.CTkLabel(
            desc_section,
            text=description_text,
            font=("Arial", 12),
            justify="left",
            wraplength=600
        )
        desc_label.pack(pady=(5, 10), padx=10)
        
        # Copyright information
        copyright_label = ctk.CTkLabel(
            about_section,
            text=f"© {datetime.now().year} John Ortega. All rights reserved.",
            font=("Arial", 12)
        )
        copyright_label.pack(pady=(20, 10))

    def export_direct_vector(self):
        """Export using a direct vector rendering approach for maximum clarity"""
        import os
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            messagebox.showerror("Error", "Pillow library is required. Please install with: pip install pillow")
            return
            
        # Get save location
        file_name = f"{self.project_name_var.get().replace(' ', '-')}-{self.date_var.get()}.tiff"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".tiff",
            initialfile=file_name,
            filetypes=[
                ("TIFF files (Ultra HD)", "*.tiff"), 
                ("PNG files (Ultra HD)", "*.png")
            ]
        )
        
        if not save_path:
            return
            
        try:
            # Calculate super high resolution dimensions (8x actual size)
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            scale_factor = 8  # 8x larger than screen for ultra-crisp lines
            
            img_width = canvas_width * scale_factor
            img_height = canvas_height * scale_factor
            
            # Create a blank white image at high resolution
            image = Image.new('RGB', (img_width, img_height), color='white')
            draw = ImageDraw.Draw(image)
            
            # Get accurate dimensions from original canvas
            margin = 100 * scale_factor
            
            # Wall dimensions in inches (including fractions)
            wall_width_inches = self.convert_to_inches(
                self.wall_dimensions["width"].feet,
                self.wall_dimensions["width"].inches,
                self.wall_dimensions.get("width_fraction", "0")
            )
            
            wall_height_inches = self.convert_to_inches(
                self.wall_dimensions["height"].feet,
                self.wall_dimensions["height"].inches,
                self.wall_dimensions.get("height_fraction", "0")
            )
            
            # Calculate baseboard height
            baseboard_height_inches = self.baseboard_height
            if hasattr(self, 'baseboard_fraction_var'):
                baseboard_height_inches += self.fraction_to_decimal(self.baseboard_fraction_var.get())
                
            # Calculate visual usable height
            visual_usable_height = wall_height_inches
            if self.use_baseboard:
                visual_usable_height -= baseboard_height_inches
            
            # Calculate scaling for high-resolution rendering
            wall_aspect_ratio = wall_width_inches / wall_height_inches
            image_aspect_ratio = (img_width - 2 * margin) / (img_height - 2 * margin)
            
            if wall_aspect_ratio > image_aspect_ratio:
                scale = (img_width - 2 * margin) / wall_width_inches
            else:
                scale = (img_height - 2 * margin) / wall_height_inches
            
            scale *= 0.8  # Same factor as in draw_wall method
            
            scaled_width = wall_width_inches * scale
            scaled_height = wall_height_inches * scale
            
            x_offset = (img_width - scaled_width) / 2
            y_offset = (img_height - scaled_height) / 2
            
            # Calculate baseboard height for visualization
            baseboard_height = baseboard_height_inches * scale if self.use_baseboard else 0
            
            # Calculate font sizes scaled to high resolution
            title_font_size = int(18 * scale_factor / 3)
            normal_font_size = int(12 * scale_factor / 3)
            small_font_size = int(8 * scale_factor / 3)
            
            # Try to load fonts - use default if not available
            try:
                title_font = ImageFont.truetype("Arial.ttf", title_font_size)
                normal_font = ImageFont.truetype("Arial.ttf", normal_font_size)
                small_font = ImageFont.truetype("Arial.ttf", small_font_size)
            except IOError:
                # Fallback to default font
                title_font = ImageFont.load_default()
                normal_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            # Draw wall outline with thick lines (scaled by resolution)
            line_width = max(2 * scale_factor // 2, 1)
            draw.rectangle(
                (x_offset, y_offset, x_offset + scaled_width, y_offset + scaled_height),
                outline='black',
                width=line_width
            )
            
            # Get panels
            panels = self.calculate_panels()
            
            # Sort panels by x position
            sorted_panels = sorted(panels, key=lambda p: p.x)
            
            # Fix overlapping panels
            fixed_panels = []
            current_x_percent = 0
            
            for panel in sorted_panels:
                fixed_panel = Panel(
                    id=panel.id,
                    x=current_x_percent,
                    width=panel.width,
                    actual_width=panel.actual_width,
                    actual_width_fraction=panel.actual_width_fraction,
                    height=panel.height,
                    height_fraction=panel.height_fraction,
                    color=panel.color,
                    border_color=panel.border_color
                )
                fixed_panels.append(fixed_panel)
                current_x_percent += panel.width
            
            # Draw baseboard if enabled
            if self.use_baseboard:
                draw.rectangle(
                    (
                        x_offset,
                        y_offset + scaled_height - baseboard_height,
                        x_offset + scaled_width,
                        y_offset + scaled_height
                    ),
                    fill='gray'
                )
            
            # Draw panels
            for panel in fixed_panels:
                panel_x = x_offset + (panel.x / 100 * scaled_width)
                panel_width = (panel.width / 100 * scaled_width)
                
                # Calculate panel height
                panel_height_inches = self.convert_to_inches(
                    panel.height.feet, 
                    panel.height.inches, 
                    panel.height_fraction
                )
                visual_panel_height = min(panel_height_inches, visual_usable_height) * scale
                
                # Calculate panel y position
                if self.use_baseboard:
                    panel_bottom = y_offset + scaled_height - baseboard_height
                else:
                    panel_bottom = y_offset + scaled_height
                    
                panel_top = panel_bottom - visual_panel_height
                
                # Convert color hex to RGB
                try:
                    # Parse panel color which is in hex format (#RRGGBB)
                    panel_fill = panel.color
                    r = int(panel_fill[1:3], 16)
                    g = int(panel_fill[3:5], 16)
                    b = int(panel_fill[5:7], 16)
                    panel_fill_rgb = (r, g, b)
                    
                    # Parse border color
                    border_color = panel.border_color
                    r = int(border_color[1:3], 16)
                    g = int(border_color[3:5], 16)
                    b = int(border_color[5:7], 16)
                    border_rgb = (r, g, b)
                except:
                    # Fallback to blue for fill, red for border
                    panel_fill_rgb = (100, 150, 240)  # Light blue
                    border_rgb = (255, 0, 0)  # Red
                
                # Draw panel rectangle
                draw.rectangle(
                    (panel_x, panel_top, panel_x + panel_width, panel_bottom),
                    fill=panel_fill_rgb,
                    outline=border_rgb,
                    width=max(1, line_width // 2)
                )
                
                # Draw panel vertical dividing lines if not leftmost edge
                if panel.x > 0:
                    draw.line(
                        (panel_x, y_offset, panel_x, y_offset + scaled_height),
                        fill=border_rgb,
                        width=max(1, line_width // 2)
                    )
                
                # Draw panel label
                custom_name = self.custom_name_var.get() or "Panel"
                text_x = panel_x + panel_width / 2
                text_y = panel_top + visual_panel_height / 2
                draw.text(
                    (text_x, text_y),
                    f"{custom_name}",
                    fill='black',
                    font=small_font,
                    anchor="mm"  # Center alignment
                )
            
            # Draw dimensions if enabled
            if self.show_dimensions_var.get():
                # Draw wall width dimension at top
                self.draw_direct_dimension(
                    draw,
                    x_offset, y_offset - 40 * scale_factor / 3,
                    x_offset + scaled_width, y_offset - 40 * scale_factor / 3,
                    self.wall_dimensions["width"],
                    self.wall_dimensions.get("width_fraction", "0"),
                    normal_font,
                    scale_factor
                )
                
                # Draw wall height dimension
                self.draw_direct_dimension(
                    draw,
                    x_offset - 40 * scale_factor / 3, y_offset,
                    x_offset - 40 * scale_factor / 3, y_offset + scaled_height,
                    self.wall_dimensions["height"],
                    self.wall_dimensions.get("height_fraction", "0"),
                    normal_font,
                    scale_factor,
                    is_vertical=True
                )
                
                # Draw panel width dimensions
                for panel in fixed_panels:
                    panel_x = x_offset + (panel.x / 100 * scaled_width)
                    panel_width = (panel.width / 100 * scaled_width)
                    
                    self.draw_direct_dimension(
                        draw,
                        panel_x, y_offset - 20 * scale_factor / 3,
                        panel_x + panel_width, y_offset - 20 * scale_factor / 3,
                        panel.actual_width,
                        panel.actual_width_fraction,
                        small_font,
                        scale_factor
                    )
                
                # Draw baseboard dimension if enabled
                if self.use_baseboard:
                    baseboard_dim, baseboard_frac = self.convert_to_feet_inches_fraction(baseboard_height_inches)
                    self.draw_direct_dimension(
                        draw,
                        x_offset + scaled_width + 20 * scale_factor / 3, 
                        y_offset + scaled_height - baseboard_height,
                        x_offset + scaled_width + 20 * scale_factor / 3,
                        y_offset + scaled_height,
                        baseboard_dim,
                        baseboard_frac,
                        small_font,
                        scale_factor,
                        is_vertical=True
                    )
            
            # Draw wall objects if any
            if hasattr(self, 'wall_objects') and self.wall_objects:
                for obj in self.wall_objects:
                    # Calculate object dimensions in inches
                    width_inches = self.convert_to_inches(
                        obj.width.feet,
                        obj.width.inches,
                        obj.width_fraction
                    )
                    
                    height_inches = self.convert_to_inches(
                        obj.height.feet,
                        obj.height.inches,
                        obj.height_fraction
                    )
                    
                    # Calculate position and size
                    obj_width = width_inches * scale
                    obj_height = height_inches * scale
                    
                    # Calculate horizontal position
                    obj_x = x_offset + (obj.x_position * scaled_width / 100) - (obj_width / 2)
                    
                    # Calculate vertical position accounting for baseboard
                    if self.use_baseboard:
                        wall_top = y_offset
                        wall_bottom = y_offset + scaled_height - baseboard_height
                    else:
                        wall_top = y_offset
                        wall_bottom = y_offset + scaled_height
                    
                    usable_height = wall_bottom - wall_top
                    
                    # Position from top
                    obj_y = wall_top + ((obj.y_position / 100) * usable_height) - (obj_height / 2)
                    
                    # Parse object color
                    try:
                        obj_color = obj.color
                        r = int(obj_color[1:3], 16)
                        g = int(obj_color[3:5], 16)
                        b = int(obj_color[5:7], 16)
                        obj_color_rgb = (r, g, b)
                        
                        border_color = obj.border_color
                        r = int(border_color[1:3], 16)
                        g = int(border_color[3:5], 16)
                        b = int(border_color[5:7], 16)
                        border_rgb = (r, g, b)
                    except:
                        obj_color_rgb = (170, 170, 170)  # Gray
                        border_rgb = (0, 0, 0)  # Black
                    
                    # Draw object rectangle
                    if obj.show_border:
                        draw.rectangle(
                            (obj_x, obj_y, obj_x + obj_width, obj_y + obj_height),
                            fill=obj_color_rgb,
                            outline=border_rgb,
                            width=obj.border_width * scale_factor // 4
                        )
                    else:
                        draw.rectangle(
                            (obj_x, obj_y, obj_x + obj_width, obj_y + obj_height),
                            fill=obj_color_rgb
                        )
                    
                    # Draw object label
                    draw.text(
                        (obj_x + obj_width / 2, obj_y + obj_height / 2),
                        obj.name,
                        fill='black',
                        font=normal_font,
                        anchor="mm"  # Center alignment
                    )
            
            # Save the high-resolution image
            if save_path.lower().endswith('.tiff'):
                # For TIFF format with LZW compression
                image.save(save_path, 'TIFF', compression='tiff_lzw', dpi=(600, 600))
            else:
                # Default to PNG
                image.save(save_path, 'PNG', dpi=(600, 600))
            
            messagebox.showinfo("Success", "Ultra high-resolution image saved successfully!")
        
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during export: {str(e)}")
            import traceback
            traceback.print_exc()

    def draw_direct_dimension(self, draw, x1, y1, x2, y2, dimension, fraction, font, scale_factor, is_vertical=False):
        """Draw dimension line directly on PIL ImageDraw canvas"""
        # Draw main dimension line
        line_width = max(1, scale_factor // 8)
        arrow_size = max(5, scale_factor // 6)
        
        # Draw main dimension line
        draw.line((x1, y1, x2, y2), fill='black', width=line_width)
        
        # Draw arrow at start
        if is_vertical:
            draw.line((x1 - arrow_size, y1 + arrow_size, x1, y1, x1 + arrow_size, y1 + arrow_size), 
                     fill='black', width=line_width)
        else:
            draw.line((x1 - arrow_size, y1 - arrow_size, x1, y1, x1 - arrow_size, y1 + arrow_size), 
                     fill='black', width=line_width)
        
        # Draw arrow at end
        if is_vertical:
            draw.line((x2 - arrow_size, y2 - arrow_size, x2, y2, x2 + arrow_size, y2 - arrow_size), 
                     fill='black', width=line_width)
        else:
            draw.line((x2 + arrow_size, y2 - arrow_size, x2, y2, x2 + arrow_size, y2 + arrow_size), 
                     fill='black', width=line_width)
        
        # Format dimension text
        text = self.format_dimension(dimension, fraction)
        
        # Position text
        text_x = (x1 + x2) / 2
        text_y = (y1 + y2) / 2
        
        if is_vertical:
            # For vertical text, we need to adjust position
            draw.text((text_x - 20, text_y), text, fill='black', font=font)
        else:
            # Draw centered above the line for horizontal dimensions
            draw.text((text_x, y1 - 15), text, fill='black', font=font, anchor="mm")

    def export_high_quality_image(self):
        """Export the wall drawing as a high resolution image with proper color rendering"""
        try:
            from PIL import Image
            import numpy as np
            import pyscreenshot as ImageGrab
        except ImportError:
            messagebox.showerror("Error", "Required libraries missing. Please install with:\npip install pillow numpy pyscreenshot")
            return

        # Get save location
        file_name = f"{self.project_name_var.get().replace(' ', '-')}-{self.date_var.get()}.tiff"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".tiff",
            initialfile=file_name,
            filetypes=[("TIFF files", "*.tiff"), ("PNG files", "*.png"), ("JPEG files", "*.jpg")]
        )

        if not save_path:
            return

        try:
            # Make sure canvas is fully updated and give time for rendering
            self.update()
            self.after(100)  # Small delay to ensure canvas is fully rendered
            
            # Get the canvas coordinates on screen
            canvas_x = self.canvas.winfo_rootx()
            canvas_y = self.canvas.winfo_rooty()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Take a screenshot of just the canvas area at maximum quality
            img = ImageGrab.grab(bbox=(canvas_x, canvas_y, 
                                      canvas_x + canvas_width, 
                                      canvas_y + canvas_height))
            
            # Calculate scaling factor for high resolution (4x)
            scale_factor = 4
            target_width = canvas_width * scale_factor
            target_height = canvas_height * scale_factor
            
            # Resize with high-quality algorithm
            img = img.resize((target_width, target_height), Image.LANCZOS)
            
            # Set DPI for print quality
            dpi = (600, 600)
            
            # Save with appropriate format and maximum quality settings
            if save_path.lower().endswith('.jpg') or save_path.lower().endswith('.jpeg'):
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(save_path, 'JPEG', quality=100, dpi=dpi)
                
            elif save_path.lower().endswith('.tiff'):
                # Use best TIFF compression for quality
                img.save(save_path, 'TIFF', compression='tiff_lzw', dpi=dpi)
                
            else:  # Default to PNG
                img.save(save_path, 'PNG', dpi=dpi)
            
            messagebox.showinfo("Success", f"High-resolution image saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during image export: {str(e)}")
            import traceback
            traceback.print_exc()  # Print stack trace for debugging

    def export_eps(self):
        """Export the wall drawing as an Encapsulated PostScript (EPS) file with proper color support"""
        # Get save location
        file_name = f"{self.project_name_var.get().replace(' ', '-')}-{self.date_var.get()}.eps"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".eps",
            initialfile=file_name,
            filetypes=[("EPS files", "*.eps")]
        )

        if not save_path:
            return

        try:
            # Force a redraw to ensure all elements are rendered correctly
            self.update()
            
            # Create a PostScript file directly from the canvas
            # Use extended options for better color handling
            ps_data = self.canvas.postscript(
                colormode='color',  # Use color mode
                pagewidth=self.canvas.winfo_width(),
                pageheight=self.canvas.winfo_height(),
                x=0, y=0,
                width=self.canvas.winfo_width(),
                height=self.canvas.winfo_height()
            )
            
            # Write the EPS file
            with open(save_path, 'w') as f:
                f.write(ps_data)
            
            messagebox.showinfo("Success", "EPS file exported successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during EPS export: {str(e)}")
            import traceback
            traceback.print_exc()  # Print stack trace for debugging

    def export_enhanced_svg(self):
        """Export an enhanced SVG with better compatibility and quality"""
        try:
            import os
            import tempfile
            
            # Get save location
            file_name = f"{self.project_name_var.get().replace(' ', '-')}-{self.date_var.get()}.svg"
            save_path = filedialog.asksaveasfilename(
                defaultextension=".svg",
                initialfile=file_name,
                filetypes=[("SVG files", "*.svg")]
            )
            
            if not save_path:
                return
                
            # Create a temporary directory for intermediate files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Use the existing SVG export method but redirect to a temp file
                temp_svg_path = os.path.join(temp_dir, "temp.svg")
                
                # Store original asksaveasfilename function
                original_ask = filedialog.asksaveasfilename
                
                # Override with our temp path
                filedialog.asksaveasfilename = lambda **kwargs: temp_svg_path
                
                # Call the existing SVG export method
                self.export_svg_enhanced()
                
                # Restore original function
                filedialog.asksaveasfilename = original_ask
                
                # Now we have the SVG in temp_svg_path
                # Optionally post-process it for better quality
                
                # Read the SVG content
                with open(temp_svg_path, 'r') as f:
                    svg_content = f.read()
                    
                # You could enhance the SVG content here if needed
                # For example, add better metadata, optimize paths, etc.
                
                # Write the final SVG
                with open(save_path, 'w') as f:
                    f.write(svg_content)
                    
                messagebox.showinfo("Success", "Enhanced SVG exported successfully!")
                

        
        except Exception as e:
            messagebox.showerror("Error", f"SVG export failed: {str(e)}")
            import traceback
            traceback.print_exc()

    def export_enhanced_pdf(self):
        """Export an enhanced PDF with better compatibility and quality"""
        try:
            import os
            import tempfile
            
            # Get save location
            file_name = f"{self.project_name_var.get().replace(' ', '-')}-{self.date_var.get()}.pdf"
            save_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                initialfile=file_name,
                filetypes=[("PDF files", "*.pdf")]
            )
            
            if not save_path:
                return
                
            # Create a temporary directory for intermediate files
            with tempfile.TemporaryDirectory() as temp_dir:
                # First generate a high-quality SVG
                temp_svg_path = os.path.join(temp_dir, "temp.svg")
                
                # Store original function
                original_ask = filedialog.asksaveasfilename
                
                # Override with our temp path
                filedialog.asksaveasfilename = lambda **kwargs: temp_svg_path
                
                # Call SVG export
                self.export_svg_enhanced()
                
                # Restore original function
                filedialog.asksaveasfilename = original_ask
                
                # Create an instance of PDFExporter
                pdf_exporter = PDFExporter(self.canvas, self.summary_text)
                
                # Convert SVG to PDF using the PDF exporter
                pdf_exporter.svg_to_pdf(
                    temp_svg_path, 
                    save_path, 
                    dpi=600  # High resolution
                )
                
                messagebox.showinfo("Success", "Enhanced PDF exported successfully!")
                

        
        except Exception as e:
            messagebox.showerror("Error", f"PDF export failed: {str(e)}")
            import traceback
            traceback.print_exc()

    def export_enhanced_eps(self):
        """Export an enhanced EPS file with better compatibility and quality"""
        try:
            import os
            
            # Get save location
            file_name = f"{self.project_name_var.get().replace(' ', '-')}-{self.date_var.get()}.eps"
            save_path = filedialog.asksaveasfilename(
                defaultextension=".eps",
                initialfile=file_name,
                filetypes=[("EPS files", "*.eps")]
            )
            
            if not save_path:
                return
                
            # Use the canvas's postscript method for best vector quality
            ps_data = self.canvas.postscript(
                colormode='color',
                pagewidth=self.canvas.winfo_width(),
                pageheight=self.canvas.winfo_height(),
                x=0, y=0,
                width=self.canvas.winfo_width(),
                height=self.canvas.winfo_height()
            )
            
            # Write the postscript data to file
            with open(save_path, 'w') as f:
                f.write(ps_data)
                
            messagebox.showinfo("Success", "Enhanced EPS exported successfully!")
            

        
        except Exception as e:
            messagebox.showerror("Error", f"EPS export failed: {str(e)}")
            import traceback
            traceback.print_exc()

    def export_high_res_via_svg(self, format_type, scale_factor=6):
        """
        Export high-resolution raster image via SVG first approach
        
        Args:
            format_type: Format type string ('png', 'tiff', 'jpg')
            scale_factor: Resolution multiplier (default: 6)
        """
        try:
            import os
            import tempfile
            
            # Make sure format type is lowercase
            format_type = format_type.lower()
            
            # Map format type to extension and proper PIL format identifier
            format_map = {
                'png': ('png', 'PNG'),
                'tiff': ('tiff', 'TIFF'),
                'jpg': ('jpg', 'JPEG'),
                'jpeg': ('jpg', 'JPEG')
            }
            
            if format_type not in format_map:
                messagebox.showerror("Error", f"Unsupported format: {format_type}")
                return
                
            extension, pil_format = format_map[format_type]
            
            # Get save location
            file_name = f"{self.project_name_var.get().replace(' ', '-')}-{self.date_var.get()}.{extension}"
            save_path = filedialog.asksaveasfilename(
                defaultextension=f".{extension}",
                initialfile=file_name,
                filetypes=[(f"{format_type.upper()} files", f"*.{extension}")]
            )
            
            if not save_path:
                return
                
            try:
                from PIL import Image
                import cairosvg
            except ImportError:
                messagebox.showerror("Error", "Required libraries missing. Please install with:\npip install pillow cairosvg")
                return
                
            # Create a temporary directory for intermediate files
            with tempfile.TemporaryDirectory() as temp_dir:
                # First generate a high-quality SVG
                temp_svg_path = os.path.join(temp_dir, "temp.svg")
                
                # Store original function
                original_ask = filedialog.asksaveasfilename
                
                # Override with our temp path
                filedialog.asksaveasfilename = lambda **kwargs: temp_svg_path
                
                # Call SVG export
                self.export_svg_enhanced()
                
                # Restore original function
                filedialog.asksaveasfilename = original_ask
                
                # Calculate target dimensions
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                target_width = canvas_width * scale_factor
                target_height = canvas_height * scale_factor
                
                # Calculate DPI for print-quality output
                # Standard DPI is 72, so we multiply by the scale factor
                dpi = 72 * scale_factor
                
                # Create a temporary PNG file
                temp_png_path = os.path.join(temp_dir, "temp.png")
                
                # Use CairoSVG to render the SVG to a high-resolution PNG
                cairosvg.svg2png(
                    url=temp_svg_path,
                    write_to=temp_png_path,
                    output_width=target_width,
                    output_height=target_height,
                    dpi=dpi
                )
                
                # Open the temporary PNG
                img = Image.open(temp_png_path)
                
                # Format-specific settings for saving
                if pil_format == 'TIFF':
                    # Use LZW compression for TIFF (lossless)
                    img.save(save_path, pil_format, compression='tiff_lzw', dpi=(dpi, dpi))
                elif pil_format == 'JPEG':
                    # Convert to RGB for JPEG and use maximum quality
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(save_path, pil_format, quality=95, dpi=(dpi, dpi))
                else:  # PNG
                    # Use maximum compression for PNG
                    img.save(save_path, pil_format, dpi=(dpi, dpi), compress_level=9)
                    
                messagebox.showinfo("Success", f"High-resolution {format_type.upper()} exported at {dpi} DPI!")
                

        
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Try alternative export method if SVG conversion fails
            try:
                messagebox.showinfo("Notice", "Trying alternative export method...")
                if format_type == 'png':
                    self.export_direct_vector(save_path)
                else:
                    self.export_direct_vector()
            except:
                pass


    def export_pdf(self):
        # Validate inputs
        if not self.project_name_var.get().strip():
            messagebox.showerror("Error", "Please enter a project name")
            return

        if not self.location_var.get().strip():
            messagebox.showerror("Error", "Please enter a location")
            return

        # Get save location
        file_name = f"{self.project_name_var.get().replace(' ', '-')}-{self.date_var.get()}.pdf"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=file_name,
            filetypes=[("PDF files", "*.pdf")]
        )

        if not save_path:
            return

        # Generate SVG path
        svg_path = save_path.replace(".pdf", ".svg")

        # Create an instance of PDFExporter
        pdf_exporter = PDFExporter(self.canvas, self.summary_text)

        try:
            # Export canvas to SVG
            pdf_exporter.canvas_to_svg(
                self.canvas,
                svg_path,
                project_name=self.project_name_var.get(),
                location=self.location_var.get(),
                date=self.date_var.get()
            )

            # Convert SVG to PDF
            pdf_exporter.svg_to_pdf(svg_path, save_path)

            # Optional: Remove the temporary SVG file
            os.remove(svg_path)

            messagebox.showinfo("Success", "PDF saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while saving the PDF: {str(e)}")
            


    def export_svg_enhanced(self):
        """Export the wall drawing as a clean SVG file optimized for Inkscape editing"""
        # Get save location
        file_name = f"{self.project_name_var.get().replace(' ', '-')}-{self.date_var.get()}.svg"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".svg",
            initialfile=file_name,
            filetypes=[("SVG files", "*.svg")]
        )

        if not save_path:
            return

        try:
            # Calculate wall dimensions
            wall_width_inches = self.convert_to_inches(
                self.wall_dimensions["width"].feet,
                self.wall_dimensions["width"].inches,
                self.wall_dimensions.get("width_fraction", "0")
            )
            
            wall_height_inches = self.convert_to_inches(
                self.wall_dimensions["height"].feet,
                self.wall_dimensions["height"].inches,
                self.wall_dimensions.get("height_fraction", "0")
            )
            
            # Set up scaling and margins
            scale = 10  # Each inch = 10 units in SVG
            margin = 100
            svg_width = int(wall_width_inches * scale) + (2 * margin)
            svg_height = int(wall_height_inches * scale) + (2 * margin)
            
            # Start SVG content with proper Inkscape namespaces
            svg_content = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
    <svg
       width="{svg_width}"
       height="{svg_height}"
       viewBox="0 0 {svg_width} {svg_height}"
       version="1.1"
       id="wallpanels"
       xmlns="http://www.w3.org/2000/svg"
       xmlns:svg="http://www.w3.org/2000/svg"
       xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
       xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd">

      <!-- Project metadata -->
      <title>Wall Panel Shop Drawing</title>
      <desc>Project: {self.project_name_var.get()}, Date: {self.date_var.get()}</desc>
      
      <!-- Create layers for easier editing in Inkscape -->
      <g inkscape:groupmode="layer" id="layer_wall" inkscape:label="Wall">
    '''
            
            # Calculate wall position with margins
            wall_left = margin
            wall_top = margin
            wall_width = wall_width_inches * scale
            wall_height = wall_height_inches * scale
            
            # Draw wall outline
            svg_content += f'''    <rect
           id="wall_outline"
           x="{wall_left}"
           y="{wall_top}"
           width="{wall_width}"
           height="{wall_height}"
           fill="none"
           stroke="black"
           stroke-width="2" />
    '''
            
            # Add baseboard if enabled
            if self.use_baseboard:
                baseboard_height_inches = self.baseboard_height
                if hasattr(self, 'baseboard_fraction_var'):
                    baseboard_height_inches += self.fraction_to_decimal(self.baseboard_fraction_var.get())
                
                baseboard_height = baseboard_height_inches * scale
                
                svg_content += f'''    <rect
           id="baseboard"
           x="{wall_left}"
           y="{wall_top + wall_height - baseboard_height}"
           width="{wall_width}"
           height="{baseboard_height}"
           fill="#808080"
           stroke="none" />
    '''

            svg_content += '''  </g>
      <g inkscape:groupmode="layer" id="layer_panels" inkscape:label="Panels">
    '''
            
            # Get panels and draw them
            panels = self.calculate_panels()
            
            for i, panel in enumerate(panels):
                # Calculate panel position and dimensions
                panel_x = wall_left + (panel.x / 100 * wall_width)
                panel_width = (panel.width / 100 * wall_width)
                
                # Calculate panel height
                panel_height_inches = self.convert_to_inches(
                    panel.height.feet, 
                    panel.height.inches, 
                    panel.height_fraction
                )
                panel_height = panel_height_inches * scale
                
                # Calculate baseboard height if used
                baseboard_height = 0
                if self.use_baseboard:
                    baseboard_height_inches = self.baseboard_height
                    if hasattr(self, 'baseboard_fraction_var'):
                        baseboard_height_inches += self.fraction_to_decimal(self.baseboard_fraction_var.get())
                    baseboard_height = baseboard_height_inches * scale
                
                # Calculate panel top position
                panel_top = wall_top
                panel_bottom = wall_top + wall_height - baseboard_height
                
                # Draw panel dividing lines if not the leftmost edge
                if panel.x > 0:
                    svg_content += f'''    <path
           id="panel_divider_{i}"
           d="M {panel_x} {wall_top} L {panel_x} {wall_top + wall_height}"
           stroke="{panel.border_color}"
           stroke-width="1"
           stroke-dasharray="5,5" />
    '''
                
                # Add panel label
                panel_label_x = panel_x + (panel_width / 2)
                panel_label_y = panel_top + (panel_height / 2)
                custom_name = self.custom_name_var.get() or "Panel"
                
                svg_content += f'''    <text
           id="panel_label_{i}"
           x="{panel_label_x}"
           y="{panel_label_y}"
           text-anchor="middle"
           dominant-baseline="middle"
           font-family="Arial"
           font-size="12">{custom_name} {i+1}</text>
    '''
            
            svg_content += '''  </g>
      <g inkscape:groupmode="layer" id="layer_dimensions" inkscape:label="Dimensions">
    '''
            
            # Add dimensions if requested
            if self.show_dimensions_var.get():
                # Overall wall width dimension
                dim_y = wall_top - 40
                svg_content += self.create_svg_dimension(
                    wall_left, dim_y, 
                    wall_left + wall_width, dim_y,
                    self.wall_dimensions["width"],
                    self.wall_dimensions.get("width_fraction", "0"),
                    "wall_width_dim"
                )
                
                # Wall height dimension
                dim_x = wall_left - 40
                svg_content += self.create_svg_dimension(
                    dim_x, wall_top,
                    dim_x, wall_top + wall_height,
                    self.wall_dimensions["height"],
                    self.wall_dimensions.get("height_fraction", "0"),
                    "wall_height_dim",
                    is_vertical=True
                )
                
                # Panel width dimensions
                for i, panel in enumerate(panels):
                    panel_x = wall_left + (panel.x / 100 * wall_width)
                    panel_width = (panel.width / 100 * wall_width)
                    
                    dim_y = wall_top - 20
                    svg_content += self.create_svg_dimension(
                        panel_x, dim_y,
                        panel_x + panel_width, dim_y,
                        panel.actual_width,
                        panel.actual_width_fraction,
                        f"panel_{i+1}_width_dim"
                    )
                
                # Baseboard dimension if enabled
                if self.use_baseboard:
                    baseboard_height_inches = self.baseboard_height
                    if hasattr(self, 'baseboard_fraction_var'):
                        baseboard_height_inches += self.fraction_to_decimal(self.baseboard_fraction_var.get())
                    
                    baseboard_dim, baseboard_frac = self.convert_to_feet_inches_fraction(baseboard_height_inches)
                    
                    dim_x = wall_left + wall_width + 30
                    baseboard_y = wall_top + wall_height - (baseboard_height_inches * scale)
                    
                    svg_content += self.create_svg_dimension(
                        dim_x, baseboard_y,
                        dim_x, wall_top + wall_height,
                        baseboard_dim,
                        baseboard_frac,
                        "baseboard_height_dim",
                        is_vertical=True
                    )
            
            # Add wall objects if any
            if hasattr(self, 'wall_objects') and self.wall_objects:
                svg_content += '''  </g>
      <g inkscape:groupmode="layer" id="layer_objects" inkscape:label="Wall Objects">
    '''
                
                for i, obj in enumerate(self.wall_objects):
                    # Calculate object dimensions in inches
                    width_inches = self.convert_to_inches(
                        obj.width.feet,
                        obj.width.inches,
                        obj.width_fraction
                    )
                    
                    height_inches = self.convert_to_inches(
                        obj.height.feet,
                        obj.height.inches,
                        obj.height_fraction
                    )
                    
                    # Calculate position and size on SVG
                    obj_width = width_inches * scale
                    obj_height = height_inches * scale
                    
                    # Calculate horizontal position based on percentage
                    obj_x = wall_left + (obj.x_position * wall_width / 100) - (obj_width / 2)
                    
                    # Calculate vertical position (Y) accounting for baseboard
                    usable_height = wall_height
                    if self.use_baseboard:
                        baseboard_height_inches = self.baseboard_height
                        if hasattr(self, 'baseboard_fraction_var'):
                            baseboard_height_inches += self.fraction_to_decimal(self.baseboard_fraction_var.get())
                        usable_height -= baseboard_height_inches * scale
                    
                    # Calculate position from top
                    obj_y = wall_top + ((obj.y_position / 100) * usable_height) - (obj_height / 2)
                    
                    # Draw object rectangle
                    border_attr = f'stroke="{obj.border_color}" stroke-width="{obj.border_width}"' if obj.show_border else 'stroke="none"'
                    
                    svg_content += f'''    <rect
           id="object_{i}"
           x="{obj_x}"
           y="{obj_y}"
           width="{obj_width}"
           height="{obj_height}"
           fill="{obj.color}"
           {border_attr} />
           
        <text
           id="object_label_{i}"
           x="{obj_x + obj_width/2}"
           y="{obj_y + obj_height/2}"
           text-anchor="middle"
           dominant-baseline="middle"
           font-family="Arial"
           font-size="12">{obj.name}</text>
    '''
                    
                    # Add dimensions if requested
                    if self.show_dimensions_var.get():
                        svg_content += self.create_svg_dimension(
                            obj_x, obj_y - 15,
                            obj_x + obj_width, obj_y - 15,
                            obj.width,
                            obj.width_fraction,
                            f"object_{i}_width_dim"
                        )
                        
                        svg_content += self.create_svg_dimension(
                            obj_x - 15, obj_y,
                            obj_x - 15, obj_y + obj_height,
                            obj.height,
                            obj.height_fraction,
                            f"object_{i}_height_dim",
                            is_vertical=True
                        )
            
            # Close SVG tag
            svg_content += '''  </g>
    </svg>'''
            
            # Write SVG content to file
            with open(save_path, 'w') as f:
                f.write(svg_content)
            
            messagebox.showinfo("Success", "SVG saved successfully for Inkscape editing!")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while saving the SVG: {str(e)}")
            import traceback
            traceback.print_exc()  # Print stack trace for debugging

    def create_svg_dimension(self, x1, y1, x2, y2, dimension, fraction, id_prefix, is_vertical=False, offset=10):
        """Create an SVG dimension line with arrows and text"""
        dim_text = self.format_dimension(dimension, fraction)
        
        # Calculate midpoint for text placement
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        
        # Different attributes for horizontal vs vertical dimensions
        if is_vertical:
            text_transform = f'transform="rotate(-90,{mid_x-offset},{mid_y})"'
        else:
            text_transform = ""
        
        # Create arrow markers 
        # (Note: We define these once in the SVG, but including here for completeness)
        svg_content = f'''    <g id="{id_prefix}_group">
          <line
             id="{id_prefix}_line"
             x1="{x1}"
             y1="{y1}"
             x2="{x2}"
             y2="{y2}"
             stroke="black"
             stroke-width="1"
             marker-start="url(#arrow_start)"
             marker-end="url(#arrow_end)" />
             
          <text
             id="{id_prefix}_text"
             x="{mid_x}"
             y="{is_vertical and mid_y or y1 - offset}"
             text-anchor="middle"
             font-family="Arial"
             font-size="12"
             {text_transform}>{dim_text}</text>
        </g>
    '''
        
        return svg_content

    def export_clean_pdf(self):
        """Export a clean PDF without grid lines for printing"""
        # Get save location
        file_name = f"{self.project_name_var.get().replace(' ', '-')}-{self.date_var.get()}.pdf"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=file_name,
            filetypes=[("PDF files", "*.pdf")]
        )

        if not save_path:
            return

        try:
            # First export to SVG as an intermediate format
            svg_path = save_path.replace(".pdf", ".svg")
            
            # Use enhanced SVG export function
            # Save to the temporary SVG path
            old_save_path = filedialog.asksaveasfilename
            filedialog.asksaveasfilename = lambda **kwargs: svg_path
            self.export_svg_enhanced()
            filedialog.asksaveasfilename = old_save_path
            
            # Convert SVG to PDF using cairosvg
            pdf_exporter = PDFExporter(self.canvas, self.summary_text)
            pdf_exporter.svg_to_pdf(svg_path, save_path, dpi=300)
            
            # Remove temporary SVG file
            os.remove(svg_path)
            
            messagebox.showinfo("Success", "PDF exported successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during PDF export: {str(e)}")
            import traceback
            traceback.print_exc()  # Print stack trace for debugging

    def create_dimension_inputs(self, parent, label, prefix):
        frame = ctk.CTkFrame(parent)
        frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(frame, text=f"{label}:").pack(side=tk.LEFT)
        
        # Feet input
        feet_var = tk.StringVar(value="0")
        setattr(self, f"{prefix}_feet_var", feet_var)
        feet_entry = ctk.CTkEntry(frame, textvariable=feet_var, width=50)
        feet_entry.pack(side=tk.LEFT, padx=5)
        
        ctk.CTkLabel(frame, text="feet").pack(side=tk.LEFT)
        
        # Inches input
        inches_var = tk.StringVar(value="0")
        setattr(self, f"{prefix}_inches_var", inches_var)
        inches_entry = ctk.CTkEntry(frame, textvariable=inches_var, width=50)
        inches_entry.pack(side=tk.LEFT, padx=5)
        
        ctk.CTkLabel(frame, text="inches").pack(side=tk.LEFT)
        
        # Fraction dropdown
        ctk.CTkLabel(frame, text="+").pack(side=tk.LEFT, padx=2)
        
        fraction_options = ["0", "1/16", "1/8", "3/16", "1/4", "5/16", "3/8", "7/16", 
                            "1/2", "9/16", "5/8", "11/16", "3/4", "13/16", "7/8", "15/16"]
        
        fraction_var = tk.StringVar(value="0")
        setattr(self, f"{prefix}_fraction_var", fraction_var)
        
        fraction_dropdown = ctk.CTkOptionMenu(
            frame,
            variable=fraction_var,
            values=fraction_options,
            width=70
        )
        fraction_dropdown.pack(side=tk.LEFT, padx=5)


    def fraction_to_decimal(self, fraction_str):
        """Convert a fraction string to its decimal value"""
        if fraction_str == "0":
            return 0.0
            
        try:
            if "/" in fraction_str:
                num, denom = fraction_str.split("/")
                return float(num) / float(denom)
            return float(fraction_str)
        except (ValueError, ZeroDivisionError):
            return 0.0

    def convert_to_inches(self, feet: int, inches: int, fraction_str: str) -> float:
        """Convert feet, inches, and fraction to total inches"""
        fraction_decimal = self.fraction_to_decimal(fraction_str)
        return feet * 12 + inches + fraction_decimal

    def convert_to_feet_inches_fraction(self, total_inches: float) -> tuple:
        """Convert total inches to feet, inches, and closest fraction with high precision"""
        # Add a small epsilon to handle floating point errors
        epsilon = 0.001
        total_inches += epsilon
        
        feet = int(total_inches // 12)
        remaining_inches = total_inches % 12
        
        whole_inches = int(remaining_inches)
        fraction_decimal = remaining_inches - whole_inches
        
        # Find closest fraction with higher precision
        fractions = {
            0: "0", 0.0625: "1/16", 0.125: "1/8", 0.1875: "3/16", 
            0.25: "1/4", 0.3125: "5/16", 0.375: "3/8", 0.4375: "7/16",
            0.5: "1/2", 0.5625: "9/16", 0.625: "5/8", 0.6875: "11/16", 
            0.75: "3/4", 0.8125: "13/16", 0.875: "7/8", 0.9375: "15/16"
        }
        
        # Find the closest fraction with enhanced precision
        closest_decimal = min(fractions.keys(), key=lambda x: abs(x - fraction_decimal))
        closest_fraction = fractions[closest_decimal]
        
        # Handle rounding more carefully
        if abs(fraction_decimal - closest_decimal) < 0.01 and closest_decimal > 0.94:
            whole_inches += 1
            closest_fraction = "0"
            
        # Handle case where inches becomes 12
        if whole_inches == 12:
            feet += 1
            whole_inches = 0
        
        return Dimension(feet, whole_inches), closest_fraction

    def create_canvas(self):
        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def on_equal_panels_change(self):
        """Handle equal panels checkbox change"""
        self.save_current_wall_data()  # This line should be properly indented
        
        if self.equal_panels_var.get():
            self.panel_count_frame.pack(pady=5)
            self.center_panels_var.set(False)
            if hasattr(self, 'center_panel_inputs'):
                self.center_panel_inputs.pack_forget()
        else:
            self.panel_count_frame.pack_forget()
        self.calculate()

    def on_center_panels_change(self):
        """Handle center panels checkbox change"""
        if self.center_panels_var.get():
            self.center_panel_inputs.pack(pady=5)
            self.equal_panels_var.set(False)
            self.panel_count_frame.pack_forget()
            
            # Don't clear custom panel widths when changing layout
            # if hasattr(self, 'custom_panel_widths'):
            #    self.custom_panel_widths = {}
        else:
            self.center_panel_inputs.pack_forget()
        self.calculate()

    def on_baseboard_change(self):
        """Optimized baseboard change handler"""
        print(f"Baseboard state changed to: {self.baseboard_var.get()}")
        
        # Update instance variable
        self.use_baseboard = self.baseboard_var.get()
        
        # Show/hide baseboard frame based on checkbox state
        if self.baseboard_var.get():
            if hasattr(self, 'baseboard_frame'):
                self.baseboard_frame.pack(pady=5, fill=tk.X)
        else:
            if hasattr(self, 'baseboard_frame'):
                self.baseboard_frame.pack_forget()
        
        # CRITICAL: Save the current wall data immediately
        current_wall = self.get_current_wall()
        if current_wall:
            print(f"  Immediately saving baseboard state to wall: {current_wall.name}")
            current_wall.baseboard_enabled = self.baseboard_var.get()
            
            # Also save all wall data to ensure consistency
            self.save_current_wall_data()
        
        # Use a delayed calculation to prevent multiple rapid calculations
        if hasattr(self, '_baseboard_timer'):
            self.after_cancel(self._baseboard_timer)
        
        self._baseboard_timer = self.after(100, self.calculate)  # 100ms delay

        
    def choose_color(self):
        """Open color picker and update the panel color"""
        color = colorchooser.askcolor(color=self.panel_color, title="Choose Panel Color")
        if color[1]:  # color is ((R, G, B), hex_color)
            self.panel_color = color[1]
            self.color_preview.configure(bg=self.panel_color)
            self.calculate()

    def reset_form(self):
        """Reset all form inputs to default values"""
        # Reset wall dimensions
        self.wall_width_feet_var.set("0")
        self.wall_width_inches_var.set("0")
        self.wall_height_feet_var.set("0")
        self.wall_height_inches_var.set("0")
        
        # Reset fractions
        self.wall_width_fraction_var.set("0")
        self.wall_height_fraction_var.set("0")
        self.panel_width_fraction_var.set("0")
        self.panel_height_fraction_var.set("0")
        if hasattr(self, 'baseboard_fraction_var'):
            self.baseboard_fraction_var.set("0")
            
        # Reset panel dimensions
        self.panel_width_feet_var.set("0")
        self.panel_width_inches_var.set("0")
        self.panel_height_feet_var.set("0")
        self.panel_height_inches_var.set("0")
        self.show_dimensions_var.set(True)  # Reset to showing dimensions
        
        # Reset options
        self.equal_panels_var.set(False)
        self.panel_count_var.set("2")
        self.center_panels_var.set(False)
        self.center_panel_count_var.set("4")
        
        # Reset baseboard options
        self.baseboard_var.set(False)
        self.baseboard_height_var.set("4")
        if hasattr(self, 'baseboard_frame'):
            self.baseboard_frame.pack_forget()
        
        # Reset floor mounting options
        self.floor_mounted_var.set(True)  # Default to floor mounted
        if hasattr(self, 'height_offset_frame'):
            self.height_offset_frame.pack_forget()
        self.height_offset_feet_var.set("0")
        self.height_offset_inches_var.set("0")
        self.height_offset_fraction_var.set("0")
        
        # Reset colors
        self.panel_color = "#FFFFFF"
        self.panel_border_color = "red"
        self.color_preview.configure(bg=self.panel_color)
        self.border_color_preview.configure(bg=self.panel_border_color)
        
        # Reset panel adjustments
        if hasattr(self, 'custom_panel_widths'):
            self.custom_panel_widths = {}
        
        # Reset split panels
        if hasattr(self, 'split_panels'):
            self.split_panels = {}
            
        # Clear canvas
        self.canvas.delete("all")
        
        # Clear summary
        self.summary_text.delete("1.0", tk.END)

    def safe_int_conversion(self, value, default=0):
        """Safely convert string to int, returning default if conversion fails"""
        try:
            return int(value) if value.strip() else default
        except (ValueError, AttributeError):
            return default


    def convert_to_feet_and_inches(self, total_inches: float) -> Dimension:
        feet = int(total_inches // 12)
        inches = round(total_inches % 12)
        if inches == 12:
            feet += 1
            inches = 0
        return Dimension(feet, inches)

    def format_dimension(self, dimension: Dimension, fraction: str = "0") -> str:
        """Format dimensions with dash between feet and inches - UPDATED"""
        if dimension.inches == 0 and fraction == "0":
            return f"{dimension.feet}'"
        elif fraction == "0":
            return f"{dimension.feet}'-{dimension.inches}\""
        else:
            return f"{dimension.feet}'-{dimension.inches} {fraction}\""
    def add_panel_adjustment_system(self):
        """Add UI for adjusting individual panel widths"""
        try:
            panel_adjustment_frame = ctk.CTkFrame(self.input_frame)
            panel_adjustment_frame.pack(pady=10, padx=10, fill=tk.X)
            
            ctk.CTkLabel(panel_adjustment_frame, text="Adjust Individual Panel").pack(pady=5)
            
            # Panel selection
            selection_frame = ctk.CTkFrame(panel_adjustment_frame)
            selection_frame.pack(pady=5, fill=tk.X)
            
            ctk.CTkLabel(selection_frame, text="Panel ID:").pack(side=tk.LEFT, padx=5)
            self.panel_id_var = tk.StringVar(value="1")
            panel_id_entry = ctk.CTkEntry(selection_frame, textvariable=self.panel_id_var, width=50)
            panel_id_entry.pack(side=tk.LEFT, padx=5)
            
            # Width adjustment
            width_frame = ctk.CTkFrame(panel_adjustment_frame)
            width_frame.pack(pady=5, fill=tk.X)
            
            ctk.CTkLabel(width_frame, text="Width:").pack(side=tk.LEFT, padx=5)
            
            self.panel_width_feet_adjust_var = tk.StringVar(value="0")
            feet_entry = ctk.CTkEntry(width_frame, textvariable=self.panel_width_feet_adjust_var, width=40)
            feet_entry.pack(side=tk.LEFT, padx=2)
            ctk.CTkLabel(width_frame, text="feet").pack(side=tk.LEFT)
            
            self.panel_width_inches_adjust_var = tk.StringVar(value="0")
            inches_entry = ctk.CTkEntry(width_frame, textvariable=self.panel_width_inches_adjust_var, width=40)
            inches_entry.pack(side=tk.LEFT, padx=2)
            ctk.CTkLabel(width_frame, text="inches").pack(side=tk.LEFT)
            
            # Initialize fraction_options if it doesn't exist
            if not hasattr(self, 'fraction_options'):
                self.fraction_options = ["0", "1/16", "1/8", "3/16", "1/4", "5/16", "3/8", "7/16", 
                                      "1/2", "9/16", "5/8", "11/16", "3/4", "13/16", "7/8", "15/16"]
            
            ctk.CTkLabel(width_frame, text="+").pack(side=tk.LEFT, padx=2)
            self.panel_width_fraction_adjust_var = tk.StringVar(value="0")
            fraction_dropdown = ctk.CTkOptionMenu(
                width_frame, 
                variable=self.panel_width_fraction_adjust_var,
                values=self.fraction_options,
                width=70
            )
            fraction_dropdown.pack(side=tk.LEFT, padx=2)
            
            # Button to apply adjustment
            button_frame = ctk.CTkFrame(panel_adjustment_frame)
            button_frame.pack(pady=5)
            
            apply_button = ctk.CTkButton(
                button_frame,
                text="Apply Width Adjustment",
                command=self.apply_panel_width_adjustment
            )
            apply_button.pack(side=tk.LEFT, padx=5)
            
            reset_button = ctk.CTkButton(
                button_frame,
                text="Reset All Adjustments",
                command=self.reset_panel_adjustments
            )
            reset_button.pack(side=tk.LEFT, padx=5)
            
            # Initialize dictionary to store custom widths if it doesn't exist
            if not hasattr(self, 'custom_panel_widths'):
                self.custom_panel_widths = {}
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create panel adjustment UI: {str(e)}")
    def add_panel_adjustment_ui(self):
        """Add UI controls for adjusting individual panel widths"""
        adjustment_frame = ctk.CTkFrame(self.input_frame)
        adjustment_frame.pack(pady=10, padx=10, fill=tk.X)
        
        ctk.CTkLabel(adjustment_frame, text="Panel Width Adjustments").pack()
        
        # Panel ID selection
        id_frame = ctk.CTkFrame(adjustment_frame)
        id_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(id_frame, text="Panel ID:").pack(side=tk.LEFT, padx=5)
        self.adjust_panel_id_var = tk.StringVar(value="1")
        id_entry = ctk.CTkEntry(id_frame, textvariable=self.adjust_panel_id_var, width=50)
        id_entry.pack(side=tk.LEFT, padx=5)
        
        # Width input
        width_frame = ctk.CTkFrame(adjustment_frame)
        width_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(width_frame, text="Width:").pack(side=tk.LEFT, padx=5)
        
        # Feet
        self.adjust_width_feet_var = tk.StringVar(value="0")
        feet_entry = ctk.CTkEntry(width_frame, textvariable=self.adjust_width_feet_var, width=50)
        feet_entry.pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(width_frame, text="feet").pack(side=tk.LEFT)
        
        # Inches
        self.adjust_width_inches_var = tk.StringVar(value="0")
        inches_entry = ctk.CTkEntry(width_frame, textvariable=self.adjust_width_inches_var, width=50)
        inches_entry.pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(width_frame, text="inches").pack(side=tk.LEFT)
        
        # Fraction
        ctk.CTkLabel(width_frame, text="+").pack(side=tk.LEFT, padx=2)
        self.adjust_width_fraction_var = tk.StringVar(value="0")
        fraction_options = ["0", "1/16", "1/8", "3/16", "1/4", "5/16", "3/8", "7/16", 
                            "1/2", "9/16", "5/8", "11/16", "3/4", "13/16", "7/8", "15/16"]
        fraction_dropdown = ctk.CTkOptionMenu(
            width_frame,
            variable=self.adjust_width_fraction_var,
            values=fraction_options,
            width=70
        )
        fraction_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = ctk.CTkFrame(adjustment_frame)
        button_frame.pack(pady=5)
        
        apply_btn = ctk.CTkButton(
            button_frame, 
            text="Apply Width Adjustment",
            command=self.apply_panel_width_adjustment
        )
        apply_btn.pack(side=tk.LEFT, padx=5)
        
        reset_btn = ctk.CTkButton(
            button_frame,
            text="Reset All Adjustments",
            command=self.reset_panel_adjustments
        )
        reset_btn.pack(side=tk.LEFT, padx=5)

        # Initialize custom panel widths dictionary if needed
        if not hasattr(self, 'custom_panel_widths'):
            self.custom_panel_widths = {}

        
    def apply_panel_width_adjustment(self):
        """Apply custom width to a specific panel"""
        try:
            # Determine which panel ID variable to use based on what exists
            if hasattr(self, 'panel_id_var'):
                panel_id = int(self.panel_id_var.get())
                feet_var = self.panel_width_feet_adjust_var
                inches_var = self.panel_width_inches_adjust_var
                fraction_var = self.panel_width_fraction_adjust_var
            elif hasattr(self, 'adjust_panel_id_var'):
                panel_id = int(self.adjust_panel_id_var.get())
                feet_var = self.adjust_width_feet_var
                inches_var = self.adjust_width_inches_var
                fraction_var = self.adjust_width_fraction_var
            else:
                messagebox.showerror("Error", "Panel ID variable not found")
                return
            
            # Get width dimensions
            feet = self.safe_int_conversion(feet_var.get(), 0)
            inches = self.safe_int_conversion(inches_var.get(), 0)
            fraction = fraction_var.get()
            
            # Convert to total inches
            total_inches = self.convert_to_inches(feet, inches, fraction)
            
            if total_inches <= 0:
                messagebox.showerror("Error", "Width must be greater than zero")
                return
            
            # Ensure this panel exists or will exist
            if panel_id <= 0 or panel_id > 10:  # Reasonable limit
                messagebox.showerror("Error", "Invalid panel ID. Please use 1-10.")
                return
            
            # Initialize custom panel widths dictionary if needed
            if not hasattr(self, 'custom_panel_widths'):
                self.custom_panel_widths = {}
            
            # Store custom width
            self.custom_panel_widths[panel_id] = total_inches
            print(f"Applied width adjustment for panel {panel_id}: {total_inches} inches")
            print(f"Custom panel widths: {self.custom_panel_widths}")
            
            # Important: Turn off center panels and equal panels to avoid conflicts
            if self.center_panels_var.get():
                self.center_panels_var.set(False)
                
            if self.use_equal_panels:
                self.equal_panels_var.set(False)
            
            # Recalculate and redraw
            self.calculate()
            
            # Format dimension for display
            dim, frac = self.convert_to_feet_inches_fraction(total_inches)
            formatted_width = self.format_dimension(dim, frac)
            messagebox.showinfo("Success", f"Panel {panel_id} width adjusted to {formatted_width}")
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")

    def reset_panel_adjustments(self):
        """Clear all panel width adjustments and split information"""
        try:
            # Initialize dictionaries if they don't exist
            if not hasattr(self, 'custom_panel_widths'):
                self.custom_panel_widths = {}
            if not hasattr(self, 'split_panels'):
                self.split_panels = {}
            
            # Clear dictionaries
            self.custom_panel_widths.clear()
            self.split_panels.clear()
            
            # Recalculate and redraw
            self.calculate()
            
            messagebox.showinfo("Success", "All panel width adjustments have been reset")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset panel adjustments: {str(e)}")
            # Print stack trace for debugging
            import traceback
            traceback.print_exc()
        
    def calculate_panels(self) -> List[Panel]:
            # Add debugging
        current_wall = self.get_current_wall()
        if current_wall:
            print(f"Calculating panels for: {current_wall.name} with height {current_wall.dimensions['height'].feet}'{current_wall.dimensions['height'].inches}\"")
        
        # Update dimensions from UI with safe conversion
        wall_width_feet = self.safe_int_conversion(self.wall_width_feet_var.get(), 0)
        wall_width_inches = self.safe_int_conversion(self.wall_width_inches_var.get(), 0)
        wall_width_fraction = self.wall_width_fraction_var.get()
        
        wall_height_feet = self.safe_int_conversion(self.wall_height_feet_var.get(), 0)
        wall_height_inches = self.safe_int_conversion(self.wall_height_inches_var.get(), 0)
        wall_height_fraction = self.wall_height_fraction_var.get()
        
        panel_width_feet = self.safe_int_conversion(self.panel_width_feet_var.get(), 0)
        panel_width_inches = self.safe_int_conversion(self.panel_width_inches_var.get(), 0)
        panel_width_fraction = self.panel_width_fraction_var.get()
        
        panel_height_feet = self.safe_int_conversion(self.panel_height_feet_var.get(), 0)
        panel_height_inches = self.safe_int_conversion(self.panel_height_inches_var.get(), 0)
        panel_height_fraction = self.panel_height_fraction_var.get()
        
        self.wall_dimensions = {
            "width": Dimension(wall_width_feet, wall_width_inches),
            "width_fraction": wall_width_fraction,
            "height": Dimension(wall_height_feet, wall_height_inches),
            "height_fraction": wall_height_fraction
        }
        
        self.panel_dimensions = {
            "width": Dimension(panel_width_feet, panel_width_inches),
            "width_fraction": panel_width_fraction,
            "height": Dimension(panel_height_feet, panel_height_inches),
            "height_fraction": panel_height_fraction
        }
        
        self.use_equal_panels = self.equal_panels_var.get()
        self.panel_count = max(1, self.safe_int_conversion(self.panel_count_var.get(), 2))
        self.use_baseboard = self.baseboard_var.get()
        self.baseboard_height = self.safe_int_conversion(self.baseboard_height_var.get(), 4)
        self.baseboard_fraction = self.baseboard_fraction_var.get() if hasattr(self, 'baseboard_fraction_var') else "0"
        floor_mounted = self.floor_mounted_var.get()
        height_offset_feet = self.safe_int_conversion(self.height_offset_feet_var.get(), 0)
        height_offset_inches = self.safe_int_conversion(self.height_offset_inches_var.get(), 0)
        height_offset_fraction = self.height_offset_fraction_var.get()

        height_offset_dim = Dimension(height_offset_feet, height_offset_inches)
        # Calculate wall dimensions in inches with fractions
        wall_width_inches_total = self.convert_to_inches(
            wall_width_feet,
            wall_width_inches,
            wall_width_fraction
        )
        
        wall_height_inches_total = self.convert_to_inches(
            wall_height_feet,
            wall_height_inches,
            wall_height_fraction
        )

        if wall_width_inches_total <= 0 or wall_height_inches_total <= 0:
            return []

        # Calculate baseboard height with fraction
        baseboard_inches_total = self.baseboard_height
        if hasattr(self, 'baseboard_fraction_var'):
            baseboard_inches_total += self.fraction_to_decimal(self.baseboard_fraction_var.get())

        # Calculate usable height
        usable_height_inches = wall_height_inches_total - (baseboard_inches_total if self.use_baseboard else 0)
        if usable_height_inches <= 0:
            return []

        # Calculate panel height with fraction
        panel_height_inches_total = self.convert_to_inches(
            panel_height_feet,
            panel_height_inches,
            panel_height_fraction
        )
        
        panel_height_inches_total = min(panel_height_inches_total, usable_height_inches)
        panel_height_dim, panel_height_frac = self.convert_to_feet_inches_fraction(panel_height_inches_total)

        # Initialize panels as an empty list
        panels = []
        
        # Check if we have custom widths that should override everything else
        use_custom_panels = False
        if hasattr(self, 'custom_panel_widths') and self.custom_panel_widths:
            # Only use custom panels if we have a reasonable number of widths defined
            custom_panel_ids = sorted(self.custom_panel_widths.keys())
            if len(custom_panel_ids) > 0 and max(custom_panel_ids) <= 10:  # Reasonable limit
                total_width = sum(self.custom_panel_widths.values())
                # If total width is reasonable, use custom panels
                if total_width > 0 and total_width <= wall_width_inches_total * 1.05:  # Allow slight margin
                    use_custom_panels = True
        
        if use_custom_panels:
            # Use purely custom panels based on stored widths
            print("Using custom panel widths")
            # Sort panel IDs to ensure consistent ordering
            panel_ids = sorted(self.custom_panel_widths.keys())
            
            # Scale widths if they exceed wall width
            total_width = sum(self.custom_panel_widths.values())
            scale_factor = 1.0
            if total_width > wall_width_inches_total:
                scale_factor = wall_width_inches_total / total_width
                print(f"Scaling panel widths by factor {scale_factor}")
            
            # Create panels with custom widths
            current_x_percent = 0
            for panel_id in panel_ids:
                # Get scaled width
                panel_width = self.custom_panel_widths[panel_id] * scale_factor
                panel_width_percent = (panel_width / wall_width_inches_total * 100)
                panel_dim, panel_frac = self.convert_to_feet_inches_fraction(panel_width)
                
                # Create panel
                panel = Panel(
                    id=panel_id,
                    x=current_x_percent,  # Position as percentage
                    width=panel_width_percent,  # Width as percentage
                    actual_width=panel_dim, 
                    actual_width_fraction=panel_frac,
                    height=panel_height_dim,
                    height_fraction=panel_height_frac,
                    color=self.panel_color,
                    border_color=self.panel_border_color,
                    floor_mounted=floor_mounted,
                    height_offset=height_offset_dim if not floor_mounted else None,
                    height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                )
                panels.append(panel)
                current_x_percent += panel_width_percent  # Update x position for next panel
                
        # If we're not using custom panels, apply standard panel layouts
        else:
            # Center Equal Panels Logic
            if self.center_panels_var.get():
                center_panel_count = max(1, self.safe_int_conversion(self.center_panel_count_var.get(), 4))
                center_panel_width = 48  # Fixed width for center panels in inches
                total_center_width = center_panel_count * center_panel_width

                if total_center_width > wall_width_inches_total:
                    messagebox.showerror("Error", "Center panels exceed wall width!")
                    return []

                # Calculate remaining width for side panels
                side_panel_width = (wall_width_inches_total - total_center_width) / 2

                # Add left panel if applicable
                if side_panel_width > 0:
                    side_panel_dim, side_panel_frac = self.convert_to_feet_inches_fraction(side_panel_width)
                    panels.append(Panel(
                        id=1,
                        x=0,
                        width=(side_panel_width / wall_width_inches_total * 100),
                        actual_width=side_panel_dim,
                        actual_width_fraction=side_panel_frac,
                        height=panel_height_dim,
                        height_fraction=panel_height_frac,
                        color=self.panel_color,
                        border_color=self.panel_border_color,
                        floor_mounted=floor_mounted,
                        height_offset=height_offset_dim if not floor_mounted else None,
                        height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                    ))

                # Add center panels
                for i in range(center_panel_count):
                    center_panel_dim, center_panel_frac = self.convert_to_feet_inches_fraction(center_panel_width)
                    panels.append(Panel(
                        id=len(panels) + 1,
                        x=(side_panel_width + i * center_panel_width) / wall_width_inches_total * 100,
                        width=(center_panel_width / wall_width_inches_total * 100),
                        actual_width=center_panel_dim,
                        actual_width_fraction=center_panel_frac,
                        height=panel_height_dim,
                        height_fraction=panel_height_frac,
                        color=self.panel_color,
                        border_color=self.panel_border_color,
                        floor_mounted=floor_mounted,
                        height_offset=height_offset_dim if not floor_mounted else None,
                        height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                    ))

                # Add right panel if applicable
                if side_panel_width > 0:
                    side_panel_dim, side_panel_frac = self.convert_to_feet_inches_fraction(side_panel_width)
                    panels.append(Panel(
                        id=len(panels) + 1,
                        x=((wall_width_inches_total - side_panel_width) / wall_width_inches_total * 100),
                        width=(side_panel_width / wall_width_inches_total * 100),
                        actual_width=side_panel_dim,
                        actual_width_fraction=side_panel_frac,
                        height=panel_height_dim,
                        height_fraction=panel_height_frac,
                        color=self.panel_color,
                        border_color=self.panel_border_color,
                        floor_mounted=floor_mounted,
                        height_offset=height_offset_dim if not floor_mounted else None,
                        height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                    ))
            # In calculate_panels method, add this elif condition:
            elif self.use_start_seam_var.get():
                # Use start seam positioning
                panels = self.calculate_start_seam_panels(
                    wall_width_inches_total, panel_height_dim, panel_height_frac,
                    floor_mounted, height_offset_dim, height_offset_fraction
                )                    
            # Equal Panels Logic
            elif self.use_equal_panels:
                base_panel_width = wall_width_inches_total / self.panel_count
                
                current_x = 0
                for i in range(self.panel_count):
                    panel_dim, panel_frac = self.convert_to_feet_inches_fraction(base_panel_width)
                    panels.append(Panel(
                        id=i+1,  # Start IDs from 1 for better user understanding
                        x=(current_x / wall_width_inches_total * 100),
                        width=(base_panel_width / wall_width_inches_total * 100),
                        actual_width=panel_dim,
                        actual_width_fraction=panel_frac,
                        height=panel_height_dim,
                        height_fraction=panel_height_frac,
                        color=self.panel_color,
                        border_color=self.panel_border_color,
                        floor_mounted=floor_mounted,
                        height_offset=height_offset_dim if not floor_mounted else None,
                        height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                    ))
                    current_x += base_panel_width
                    
            # Fixed Width Panels Logic
            else:
                panel_width_inches_total = self.convert_to_inches(
                    panel_width_feet,
                    panel_width_inches,
                    panel_width_fraction
                )
                
                if panel_width_inches_total <= 0:
                    return []

                current_x = 0
                panel_id = 1
                while current_x < wall_width_inches_total:
                    current_panel_width = min(panel_width_inches_total, wall_width_inches_total - current_x)
                    panel_dim, panel_frac = self.convert_to_feet_inches_fraction(current_panel_width)
                    
                    panels.append(Panel(
                        id=panel_id,
                        x=(current_x / wall_width_inches_total * 100),
                        width=(current_panel_width / wall_width_inches_total * 100),
                        actual_width=panel_dim,
                        actual_width_fraction=panel_frac,
                        height=panel_height_dim,
                        height_fraction=panel_height_frac,
                        color=self.panel_color,
                        border_color=self.panel_border_color,
                        floor_mounted=floor_mounted,
                        height_offset=height_offset_dim if not floor_mounted else None,
                        height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                    ))
                    current_x += panel_width_inches_total
                    panel_id += 1
        
        # Process split panels
        # Inside calculate_panels, replace the split panel handling section:
        # Process split panels
        if hasattr(self, 'split_panels') and self.split_panels:
            # Create a mapping of original panels by ID
            panel_map = {p.id: p for p in panels}
            
            # Create the final panel list
            final_panels = []
            processed_ids = set()
            
            # Sort panels by their x position for consistent ordering
            sorted_panels = sorted(panels, key=lambda p: p.x)
            
            for panel in sorted_panels:
                # Skip if we've already processed this panel
                if panel.id in processed_ids:
                    continue
                
                # Check if this panel is the left side of a split
                is_left_panel = False
                split_info = None
                
                for orig_id, info in self.split_panels.items():
                    if panel.id == info['left_id']:
                        is_left_panel = True
                        split_info = info
                        break
                
                if not is_left_panel:
                    # This is not a split panel's left side, add as-is
                    final_panels.append(panel)
                    processed_ids.add(panel.id)
                    continue
                
                # This is a left panel in a split
                
                # Get the half width in inches
                half_width_inches = split_info['half_width']
                # Convert to dimensions
                half_dim, half_frac = self.convert_to_feet_inches_fraction(half_width_inches)
                
                # Calculate percentages
                half_width_percent = (half_width_inches / wall_width_inches_total) * 100
                
                # Add left panel
                left_panel = Panel(
                    id=panel.id,
                    x=panel.x,  # Use existing x position
                    width=half_width_percent,
                    actual_width=half_dim,
                    actual_width_fraction=half_frac,
                    height=panel.height,
                    height_fraction=panel.height_fraction,
                    color=panel.color,
                    border_color=self.panel_border_color,
                    floor_mounted=floor_mounted,
                    height_offset=height_offset_dim if not floor_mounted else None,
                    height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                )
                final_panels.append(left_panel)
                processed_ids.add(panel.id)
                
                # Calculate right panel position
                right_x_percent = panel.x + half_width_percent
                right_id = split_info['right_id']
                
                # Add right panel
                right_panel = Panel(
                    id=right_id,
                    x=right_x_percent,
                    width=half_width_percent,
                    actual_width=half_dim,
                    actual_width_fraction=half_frac,
                    height=panel.height,
                    height_fraction=panel.height_fraction,
                    color=panel.color,
                    border_color=self.panel_border_color,
                    floor_mounted=floor_mounted,
                    height_offset=height_offset_dim if not floor_mounted else None,
                    height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                )
                final_panels.append(right_panel)
                processed_ids.add(right_id)
            
            return final_panels
        
        return panels

    def debug_panel_state(self):
        """Print debugging information about the current panel state"""
        print("\n=== PANEL STATE DEBUG ===")
        
        # Print custom panel widths
        if hasattr(self, 'custom_panel_widths'):
            print(f"Custom Panel Widths: {self.custom_panel_widths}")
        else:
            print("No custom panel widths")
        
        # Print split panels
        if hasattr(self, 'split_panels'):
            print(f"Split Panels: {self.split_panels}")
        else:
            print("No split panels")
        
        # Print current panels
        panels = self.calculate_panels()
        print(f"Panel count: {len(panels)}")
        for p in panels:
            print(f"Panel {p.id}: width={p.width}%, actual_width={self.format_dimension(p.actual_width, p.actual_width_fraction)}")
        
        print("=========================\n")

        
    def toggle_selection_mode(self):
        """Toggle panel selection mode"""
        self.selection_mode = self.selection_mode_var.get()
        cursor = "hand2" if self.selection_mode else ""
        self.canvas.config(cursor=cursor)
        
        # Update canvas with visual cue for selection mode
        self.calculate()  # Redraw everything
        
    def on_canvas_click(self, event):
        """Handle canvas click based on current mode"""
        if self.annotation_mode:
            print(f"Click in annotation mode: ({event.x}, {event.y})")
            self.debug_line_drawing_state()
            
            # Check if clicked on an existing annotation
            annotation = self.find_annotation_at_position(event.x, event.y)
            
            if annotation:
                print(f"Found annotation {annotation.id}")
                # Start moving the annotation
                self.moving_annotation = True
                self.current_annotation = annotation
                return
            
            # If line drawing is enabled and we have an annotation selected
            if self.line_drawing_var.get() and self.current_annotation:
                print(f"Starting line from annotation {self.current_annotation.id}")
                # Start drawing a line from the current annotation
                self.line_drawing = True
                self.annotation_line_start = self.current_annotation
                return
            
            # Create a new annotation circle at click position
            print("Adding new annotation")
            self.manual_add_circle(event.x, event.y)
        elif self.selection_mode:
            # Handle panel selection (existing code)
            clicked_panel = self.find_panel_at_position(event.x, event.y)
            if clicked_panel:
                if clicked_panel.id in self.selected_panels:
                    # Deselect the panel
                    self.selected_panels.remove(clicked_panel.id)
                else:
                    # Select the panel
                    self.selected_panels.append(clicked_panel.id)
                
                # Update the selected panels display
                self.update_selected_panels_display()
                
                # Redraw the canvas to show selection
                self.calculate()
        
    def find_panel_at_position(self, x, y):
        """Find the panel at the given canvas coordinates"""
        # Get the current panels
        panels = self.calculate_panels()
        if not panels:
            return None
        
        # Get canvas dimensions and scaling
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        margin = 100
        
        # Calculate wall dimensions
        wall_width_inches = self.convert_to_inches(
            self.wall_dimensions["width"].feet,
            self.wall_dimensions["width"].inches,
            self.wall_dimensions.get("width_fraction", "0")
        )
        
        wall_height_inches = self.convert_to_inches(
            self.wall_dimensions["height"].feet,
            self.wall_dimensions["height"].inches,
            self.wall_dimensions.get("height_fraction", "0")
        )
        
        # Calculate scaling factor
        wall_aspect_ratio = wall_width_inches / wall_height_inches
        canvas_aspect_ratio = (canvas_width - 2 * margin) / (canvas_height - 2 * margin)
        
        if wall_aspect_ratio > canvas_aspect_ratio:
            scale = (canvas_width - 2 * margin) / wall_width_inches
        else:
            scale = (canvas_height - 2 * margin) / wall_height_inches
        
        scale *= 0.8
        
        scaled_width = wall_width_inches * scale
        scaled_height = wall_height_inches * scale
        
        x_offset = (canvas_width - scaled_width) / 2
        y_offset = (canvas_height - scaled_height) / 2
        
        # Check each panel
        for panel in panels:
            panel_x = x_offset + (panel.x / 100 * scaled_width)
            panel_width = (panel.width / 100 * scaled_width)
            
            # Calculate baseboard height
            baseboard_height_inches = 0
            if self.use_baseboard:
                baseboard_height_inches = self.baseboard_height
                if hasattr(self, 'baseboard_fraction_var'):
                    baseboard_height_inches += self.fraction_to_decimal(self.baseboard_fraction_var.get())
            
            baseboard_height = baseboard_height_inches * scale if self.use_baseboard else 0
            
            # Calculate panel height
            panel_height_inches = self.convert_to_inches(
                panel.height.feet, 
                panel.height.inches, 
                panel.height_fraction
            )
            
            # Calculate panel y position
            if self.use_baseboard:
                panel_bottom = y_offset + scaled_height - baseboard_height
            else:
                panel_bottom = y_offset + scaled_height
                
            panel_top = panel_bottom - (panel_height_inches * scale)
            
            # Check if click is inside this panel
            if (panel_x <= x <= panel_x + panel_width and
                panel_top <= y <= panel_bottom):
                return panel
        
        return None

    def update_selected_panels_display(self):
        """Update the label showing selected panels"""
        if not self.selected_panels:
            self.selected_panels_label.configure(text="None")
        else:
            sorted_ids = sorted(self.selected_panels)
            self.selected_panels_label.configure(text=", ".join(map(str, sorted_ids)))

    def clear_panel_selection(self):
        """Clear all selected panels"""
        self.selected_panels = []
        self.update_selected_panels_display()
        self.calculate()  # Redraw everything

    def choose_object_color(self):
        """Open color picker for the object"""
        current_color = self.object_color_preview["background"]
        color = colorchooser.askcolor(color=current_color, title="Choose Object Color")
        if color[1]:  # color is ((R, G, B), hex_color)
            self.object_color_preview.configure(bg=color[1])
            
    # Method 2: add_wall_object - The part that needs updating
    def add_wall_object(self):
        """Add a wall object with reference point handling"""
        if not self.selected_panels:
            messagebox.showerror("Error", "Please select at least one panel first")
            return
        
        # Get object dimensions
        width_feet = self.safe_int_conversion(self.object_width_feet_var.get(), 0)
        width_inches = self.safe_int_conversion(self.object_width_inches_var.get(), 0)
        width_fraction = self.object_width_fraction_var.get()
        
        height_feet = self.safe_int_conversion(self.object_height_feet_var.get(), 0)
        height_inches = self.safe_int_conversion(self.object_height_inches_var.get(), 0)
        height_fraction = self.object_height_fraction_var.get()
        
        # Convert to dimensions
        width_dim = Dimension(width_feet, width_inches)
        height_dim = Dimension(height_feet, height_inches)
        
        # Get object dimensions in inches
        object_width_inches = self.convert_to_inches(width_feet, width_inches, width_fraction)
        object_height_inches = self.convert_to_inches(height_feet, height_inches, height_fraction)
        
        # Get wall and panel dimensions
        wall_width_inches = self.convert_to_inches(
            self.wall_dimensions["width"].feet,
            self.wall_dimensions["width"].inches,
            self.wall_dimensions.get("width_fraction", "0")
        )
        
        wall_height_inches = self.convert_to_inches(
            self.wall_dimensions["height"].feet,
            self.wall_dimensions["height"].inches,
            self.wall_dimensions.get("height_fraction", "0")
        )
        
        # Calculate panel height
        panel_height_inches = self.convert_to_inches(
            self.panel_dimensions["height"].feet,
            self.panel_dimensions["height"].inches,
            self.panel_dimensions.get("height_fraction", "0")
        )
        
        # Calculate baseboard height if used
        baseboard_height_inches = 0
        if self.use_baseboard:
            baseboard_height_inches = self.baseboard_height
            if hasattr(self, 'baseboard_fraction_var'):
                baseboard_height_inches += self.fraction_to_decimal(self.baseboard_fraction_var.get())
        
        usable_height_inches = wall_height_inches - baseboard_height_inches
        
        # Process vertical position with reference points
        y_feet = self.safe_int_conversion(self.object_y_feet_var.get(), 0)
        y_inches = self.safe_int_conversion(self.object_y_inches_var.get(), 0)
        y_fraction = self.object_y_fraction_var.get()
        
        # Get vertical position in inches from input
        v_position_inches = self.convert_to_inches(y_feet, y_inches, y_fraction)
        
        # Get reference point selections
        v_reference = self.v_reference_var.get()  # "Top Edge", "Center", or "Bottom Edge"
        v_origin = self.v_origin_var.get()  # "Wall Top" or "Panel Top"
        
        # Calculate object center position from reference point
        if v_reference == "Top Edge":
            # If referencing top edge, add half height to get to center
            v_position_inches += object_height_inches / 2
        elif v_reference == "Bottom Edge":
            # If referencing bottom edge, subtract half height to get to center
            v_position_inches -= object_height_inches / 2
        # "Center" reference doesn't need adjustment
        
        # Adjust for panel top if needed
        if v_origin == "Panel Top":
            # FIXED: Calculate the non-panel height (distance from wall top to panel top)
            non_panel_height = wall_height_inches - panel_height_inches
            if self.use_baseboard:
                non_panel_height -= baseboard_height_inches
            
            # Add the non-panel height to position from panel top
            v_position_inches += non_panel_height
        
        # Calculate vertical position as percentage from top of usable wall area
        y_position = (v_position_inches / usable_height_inches) * 100
        y_position = max(0, min(100, y_position))  # Clamp to valid range
        
        # Process horizontal position (similar to existing code)
        use_exact_position = hasattr(self, 'use_exact_h_position_var') and self.use_exact_h_position_var.get()
        
        if use_exact_position:
            # Using exact horizontal position
            h_feet = self.safe_int_conversion(self.object_h_feet_var.get(), 0)
            h_inches = self.safe_int_conversion(self.object_h_inches_var.get(), 0)
            h_fraction = self.object_h_fraction_var.get()
            
            # Calculate position in inches
            h_position_inches = self.convert_to_inches(h_feet, h_inches, h_fraction)
            
            # Get horizontal reference point
            h_reference = self.h_reference_var.get()  # "Left Edge", "Center", or "Right Edge"
            
            # Adjust based on reference point
            if h_reference == "Center":
                # Center reference - no adjustment needed
                pass
            elif h_reference == "Right Edge":
                # Right edge reference - subtract object width to get to center
                h_position_inches -= object_width_inches / 2
            else:  # Left Edge
                # Left edge reference - add half width to get to center
                h_position_inches += object_width_inches / 2
            
            # Convert to percentage of wall width
            x_position = (h_position_inches / wall_width_inches) * 100
            x_position = min(max(x_position, 0), 100)  # Clamp to valid range
            
            # Store values for the object
            h_position_feet = h_feet
            h_position_inches = h_inches
            h_position_fraction = h_fraction
            alignment = "Custom"
        else:
            # Using alignment (same as existing code)
            panels = self.calculate_panels()
            selected_panels = [p for p in panels if p.id in self.selected_panels]
            alignment = self.object_alignment_var.get()
            
            if alignment == "Center":
                min_x = min(p.x for p in selected_panels)
                max_x = max(p.x + p.width for p in selected_panels)
                x_position = (min_x + max_x) / 2
            elif alignment == "Left Edge":
                min_x = min(p.x for p in selected_panels)
                object_half_width_pct = (object_width_inches / wall_width_inches * 100) / 2
                x_position = min_x + object_half_width_pct
            elif alignment == "Right Edge":
                max_x = max(p.x + p.width for p in selected_panels)
                object_half_width_pct = (object_width_inches / wall_width_inches * 100) / 2
                x_position = max_x - object_half_width_pct
                
            # Calculate equivalent measurements for display
            h_position_inches = (x_position / 100 * wall_width_inches) - (object_width_inches / 2)
            h_position_dim, h_position_frac = self.convert_to_feet_inches_fraction(h_position_inches)
            h_position_feet = h_position_dim.feet
            h_position_inches = h_position_dim.inches
            h_position_fraction = h_position_frac
        
        # Create the wall object with reference points
        wall_object = WallObject(
            id=self.next_object_id,
            name=self.object_name_var.get() or "Object",
            width=width_dim,
            width_fraction=width_fraction,
            height=height_dim,
            height_fraction=height_fraction,
            x_position=x_position,
            y_position=y_position,
            affected_panels=self.selected_panels.copy(),
            color=self.object_color_preview["background"],
            border_color=self.object_border_color_preview["background"],
            border_width=int(self.object_border_width_var.get()),
            show_border=self.object_border_var.get(),
            alignment=alignment,
            h_position_feet=h_position_feet,
            h_position_inches=h_position_inches,
            h_position_fraction=h_position_fraction,
            use_exact_position=use_exact_position,
            # Store reference points
            v_reference=v_reference,
            h_reference=self.h_reference_var.get() if use_exact_position else "Left Edge"
        )
        
        self.wall_objects.append(wall_object)
        self.next_object_id += 1
        
        # Redraw everything
        self.calculate()
        
        # Clear selection after adding
        self.clear_panel_selection()



        
    def remove_all_objects(self):
        """Remove all wall objects"""
        if not self.wall_objects:
            return
            
        if messagebox.askyesno("Confirm", "Remove all objects from the wall?"):
            self.wall_objects = []
            self.calculate()  # Redraw everything

    def draw_wall_objects(self, canvas_width, canvas_height, x_offset, y_offset, 
                         scaled_width, scaled_height, scale, baseboard_height=0):
        """Draw all wall objects with accurately positioned panel top reference line and precise measurements"""
        if not self.wall_objects:
            return
        
        # Define wall border thickness and calculate offset
        wall_border_width = 2  # This seems to be the default in your code for wall outline
        wall_border_offset = wall_border_width / 2
        
        # Determine if baseboard is being shown
        is_baseboard_shown = self.use_baseboard  # This is True if baseboard is shown, False otherwise
        
        # Get wall dimensions
        wall_width_inches = self.convert_to_inches(
            self.wall_dimensions["width"].feet,
            self.wall_dimensions["width"].inches,
            self.wall_dimensions.get("width_fraction", "0")
        )
        
        wall_height_inches = self.convert_to_inches(
            self.wall_dimensions["height"].feet,
            self.wall_dimensions["height"].inches,
            self.wall_dimensions.get("height_fraction", "0")
        )
        
        # Calculate panel height
        panel_height_inches = self.convert_to_inches(
            self.panel_dimensions["height"].feet,
            self.panel_dimensions["height"].inches,
            self.panel_dimensions.get("height_fraction", "0")
        )
        
        # Calculate usable wall height (accounting for baseboard)
        usable_height_inches = wall_height_inches
        baseboard_height_inches = 0
        if self.use_baseboard:
            baseboard_height_inches = self.baseboard_height
            if hasattr(self, 'baseboard_fraction_var'):
                baseboard_height_inches += self.fraction_to_decimal(self.baseboard_fraction_var.get())
            usable_height_inches -= baseboard_height_inches
        
        # Calculate actual wall positions on canvas
        wall_top = y_offset
        if self.use_baseboard:
            wall_bottom = y_offset + scaled_height - baseboard_height
        else:
            wall_bottom = y_offset + scaled_height
        
        # Adjusted wall boundaries accounting for border
        wall_top_effective = wall_top + wall_border_offset
        wall_bottom_effective = wall_bottom - wall_border_offset
        wall_left_effective = x_offset + wall_border_offset
        wall_right_effective = x_offset + scaled_width - wall_border_offset
        
        # Calculate the panel top position correctly based on actual panel height
        # Panel height should be constrained by usable height
        visual_panel_height = min(panel_height_inches, usable_height_inches) * scale
        
        # The panel top is determined by the wall height minus panel height
        # (accounting for baseboard if present)
        panel_top = wall_bottom - visual_panel_height
        
        # Determine distance reference point
        distance_reference = "Wall Top"
        if hasattr(self, 'distance_reference_var'):
            distance_reference = self.distance_reference_var.get()
        
        # Draw vertical object distances if that option is enabled
        if self.show_object_distances_var.get():
            # Draw the panel top reference line as a visual indicator
            if distance_reference == "Panel Top":
                self.canvas.create_line(
                    x_offset, panel_top,
                    x_offset + scaled_width, panel_top,
                    fill="#FF0000",  # Red - matching your existing red line
                    width=1,
                    dash=(5, 3)      # Dashed line
                )
        
        # Draw all objects
        for obj in self.wall_objects:
            # Calculate object dimensions in inches
            width_inches = self.convert_to_inches(
                obj.width.feet,
                obj.width.inches,
                obj.width_fraction
            )
            
            height_inches = self.convert_to_inches(
                obj.height.feet,
                obj.height.inches,
                obj.height_fraction
            )
            
            # Calculate border thickness in pixels
            border_width = obj.border_width if obj.show_border else 0
            
            # Calculate position and size on canvas
            obj_width = width_inches * scale
            obj_height = height_inches * scale
            
            # Calculate horizontal position based on percentage
            obj_x = x_offset + (obj.x_position * scaled_width / 100) - (obj_width / 2)
            
            # Calculate the usable wall height (total minus baseboard if used)
            if self.use_baseboard:
                usable_canvas_height = scaled_height - baseboard_height
            else:
                usable_canvas_height = scaled_height
            
            # Calculate Y position from top of wall (adjust for object centering)
            obj_y = y_offset + ((obj.y_position / 100) * usable_canvas_height) - (obj_height / 2)
            
            # Calculate effective boundaries including border
            # For Tkinter, the border is drawn centered on the boundary
            # So half extends outside, half inside
            border_offset = border_width / 2
            effective_top = obj_y - border_offset
            effective_bottom = obj_y + obj_height + border_offset
            effective_left = obj_x - border_offset
            effective_right = obj_x + obj_width + border_offset
            
            # Draw object rectangle
            self.canvas.create_rectangle(
                obj_x, obj_y,
                obj_x + obj_width, obj_y + obj_height,
                fill=obj.color,
                outline=obj.border_color if obj.show_border else "",
                width=border_width
            )
            
            # Draw object label
            self.canvas.create_text(
                obj_x + obj_width / 2,
                obj_y + obj_height / 2,
                text=obj.name,
                fill="black",
                font=("Arial", 10, "bold")
            )
            
            # Show position information
            if self.show_dimensions_var.get():
                # Draw width and height dimensions
                self.draw_dimension_line(
                    obj_x, obj_y - 10,
                    obj_x + obj_width, obj_y - 10,
                    obj.width,
                    obj.width_fraction,
                    offset=15,
                    side="top"
                )
                
                self.draw_dimension_line(
                    obj_x - 10, obj_y,
                    obj_x - 10, obj_y + obj_height,
                    obj.height,
                    obj.height_fraction,
                    offset=15,
                    side="left"
                )
            
            # Show vertical object distances if that option is enabled
            if self.show_object_distances_var.get():
                # When determining reference points, use the effective boundaries
                reference_top = panel_top if distance_reference == "Panel Top" else wall_top_effective
                
                # Add a small epsilon to avoid floating point errors
                epsilon = 0.001
                
                # IMPORTANT: Use different correction factors and account for baseboard visibility
                # Only for top distance - different correction factors based on reference and baseboard
                if distance_reference == "Panel Top":
                    if is_baseboard_shown:
                        # Panel Top WITH baseboard: 7'3 11/16" vs 8'0" → need to add 8 5/16"
                        panel_top_correction = -8.3125  # Negative to add 8 5/16 inches (8.3125)
                    else:
                        # Panel Top WITHOUT baseboard: 8'0 1/2" vs 8'0" → need to subtract 1/2"
                        panel_top_correction = 0.5  # Positive to subtract 1/2 inch
                        
                    # TOP DISTANCE calculation for Panel Top reference
                    top_distance_pixels = abs(effective_top - reference_top)
                    top_distance_inches = (top_distance_pixels / scale) + epsilon + panel_top_correction
                    if top_distance_inches < 0:
                        top_distance_inches = 0
                else:
                    # For Wall Top reference:
                    if is_baseboard_shown:
                        # Wall Top WITH baseboard: 9'1 13/16" vs 9'8" → need to add 6 3/16"
                        wall_top_correction = -6.1875  # Negative to add 6 3/16 inches (6.1875)
                    else:
                        # Wall Top WITHOUT baseboard: 9'5" vs 10'0" → need to add 7 inches
                        wall_top_correction = -7.0  # Negative to add 7 inches
                        
                    # TOP DISTANCE calculation for Wall Top reference
                    top_distance_pixels = abs(effective_top - reference_top)
                    top_distance_inches = (top_distance_pixels / scale) + epsilon + wall_top_correction
                    if top_distance_inches < 0:
                        top_distance_inches = 0
                
                # Convert to feet/inches with proper rounding
                top_dim, top_frac = self.convert_to_feet_inches_fraction(top_distance_inches)
                
                # Define a consistent reference point for the bottom of the panel
                # This ensures bottom measurements are consistent regardless of baseboard visibility
                
                # Calculate the baseboard height in scaled canvas units
                if self.use_baseboard:
                    baseboard_scaled_height = baseboard_height  # This is already scaled for canvas
                else:
                    # If baseboard is not showing, we still need to account for what would be the baseboard area
                    baseboard_inches = self.baseboard_height
                    if hasattr(self, 'baseboard_fraction_var'):
                        baseboard_inches += self.fraction_to_decimal(self.baseboard_fraction_var.get())
                    baseboard_scaled_height = baseboard_inches * scale
                
                # Always use the panel bottom without baseboard as our consistent reference
                consistent_panel_bottom = wall_bottom_effective - baseboard_scaled_height
                
                # BOTTOM DISTANCE - from bottom of object to bottom of panels (NOT including baseboard)
                bottom_distance_pixels = abs(consistent_panel_bottom - effective_bottom)
                bottom_distance_inches = (bottom_distance_pixels / scale) + epsilon
                
                # Apply a consistent correction for bottom measurements
                bottom_correction = 0.0  # Adjust if needed based on testing
                bottom_distance_inches += bottom_correction
                
                # No additional correction needed if we're using a consistent reference point
                bottom_dim, bottom_frac = self.convert_to_feet_inches_fraction(bottom_distance_inches)
                
                # For drawing the dimension line, use the visual panel bottom
                visual_panel_bottom = wall_bottom_effective
                if self.use_baseboard:
                    visual_panel_bottom -= baseboard_scaled_height
                
                # Use precise coordinates for dimension lines
                top_line_x = obj_x + obj_width + 20
                self.draw_dimension_line(
                    top_line_x, reference_top,
                    top_line_x, effective_top,
                    top_dim, top_frac,
                    offset=15,
                    side="right"
                )
                
                # Draw bottom distance measurement to the visual panel bottom
                bottom_line_x = obj_x + obj_width + 20
                self.draw_dimension_line(
                    bottom_line_x, effective_bottom,
                    bottom_line_x, visual_panel_bottom,  # Use visual panel bottom for the line
                    bottom_dim, bottom_frac,            # But use consistent measurement
                    offset=15,
                    side="right"
                )
            
            # Show horizontal distances independently if that option is enabled
            if self.show_horizontal_distances_var.get():
                # Apply the same precise measurement approach for horizontal distances
                epsilon = 0.001
                
                # Left distance - distance from object left to wall left
                left_distance_pixels = abs(effective_left - wall_left_effective)
                left_distance_inches = (left_distance_pixels / scale) + epsilon
                left_dim, left_frac = self.convert_to_feet_inches_fraction(left_distance_inches)
                
                # Right distance - distance from object right to wall right
                right_distance_pixels = abs(wall_right_effective - effective_right)
                right_distance_inches = (right_distance_pixels / scale) + epsilon
                right_dim, right_frac = self.convert_to_feet_inches_fraction(right_distance_inches)
                
                # Determine vertical position for horizontal measurements
                # If vertical dimensions are shown, place these a bit higher
                vertical_offset = -20
                if self.show_object_distances_var.get():
                    vertical_offset -= 25  # Move up further to avoid overlap
                
                # For horizontal distances
                self.draw_dimension_line(
                    wall_left_effective, obj_y + vertical_offset,
                    effective_left, obj_y + vertical_offset,
                    left_dim, left_frac,
                    offset=15,
                    side="top"
                )
                
                self.draw_dimension_line(
                    effective_right, obj_y + vertical_offset,
                    wall_right_effective, obj_y + vertical_offset,
                    right_dim, right_frac,
                    offset=15,
                    side="top"
                )
                
    def add_panel_splitting_feature(self):
        """Add UI for splitting a panel into two equal panels"""
        split_frame = ctk.CTkFrame(self.input_frame)
        split_frame.pack(pady=5, fill=tk.X)
        
        ctk.CTkLabel(split_frame, text="Panel Splitting").pack(pady=5)
        
        # Split selected panel button
        split_btn = ctk.CTkButton(
            split_frame,
            text="Split Selected Panel into Two Equal Panels",
            command=self.split_selected_panel
        )
        split_btn.pack(pady=5)
        
        # Note: This requires having a panel selected first
        instruction_label = ctk.CTkLabel(
            split_frame, 
            text="Note: Select a single panel first, then click to split"
        )
        instruction_label.pack(pady=2)
    def on_dimension_change(self, *args):
        """Save wall data when dimensions are changed"""
        current_wall = self.get_current_wall()
        if current_wall:
            self.save_current_wall_data()

    # Add this method to bind variable changes to auto-saving
    def setup_auto_save_bindings(self):
        """Set up bindings to auto-save wall data when values change"""
        # Bind dimension variables
        self.wall_width_feet_var.trace_add("write", self.on_dimension_change)
        self.wall_width_inches_var.trace_add("write", self.on_dimension_change)
        self.wall_width_fraction_var.trace_add("write", self.on_dimension_change)
        
        self.wall_height_feet_var.trace_add("write", self.on_dimension_change)
        self.wall_height_inches_var.trace_add("write", self.on_dimension_change)
        self.wall_height_fraction_var.trace_add("write", self.on_dimension_change)
    def split_selected_panel(self):
        """Split a selected panel into two equal panels"""
        if len(self.selected_panels) != 1:
            messagebox.showerror("Error", "Please select exactly one panel to split")
            return
        
        panel_id = self.selected_panels[0]
        
        # Get original panel configuration - make sure we have the latest panels
        panels = self.calculate_panels()
        
        # Find the selected panel
        selected_panel = None
        for panel in panels:
            if panel.id == panel_id:
                selected_panel = panel
                break
        
        if not selected_panel:
            messagebox.showerror("Error", "Selected panel not found")
            return
        
        # Get wall dimensions
        wall_width_inches = self.convert_to_inches(
            self.wall_dimensions["width"].feet,
            self.wall_dimensions["width"].inches,
            self.wall_dimensions.get("width_fraction", "0")
        )
        
        # Calculate panel width in ABSOLUTE inches (not percentage)
        panel_width_inches = (selected_panel.width / 100) * wall_width_inches
        
        # Calculate half width
        half_width_inches = panel_width_inches / 2
        
        # Find the highest ID currently in use
        highest_id = max([p.id for p in panels])
        new_right_id = highest_id + 1
        
        # Initialize custom panel widths dictionary if needed
        if not hasattr(self, 'custom_panel_widths'):
            self.custom_panel_widths = {}
        
        # Get current x position in inches from the left edge
        current_x_inches = (selected_panel.x / 100) * wall_width_inches
        
        # Calculate the new positions and widths in absolute inches
        left_x_inches = current_x_inches
        right_x_inches = current_x_inches + half_width_inches
        
        # Convert to percentages for panel positions
        left_x_percent = (left_x_inches / wall_width_inches) * 100
        right_x_percent = (right_x_inches / wall_width_inches) * 100
        width_percent = (half_width_inches / wall_width_inches) * 100
        
        # Calculate the dimensions for display
        half_dim, half_frac = self.convert_to_feet_inches_fraction(half_width_inches)
        
        # Clear any existing custom width for this panel
        if panel_id in self.custom_panel_widths:
            del self.custom_panel_widths[panel_id]
        
        # Clear any existing split panel relationships for this panel
        if hasattr(self, 'split_panels'):
            # Remove any existing split relationships for this panel
            for orig_id in list(self.split_panels.keys()):
                if (self.split_panels[orig_id]['left_id'] == panel_id or 
                    self.split_panels[orig_id]['right_id'] == panel_id):
                    del self.split_panels[orig_id]
        else:
            self.split_panels = {}
        
        # Store the split information
        self.split_panels[panel_id] = {
            'original_width': panel_width_inches,
            'half_width': half_width_inches,
            'left_id': panel_id,
            'right_id': new_right_id,
            'left_x': left_x_percent,
            'right_x': right_x_percent
        }
        
        # Store custom width for both panels
        self.custom_panel_widths[panel_id] = half_width_inches
        self.custom_panel_widths[new_right_id] = half_width_inches
        
        # Temporarily turn off center panels mode if active
        center_was_active = self.center_panels_var.get()
        if center_was_active:
            self.center_panels_var.set(False)
        
        # Recalculate and redraw
        self.calculate()
        
        # Select both new panels
        self.selected_panels = [panel_id, new_right_id]
        self.update_selected_panels_display()
        
        messagebox.showinfo("Success", f"Panel {panel_id} split into two equal panels (IDs: {panel_id} and {new_right_id})")
                
    def add_selection_frame(self):
        """Add UI controls for panel selection and object placement"""
        selection_frame = ctk.CTkFrame(self.input_frame)
        selection_frame.pack(pady=10, padx=10, fill=tk.X)
        
        ctk.CTkLabel(selection_frame, text="Panel Selection & Objects").pack(pady=5)
        
        # Selection mode toggle
        self.selection_mode_var = tk.BooleanVar(value=False)
        selection_mode_cb = ctk.CTkCheckBox(
            selection_frame,
            text="Enable Panel Selection Mode",
            variable=self.selection_mode_var,
            command=self.toggle_selection_mode
        )
        selection_mode_cb.pack(pady=5, anchor="w", padx=10)
        
        # Selected panels display
        selected_panels_frame = ctk.CTkFrame(selection_frame)
        selected_panels_frame.pack(pady=5, fill=tk.X)
        ctk.CTkLabel(selected_panels_frame, text="Selected Panels:").pack(side=tk.LEFT, padx=5)
        self.selected_panels_label = ctk.CTkLabel(selected_panels_frame, text="None")
        self.selected_panels_label.pack(side=tk.LEFT, padx=5)
        
        # Clear selection button
        clear_selection_btn = ctk.CTkButton(
            selection_frame,
            text="Clear Selection",
            command=self.clear_panel_selection
        )
        clear_selection_btn.pack(pady=5)
        
        # Object frame - for adding wall objects like TVs
        object_frame = ctk.CTkFrame(selection_frame)
        object_frame.pack(pady=5, fill=tk.X)
        
        # Object name
        name_frame = ctk.CTkFrame(object_frame)
        name_frame.pack(pady=5, fill=tk.X)
        ctk.CTkLabel(name_frame, text="Object Name:").pack(side=tk.LEFT, padx=5)
        self.object_name_var = tk.StringVar(value="TV")
        name_entry = ctk.CTkEntry(name_frame, textvariable=self.object_name_var, width=100)
        name_entry.pack(side=tk.LEFT, padx=5)
        
        # Object dimensions
        ctk.CTkLabel(object_frame, text="Object Dimensions:").pack(anchor="w", padx=5)
        
        # Width dimension
        width_frame = ctk.CTkFrame(object_frame)
        width_frame.pack(pady=2, fill=tk.X)
        ctk.CTkLabel(width_frame, text="Width:").pack(side=tk.LEFT, padx=5)
        
        # Feet
        self.object_width_feet_var = tk.StringVar(value="0")
        feet_entry = ctk.CTkEntry(width_frame, textvariable=self.object_width_feet_var, width=40)
        feet_entry.pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(width_frame, text="feet").pack(side=tk.LEFT)
        
        # Inches
        self.object_width_inches_var = tk.StringVar(value="0")
        inches_entry = ctk.CTkEntry(width_frame, textvariable=self.object_width_inches_var, width=40)
        inches_entry.pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(width_frame, text="inches").pack(side=tk.LEFT)
        
        # Fraction
        ctk.CTkLabel(width_frame, text="+").pack(side=tk.LEFT, padx=2)
        self.object_width_fraction_var = tk.StringVar(value="0")
        fraction_options = ["0", "1/16", "1/8", "3/16", "1/4", "5/16", "3/8", "7/16", 
                          "1/2", "9/16", "5/8", "11/16", "3/4", "13/16", "7/8", "15/16"]
        fraction_dropdown = ctk.CTkOptionMenu(
            width_frame, 
            variable=self.object_width_fraction_var,
            values=fraction_options,
            width=70
        )
        fraction_dropdown.pack(side=tk.LEFT, padx=2)
        
        # Height dimension
        height_frame = ctk.CTkFrame(object_frame)
        height_frame.pack(pady=2, fill=tk.X)
        ctk.CTkLabel(height_frame, text="Height:").pack(side=tk.LEFT, padx=5)
        
        # Feet
        self.object_height_feet_var = tk.StringVar(value="0")
        feet_entry = ctk.CTkEntry(height_frame, textvariable=self.object_height_feet_var, width=40)
        feet_entry.pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(height_frame, text="feet").pack(side=tk.LEFT)
        
        # Inches
        self.object_height_inches_var = tk.StringVar(value="0")
        inches_entry = ctk.CTkEntry(height_frame, textvariable=self.object_height_inches_var, width=40)
        inches_entry.pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(height_frame, text="inches").pack(side=tk.LEFT)
        
        # Fraction
        ctk.CTkLabel(height_frame, text="+").pack(side=tk.LEFT, padx=2)
        self.object_height_fraction_var = tk.StringVar(value="0")
        fraction_dropdown = ctk.CTkOptionMenu(
            height_frame, 
            variable=self.object_height_fraction_var,
            values=fraction_options,
            width=70
        )
        fraction_dropdown.pack(side=tk.LEFT, padx=2)
        
        # Object color
        color_frame = ctk.CTkFrame(object_frame)
        color_frame.pack(pady=2, fill=tk.X)
        ctk.CTkLabel(color_frame, text="Fill Color:").pack(side=tk.LEFT, padx=5)
        
        self.object_color_preview = tk.Canvas(color_frame, width=20, height=20, bg="#AAAAAA")
        self.object_color_preview.pack(side=tk.LEFT, padx=5)
        
        color_picker_button = ctk.CTkButton(
            color_frame,
            text="Choose Fill Color",
            command=self.choose_object_color,
            width=100
        )
        color_picker_button.pack(side=tk.LEFT, padx=5)
        
        # Add object border color picker
        border_color_frame = ctk.CTkFrame(object_frame)
        border_color_frame.pack(pady=2, fill=tk.X)
        ctk.CTkLabel(border_color_frame, text="Border Color:").pack(side=tk.LEFT, padx=5)
        
        self.object_border_color_preview = tk.Canvas(border_color_frame, width=20, height=20, bg="black")
        self.object_border_color_preview.pack(side=tk.LEFT, padx=5)
        
        border_color_picker_button = ctk.CTkButton(
            border_color_frame,
            text="Choose Border Color",
            command=self.choose_object_border_color,
            width=100
        )
        border_color_picker_button.pack(side=tk.LEFT, padx=5)
        
        # Add border width option
        border_width_frame = ctk.CTkFrame(object_frame)
        border_width_frame.pack(pady=2, fill=tk.X)
        ctk.CTkLabel(border_width_frame, text="Border Width:").pack(side=tk.LEFT, padx=5)
        
        self.object_border_width_var = tk.StringVar(value="2")
        border_width_entry = ctk.CTkEntry(border_width_frame, textvariable=self.object_border_width_var, width=50)
        border_width_entry.pack(side=tk.LEFT, padx=5)
        
        # Add border toggle
        self.object_border_var = tk.BooleanVar(value=True)
        border_toggle = ctk.CTkCheckBox(
            object_frame,
            text="Show Object Border",
            variable=self.object_border_var
        )
        border_toggle.pack(pady=2, anchor="w", padx=10)
        
        # Object placement buttons
        button_frame = ctk.CTkFrame(object_frame)
        button_frame.pack(pady=5)
        
        add_object_btn = ctk.CTkButton(
            button_frame,
            text="Add Object to Selected Panels",
            command=self.add_wall_object
        )
        add_object_btn.pack(side=tk.LEFT, padx=5)
        
        remove_objects_btn = ctk.CTkButton(
            button_frame,
            text="Remove All Objects",
            command=self.remove_all_objects
        )
        remove_objects_btn.pack(side=tk.LEFT, padx=5)

        # Add this after your height dimension inputs in the object frame

        # In your add_selection_frame method, modify the vertical position slider setup:

        # Replace the vertical position slider with feet, inches, and fraction inputs
        vertical_pos_frame = ctk.CTkFrame(object_frame)
        vertical_pos_frame.pack(pady=5, fill=tk.X)

        ctk.CTkLabel(vertical_pos_frame, text="Position:").pack(side=tk.LEFT, padx=5)

        # Feet input
        self.object_y_feet_var = tk.StringVar(value="0")
        feet_entry = ctk.CTkEntry(vertical_pos_frame, textvariable=self.object_y_feet_var, width=40)
        feet_entry.pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(vertical_pos_frame, text="feet").pack(side=tk.LEFT)

        # Inches input
        self.object_y_inches_var = tk.StringVar(value="0")
        inches_entry = ctk.CTkEntry(vertical_pos_frame, textvariable=self.object_y_inches_var, width=40)
        inches_entry.pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(vertical_pos_frame, text="inches").pack(side=tk.LEFT)

        # Fraction dropdown
        ctk.CTkLabel(vertical_pos_frame, text="+").pack(side=tk.LEFT, padx=2)
        self.object_y_fraction_var = tk.StringVar(value="0")
        fraction_dropdown = ctk.CTkOptionMenu(
            vertical_pos_frame, 
            variable=self.object_y_fraction_var,
            values=fraction_options,  # Use the same fraction options defined elsewhere
            width=70
        )
        fraction_dropdown.pack(side=tk.LEFT, padx=2)


        # After the vertical_pos_frame, add alignment options
        alignment_frame = ctk.CTkFrame(object_frame)
        alignment_frame.pack(pady=2, fill=tk.X)
        
        ctk.CTkLabel(alignment_frame, text="Alignment:").pack(side=tk.LEFT, padx=5)
        
        self.object_alignment_var = tk.StringVar(value="Center")
        alignment_options = ["Center", "Left Edge", "Right Edge"]
        alignment_dropdown = ctk.CTkOptionMenu(
            alignment_frame,
            variable=self.object_alignment_var,
            values=alignment_options,
            width=150
        )
        alignment_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Info button
        info_button = ctk.CTkButton(
            alignment_frame,
            text="?",
            width=25,
            command=self.show_alignment_info
        )
        info_button.pack(side=tk.LEFT, padx=5)
    def add_panel_selection_system(self):
        """Add panel selection and object placement functionality"""
        # Initialize properties for panel selection
        self.selected_panels = []  # List of selected panel IDs
        self.wall_objects = []     # List of WallObject instances
        self.next_object_id = 1    # ID counter for wall objects
        self.selection_mode = False  # If True, clicks will select panels
        
        # Add panel selection frame
        self.add_selection_frame()
        
        # Bind mouse events for panel selection
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        
    def choose_object_border_color(self):
        """Open color picker for the object border11"""
        color = colorchooser.askcolor(color=self.object_border_color_preview["background"], title="Choose Object Border Color")
        if color[1]:  # color is ((R, G, B), hex_color)
            self.object_border_color_preview.configure(bg=color[1])
            

    
    def draw_dimension_line(self, x1, y1, x2, y2, dimension: Dimension, fraction: str = "0", offset=20, side="top"):
        """Draw a dimension line with arrows and text in feet, inches, and fractions format"""
        # Calculate angle and offset points
        angle = math.atan2(y2 - y1, x2 - x1)
        dx = offset * math.sin(angle)
        dy = offset * math.cos(angle)
        
        ox1, oy1 = x1 + dx, y1 - dy
        ox2, oy2 = x2 + dx, y2 - dy
        
        # Extension lines
        self.canvas.create_line(x1, y1, ox1, oy1, fill="black", dash=(2, 2))
        self.canvas.create_line(x2, y2, ox2, oy2, fill="black", dash=(2, 2))
        
        # Dimension line with arrows
        self.canvas.create_line(ox1, oy1, ox2, oy2, fill="black", arrow="both")
        
        # Format dimension text
        if dimension is None:
            text = "0"
        else:
            text = self.format_dimension(dimension, fraction)
        
        # Position text based on side parameter
        text_x = (ox1 + ox2) / 2
        text_y = (oy1 + oy2) / 2
        
        if side == "top":
            text_y -= 10
            anchor = "s"
        elif side == "bottom":
            text_y += 10
            anchor = "n"
        elif side == "left":
            text_x -= 10
            anchor = "e"
        else:  # right
            text_x += 10
            anchor = "w"
        
        self.canvas.create_text(text_x, text_y, text=text, anchor=anchor)

    def draw_wall(self, panels: List[Panel]):
        """Draw wall with panels and baseboard if enabled"""
        self.canvas.delete("all")
        
        # Add debug output to track baseboard state at drawing time
        print(f"DRAW_WALL: baseboard_enabled={self.baseboard_var.get()}, use_baseboard={self.use_baseboard}")
        
        # Calculate scaling factors
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        margin = 100
        
        # Calculate total inches for wall dimensions including fractions
        wall_width_inches = self.convert_to_inches(
            self.wall_dimensions["width"].feet,
            self.wall_dimensions["width"].inches,
            self.wall_dimensions.get("width_fraction", "0")
        )
        
        wall_height_inches = self.convert_to_inches(
            self.wall_dimensions["height"].feet,
            self.wall_dimensions["height"].inches,
            self.wall_dimensions.get("height_fraction", "0")
        )
        
        # Calculate usable height for visual representation
        visual_wall_height = wall_height_inches
        visual_usable_height = wall_height_inches
        
        # Calculate baseboard height including fraction
        baseboard_height_inches = self.baseboard_height
        if hasattr(self, 'baseboard_fraction_var'):
            baseboard_height_inches += self.fraction_to_decimal(self.baseboard_fraction_var.get())
            
        # CRITICAL: Direct check of baseboard_var state, not instance variable
        use_baseboard = self.baseboard_var.get()
        
        if use_baseboard:
            visual_usable_height -= baseboard_height_inches
        
        # Calculate aspect ratio and scaling
        wall_aspect_ratio = wall_width_inches / wall_height_inches
        canvas_aspect_ratio = (canvas_width - 2 * margin) / (canvas_height - 2 * margin)
        
        if wall_aspect_ratio > canvas_aspect_ratio:
            scale = (canvas_width - 2 * margin) / wall_width_inches
        else:
            scale = (canvas_height - 2 * margin) / wall_height_inches
        
        scale *= 0.8
        
        scaled_width = wall_width_inches * scale
        scaled_height = wall_height_inches * scale
        
        # Calculate baseboard height if used
        baseboard_height = baseboard_height_inches * scale if use_baseboard else 0
        
        x_offset = (canvas_width - scaled_width) / 2
        y_offset = (canvas_height - scaled_height) / 2

        # Draw wall outline
        self.canvas.create_rectangle(
            x_offset, y_offset,
            x_offset + scaled_width,
            y_offset + scaled_height,
            outline="black", width=2
        )

        # Sort panels by x position to ensure proper drawing order
        sorted_panels = sorted(panels, key=lambda p: p.x)
        
        # Fix any overlapping panels
        fixed_panels = []
        current_x_percent = 0
        
        for panel in sorted_panels:
            # Create a corrected panel that doesn't overlap
            # Include floor_mounted and height_offset properties
            fixed_panel = Panel(
                id=panel.id,
                x=current_x_percent,
                width=panel.width,
                actual_width=panel.actual_width,
                actual_width_fraction=panel.actual_width_fraction,
                height=panel.height,
                height_fraction=panel.height_fraction,
                color=panel.color,
                border_color=panel.border_color,
                floor_mounted=panel.floor_mounted if hasattr(panel, 'floor_mounted') else True,
                height_offset=panel.height_offset if hasattr(panel, 'height_offset') else None,
                height_offset_fraction=panel.height_offset_fraction if hasattr(panel, 'height_offset_fraction') else "0"
            )
            fixed_panels.append(fixed_panel)
            current_x_percent += panel.width  # Update for next panel
        
        # CRITICAL: Draw baseboard BEFORE panels to ensure panels are on top
        # Draw baseboard if enabled - directly check baseboard_var
        if use_baseboard:
            print(f"  Drawing baseboard: height={baseboard_height_inches} inches, {baseboard_height} pixels")
            self.canvas.create_rectangle(
                x_offset,
                y_offset + scaled_height - baseboard_height,
                x_offset + scaled_width,
                y_offset + scaled_height,
                fill="gray",
                outline="black",  # Add outline for better visibility
                width=1,
                tags=["baseboard"]  # Add a tag for identification
            )
        
        # Now draw the fixed panels
        for panel in fixed_panels:
            panel_x = x_offset + (panel.x / 100 * scaled_width)
            panel_width = (panel.width / 100 * scaled_width)
            
            # Calculate constrained panel height for visualization
            panel_height_inches = self.convert_to_inches(
                panel.height.feet, 
                panel.height.inches, 
                panel.height_fraction
            )
            visual_panel_height = min(panel_height_inches, visual_usable_height) * scale
            
            # Calculate panel y position based on floor mounting
            floor_mounted = True
            if hasattr(panel, 'floor_mounted'):
                floor_mounted = panel.floor_mounted
                
            if floor_mounted:
                # Floor mounted panels start from bottom (minus baseboard if used)
                if use_baseboard:
                    panel_bottom = y_offset + scaled_height - baseboard_height
                else:
                    panel_bottom = y_offset + scaled_height
            else:
                # Calculate height offset in inches
                height_offset_inches = 0
                if hasattr(panel, 'height_offset') and panel.height_offset:
                    height_offset_inches = self.convert_to_inches(
                        panel.height_offset.feet,
                        panel.height_offset.inches,
                        panel.height_offset_fraction
                    )
                
                # For non-floor mounted panels, position from bottom with offset
                height_offset_scaled = height_offset_inches * scale
                
                # Calculate bottom position considering offset from floor
                panel_bottom = y_offset + scaled_height - height_offset_scaled
                
                # If there's a baseboard, make sure the panel is above it
                if use_baseboard:
                    min_bottom = y_offset + scaled_height - baseboard_height
                    panel_bottom = min(panel_bottom, min_bottom)
                
            panel_top = panel_bottom - visual_panel_height
            
            # Draw panel
            self.canvas.create_rectangle(
                panel_x,
                panel_top,
                panel_x + panel_width,
                panel_bottom,
                fill=panel.color,
                outline=panel.border_color,
                width=1
            )

        # Draw vertical lines between panels using fixed panel positions
        for panel in fixed_panels:
            panel_x = x_offset + (panel.x / 100 * scaled_width)
            if panel.x > 0:  # Don't draw at left edge of wall
                self.canvas.create_line(
                    panel_x, y_offset,
                    panel_x, y_offset + scaled_height,
                    fill=panel.border_color,  
                    width=1,
                    dash=(4, 4)
                )
            
        # Draw custom name for panels
        custom_name = self.custom_name_var.get()
        for panel in fixed_panels:
            panel_x = x_offset + (panel.x / 100 * scaled_width)
            panel_width = (panel.width / 100 * scaled_width)
            
            # Calculate constrained panel height for visualization
            panel_height_inches = self.convert_to_inches(
                panel.height.feet, 
                panel.height.inches, 
                panel.height_fraction
            )
            visual_panel_height = min(panel_height_inches, visual_usable_height) * scale
            
            # Calculate panel y position based on floor mounting
            floor_mounted = True
            if hasattr(panel, 'floor_mounted'):
                floor_mounted = panel.floor_mounted
                
            if floor_mounted:
                # Floor mounted panels start from bottom (minus baseboard if used)
                if use_baseboard:
                    panel_bottom = y_offset + scaled_height - baseboard_height
                else:
                    panel_bottom = y_offset + scaled_height
            else:
                # Calculate height offset in inches
                height_offset_inches = 0
                if hasattr(panel, 'height_offset') and panel.height_offset:
                    height_offset_inches = self.convert_to_inches(
                        panel.height_offset.feet,
                        panel.height_offset.inches,
                        panel.height_offset_fraction
                    )
                
                # For non-floor mounted panels, position from bottom with offset
                height_offset_scaled = height_offset_inches * scale
                
                # Calculate bottom position considering offset from floor
                panel_bottom = y_offset + scaled_height - height_offset_scaled
                
                # If there's a baseboard, make sure the panel is above it
                if use_baseboard:
                    min_bottom = y_offset + scaled_height - baseboard_height
                    panel_bottom = min(panel_bottom, min_bottom)
                
            panel_top = panel_bottom - visual_panel_height

            # Display custom name at the center of the panel
            text_x = panel_x + panel_width / 2
            text_y = panel_top + visual_panel_height / 2
            self.canvas.create_text(
                text_x,
                text_y,
                text=custom_name,
                fill="black",
                font=("Arial", 8, "bold"),
                anchor="center"
            )
        
        # Highlight selected panels (using the original panel IDs but fixed positions)
        if hasattr(self, 'selected_panels') and self.selected_panels:
            for panel_id in self.selected_panels:
                for panel in fixed_panels:  # Use fixed panels for display
                    if panel.id == panel_id:
                        panel_x = x_offset + (panel.x / 100 * scaled_width)
                        panel_width = (panel.width / 100 * scaled_width)
                        
                        # Calculate panel height for visualization
                        panel_height_inches = self.convert_to_inches(
                            panel.height.feet, 
                            panel.height.inches, 
                            panel.height_fraction
                        )
                        visual_panel_height = min(panel_height_inches, visual_usable_height) * scale
                        
                        # Calculate panel y position based on floor mounting
                        floor_mounted = True
                        if hasattr(panel, 'floor_mounted'):
                            floor_mounted = panel.floor_mounted
                            
                        if floor_mounted:
                            # Floor mounted panels start from bottom (minus baseboard if used)
                            if use_baseboard:
                                panel_bottom = y_offset + scaled_height - baseboard_height
                            else:
                                panel_bottom = y_offset + scaled_height
                        else:
                            # Calculate height offset in inches
                            height_offset_inches = 0
                            if hasattr(panel, 'height_offset') and panel.height_offset:
                                height_offset_inches = self.convert_to_inches(
                                    panel.height_offset.feet,
                                    panel.height_offset.inches,
                                    panel.height_offset_fraction
                                )
                            
                            # For non-floor mounted panels, position from bottom with offset
                            height_offset_scaled = height_offset_inches * scale
                            
                            # Calculate bottom position considering offset from floor
                            panel_bottom = y_offset + scaled_height - height_offset_scaled
                            
                            # If there's a baseboard, make sure the panel is above it
                            if use_baseboard:
                                min_bottom = y_offset + scaled_height - baseboard_height
                                panel_bottom = min(panel_bottom, min_bottom)
                            
                        panel_top = panel_bottom - visual_panel_height
                        
                        # Draw selection border
                        self.canvas.create_rectangle(
                            panel_x, panel_top,
                            panel_x + panel_width, panel_bottom,
                            outline="blue",
                            width=3,
                            dash=(5, 3)
                        )

        # Draw wall objects
        if hasattr(self, 'wall_objects') and self.wall_objects:
            self.draw_wall_objects(
                canvas_width, canvas_height,
                x_offset, y_offset,
                scaled_width, scaled_height,
                scale, baseboard_height
            )
        
        # Only draw dimensions if show_dimensions_var is True
        if self.show_dimensions_var.get():
            # Draw wall width dimension at top
            self.draw_dimension_line(
                x_offset, y_offset - 40,
                x_offset + scaled_width, y_offset - 40,
                self.wall_dimensions["width"],
                self.wall_dimensions.get("width_fraction", "0"),
                offset=30
            )
            
            # Draw wall height dimension on left side
            self.draw_dimension_line(
                x_offset - 40, y_offset,
                x_offset - 40, y_offset + scaled_height,
                self.wall_dimensions["height"],
                self.wall_dimensions.get("height_fraction", "0"),
                offset=30,
                side="left"
            )

            # Draw panel height dimension on right side
            if fixed_panels:
                # For the first panel, show its height dimension
                panel = fixed_panels[0]
                
                # Calculate panel y position based on floor mounting
                floor_mounted = True
                if hasattr(panel, 'floor_mounted'):
                    floor_mounted = panel.floor_mounted
                    
                if floor_mounted:
                    # Floor mounted panels start from bottom (minus baseboard if used)
                    if use_baseboard:
                        panel_bottom = y_offset + scaled_height - baseboard_height
                    else:
                        panel_bottom = y_offset + scaled_height
                else:
                    # Calculate height offset in inches
                    height_offset_inches = 0
                    if hasattr(panel, 'height_offset') and panel.height_offset:
                        height_offset_inches = self.convert_to_inches(
                            panel.height_offset.feet,
                            panel.height_offset.inches,
                            panel.height_offset_fraction
                        )
                    
                    # For non-floor mounted panels, position from bottom with offset
                    height_offset_scaled = height_offset_inches * scale
                    
                    # Calculate bottom position considering offset from floor
                    panel_bottom = y_offset + scaled_height - height_offset_scaled
                    
                    # If there's a baseboard, make sure the panel is above it
                    if use_baseboard:
                        min_bottom = y_offset + scaled_height - baseboard_height
                        panel_bottom = min(panel_bottom, min_bottom)
                    
                # Calculate panel height for visualization
                panel_height_inches = self.convert_to_inches(
                    panel.height.feet, 
                    panel.height.inches, 
                    panel.height_fraction
                )
                visual_panel_height = min(panel_height_inches, visual_usable_height) * scale
                panel_top = panel_bottom - visual_panel_height
                
                # Draw height dimension
                self.draw_dimension_line(
                    x_offset + scaled_width + 40, 
                    panel_bottom,
                    x_offset + scaled_width + 40, 
                    panel_top,
                    panel.height,
                    panel.height_fraction,
                    offset=30,
                    side="right"
                )

            # Draw panel width dimensions
            for panel in fixed_panels:
                panel_x = x_offset + (panel.x / 100 * scaled_width)
                panel_width = (panel.width / 100 * scaled_width)
                
                self.draw_dimension_line(
                    panel_x, y_offset - 10,
                    panel_x + panel_width, y_offset - 10,
                    panel.actual_width,
                    panel.actual_width_fraction,
                    offset=20,
                    side="top"
                )

            # Draw baseboard dimension if enabled - use baseboard_var for consistency
            if use_baseboard:
                baseboard_dim, baseboard_frac = self.convert_to_feet_inches_fraction(baseboard_height_inches)
                self.draw_dimension_line(
                    x_offset + scaled_width + 20,
                    y_offset + scaled_height - baseboard_height,
                    x_offset + scaled_width + 20,
                    y_offset + scaled_height,
                    baseboard_dim,
                    baseboard_frac,
                    offset=15,
                    side="right"
                )
                
            # Draw height offset dimension for panels not mounted on floor
            for panel in fixed_panels:
                if hasattr(panel, 'floor_mounted') and not panel.floor_mounted and hasattr(panel, 'height_offset') and panel.height_offset:
                    panel_x = x_offset + (panel.x / 100 * scaled_width)
                    panel_width = (panel.width / 100 * scaled_width)
                    
                    # Calculate height offset in inches
                    height_offset_inches = self.convert_to_inches(
                        panel.height_offset.feet,
                        panel.height_offset.inches,
                        panel.height_offset_fraction
                    )
                    height_offset_scaled = height_offset_inches * scale
                    
                    # Calculate bottom position considering offset from floor
                    panel_bottom = y_offset + scaled_height - height_offset_scaled
                    
                    # If there's a baseboard, the visible floor line may be different
                    floor_line = y_offset + scaled_height
                    
                    # Draw dimension line for height offset from floor
                    self.draw_dimension_line(
                        panel_x - 20,
                        panel_bottom,
                        panel_x - 20,
                        floor_line,
                        panel.height_offset,
                        panel.height_offset_fraction,
                        offset=15,
                        side="left"
                    )

    def refresh_summary(self):
        """Refresh the summary and switch to the summary tab"""
        # Set a flag that we're requesting a refresh with tab switch
        self.summary_refresh_requested = True
        
        # Call calculate to update panels and summary
        self.calculate()
        
        # Switch to the summary tab
        if hasattr(self, 'tab_view'):
            self.tab_view.set("Summary")

    # Modify the create_summary_controls method to use refresh_summary instead of calculate
    def create_summary_controls(self, parent):
        """Create controls for the Summary tab"""
        # Create a frame for actions/settings related to summary
        control_frame = ctk.CTkFrame(parent)
        control_frame.pack(fill=tk.X, padx=10, pady=(0, 10), before=self.summary_text)
        
        # Add refresh button that uses the new refresh_summary method
        refresh_btn = ctk.CTkButton(
            control_frame,
            text="Refresh Summary",
            command=self.refresh_summary,  # Use the new method
            fg_color="#1E88E5",
            hover_color="#1565C0"
        )
        refresh_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Add copy to clipboard button
        copy_btn = ctk.CTkButton(
            control_frame,
            text="Copy to Clipboard",
            command=self.copy_summary_to_clipboard,
            fg_color="#757575",
            hover_color="#616161"
        )
        copy_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Add print summary button
        print_btn = ctk.CTkButton(
            control_frame,
            text="Print Summary",
            command=self.print_summary,
            fg_color="#009688",
            hover_color="#00796B"
        )
        print_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Add heading above the summary text
        heading_label = ctk.CTkLabel(
            parent,
            text="Panel Summary",
            font=("Arial", 16, "bold")
        )
        heading_label.pack(before=self.summary_text, pady=(0, 5))
        
        # Add formatting options
        format_frame = ctk.CTkFrame(parent)
        format_frame.pack(fill=tk.X, padx=10, pady=(0, 10), before=self.summary_text)
        
        ctk.CTkLabel(format_frame, text="Format:").pack(side=tk.LEFT, padx=5)
        
        # Format options dropdown
        self.summary_format_var = tk.StringVar(value="Standard")
        format_dropdown = ctk.CTkOptionMenu(
            format_frame,
            variable=self.summary_format_var,
            values=["Standard", "Detailed", "Compact"],
            command=self.change_summary_format
        )
        format_dropdown.pack(side=tk.LEFT, padx=5)

    def print_summary(self):
        """Print the summary text"""
        try:
            import tempfile
            import os
            import webbrowser
            
            # Create a temporary HTML file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w') as f:
                temp_path = f.name
                
                # Write HTML content
                f.write("<html><head>")
                f.write("<title>Wall Panel Summary</title>")
                f.write("<style>")
                f.write("body { font-family: Arial, sans-serif; margin: 20px; }")
                f.write("h1 { color: #333; }")
                f.write("pre { background-color: #f5f5f5; padding: 10px; border-radius: 5px; }")
                f.write("@media print { body { margin: 0.5in; } }")
                f.write("</style></head><body>")
                
                # Get summary content
                summary_content = self.summary_text.get("1.0", tk.END)
                
                # Add content to HTML
                f.write("<h1>Wall Panel Summary</h1>")
                f.write("<pre>" + summary_content + "</pre>")
                
                # Add footer
                from datetime import datetime
                current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                f.write(f"<p><small>Generated on {current_date}</small></p>")
                
                f.write("</body></html>")
            
            # Open the temporary file in the default browser for printing
            webbrowser.open('file://' + temp_path)
            
            # Show a confirmation message
            success_label = ctk.CTkLabel(
                self.summary_frame,
                text="Summary opened for printing!",
                fg_color="#4CAF50",
                text_color="white",
                corner_radius=8,
                padx=10, 
                pady=5
            )
            success_label.pack(pady=10)
            
            # Auto-hide the success message after 2 seconds
            self.after(2000, success_label.destroy)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to print summary: {str(e)}")

    def change_summary_format(self, format_type):
        """Change the format of the summary display"""
        # Store current summary content
        summary_content = self.summary_text.get("1.0", tk.END)
        
        # Re-format based on the selected format type
        if format_type == "Compact":
            # Create a compact version without blank lines and with shorter labels
            lines = summary_content.strip().split('\n')
            compact_lines = []
            
            for line in lines:
                if line.strip():  # Skip empty lines
                    # Shorten labels
                    line = line.replace("Wall dimensions: ", "Wall: ")
                    line = line.replace("Baseboard height: ", "Baseboard: ")
                    line = line.replace("Usable height: ", "Usable: ")
                    line = line.replace("Number of panels: ", "Panels: ")
                    line = line.replace("Panel color: ", "Color: ")
                    line = line.replace("  Width: ", "W: ")
                    line = line.replace("  Height: ", "H: ")
                    line = line.replace("  Position: ", "Pos: ")
                    
                    compact_lines.append(line)
            
            # Update summary text
            self.summary_text.delete("1.0", tk.END)
            self.summary_text.insert("1.0", "\n".join(compact_lines))
            
        elif format_type == "Detailed":
            # Re-calculate to get a more detailed summary
            # First store original format
            original_format = self.summary_format_var.get()
            
            # We'll add more detail by recalculating with extra info
            panels = self.calculate_panels()
            
            # Create a more detailed summary
            detailed_summary = []
            
            # Add the current wall name to the summary
            current_wall = self.get_current_wall()
            if current_wall:
                detailed_summary.append(f"Wall: {current_wall.name}")
            
            # Add detailed wall dimensions 
            wall_w_inches = self.convert_to_inches(
                self.wall_dimensions['width'].feet,
                self.wall_dimensions['width'].inches,
                self.wall_dimensions.get('width_fraction', '0')
            )
            wall_h_inches = self.convert_to_inches(
                self.wall_dimensions['height'].feet,
                self.wall_dimensions['height'].inches,
                self.wall_dimensions.get('height_fraction', '0')
            )
            
            detailed_summary.append(f"Wall dimensions: {self.format_dimension(self.wall_dimensions['width'], self.wall_dimensions.get('width_fraction', '0'))} × "
                           f"{self.format_dimension(self.wall_dimensions['height'], self.wall_dimensions.get('height_fraction', '0'))}")
            detailed_summary.append(f"Wall area: {(wall_w_inches * wall_h_inches / 144):.2f} sq ft")
            
            # Add more detail about each panel
            detailed_summary.append(f"\nNumber of panels: {len(panels)}")
            detailed_summary.append(f"Panel color: {self.panel_color}")
            detailed_summary.append(f"Panel border color: {self.panel_border_color}")
            
            total_panel_area = 0
            
            for i, panel in enumerate(panels, 1):
                # Calculate panel dimensions in inches
                panel_width_inches = self.convert_to_inches(
                    panel.actual_width.feet,
                    panel.actual_width.inches,
                    panel.actual_width_fraction
                )
                
                panel_height_inches = self.convert_to_inches(
                    panel.height.feet,
                    panel.height.inches,
                    panel.height_fraction
                )
                
                # Calculate panel area in square feet
                panel_area = (panel_width_inches * panel_height_inches) / 144  # Convert to sq ft
                total_panel_area += panel_area
                
                detailed_summary.append(f"\nPanel {i}:")
                detailed_summary.append(f"  Width: {self.format_dimension(panel.actual_width, panel.actual_width_fraction)} ({panel_width_inches:.2f} inches)")
                detailed_summary.append(f"  Height: {self.format_dimension(panel.height, panel.height_fraction)} ({panel_height_inches:.2f} inches)")
                detailed_summary.append(f"  Position: {panel.x:.1f}% from left")
                detailed_summary.append(f"  Area: {panel_area:.2f} sq ft")
            
            # Add total panel area
            detailed_summary.append(f"\nTotal panel area: {total_panel_area:.2f} sq ft")
            
            # Add information about wall objects if present
            if hasattr(self, 'wall_objects') and self.wall_objects:
                detailed_summary.append(f"\nWall Objects: {len(self.wall_objects)}")
                for i, obj in enumerate(self.wall_objects, 1):
                    detailed_summary.append(f"\nObject {i}: {obj.name}")
                    detailed_summary.append(f"  Width: {self.format_dimension(obj.width, obj.width_fraction)}")
                    detailed_summary.append(f"  Height: {self.format_dimension(obj.height, obj.height_fraction)}")
                    detailed_summary.append(f"  Position: {obj.x_position:.1f}% from left, {obj.y_position:.1f}% from top")
                    
                    # Add affected panels
                    if hasattr(obj, 'affected_panels') and obj.affected_panels:
                        affected = ", ".join(map(str, obj.affected_panels))
                        detailed_summary.append(f"  Affects panels: {affected}")
            
            # Add timestamp
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            detailed_summary.append(f"\nSummary generated: {current_time}")
            
            # Update summary text
            self.summary_text.delete("1.0", tk.END)
            self.summary_text.insert("1.0", "\n".join(detailed_summary))
            
            # Reset format dropdown to avoid recursive calls
            self.summary_format_var.set(original_format)
            
        else:  # Standard format - use current calculation results
            # Just refresh the summary with standard format
            self.calculate()
                
    # For any calculation actions or wall property changes, wrap them to save the current wall data
    def on_calculate_button_click(self):
        """Handle Calculate button click"""
        # Already implemented in your reset_form button handler
        self.calculate()

        
    def calculate(self):
        """Complete optimized calculate method to prevent excessive recalculations"""
        
        # Prevent recursive calculations
        if self.calculation_in_progress:
            self.pending_calculation = True
            return
        
        # Skip unnecessary calculations during wall switching
        if hasattr(self, 'switching_walls') and self.switching_walls:
            print("Skipping calculation during wall switching")
            return
        
        # Set flag to prevent recursive calls
        self.calculation_in_progress = True
        
        try:
            # COMPLETE CALCULATION LOGIC FROM YOUR ORIGINAL METHOD
            
            # Add debugging
            current_wall = self.get_current_wall()
            if current_wall:
                print(f"Calculating panels for: {current_wall.name} with height {current_wall.dimensions['height'].feet}'{current_wall.dimensions['height'].inches}\"")
            
            # Update dimensions from UI with safe conversion
            wall_width_feet = self.safe_int_conversion(self.wall_width_feet_var.get(), 0)
            wall_width_inches = self.safe_int_conversion(self.wall_width_inches_var.get(), 0)
            wall_width_fraction = self.wall_width_fraction_var.get()
            
            wall_height_feet = self.safe_int_conversion(self.wall_height_feet_var.get(), 0)
            wall_height_inches = self.safe_int_conversion(self.wall_height_inches_var.get(), 0)
            wall_height_fraction = self.wall_height_fraction_var.get()
            
            panel_width_feet = self.safe_int_conversion(self.panel_width_feet_var.get(), 0)
            panel_width_inches = self.safe_int_conversion(self.panel_width_inches_var.get(), 0)
            panel_width_fraction = self.panel_width_fraction_var.get()
            
            panel_height_feet = self.safe_int_conversion(self.panel_height_feet_var.get(), 0)
            panel_height_inches = self.safe_int_conversion(self.panel_height_inches_var.get(), 0)
            panel_height_fraction = self.panel_height_fraction_var.get()
            
            # CRITICAL FIX: Validate before updating dimensions
            if (wall_width_feet > 0 or wall_width_inches > 0) and (wall_height_feet > 0 or wall_height_inches > 0):
                self.wall_dimensions = {
                    "width": Dimension(wall_width_feet, wall_width_inches),
                    "width_fraction": wall_width_fraction,
                    "height": Dimension(wall_height_feet, wall_height_inches),
                    "height_fraction": wall_height_fraction
                }
                
                self.panel_dimensions = {
                    "width": Dimension(panel_width_feet, panel_width_inches),
                    "width_fraction": panel_width_fraction,
                    "height": Dimension(panel_height_feet, panel_height_inches),
                    "height_fraction": panel_height_fraction
                }
            else:
                print(f"CALC: Skipping dimension update - invalid values")
                return  # Don't proceed with invalid dimensions
            
            # Update other variables
            self.use_equal_panels = self.equal_panels_var.get()
            self.panel_count = max(1, self.safe_int_conversion(self.panel_count_var.get(), 2))
            self.use_baseboard = self.baseboard_var.get()
            self.baseboard_height = self.safe_int_conversion(self.baseboard_height_var.get(), 4)
            self.baseboard_fraction = self.baseboard_fraction_var.get() if hasattr(self, 'baseboard_fraction_var') else "0"
            floor_mounted = self.floor_mounted_var.get()
            height_offset_feet = self.safe_int_conversion(self.height_offset_feet_var.get(), 0)
            height_offset_inches = self.safe_int_conversion(self.height_offset_inches_var.get(), 0)
            height_offset_fraction = self.height_offset_fraction_var.get()

            height_offset_dim = Dimension(height_offset_feet, height_offset_inches)
            
            # Calculate wall dimensions in inches with fractions
            wall_width_inches_total = self.convert_to_inches(
                wall_width_feet,
                wall_width_inches,
                wall_width_fraction
            )
            
            wall_height_inches_total = self.convert_to_inches(
                wall_height_feet,
                wall_height_inches,
                wall_height_fraction
            )

            if wall_width_inches_total <= 0 or wall_height_inches_total <= 0:
                return

            # Calculate baseboard height with fraction
            baseboard_inches_total = self.baseboard_height
            if hasattr(self, 'baseboard_fraction_var'):
                baseboard_inches_total += self.fraction_to_decimal(self.baseboard_fraction_var.get())

            # Calculate usable height
            usable_height_inches = wall_height_inches_total - (baseboard_inches_total if self.use_baseboard else 0)
            if usable_height_inches <= 0:
                return

            # Calculate panel height with fraction
            panel_height_inches_total = self.convert_to_inches(
                panel_height_feet,
                panel_height_inches,
                panel_height_fraction
            )
            
            panel_height_inches_total = min(panel_height_inches_total, usable_height_inches)
            panel_height_dim, panel_height_frac = self.convert_to_feet_inches_fraction(panel_height_inches_total)

            # Initialize panels as an empty list
            panels = []
            
            # Check if we have custom widths that should override everything else
            use_custom_panels = False
            if hasattr(self, 'custom_panel_widths') and self.custom_panel_widths:
                custom_panel_ids = sorted(self.custom_panel_widths.keys())
                if len(custom_panel_ids) > 0 and max(custom_panel_ids) <= 10:
                    total_width = sum(self.custom_panel_widths.values())
                    if total_width > 0 and total_width <= wall_width_inches_total * 1.05:
                        use_custom_panels = True
            
            if use_custom_panels:
                # Use purely custom panels based on stored widths
                print("Using custom panel widths")
                panel_ids = sorted(self.custom_panel_widths.keys())
                
                total_width = sum(self.custom_panel_widths.values())
                scale_factor = 1.0
                if total_width > wall_width_inches_total:
                    scale_factor = wall_width_inches_total / total_width
                    print(f"Scaling panel widths by factor {scale_factor}")
                
                current_x_percent = 0
                for panel_id in panel_ids:
                    panel_width = self.custom_panel_widths[panel_id] * scale_factor
                    panel_width_percent = (panel_width / wall_width_inches_total * 100)
                    panel_dim, panel_frac = self.convert_to_feet_inches_fraction(panel_width)
                    
                    panel = Panel(
                        id=panel_id,
                        x=current_x_percent,
                        width=panel_width_percent,
                        actual_width=panel_dim, 
                        actual_width_fraction=panel_frac,
                        height=panel_height_dim,
                        height_fraction=panel_height_frac,
                        color=self.panel_color,
                        border_color=self.panel_border_color,
                        floor_mounted=floor_mounted,
                        height_offset=height_offset_dim if not floor_mounted else None,
                        height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                    )
                    panels.append(panel)
                    current_x_percent += panel_width_percent
                    
            # ADD START SEAM LOGIC HERE (if you implemented it)
            elif hasattr(self, 'use_start_seam_var') and self.use_start_seam_var.get():
                # Use start seam positioning
                panels = self.calculate_start_seam_panels(
                    wall_width_inches_total, panel_height_dim, panel_height_frac,
                    floor_mounted, height_offset_dim, height_offset_fraction
                )
                    
            # Center Equal Panels Logic
            elif self.center_panels_var.get():
                center_panel_count = max(1, self.safe_int_conversion(self.center_panel_count_var.get(), 4))
                center_panel_width = 48
                total_center_width = center_panel_count * center_panel_width

                if total_center_width > wall_width_inches_total:
                    messagebox.showerror("Error", "Center panels exceed wall width!")
                    return

                side_panel_width = (wall_width_inches_total - total_center_width) / 2

                # Add left panel if applicable
                if side_panel_width > 0:
                    side_panel_dim, side_panel_frac = self.convert_to_feet_inches_fraction(side_panel_width)
                    panels.append(Panel(
                        id=1,
                        x=0,
                        width=(side_panel_width / wall_width_inches_total * 100),
                        actual_width=side_panel_dim,
                        actual_width_fraction=side_panel_frac,
                        height=panel_height_dim,
                        height_fraction=panel_height_frac,
                        color=self.panel_color,
                        border_color=self.panel_border_color,
                        floor_mounted=floor_mounted,
                        height_offset=height_offset_dim if not floor_mounted else None,
                        height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                    ))

                # Add center panels
                for i in range(center_panel_count):
                    center_panel_dim, center_panel_frac = self.convert_to_feet_inches_fraction(center_panel_width)
                    panels.append(Panel(
                        id=len(panels) + 1,
                        x=(side_panel_width + i * center_panel_width) / wall_width_inches_total * 100,
                        width=(center_panel_width / wall_width_inches_total * 100),
                        actual_width=center_panel_dim,
                        actual_width_fraction=center_panel_frac,
                        height=panel_height_dim,
                        height_fraction=panel_height_frac,
                        color=self.panel_color,
                        border_color=self.panel_border_color,
                        floor_mounted=floor_mounted,
                        height_offset=height_offset_dim if not floor_mounted else None,
                        height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                    ))

                # Add right panel if applicable
                if side_panel_width > 0:
                    side_panel_dim, side_panel_frac = self.convert_to_feet_inches_fraction(side_panel_width)
                    panels.append(Panel(
                        id=len(panels) + 1,
                        x=((wall_width_inches_total - side_panel_width) / wall_width_inches_total * 100),
                        width=(side_panel_width / wall_width_inches_total * 100),
                        actual_width=side_panel_dim,
                        actual_width_fraction=side_panel_frac,
                        height=panel_height_dim,
                        height_fraction=panel_height_frac,
                        color=self.panel_color,
                        border_color=self.panel_border_color,
                        floor_mounted=floor_mounted,
                        height_offset=height_offset_dim if not floor_mounted else None,
                        height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                    ))
                    
            # Equal Panels Logic
            elif self.use_equal_panels:
                base_panel_width = wall_width_inches_total / self.panel_count
                
                current_x = 0
                for i in range(self.panel_count):
                    panel_dim, panel_frac = self.convert_to_feet_inches_fraction(base_panel_width)
                    panels.append(Panel(
                        id=i+1,
                        x=(current_x / wall_width_inches_total * 100),
                        width=(base_panel_width / wall_width_inches_total * 100),
                        actual_width=panel_dim,
                        actual_width_fraction=panel_frac,
                        height=panel_height_dim,
                        height_fraction=panel_height_frac,
                        color=self.panel_color,
                        border_color=self.panel_border_color,
                        floor_mounted=floor_mounted,
                        height_offset=height_offset_dim if not floor_mounted else None,
                        height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                    ))
                    current_x += base_panel_width
                    
            # Fixed Width Panels Logic
            else:
                panel_width_inches_total = self.convert_to_inches(
                    panel_width_feet,
                    panel_width_inches,
                    panel_width_fraction
                )
                
                if panel_width_inches_total <= 0:
                    return

                current_x = 0
                panel_id = 1
                while current_x < wall_width_inches_total:
                    current_panel_width = min(panel_width_inches_total, wall_width_inches_total - current_x)
                    panel_dim, panel_frac = self.convert_to_feet_inches_fraction(current_panel_width)
                    
                    panels.append(Panel(
                        id=panel_id,
                        x=(current_x / wall_width_inches_total * 100),
                        width=(current_panel_width / wall_width_inches_total * 100),
                        actual_width=panel_dim,
                        actual_width_fraction=panel_frac,
                        height=panel_height_dim,
                        height_fraction=panel_height_frac,
                        color=self.panel_color,
                        border_color=self.panel_border_color,
                        floor_mounted=floor_mounted,
                        height_offset=height_offset_dim if not floor_mounted else None,
                        height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                    ))
                    current_x += panel_width_inches_total
                    panel_id += 1
            
            # Process split panels (your existing logic)
            if hasattr(self, 'split_panels') and self.split_panels:
                # Create a mapping of original panels by ID
                panel_map = {p.id: p for p in panels}
                
                # Create the final panel list
                final_panels = []
                processed_ids = set()
                
                # Sort panels by their x position for consistent ordering
                sorted_panels = sorted(panels, key=lambda p: p.x)
                
                for panel in sorted_panels:
                    # Skip if we've already processed this panel
                    if panel.id in processed_ids:
                        continue
                    
                    # Check if this panel is the left side of a split
                    is_left_panel = False
                    split_info = None
                    
                    for orig_id, info in self.split_panels.items():
                        if panel.id == info['left_id']:
                            is_left_panel = True
                            split_info = info
                            break
                    
                    if not is_left_panel:
                        # This is not a split panel's left side, add as-is
                        final_panels.append(panel)
                        processed_ids.add(panel.id)
                        continue
                    
                    # This is a left panel in a split
                    half_width_inches = split_info['half_width']
                    half_dim, half_frac = self.convert_to_feet_inches_fraction(half_width_inches)
                    half_width_percent = (half_width_inches / wall_width_inches_total) * 100
                    
                    # Add left panel
                    left_panel = Panel(
                        id=panel.id,
                        x=panel.x,
                        width=half_width_percent,
                        actual_width=half_dim,
                        actual_width_fraction=half_frac,
                        height=panel.height,
                        height_fraction=panel.height_fraction,
                        color=panel.color,
                        border_color=self.panel_border_color,
                        floor_mounted=floor_mounted,
                        height_offset=height_offset_dim if not floor_mounted else None,
                        height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                    )
                    final_panels.append(left_panel)
                    processed_ids.add(panel.id)
                    
                    # Calculate right panel position
                    right_x_percent = panel.x + half_width_percent
                    right_id = split_info['right_id']
                    
                    # Add right panel
                    right_panel = Panel(
                        id=right_id,
                        x=right_x_percent,
                        width=half_width_percent,
                        actual_width=half_dim,
                        actual_width_fraction=half_frac,
                        height=panel.height,
                        height_fraction=panel.height_fraction,
                        color=panel.color,
                        border_color=self.panel_border_color,
                        floor_mounted=floor_mounted,
                        height_offset=height_offset_dim if not floor_mounted else None,
                        height_offset_fraction=height_offset_fraction if not floor_mounted else "0"
                    )
                    final_panels.append(right_panel)
                    processed_ids.add(right_id)
                
                panels = final_panels

            # Draw the wall with calculated panels
            self.draw_wall_with_annotations(panels) if hasattr(self, 'draw_wall_with_annotations') else self.draw_wall(panels)
            
            # Update summary
            self.update_summary(panels, current_wall)
            
            # Important: Update current wall's panels property
            if current_wall and not hasattr(self, 'recalculating'):
                import copy
                current_wall.panels = copy.deepcopy(panels)
                if hasattr(self, 'wall_dimensions'):
                    current_wall.dimensions = copy.deepcopy(self.wall_dimensions)
                print(f"Updated {current_wall.name} panels: {len(panels)}")
            
        finally:
            # Always reset the flag
            self.calculation_in_progress = False
            
            # If there was a pending calculation request, do it now
            if self.pending_calculation:
                self.pending_calculation = False
                self.after_idle(self.calculate)  # Schedule for next idle time

    def update_summary(self, panels, current_wall):
        """Separated summary update logic"""
        summary = []
        
        # Add the current wall name to the summary
        if current_wall:
            summary.append(f"Wall: {current_wall.name}")
        
        # Add wall dimensions to summary with the dash format
        summary.append(f"Wall dimensions: {self.format_dimension(self.wall_dimensions['width'], self.wall_dimensions.get('width_fraction', '0'))} x "
                      f"{self.format_dimension(self.wall_dimensions['height'], self.wall_dimensions.get('height_fraction', '0'))}")
        
        if self.use_baseboard:
            baseboard_height_inches = self.baseboard_height
            baseboard_fraction = "0"
            
            if hasattr(self, 'baseboard_fraction_var'):
                baseboard_fraction = self.baseboard_fraction_var.get()
                baseboard_height_inches += self.fraction_to_decimal(baseboard_fraction)
                
            baseboard_dim, baseboard_frac = self.convert_to_feet_inches_fraction(baseboard_height_inches)
            summary.append(f"Baseboard height: {self.format_dimension(baseboard_dim, baseboard_frac)}")
            
            usable_height_inches = self.convert_to_inches(
                self.wall_dimensions['height'].feet, 
                self.wall_dimensions['height'].inches,
                self.wall_dimensions.get('height_fraction', '0')
            ) - baseboard_height_inches
            
            usable_height_dim, usable_height_frac = self.convert_to_feet_inches_fraction(usable_height_inches)
            summary.append(f"Usable height: {self.format_dimension(usable_height_dim, usable_height_frac)}")

        summary.append(f"\nNumber of panels: {len(panels)}")
        summary.append(f"Panel color: {self.panel_color}")
        
        for i, panel in enumerate(panels, 1):
            summary.append(f"\nPanel {i}:")
            summary.append(f"  Width: {self.format_dimension(panel.actual_width, panel.actual_width_fraction)}")
            summary.append(f"  Height: {self.format_dimension(panel.height, panel.height_fraction)}")
            summary.append(f"  Position: {panel.x:.1f}% from left")

        # Add information about wall objects if present
        if hasattr(self, 'wall_objects') and self.wall_objects:
            summary.append(f"\nWall Objects: {len(self.wall_objects)}")
            for i, obj in enumerate(self.wall_objects, 1):
                summary.append(f"\nObject {i}: {obj.name}")
                summary.append(f"  Width: {self.format_dimension(obj.width, obj.width_fraction)}")
                summary.append(f"  Height: {self.format_dimension(obj.height, obj.height_fraction)}")
                summary.append(f"  Position: {obj.x_position:.1f}% from left, {obj.y_position:.1f}% from top")

        # Add information about annotations if present
        if hasattr(self, 'annotation_circles') and self.annotation_circles:
            summary.append(f"\nAnnotations: {len(self.annotation_circles)}")

        # Update the summary text widget
        if hasattr(self, 'summary_text') and self.summary_text is not None:
            self.summary_text.delete("1.0", tk.END)
            self.summary_text.insert("1.0", "\n".join(summary))
            
            # Switch to the summary tab if requested
            if hasattr(self, 'tab_view') and hasattr(self, 'tab_summary'):
                if hasattr(self, 'summary_refresh_requested') and self.summary_refresh_requested:
                    self.tab_view.set("Summary")
                    self.summary_refresh_requested = False


if __name__ == "__main__":
    app = WallcoveringCalculatorUI()
    app.mainloop()
