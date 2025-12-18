import numpy as np
import scipy.signal as signal
from scipy.interpolate import interp1d
from scipy.optimize import curve_fit

def sine_model(t, amp, freq_hz, phase_rad, offset):
    """
    The mathematical model we are forcing the data to fit.
    t: time vector
    amp: Amplitude (half peak-to-peak)
    freq_hz: Frequency in Hertz
    phase_rad: Phase shift in radians
    offset: DC offset (vertical shift)
    """
    return amp * np.sin(2 * np.pi * freq_hz * t + phase_rad) + offset
    
def fit_sine_wave(t_data, y_data, freq_guess):
    """
    Performs the curve fitting on a single phase.
    """
    # 1. Generate initial parameter guesses (crucial for success)
    guess_offset = np.mean(y_data)
    # Estimate amplitude from max/min
    guess_amp = (np.max(y_data) - np.min(y_data)) / 2
    guess_phase = 0
    
    # Pack guesses: [amp, freq, phase, offset]
    p0 = [guess_amp, freq_guess, guess_phase, guess_offset]

    try:
        # 2. Run the optimization
        # curve_fit tries to minimize the squared difference between the model and the data
        params, covariance = curve_fit(sine_model, t_data, y_data, p0=p0, maxfev=10000)
        return params
    except RuntimeError:
        print("Error: Curve fit failed to converge. Check initial frequency guess.")
        return None