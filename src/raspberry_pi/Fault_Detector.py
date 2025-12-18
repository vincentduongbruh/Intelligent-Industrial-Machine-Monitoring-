import numpy as np
import scipy.signal as signal
from scipy.interpolate import interp1d
from scipy.optimize import curve_fit


class MotorFaultDetector:
    def __init__(self, fs_target=3600, f0_target=60): # replicating the frequencies described in Isak's paper
        self.fs_target = fs_target
        self.f0_target = f0_target

        # 1. Elliptic Low-Pass: Order 5, Ripple 40dB, Stop 84dB, Cutoff 430Hz
        self.ellip_b, self.ellip_a = signal.ellip(5, 40, 84, 430, btype='lowpass', fs=self.fs_target)
        
        # 2. Notch Filter: 60Hz, Q=1
        self.notch_b, self.notch_a = signal.iirnotch(60, Q=1, fs=self.fs_target)

    # def upsample_data(self, time, ia, ib, ic, target_fs):
    #     duration = time[-1] - time[0]
    #     num_points = int(duration * target_fs)
    #     new_time = np.linspace(time[0], time[-1], num_points)
        
    #     # 2. Create interpolation functions
    #     # 'cubic' fits a smooth curve, which mimics sine waves better than 'linear'
    #     # 'linear' would just draw straight lines between your jagged points
    #     f_ia = interp1d(time, ia, kind='cubic', fill_value="extrapolate")
    #     f_ib = interp1d(time, ib, kind='cubic', fill_value="extrapolate")
    #     f_ic = interp1d(time, ic, kind='cubic', fill_value="extrapolate")
        
    #     # 3. Generate new data
    #     new_ia = f_ia(new_time)
    #     new_ib = f_ib(new_time)
    #     new_ic = f_ic(new_time)
        
    #     return new_time, new_ia, new_ib, new_ic

    def compute_park_vector(self, ia, ib, ic):
        # Assuming ia, ib, ic are numpy arrays
        i_d = (np.sqrt(2/3) * ia) - (ib / np.sqrt(6)) - (ic / np.sqrt(6))
        i_q = (ib / np.sqrt(2)) - (ic / np.sqrt(2))
        return i_d, i_q

    def scale_trajectory(self, i_d, i_q):
        # Calculate distance from origin for every point
        r = np.sqrt(i_d**2 + i_q**2)
        r_mean = np.mean(r)
        
        if r_mean == 0:
            return i_d, i_q

        # Scale
        i_d_scaled = i_d / r_mean
        i_q_scaled = i_q / r_mean
        
        return i_d_scaled, i_q_scaled

    def apply_odt(self, values, fs_original, f0_detected):
        # # 1. Estimate fundamental frequency (f0) using FFT peak detection [cite: 426]
        # # Use a window to reduce spectral leakage
        # window = signal.windows.hann(len(values))
        # fft_vals = np.fft.rfft(values * window)
        # fft_freq = np.fft.rfftfreq(len(values), d=1/fs_original)
        
        # # Find peak frequency (ignore DC component at index 0)
        # peak_idx = np.argmax(np.abs(fft_vals[1:])) + 1
        # f0_detected = fft_freq[peak_idx]

        # if f0_detected <= 0:
        #     return values # Fallback

        # f0_detected = 50

        # 2. Calculate number of periods T (Eq 3.8) [cite: 430]
        N = len(values)
        T = (N * f0_detected) / fs_original

        # 3. Calculate target length S (Eq 3.9) [cite: 432]
        S = int((self.fs_target * T) / self.f0_target)

        # 4. Interpolate (Eq 3.10) [cite: 438]
        x_old = np.linspace(0, 1, N)
        x_new = np.linspace(0, 1, S)
        
        interpolator = interp1d(x_old, values, kind='linear')
        return interpolator(x_new)

    def apply_filters(self, data):
        # Apply Elliptic
        filtered_1 = signal.lfilter(self.ellip_b, self.ellip_a, data)
        # Apply Notch
        filtered_final = signal.lfilter(self.notch_b, self.notch_a, filtered_1)
        return filtered_final
    
    def process_pipeline_minimal(self, ia, ib, ic):
        id, iq = self.compute_park_vector(ia, ib, ic)
        return self.scale_trajectory(id, iq)
    
    def process_park_vector(self, ia, ib, ic):
        return self.compute_park_vector(ia, ib, ic)

    def process_pipeline(self, ia, ib, ic, fs_original, f0_detected):
        # Step 2: Calculate Id, Iq
        id_raw, iq_raw = self.compute_park_vector(ia, ib, ic)
        
        # Step 3: Scaling
        id_scaled, iq_scaled = self.scale_trajectory(id_raw, iq_raw)
        
        # Step 4: ODT (Process Id and Iq separately)
        id_odt = self.apply_odt(id_scaled, fs_original, f0_detected)
        iq_odt = self.apply_odt(iq_scaled, fs_original, f0_detected)
        
        # Step 5: Filter
        id_final = self.apply_filters(id_odt)
        iq_final = self.apply_filters(iq_odt)
        
        return id_final, iq_final
    
    def least_squares_v1(self, ia, ib, ic):
        id_raw, iq_raw = self.compute_park_vector(ia, ib, ic)

        id_scaled, iq_scaled = self.scale_trajectory(id_raw, iq_raw)

        PVM = np.sqrt(id_scaled ** 2 + iq_scaled ** 2)

        healthy = 1.0

        mse = np.mean((PVM - healthy) ** 2)

        return mse