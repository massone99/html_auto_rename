import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(
    filename='html_renamer.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Constants
INVALID_FILENAME_CHARS = r'[\\/:*?"<>|]'
SPACE_REPLACEMENT = '_'
LOG_FILENAME = 'html_renamer.log'


class FilenameSanitizer:
    """Utility class for sanitizing filenames."""

    @staticmethod
    def sanitize(filename: str) -> str:
        """Remove invalid characters and replace spaces with underscores."""
        sanitized = re.sub(INVALID_FILENAME_CHARS, '', filename)
        sanitized = re.sub(r'\s+', SPACE_REPLACEMENT, sanitized)
        return sanitized


class HTMLFileProcessor:
    """Processes HTML files to extract <h1> elements and generate new filenames."""

    def __init__(self, directory: str):
        self.directory = directory
        self.html_files = self._collect_html_files()

    def _collect_html_files(self):
        """Collect all .html files in the directory with their creation times."""
        html_files = []
        for filename in os.listdir(self.directory):
            if filename.lower().endswith('.html'):
                filepath = os.path.join(self.directory, filename)
                try:
                    creation_time = os.path.getctime(filepath)
                    html_files.append({'filename': filename, 'filepath': filepath, 'ctime': creation_time})
                except Exception as e:
                    logging.error(f"Error accessing {filepath}: {e}")
        return html_files

    def sort_files_by_creation_date(self) -> list:
        """Sort HTML files by creation time (oldest first)."""
        return sorted(self.html_files, key=lambda x: x['ctime'])

    def extract_title(self, filepath: str) -> str:
        """Extract text from <h1 class="panel__title"> in the HTML file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                soup = BeautifulSoup(file, 'html.parser')
                h1 = soup.find('h1', class_='panel__title')
                if h1 and h1.get_text(strip=True):
                    return FilenameSanitizer.sanitize(h1.get_text(strip=True))
                else:
                    logging.warning(f"<h1 class='panel__title'> not found or empty in {filepath}.")
                    return None
        except Exception as e:
            logging.error(f"Error processing {filepath}: {e}")
            return None


class FileRenamer:
    """Handles the renaming of HTML files based on extracted titles and indexing."""

    def __init__(self, processor: HTMLFileProcessor, add_index: bool = False):
        self.processor = processor
        self.add_index = add_index
        self.renamed_files = []
        self.skipped_files = []
        self.new_filenames_set = set()

    def generate_new_filenames(self):
        """Generate new filenames, optionally with indexing."""
        sorted_files = self.processor.sort_files_by_creation_date()
        index = 1

        for file_info in sorted_files:
            original_filename = file_info['filename']
            original_filepath = file_info['filepath']
            new_title = self.processor.extract_title(original_filepath)

            if not new_title:
                self.skipped_files.append({'original': original_filename, 'reason': 'No <h1 class="panel__title"> found.'})
                continue

            new_name = f"{new_title}.html"

            # Handle duplicates
            duplicate_suffix = 1
            base_new_name = new_name
            while new_name in self.new_filenames_set or os.path.exists(os.path.join(self.processor.directory, new_name)):
                duplicate_suffix += 1
                name, ext = os.path.splitext(base_new_name)
                new_name = f"{name}_{duplicate_suffix}{ext}"

            # Add index if required
            if self.add_index:
                new_name = f"{index}. {new_name}"
                index += 1

            self.new_filenames_set.add(new_name)

            target_filepath = os.path.join(self.processor.directory, new_name)

            # Rename the file
            try:
                os.rename(original_filepath, target_filepath)
                logging.info(f"Renamed '{original_filename}' to '{new_name}'")
                self.renamed_files.append({'original': original_filename, 'new': new_name})
            except Exception as e:
                logging.error(f"Error renaming {original_filename} to {new_name}: {e}")
                self.skipped_files.append({'original': original_filename, 'reason': str(e)})

    def perform_renaming(self):
        """Execute the renaming process."""
        self.generate_new_filenames()
        return self.renamed_files, self.skipped_files


class HTMLRenamerGUI:
    """Graphical User Interface for the HTML File Renamer."""

    def __init__(self, root):
        self.root = root
        self.root.title("HTML File Renamer")
        self.root.geometry("500x300")
        self.root.resizable(False, False)

        # Center the window
        self.center_window()

        # Initialize variables
        self.add_index_var = tk.BooleanVar()

        # Create GUI components
        self.create_widgets()

    def center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        """Create and arrange GUI components."""
        # Title Label
        title_label = tk.Label(self.root, text="HTML File Renamer", font=("Helvetica", 16))
        title_label.pack(pady=20)

        # Add Index Checkbox
        index_check = ttk.Checkbutton(
            self.root,
            text="Add Index (e.g., '1. ')",
            variable=self.add_index_var
        )
        index_check.pack(pady=10)

        # Select Directory Button
        select_button = tk.Button(
            self.root,
            text="Select Directory and Rename",
            command=self.handle_rename,
            width=25,
            height=2
        )
        select_button.pack(pady=10)

        # Progress Bar
        self.progress = ttk.Progressbar(self.root, orient='horizontal', length=400, mode='determinate')
        self.progress.pack(pady=10)
        self.progress['value'] = 0

        # Exit Button
        exit_button = tk.Button(
            self.root,
            text="Exit",
            command=self.root.quit,
            width=25,
            height=2
        )
        exit_button.pack(pady=10)

    def handle_rename(self):
        """Handle the renaming process initiated by the user."""
        directory = filedialog.askdirectory()
        if not directory:
            return  # User cancelled

        # Confirm action
        confirm_message = f"Are you sure you want to rename .html files in:\n{directory}"
        if self.add_index_var.get():
            confirm_message += "\n\nThe files will be prefixed with an index based on creation date."
        confirm = messagebox.askyesno("Confirm", confirm_message)
        if not confirm:
            return

        # Initialize processor and renamer
        processor = HTMLFileProcessor(directory)
        renamer = FileRenamer(processor, add_index=self.add_index_var.get())

        # Update progress bar maximum
        total_files = len(processor.html_files)
        self.progress['maximum'] = total_files
        self.progress['value'] = 0
        self.root.update_idletasks()

        # Perform renaming with progress updates
        sorted_files = processor.sort_files_by_creation_date()
        index = 1

        for file_info in sorted_files:
            original_filename = file_info['filename']
            original_filepath = file_info['filepath']
            new_title = processor.extract_title(original_filepath)

            if not new_title:
                renamer.skipped_files.append({'original': original_filename, 'reason': 'No <h1 class="panel__title"> found.'})
                self.progress['value'] += 1
                self.root.update_idletasks()
                continue

            new_name = f"{new_title}.html"

            # Handle duplicates
            duplicate_suffix = 1
            base_new_name = new_name
            while new_name in renamer.new_filenames_set or os.path.exists(os.path.join(processor.directory, new_name)):
                duplicate_suffix += 1
                name, ext = os.path.splitext(base_new_name)
                new_name = f"{name}_{duplicate_suffix}{ext}"

            # Add index if required
            if self.add_index_var.get():
                new_name = f"{index}. {new_name}"
                index += 1

            renamer.new_filenames_set.add(new_name)

            target_filepath = os.path.join(processor.directory, new_name)

            # Rename the file
            try:
                os.rename(original_filepath, target_filepath)
                logging.info(f"Renamed '{original_filename}' to '{new_name}'")
                renamer.renamed_files.append({'original': original_filename, 'new': new_name})
            except Exception as e:
                logging.error(f"Error renaming {original_filename} to {new_name}: {e}")
                renamer.skipped_files.append({'original': original_filename, 'reason': str(e)})

            # Update progress bar
            self.progress['value'] += 1
            self.root.update_idletasks()

        # Display results
        self.show_results(renamer.renamed_files, renamer.skipped_files)

    def show_results(self, renamed, skipped):
        """Display the results of the renaming process."""
        result_message = f"Renaming Completed!\n\nTotal files renamed: {len(renamed)}\nTotal files skipped: {len(skipped)}"
        if skipped:
            result_message += "\n\nSkipped Files:\n"
            for item in skipped:
                if item['reason']:
                    result_message += f"- {item['original']} (Reason: {item['reason']})\n"
                else:
                    result_message += f"- {item['original']} (No <h1 class='panel__title'> found)\n"
        messagebox.showinfo("Result", result_message)


def main():
    """Main function to run the GUI application."""
    root = tk.Tk()
    app = HTMLRenamerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
