import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import os
import rawpy
import numpy as np
import threading
import io
import argparse

class RawImageViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("fastraw")
        
        # Configure the main window with dark theme
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        self.root.configure(bg="#121212")
        
        # Create canvas for image display with dark background
        self.canvas = tk.Canvas(self.root, bg="#121212", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Create minimal status bar with dark theme
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, 
                                   bg="#1E1E1E", fg="#AAAAAA", 
                                   anchor=tk.W, padx=10, pady=5)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create a native button with rounded style
        self.open_button = tk.Button(
            self.canvas, 
            text="Open Image",
            font=("Helvetica", 12, "bold"),
            bg="#2D2D2D", 
            fg="#FFFFFF",
            activebackground="#3D3D3D",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            borderwidth=0,
            padx=20,
            pady=10,
            command=self.open_file
        )
        # We'll initialize it in show_open_button
        self.open_button_window = None
        
        # Variables for image display
        self.current_image_path = None
        self.preview_image = None           # PhotoImage for display
        self.full_image = None              # PhotoImage for display
        self.displayed_image = None         # Current PhotoImage being displayed
        self.image_id = None                # Canvas image ID
        
        # Store PIL versions of images for blending
        self.preview_pil = None             # PIL version of preview
        self.full_pil = None                # PIL version of full image
        
        # Variables for fade transition
        self.transition_active = False
        self.alpha = 0.0
        self.fade_speed = 0.01
        self.fade_after_id = None
        self._resize_job = None
        
        # Bind events
        self.root.bind("<Configure>", self.on_resize)
        self.root.bind("<o>", lambda e: self.open_file())     # Keyboard shortcut 'o' to open files
        self.root.bind("<Escape>", lambda e: root.quit())     # ESC to quit
        
        # Right-click menu for basic operations
        self.context_menu = tk.Menu(self.root, tearoff=0, bg="#1E1E1E", fg="#AAAAAA", 
                                   activebackground="#2D2D2D", activeforeground="#FFFFFF")
        self.context_menu.add_command(label="Open RAW file", command=self.open_file)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Exit", command=root.quit)
        
        # Bind right-click to show menu
        self.root.bind("<Button-3>", self.show_context_menu)
        
        # Show the Open Image button initially
        self.root.after(100, self.show_open_button)
        
    def show_context_menu(self, event):
        """Show the context menu on right-click"""
        self.context_menu.tk_popup(event.x_root, event.y_root)
        
    def open_file(self):
        """Open a file dialog to select a RAW image file"""
        file_types = [("RAW Files", "*.raw *.arw *.cr2 *.cr3 *.nef *.dng *.raf *.orf *.pef *.rw2 *.srw *.x3f")]
        file_path = filedialog.askopenfilename(filetypes=file_types)
        
        if file_path:
            self.open_specific_file(file_path)
    
    def open_specific_file(self, file_path):
        """Open a specific RAW file given its path"""
        if os.path.isfile(file_path):
            # Use existing open_file logic after setting the path
            self.current_image_path = file_path
            self.status_var.set(f"Loading: {os.path.basename(file_path)}")
            
            # Clear previous images and hide the button
            if self.image_id:
                self.canvas.delete(self.image_id)
            if self.open_button_window:
                self.canvas.delete(self.open_button_window)
                self.open_button_window = None
                
            self.preview_image = None
            self.preview_pil = None
            self.full_image = None
            self.full_pil = None
            self.displayed_image = None
            
            # Start loading the embedded preview
            threading.Thread(target=self.load_preview, args=(file_path,), daemon=True).start()
        else:
            self.status_var.set(f"Error: File not found - {file_path}")
            # Show the Open Image button if file loading failed
            self.show_open_button()

    def load_preview(self, file_path):
        """Load the embedded preview of the RAW file"""
        try:
            # Load the preview from the RAW file
            with rawpy.imread(file_path) as raw:
                try:
                    # Try to extract the thumbnail
                    thumb = raw.extract_thumb()
                    if thumb.format == rawpy.ThumbFormat.JPEG:
                        preview_data = thumb.data
                        preview_img = Image.open(io.BytesIO(preview_data))
                    else:
                        # If thumbnail isn't a JPEG, create a quick low-res render
                        rgb = raw.postprocess(use_camera_wb=True, half_size=True, no_auto_bright=True)
                        preview_img = Image.fromarray(rgb)
                except (AttributeError, RuntimeError):
                    # If thumbnail extraction fails, create a quick low-res render
                    rgb = raw.postprocess(use_camera_wb=True, half_size=True, no_auto_bright=True)
                    preview_img = Image.fromarray(rgb)
            
            # Display the preview in the main UI thread
            self.root.after(0, lambda img=preview_img: self.display_image(img, is_preview=True))
            
            # Start loading the full image in another thread
            threading.Thread(target=self.load_full_image, args=(file_path,), daemon=True).start()
            
        except Exception as e:
            error_message = str(e)
            self.root.after(0, lambda msg=error_message: self.status_var.set(f"Error: {msg}"))
    
    def load_full_image(self, file_path):
        """Load and process the full RAW image"""
        try:
            filename = os.path.basename(file_path)
            self.root.after(0, lambda fname=filename: self.status_var.set(f"Processing RAW image: {fname}"))
            
            # Load and process the RAW file
            with rawpy.imread(file_path) as raw:
                # Process with high quality settings
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    demosaic_algorithm=rawpy.DemosaicAlgorithm.DCB,
                    no_auto_bright=True,
                    output_bps=16
                )
                
                # Convert to 8-bit for display
                if rgb.dtype != np.uint8:
                    # Scale 16-bit to 8-bit
                    rgb = (rgb / 256).astype(np.uint8)
                
                full_img = Image.fromarray(rgb)
            
            # Signal that the full image is ready in the main UI thread
            # Pass the image as an argument to the lambda to ensure it's available when the lambda executes
            self.root.after(0, lambda img=full_img: self.start_transition(img))
            
        except Exception as e:
            error_message = str(e)
            self.root.after(0, lambda msg=error_message: self.status_var.set(f"Error: {msg}"))
    
    def display_image(self, img, is_preview=False):
        """Display an image on the canvas with proper scaling"""
        if img:
            # Resize image to fit the canvas
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                img_resized = self.resize_image_to_fit(img, canvas_width, canvas_height)
                
                # Convert to PhotoImage for display
                photo_img = ImageTk.PhotoImage(img_resized)
                
                # Calculate position to center the image
                x_pos = (canvas_width - photo_img.width()) // 2
                y_pos = (canvas_height - photo_img.height()) // 2
                
                # Display the image
                if self.image_id:
                    self.canvas.delete(self.image_id)
                
                self.image_id = self.canvas.create_image(x_pos, y_pos, anchor=tk.NW, image=photo_img)
                
                # We need to keep a reference to prevent garbage collection
                if is_preview:
                    # Store both the PIL and PhotoImage versions
                    self.preview_pil = img_resized
                    self.preview_image = photo_img
                    self.displayed_image = photo_img
                    self.status_var.set(f"Preview: {os.path.basename(self.current_image_path)}")
                else:
                    self.full_pil = img_resized
                    self.full_image = photo_img
    
    def start_transition(self, full_img):
        """Start the transition from preview to full image"""
        if not self.preview_image:
            # If no preview was shown, just display the full image
            self.display_image(full_img)
            self.status_var.set(f"Loaded: {os.path.basename(self.current_image_path)}")
            return
        
        # Store the original full-size image
        self.full_size_img = full_img
        
        # Resize to match the current display size
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Store the initial transition size for resize detection
        self._last_transition_size = (canvas_width, canvas_height)
        
        # Resize the full image to the same dimensions as the preview
        if canvas_width > 1 and canvas_height > 1:
            resized_full = self.resize_image_to_fit(full_img, canvas_width, canvas_height)
            
            # Store both PIL and PhotoImage versions
            self.full_pil = resized_full
            self.full_image = ImageTk.PhotoImage(resized_full)
            
            # Cancel any existing fade transition
            if self.fade_after_id:
                try:
                    self.root.after_cancel(self.fade_after_id)
                except ValueError:
                    pass
                self.fade_after_id = None
            
            # Start fade transition
            self.alpha = 0.0
            self.transition_active = True
            self.status_var.set("Loading...")
            
            # Start the fade transition in the main thread via after()
            # This will execute in the main thread's event loop ensuring smooth UI
            self.fade_after_id = self.root.after(10, self.fade_transition)
    
    def fade_transition(self):
        """Perform a smooth fade transition between preview and full image"""
        if not self.transition_active or not self.preview_pil or not self.full_pil:
            return
        
        # Increase alpha for the transition
        self.alpha += self.fade_speed
        
        # Get current canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if self.alpha >= 1.0:
            # Transition complete, display the full image
            self.transition_active = False
            self.alpha = 1.0
            
            # Update the canvas with the final image
            if self.image_id:
                self.canvas.delete(self.image_id)
            
            x_pos = (canvas_width - self.full_image.width()) // 2
            y_pos = (canvas_height - self.full_image.height()) // 2
            
            self.image_id = self.canvas.create_image(x_pos, y_pos, anchor=tk.NW, image=self.full_image)
            self.displayed_image = self.full_image
            
            # Clear any fade timer reference
            self.fade_after_id = None
            
            self.status_var.set(f"Loaded: {os.path.basename(self.current_image_path)}")
            return
        
        try:
            # Create a simple crossfade
            # Convert both images to the same mode if needed
            if self.preview_pil.mode != self.full_pil.mode:
                if 'A' in self.full_pil.mode:  # If full has alpha
                    preview_img = self.preview_pil.convert(self.full_pil.mode)
                else:
                    preview_img = self.preview_pil
            else:
                preview_img = self.preview_pil
            
            # Always ensure dimensions match the current canvas size
            # and both images have the same size for proper blending
            curr_width = self.canvas.winfo_width()
            curr_height = self.canvas.winfo_height()
            
            # Check if the canvas size has changed during transition
            if hasattr(self, '_last_transition_size'):
                w_diff = abs(curr_width - self._last_transition_size[0])
                h_diff = abs(curr_height - self._last_transition_size[1])
                
                if w_diff > 5 or h_diff > 5:  # If size changed significantly
                    # Update the size record
                    self._last_transition_size = (curr_width, curr_height)
                    
                    # Resize both images to match the new canvas size
                    if hasattr(self, 'full_size_img') and self.full_size_img:
                        preview_img = self.resize_image_to_fit(preview_img, curr_width, curr_height)
                        self.full_pil = self.resize_image_to_fit(self.full_size_img, curr_width, curr_height)
            
            # Double-check that dimensions match
            if preview_img.size != self.full_pil.size:
                # Force them to be the same size for proper blending
                preview_img = preview_img.resize(self.full_pil.size, Image.Resampling.LANCZOS)
            
            # Now blend the two images
            blended = Image.blend(preview_img, self.full_pil, self.alpha)
            
            # Convert to PhotoImage and display
            blended_photo = ImageTk.PhotoImage(blended)
            self.displayed_image = blended_photo
            
            # Display the blended image
            if self.image_id:
                self.canvas.delete(self.image_id)
                
            x_pos = (curr_width - blended_photo.width()) // 2
            y_pos = (curr_height - blended_photo.height()) // 2
            
            self.image_id = self.canvas.create_image(x_pos, y_pos, anchor=tk.NW, image=blended_photo)
            
            # Update status
            self.status_var.set(f"Loading... {int(self.alpha * 100)}%")
            
        except Exception as e:
            # If anything fails, just jump to the full image
            print(f"Error during transition: {e}")
            self.transition_active = False
            if hasattr(self, 'full_size_img') and self.full_size_img:
                self.display_image(self.full_size_img)
            return
            
        # Schedule the next frame of the transition - use 40ms for ~25fps animation
        self.fade_after_id = self.root.after(40, self.fade_transition)
    
    def resize_image_to_fit(self, img, canvas_width, canvas_height):
        """Resize an image to fit within the canvas while maintaining aspect ratio"""
        img_width, img_height = img.size
        
        # Calculate the scaling factor
        width_ratio = canvas_width / img_width
        height_ratio = canvas_height / img_height
        scale_factor = min(width_ratio, height_ratio)
        
        # Calculate new size
        new_width = int(img_width * scale_factor)
        new_height = int(img_height * scale_factor)
        
        # Resize the image
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def on_resize(self, event):
        """Handle window resize events"""
        # Only handle resizing of the main window, not child widgets
        if event.widget == self.root:
            # Wait a bit to avoid excessive resizing operations
            if hasattr(self, '_resize_job') and self._resize_job:
                try:
                    self.root.after_cancel(self._resize_job)
                except ValueError:
                    # Handle the case where the ID is not valid
                    pass
                
            if self.displayed_image:
                self._resize_job = self.root.after(100, self.resize_displayed_image)
            elif self.open_button_window:
                # If no image is displayed but we have a button, reposition it
                self._resize_job = self.root.after(100, self.show_open_button)
    
    def resize_displayed_image(self):
        """Resize the currently displayed image to fit the new canvas size"""
        try:
            # Get the canvas dimensions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if self.transition_active:
                # Don't cancel the transition, just resize both images and continue
                if hasattr(self, 'full_size_img') and self.full_size_img:
                    # Resize both images to the new canvas size
                    new_preview = self.resize_image_to_fit(
                        self.preview_pil, canvas_width, canvas_height)
                    new_full = self.resize_image_to_fit(
                        self.full_size_img, canvas_width, canvas_height)
                        
                    # Update the PIL versions
                    self.preview_pil = new_preview
                    self.full_pil = new_full
                    self.full_image = ImageTk.PhotoImage(new_full)
                    
                    # Update transition size for future checks
                    self._last_transition_size = (canvas_width, canvas_height)
            else:
                # If no transition is active, just resize the current image
                if hasattr(self, 'full_size_img') and self.full_size_img:
                    # If we have the full image loaded, resize and display it
                    self.display_image(self.full_size_img)
                elif hasattr(self, 'preview_pil') and self.preview_pil:
                    # If only the preview is loaded, resize and display it
                    self.display_image(self.preview_pil, is_preview=True)
                
        except Exception as e:
            print(f"Error during resize: {e}")
            
        # Reset the resize job ID to prevent further errors
        self._resize_job = None

    def show_open_button(self):
        """Display a native button in the center of the canvas"""
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            # Canvas not yet properly sized, schedule this again
            self.root.after(100, self.show_open_button)
            return
        
        # Configure the button style
        if hasattr(self, '_init_button_style') and not self._init_button_style:
            # Round the button corners using custom styling
            # Initialize a custom style for the button
            self.open_button.config(
                highlightthickness=0,
                highlightbackground="#2D2D2D",
                cursor="hand2"  # Change cursor to hand when hovering
            )
            
            # Configure hover effects
            self.open_button.bind("<Enter>", lambda e: e.widget.config(bg="#3D3D3D"))
            self.open_button.bind("<Leave>", lambda e: e.widget.config(bg="#2D2D2D"))
            
            self._init_button_style = True
        
        # Position the button in the center of the canvas
        button_width = 180  # Fixed width
        button_height = 50  # Fixed height
        
        x = (canvas_width - button_width) // 2
        y = (canvas_height - button_height) // 2
        
        # Configure the button size
        self.open_button.config(width=15, height=2)  # Approximate size in characters/lines
        
        # Create or update the button window on the canvas
        if self.open_button_window:
            self.canvas.coords(self.open_button_window, x, y)
        else:
            self.open_button_window = self.canvas.create_window(x, y, window=self.open_button, anchor=tk.NW)
            self._init_button_style = False  # Trigger style initialization

def parse_arguments():
    """Parse command line arguments for the application"""
    parser = argparse.ArgumentParser(description='Fast Raw Image Viewer')
    parser.add_argument('file', nargs='?', default=None, help='Path to a RAW image file to open')
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Initialize the application
    root = tk.Tk()
    
    # Set dark mode for all dialog windows
    root.tk_setPalette(
        background='#121212', 
        foreground='#EEEEEE',
        activeBackground='#2D2D2D',
        activeForeground='#FFFFFF'
    )
    
    app = RawImageViewer(root)
    
    # If a file path was provided as an argument, open it
    if args.file and os.path.isfile(args.file):
        # Schedule the file opening after the UI is fully initialized
        root.after(100, lambda: app.open_specific_file(args.file))
    
    root.mainloop()

if __name__ == "__main__":
    main()