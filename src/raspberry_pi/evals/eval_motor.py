import pandas as pd
import matplotlib.pyplot as plt
import scipy
from fault import MotorFaultDetector

file_path = "experiment2.csv"

# sampling = 16 ms
# 62.5 Hz - fundamental frequency
# 136k Hz

# 60 Hz AC wave, 120 degree shift for each phase


def main():
    # 1. Load Data
    print("Loading dataset...")
    # columns = ["s", "ia", "ib", "ic", "va", "vb", "vc", "rad/s", "rad"]
    df = pd.read_csv(file_path)
    print(df)

    # middle = (len(df) // 2) - 1
    # low = middle - round(len(df) * 0.325)
    # high = middle + round(len(df) * 0.325)

    # df = df[low:high] # get the samples within 1 standard deviation of middle
    # print(df)

    time = df['time'].values
    ia = df['ia'].values
    ib = df['ib'].values
    ic = df['ic'].values

    print(f"time:{time}")
    print(f"ia:{ia}")
    print(f"ib:{ib}")
    print(f"ic:{ic}")

    # 2. Initialize Detector
    detector = MotorFaultDetector()


    # 3. Run Pipeline
    print("Processing data...")
    # id_final, iq_final = detector.process_pipeline(ia, ib, ic, BOUSHABA_FS_ORIGINAL, BOUSHABA_F0_DETECTED)
    id_initial, iq_initial = detector.process_pipeline_minimal(ia, ib, ic)
    # id_initial, iq_initial = detector.process_pipeline_minimal(ia_new, ib_new, ic_new)

    mse = detector.least_squares_v1(ia, ib, ic)
    print(f"Mean Squared Error: {mse}")

    plt.figure(figsize=(6, 6))
    plt.plot(time, ia, 'o')
    # plt.plot(id_initial, iq_initial, linewidth=0.5)
    plt.xlabel("t")
    plt.ylabel("i_a")
    plt.grid(True)
    # plt.axis("equal")
    plt.axis("tight")
    plt.show()

    plt.figure(figsize=(6, 6))
    plt.plot(time, ib, 'o')
    # plt.plot(id_initial, iq_initial, linewidth=0.5)
    plt.xlabel("t")
    plt.ylabel("i_b")
    plt.grid(True)
    # plt.axis("equal")
    plt.axis("tight")
    plt.show()

    plt.figure(figsize=(6, 6))
    plt.plot(time, ic, 'o')
    # plt.plot(id_initial, iq_initial, linewidth=0.5)
    plt.xlabel("t")
    plt.ylabel("i_c")
    plt.grid(True)
    # plt.axis("equal")
    plt.axis("tight")
    plt.show()

    # 4. Plot Result (Filtered Lissajous Curve)
    plt.figure(figsize=(6, 6))
    plt.plot(id_initial, iq_initial, 'o')
    # plt.plot(id_initial, iq_initial, linewidth=0.5)
    plt.title("Filtered Park's Vector Pattern")
    plt.xlabel("i_d")
    plt.ylabel("i_q")
    plt.grid(True)
    # plt.axis("equal")
    plt.axis("tight")
    plt.show()

if __name__ == "__main__":
    main()