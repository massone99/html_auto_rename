import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from bs4 import BeautifulSoup
from datetime import datetime

def sanitize_filename(filename):
    """
    Sanitize the filename by removing or replacing invalid characters.
    """
    # Remove invalid characters
    sanitized = re.sub(r'[\\/:*?"<>|]', '', filename)
    # Replace spaces with underscores
    sanitized = re.sub(r'\s+', '_', sanitized)
    return sanitized

def get_new_filename(html_file_path):
    """
    Extract the text from the <h1 class="panel__title"> element.
    """
    try:
        with open(html_file_path, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')
            h1 = soup.find('h1', class_='panel__title')
            if h1 and h1.text.strip():
                return sanitize_filename(h1.text.strip()) + '.html'
            else:
                print(f"Warning: <h1 class='panel__title'> not found or empty in {html_file_path}. Skipping.")
                return None
    except Exception as e:
        print(f"Error processing {html_file_path}: {e}")
        return None

def rename_html_files(directory, add_index=False):
    """
    Rename all .html files in the given directory based on their <h1 class="panel__title"> content.
    If add_index is True, prefix filenames with an index based on creation date.
    """
    # Retrieve all .html files with their creation times
    html_files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith('.html'):
            filepath = os.path.join(directory, filename)
            try:
                creation_time = os.path.getctime(filepath)
                html_files.append((filename, creation_time))
            except Exception as e:
                print(f"Error accessing {filepath}: {e}")

    # Sort files by creation time (oldest first)
    html_files.sort(key=lambda x: x[1])

    new_filenames = {}
    renamed_files = []
    skipped_files = []
    index = 1  # Initialize index for prefixing

    for original_filename, _ in html_files:
        original_filepath = os.path.join(directory, original_filename)
        new_name = get_new_filename(original_filepath)
        if new_name:
            # Handle duplicate filenames
            base_name, ext = os.path.splitext(new_name)
            duplicate_count = new_filenames.get(new_name, 0)
            if duplicate_count > 0:
                new_name = f"{base_name}_{duplicate_count}{ext}"
            new_filenames[new_name] = duplicate_count + 1

            # If add_index is enabled, prefix the filename with the index
            if add_index:
                new_name = f"{index}. {new_name}"
                index += 1

            # Ensure the new filename does not already exist
            target_filepath = os.path.join(directory, new_name)
            if os.path.exists(target_filepath):
                print(f"Error: Cannot rename {original_filename} to {new_name} because {new_name} already exists. Skipping.")
                skipped_files.append((original_filename, new_name))
                continue

            try:
                os.rename(original_filepath, target_filepath)
                print(f"Renamed '{original_filename}' to '{new_name}'")
                renamed_files.append((original_filename, new_name))
            except Exception as e:
                print(f"Error renaming {original_filename} to {new_name}: {e}")
                skipped_files.append((original_filename, new_name))
        else:
            skipped_files.append((original_filename, None))

    return renamed_files, skipped_files

def select_directory_and_rename(add_index=False):
    """
    Open a GUI dialog to select a directory and perform the renaming operation.
    """
    directory = filedialog.askdirectory()
    if not directory:
        return  # User cancelled the dialog

    # Confirm with the user
    confirm_message = f"Are you sure you want to rename .html files in:\n{directory}"
    if add_index:
        confirm_message += "\n\nThe files will be prefixed with an index based on creation date."
    confirm = messagebox.askyesno("Confirm", confirm_message)
    if not confirm:
        return

    # Perform renaming
    renamed_files, skipped_files = rename_html_files(directory, add_index=add_index)

    # Prepare the result message
    message = f"Renaming Completed!\n\nTotal files renamed: {len(renamed_files)}\nTotal files skipped: {len(skipped_files)}"
    if skipped_files:
        message += "\n\nSkipped Files:\n"
        for original, new in skipped_files:
            if new:
                message += f"- {original} -> {new} (Conflict or Error)\n"
            else:
                message += f"- {original} (No <h1 class='panel__title'> found)\n"

    messagebox.showinfo("Result", message)

def create_gui():
    """
    Create the main GUI window.
    """
    root = tk.Tk()
    root.title("HTML File Renamer")
    root.geometry("500x250")
    root.resizable(False, False)

    # Center the window on the screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    # Add a welcome label
    label = tk.Label(root, text="HTML File Renamer", font=("Helvetica", 16))
    label.pack(pady=20)

    # Add a checkbox for "Add Index"
    add_index_var = tk.BooleanVar()
    add_index_check = ttk.Checkbutton(root, text="Add Index (e.g., '1. ')", variable=add_index_var)
    add_index_check.pack(pady=10)

    # Add a button to select directory
    select_button = tk.Button(root, text="Select Directory and Rename", command=lambda: select_directory_and_rename(add_index=add_index_var.get()), width=25, height=2)
    select_button.pack(pady=10)

    # Add an exit button
    exit_button = tk.Button(root, text="Exit", command=root.quit, width=25, height=2)
    exit_button.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    create_gui()
