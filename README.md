# Unsupervised Concept Drift Detection in Network Traffic Through Detector Consensus

**Abrahao Ferreira, Lucas Matni, Silvia Lins, Andrey Silva, Aldebaro Klautau, and Glauco Gonçalves**

Abrahao Ferreira, Lucas Matni, Aldebaro Klautau, and Glauco Gonçalves are with the **Federal University of Pará (UFPA), Belém, Pará, Brazil**.  
Silvia Lins and Andrey Silva are with **Ericsson Research, Brazil**.

## Supplementary Material

This repository contains supplementary material associated with our study on unsupervised concept drift detection in network traffic.

Due to space limitations in the manuscript, some analyses, figures, tables, implementation details, and additional experimental results could not be included in the final version of the paper. Rather than omitting this material entirely, we provide it here for readers interested in further details about the methodology and experimental results.

The material presented in this repository complements the paper and is intended to improve transparency, reproducibility, and access to additional results that may be useful for future research.

The following sections provide the supplementary content organized according to the corresponding parts of the study.

## Study at a glance

| Setting | Abilene | GÉANT |
|---|---|---|
| Directed OD flows | 132 | 462 |
| Sampling interval | 5 minutes | 15 minutes |
| Weekly seasonal differencing | 2,016 samples | 672 samples |
| Selected detector window | 120 samples | 60 samples |
| Seed used for reported event tables | 42 | 42 |
| Individual detector alarms (counting each detector separately) | 60 | 51 |
| Distinct alarm timestamps | 39 | 30 |
| Consensus drift candidates | **12** | **13** |
| Maximum consensus separation (20 samples) | 1 h 40 min | 5 h |

The alarm totals count each detector's notification, whereas distinct timestamps count simultaneous notifications only once. Consensus candidates require agreement among at least **three of the four multivariate detectors** within 20 samples and are **not ground-truth drift labels**.

## Repository structure

The following directory names are taken from the repository root shown by the authors. Some output subdirectories are created by the analysis scripts when executed.

| Path | Description |
|---|---|
| `datasets/` | Original Abilene and GÉANT origin–destination (OD) traffic matrices in CSV format. |
| `detectors/` | Drift-detector implementations used in the study. |
| `Run/` | Scripts that coordinate and execute multivariate drift-detection experiments. |
| `main .ipynb` | Main preprocessing, multivariate result analysis, consensus and plotting notebook. **The filename contains a space before `.ipynb`.** |
| `uni.ipynb` | Complementary univariate analysis (ADWIN, KSWIN, Page-Hinkley), CSV summaries, and top-four original OD-flow plots. |
| `plt_correlation_matrix.py` | Standalone pre-/post-event OD-flow correlation-matrix analysis. |
| `outputs/` | Preprocessed matrices and the `drifts_tabelas/` event CSV exports. |
| `results_sem_log/` | Multivariate experiment output directories, including per-dataset summary files; the name reflects non-logarithmic seasonal differencing. |
| `plots/` | Multivariate visualizations, CCDF figures and correlation heatmaps. |
| `univariada/` | Complementary univariate detections, detector-agreement CSVs, and OD-flow figures. |

All relative paths below assume that the notebook or script is executed with the **repository root as the working directory**.

## Datasets and preprocessing

The study uses **Abilene** (132 directed OD flows sampled every five minutes) and **GÉANT** (462 directed OD flows sampled every 15 minutes). The original matrices describe **traffic rates in Mbps**. The main analysis applies weekly seasonal differencing **without a logarithmic transform**, handles temporal gaps and invalid readings, and retains separate, continuous data fragments for detection.

The main notebook reads:

- `datasets/abilene_demand_matrix.csv`
- `datasets/geant_demand_matrix.csv`

It writes the following intermediate CSVs under `outputs/`:

| File | Contents |
|---|---|
| `abilene_processed_with_gaps.csv` | Abilene cleaned/reindexed traffic matrix, retaining gaps. |
| `geant_processed_with_gaps.csv` | GÉANT cleaned/reindexed traffic matrix, retaining gaps. |
| `abilene_seasonal_difference_with_gaps.csv` | Non-log weekly seasonal differences for Abilene. |
| `geant_seasonal_difference_with_gaps.csv` | Non-log weekly seasonal differences for GÉANT. |

The **original traffic rates**, not their seasonal differences, are used for the post-consensus CCDF, correlation-matrix, and original-flow plots when configured in original-data mode. For the CCDF x-axis, the proper label is **Traffic rate (Mbps)**.

## Reproducing the experiments

1. **Prepare the data:** start Jupyter in the repository root, open `main .ipynb`, and execute its data-loading and preprocessing cells. Verify that the four intermediate CSVs above were created.
2. **Run the multivariate detectors:** use `Run/run_detectors_parallel.py`, which launches `run_detectors_worker.py` for detector, window-size and seed configurations. Review `MAX_WORKERS`, `SEEDS`, `WINDOW_SIZES` and `DETECTOR_NAMES` before running; the worker count should match available hardware. The study uses D3, BNDM, CSDDM and OCDD, with seeds 42, 123, 456, 789 and 1024 for stochastic runs. The event tables below use a representative seed of 42.
3. **Check the detector summaries:** the subsequent analysis expects the following files (these existing experiment-output directories **retain their Portuguese names**):
   - `results_sem_log/outputs/abilene_diferenca_sazonal_sem_log_com_lacunas/abilene_summary.csv`
   - `results_sem_log/outputs/geant_diferenca_sazonal_sem_log_com_lacunas/geant_summary.csv`
4. **Analyze alarms and consensus:** run the relevant cells of `main .ipynb`. For the reported event analysis, use **W = 120** for Abilene and **W = 60** for GÉANT, and require agreement of at least **three of four multivariate detectors** within **20 samples** (100 minutes in Abilene and 300 minutes in GÉANT).
5. **Create additional figures:** the main notebook generates window-size sensitivity plots, drift timelines, CCDFs and other event-centered analyses. Run `plt_correlation_matrix.py` from the repository root to generate ordered pre-/post-event correlation matrices from the saved detailed alarm CSV.
6. **Run the complementary univariate analysis:** open the **updated** `uni.ipynb` and run its sections sequentially (detector evaluation, agreement/CSV summaries, top-four original OD-flow plots). Its input data filenames must match the English-language seasonal-difference CSVs listed above.

**Compatibility note:** the corrected univariate notebook uses `outputs/abilene_seasonal_difference_with_gaps.csv` and `outputs/geant_seasonal_difference_with_gaps.csv`. If your existing `uni.ipynb` still refers to `*_diferenca_sazonal_sem_log_com_lacunas.csv` under `outputs/`, replace it with the corrected version before running. The `results_sem_log/.../*_summary.csv` paths should *not* be renamed just to translate them.

This repository does not supply a universal one-command pipeline: some figures depend on CSVs generated by earlier notebook cells or by separate detector runs. Reproduce them in the order above.

## Results and generated files

| Location | Purpose |
|---|---|
| `outputs/drifts_tabelas/drifts_resumo.csv` | Summary of detected alarms by dataset/detector. |
| `outputs/drifts_tabelas/drifts_detalhados.csv` | Individual alarm records, including detector, window, timestamp and index information. |
| `outputs/drifts_tabelas/drifts_consenso_detectores.csv` | Candidate events formed through multivariate detector agreement. |
| `plots/` | Window-size sensitivity plots and other graphics from the main notebook. |
| `plots/drifts_marcados/` | Traffic time-series visualizations with detected alarms overlaid. |
| `plots/ccdf_fluxos_concatenados_ao_redor_dos_drifts/` | Before/after CCDF figures and CSV summaries for concatenated OD flows. |
| `plots/bitmaps_ordenados_por_media_corr/` | Ordered before/after correlation figures, flow-order CSVs, statistical summaries and diagnostic text logs. |
| `univariada/abilene/` and `univariada/geant/` | Per-dataset univariate detection and event information CSVs. |
| `univariada/analise_resultados/` | Univariate detector-agreement and flow-ranking CSVs, including combined summaries. |
| `univariada/plots_top4_fluxos_dado_original_sem_transformacao/` | Top-four high-variance OD-flow figures using original, untransformed traffic data. |

The three key multivariate result files are `drifts_detalhados.csv` (per-detector alarms), `drifts_resumo.csv` (counts and timing summaries), and `drifts_consenso_detectores.csv` (candidate events, supporting detectors and time spans). Their actual CSV fields may retain Portuguese names, such as `inicio_timestamp`, `fim_timestamp`, and `n_detectores_concordando`; the Markdown tables below use English display names without changing the CSV schema.

The correlation script `plt_correlation_matrix.py` reads `outputs/drifts_tabelas/drifts_detalhados.csv`, then calculates before/after flow correlation matrices over regions of `3 × window` observations on each side of a candidate alarm. It uses **all available OD flows** and a shared ordering derived from the two correlation matrices; the ordering changes only their display, not the underlying correlation values. By default, the diagonal and lower triangle are hidden. The script also exports `resumo_figuras_correlacao_before_after_ordenadas.csv`, per-event flow-order CSVs, and `problemas_correlacao.txt` when diagnostic issues are found.

The univariate notebook uses the seasonally differenced data for detector evaluation and **original** traffic matrices for the retained four-flow visualizations. Its summaries include `univariado_detalhado.csv`, `eventos_multivariados_analisados.csv`, detector agreement reports, and rankings of flows. These complementary univariate results are **not** part of the four-detector multivariate consensus criterion used for the main paper tables.

## Interpreting the reported events

A **detector alarm** is an individual detector's alert at one timestamp. The tables in the next section list individual alarm timestamps; they are **not** lists of distinct consensus events. A **consensus candidate** is a cluster of alarms supported by at least three multivariate detectors within the specified tolerance. Since the datasets do not have verified drift labels, these candidates should **not** be described as ground-truth concept drifts.

The paper numbers consensus events separately from the alarm indices shown below. For example, Abilene consensus **event #1** begins at `2004-03-13 15:35:00`, while GÉANT consensus **event #11** begins at `2005-08-29 05:15:00`. Internal CSV identifiers may differ from the paper's numbering; match dataset and timestamps when cross-referencing results.

### Detector Drift Events

The tables below report the individual drift instances detected by each method using the operating window sizes adopted in the study. A dash (`—`) indicates that the corresponding detector did not signal a drift at that timestamp.

#### GÉANT

<details>
<summary><b>Drift instances detected in GÉANT (window size = 60, seed = 42)</b></summary>

<br>

| Index | D3 | BNDM | CSDDM | OCDD |
|---:|---|---|---|---|
| 1  | 2005-06-09 10:15:00 | — | — | — |
| 2  | 2005-07-19 03:45:00 | — | — | — |
| 3  | 2005-08-09 01:45:00 | — | — | — |
| 4  | 2005-08-10 02:15:00 | — | — | — |
| 5  | — | 2005-08-10 15:30:00 | 2005-08-10 15:30:00 | 2005-08-10 15:30:00 |
| 6  | 2005-08-10 17:30:00 | — | — | — |
| 7  | 2005-08-21 17:15:00 | — | — | — |
| 8  | — | 2005-08-22 06:30:00 | 2005-08-22 06:30:00 | 2005-08-22 06:30:00 |
| 10 | 2005-08-22 08:30:00 | — | — | — |
| 11 | — | — | 2005-08-22 21:30:00 | 2005-08-22 21:30:00 |
| 12 | 2005-08-22 23:45:00 | — | — | — |
| 13 | — | 2005-08-23 12:30:00 | 2005-08-23 12:30:00 | 2005-08-23 12:30:00 |
| 14 | 2005-08-24 22:00:00 | — | — | — |
| 15 | — | 2005-08-25 11:15:00 | 2005-08-25 11:15:00 | 2005-08-25 11:15:00 |
| 16 | 2005-08-25 13:15:00 | — | — | — |
| 17 | — | — | 2005-08-26 02:15:00 | 2005-08-26 02:15:00 |
| 18 | 2005-08-26 04:30:00 | — | — | — |
| 19 | — | 2005-08-26 17:15:00 | 2005-08-26 17:15:00 | 2005-08-26 17:15:00 |
| 20 | 2005-08-26 19:45:00 | — | — | — |
| 21 | — | — | 2005-08-27 08:15:00 | 2005-08-27 08:15:00 |
| 22 | 2005-08-27 11:00:00 | — | — | — |
| 23 | — | 2005-08-27 23:15:00 | — | 2005-08-27 23:15:00 |
| 24 | 2005-08-28 02:15:00 | — | — | — |
| 25 | — | — | 2005-08-28 14:15:00 | — |
| 26 | 2005-08-28 17:30:00 | — | — | — |
| 27 | — | 2005-08-29 05:15:00 | 2005-08-29 05:15:00 | 2005-08-29 05:15:00 |
| 28 | 2005-08-29 08:45:00 | — | — | — |
| 29 | — | — | 2005-08-29 20:15:00 | 2005-08-29 20:15:00 |
| 30 | 2005-08-30 00:00:00 | — | — | — |
| 31 | — | 2005-08-30 11:15:00 | 2005-08-30 11:15:00 | 2005-08-30 11:15:00 |

</details>

*The original GÉANT appendix skips index 9 (from 8 to 10). This numbering is preserved; there are 30 distinct alarm timestamps.*

#### Abilene

<details>
<summary><b>Drift instances detected in Abilene (window size = 120, seed = 42)</b></summary>

<br>

| Index | D3 | BNDM | CSDDM | OCDD |
|---:|---|---|---|---|
| 1  | 2004-03-13 06:40:00 | — | — | — |
| 2  | — | 2004-03-13 15:35:00 | 2004-03-13 15:35:00 | 2004-03-13 15:35:00 |
| 3  | 2004-03-13 16:45:00 | — | — | — |
| 4  | 2004-03-14 06:30:00 | — | — | — |
| 5  | 2004-04-11 00:05:00 | — | — | — |
| 6  | — | 2004-04-11 09:00:00 | 2004-04-11 09:00:00 | 2004-04-11 09:00:00 |
| 7  | 2004-04-11 10:10:00 | — | — | — |
| 8  | 2004-04-12 23:25:00 | — | — | — |
| 9  | — | 2004-04-13 08:20:00 | 2004-04-13 08:20:00 | 2004-04-13 08:20:00 |
| 10 | 2004-04-13 09:30:00 | — | — | — |
| 11 | — | — | 2004-04-13 18:20:00 | 2004-04-13 18:20:00 |
| 12 | 2004-04-13 19:35:00 | — | — | — |
| 13 | 2004-05-21 16:10:00 | — | — | — |
| 14 | 2004-06-04 11:55:00 | — | — | — |
| 15 | — | 2004-06-04 20:50:00 | 2004-06-04 20:50:00 | 2004-06-04 20:50:00 |
| 16 | 2004-06-04 22:00:00 | — | — | — |
| 17 | 2004-06-06 20:40:00 | — | — | — |
| 18 | 2004-07-12 22:45:00 | — | — | — |
| 19 | 2004-07-18 10:05:00 | — | — | — |
| 20 | — | 2004-07-18 19:00:00 | 2004-07-18 19:00:00 | 2004-07-18 19:00:00 |
| 21 | 2004-07-18 20:10:00 | — | — | — |
| 22 | — | — | 2004-07-19 05:00:00 | 2004-07-19 05:00:00 |
| 23 | 2004-07-19 06:15:00 | — | — | — |
| 24 | 2004-07-30 17:40:00 | — | — | — |
| 25 | 2004-08-29 05:05:00 | — | — | — |
| 26 | — | 2004-08-29 14:00:00 | 2004-08-29 14:00:00 | 2004-08-29 14:00:00 |
| 27 | 2004-08-29 15:10:00 | — | — | — |
| 28 | — | — | 2004-08-30 00:00:00 | 2004-08-30 00:00:00 |
| 29 | 2004-08-30 01:15:00 | — | — | — |
| 30 | 2004-08-30 20:45:00 | — | — | — |
| 31 | — | 2004-08-31 05:40:00 | 2004-08-31 05:40:00 | 2004-08-31 05:40:00 |
| 32 | 2004-08-31 06:50:00 | — | — | — |
| 33 | 2004-08-31 21:35:00 | — | — | — |
| 34 | — | 2004-09-01 06:30:00 | 2004-09-01 06:30:00 | 2004-09-01 06:30:00 |
| 35 | 2004-09-01 07:40:00 | — | — | — |
| 36 | 2004-09-07 14:30:00 | — | — | — |
| 37 | 2004-09-09 12:15:00 | — | — | — |
| 38 | — | 2004-09-09 21:10:00 | 2004-09-09 21:10:00 | 2004-09-09 21:10:00 |
| 39 | 2004-09-09 22:20:00 | — | — | — |

</details>

## Consensus drift candidates

The *Number* below is the paper's ordinal consensus-event identifier, not the alarm-table index or the internal `evento_consenso` field from the CSV. CDS denotes the distance, **in sample intervals**, between first and last contributing alarms. The underlying exported CSV may use a different interval-width convention; consult the two timestamps to compare consistently.

### Abilene consensus events

| Number | First detection | Last detection | CDS (samples) | Supporting detectors |
|---:|---|---|---:|---|
| 01 | 2004-03-13 15:35:00 | 2004-03-13 16:45:00 | 14 | D3, BNDM, CSDDM, OCDD |
| 02 | 2004-04-11 09:00:00 | 2004-04-11 10:10:00 | 14 | D3, BNDM, CSDDM, OCDD |
| 03 | 2004-04-13 08:20:00 | 2004-04-13 09:30:00 | 14 | D3, BNDM, CSDDM, OCDD |
| 04 | 2004-04-13 18:20:00 | 2004-04-13 19:35:00 | 15 | D3, CSDDM, OCDD |
| 05 | 2004-06-04 20:50:00 | 2004-06-04 22:00:00 | 14 | D3, BNDM, CSDDM, OCDD |
| 06 | 2004-07-18 19:00:00 | 2004-07-18 20:10:00 | 14 | D3, BNDM, CSDDM, OCDD |
| 07 | 2004-07-19 05:00:00 | 2004-07-19 06:15:00 | 15 | D3, CSDDM, OCDD |
| 08 | 2004-08-29 14:00:00 | 2004-08-29 15:10:00 | 14 | D3, BNDM, CSDDM, OCDD |
| 09 | 2004-08-30 00:00:00 | 2004-08-30 01:15:00 | 15 | D3, CSDDM, OCDD |
| 10 | 2004-08-31 05:40:00 | 2004-08-31 06:50:00 | 14 | D3, BNDM, CSDDM, OCDD |
| 11 | 2004-09-01 06:30:00 | 2004-09-01 07:40:00 | 14 | D3, BNDM, CSDDM, OCDD |
| 12 | 2004-09-09 21:10:00 | 2004-09-09 22:20:00 | 14 | D3, BNDM, CSDDM, OCDD |

### GÉANT consensus events

| Number | First detection | Last detection | CDS (samples) | Supporting detectors |
|---:|---|---|---:|---|
| 01 | 2005-08-10 15:30:00 | 2005-08-10 17:30:00 | 8 | D3, BNDM, CSDDM, OCDD |
| 02 | 2005-08-22 06:30:00 | 2005-08-22 08:30:00 | 8 | D3, BNDM, CSDDM, OCDD |
| 03 | 2005-08-22 21:30:00 | 2005-08-22 23:45:00 | 9 | D3, CSDDM, OCDD |
| 04 | 2005-08-23 12:30:00 | 2005-08-23 12:30:00 | 0 | BNDM, CSDDM, OCDD |
| 05 | 2005-08-25 11:15:00 | 2005-08-25 13:15:00 | 8 | D3, BNDM, CSDDM, OCDD |
| 06 | 2005-08-26 02:15:00 | 2005-08-26 04:30:00 | 9 | D3, CSDDM, OCDD |
| 07 | 2005-08-26 17:15:00 | 2005-08-26 19:45:00 | 10 | D3, BNDM, CSDDM, OCDD |
| 08 | 2005-08-27 08:15:00 | 2005-08-27 11:00:00 | 11 | D3, CSDDM, OCDD |
| 09 | 2005-08-27 23:15:00 | 2005-08-28 02:15:00 | 12 | D3, BNDM, CSDDM, OCDD |
| 10 | 2005-08-28 14:15:00 | 2005-08-28 17:30:00 | 13 | D3, CSDDM, OCDD |
| 11 | 2005-08-29 05:15:00 | 2005-08-29 08:45:00 | 14 | D3, BNDM, CSDDM, OCDD |
| 12 | 2005-08-29 20:15:00 | 2005-08-30 00:00:00 | 15 | D3, CSDDM, OCDD |
| 13 | 2005-08-30 11:15:00 | 2005-08-30 11:15:00 | 0 | BNDM, CSDDM, OCDD |

**Note:** The event identifiers above match the `Number` column in the paper; they are separate from individual alarm indices. The reported events are candidates identified through detector agreement, not verified ground-truth changes.

### Detector-level alarm summary

For the selected operating windows and seed used in the event tables, the reported alarm counts are:

| Dataset | D3 | BNDM | CSDDM | OCDD |
|---|---:|---:|---:|---:|
| Abilene | 27 | 9 | 12 | 12 |
| GÉANT | 17 | 8 | 13 | 13 |

These are **alarm counts**, not measures of detection accuracy or confirmed drift events.

### Reading the figures

- **Window-size sensitivity (Figures 3–4):** curves show the average number of alarms as window size changes, not detector accuracy. The selected operating windows lie in regions where alarm counts begin to stabilize; no ground-truth labels were available for supervised tuning.
- **Drift timelines:** detections are placed over aggregate traffic-rate series to show their temporal context. Aggregate traffic rate is the sum of the OD rates at a sampling instant.
- **CCDFs:** compare the empirical distributions of concatenated OD traffic rates before and after selected candidate events, using **Traffic rate (Mbps)** on the horizontal axis when plotting untransformed data.
- **Correlation matrices:** compare inter-flow relationships before and after candidate events. The same visual flow ordering is applied to both matrices; reordering does not alter calculated correlations.
- **Top-four flow plots:** show selected high-variance OD flows from the original data. These descriptions are exploratory and do not establish the causes of candidate changes.

### Dataset and preprocessing notes

The input measurements are **traffic rates (Mbps)** rather than traffic volumes. Weekly seasonal differencing is computed within continuous fragments to avoid treating timestamp gaps as transitions. Each fragment requires one week of reference history before seasonally differenced values become available. The GÉANT record `20050527-1745` is flagged as suspect in the SNDlib `geant-readme.txt` and treated as invalid during preprocessing. The paper's detector experiments use the **non-logarithmic** seasonal difference; a logarithmic plotting axis is a visualization choice and should not be confused with a log transform of input data.

## Citation and acknowledgments

If you use the materials, please cite the accompanying study, *Unsupervised Concept Drift Detection in Network Traffic Through Detector Consensus*, together with the original dataset publications. Add the final article DOI and bibliography entry when available.

The authors acknowledge support as described in the accompanying paper. This supplementary repository contains candidate drift annotations and code for reproducibility; it does not provide independently verified ground-truth drift labels.
