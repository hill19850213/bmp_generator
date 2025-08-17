import struct
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Define available patterns at the module level for reusability
PATTERNS = [
    "RGB Stripes", "Color Bars", "Vertical Gradient", "Horizontal Gradient",
    "Solid Red", "Solid Green", "Solid Blue", "Solid White", "Solid Black"
]

SOLID_COLORS = {
    "Solid Red": (255, 0, 0),
    "Solid Green": (0, 255, 0),
    "Solid Blue": (0, 0, 255),
    "Solid White": (255, 255, 255),
    "Solid Black": (0, 0, 0),
}

def _pack_pixel(rgb_tuple: tuple[int, int, int], pixel_order: str) -> bytes:
    """Packs an RGB tuple into bytes based on the specified pixel order."""
    return struct.pack('<BBB', rgb_tuple[2], rgb_tuple[1], rgb_tuple[0]) if pixel_order == "BGR" else struct.pack('<BBB', *rgb_tuple)

def generate_bmp(filename: str, width: int, height: int, pattern: str, pixel_order: str = "BGR") -> None:
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

    # BMP constants
    FILE_HEADER_SIZE = 14
    INFO_HEADER_SIZE = 40  # BITMAPINFOHEADER size
    BITS_PER_PIXEL = 24

    try:
        with open(filename, 'wb') as f:
            # Calculate row size and padding
            # Each row's data must be a multiple of 4 bytes.
            bytes_per_pixel = BITS_PER_PIXEL // 8
            row_size_unpadded = width * bytes_per_pixel
            padding = (4 - (row_size_unpadded % 4)) % 4
            row_size_padded = row_size_unpadded + padding

            image_data_size = row_size_padded * height
            file_size = FILE_HEADER_SIZE + INFO_HEADER_SIZE + image_data_size

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

            # --- Pixel Data (Optimized Row-by-Row Generation) ---
            padding_bytes = b'\x00' * padding

            # For patterns that are constant vertically, we generate the row once.
            if pattern != "Vertical Gradient":
                row_data = bytearray()

                # Pre-calculate values for horizontal patterns
                if pattern == "Color Bars":
                    colors_rgb = [
                        (255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
                        (255, 0, 255), (255, 0, 0), (0, 0, 255), (0, 0, 0)
                    ]
                    bar_width = width / 8
                elif pattern == "RGB Stripes":
                    stripe1_end_x = width // 3
                    stripe2_end_x = 2 * (width // 3)

                for x in range(width):
                    current_color_tuple_rgb = (0, 0, 0)
                    if pattern in SOLID_COLORS:
                        current_color_tuple_rgb = SOLID_COLORS[pattern]
                    elif pattern == "RGB Stripes":
                        if x < stripe1_end_x: current_color_tuple_rgb = (255, 0, 0)
                        elif x < stripe2_end_x: current_color_tuple_rgb = (0, 255, 0)
                        else: current_color_tuple_rgb = (0, 0, 255)
                    elif pattern == "Color Bars":
                        bar_index = int(x // bar_width)
                        current_color_tuple_rgb = colors_rgb[min(bar_index, 7)]
                    elif pattern == "Horizontal Gradient":
                        val = int(255 * x / (width - 1)) if width > 1 else 255
                        current_color_tuple_rgb = (val, val, val)

                    row_data.extend(_pack_pixel(current_color_tuple_rgb, pixel_order))

                full_row_bytes = bytes(row_data) + padding_bytes
                for _ in range(height):
                    f.write(full_row_bytes)

            else:  # For patterns that change vertically (e.g., Vertical Gradient)
                for y in range(height):
                    val = int(255 * y / (height - 1)) if height > 1 else 255
                    current_color_tuple_rgb = (val, val, val)
                    pixel_bytes = _pack_pixel(current_color_tuple_rgb, pixel_order)
                    f.write(pixel_bytes * width + padding_bytes)

        # If no exceptions were raised, generation is considered successful.

    except IOError as e:
        raise IOError(f"Error writing file '{filename}': {e}")
    except Exception as e:
        raise Exception(f"Unexpected error generating BMP file '{filename}': {e}")

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

        pixel_order_input = input("Enter pixel order (BGR or RGB, default BGR): ").strip().upper()
        if not pixel_order_input:
            pixel_order_input = "BGR"
        elif pixel_order_input not in ["BGR", "RGB"]:
            print(f"Invalid pixel order '{pixel_order_input}'. Using default BGR.")
            pixel_order_input = "BGR"

        safe_pattern_name = pattern_input.lower().replace(' ', '_')
        output_filename = f"{safe_pattern_name}_{width}x{height}_{pixel_order_input}.bmp"
        print(f"\nGenerating '{output_filename}'...")
        generate_bmp(output_filename, width, height, pattern_input, pixel_order_input)
        print("Done.")
    except ValueError:
        print("Invalid input. Please enter numbers for width/height, or check pattern/pixel order.")
    except Exception as e:
        print(f"Main program error: {e}")

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
        input_frame = ttk.Frame(master, padding="10 10 10 10")
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
        self.pattern_combo = ttk.Combobox(input_frame, textvariable=self.pattern_var, values=PATTERNS, state="readonly", width=12)
        self.pattern_combo.grid(row=2, column=1, sticky="ew", pady=2)

        # Pixel order selection
        ttk.Label(input_frame, text="Pixel Order:").grid(row=3, column=0, sticky="w", pady=2) # Pixel Order
        self.pixel_order_var = tk.StringVar(value="BGR") # Default value
        self.pixel_order_combo = ttk.Combobox(input_frame, textvariable=self.pixel_order_var, values=["BGR", "RGB"], state="readonly", width=12)
        self.pixel_order_combo.grid(row=3, column=1, sticky="ew", pady=2)

        # Frame for the generate button
        button_frame = ttk.Frame(master, padding="10 0 10 10")
        button_frame.grid(row=1, column=0, sticky="ew")

        # Generate button
        self.generate_button = ttk.Button(button_frame, text="Generate BMP", command=self.trigger_generate_bmp) # Generate BMP
        self.generate_button.pack(expand=True, pady=5) # Use pack to center button

        # Configure column weights for proper resizing behavior within input_frame
        input_frame.grid_columnconfigure(1, weight=1)

        # Set initial focus to the width entry field
        self.width_entry.focus()

    def trigger_generate_bmp(self):
        """Handles the 'Generate BMP' button click event."""
        try:
            width_str = self.width_var.get()
            height_str = self.height_var.get()
            pattern = self.pattern_var.get()
            pixel_order = self.pixel_order_var.get()

            if not width_str or not height_str:
                messagebox.showerror("Input Error: Width and height cannot be empty.") # Input Error: Width and height cannot be empty.
                return

            width = int(width_str)
            height = int(height_str)

            # Basic positive check here for quick GUI feedback,
            # generate_bmp will do more thorough validation.
            if not (width > 0 and height > 0):
                 messagebox.showerror("Input Error: Width and height must be positive integers.") # Input Error: Width and height must be positive integers.
                 return

        except ValueError: # Catches int conversion error
            messagebox.showerror("Invalid Input: Width and height must be valid numbers.") # Invalid Input: Width and height must be valid numbers.
            return

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
            generate_bmp(output_filename, width, height, pattern, pixel_order)
            messagebox.showinfo("Success", f"BMP file '{output_filename}' generated successfully.\n(Pattern: {pattern}, {width}x{height}, {pixel_order})") # Success: BMP file ... generated successfully.
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
