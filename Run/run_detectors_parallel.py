import os, sys, json, time, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd


# ── Config ────────────────────────────────────────────────────────────

DATASETS = [
    "./outputs/abilene_diferenca_sazonal_log_com_lacunas.csv",
    "./outputs/geant_diferenca_sazonal_log_com_lacunas.csv"
]
for DATASET_FILE in DATASETS:
    MAX_WORKERS = 100

    SEEDS = [42, 123, 456, 789, 1024]

    if "abilene" in DATASET_FILE.lower():
        PREFIX = "abilene"
        # WINDOW_SIZES = list(range(2, 2016))
        WINDOW_SIZES = list(range(40, 41))
    else:
        PREFIX = "geant"
        # WINDOW_SIZES = list(range(2, 98))
        WINDOW_SIZES = list(range(40, 41))


    DETECTOR_NAMES = ["D3", "BNDM", "CSDDM", "OCDD"]

    DETECTOR_SEEDS = {
        "D3": SEEDS,
        "BNDM": [None],
        "CSDDM": SEEDS,
        "OCDD": [None],
    }


    DATASET_NAME = DATASET_FILE.replace(".csv", "")
    OUT_DIR = os.path.join(os.path.dirname(__file__), f"results_{DATASET_NAME}")
    os.makedirs(OUT_DIR, exist_ok=True)

    IDX_PATH = os.path.join(OUT_DIR, f"{PREFIX}_all_drift_indices.csv")
    SUM_PATH = os.path.join(OUT_DIR, f"{PREFIX}_summary.csv")
    ERROR_LOG = os.path.join(OUT_DIR, "errors.log")

    for p in [IDX_PATH, SUM_PATH, ERROR_LOG]:
        if os.path.exists(p):
            os.remove(p)


    # salva timestamps uma vez só
    data = pd.read_csv(
        os.path.join(os.path.dirname(__file__), DATASET_FILE),
        index_col=0,
        parse_dates=True
    ).sort_index()

    pd.Series(data.index, name="timestamp").to_csv(
        os.path.join(OUT_DIR, f"{PREFIX}_timestamps.csv"),
        index_label="local_index"
    )

    print(f"Starting parallel experiments for: {DATASET_NAME}")
    print(f"T={len(data)}, features={len(data.columns)}")
    print(f"Date range: {data.index[0]} → {data.index[-1]}")
    print(f"MAX_WORKERS={MAX_WORKERS}")


    def save_result(result):
        det_name = result["detector"]
        W = result["window"]
        seed = result["seed"]
        drifts = result["drifts"]

        if drifts:
            df_idx = pd.DataFrame({
                "detector": det_name,
                "window": W,
                "seed": seed,
                "drift_index": drifts,
            })
        else:
            df_idx = pd.DataFrame(columns=["detector", "window", "seed", "drift_index"])

        header = not os.path.exists(IDX_PATH)
        df_idx.to_csv(IDX_PATH, mode="a", header=header, index=False)

        df_sum = pd.DataFrame([{
            "detector": det_name,
            "window": W,
            "seed": seed,
            "n_drifts": len(drifts),
            "drift_indices_json": json.dumps(drifts),
        }])

        header = not os.path.exists(SUM_PATH)
        df_sum.to_csv(SUM_PATH, mode="a", header=header, index=False)


    def run_worker(det_name, W, seed):
        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "run_detectors_worker.py"),
            DATASET_FILE,
            det_name,
            str(W),
            str(seed),
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        if not stdout:
            return {
                "ok": False,
                "detector": det_name,
                "window": W,
                "seed": seed if seed is not None else -1,
                "error": stderr or "Worker returned empty stdout"
            }

        try:
            return json.loads(stdout.splitlines()[-1])
        except Exception as e:
            return {
                "ok": False,
                "detector": det_name,
                "window": W,
                "seed": seed if seed is not None else -1,
                "error": f"Invalid JSON: {e}; stdout={stdout}; stderr={stderr}"
            }


    tasks = []
    for det_name in DETECTOR_NAMES:
        for W in WINDOW_SIZES:
            for seed in DETECTOR_SEEDS[det_name]:
                tasks.append((det_name, W, seed))

    total_runs = len(tasks)
    done = 0

    t_global = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(run_worker, det_name, W, seed): (det_name, W, seed)
            for det_name, W, seed in tasks
        }

        for future in as_completed(futures):
            done += 1
            det_name, W, seed = futures[future]
            seed_str = str(seed) if seed is not None else "-"

            result = future.result()

            if result["ok"]:
                save_result(result)
                print(
                    f"[{done:5d}/{total_runs}] "
                    f"{det_name} W={W} seed={seed_str} "
                    f"n_drifts={result['n_drifts']}"
                )
            else:
                msg = (
                    f"{det_name}, W={W}, seed={seed_str} "
                    f"-> {result.get('error', 'Unknown error')}\n"
                )
                with open(ERROR_LOG, "a", encoding="utf-8") as f:
                    f.write(msg)

                print(
                    f"[{done:5d}/{total_runs}] "
                    f"{det_name} W={W} seed={seed_str} ❌ SKIPPED"
                )

    elapsed = time.time() - t_global
    print(f"\nDone! Results in {OUT_DIR}")
    print(f"Elapsed: {elapsed / 60:.2f} min")