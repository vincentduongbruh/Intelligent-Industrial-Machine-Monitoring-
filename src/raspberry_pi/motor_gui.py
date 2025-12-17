"""
Motor Health Monitoring Dashboard GUI
=====================================
This GUI displays real-time motor health data from ESP32 via Bluetooth.

ARCHITECTURE:
1. MotorApp: Main application that manages pages and receives BLE data
2. DashboardPage: Overview page showing motor status
3. MotorDetailsPage: Detailed page with 4 real-time plots

DATA FLOW:
ESP32 (BLE) → main.py callback → MotorApp.add_data_point() → buffers → plots
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
import threading
import asyncio
import time
from collections import deque
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

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
MAX_ACCEL_TEMP_POINTS = 30   # ~1 second of data
MAX_CURRENT_POINTS = 100     # Enough to show Park's vector pattern


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

        # Motor state (updated from BLE data)
        self.motor_state = {
            "name": "Motor 1",
            "status": "Off",           # Off / Good / Fault
            "status_detail": "",       # Additional status info
            "power_kw": None,          # Power consumption
            "configuration": "Cooling" # Motor configuration
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
            # Park's vector (longer buffer for pattern)
            'park_id': deque(maxlen=MAX_CURRENT_POINTS),
            'park_iq': deque(maxlen=MAX_CURRENT_POINTS),
            'filtered_id': deque(maxlen=MAX_CURRENT_POINTS),
            'filtered_iq': deque(maxlen=MAX_CURRENT_POINTS),
        }
        
        self.last_update = 0  # For 60Hz throttling

        # Setup UI
        self._setup_styles()
        self._create_pages()
        
        # Start periodic updates
        self.after(200, self._tick_clock)
        
        # Connect to BLE data source
        main.gui_app = self  # Register this GUI with BLE handler
        self.ble_thread = threading.Thread(target=self._run_ble_loop, daemon=True)
        self.ble_thread.start()

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
            asyncio.run(main.main())
        except Exception as e:
            print(f"BLE connection error: {e}")
    
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
        # Schedule on main GUI thread for thread safety
        self.after(0, self._process_data_point, 
                   timestamp, ax, ay, az, temp, ia, ib, ic,
                   id_val, iq_val, filtered_id, filtered_iq)
    
    def _process_data_point(self, timestamp, ax, ay, az, temp, ia, ib, ic,
                            id_val, iq_val, filtered_id, filtered_iq):
        """Process incoming data point on main GUI thread"""
        
        # Add data to buffers (deque auto-removes old data)
        self.data_buffers['accel_ts'].append(timestamp)
        self.data_buffers['accel_x'].append(ax)
        self.data_buffers['accel_y'].append(ay)
        self.data_buffers['accel_z'].append(az)
        self.data_buffers['temp_ts'].append(timestamp)
        self.data_buffers['temp_vals'].append(temp)
        self.data_buffers['park_id'].append(id_val)
        self.data_buffers['park_iq'].append(iq_val)
        self.data_buffers['filtered_id'].append(filtered_id)
        self.data_buffers['filtered_iq'].append(filtered_iq)
        
        # Update motor status
        if len(self.data_buffers['accel_x']) > 0:
            self.motor_state['status'] = 'Good'
            self.motor_state['status_detail'] = 'Running Normally'
        
        # Update plots at 60Hz (throttle to avoid GUI lag)
        current_time = time.time()
        if current_time - self.last_update > 0.0167:  # 16.67ms = 60Hz
            self.last_update = current_time
            self._update_plots()
    
    def _update_plots(self):
        """Push buffered data to plots"""
        # Convert deques to lists for plotting
        data = {
            'park_id': list(self.data_buffers['park_id']),
            'park_iq': list(self.data_buffers['park_iq']),
            'filtered_id': list(self.data_buffers['filtered_id']),
            'filtered_iq': list(self.data_buffers['filtered_iq']),
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

    # ------------------------------------------------------------------------
    # HELPER: NASA Logo
    # ------------------------------------------------------------------------

    def create_nasa_logo(self, parent):
        """Draw NASA Ames logo on canvas"""
        try:
            bg = parent.cget("background")
        except:
            bg = "white"
        
        canvas = tk.Canvas(parent, width=86, height=54, bg=bg, 
                          highlightthickness=0, bd=0)
        canvas.create_oval(6, 6, 78, 48, fill="#0b3d91", outline="#0b3d91")
        canvas.create_line(10, 36, 38, 18, 62, 30, 76, 16, 
                          smooth=True, fill="#d83939", width=3)
        canvas.create_text(42, 22, text="NASA", fill="white", 
                          font=("Arial", 12, "bold"))
        canvas.create_text(42, 38, text="Ames", fill="white", 
                          font=("Arial", 9, "bold"))
        return canvas


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
    1. Park's Vector Pattern (id vs iq)
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
        
        # Separator
        tk.Frame(panel, height=1, bg=COLORS["gray_medium"]).pack(fill="x", pady=15)
        
        # About section
        self._add_info_label(panel, "ABOUT")
        help_text = (
            "Real-time motor health monitoring.\n\n"
            "• Park's Vector: Current signature\n"
            "• Filtered Pattern: Fault detection\n"
            "• Acceleration: Vibration (X, Y, Z)\n"
            "• Temperature: Thermal monitoring"
        )
        tk.Label(panel, text=help_text, wraplength=280, justify="left",
                font=("Segoe UI", 10), bg=COLORS["white"],
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
        self.fig1, self.ax1, self.canvas1 = \
            self._make_plot(grid, "Park's Vector Pattern", 0, 0)
        
        self.fig2, self.ax2, self.canvas2 = \
            self._make_plot(grid, "Filtered Park's Vector Pattern", 0, 1)
        
        self.fig3, self.ax3, self.canvas3, self.accel_toggle_btn = \
            self._make_accel_plot(grid, 1, 0)
        
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
        for ax in (self.ax1, self.ax2, self.ax3, self.ax4):
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
        - park_id, park_iq: Park's vector components
        - filtered_id, filtered_iq: Filtered Park's vector
        - accel_ts, accel_x, accel_y, accel_z: Acceleration data
        - temp_ts, temp_vals: Temperature data
        """
        
        # Plot 1: Park's Vector Pattern
        if "park_id" in data and "park_iq" in data:
            self._update_parks_vector_plot(data)
        
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

    def _update_parks_vector_plot(self, data):
        """Update Park's vector plot (id vs iq)"""
        self.ax1.clear()
        self.ax1.set_title("Park's Vector Pattern", fontsize=11, 
                          fontweight='bold', color=COLORS["primary"], pad=10)
        self.ax1.set_facecolor(COLORS["gray_light"])
        self.ax1.plot(data["park_id"], data["park_iq"],
                     linewidth=1.5, color=COLORS["secondary"])
        self.ax1.set_xlabel("id", fontsize=9, color=COLORS["gray_dark"])
        self.ax1.set_ylabel("iq", fontsize=9, color=COLORS["gray_dark"])
        self.ax1.grid(True, alpha=0.2, color=COLORS["gray_dark"])
        self.ax1.tick_params(colors=COLORS["gray_dark"], labelsize=8)
        self.canvas1.draw()

    def _update_filtered_parks_plot(self, data):
        """Update filtered Park's vector plot with fault threshold"""
        self.ax2.clear()
        self.ax2.set_title("Filtered Park's Vector Pattern", fontsize=11,
                          fontweight='bold', color=COLORS["primary"], pad=10)
        self.ax2.set_facecolor(COLORS["gray_light"])
        self.ax2.plot(data["filtered_id"], data["filtered_iq"],
                     linewidth=1.5, color=COLORS["secondary"])
        
        # Draw fault threshold circle
        try:
            from matplotlib.patches import Circle
            circle = Circle((0, 0), 0.08, fill=False, linewidth=1.5,
                          edgecolor=COLORS["danger"], linestyle='--')
            self.ax2.add_patch(circle)
        except:
            pass
        
        self.ax2.set_xlabel("filtered id", fontsize=9, color=COLORS["gray_dark"])
        self.ax2.set_ylabel("filtered iq", fontsize=9, color=COLORS["gray_dark"])
        self.ax2.grid(True, alpha=0.2, color=COLORS["gray_dark"])
        self.ax2.tick_params(colors=COLORS["gray_dark"], labelsize=8)
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
        self.ax4.set_xlabel("time (s)", fontsize=9, color=COLORS["gray_dark"])
        self.ax4.set_ylabel("temperature (°C)", fontsize=9, color=COLORS["gray_dark"])
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


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    app = MotorApp()
    app.mainloop()
