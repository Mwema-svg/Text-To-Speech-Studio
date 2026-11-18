
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from gtts import gTTS
from pydub import AudioSegment
import threading
import tempfile
import os
import re
import queue
import subprocess
import sys


# -------------------------------
# APPLICATION CONFIGURATION
# -------------------------------

root = tk.Tk()
root.title("Text To Speech Studio")
root.geometry("850x800")
root.configure(bg="#1e1e2e")
root.minsize(650, 550)

BG = "#1e1e2e"
PANEL = "#313244"
TEXT_COLOR = "#cdd6f4"
BLUE = "#89b4fa"
GREEN = "#a6e3a1"

events = queue.Queue()
converting = False


# -------------------------------
# SPLIT LONG TEXT
# -------------------------------

def split_text(text, max_chars=3500):

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    chunks = []
    current = ""

    for sentence in sentences:

        if len(sentence) > max_chars:

            if current:
                chunks.append(current)
                current = ""

            words = sentence.split()

            for word in words:

                if len(current) + len(word) + 1 > max_chars:
                    chunks.append(current)
                    current = word

                else:
                    current = (current + " " + word).strip()

            continue

        if len(current) + len(sentence) + 1 <= max_chars:
            current = (current + " " + sentence).strip()

        else:
            chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return chunks


# -------------------------------
# WORD COUNTER
# -------------------------------

def update_counter(event=None):

    text = text_area.get("1.0", "end-1c")

    words = len(text.split())
    characters = len(text)

    counter_label.config(
        text=f"Words: {words}   |   Characters: {characters}"
    )


# -------------------------------
# CONVERT TEXT TO SPEECH
# -------------------------------

def convert_worker(text, language, save_path):

    try:

        chunks = split_text(text)

        combined_audio = AudioSegment.empty()

        with tempfile.TemporaryDirectory() as temp_dir:

            for index, chunk in enumerate(chunks):

                events.put(("progress", index + 1, len(chunks)))

                temp_file = os.path.join(
                    temp_dir,
                    f"chunk_{index}.mp3"
                )

                tts = gTTS(
                    text=chunk,
                    lang=language
                )

                tts.save(temp_file)

                audio = AudioSegment.from_mp3(temp_file)

                combined_audio += audio

            combined_audio.export(
                save_path,
                format="mp3"
            )

        events.put(("success", save_path))

    except Exception as error:

        events.put(("error", str(error)))


def convert_text():

    global converting

    if converting:
        return

    text = text_area.get("1.0", "end-1c").strip()

    if not text:
        messagebox.showwarning(
            "Empty Text",
            "Please enter some text first."
        )
        return

    language = language_box.get().split(" - ")[0]

    save_path = filedialog.asksaveasfilename(
        defaultextension=".mp3",
        filetypes=[("MP3 Audio", "*.mp3")],
        initialfile="Speech.mp3"
    )

    if not save_path:
        return

    converting = True

    convert_btn.config(
        state="disabled",
        text="Converting..."
    )

    progress_bar["value"] = 0
    status_label.config(text="Preparing audio...")

    thread = threading.Thread(
        target=convert_worker,
        args=(text, language, save_path),
        daemon=True
    )

    thread.start()


# -------------------------------
# PLAY GENERATED AUDIO
# -------------------------------

def play_audio():

    path = filedialog.askopenfilename(
        filetypes=[("MP3 Audio", "*.mp3")]
    )

    if not path:
        return

    try:

        if sys.platform == "win32":
            os.startfile(path)

        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])

        else:
            subprocess.Popen(["xdg-open", path])

    except Exception as error:

        messagebox.showerror("Playback Error", str(error))


# -------------------------------
# CLEAR TEXT
# -------------------------------

def clear_text():

    text_area.delete("1.0", tk.END)
    update_counter()
    status_label.config(text="Ready")


# -------------------------------
# HANDLE BACKGROUND EVENTS
# -------------------------------

def check_events():

    global converting

    try:

        while True:

            event = events.get_nowait()

            if event[0] == "progress":

                current = event[1]
                total = event[2]

                progress_bar["maximum"] = total
                progress_bar["value"] = current

                status_label.config(
                    text=f"Converting chunk {current} of {total}..."
                )

            elif event[0] == "success":

                converting = False

                convert_btn.config(
                    state="normal",
                    text="Convert to Speech"
                )

                status_label.config(text="Conversion completed!")

                messagebox.showinfo(
                    "Success",
                    f"Audio saved successfully:\n{event[1]}"
                )

            elif event[0] == "error":

                converting = False

                convert_btn.config(
                    state="normal",
                    text="Convert to Speech"
                )

                status_label.config(text="Conversion failed")

                messagebox.showerror(
                    "Conversion Error",
                    event[1]
                )

    except queue.Empty:
        pass

    root.after(100, check_events)


# -------------------------------
# USER INTERFACE
# -------------------------------

title = tk.Label(
    root,
    text="TEXT TO SPEECH STUDIO",
    font=("Arial", 25, "bold"),
    bg=BG,
    fg=BLUE
)
title.pack(pady=20)

subtitle = tk.Label(
    root,
    text="Convert your written words into natural speech",
    font=("Arial", 11),
    bg=BG,
    fg=TEXT_COLOR
)
subtitle.pack(pady=5)


# Text editor

editor_frame = tk.Frame(root, bg=PANEL, height=350)
editor_frame.pack(
    padx=25,
    pady=15,
    fill="both",
    expand=True
)

editor_frame.pack_propagate(False)

text_area = tk.Text(
    editor_frame,
    font=("Arial", 12),
    bg=PANEL,
    fg=TEXT_COLOR,
    insertbackground="white",
    wrap="word",
    relief="flat",
    padx=15,
    pady=15
)

text_area.pack(
    fill="both",
    expand=True
)

text_area.bind("<KeyRelease>", update_counter)
text_area.bind("<<Paste>>", lambda event: root.after(50, update_counter))


# Word counter

counter_label = tk.Label(
    root,
    text="Words: 0   |   Characters: 0",
    bg=BG,
    fg=TEXT_COLOR,
    font=("Arial", 10)
)

counter_label.pack(anchor="e", padx=30)


# Language selection

language_frame = tk.Frame(root, bg=BG)
language_frame.pack(pady=12)

language_label = tk.Label(
    language_frame,
    text="Language:",
    bg=BG,
    fg=TEXT_COLOR,
    font=("Arial", 11)
)

language_label.pack(side="left", padx=8)

language_box = ttk.Combobox(
    language_frame,
    values=[
        "en - English",
        "en-uk - English (UK)",
        "en-us - English (US)",
        "sw - Swahili",
        "fr - French",
        "de - German",
        "es - Spanish"
    ],
    state="readonly",
    width=22
)

language_box.set("en - English")
language_box.pack(side="left")


# Buttons
# Buttons

button_frame = tk.Frame(root, bg=BG)
button_frame.pack(
    side="bottom",
    fill="x",
    padx=20,
    pady=15
)

convert_btn = tk.Button(
    button_frame,
    text="Convert to Speech",
    command=convert_text,
    bg=BLUE,
    fg="#11111b",
    font=("Arial", 11, "bold"),
    width=20,
    relief="flat",
    padx=10,
    pady=10
)

convert_btn.pack(side="left", padx=10, expand=True)

play_btn = tk.Button(
    button_frame,
    text="Play Audio",
    command=play_audio,
    bg=GREEN,
    fg="#11111b",
    font=("Arial", 11, "bold"),
    width=15,
    relief="flat",
    padx=10,
    pady=10
)

play_btn.pack(side="left", padx=10, expand=True)

clear_btn = tk.Button(
    button_frame,
    text="Clear Text",
    command=clear_text,
    bg="#f38ba8",
    fg="#11111b",
    font=("Arial", 11, "bold"),
    width=12,
    relief="flat",
    padx=10,
    pady=10
)

clear_btn.pack(side="left", padx=10, expand=True)

# Progress indicator

progress_bar = ttk.Progressbar(
    root,
    mode="determinate",
    length=450
)

progress_bar.pack(pady=10)

status_label = tk.Label(
    root,
    text="Ready",
    bg=BG,
    fg=GREEN,
    font=("Arial", 10)
)

status_label.pack(pady=5)


# Start event checking

root.after(100, check_events)

root.mainloop()
