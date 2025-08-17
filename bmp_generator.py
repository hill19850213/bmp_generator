import struct
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Define available patterns at the module level for reusability
PATTERNS = [
    "Solid Color", "RGB Stripes", "Checkerboard", "Vertical Gradient",
    "Horizontal Gradient", "Color Bars", "Grayscale Bars"
]

def _pack_pixel(rgb_tuple: tuple[int, int, int], pixel_order: str) -> bytes:
    """Packs an RGB tuple into bytes based on the specified pixel order."""
    return struct.pack('<BBB', rgb_tuple[2], rgb_tuple[1], rgb_tuple[0]) if pixel_order == "BGR" else struct.pack('<BBB', *rgb_tuple)

def _generate_pixel_rows(width: int, height: int, pattern: str, pattern_options: dict | None = None):
    """
    A generator that yields pixel data row by row.
    This centralizes the image generation logic to be used by both
    file generation and preview generation, avoiding code duplication.
    """
    options = pattern_options or {}
    CHECKER_SIZE = 16

    # --- Patterns that are constant vertically ---
    if pattern not in ["Vertical Gradient", "Checkerboard"]:
        row_data = bytearray()
        # Pre-calculate values for horizontal patterns
        if pattern == "Color Bars":
            colors_rgb = [
                (255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
                (255, 0, 255), (255, 0, 0), (0, 0, 255), (0, 0, 0)
            ]
            bar_width = width / 8
        elif pattern == "RGB Stripes":
            color1 = options.get('color1', (255, 0, 0))
            color2 = options.get('color2', (0, 255, 0))
            color3 = options.get('color3', (0, 0, 255))
            stripe1_end_x = width // 3
            stripe2_end_x = 2 * (width // 3)

        for x in range(width):
            if pattern == "Solid Color": current_color = options.get('color', (0, 0, 0))
            elif pattern == "RGB Stripes":
                if x < stripe1_end_x: current_color = color1
                elif x < stripe2_end_x: current_color = color2
                else: current_color = color3
            elif pattern == "Color Bars": current_color = colors_rgb[min(int(x // bar_width), 7)]
            elif pattern == "Grayscale Bars":
                # Use the same robust bar calculation as Color Bars for edge cases
                bar_width_gray = width / 8
                bar_index = min(int(x // bar_width_gray), 7)
                val = 255 - int(bar_index * (255 / 7))
                current_color = (val, val, val)
            elif pattern == "Horizontal Gradient":
                start_color = options.get('start_color', (0, 0, 0))
                end_color = options.get('end_color', (255, 255, 255))
                ratio = x / (width - 1) if width > 1 else 1.0
                current_color = tuple(int(s * (1 - ratio) + e * ratio) for s, e in zip(start_color, end_color))
            row_data.extend(struct.pack('BBB', *current_color))

        # For vertically constant patterns, yield the same row 'height' times.
        for _ in range(height):
            yield bytes(row_data) # Yield a copy of the row data

    # --- Patterns that change vertically ---
    elif pattern == "Vertical Gradient":
        start_color = options.get('start_color', (0, 0, 0))
        end_color = options.get('end_color', (255, 255, 255))
        for y in range(height):
            ratio = y / (height - 1) if height > 1 else 1.0
            current_color = tuple(int(s * (1 - ratio) + e * ratio) for s, e in zip(start_color, end_color))
            yield struct.pack('BBB', *current_color) * width
    elif pattern == "Checkerboard":
        color1, color2 = options.get('color1', (255, 255, 255)), options.get('color2', (0, 0, 0))
        row1 = b''.join(struct.pack('BBB', *(color1 if (x // CHECKER_SIZE) % 2 == 0 else color2)) for x in range(width))
        row2 = b''.join(struct.pack('BBB', *(color2 if (x // CHECKER_SIZE) % 2 == 0 else color1)) for x in range(width))
        for y in range(height):
            yield row1 if (y // CHECKER_SIZE) % 2 == 0 else row2

def generate_bmp(filename: str, width: int, height: int, pattern: str,
                 pixel_order: str = "BGR", # type: ignore
                 pattern_options: dict | None = None) -> None: # type: ignore
    """
    Generates a 24-bit BMP file with a specified pattern.
    Supported patterns are useful for display testing, such as solid colors,
    gradients, and color bars.
    Pixel data can be written in BGR (standard) or RGB order.

    Args:
        filename: The name of the BMP file to create.
        width: The width of the image in pixels.
        height: The height of the image in pixels.
        pattern: The pattern to generate (e.g., "RGB Stripes", "Color Bars").
        pixel_order: The order of pixel color components. "BGR" or "RGB".
                     Defaults to "BGR".
        pattern_options: A dictionary with pattern-specific options, like custom
                         colors. Defaults to None.

    Returns:
        None. Raises an exception if generation fails.

    Raises:
        ValueError: If width/height are not positive, or pattern/pixel_order
                    is invalid.
        IOError: If there's an error writing the file.
        Exception: For other unexpected errors during generation.
    """
    if not (isinstance(width, int) and width > 0 and
            isinstance(height, int) and height > 0):
        raise ValueError("Width and height must be positive integers.")
    pixel_order = pixel_order.upper()
    if pixel_order not in ["BGR", "RGB"]:
        raise ValueError("Pixel order must be 'BGR' or 'RGB'.")
    if pattern not in PATTERNS:
        raise ValueError(f"Invalid pattern '{pattern}'. Valid patterns are: {', '.join(PATTERNS)}")

    # Ensure pattern_options is a dictionary for safe access
    options = pattern_options or {}

    # BMP constants
    FILE_HEADER_SIZE = 14
    INFO_HEADER_SIZE = 40  # BITMAPINFOHEADER size
    BITS_PER_PIXEL = 24
    bytes_per_pixel = BITS_PER_PIXEL // 8
    row_size_unpadded = width * bytes_per_pixel
    padding = (4 - (row_size_unpadded % 4)) % 4
    row_size_padded = row_size_unpadded + padding
    image_data_size = row_size_padded * height
    file_size = FILE_HEADER_SIZE + INFO_HEADER_SIZE + image_data_size

    try:
        with open(filename, 'wb') as f:
            # --- BMP File Header (14 bytes) ---
            f.write(b'BM')                                  # Signature
            f.write(struct.pack('<L', file_size))           # File size (unsigned long)
            f.write(struct.pack('<H', 0))                   # Reserved (unsigned short)
            f.write(struct.pack('<H', 0))                   # Reserved (unsigned short)
            f.write(struct.pack('<L', FILE_HEADER_SIZE + INFO_HEADER_SIZE)) # Offset to pixel data (unsigned long)

            # --- BMP Info Header (BITMAPINFOHEADER - 40 bytes) ---
            f.write(struct.pack('<L', INFO_HEADER_SIZE))    # Header size (unsigned long)
            f.write(struct.pack('<l', width))               # Image width (signed long)
            f.write(struct.pack('<l', height))              # Image height (signed long, positive for bottom-up)
            f.write(struct.pack('<H', 1))                   # Number of color planes (must be 1) (unsigned short)
            f.write(struct.pack('<H', BITS_PER_PIXEL))      # Bits per pixel (unsigned short)
            f.write(struct.pack('<L', 0))                   # Compression method (0=BI_RGB, no compression) (unsigned long)
            f.write(struct.pack('<L', image_data_size))     # Image size (can be 0 for BI_RGB) (unsigned long)
            f.write(struct.pack('<l', 0))                   # Horizontal resolution (pixels per meter, 0 is common) (signed long)
            f.write(struct.pack('<l', 0))                   # Vertical resolution (pixels per meter, 0 is common) (signed long)
            f.write(struct.pack('<L', 0))                   # Number of colors in palette (0 for 24-bit) (unsigned long)
            f.write(struct.pack('<L', 0))                   # Number of important colors (0 = all important) (unsigned long)

            # --- Pixel Data ---
            padding_bytes = b'\x00' * padding
            # The pixel order for BMP is BGR. If the user wants RGB, we need to swap.
            # Our generator always yields standard RGB, so we handle the swap here.
            for rgb_row in _generate_pixel_rows(width, height, pattern, options):
                if pixel_order == "BGR":
                    bgr_row = bytearray()
                    for p in range(0, len(rgb_row), 3):
                        r, g, b = rgb_row[p:p+3]
                        bgr_row.extend((b, g, r))
                    f.write(bgr_row + padding_bytes)
                else: # RGB
                    f.write(rgb_row + padding_bytes)

    except IOError as e:
        raise IOError(f"Error writing file '{filename}': {e}")
    except Exception as e:
        raise Exception(f"Unexpected error generating BMP file '{filename}': {e}")

def generate_preview_data_for_put(width: int, height: int, pattern: str, pattern_options: dict | None = None) -> str:
    """Generates pixel data in Tcl/Tk's list-of-lists-of-colors format for the .put() method."""
    rows_of_colors = []
    # The generator yields data row by row.
    for row_bytes in _generate_pixel_rows(width, height, pattern, pattern_options):
        # Format each row as a space-separated list of hex colors: #RRGGBB
        # This is a highly efficient way to format the row using a generator expression.
        row_str = " ".join(
            f"#{row_bytes[i]:02x}{row_bytes[i+1]:02x}{row_bytes[i+2]:02x}"
            for i in range(0, len(row_bytes), 3)
        )
        rows_of_colors.append("{" + row_str + "}")
    # Join all rows into a single string, e.g., "{#... #...} {#... #...}"
    return " ".join(rows_of_colors)

def _prompt_for_color(prompt_text: str) -> tuple[int, int, int]:
    """Helper function for CLI to prompt for an RGB color."""
    print(f"--- Enter values for {prompt_text} ---")
    while True:
        try:
            r = int(input("  Enter Red value (0-255): "))
            g = int(input("  Enter Green value (0-255): "))
            b = int(input("  Enter Blue value (0-255): "))
            if not all(0 <= c <= 255 for c in [r, g, b]):
                raise ValueError("Values must be between 0 and 255.")
            return (r, g, b)
        except ValueError as e:
            print(f"Invalid input: {e}. Please try again.")

def main_cli(): # Renamed original main function for command-line usage
    try:
        width_str = input("Enter image width (pixels): ")
        height_str = input("Enter image height (pixels): ")

        width = int(width_str)
        height = int(height_str)

        if width <= 0 or height <= 0: # Basic validation, more in generate_bmp
            print("Error: Width and height must be positive integers.")
            return

        print("\nAvailable patterns:")
        for p in PATTERNS:
            print(f"- {p}")
        pattern_input = input(f"Enter pattern (default: {PATTERNS[0]}): ").strip()
        if not pattern_input:
            pattern_input = PATTERNS[0]
        # Allow for case-insensitive matching
        elif pattern_input.title() in PATTERNS:
            pattern_input = pattern_input.title()
        elif pattern_input not in PATTERNS:
            print(f"Invalid pattern '{pattern_input}'. Using default '{PATTERNS[0]}'.")
            pattern_input = PATTERNS[0]

        pattern_options = {}
        if pattern_input == "Solid Color":
            pattern_options['color'] = _prompt_for_color("Solid Color")
        elif pattern_input == "Checkerboard":
            pattern_options['color1'] = _prompt_for_color("Color 1")
            pattern_options['color2'] = _prompt_for_color("Color 2")
        elif "Gradient" in pattern_input:
            pattern_options['start_color'] = _prompt_for_color("Start Color")
            pattern_options['end_color'] = _prompt_for_color("End Color")
        elif pattern_input == "RGB Stripes":
            pattern_options['color1'] = _prompt_for_color("Stripe 1 Color (R)")
            pattern_options['color2'] = _prompt_for_color("Stripe 2 Color (G)")
            pattern_options['color3'] = _prompt_for_color("Stripe 3 Color (B)")

        pixel_order_input = input("Enter pixel order (BGR or RGB, default BGR): ").strip().upper()
        if not pixel_order_input:
            pixel_order_input = "BGR"
        elif pixel_order_input not in ["BGR", "RGB"]:
            print(f"Invalid pixel order '{pixel_order_input}'. Using default BGR.")
            pixel_order_input = "BGR"

        safe_pattern_name = pattern_input.lower().replace(' ', '_')
        output_filename = f"{safe_pattern_name}_{width}x{height}_{pixel_order_input}.bmp"
        print(f"\nGenerating '{output_filename}'...")
        generate_bmp(output_filename, width, height, pattern_input, pixel_order_input, pattern_options=pattern_options)
        print("Done.")
    except ValueError:
        print("Invalid input. Please enter numbers for width/height, or check pattern/pixel order.")
    except Exception as e:
        print(f"Main program error: {e}")

class ColorInputFrame(ttk.Frame):
    """A reusable frame for entering an RGB color."""
    def __init__(self, parent, label_text: str, default_colors: tuple[int, int, int]):
        super().__init__(parent)
        self.r_var = tk.StringVar(value=str(default_colors[0]))
        self.g_var = tk.StringVar(value=str(default_colors[1]))
        self.b_var = tk.StringVar(value=str(default_colors[2]))

        ttk.Label(self, text=f"{label_text}:").pack(side="left", padx=(0, 5))
        ttk.Label(self, text="R:").pack(side="left")
        ttk.Entry(self, textvariable=self.r_var, width=4).pack(side="left", padx=(0, 5))
        ttk.Label(self, text="G:").pack(side="left")
        ttk.Entry(self, textvariable=self.g_var, width=4).pack(side="left", padx=(0, 5))
        ttk.Label(self, text="B:").pack(side="left")
        ttk.Entry(self, textvariable=self.b_var, width=4).pack(side="left")

class BmpGeneratorApp:
    def __init__(self, master: tk.Tk):
        self.master = master
        master.title("BMP Generator") # BMP Generator
        master.resizable(False, False) # Prevent resizing

        # Configure style for ttk widgets
        style = ttk.Style()
        style.configure("TLabel", padding=5)
        style.configure("TEntry", padding=5)
        style.configure("TButton", padding=5)
        style.configure("TCombobox", padding=5)

        # Main frame for input widgets
        input_frame = ttk.Frame(master, padding="10 10 10 0")
        input_frame.grid(row=0, column=0, sticky="nsew")

        # Width input
        ttk.Label(input_frame, text="Image Width (pixels):").grid(row=0, column=0, sticky="w", pady=2) # Image Width
        self.width_var = tk.StringVar()
        self.width_entry = ttk.Entry(input_frame, textvariable=self.width_var, width=15)
        self.width_entry.grid(row=0, column=1, sticky="ew", pady=2)

        # Height input
        ttk.Label(input_frame, text="Image Height (pixels):").grid(row=1, column=0, sticky="w", pady=2) # Image Height
        self.height_var = tk.StringVar()
        self.height_entry = ttk.Entry(input_frame, textvariable=self.height_var, width=15)
        self.height_entry.grid(row=1, column=1, sticky="ew", pady=2)

        # Pattern selection
        ttk.Label(input_frame, text="Pattern:").grid(row=2, column=0, sticky="w", pady=2)
        self.pattern_var = tk.StringVar(value=PATTERNS[0]) # Default value
        self.pattern_combo = ttk.Combobox(input_frame, textvariable=self.pattern_var, values=PATTERNS, state="readonly", width=20)
        self.pattern_combo.grid(row=2, column=1, sticky="ew", pady=2)

        # --- Container for dynamic pattern options ---
        self.options_container = ttk.Frame(master, padding="10 5 10 10")
        self.options_container.grid(row=1, column=0, sticky="nsew")
        self.option_frames = {}

        # Create option frames for each pattern that needs them
        self.option_frames["Solid Color"] = [
            ColorInputFrame(self.options_container, "Color", (255, 255, 255))
        ]
        self.option_frames["RGB Stripes"] = [
            ColorInputFrame(self.options_container, "Stripe 1", (255, 0, 0)),
            ColorInputFrame(self.options_container, "Stripe 2", (0, 255, 0)),
            ColorInputFrame(self.options_container, "Stripe 3", (0, 0, 255))
        ]
        self.option_frames["Checkerboard"] = [
            ColorInputFrame(self.options_container, "Color 1", (255, 255, 255)),
            ColorInputFrame(self.options_container, "Color 2", (0, 0, 0))
        ]
        self.option_frames["Vertical Gradient"] = self.option_frames["Horizontal Gradient"] = [
            ColorInputFrame(self.options_container, "Start", (0, 0, 0)),
            ColorInputFrame(self.options_container, "End", (255, 255, 255))
        ]

        # Pack all frames but hide them initially
        for frames in self.option_frames.values():
            for frame in frames:
                frame.pack(anchor="w", pady=2, fill="x")

        # Pixel order selection
        ttk.Label(input_frame, text="Pixel Order:").grid(row=3, column=0, sticky="w", pady=2) # Pixel Order
        self.pixel_order_var = tk.StringVar(value="BGR") # Default value
        self.pixel_order_combo = ttk.Combobox(input_frame, textvariable=self.pixel_order_var, values=["BGR", "RGB"], state="readonly", width=12)
        self.pixel_order_combo.grid(row=3, column=1, sticky="ew", pady=2)

        # Frame for the generate button
        button_frame = ttk.Frame(master, padding="10 5 10 10") # type: ignore
        button_frame.grid(row=2, column=0, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        # Preview Button
        self.preview_button = ttk.Button(button_frame, text="Preview", command=self.show_preview)
        self.preview_button.grid(row=0, column=0, padx=5, sticky="e")

        # Generate button
        self.generate_button = ttk.Button(button_frame, text="Generate BMP", command=self.trigger_generate_bmp) # Generate BMP
        self.generate_button.grid(row=0, column=1, padx=5, sticky="w")

        # Configure column weights for proper resizing behavior within input_frame
        input_frame.grid_columnconfigure(1, weight=1)

        # Set initial focus to the width entry field
        self.width_entry.focus()
        # Bind event to handle showing/hiding the custom color frame
        self.pattern_combo.bind("<<ComboboxSelected>>", self.on_pattern_change)
        # Initial call to set the correct UI state
        self.on_pattern_change()

    def on_pattern_change(self, event=None):
        """Shows or hides the custom color input fields based on pattern selection."""
        selected_pattern = self.pattern_var.get()
        # Hide all option frames first
        for frames in self.option_frames.values():
            for frame in frames:
                frame.pack_forget()
        # Show the frames for the selected pattern
        if selected_pattern in self.option_frames:
            for frame in self.option_frames[selected_pattern]:
                frame.pack(anchor="w", pady=2, fill="x")

    def _collect_and_validate_inputs(self):
        """Validates all user inputs and collects them into a tuple."""
        try:
            width_str = self.width_var.get()
            height_str = self.height_var.get()
            pattern = self.pattern_var.get()
            pixel_order = self.pixel_order_var.get()
            pattern_options = {}

            if not width_str or not height_str:
                messagebox.showerror("Input Error", "Width and height cannot be empty.")
                return None

            width = int(width_str)
            height = int(height_str)

            if not (width > 0 and height > 0):
                 messagebox.showerror("Input Error", "Width and height must be positive integers.")
                 return None

            # Collect colors from the visible option frames
            if pattern in self.option_frames:
                frames = self.option_frames[pattern]
                color_keys = []
                if pattern == "Solid Color": color_keys = ["color"]
                elif pattern == "Checkerboard": color_keys = ["color1", "color2"]
                elif "Gradient" in pattern: color_keys = ["start_color", "end_color"]
                elif pattern == "RGB Stripes": color_keys = ["color1", "color2", "color3"]

                for i, key in enumerate(color_keys):
                    r = int(frames[i].r_var.get())
                    g = int(frames[i].g_var.get())
                    b = int(frames[i].b_var.get())
                    if not all(0 <= c <= 255 for c in [r, g, b]):
                        messagebox.showerror("Invalid Color", f"Values for '{key}' must be integers between 0 and 255.")
                        return None
                    pattern_options[key] = (r, g, b)

            return width, height, pattern, pixel_order, pattern_options

        except ValueError: # Catches int conversion error
            messagebox.showerror("Invalid Input", "Width, height, and color values must be valid integers.")
            return None

    def show_preview(self):
        """Generates and displays a preview of the selected pattern."""
        inputs = self._collect_and_validate_inputs()
        if not inputs:
            return

        width, height, pattern, _, pattern_options = inputs

        preview_window = tk.Toplevel(self.master)
        preview_window.title(f"Preview: {pattern} ({width}x{height})")
        preview_window.resizable(False, False)

        try:
            # PhotoImage can be slow for large images, so we can cap the preview size
            preview_w, preview_h = min(width, 400), min(height, 300)
            
            # Generate data in the specific format required by the .put() method
            pixel_data_for_put = generate_preview_data_for_put(preview_w, preview_h, pattern, pattern_options)
            
            # Keep a reference to the image to prevent garbage collection
            # Create a blank image and then 'put' the data onto it. This is more robust than PPM.
            self.preview_image = tk.PhotoImage(width=preview_w, height=preview_h)
            self.preview_image.put(pixel_data_for_put)

            preview_label = ttk.Label(preview_window, image=self.preview_image)
            preview_label.pack()

        except Exception as e:
            preview_window.destroy()
            messagebox.showerror("Preview Error", f"Could not generate preview:\n{e}")

    def trigger_generate_bmp(self):
        """Handles the 'Generate BMP' button click event."""
        inputs = self._collect_and_validate_inputs()
        if not inputs:
            return

        width, height, pattern, pixel_order, pattern_options = inputs

        safe_pattern_name = pattern.lower().replace(' ', '_')
        suggested_filename = f"{safe_pattern_name}_{width}x{height}_{pixel_order}.bmp"
        output_filename = filedialog.asksaveasfilename(
            defaultextension=".bmp",
            filetypes=[("BMP files", "*.bmp"), ("All files", "*.*")],
            title="Save BMP File", # Save BMP File
            initialfile=suggested_filename
        )

        if not output_filename: # User cancelled the save dialog
            return

        try:
            generate_bmp(
                output_filename, width, height, pattern, pixel_order, pattern_options
            )
            success_message = f"BMP file '{output_filename}' generated successfully.\n(Pattern: {pattern}, {width}x{height}, {pixel_order})"
            messagebox.showinfo("Success", success_message)
        except (ValueError, IOError) as e: # Catch specific errors from generate_bmp
            messagebox.showerror("Generation Error", str(e)) # Generation Error
        except Exception as e: # Catch any other unexpected errors
            messagebox.showerror("Unexpected Error", f"An unexpected error occurred...\n{e}") # Unexpected Error: An unexpected error occurred...

def main_gui():
    """Initializes and runs the Tkinter GUI application."""
    root = tk.Tk()
    app = BmpGeneratorApp(root)
    root.mainloop()

if __name__ == "__main__":
    # main_cli() # Uncomment to run the command-line interface version
    main_gui()   # Run the graphical user interface version
