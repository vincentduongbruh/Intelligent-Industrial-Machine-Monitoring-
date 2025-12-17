import pandas as pd
import matplotlib.pyplot as plt
import scipy
from Fault_Detector import MotorFaultDetector

BOUSHABA_DATASET = "../datasets/boushaba/ccs20.csv" 
CARLETTI_DATASET = "../datasets/carletti/M2.r4b.torque100.mat"
BOUSHABA_FS_ORIGINAL = 1428
BOUSHABA_F0_DETECTED = 50

CARLETTI_FS_ORIGINAL = 8000
CARLETTI_F0_DETECTED = 50

# BOUSHABA FORMAT:
# time in seconds, current in amps, voltage in volts, speed in rad/s, rotor mechanical position in rad

# CARLETTI FORMAT:
# name MX.rYb.torqueZ.mat
# X = induction motor identification (1 to 26)
# Y = number of broken bars
# Z = percentage loading of induction motor (50, 75, 100)

def main():
    detector = MotorFaultDetector()

    mat = scipy.io.loadmat(CARLETTI_DATASET)
    mat = {key:value for key, value in mat.items() if key[0] != '_'}
    df = pd.DataFrame(mat["Istator"], columns=["s", "ia", "ib", "ic"])

    middle = (len(df) // 2) - 1
    low = middle - round(len(df) * 0.325)
    high = middle + round(len(df) * 0.325)

    df = df[low:high] # get the samples within 1 standard deviation of middle

    ia = df['ia'].values
    ib = df['ib'].values
    ic = df['ic'].values

    # id_final, iq_final = detector.process_pipeline(ia, ib, ic, CARLETTI_FS_ORIGINAL, CARLETTI_F0_DETECTED)
    id_initial, iq_initial = detector.process_pipeline_minimal(ia, ib, ic)

    mse = detector.least_squares_v1(ia, ib, ic)
    print(f"Mean Squared Error: {mse}")

    plt.figure(figsize=(6, 6))
    plt.plot(id_initial, iq_initial)
    plt.title("Filtered Park's Vector Pattern")
    plt.xlabel("i_d")
    plt.ylabel("i_q")
    plt.grid(True)
    plt.axis("equal")
    plt.show()

# def main():
#     # 1. Load Data
#     print("Loading dataset...")
#     columns = ["s", "ia", "ib", "ic", "va", "vb", "vc", "rad/s", "rad"]
#     df = pd.read_csv(BOUSHABA_DATASET, names=columns)
#     print(df)

#     middle = (len(df) // 2) - 1
#     low = middle - round(len(df) * 0.325)
#     high = middle + round(len(df) * 0.325)

#     df = df[low:high] # get the samples within 1 standard deviation of middle
#     print(df)

#     ia = df['ia'].values
#     ib = df['ib'].values
#     ic = df['ic'].values

#     # 2. Initialize Detector
#     detector = MotorFaultDetector()

#     # 3. Run Pipeline
#     print("Processing data...")
#     id_final, iq_final = detector.process_pipeline(ia, ib, ic, BOUSHABA_FS_ORIGINAL, BOUSHABA_F0_DETECTED)
#     id_initial, iq_initial = detector.process_pipeline_minimal(ia, ib, ic)

#     mse = detector.least_squares_v1(ia, ib, ic)
#     print(f"Mean Squared Error: {mse}")

#     # 4. Plot Result (Filtered Lissajous Curve)
#     plt.figure(figsize=(6, 6))
#     plt.plot(id_initial, iq_initial, linewidth=0.5)
#     plt.title("Filtered Park's Vector Pattern")
#     plt.xlabel("i_d")
#     plt.ylabel("i_q")
#     plt.grid(True)
#     plt.axis("equal")
#     plt.show()

if __name__ == "__main__":
    main()