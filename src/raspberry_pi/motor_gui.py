import tkinter as tk
from tkinter import ttk
from datetime import datetime
import threading
import asyncio
from collections import deque

# Matplotlib (for graph placeholders + later real plots)
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Import BLE data collection
import main


APP_TITLE = "Motor Health Monitoring Dashboard"

# Professional color scheme
COLORS = {
    "primary": "#1e3a8a",      # Deep blue
    "secondary": "#3b82f6",    # Bright blue
    "success": "#10b981",      # Green
    "warning": "#f59e0b",      # Amber
    "danger": "#ef4444",       # Red
    "gray_light": "#f3f4f6",   # Light gray background
    "gray_medium": "#e5e7eb",  # Medium gray
    "gray_dark": "#6b7280",    # Dark gray text
    "white": "#ffffff",
    "text_primary": "#111827",
    "text_secondary": "#4b5563",
}


class MotorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1200x720")
        self.minsize(1050, 650)
        
        # Set background color
        self.configure(bg=COLORS["gray_light"])

        # Shared state (later: replace with RPi-fed values)
        self.motor_state = {
            "name": "Motor 1",
            "status": "Off",                # Off / Good / Fault / etc.
            "status_detail": "",            # e.g. "Configured for Heating" -> now maybe "Running Normally"
            "power_kw": None,               # float or None
            "configuration": "Cooling",     # placeholder field from your screenshot
        }
        
        # Data buffers for plotting (small buffers for low latency)
        MAX_ACCEL_TEMP = 30   # ~1 second of data at typical rates
        MAX_CURRENT = 100     # Enough to show Park's vector pattern
        self.data_buffers = {
            'accel_ts': deque(maxlen=MAX_ACCEL_TEMP),
            'accel_x': deque(maxlen=MAX_ACCEL_TEMP),
            'accel_y': deque(maxlen=MAX_ACCEL_TEMP),
            'accel_z': deque(maxlen=MAX_ACCEL_TEMP),
            'temp_ts': deque(maxlen=MAX_ACCEL_TEMP),
            'temp_vals': deque(maxlen=MAX_ACCEL_TEMP),
            'park_id': deque(maxlen=MAX_CURRENT),
            'park_iq': deque(maxlen=MAX_CURRENT),
            'filtered_id': deque(maxlen=MAX_CURRENT),
            'filtered_iq': deque(maxlen=MAX_CURRENT),
        }
        
        self.last_update = 0  # Throttle GUI updates to 60Hz

        # Configure ttk styles
        self._setup_styles()

        self.container = ttk.Frame(self, style="Container.TFrame")
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (DashboardPage, MotorDetailsPage):
            frame = F(parent=self.container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("DashboardPage")

        # Update clock in header areas
        self.after(200, self._tick)

        # Set this GUI as the target for BLE data updates
        main.gui_app = self
        
        # Start BLE connection in background thread
        self.ble_thread = threading.Thread(target=self._run_ble_loop, daemon=True)
        self.ble_thread.start()

    def _setup_styles(self):
        """Configure ttk styles for professional appearance"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Container/Frame styles
        style.configure("Container.TFrame", background=COLORS["gray_light"])
        style.configure("Header.TFrame", background=COLORS["white"])
        style.configure("Card.TFrame", background=COLORS["white"], borderwidth=2, relief="solid")
        
        # Label styles
        style.configure("Title.TLabel", 
                       background=COLORS["white"],
                       foreground=COLORS["primary"],
                       font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel",
                       background=COLORS["white"],
                       foreground=COLORS["text_secondary"],
                       font=("Segoe UI", 11))
        style.configure("CardTitle.TLabel",
                       background=COLORS["white"],
                       foreground=COLORS["text_primary"],
                       font=("Segoe UI", 18, "bold"))
        style.configure("InfoLabel.TLabel",
                       background=COLORS["white"],
                       foreground=COLORS["text_secondary"],
                       font=("Segoe UI", 11))
        style.configure("ValueLabel.TLabel",
                       background=COLORS["white"],
                       foreground=COLORS["text_primary"],
                       font=("Segoe UI", 13))
        style.configure("SectionLabel.TLabel",
                       background=COLORS["white"],
                       foreground=COLORS["text_primary"],
                       font=("Segoe UI", 12, "bold"))
        
        # Button styles
        style.configure("Primary.TButton",
                       font=("Segoe UI", 10, "bold"),
                       padding=(20, 10),
                       background=COLORS["secondary"])
        style.map("Primary.TButton",
                 background=[('active', COLORS["primary"])])

    def create_logo_canvas(self, parent):
        """
        Draw a lightweight NASA Ames badge on a canvas so we don't depend
        on external image files. Match parent background to keep it
        visually "transparent".
        """
        try:
            bg = parent.cget("background")
        except Exception:
            bg = "white"

        c = tk.Canvas(parent, width=86, height=54, bg=bg, highlightthickness=0, bd=0)
        # Blue circle
        c.create_oval(6, 6, 78, 48, fill="#0b3d91", outline="#0b3d91")
        # Red swoosh
        c.create_line(10, 36, 38, 18, 62, 30, 76, 16, smooth=True, fill="#d83939", width=3)
        # NASA text
        c.create_text(42, 22, text="NASA", fill="white", font=("Arial", 12, "bold"))
        c.create_text(42, 38, text="Ames", fill="white", font=("Arial", 9, "bold"))
        return c

    def show_frame(self, name: str):
        frame = self.frames[name]
        frame.tkraise()
        # Let page refresh itself when shown
        if hasattr(frame, "on_show"):
            frame.on_show()

    def _tick(self):
        now = datetime.now()
        for frame in self.frames.values():
            if hasattr(frame, "set_clock"):
                frame.set_clock(now)
        self.after(200, self._tick)

    # -----------------------------
    # RPi integration entry point
    # -----------------------------
    def update_from_rpi(self, data: dict):
        """
        Call this with data coming from the RPi.
        Example data payload:
        {
          "status": "Good",
          "status_detail": "Running",
          "power_kw": 1.23,
          "configuration": "Cooling",
          "park_id": [...],
          "park_iq": [...],
          "filtered_id": [...],
          "filtered_iq": [...],
          "accel_ts": [...],
          "accel_x": [...],
          "accel_y": [...],
          "accel_z": [...],
          "temp_ts": [...],
          "temp_vals": [...],
        }
        """
        # Update motor state fields if present
        for k in ("status", "status_detail", "power_kw", "configuration", "name"):
            if k in data:
                self.motor_state[k] = data[k]

        # Push plot data to details page if it exists
        details = self.frames["MotorDetailsPage"]
        if hasattr(details, "update_plots_from_data"):
            details.update_plots_from_data(data)

        # Refresh UI labels on visible pages
        for frame in self.frames.values():
            if hasattr(frame, "refresh"):
                frame.refresh()

    # -----------------------------
    # BLE Integration
    # -----------------------------
    def _run_ble_loop(self):
        """Run the BLE asyncio loop in a background thread"""
        try:
            asyncio.run(main.main())
        except Exception as e:
            print(f"BLE connection error: {e}")
    
    def add_data_point(self, timestamp, ax, ay, az, temp, ia, ib, ic, id, iq, filtered_id, filtered_iq):
        """
        Called directly from BLE callback with each new data point.
        Adds to buffers and updates GUI.
        """
        import time
        
        # Add to buffers
        self.data_buffers['accel_ts'].append(timestamp)
        self.data_buffers['accel_x'].append(ax)
        self.data_buffers['accel_y'].append(ay)
        self.data_buffers['accel_z'].append(az)
        self.data_buffers['temp_ts'].append(timestamp)
        self.data_buffers['temp_vals'].append(temp)
        self.data_buffers['park_id'].append(id)
        self.data_buffers['park_iq'].append(iq)
        self.data_buffers['filtered_id'].append(filtered_id)
        self.data_buffers['filtered_iq'].append(filtered_iq)
        
        # Update motor state
        if len(self.data_buffers['accel_x']) > 0:
            self.motor_state['status'] = 'Good'
            self.motor_state['status_detail'] = 'Running Normally'
        
        # 60Hz update rate for low latency (16.67ms between updates)
        current_time = time.time()
        if current_time - self.last_update > 0.0167:
            self.last_update = current_time
            self._update_plots()
    
    def _update_plots(self):
        """Update GUI with buffered data"""
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
        
        self.update_from_rpi(data)


class DashboardPage(ttk.Frame):
    def __init__(self, parent, controller: MotorApp):
        super().__init__(parent, style="Container.TFrame")
        self.controller = controller

        # Header with white background
        header = tk.Frame(self, bg=COLORS["white"], height=85)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        # Header content container
        header_content = tk.Frame(header, bg=COLORS["white"])
        header_content.pack(fill="both", expand=True, padx=24, pady=(15, 20))

        title = ttk.Label(header_content, text=APP_TITLE, style="Title.TLabel")
        title.pack(side="left")

        # NASA Ames logo on the absolute top-right (pack first to be rightmost)
        self.logo = controller.create_logo_canvas(header_content)
        self.logo.pack(side="right", padx=(0, 45))

        self.clock_lbl = ttk.Label(header_content, text="", style="Subtitle.TLabel")
        self.clock_lbl.pack(side="right", padx=(20, 45))

        # Body area
        body = ttk.Frame(self, style="Container.TFrame")
        body.pack(fill="both", expand=True, padx=24, pady=40)

        # Motor card (single motor) - centered with modern styling
        card_container = tk.Frame(body, bg=COLORS["white"], 
                                 highlightbackground=COLORS["gray_medium"],
                                 highlightthickness=1)
        card_container.pack(anchor="center", pady=(80, 0))
        
        self.card = tk.Frame(card_container, bg=COLORS["white"], padx=40, pady=35)
        self.card.pack()

        # Motor name with icon
        name_frame = tk.Frame(self.card, bg=COLORS["white"])
        name_frame.pack(fill="x", pady=(0, 20))
        
        name = tk.Label(name_frame, 
                       text=self.controller.motor_state["name"], 
                       font=("Segoe UI", 20, "bold"),
                       bg=COLORS["white"],
                       fg=COLORS["text_primary"])
        name.pack(side="left")

        # Status badge
        self.status_badge = tk.Label(name_frame, 
                                     text="●",
                                     font=("Segoe UI", 16),
                                     bg=COLORS["white"],
                                     fg=COLORS["gray_dark"])
        self.status_badge.pack(side="left", padx=(10, 0))

        # Motor icon - larger and more prominent
        icon_frame = tk.Frame(self.card, bg=COLORS["gray_light"], 
                             highlightbackground=COLORS["gray_medium"],
                             highlightthickness=1)
        icon_frame.pack(pady=(10, 20))
        
        self.icon = tk.Canvas(icon_frame, width=160, height=120, 
                            bg=COLORS["gray_light"], 
                            highlightthickness=0, bd=0)
        self.icon.pack(padx=20, pady=20)
        self._draw_motor_icon(self.icon)
        self.icon.bind("<Button-1>", self._go_details)
        self.icon.configure(cursor="hand2")

        # Info section with better spacing
        info_frame = tk.Frame(self.card, bg=COLORS["white"])
        info_frame.pack(fill="x", pady=(10, 20))

        # Status
        status_container = tk.Frame(info_frame, bg=COLORS["white"])
        status_container.pack(fill="x", pady=(0, 12))
        
        tk.Label(status_container, 
                text="STATUS",
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["white"],
                fg=COLORS["gray_dark"]).pack(anchor="w")
        
        self.status_lbl = tk.Label(status_container, 
                                   text="-",
                                   font=("Segoe UI", 13),
                                   bg=COLORS["white"],
                                   fg=COLORS["text_primary"])
        self.status_lbl.pack(anchor="w", pady=(4, 0))

        # Power consumption
        power_container = tk.Frame(info_frame, bg=COLORS["white"])
        power_container.pack(fill="x")
        
        tk.Label(power_container, 
                text="POWER CONSUMPTION",
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["white"],
                fg=COLORS["gray_dark"]).pack(anchor="w")
        
        self.power_lbl = tk.Label(power_container, 
                                  text="-",
                                  font=("Segoe UI", 13),
                                  bg=COLORS["white"],
                                  fg=COLORS["text_primary"])
        self.power_lbl.pack(anchor="w", pady=(4, 0))

        # More info button - styled as primary button
        btn_frame = tk.Frame(self.card, bg=COLORS["white"])
        btn_frame.pack(pady=(10, 0))
        
        self.more_btn = tk.Button(btn_frame,
                                  text="View Detailed Analysis →",
                                  command=self._go_details,
                                  font=("Segoe UI", 11, "bold"),
                                  bg=COLORS["gray_light"],
                                  fg=COLORS["secondary"],
                                  activebackground=COLORS["secondary"],
                                  activeforeground=COLORS["white"],
                                  relief="flat",
                                  padx=30,
                                  pady=12,
                                  cursor="hand2",
                                  borderwidth=0)
        self.more_btn.pack()

        self.refresh()

    def _draw_motor_icon(self, c: tk.Canvas):
        # Enhanced motor glyph with better proportions
        c.delete("all")
        
        # Draw with better colors
        color = COLORS["primary"]
        accent = COLORS["secondary"]
        
        # body
        c.create_rectangle(25, 30, 105, 90, outline=color, width=3, fill=COLORS["white"])
        # end cap
        c.create_rectangle(105, 42, 135, 78, outline=color, width=3, fill=COLORS["white"])
        # shaft
        c.create_line(135, 60, 155, 60, fill=accent, width=4)
        # vents
        for x in (38, 52, 66, 80, 94):
            c.create_line(x, 38, x, 82, fill=accent, width=2)
        # base
        c.create_line(25, 90, 115, 90, fill=color, width=4)
        c.create_line(35, 98, 105, 98, fill=color, width=4)
        
        # Label
        c.create_text(80, 16, text="MOTOR", font=("Segoe UI", 11, "bold"), fill=color)

    def _go_details(self, _event=None):
        self.controller.show_frame("MotorDetailsPage")

    def set_clock(self, now: datetime):
        self.clock_lbl.config(text=now.strftime("%I:%M %p  |  %b %d, %Y"))

    def refresh(self):
        st = self.controller.motor_state
        
        # Update status with color coding
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


class MotorDetailsPage(ttk.Frame):
    def __init__(self, parent, controller: MotorApp):
        super().__init__(parent, style="Container.TFrame")
        self.controller = controller
        
        # State for acceleration plot domain (True = frequency, False = time)
        self.accel_freq_domain = False
        self.accel_data_cache = {}  # Cache for toggling between domains

        # Header with white background
        header = tk.Frame(self, bg=COLORS["white"], height=85)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        # Header content container
        header_content = tk.Frame(header, bg=COLORS["white"])
        header_content.pack(fill="both", expand=True, padx=24, pady=(15, 20))

        # Back button
        back = tk.Button(header_content,
                        text="← Back",
                        command=lambda: controller.show_frame("DashboardPage"),
                        font=("Segoe UI", 10),
                        bg=COLORS["white"],
                        fg=COLORS["secondary"],
                        activebackground=COLORS["gray_light"],
                        activeforeground=COLORS["primary"],
                        relief="flat",
                        cursor="hand2",
                        borderwidth=0,
                        padx=15,
                        pady=8)
        back.pack(side="left")

        self.title_lbl = tk.Label(header_content, 
                                  text="Motor Details",
                                  font=("Segoe UI", 20, "bold"),
                                  bg=COLORS["white"],
                                  fg=COLORS["primary"])
        self.title_lbl.pack(side="left", padx=15)

        # NASA Ames logo on the absolute top-right (pack first to be rightmost)
        self.logo = controller.create_logo_canvas(header_content)
        self.logo.pack(side="right", padx=(0, 45))

        self.clock_lbl = tk.Label(header_content, 
                                  text="",
                                  font=("Segoe UI", 11),
                                  bg=COLORS["white"],
                                  fg=COLORS["text_secondary"])
        self.clock_lbl.pack(side="right", padx=(20, 45))

        # Layout: left info panel + right plots
        main = ttk.Frame(self, style="Container.TFrame")
        main.pack(fill="both", expand=True, padx=24, pady=(0, 55))

        # Left panel - info card
        left_card = tk.Frame(main, bg=COLORS["white"],
                           highlightbackground=COLORS["gray_medium"],
                           highlightthickness=1)
        left_card.pack(side="left", fill="y", padx=(0, 20))
        
        self.left = tk.Frame(left_card, bg=COLORS["white"], padx=24, pady=24)
        self.left.pack(fill="both", expand=True)

        # Status section
        tk.Label(self.left, 
                text="STATUS",
                font=("Segoe UI", 10, "bold"),
                bg=COLORS["white"],
                fg=COLORS["gray_dark"]).pack(anchor="w", pady=(0, 8))
        
        self.status_bar = tk.Label(self.left, 
                                  text="-",
                                  font=("Segoe UI", 12, "bold"),
                                  bg=COLORS["gray_light"],
                                  fg=COLORS["text_primary"],
                                  anchor="center",
                                  padx=20,
                                  pady=12,
                                  width=28)
        self.status_bar.pack(anchor="w", pady=(0, 20))

        # Power section
        tk.Label(self.left, 
                text="POWER CONSUMPTION",
                font=("Segoe UI", 10, "bold"),
                bg=COLORS["white"],
                fg=COLORS["gray_dark"]).pack(anchor="w", pady=(0, 8))
        
        self.power_lbl = tk.Label(self.left, 
                                 text="-",
                                 font=("Segoe UI", 12),
                                 bg=COLORS["white"],
                                 fg=COLORS["text_primary"])
        self.power_lbl.pack(anchor="w", pady=(0, 20))

        # Configuration section
        tk.Label(self.left, 
                text="CONFIGURATION",
                font=("Segoe UI", 10, "bold"),
                bg=COLORS["white"],
                fg=COLORS["gray_dark"]).pack(anchor="w", pady=(0, 8))
        
        self.config_lbl = tk.Label(self.left, 
                                  text="-",
                                  font=("Segoe UI", 12),
                                  bg=COLORS["white"],
                                  fg=COLORS["text_primary"])
        self.config_lbl.pack(anchor="w", pady=(0, 25))

        # Separator line
        tk.Frame(self.left, height=1, bg=COLORS["gray_medium"]).pack(fill="x", pady=15)

        # Help section
        tk.Label(self.left, 
                text="ABOUT",
                font=("Segoe UI", 10, "bold"),
                bg=COLORS["white"],
                fg=COLORS["gray_dark"]).pack(anchor="w", pady=(0, 8))
        
        help_txt = (
            "Real-time motor health monitoring using advanced signal processing.\n\n"
            "• Park's Vector: Current signature analysis\n"
            "• Filtered Pattern: Fault detection\n"
            "• Acceleration: X, Y, Z vibration data\n"
            "• Temperature: Thermal monitoring"
        )
        tk.Label(self.left, 
                text=help_txt,
                wraplength=280,
                justify="left",
                font=("Segoe UI", 10),
                bg=COLORS["white"],
                fg=COLORS["text_secondary"]).pack(anchor="w")

        # Right panel: 2x2 plot grid
        self.right = ttk.Frame(main, style="Container.TFrame")
        self.right.pack(side="left", fill="both", expand=True)

        grid = ttk.Frame(self.right, style="Container.TFrame")
        grid.pack(fill="both", expand=True)

        self.fig1, self.ax1, self.canvas1 = self._make_plot(grid, "Park's Vector Pattern", 0, 0)
        self.fig2, self.ax2, self.canvas2 = self._make_plot(grid, "Filtered Park's Vector Pattern", 0, 1)
        self.fig3, self.ax3, self.canvas3, self.accel_toggle_btn = self._make_accel_plot(grid, 1, 0)
        self.fig4, self.ax4, self.canvas4 = self._make_plot(grid, "Temperature Over Time", 1, 1)

        # Initial placeholder visuals
        self._placeholder_plots()
        self.refresh()

    def _make_plot(self, parent, title, r, c):
        # Card container for plot
        card = tk.Frame(parent, bg=COLORS["white"],
                       highlightbackground=COLORS["gray_medium"],
                       highlightthickness=1)
        card.grid(row=r, column=c, sticky="nsew", padx=8, pady=8)
        parent.rowconfigure(r, weight=1)
        parent.columnconfigure(c, weight=1)
        
        frame = tk.Frame(card, bg=COLORS["white"], padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        fig = Figure(figsize=(4.8, 3.2), dpi=100, facecolor=COLORS["white"])
        ax = fig.add_subplot(111)
        ax.set_title(title, fontsize=11, fontweight='bold', color=COLORS["text_primary"], pad=10)
        ax.set_facecolor(COLORS["gray_light"])
        
        # Adjust layout to ensure x-axis labels are visible
        fig.subplots_adjust(bottom=0.22, top=0.88, left=0.12, right=0.92)

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)

        return fig, ax, canvas

    def _make_accel_plot(self, parent, r, c):
        # Card container for plot with toggle button
        card = tk.Frame(parent, bg=COLORS["white"],
                       highlightbackground=COLORS["gray_medium"],
                       highlightthickness=1)
        card.grid(row=r, column=c, sticky="nsew", padx=8, pady=8)
        parent.rowconfigure(r, weight=1)
        parent.columnconfigure(c, weight=1)
        
        # Header with toggle button
        header_frame = tk.Frame(card, bg=COLORS["white"])
        header_frame.pack(fill="x", padx=12, pady=(12, 0))
        
        toggle_btn = tk.Button(header_frame,
                              text="⇄ Frequency Domain",
                              command=self._toggle_accel_domain,
                              font=("Segoe UI", 9),
                              bg=COLORS["gray_light"],
                              fg=COLORS["secondary"],
                              activebackground=COLORS["secondary"],
                              activeforeground=COLORS["white"],
                              relief="flat",
                              padx=10,
                              pady=4,
                              cursor="hand2",
                              borderwidth=0)
        toggle_btn.pack(side="right")
        
        frame = tk.Frame(card, bg=COLORS["white"])
        frame.pack(fill="both", expand=True, padx=12, pady=(6, 12))

        fig = Figure(figsize=(4.8, 3.2), dpi=100, facecolor=COLORS["white"])
        ax = fig.add_subplot(111)
        ax.set_title("Acceleration Data (X, Y, Z)", fontsize=11, fontweight='bold', 
                    color=COLORS["text_primary"], pad=10)
        ax.set_facecolor(COLORS["gray_light"])
        
        # Adjust layout to ensure x-axis labels are visible
        fig.subplots_adjust(bottom=0.22, top=0.88, left=0.12, right=0.92)

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)

        return fig, ax, canvas, toggle_btn

    def _toggle_accel_domain(self):
        """Toggle between time and frequency domain for acceleration plot"""
        self.accel_freq_domain = not self.accel_freq_domain
        
        if self.accel_freq_domain:
            self.accel_toggle_btn.config(text="⇄ Time Domain")
        else:
            self.accel_toggle_btn.config(text="⇄ Frequency Domain")
        
        # Replot with cached data
        if self.accel_data_cache:
            self._plot_accel_data(self.accel_data_cache)

    def _plot_accel_data(self, data):
        """Plot acceleration data in either time or frequency domain"""
        self.ax3.clear()
        
        if self.accel_freq_domain:
            # Frequency domain (FFT)
            import numpy as np
            
            # Compute FFT for each axis
            ts = data["accel_ts"]
            dt = ts[1] - ts[0] if len(ts) > 1 else 0.01
            
            fft_x = np.fft.rfft(data["accel_x"])
            fft_y = np.fft.rfft(data["accel_y"])
            fft_z = np.fft.rfft(data["accel_z"])
            
            freqs = np.fft.rfftfreq(len(data["accel_x"]), dt)
            
            # Plot magnitude
            self.ax3.set_title("Acceleration Spectrum (X, Y, Z)", fontsize=11, fontweight='bold',
                             color=COLORS["text_primary"], pad=10)
            self.ax3.plot(freqs, np.abs(fft_x), 
                         linewidth=1.5, color="#ef4444", label="X-axis", alpha=0.8)
            self.ax3.plot(freqs, np.abs(fft_y), 
                         linewidth=1.5, color="#10b981", label="Y-axis", alpha=0.8)
            self.ax3.plot(freqs, np.abs(fft_z), 
                         linewidth=1.5, color="#3b82f6", label="Z-axis", alpha=0.8)
            self.ax3.set_xlabel("frequency (Hz)", fontsize=9, color=COLORS["text_secondary"])
            self.ax3.set_ylabel("magnitude", fontsize=9, color=COLORS["text_secondary"])
        else:
            # Time domain
            self.ax3.set_title("Acceleration Data (X, Y, Z)", fontsize=11, fontweight='bold',
                             color=COLORS["text_primary"], pad=10)
            self.ax3.plot(data["accel_ts"], data["accel_x"], 
                         linewidth=1.5, color="#ef4444", label="X-axis", alpha=0.8)
            self.ax3.plot(data["accel_ts"], data["accel_y"], 
                         linewidth=1.5, color="#10b981", label="Y-axis", alpha=0.8)
            self.ax3.plot(data["accel_ts"], data["accel_z"], 
                         linewidth=1.5, color="#3b82f6", label="Z-axis", alpha=0.8)
            self.ax3.set_xlabel("time (s)", fontsize=9, color=COLORS["text_secondary"])
            self.ax3.set_ylabel("acceleration (g)", fontsize=9, color=COLORS["text_secondary"])
        
        self.ax3.set_facecolor(COLORS["gray_light"])
        self.ax3.legend(loc="upper right", fontsize=8, framealpha=0.9)
        self.ax3.grid(True, alpha=0.2, color=COLORS["gray_dark"])
        self.ax3.tick_params(colors=COLORS["text_secondary"], labelsize=8)
        self.canvas3.draw()

    def _placeholder_plots(self):
        # Simple placeholders so the page isn't empty
        for ax in (self.ax1, self.ax2, self.ax3, self.ax4):
            ax.clear()
            ax.set_title(ax.get_title(), fontsize=11, fontweight='bold', 
                        color=COLORS["text_primary"], pad=10)
            ax.set_facecolor(COLORS["gray_light"])
            ax.text(0.5, 0.5, "Waiting for RPi data…", 
                   ha="center", va="center", 
                   transform=ax.transAxes,
                   fontsize=10,
                   color=COLORS["text_secondary"])
            ax.grid(True, alpha=0.2, color=COLORS["gray_dark"])

        self.canvas1.draw()
        self.canvas2.draw()
        self.canvas3.draw()
        self.canvas4.draw()

    def set_clock(self, now: datetime):
        self.clock_lbl.config(text=now.strftime("%I:%M %p  |  %b %d, %Y"))

    def on_show(self):
        self.refresh()

    def refresh(self):
        st = self.controller.motor_state
        self.title_lbl.config(text=f"{st['name']} Details")

        # status bar color
        status = st["status"]
        if status == "Good":
            bg = COLORS["success"]
            fg = COLORS["white"]
        elif status == "Fault":
            bg = COLORS["danger"]
            fg = COLORS["white"]
        else:
            bg = COLORS["gray_light"]
            fg = COLORS["text_primary"]

        label_text = status + (f" — {st['status_detail']}" if st["status_detail"] else "")
        self.status_bar.config(text=label_text, bg=bg, fg=fg)

        if st["power_kw"] is None:
            self.power_lbl.config(text="—")
        else:
            self.power_lbl.config(text=f"{st['power_kw']} kW")

        self.config_lbl.config(text=st["configuration"])

    def update_plots_from_data(self, data: dict):
        """
        Update plots if RPi provides data arrays.
        Expected keys (optional):
          park_id, park_iq
          filtered_id, filtered_iq
          accel_ts, accel_x, accel_y, accel_z
          temp_ts, temp_vals
        """
        updated_any = False

        if "park_id" in data and "park_iq" in data:
            self.ax1.clear()
            self.ax1.set_title("Park's Vector Pattern", fontsize=11, fontweight='bold',
                             color=COLORS["text_primary"], pad=10)
            self.ax1.set_facecolor(COLORS["gray_light"])
            self.ax1.plot(data["park_id"], data["park_iq"], 
                         linewidth=1.5, color=COLORS["secondary"])
            self.ax1.set_xlabel("id", fontsize=9, color=COLORS["text_secondary"])
            self.ax1.set_ylabel("iq", fontsize=9, color=COLORS["text_secondary"])
            self.ax1.grid(True, alpha=0.2, color=COLORS["gray_dark"])
            self.ax1.tick_params(colors=COLORS["text_secondary"], labelsize=8)
            self.canvas1.draw()
            updated_any = True

        if "filtered_id" in data and "filtered_iq" in data:
            self.ax2.clear()
            self.ax2.set_title("Filtered Park's Vector Pattern", fontsize=11, fontweight='bold',
                             color=COLORS["text_primary"], pad=10)
            self.ax2.set_facecolor(COLORS["gray_light"])
            self.ax2.plot(data["filtered_id"], data["filtered_iq"], 
                         linewidth=1.5, color=COLORS["secondary"])
            # optional threshold circle placeholder
            try:
                from matplotlib.patches import Circle
                circ = Circle((0, 0), 0.08, fill=False, linewidth=1.5, 
                            edgecolor=COLORS["danger"], linestyle='--')
                self.ax2.add_patch(circ)
            except Exception:
                pass
            self.ax2.set_xlabel("filtered id", fontsize=9, color=COLORS["text_secondary"])
            self.ax2.set_ylabel("filtered iq", fontsize=9, color=COLORS["text_secondary"])
            self.ax2.grid(True, alpha=0.2, color=COLORS["gray_dark"])
            self.ax2.tick_params(colors=COLORS["text_secondary"], labelsize=8)
            self.canvas2.draw()
            updated_any = True

        # Acceleration data (X, Y, Z)
        if "accel_ts" in data and "accel_x" in data and "accel_y" in data and "accel_z" in data:
            # Cache the data for domain toggling
            self.accel_data_cache = {
                "accel_ts": data["accel_ts"],
                "accel_x": data["accel_x"],
                "accel_y": data["accel_y"],
                "accel_z": data["accel_z"]
            }
            self._plot_accel_data(self.accel_data_cache)
            updated_any = True

        # Temperature over time
        if "temp_ts" in data and "temp_vals" in data:
            self.ax4.clear()
            self.ax4.set_title("Temperature Over Time", fontsize=11, fontweight='bold',
                             color=COLORS["text_primary"], pad=10)
            self.ax4.set_facecolor(COLORS["gray_light"])
            self.ax4.plot(data["temp_ts"], data["temp_vals"], 
                         linewidth=2, color="#f59e0b")
            self.ax4.fill_between(data["temp_ts"], data["temp_vals"], 
                                 alpha=0.3, color="#f59e0b")
            self.ax4.set_xlabel("time (s)", fontsize=9, color=COLORS["text_secondary"])
            self.ax4.set_ylabel("temperature (°C)", fontsize=9, color=COLORS["text_secondary"])
            self.ax4.grid(True, alpha=0.2, color=COLORS["gray_dark"])
            self.ax4.tick_params(colors=COLORS["text_secondary"], labelsize=8)
            self.canvas4.draw()
            updated_any = True

        if not updated_any:
            # If the RPi payload didn't include plots, keep placeholders
            pass


if __name__ == "__main__":
    app = MotorApp()
    app.mainloop()