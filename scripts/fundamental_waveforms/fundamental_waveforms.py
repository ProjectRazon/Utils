import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pyaudio
import threading
import time # For time.sleep if ever needed, not actively used for critical timing
import traceback # For more detailed error printing if needed
import sys # For sys.exit as a last resort diagnostic

# --- Constants ---
SAMPLE_RATE = 44100
PLAY_DURATION_S = 5.0
AMPLITUDE = 0.5
FRAMES_PER_BUFFER = 1024

class WaveformApp:
    NUM_PERIODS_TO_PLOT = 3

    def __init__(self, master):
        self.master = master
        master.title("Waveform Generator")
        self._is_closed = False
        self.waveform_generators = {
            "Sine": self.generate_sine, "Square": self.generate_square,
            "Triangle": self.generate_triangle, "Sawtooth": self.generate_sawtooth
        }
        self.pa = None
        self.audio_thread = None
        self.stop_audio_event = None
        self.audio_active = False
        self.fig = None # Initialize fig attribute
        self.ax = None  # Initialize ax attribute

        self._init_gui_elements()
        self._init_pyaudio()
        self.update_plot_display_only()
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _init_gui_elements(self):
        control_frame = ttk.Frame(self.master, padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(control_frame, text="Waveform Type:").pack(side=tk.LEFT, padx=5)
        self.wave_type_var = tk.StringVar(value=list(self.waveform_generators.keys())[0])
        self.wave_combo = ttk.Combobox(control_frame, textvariable=self.wave_type_var,
                                       values=list(self.waveform_generators.keys()),
                                       state="readonly", width=10)
        self.wave_combo.pack(side=tk.LEFT, padx=5)
        self.wave_combo.bind("<<ComboboxSelected>>", lambda e: self.update_plot_display_only())
        ttk.Label(control_frame, text="Frequency (Hz):").pack(side=tk.LEFT, padx=5)
        self.freq_var = tk.StringVar(value="440")
        self.freq_entry = ttk.Entry(control_frame, textvariable=self.freq_var, width=7)
        self.freq_entry.pack(side=tk.LEFT, padx=5)
        self.freq_entry.bind("<Return>", lambda e: self.update_plot_display_only())
        self.freq_entry.bind("<FocusOut>", lambda e: self.update_plot_display_only())
        self.play_stop_button = ttk.Button(control_frame, text="Play", command=self.on_play_stop_button_click)
        self.play_stop_button.pack(side=tk.LEFT, padx=5)
        plot_frame = ttk.Frame(self.master, padding="5")
        plot_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Initialize fig and ax here
        self.fig, self.ax = plt.subplots() 
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)
        self._setup_plot_style()

    def _init_pyaudio(self):
        try:
            self.pa = pyaudio.PyAudio()
        except Exception as e:
            messagebox.showerror("Audio Error", f"Could not initialize PyAudio: {e}\nPlayback will be disabled.")
            self.pa = None
            if hasattr(self, 'play_stop_button'):
                self.play_stop_button.config(state=tk.DISABLED)

    def generate_sine(self, frequency, duration, sample_rate):
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        return t, (AMPLITUDE * np.sin(2 * np.pi * frequency * t)).astype(np.float32)

    def generate_square(self, frequency, duration, sample_rate):
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        waveform = AMPLITUDE * np.sign(np.sin(2 * np.pi * frequency * t))
        waveform[waveform == 0] = AMPLITUDE
        return t, waveform.astype(np.float32)

    def generate_triangle(self, frequency, duration, sample_rate):
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        return t, (AMPLITUDE * (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * frequency * t))).astype(np.float32)

    def generate_sawtooth(self, frequency, duration, sample_rate):
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        return t, (AMPLITUDE * 2 * (t * frequency - np.floor(0.5 + t * frequency))).astype(np.float32)

    def _setup_plot_style(self):
        if not self.ax: return # Should not happen if _init_gui_elements ran
        self.ax.set_ylim(-1.1, 1.1)
        self.ax.set_yticks([-1.0, -0.5, 0, 0.5, 1.0])
        self.ax.set_ylabel("Amplitude")
        self.ax.set_xticks([])
        self.ax.set_xlabel("Time")
        self.ax.grid(True, axis='y', linestyle=':')
        if self.fig: self.fig.tight_layout()

    def update_plot_display_only(self, frequency_hz_override=None, wave_type_key_override=None):
        if self._is_closed or not self.fig or not self.ax: return
        wave_type_key = wave_type_key_override if wave_type_key_override else self.wave_type_var.get()
        frequency_hz = 440.0
        try:
            temp_freq = float(frequency_hz_override if frequency_hz_override is not None else self.freq_var.get())
            if temp_freq > 0: frequency_hz = temp_freq
        except ValueError: pass
        generator_func = self.waveform_generators[wave_type_key]
        plot_duration_s = max(0.001, min(self.NUM_PERIODS_TO_PLOT / frequency_hz, 0.2))
        t_plot, waveform_plot = generator_func(frequency_hz, plot_duration_s, SAMPLE_RATE)
        self.ax.clear()
        self._setup_plot_style()
        self.ax.plot(t_plot, waveform_plot, color='b')
        self.ax.set_xlim(0, plot_duration_s)
        try:
            if self.canvas: self.canvas.draw()
        except tk.TclError: pass

    def on_play_stop_button_click(self):
        if self._is_closed: return
        if not self.pa:
            messagebox.showerror("Audio Error", "PyAudio is not available.")
            return
        if self.audio_active:
            print("Stop button pressed.")
            self.audio_active = False
            if self.stop_audio_event: self.stop_audio_event.set()
            self.play_stop_button.config(text="Play")
        else:
            print("Play button pressed.")
            try:
                frequency = float(self.freq_var.get())
                if frequency <= 0:
                    messagebox.showerror("Input Error", "Frequency must be positive.")
                    return
            except ValueError:
                messagebox.showerror("Input Error", "Invalid frequency.")
                return
            self.update_plot_display_only(frequency_hz_override=frequency)
            if self.audio_thread and self.audio_thread.is_alive():
                print("Play: Previous audio thread active. Signaling stop...")
                if self.stop_audio_event: self.stop_audio_event.set()
                self.audio_thread.join(timeout=0.5)
                if self.audio_thread.is_alive(): print("Play: Warning! Previous audio thread didn't exit.")
            wave_type = self.wave_type_var.get()
            _, waveform_play = self.waveform_generators[wave_type](frequency, PLAY_DURATION_S, SAMPLE_RATE)
            self.audio_active = True
            self.play_stop_button.config(text="Stop")
            self.stop_audio_event = threading.Event()
            self.audio_thread = threading.Thread(target=self._play_audio_thread_target,
                                                 args=(self.stop_audio_event, waveform_play, wave_type, frequency))
            self.audio_thread.daemon = True
            self.audio_thread.start()

    def _play_audio_thread_target(self, stop_event, audio_data, wave_type, freq):
        stream = None
        sound_played = False
        tid = threading.get_ident()
        print(f"AudioThread-{tid} ({wave_type}@{freq}Hz): Started.")
        try:
            if stop_event.is_set() or not self.audio_active: return
            if not self.pa: print(f"AudioThread-{tid}: PyAudio (self.pa) is None."); return
            stream = self.pa.open(format=pyaudio.paFloat32, channels=1, rate=SAMPLE_RATE,
                                  output=True, frames_per_buffer=FRAMES_PER_BUFFER)
            print(f"AudioThread-{tid}: Stream opened.")
            for i in range(0, len(audio_data), FRAMES_PER_BUFFER):
                if stop_event.is_set() or not self.audio_active: break
                chunk = audio_data[i:min(i + FRAMES_PER_BUFFER, len(audio_data))]
                if len(chunk) > 0: stream.write(chunk.tobytes()); sound_played = True
            if sound_played and not stop_event.is_set() and self.audio_active:
                 print(f"AudioThread-{tid}: Playback finished naturally.")
        except Exception as e:
            if not stop_event.is_set() and self.audio_active : print(f"AudioThread-{tid}: Exception: {e}")
        finally:
            print(f"AudioThread-{tid}: Entering finally block.")
            if stream:
                try:
                    print(f"AudioThread-{tid}: Attempting to stop/close stream.")
                    if stream.is_active(): stream.stop_stream(); print(f"AudioThread-{tid}: Stream stopped.")
                    stream.close(); print(f"AudioThread-{tid}: Stream closed.")
                except Exception as e_close: print(f"AudioThread-{tid}: Error stopping/closing stream: {e_close}")
            else: print(f"AudioThread-{tid}: No stream object in finally.")
            if not self._is_closed:
                print(f"AudioThread-{tid}: Scheduling UI update.")
                if self.master and self.master.winfo_exists(): # Check master exists
                    self.master.after(0, self._update_ui_after_playback_change)
                else:
                    print(f"AudioThread-{tid}: Master window gone, not scheduling UI update.")
            else: print(f"AudioThread-{tid}: App closing, not scheduling UI update.")
            print(f"AudioThread-{tid}: Exiting.")

    def _update_ui_after_playback_change(self):
        if self._is_closed: return
        try: # Add try-except for robustness during shutdown
            if not self.master.winfo_exists(): return # Check again
            if not self.audio_active:
                if self.play_stop_button['text'] != "Play": self.play_stop_button.config(text="Play")
            else:
                if self.audio_thread and self.audio_thread.is_alive():
                    if self.play_stop_button['text'] != "Stop": self.play_stop_button.config(text="Stop")
                else: # Audio active but thread dead means natural finish or error
                    self.audio_active = False
                    if self.play_stop_button['text'] != "Play": self.play_stop_button.config(text="Play")
        except tk.TclError:
            print("UI Update: TclError (likely window destroyed during update)")
        except Exception as e:
            print(f"UI Update: Unexpected error: {e}")


    def on_closing(self):
        if self._is_closed:
            print("on_closing: Already processed.")
            return
        print("Application closing sequence initiated...")
        self.audio_active = False
        if self.stop_audio_event: self.stop_audio_event.set()

        if self.audio_thread and self.audio_thread.is_alive():
            print("Waiting for audio thread to exit (max 1s)...")
            self.audio_thread.join(timeout=1.0)
            if self.audio_thread.is_alive(): print("Warning: Audio thread did not terminate cleanly.")

        if self.pa is not None:
            try:
                print("Terminating PyAudio instance...")
                self.pa.terminate()
                self.pa = None
                print("PyAudio instance terminated.")
            except Exception as e: print(f"Error terminating PyAudio: {e}")

        # Step 1: Explicitly Close Matplotlib Figure
        if self.fig is not None:
            try:
                print("Closing Matplotlib figure...")
                plt.close(self.fig) # Close the figure object
                self.fig = None
                self.canvas = None # Also clear canvas reference
                print("Matplotlib figure closed.")
            except Exception as e: print(f"Error closing Matplotlib figure: {e}")
        
        window_destroyed_successfully = False
        try:
            if self.master and self.master.winfo_exists():
                # Step 2: Ensure Tkinter Processes Pending Events
                print("Updating Tkinter idle tasks before destroying master window...")
                self.master.update_idletasks()
                self.master.update() # Process events

                print("Destroying master window...")
                self.master.destroy()
                print("Application window destroyed.")
                window_destroyed_successfully = True
            else: print("Master window TK widget already destroyed or master is None.")
        except tk.TclError as e: print(f"TclError destroying master window: {e}")
        except Exception as e: print(f"General error destroying master window: {e}")
        finally:
            self._is_closed = True
            print(f"on_closing: _is_closed flag set to True. Window destroyed: {window_destroyed_successfully}")
            # Diagnostic: Force exit if still hanging after these steps.
            # This is a heavy hammer, indicates something else is wrong if needed.
            # print("Forcing exit with sys.exit(0) as a diagnostic.")
            # sys.exit(0) # Uncomment this line ONLY for diagnostics if it still hangs

# --- Main Execution ---
if __name__ == "__main__":
    app = None
    root = tk.Tk()
    try:
        app = WaveformApp(root)
        root.mainloop()
        # Step 3: Add a Print Statement After mainloop()
        print("Main: root.mainloop() has successfully exited.")
    except KeyboardInterrupt:
        print("Main: Application interrupted by user (KeyboardInterrupt).")
    except Exception as e:
        print(f"Main: Unhandled exception in main try block: {e}")
        traceback.print_exc()
    finally:
        print("Main: Entering __main__'s finally block.")
        if app is not None:
            if not app._is_closed:
                print("Main: App not marked as closed, calling app.on_closing() to ensure cleanup.")
                try:
                    app.on_closing()
                except Exception as e_final_cleanup:
                    print(f"Main: Error during app.on_closing() from finally block: {e_final_cleanup}")
                    traceback.print_exc()
            else:
                print("Main: App already marked as closed by its on_closing method.")
        else:
            print("Main: App object is None.")
            try:
                if 'root' in locals() and isinstance(root, tk.Tk) and root.winfo_exists():
                    print("Main: App is None, attempting to destroy root window directly.")
                    root.destroy()
            except Exception as e_root_destroy:
                print(f"Main: Error destroying root window directly when app is None: {e_root_destroy}")
        print("Main: Application exit process complete.")