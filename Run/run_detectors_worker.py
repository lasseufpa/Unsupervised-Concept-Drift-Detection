import os, sys, json, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "unsupervised-concept-drift-detection")
)

from detectors.d3 import DiscriminativeDriftDetector2019
from detectors.bndm import BayesianNonparametricDetectionMethod
from detectors.csddm import ClusteredStatisticalTestDriftDetectionMethod
from detectors.ocdd import OneClassDriftDetector


DATASET_FILE = sys.argv[1]
DET_NAME = sys.argv[2]
W = int(sys.argv[3])
SEED_ARG = sys.argv[4]
SEED = None if SEED_ARG == "None" else int(SEED_ARG)

if "abilene" in DATASET_FILE.lower():
    GAP_THRESHOLD_MINUTES = 5
else:
    GAP_THRESHOLD_MINUTES = 15


def make_detector(name, W, seed=None):
    if name == "D3":
        return DiscriminativeDriftDetector2019(
            n_reference_samples=W,
            recent_samples_proportion=0.1,
            threshold=0.7,
            seed=seed
        )
    elif name == "BNDM":
        return BayesianNonparametricDetectionMethod(
            n_samples=W,
            const=1.0,
            max_depth=3,
            threshold=0.5
        )
    elif name == "CSDDM":
        return ClusteredStatisticalTestDriftDetectionMethod(
            n_samples=W,
            n_clusters=2,
            confidence=0.05,
            feature_proportion=0.1,
            seed=seed
        )
    elif name == "OCDD":
        return OneClassDriftDetector(
            n_samples=W,
            threshold=0.3
        )
    else:
        raise ValueError(f"Unknown detector: {name}")


def run_detector_com_gatilho_valido(det_name, W, seed, data_np, timestamps, columns):
    drifts = []
    ts_dt = pd.to_datetime(timestamps)

    detector = make_detector(det_name, W, seed)
    amostras_validas_acumuladas = 0

    for i in range(len(data_np)):
        features = {columns[j]: data_np[i, j] for j in range(len(columns))}

        val_sum = np.nansum(list(features.values()))
        dado_valido = np.isfinite(val_sum) and val_sum > 0

        has_gap = False
        if i > 0:
            diff = (ts_dt[i] - ts_dt[i - 1]).total_seconds() / 60
            has_gap = diff > GAP_THRESHOLD_MINUTES

        if not dado_valido or has_gap:
            detector = make_detector(det_name, W, seed)
            amostras_validas_acumuladas = 0
            continue

        amostras_validas_acumuladas += 1

        is_drift_detected = detector.update(features)

        if amostras_validas_acumuladas <= W:
            continue

        if is_drift_detected:
            drifts.append(i)

    return drifts


try:
    data = pd.read_csv(
        os.path.join(os.path.dirname(__file__), DATASET_FILE),
        index_col=0,
        parse_dates=True
    ).sort_index()

    columns = list(data.columns)
    timestamps = data.index
    data_np = data.values.astype(float)

    drifts = run_detector_com_gatilho_valido(
        DET_NAME, W, SEED, data_np, timestamps, columns
    )

    print(json.dumps({
        "ok": True,
        "detector": DET_NAME,
        "window": W,
        "seed": SEED if SEED is not None else -1,
        "n_drifts": len(drifts),
        "drifts": drifts
    }))

except Exception as e:
    print(json.dumps({
        "ok": False,
        "detector": DET_NAME,
        "window": W,
        "seed": SEED if SEED is not None else -1,
        "error": str(e)
    }))