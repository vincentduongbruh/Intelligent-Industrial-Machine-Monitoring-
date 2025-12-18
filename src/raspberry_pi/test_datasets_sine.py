import pandas as pd
import matplotlib.pyplot as plt
import scipy
from Fault_Detector import MotorFaultDetector
from SineCurveFitter import sine_model, fit_sine_wave
import numpy as np

BOUSHABA_DATASET = "../datasets/boushaba/ccs0.csv" 

# sampling = 16 ms
# 62.5 Hz - fundamental frequency
# 136k Hz

# 60 Hz AC wave, 120 degree shift for each phase


def main():
    # 1. Load Data
    print("Loading dataset...")
    columns = ["s", "ia", "ib", "ic", "va", "vb", "vc", "rad/s", "rad"]
    df = pd.read_csv(BOUSHABA_DATASET, names=columns)
    print(df)

    middle = (len(df) // 2) - 1
    low = middle - round(len(df) * 0.325)
    high = middle + round(len(df) * 0.325)

    df = df[low:high]

    t = df["s"].values
    ia = df['ia'].values
    ib = df['ib'].values
    ic = df['ic'].values

    # 2. Initialize Detector
    detector = MotorFaultDetector()

    print(f"Attempting to fit sine wave with guess freq: 60 Hz...")
    params_ia = fit_sine_wave(t, ia, 60)
    params_ib = fit_sine_wave(t, ib, 60)
    params_ic = fit_sine_wave(t, ic, 60)

    if params_ia is None:
        return
    if params_ib is None:
        return
    if params_ic is None:
        return
    
    fit_amp, fit_freq, fit_phase, fit_offset = params_ia
    print(f"\n--- Fit Results for Ia ---")
    print(f"Amplitude: {fit_amp:.4f} A")
    print(f"Frequency: {abs(fit_freq):.4f} Hz") # Freq might come out negative, just take abs
    print(f"DC Offset: {fit_offset:.4f} A")

    # 3. Generate the smooth reconstruction
    # Create a dense time vector (e.g., 1000 points over the same duration)
    t_smooth = np.linspace(t.min(), t.max(), 1000)
    # Use the fitted parameters to generate the clean sine wave
    ia_smooth = sine_model(t_smooth, fit_amp, fit_freq, fit_phase, fit_offset)

    fit_amp, fit_freq, fit_phase, fit_offset = params_ib
    print(f"\n--- Fit Results for Ib ---")
    print(f"Amplitude: {fit_amp:.4f} A")
    print(f"Frequency: {abs(fit_freq):.4f} Hz") # Freq might come out negative, just take abs
    print(f"DC Offset: {fit_offset:.4f} A")
    ib_smooth = sine_model(t_smooth, fit_amp, fit_freq, fit_phase, fit_offset)

    fit_amp, fit_freq, fit_phase, fit_offset = params_ic
    print(f"\n--- Fit Results for Ic ---")
    print(f"Amplitude: {fit_amp:.4f} A")
    print(f"Frequency: {abs(fit_freq):.4f} Hz") # Freq might come out negative, just take abs
    print(f"DC Offset: {fit_offset:.4f} A")
    ic_smooth = sine_model(t_smooth, fit_amp, fit_freq, fit_phase, fit_offset)

    id_initial, iq_initial = detector.process_pipeline_minimal(ia_smooth, ib_smooth, ic_smooth)

    plt.figure(figsize=(6, 6))
    plt.plot(t_smooth, ia_smooth, 'o')
    # plt.plot(id_initial, iq_initial, linewidth=0.5)
    plt.xlabel("t")
    plt.ylabel("i_a")
    plt.grid(True)
    # plt.axis("equal")
    plt.axis("tight")
    plt.show()

    plt.figure(figsize=(6, 6))
    plt.plot(t_smooth, ib_smooth, 'o')
    # plt.plot(id_initial, iq_initial, linewidth=0.5)
    plt.xlabel("t")
    plt.ylabel("i_b")
    plt.grid(True)
    # plt.axis("equal")
    plt.axis("tight")
    plt.show()

    plt.figure(figsize=(6, 6))
    plt.plot(t_smooth, ic_smooth, 'o')
    # plt.plot(id_initial, iq_initial, linewidth=0.5)
    plt.xlabel("t")
    plt.ylabel("i_c")
    plt.grid(True)
    # plt.axis("equal")
    plt.axis("tight")
    plt.show()

    plt.figure(figsize=(6, 6))
    # plt.plot(id_initial, iq_initial, 'o')
    plt.plot(id_initial, iq_initial, linewidth=0.5)
    plt.title("Filtered Park's Vector Pattern")
    plt.xlabel("i_d")
    plt.ylabel("i_q")
    plt.grid(True)
    # plt.axis("equal")
    plt.axis("tight")
    plt.show()

if __name__ == "__main__":
    main()