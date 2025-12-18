"""
Motor Health Monitoring Dashboard GUI
=====================================
This GUI displays real-time motor health data from ESP32 via Bluetooth.

ARCHITECTURE:
1. MotorApp: Main application that manages pages and receives BLE data
2. DashboardPage: Overview page showing motor status
3. MotorDetailsPage: Detailed page with 4 real-time plots

DATA FLOW:
ESP32 (BLE) → main.py callback → MotorFaultDetector (filtering) → 
MotorApp.add_data_point() → buffers → plots

FILTERING:
- Raw Park's Vector: Computed directly from 3-phase currents (ia, ib, ic)
- Filtered Park's Vector: Scaled Park's vector trajectory (no ODT)
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
import threading
import asyncio
import time
import queue
from collections import deque
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
import math

# Import BLE handler
import main

# ============================================================================
# CONFIGURATION
# ============================================================================

APP_TITLE = "Motor Health Monitoring Dashboard"

# Color scheme for professional UI
COLORS = {
    "primary": "#1e3a8a",      # Deep blue
    "secondary": "#3b82f6",    # Bright blue
    "success": "#10b981",      # Green (motor running well)
    "danger": "#ef4444",       # Red (motor fault)
    "gray_light": "#f3f4f6",   # Light gray background
    "gray_medium": "#e5e7eb",  # Medium gray borders
    "gray_dark": "#6b7280",    # Dark gray text
    "white": "#ffffff",
}

# Buffer sizes for real-time plotting
# Larger accel/temp buffer so x-axis shows a longer window
MAX_ACCEL_TEMP_POINTS = 300  # ~10 seconds of data (depending on sample rate)
MAX_CURRENT_POINTS = 100     # Enough to show Park's vector pattern
ROOM_TEMP_C = 25.0           # Baseline room temperature for warnings
TEMP_WARN_DELTA_C = 5.0      # Warn if above room + this delta (more sensitive)
TEMP_WARN_HYST_C = 1.0       # Hysteresis to avoid rapid toggling
LOGO_MAX_W = 110             # Max logo width (px) to keep it compact in header
LOGO_MAX_H = 60              # Max logo height (px)
ACCEL_RUN_MAG_THRESHOLD = 0.05  # g threshold to consider motor running
ACCEL_BASELINE_SAMPLES = 60     # samples used to learn baseline once running
ACCEL_WINDOW_SAMPLES = 60       # samples for current RMS window
ACCEL_SIGMA_MULTIPLIER = 2.0    # sensitivity for vibration threshold (lower = more sensitive)
ACCEL_FLOOR_G = 0.01            # minimum extra g above baseline to trigger warning


# ============================================================================
# MAIN APPLICATION CLASS
# ============================================================================

class MotorApp(tk.Tk):
    """
    Main GUI application for motor monitoring.
    
    RESPONSIBILITIES:
    - Manages pages (Dashboard and Details)
    - Receives data from BLE (via main.py)
    - Maintains data buffers for plotting
    - Updates plots at 60Hz for low latency
    """
    
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1200x720")
        self.minsize(1050, 650)
        self.configure(bg=COLORS["gray_light"])
        self._asset_dir = os.path.join(os.path.dirname(__file__), "assets")
        self._nasa_logo_img = None
        # Vibration monitoring state
        self._accel_mag_buf = deque(maxlen=ACCEL_WINDOW_SAMPLES * 3)
        self._vibe_baseline_ready = False
        self._vibe_baseline_mean = 0.0
        self._vibe_baseline_std = 0.0
        self._vibe_consec_high = 0
        self._vibe_consec_clear = 0
        # Warning history
        self._warning_history = deque(maxlen=100)
        self._temp_warning_active = False

        # Motor state (updated from BLE data)
        self.motor_state = {
            "name": "Motor 1",
            "status": "Off",           # Off / Good / Fault
            "status_detail": "",       # Additional status info
            "power_kw": None,          # Power consumption
            "configuration": "Cooling",# Motor configuration
            "warning": ""              # Warning message for UI
        }
        
        # Data buffers (deque auto-removes old data when full)
        self.data_buffers = {
            # Acceleration and temperature (short buffer)
            'accel_ts': deque(maxlen=MAX_ACCEL_TEMP_POINTS),
            'accel_x': deque(maxlen=MAX_ACCEL_TEMP_POINTS),
            'accel_y': deque(maxlen=MAX_ACCEL_TEMP_POINTS),
            'accel_z': deque(maxlen=MAX_ACCEL_TEMP_POINTS),
            'temp_ts': deque(maxlen=MAX_ACCEL_TEMP_POINTS),
            'temp_vals': deque(maxlen=MAX_ACCEL_TEMP_POINTS),
            # 3-phase currents (for time-domain plot)
            'current_ts': deque(maxlen=MAX_CURRENT_POINTS),
            'ia': deque(maxlen=MAX_CURRENT_POINTS),
            'ib': deque(maxlen=MAX_CURRENT_POINTS),
            'ic': deque(maxlen=MAX_CURRENT_POINTS),
            # Filtered Park's vector (longer buffer for pattern)
            'filtered_id': deque(maxlen=MAX_CURRENT_POINTS),
            'filtered_iq': deque(maxlen=MAX_CURRENT_POINTS),
        }
        
        # Thread-safe ingress for high-rate data coming from BLE callback thread.
        # We poll and drain this queue on the Tk thread to avoid Tkinter cross-thread calls.
        self._incoming = queue.Queue()
        self._poll_interval_ms = 5  # lower = lower latency (more CPU). 5ms ~= 200Hz poll.

        # Setup UI
        self._setup_styles()
        self._create_pages()
        
        # Start periodic updates
        self.after(200, self._tick_clock)
        self.after(self._poll_interval_ms, self._poll_incoming)
        
        # Start UART current reader (main.py keeps latest values in latest_currents)
        # motor_gui.py must start this, because main.run_data_acquisition() only runs BLE.
        self._serial = None
        self._serial_stop_event = threading.Event()
        self._serial_thread = None
        try:
            if hasattr(main, "open_serial") and hasattr(main, "serial_reader_loop"):
                self._serial = main.open_serial(main.SERIAL_PORT, main.BAUDRATE)
                self._serial_thread = threading.Thread(
                    target=main.serial_reader_loop,
                    args=(self._serial, self._serial_stop_event),
                    daemon=True,
                )
                self._serial_thread.start()
        except Exception as e:
            print(f"Serial init error: {e}")

        # Register this GUI instance so main.py can push data into the plots
        main.gui_app = self
        self.ble_thread = threading.Thread(target=self._run_ble_loop, daemon=True)
        self.ble_thread.start()
        
        # Handle window close event
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ------------------------------------------------------------------------
    # UI SETUP
    # ------------------------------------------------------------------------

    def _setup_styles(self):
        """Configure ttk widget styles"""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Container.TFrame", background=COLORS["gray_light"])

    def _create_pages(self):
        """Create and stack the dashboard and details pages"""
        self.container = ttk.Frame(self, style="Container.TFrame")
        self.container.pack(fill="both", expand=True)

        # Create both pages and stack them
        self.frames = {}
        for PageClass in (DashboardPage, MotorDetailsPage):
            frame = PageClass(parent=self.container, controller=self)
            self.frames[PageClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Show dashboard by default
        self.show_frame("DashboardPage")

    def show_frame(self, page_name):
        """Switch to a different page"""
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()

    # ------------------------------------------------------------------------
    # PERIODIC UPDATES
    # ------------------------------------------------------------------------

    def _tick_clock(self):
        """Update clock displays on all pages (called every 200ms)"""
        now = datetime.now()
        for frame in self.frames.values():
            if hasattr(frame, "set_clock"):
                frame.set_clock(now)
        self.after(200, self._tick_clock)

    # ------------------------------------------------------------------------
    # BLE DATA INTEGRATION
    # ------------------------------------------------------------------------

    def _run_ble_loop(self):
        """Run BLE connection in background thread"""
        try:
            main.run_data_acquisition()
        except Exception as e:
            print(f"BLE connection error: {e}")
    
    def _on_closing(self):
        """Handle window close event - clean up BLE connection"""
        print("Closing application...")
        # Stop UART reader
        try:
            self._serial_stop_event.set()
            if self._serial is not None:
                self._serial.close()
        except Exception:
            pass

        # Unregister GUI from main.py
        main.gui_app = None
        # Destroy window
        self.destroy()
    
    def add_data_point(self, timestamp, ax, ay, az, temp, ia, ib, ic, 
                       id_val, iq_val, filtered_id, filtered_iq):
        """
        Called by BLE callback (main.py) with each new data point.
        Thread-safe: schedules processing on main GUI thread.
        
        PARAMETERS:
        - timestamp: Time in seconds since start
        - ax, ay, az: Acceleration X, Y, Z (in g)
        - temp: Temperature (in °C)
        - ia, ib, ic: 3-phase currents (in A)
        - id_val, iq_val: Park's vector components
        - filtered_id, filtered_iq: Filtered Park's vector
        """
        # Called from BLE callback thread. Do NOT touch Tk here.
        try:
            self._incoming.put_nowait(
                (timestamp, ax, ay, az, temp, ia, ib, ic, id_val, iq_val, filtered_id, filtered_iq)
            )
        except Exception:
            # If queueing fails, drop the sample (prefer freshness over backlog).
            pass

    def _poll_incoming(self):
        """
        Drain queued samples and update plots.
        Runs on the Tk main thread on a short timer to minimize latency.
        """
        drained_any = False
        latest = None
        processed = 0

        # Drain all queued samples and update buffers for each.
        while True:
            try:
                item = self._incoming.get_nowait()
            except queue.Empty:
                break

            drained_any = True
            latest = item
            self._process_data_point(*item)
            processed += 1

            # If the queue explodes (GUI can't keep up), drop older samples and keep freshness.
            if processed > 500:
                while True:
                    try:
                        latest = self._incoming.get_nowait()
                    except queue.Empty:
                        break
                if latest is not None:
                    self._process_data_point(*latest)
                break

        # Redraw once per poll cycle to prevent backlog / lag.
        if drained_any:
            self._update_plots()

        self.after(self._poll_interval_ms, self._poll_incoming)
    
    def _process_data_point(self, timestamp, ax, ay, az, temp, ia, ib, ic,
                            id_val, iq_val, filtered_id, filtered_iq):
        """Process incoming data point on main GUI thread"""
        warnings = []

        # Add data to buffers (deque auto-removes old data)
        self.data_buffers['accel_ts'].append(timestamp)
        self.data_buffers['accel_x'].append(ax)
        self.data_buffers['accel_y'].append(ay)
        self.data_buffers['accel_z'].append(az)
        self.data_buffers['temp_ts'].append(timestamp)
        self.data_buffers['temp_vals'].append(temp)
        # Add 3-phase currents for time-domain plot
        self.data_buffers['current_ts'].append(timestamp)
        self.data_buffers['ia'].append(ia)
        self.data_buffers['ib'].append(ib)
        self.data_buffers['ic'].append(ic)
        # Add filtered Park's vector
        self.data_buffers['filtered_id'].append(filtered_id)
        self.data_buffers['filtered_iq'].append(filtered_iq)
        
        # Update motor status
        if len(self.data_buffers['accel_x']) > 0:
            self.motor_state['status'] = 'Good'
            self.motor_state['status_detail'] = 'Running Normally'

        # Update warning if temperature is above threshold
        temp_threshold = ROOM_TEMP_C + TEMP_WARN_DELTA_C
        if temp > temp_threshold:
            if not self._temp_warning_active:
                warnings.append(
                    f"High temperature detected: {temp:.1f}°C "
                    f"(>{temp_threshold:.0f}°C threshold)"
                )
                self._temp_warning_active = True
        elif temp < temp_threshold - TEMP_WARN_HYST_C:
            self._temp_warning_active = False

        # --- Vibration (acceleration) monitoring ---
        accel_mag = math.sqrt(ax * ax + ay * ay + az * az)
        self._accel_mag_buf.append(accel_mag)

        # Learn baseline when the motor is clearly running
        if not self._vibe_baseline_ready:
            if len(self._accel_mag_buf) >= ACCEL_BASELINE_SAMPLES:
                recent = list(self._accel_mag_buf)[-ACCEL_BASELINE_SAMPLES:]
                rms_recent = math.sqrt(sum(m * m for m in recent) / len(recent))
                if rms_recent > ACCEL_RUN_MAG_THRESHOLD:
                    mean_recent = sum(recent) / len(recent)
                    var_recent = sum((m - mean_recent) ** 2 for m in recent) / len(recent)
                    std_recent = math.sqrt(var_recent)
                    self._vibe_baseline_mean = mean_recent
                    self._vibe_baseline_std = max(std_recent, 1e-6)
                    self._vibe_baseline_ready = True
                    self._vibe_consec_high = 0
                    self._vibe_consec_clear = 0
        else:
            if len(self._accel_mag_buf) >= ACCEL_WINDOW_SAMPLES:
                window = list(self._accel_mag_buf)[-ACCEL_WINDOW_SAMPLES:]
                rms_window = math.sqrt(sum(m * m for m in window) / len(window))

                # Threshold: baseline + N·σ (with a small floor), tuned for higher sensitivity
                threshold = self._vibe_baseline_mean + max(ACCEL_FLOOR_G, ACCEL_SIGMA_MULTIPLIER * self._vibe_baseline_std)

                if rms_window > threshold:
                    self._vibe_consec_high += 1
                    self._vibe_consec_clear = 0
                else:
                    self._vibe_consec_clear += 1
                    self._vibe_consec_high = 0

                if self._vibe_consec_high >= 3:
                    warnings.append(
                        f"High vibration: RMS {rms_window:.3f} g "
                        f"(baseline {self._vibe_baseline_mean:.3f} g)"
                    )

                # If vibration falls well below run threshold for a while, reset baseline (motor likely off)
                if self._vibe_consec_clear >= 20 and rms_window < ACCEL_RUN_MAG_THRESHOLD / 2:
                    self._vibe_baseline_ready = False
                    self._vibe_consec_high = 0
                    self._vibe_consec_clear = 0

        # Record warnings with timestamps so they persist in UI
        if warnings:
            for msg in warnings:
                self._add_warning_event(msg)
        self.motor_state["warning"] = " | ".join(warnings)
    
    def _update_plots(self):
        """Push buffered data to plots"""
        # Convert deques to lists for plotting
        data = {
            # 3-phase currents over time
            'current_ts': list(self.data_buffers['current_ts']),
            'ia': list(self.data_buffers['ia']),
            'ib': list(self.data_buffers['ib']),
            'ic': list(self.data_buffers['ic']),
            # Filtered Park's vector
            'filtered_id': list(self.data_buffers['filtered_id']),
            'filtered_iq': list(self.data_buffers['filtered_iq']),
            # Acceleration and temperature
            'accel_ts': list(self.data_buffers['accel_ts']),
            'accel_x': list(self.data_buffers['accel_x']),
            'accel_y': list(self.data_buffers['accel_y']),
            'accel_z': list(self.data_buffers['accel_z']),
            'temp_ts': list(self.data_buffers['temp_ts']),
            'temp_vals': list(self.data_buffers['temp_vals']),
        }
        
        # Update plots on details page
        details = self.frames["MotorDetailsPage"]
        if hasattr(details, "update_plots_from_data"):
            details.update_plots_from_data(data)
        
        # Refresh status labels
        for frame in self.frames.values():
            if hasattr(frame, "refresh"):
                frame.refresh()

    def _add_warning_event(self, message: str):
        """Store warning with timestamp for UI display"""
        now = datetime.now().strftime("%I:%M:%S %p")
        self._warning_history.append((now, message))

    # ------------------------------------------------------------------------
    # HELPER: NASA Logo
    # ------------------------------------------------------------------------

    def create_nasa_logo(self, parent):
        """Load NASA logo from assets (scaled down to fit header)"""
        logo_path = os.path.join(self._asset_dir, "nasalogo.png")
        if os.path.exists(logo_path):
            # Keep a reference to prevent garbage collection
            img = tk.PhotoImage(file=logo_path)

            # Downscale if larger than our max bounds
            try:
                w, h = img.width(), img.height()
                if w > LOGO_MAX_W or h > LOGO_MAX_H:
                    factor = max(w / LOGO_MAX_W, h / LOGO_MAX_H)
                    factor = max(1, math.ceil(factor))
                    img = img.subsample(factor, factor)
            except Exception:
                pass

            self._nasa_logo_img = img
            lbl = tk.Label(parent, image=self._nasa_logo_img, bg=parent.cget("background"))
            return lbl
        else:
            # Fallback: text placeholder if asset missing
            return tk.Label(parent, text="NASA Ames", bg=parent.cget("background"), fg=COLORS["primary"])


# ============================================================================
# DASHBOARD PAGE (Overview)
# ============================================================================

class DashboardPage(ttk.Frame):
    """
    Main overview page showing motor status card.
    Click "View Detailed Analysis" to see plots.
    """
    
    def __init__(self, parent, controller: MotorApp):
        super().__init__(parent, style="Container.TFrame")
        self.controller = controller
        
        # Create header
        self._create_header()
        
        # Create motor status card
        self._create_motor_card()
        
        self.refresh()

    def _create_header(self):
        """Create header with title, clock, and logo"""
        header = tk.Frame(self, bg=COLORS["white"], height=85)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        content = tk.Frame(header, bg=COLORS["white"])
        content.pack(fill="both", expand=True, padx=24, pady=(15, 20))
        
        # Title
        tk.Label(content, text=APP_TITLE, 
                font=("Segoe UI", 22, "bold"),
                bg=COLORS["white"], 
                fg=COLORS["primary"]).pack(side="left")
        
        # Logo (rightmost)
        self.logo = self.controller.create_nasa_logo(content)
        self.logo.pack(side="right", padx=(0, 45))
        
        # Clock
        self.clock_lbl = tk.Label(content, text="", 
                                  font=("Segoe UI", 11),
                                  bg=COLORS["white"], 
                                  fg=COLORS["gray_dark"])
        self.clock_lbl.pack(side="right", padx=(20, 45))

    def _create_motor_card(self):
        """Create centered motor status card"""
        body = ttk.Frame(self, style="Container.TFrame")
        body.pack(fill="both", expand=True, padx=24, pady=40)
        
        # Card container
        card_container = tk.Frame(body, bg=COLORS["white"],
                                 highlightbackground=COLORS["gray_medium"],
                                 highlightthickness=1)
        card_container.pack(anchor="center", pady=(80, 0))
        
        card = tk.Frame(card_container, bg=COLORS["white"], padx=40, pady=35)
        card.pack()
        
        # Motor name and status badge
        name_frame = tk.Frame(card, bg=COLORS["white"])
        name_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(name_frame, 
                text=self.controller.motor_state["name"],
                font=("Segoe UI", 20, "bold"),
                bg=COLORS["white"],
                fg=COLORS["primary"]).pack(side="left")
        
        self.status_badge = tk.Label(name_frame, text="●",
                                     font=("Segoe UI", 16),
                                     bg=COLORS["white"],
                                     fg=COLORS["gray_dark"])
        self.status_badge.pack(side="left", padx=(10, 0))
        
        # Motor icon
        self._create_motor_icon(card)
        
        # Status and power info
        self._create_info_section(card)
        
        # Details button
        btn = tk.Button(card, text="View Detailed Analysis →",
                       command=self._go_details,
                       font=("Segoe UI", 11, "bold"),
                       bg=COLORS["gray_light"],
                       fg=COLORS["secondary"],
                       activebackground=COLORS["secondary"],
                       activeforeground=COLORS["white"],
                       relief="flat", padx=30, pady=12,
                       cursor="hand2", borderwidth=0)
        btn.pack(pady=(10, 0))

    def _create_motor_icon(self, parent):
        """Draw motor icon"""
        icon_frame = tk.Frame(parent, bg=COLORS["gray_light"],
                             highlightbackground=COLORS["gray_medium"],
                             highlightthickness=1)
        icon_frame.pack(pady=(10, 20))
        
        canvas = tk.Canvas(icon_frame, width=160, height=120,
                          bg=COLORS["gray_light"],
                          highlightthickness=0, bd=0)
        canvas.pack(padx=20, pady=20)
        
        # Draw motor shape
        canvas.create_rectangle(25, 30, 105, 90, 
                               outline=COLORS["primary"], width=3, 
                               fill=COLORS["white"])
        canvas.create_rectangle(105, 42, 135, 78, 
                               outline=COLORS["primary"], width=3, 
                               fill=COLORS["white"])
        canvas.create_line(135, 60, 155, 60, 
                          fill=COLORS["secondary"], width=4)
        # Vents
        for x in (38, 52, 66, 80, 94):
            canvas.create_line(x, 38, x, 82, 
                             fill=COLORS["secondary"], width=2)
        # Base
        canvas.create_line(25, 90, 115, 90, 
                          fill=COLORS["primary"], width=4)
        canvas.create_text(80, 16, text="MOTOR", 
                          font=("Segoe UI", 11, "bold"), 
                          fill=COLORS["primary"])
        
        canvas.bind("<Button-1>", self._go_details)
        canvas.configure(cursor="hand2")

    def _create_info_section(self, parent):
        """Create status and power display"""
        info = tk.Frame(parent, bg=COLORS["white"])
        info.pack(fill="x", pady=(10, 20))
        
        # Status
        tk.Label(info, text="STATUS",
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["white"],
                fg=COLORS["gray_dark"]).pack(anchor="w")
        self.status_lbl = tk.Label(info, text="-",
                                   font=("Segoe UI", 13),
                                   bg=COLORS["white"],
                                   fg=COLORS["primary"])
        self.status_lbl.pack(anchor="w", pady=(4, 12))
        
        # Power
        tk.Label(info, text="POWER CONSUMPTION",
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["white"],
                fg=COLORS["gray_dark"]).pack(anchor="w")
        self.power_lbl = tk.Label(info, text="-",
                                  font=("Segoe UI", 13),
                                  bg=COLORS["white"],
                                  fg=COLORS["primary"])
        self.power_lbl.pack(anchor="w", pady=(4, 0))

    def _go_details(self, _event=None):
        """Navigate to details page"""
        self.controller.show_frame("MotorDetailsPage")

    def set_clock(self, now: datetime):
        """Update clock display"""
        self.clock_lbl.config(text=now.strftime("%I:%M %p  |  %b %d, %Y"))

    def refresh(self):
        """Update displayed values from motor_state"""
        st = self.controller.motor_state
        
        # Update status text
        status_text = st['status']
        if st["status_detail"]:
            status_text += f" — {st['status_detail']}"
        self.status_lbl.config(text=status_text)
        
        # Update status badge color
        if st['status'] == "Good":
            self.status_badge.config(fg=COLORS["success"])
        elif st['status'] == "Fault":
            self.status_badge.config(fg=COLORS["danger"])
        else:
            self.status_badge.config(fg=COLORS["gray_dark"])
        
        # Update power
        if st["power_kw"] is None:
            self.power_lbl.config(text="—")
        else:
            self.power_lbl.config(text=f"{st['power_kw']} kW")


# ============================================================================
# DETAILS PAGE (Plots)
# ============================================================================

class MotorDetailsPage(ttk.Frame):
    """
    Detailed view with 4 real-time plots:
    1. 3-Phase Currents (ia, ib, ic) over time
    2. Filtered Park's Vector Pattern (with fault threshold)
    3. Acceleration (X, Y, Z) - toggles between time/frequency domain
    4. Temperature over time
    """
    
    def __init__(self, parent, controller: MotorApp):
        super().__init__(parent, style="Container.TFrame")
        self.controller = controller
        
        # State for acceleration plot
        self.accel_freq_domain = False  # False = time, True = frequency
        self.accel_data_cache = {}      # For toggling domains
        
        # Create UI
        self._create_header()
        self._create_main_layout()
        
        # Show placeholders until data arrives
        self._show_placeholder_plots()
        self.refresh()

    # ------------------------------------------------------------------------
    # UI CREATION
    # ------------------------------------------------------------------------

    def _create_header(self):
        """Create header with back button, title, clock, logo"""
        header = tk.Frame(self, bg=COLORS["white"], height=85)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        content = tk.Frame(header, bg=COLORS["white"])
        content.pack(fill="both", expand=True, padx=24, pady=(15, 20))
        
        # Back button
        tk.Button(content, text="← Back",
                 command=lambda: self.controller.show_frame("DashboardPage"),
                 font=("Segoe UI", 10),
                 bg=COLORS["white"], fg=COLORS["secondary"],
                 activebackground=COLORS["gray_light"],
                 relief="flat", cursor="hand2",
                 borderwidth=0, padx=15, pady=8).pack(side="left")
        
        # Title
        self.title_lbl = tk.Label(content, text="Motor Details",
                                  font=("Segoe UI", 20, "bold"),
                                  bg=COLORS["white"],
                                  fg=COLORS["primary"])
        self.title_lbl.pack(side="left", padx=15)
        
        # Logo (rightmost)
        self.logo = self.controller.create_nasa_logo(content)
        self.logo.pack(side="right", padx=(0, 45))
        
        # Clock
        self.clock_lbl = tk.Label(content, text="",
                                  font=("Segoe UI", 11),
                                  bg=COLORS["white"],
                                  fg=COLORS["gray_dark"])
        self.clock_lbl.pack(side="right", padx=(20, 45))

    def _create_main_layout(self):
        """Create left info panel and right plot grid"""
        main = ttk.Frame(self, style="Container.TFrame")
        main.pack(fill="both", expand=True, padx=24, pady=(0, 55))
        
        # Left: Info panel
        self._create_info_panel(main)
        
        # Right: 2x2 plot grid
        self._create_plot_grid(main)

    def _create_info_panel(self, parent):
        """Create left side info panel"""
        card = tk.Frame(parent, bg=COLORS["white"],
                       highlightbackground=COLORS["gray_medium"],
                       highlightthickness=1)
        card.pack(side="left", fill="y", padx=(0, 20))
        
        panel = tk.Frame(card, bg=COLORS["white"], padx=24, pady=24)
        panel.pack(fill="both", expand=True)
        
        # Status
        self._add_info_label(panel, "STATUS")
        self.status_bar = tk.Label(panel, text="-",
                                   font=("Segoe UI", 12, "bold"),
                                   bg=COLORS["gray_light"],
                                   fg=COLORS["primary"],
                                   anchor="center", padx=20, pady=12, width=28)
        self.status_bar.pack(anchor="w", pady=(0, 20))
        
        # Power
        self._add_info_label(panel, "POWER CONSUMPTION")
        self.power_lbl = tk.Label(panel, text="-",
                                  font=("Segoe UI", 12),
                                  bg=COLORS["white"],
                                  fg=COLORS["primary"])
        self.power_lbl.pack(anchor="w", pady=(0, 20))
        
        # Configuration
        self._add_info_label(panel, "CONFIGURATION")
        self.config_lbl = tk.Label(panel, text="-",
                                   font=("Segoe UI", 12),
                                   bg=COLORS["white"],
                                   fg=COLORS["primary"])
        self.config_lbl.pack(anchor="w", pady=(0, 25))

        # Warning section
        self._add_info_label(panel, "WARNINGS")
        self.warning_lbl = tk.Label(panel, text="No active warnings",
                                    font=("Segoe UI", 10),
                                    bg=COLORS["gray_light"],
                                    fg=COLORS["danger"],
                                    wraplength=280, justify="left",
                                    padx=10, pady=10, anchor="w")
        self.warning_lbl.pack(fill="x", pady=(0, 20))
        
        # Separator
        tk.Frame(panel, height=1, bg=COLORS["gray_medium"]).pack(fill="x", pady=15)
        
        # About section
        self._add_info_label(panel, "ABOUT")
        help_text = (
            "Real-time motor health monitoring.\n\n"
            "• 3-Phase Currents: Raw ia, ib, ic waveforms over time\n"
            "• Filtered Park's Vector: Scaled Park's vector trajectory\n"
            "• Acceleration: Vibration data (X, Y, Z) in time or frequency domain\n"
            "• Temperature: Thermal monitoring over time"
        )
        tk.Label(panel, text=help_text, wraplength=280, justify="left",
                font=("Segoe UI", 9), bg=COLORS["white"],
                fg=COLORS["gray_dark"]).pack(anchor="w")

    def _add_info_label(self, parent, text):
        """Helper to create section label"""
        tk.Label(parent, text=text,
                font=("Segoe UI", 10, "bold"),
                bg=COLORS["white"],
                fg=COLORS["gray_dark"]).pack(anchor="w", pady=(0, 8))

    def _create_plot_grid(self, parent):
        """Create 2x2 grid of plots"""
        right = ttk.Frame(parent, style="Container.TFrame")
        right.pack(side="left", fill="both", expand=True)
        
        grid = ttk.Frame(right, style="Container.TFrame")
        grid.pack(fill="both", expand=True)
        
        # Create 4 plots
        # Top-left: 3-Phase Currents over Time
        self.fig1, self.ax1, self.canvas1 = \
            self._make_plot(grid, "3-Phase Currents (ia, ib, ic)", 0, 0)
        
        # Top-right: Filtered Park's Vector Pattern
        self.fig2, self.ax2, self.canvas2 = \
            self._make_plot(grid, "Filtered Park's Vector Pattern", 0, 1)
        
        # Bottom-left: Acceleration (with toggle)
        self.fig3, self.ax3, self.canvas3, self.accel_toggle_btn = \
            self._make_accel_plot(grid, 1, 0)
        
        # Bottom-right: Temperature
        self.fig4, self.ax4, self.canvas4 = \
            self._make_plot(grid, "Temperature Over Time", 1, 1)

    def _make_plot(self, parent, title, row, col):
        """Helper to create a standard plot"""
        # Card container
        card = tk.Frame(parent, bg=COLORS["white"],
                       highlightbackground=COLORS["gray_medium"],
                       highlightthickness=1)
        card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
        parent.rowconfigure(row, weight=1)
        parent.columnconfigure(col, weight=1)
        
        frame = tk.Frame(card, bg=COLORS["white"], padx=12, pady=12)
        frame.pack(fill="both", expand=True)
        
        # Create matplotlib figure
        fig = Figure(figsize=(4.8, 3.2), dpi=100, facecolor=COLORS["white"])
        ax = fig.add_subplot(111)
        ax.set_title(title, fontsize=11, fontweight='bold', 
                    color=COLORS["primary"], pad=10)
        ax.set_facecolor(COLORS["gray_light"])
        fig.subplots_adjust(bottom=0.22, top=0.88, left=0.12, right=0.92)
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
        return fig, ax, canvas

    def _make_accel_plot(self, parent, row, col):
        """Create acceleration plot with domain toggle button"""
        # Card container
        card = tk.Frame(parent, bg=COLORS["white"],
                       highlightbackground=COLORS["gray_medium"],
                       highlightthickness=1)
        card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
        parent.rowconfigure(row, weight=1)
        parent.columnconfigure(col, weight=1)
        
        # Header with toggle button
        header = tk.Frame(card, bg=COLORS["white"])
        header.pack(fill="x", padx=12, pady=(12, 0))
        
        toggle_btn = tk.Button(header, text="⇄ Frequency Domain",
                              command=self._toggle_accel_domain,
                              font=("Segoe UI", 9),
                              bg=COLORS["gray_light"],
                              fg=COLORS["secondary"],
                              activebackground=COLORS["secondary"],
                              activeforeground=COLORS["white"],
                              relief="flat", padx=10, pady=4,
                              cursor="hand2", borderwidth=0)
        toggle_btn.pack(side="right")
        
        # Plot frame
        frame = tk.Frame(card, bg=COLORS["white"])
        frame.pack(fill="both", expand=True, padx=12, pady=(6, 12))
        
        # Create matplotlib figure
        fig = Figure(figsize=(4.8, 3.2), dpi=100, facecolor=COLORS["white"])
        ax = fig.add_subplot(111)
        ax.set_title("Acceleration Data (X, Y, Z)", fontsize=11, 
                    fontweight='bold', color=COLORS["primary"], pad=10)
        ax.set_facecolor(COLORS["gray_light"])
        fig.subplots_adjust(bottom=0.22, top=0.88, left=0.12, right=0.92)
        
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
        return fig, ax, canvas, toggle_btn

    # ------------------------------------------------------------------------
    # PLOT UPDATES
    # ------------------------------------------------------------------------

    def _show_placeholder_plots(self):
        """Show 'Waiting for data...' message on all plots"""
        # Plot 1: 3-Phase Currents
        self.ax1.clear()
        self.ax1.set_title("3-Phase Currents (ia, ib, ic)", fontsize=11, 
                          fontweight='bold', color=COLORS["primary"], pad=10)
        self.ax1.set_facecolor(COLORS["gray_light"])
        self.ax1.text(0.5, 0.5, "Waiting for current data…",
                     ha="center", va="center", transform=self.ax1.transAxes,
                     fontsize=10, color=COLORS["gray_dark"])
        self.ax1.set_xlabel("time (s)", fontsize=9, color=COLORS["gray_dark"])
        self.ax1.set_ylabel("Current (A)", fontsize=9, color=COLORS["gray_dark"])
        self.ax1.grid(True, alpha=0.2, color=COLORS["gray_dark"])
        
        # Other plots
        for ax in (self.ax2, self.ax3, self.ax4):
            ax.clear()
            ax.set_facecolor(COLORS["gray_light"])
            ax.text(0.5, 0.5, "Waiting for data…",
                   ha="center", va="center", transform=ax.transAxes,
                   fontsize=10, color=COLORS["gray_dark"])
            ax.grid(True, alpha=0.2, color=COLORS["gray_dark"])
        
        self.canvas1.draw()
        self.canvas2.draw()
        self.canvas3.draw()
        self.canvas4.draw()

    def update_plots_from_data(self, data: dict):
        """
        Update all plots with new data from buffers.
        Called by MotorApp._update_plots() at 60Hz.
        
        EXPECTED DATA KEYS:
        - current_ts, ia, ib, ic: 3-phase currents
        - filtered_id, filtered_iq: Filtered Park's vector
        - accel_ts, accel_x, accel_y, accel_z: Acceleration data
        - temp_ts, temp_vals: Temperature data
        """
        
        # Plot 1: 3-Phase Currents over Time
        if all(k in data for k in ("current_ts", "ia", "ib", "ic")):
            self._update_currents_plot(data)
        
        # Plot 2: Filtered Park's Vector
        if "filtered_id" in data and "filtered_iq" in data:
            self._update_filtered_parks_plot(data)
        
        # Plot 3: Acceleration (time or frequency domain)
        if all(k in data for k in ("accel_ts", "accel_x", "accel_y", "accel_z")):
            self.accel_data_cache = {
                "accel_ts": data["accel_ts"],
                "accel_x": data["accel_x"],
                "accel_y": data["accel_y"],
                "accel_z": data["accel_z"]
            }
            self._plot_accel_data(self.accel_data_cache)
        
        # Plot 4: Temperature
        if "temp_ts" in data and "temp_vals" in data:
            self._update_temperature_plot(data)

    def _update_currents_plot(self, data):
        """Update 3-phase currents plot (ia, ib, ic vs time)"""
        self.ax1.clear()
        self.ax1.set_title("3-Phase Currents (ia, ib, ic)", fontsize=11, 
                          fontweight='bold', color=COLORS["primary"], pad=10)
        self.ax1.set_facecolor(COLORS["gray_light"])
        
        # Check if we have data
        if len(data["current_ts"]) > 0 and len(data["ia"]) > 0:
            # Plot all three phase currents
            self.ax1.plot(data["current_ts"], data["ia"],
                         linewidth=2, color="#ef4444", label="ia", alpha=0.9)
            self.ax1.plot(data["current_ts"], data["ib"],
                         linewidth=2, color="#10b981", label="ib", alpha=0.9)
            self.ax1.plot(data["current_ts"], data["ic"],
                         linewidth=2, color="#3b82f6", label="ic", alpha=0.9)
            
            self.ax1.legend(loc="upper right", fontsize=9, framealpha=0.9)
        else:
            self.ax1.text(0.5, 0.5, "Waiting for current data...",
                         ha="center", va="center", transform=self.ax1.transAxes,
                         fontsize=10, color=COLORS["gray_dark"])
        
        self.ax1.set_xlabel("time (s)", fontsize=9, color=COLORS["gray_dark"])
        self.ax1.set_ylabel("Current (A)", fontsize=9, color=COLORS["gray_dark"])
        #
        self.ax1.set_ylim(-3, 3)
        self.ax1.grid(True, alpha=0.2, color=COLORS["gray_dark"])
        self.ax1.tick_params(colors=COLORS["gray_dark"], labelsize=8)
        self.canvas1.draw()

    def _update_filtered_parks_plot(self, data):
        """
        Update filtered Park's vector plot with fault threshold.

        This plot shows the Park's vector trajectory after scaling (mean radius ~ 1).
        No ODT is applied.
        """
        self.ax2.clear()
        self.ax2.set_title("Filtered Park's Vector (Scaled Trajectory)", 
                          fontsize=10, fontweight='bold', 
                          color=COLORS["primary"], pad=10)
        self.ax2.set_facecolor(COLORS["gray_light"])
        self.ax2.plot(data["filtered_id"], data["filtered_iq"],
                     linewidth=1.5, color=COLORS["secondary"], alpha=0.8)
        
        # Draw fault threshold circle (centered at origin)
        try:
            from matplotlib.patches import Circle
            # After scaling, a healthy trajectory should be roughly radius ~1
            threshold_radius = 1.2
            circle = Circle((0, 0), threshold_radius, 
                          fill=False, linewidth=2,
                          edgecolor=COLORS["danger"], 
                          linestyle='--', 
                          label=f'Fault threshold (r={threshold_radius})')
            self.ax2.add_patch(circle)
            
            # Add origin marker
            self.ax2.plot(0, 0, 'r+', markersize=10, markeredgewidth=2)
            
        except Exception as e:
            print(f"Error drawing threshold: {e}")
        
        self.ax2.set_xlabel("filtered id", fontsize=9, color=COLORS["gray_dark"])
        self.ax2.set_ylabel("filtered iq", fontsize=9, color=COLORS["gray_dark"])
        self.ax2.grid(True, alpha=0.2, color=COLORS["gray_dark"])
        self.ax2.tick_params(colors=COLORS["gray_dark"], labelsize=8)
        
        # Set equal aspect ratio for circular pattern visibility
        self.ax2.set_aspect('equal', adjustable='datalim')
        
        self.canvas2.draw()

    def _plot_accel_data(self, data):
        """Plot acceleration in time or frequency domain"""
        self.ax3.clear()
        
        if self.accel_freq_domain:
            # FREQUENCY DOMAIN (FFT)
            import numpy as np
            
            ts = data["accel_ts"]
            dt = ts[1] - ts[0] if len(ts) > 1 else 0.01
            
            # Compute FFT for each axis
            fft_x = np.fft.rfft(data["accel_x"])
            fft_y = np.fft.rfft(data["accel_y"])
            fft_z = np.fft.rfft(data["accel_z"])
            freqs = np.fft.rfftfreq(len(data["accel_x"]), dt)
            
            # Plot magnitude spectrum
            self.ax3.set_title("Acceleration Spectrum (X, Y, Z)", fontsize=11,
                             fontweight='bold', color=COLORS["primary"], pad=10)
            self.ax3.plot(freqs, np.abs(fft_x), linewidth=1.5, 
                         color="#ef4444", label="X-axis", alpha=0.8)
            self.ax3.plot(freqs, np.abs(fft_y), linewidth=1.5,
                         color="#10b981", label="Y-axis", alpha=0.8)
            self.ax3.plot(freqs, np.abs(fft_z), linewidth=1.5,
                         color="#3b82f6", label="Z-axis", alpha=0.8)
            self.ax3.set_xlabel("frequency (Hz)", fontsize=9, color=COLORS["gray_dark"])
            self.ax3.set_ylabel("magnitude", fontsize=9, color=COLORS["gray_dark"])
        else:
            # TIME DOMAIN
            self.ax3.set_title("Acceleration Data (X, Y, Z)", fontsize=11,
                             fontweight='bold', color=COLORS["primary"], pad=10)
            self.ax3.plot(data["accel_ts"], data["accel_x"], linewidth=1.5,
                         color="#ef4444", label="X-axis", alpha=0.8)
            self.ax3.plot(data["accel_ts"], data["accel_y"], linewidth=1.5,
                         color="#10b981", label="Y-axis", alpha=0.8)
            self.ax3.plot(data["accel_ts"], data["accel_z"], linewidth=1.5,
                         color="#3b82f6", label="Z-axis", alpha=0.8)
            self.ax3.set_xlabel("time (s)", fontsize=9, color=COLORS["gray_dark"])
            self.ax3.set_ylabel("acceleration (g)", fontsize=9, color=COLORS["gray_dark"])
        
        self.ax3.set_facecolor(COLORS["gray_light"])
        self.ax3.legend(loc="upper right", fontsize=8, framealpha=0.9)
        self.ax3.grid(True, alpha=0.2, color=COLORS["gray_dark"])
        self.ax3.tick_params(colors=COLORS["gray_dark"], labelsize=8)
        self.canvas3.draw()

    def _update_temperature_plot(self, data):
        """Update temperature over time plot"""
        self.ax4.clear()
        self.ax4.set_title("Temperature Over Time", fontsize=11,
                          fontweight='bold', color=COLORS["primary"], pad=10)
        self.ax4.set_facecolor(COLORS["gray_light"])
        self.ax4.plot(data["temp_ts"], data["temp_vals"],
                     linewidth=2, color="#f59e0b")
        self.ax4.fill_between(data["temp_ts"], data["temp_vals"],
                             alpha=0.3, color="#f59e0b")
        # Danger threshold line
        temp_threshold = ROOM_TEMP_C + TEMP_WARN_DELTA_C
        self.ax4.axhline(temp_threshold, color=COLORS["danger"], linestyle="--",
                        linewidth=1.2, label=f"Threshold ({temp_threshold:.0f}°C)")
        self.ax4.set_xlabel("time (s)", fontsize=9, color=COLORS["gray_dark"])
        self.ax4.set_ylabel("temperature (°C)", fontsize=9, color=COLORS["gray_dark"])
        # Zoom y-axis around latest temp ±10°C for better detail
        if data["temp_vals"]:
            latest_temp = data["temp_vals"][-1]
            self.ax4.set_ylim(latest_temp - 10, latest_temp + 10)
        # Show legend for threshold
        self.ax4.legend(loc="upper right", fontsize=8, framealpha=0.9)
        self.ax4.grid(True, alpha=0.2, color=COLORS["gray_dark"])
        self.ax4.tick_params(colors=COLORS["gray_dark"], labelsize=8)
        self.canvas4.draw()

    def _toggle_accel_domain(self):
        """Toggle between time and frequency domain for acceleration"""
        self.accel_freq_domain = not self.accel_freq_domain
        
        # Update button text
        if self.accel_freq_domain:
            self.accel_toggle_btn.config(text="⇄ Time Domain")
        else:
            self.accel_toggle_btn.config(text="⇄ Frequency Domain")
        
        # Replot with cached data
        if self.accel_data_cache:
            self._plot_accel_data(self.accel_data_cache)

    # ------------------------------------------------------------------------
    # UI UPDATES
    # ------------------------------------------------------------------------

    def set_clock(self, now: datetime):
        """Update clock display"""
        self.clock_lbl.config(text=now.strftime("%I:%M %p  |  %b %d, %Y"))

    def on_show(self):
        """Called when page is shown"""
        self.refresh()

    def refresh(self):
        """Update status labels from motor_state"""
        st = self.controller.motor_state
        self.title_lbl.config(text=f"{st['name']} Details")
        
        # Update status bar with color
        status = st["status"]
        if status == "Good":
            bg, fg = COLORS["success"], COLORS["white"]
        elif status == "Fault":
            bg, fg = COLORS["danger"], COLORS["white"]
        else:
            bg, fg = COLORS["gray_light"], COLORS["primary"]
        
        label_text = status
        if st["status_detail"]:
            label_text += f" — {st['status_detail']}"
        self.status_bar.config(text=label_text, bg=bg, fg=fg)
        
        # Update power
        if st["power_kw"] is None:
            self.power_lbl.config(text="—")
        else:
            self.power_lbl.config(text=f"{st['power_kw']} kW")
        
        # Update configuration
        self.config_lbl.config(text=st["configuration"])

        # Update warning section
        active_warning = st.get("warning")
        if active_warning:
            self.warning_lbl.config(text=active_warning, bg=COLORS["gray_light"])
        elif self.controller._warning_history:
            ts, msg = self.controller._warning_history[-1]
            self.warning_lbl.config(
                text=f"Last warning @ {ts}: {msg}", bg=COLORS["white"]
            )
        else:
            self.warning_lbl.config(text="No warnings yet", bg=COLORS["white"])


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    app = MotorApp()
    app.mainloop()
