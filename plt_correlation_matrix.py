import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

# ============================================================
# LEITURA CORRETA DOS CSVs
# ============================================================

SUMMARY_FILES = {
    "Abilene": "./results_sem_log/outputs/abilene_diferenca_sazonal_sem_log_com_lacunas/abilene_summary.csv",
    "GÉANT": "./results_sem_log/outputs/geant_diferenca_sazonal_sem_log_com_lacunas/geant_summary.csv",
}

from pathlib import Path

path_drifts = Path("./outputs/drifts_tabelas/drifts_detalhados.csv")

if path_drifts.exists():
    df_drifts_detalhado = pd.read_csv(path_drifts)
    df_drifts_detalhado["timestamp"] = pd.to_datetime(df_drifts_detalhado["timestamp"])
    print(f"Drifts carregados de: {path_drifts}")
else:
    raise FileNotFoundError(
        f"Arquivo não encontrado: {path_drifts}\n"
        "Você precisa rodar primeiro a etapa que gera df_drifts_detalhado "
        "ou salvar o arquivo drifts_detalhados.csv."
    )


def carregar_matriz_csv(file_path, freq_min, dataset):
    df = pd.read_csv(file_path)

    if "timestamp" not in df.columns:
        raise ValueError("O arquivo precisa ter uma coluna chamada 'timestamp'.")

    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y%m%d-%H%M")
    df = df.drop_duplicates(subset="timestamp")
    df = df.set_index("timestamp").sort_index()

    cols_num = df.select_dtypes(include=[np.number]).columns
    df = df[cols_num]

    indice_completo = pd.date_range(
        start=df.index.min(),
        end=df.index.max(),
        freq=f"{freq_min}min"
    )

    df = df.reindex(indice_completo)
    df.index.name = "timestamp"

    if dataset.lower() == "geant":
        linhas_vazias = df.eq(0).all(axis=1)
        df.loc[linhas_vazias, :] = np.nan

    return df


df_abilene = carregar_matriz_csv(
    file_path="./datasets/abilene_demand_matrix.csv",
    freq_min=5,
    dataset="abilene"
)

df_geant = carregar_matriz_csv(
    file_path="./datasets/geant_demand_matrix.csv",
    freq_min=15,
    dataset="geant"
)


DATASETS_ORIGINAIS = {
    "Abilene": df_abilene,
    "GÉANT": df_geant,
}

# "original" -> usa o tráfego original
# "detector" -> usa a série usada pelos detectores
MODO_SERIE = "original"

# Tamanho da região antes/depois:
# tamanho = FATOR_JANELA * window
FATOR_JANELA = 3

# Normalizar cada fluxo antes de calcular correlação?
NORMALIZAR_POR_FLUXO = False

# Transformação aplicada aos dados antes da correlação
# "nenhuma" ou "abs"
TRANSFORMACAO_CORR = "nenhuma"

# Pasta principal
OUT_DIR = Path("./plots/bitmaps_ordenados_por_media_corr")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Arquivo para registrar problemas de correlação/ordenação
LOG_PROBLEMAS_CORR = OUT_DIR / "problemas_correlacao.txt"

# Lista acumulada de mensagens
linhas_log_problemas = []

# Se quiser limitar o número de drifts por configuração
MAX_DRIFTS_POR_CONFIG = None

# Se quiser filtrar datasets/detectores
DATASETS_FILTRAR = None
DETECTORES_FILTRAR = None

# Usa TODOS os fluxos.
# Não vamos selecionar top-k.
USAR_TODOS_OS_FLUXOS = True

# Limiar para separar:
# positiva, baixa e negativa.
#
# media_corr > +LIMIAR_CORR_BAIXA  -> positiva
# entre -limiar e +limiar          -> baixa
# media_corr < -LIMIAR_CORR_BAIXA  -> negativa
LIMIAR_CORR_BAIXA = 0.20

# Ordem visual dos blocos.
# Como você perguntou: positiva, baixa, negativa.
# Se quiser leitura gradual, troque para:
# ["negativa", "baixa", "positiva", "indefinida"]
ORDEM_BLOCOS_CORR = ["positiva", "baixa", "negativa", "indefinida"]

# Plota apenas o triângulo superior da matriz?
PLOTAR_APENAS_TRIANGULO_SUPERIOR = True

# Esconde também a diagonal?
# A diagonal é sempre 1 na correlação do fluxo com ele mesmo,
# então normalmente atrapalha a leitura.
MASCARAR_DIAGONAL = True

# Desenhar linhas separando os blocos positiva/baixa/negativa?
DESENHAR_SEPARADORES_BLOCOS = True

# Salvar um CSV com a ordem dos fluxos para cada drift?
SALVAR_ORDEM_FLUXOS = True

# DPI das figuras
DPI_FIGURA = 300


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def correlacoes_validas_fora_diagonal(corr):
    """
    Conta, para cada fluxo, quantas correlações válidas existem fora da diagonal.
    """

    arr = corr.to_numpy(dtype=float).copy()

    if arr.shape[0] != arr.shape[1]:
        raise ValueError("A matriz de correlação precisa ser quadrada.")

    np.fill_diagonal(arr, np.nan)

    contagem = np.sum(np.isfinite(arr), axis=1)

    return pd.Series(contagem, index=corr.index, name="n_corr_validas")


def diagnosticar_fluxos_problematicos(
    df_antes,
    df_depois,
    corr_antes,
    corr_depois,
    dataset,
    detector,
    window,
    drift_numero,
    timestamp_drift,
    row_drift=None,
):
    """
    Identifica fluxos cuja correlação ficou indefinida.

    Um fluxo é considerado problemático quando:
    - não possui nenhuma correlação válida fora da diagonal em before; ou
    - não possui nenhuma correlação válida fora da diagonal em after; ou
    - não possui nenhuma correlação válida na matriz de referência usada para ordenação.
    """

    fluxos_comuns = corr_antes.index.intersection(corr_depois.index)

    corr_antes = corr_antes.loc[fluxos_comuns, fluxos_comuns]
    corr_depois = corr_depois.loc[fluxos_comuns, fluxos_comuns]

    df_antes = df_antes[fluxos_comuns]
    df_depois = df_depois[fluxos_comuns]

    # Matriz usada apenas para ordenação
    corr_ref = criar_matriz_referencia_corr(corr_antes, corr_depois)

    n_corr_validas_antes = correlacoes_validas_fora_diagonal(corr_antes)
    n_corr_validas_depois = correlacoes_validas_fora_diagonal(corr_depois)
    n_corr_validas_ref = correlacoes_validas_fora_diagonal(corr_ref)

    n_validos_antes = df_antes.notna().sum(axis=0)
    n_validos_depois = df_depois.notna().sum(axis=0)

    std_antes = df_antes.std(axis=0, skipna=True)
    std_depois = df_depois.std(axis=0, skipna=True)

    registros = []

    for pos_fluxo, fluxo in enumerate(fluxos_comuns):

        sem_corr_antes = n_corr_validas_antes.loc[fluxo] == 0
        sem_corr_depois = n_corr_validas_depois.loc[fluxo] == 0
        sem_corr_ref = n_corr_validas_ref.loc[fluxo] == 0

        if not (sem_corr_antes or sem_corr_depois or sem_corr_ref):
            continue

        motivos = []

        if sem_corr_antes:
            motivos.append("sem_correlacao_valida_before")

        if sem_corr_depois:
            motivos.append("sem_correlacao_valida_after")

        if sem_corr_ref:
            motivos.append("sem_correlacao_valida_referencia")

        if n_validos_antes.loc[fluxo] < 2:
            motivos.append("poucos_pontos_validos_before")

        if n_validos_depois.loc[fluxo] < 2:
            motivos.append("poucos_pontos_validos_after")

        if pd.isna(std_antes.loc[fluxo]) or std_antes.loc[fluxo] == 0:
            motivos.append("variancia_zero_ou_nan_before")

        if pd.isna(std_depois.loc[fluxo]) or std_depois.loc[fluxo] == 0:
            motivos.append("variancia_zero_ou_nan_after")

        registro = {
            "dataset": dataset,
            "detector": detector,
            "window": int(window),
            "drift_numero": int(drift_numero),
            "timestamp": pd.to_datetime(timestamp_drift),
            "fluxo": fluxo,
            "posicao_fluxo_na_matriz": int(pos_fluxo),
            "n_validos_before": int(n_validos_antes.loc[fluxo]),
            "n_validos_after": int(n_validos_depois.loc[fluxo]),
            "std_before": float(std_antes.loc[fluxo]) if pd.notna(std_antes.loc[fluxo]) else np.nan,
            "std_after": float(std_depois.loc[fluxo]) if pd.notna(std_depois.loc[fluxo]) else np.nan,
            "n_corr_validas_before": int(n_corr_validas_antes.loc[fluxo]),
            "n_corr_validas_after": int(n_corr_validas_depois.loc[fluxo]),
            "n_corr_validas_referencia": int(n_corr_validas_ref.loc[fluxo]),
            "motivos": ";".join(motivos),
        }

        if row_drift is not None:
            registro["drift_index_detector"] = row_drift.get("drift_index_detector", np.nan)
            registro["drift_index_original"] = row_drift.get("drift_index_original", np.nan)

        registros.append(registro)

    return pd.DataFrame(registros)


def adicionar_problemas_ao_log(df_problemas, linhas_log):
    """
    Converte os problemas encontrados em texto legível para salvar em .txt.
    """

    if df_problemas.empty:
        return

    primeiro = df_problemas.iloc[0]

    linhas_log.append("=" * 90)
    linhas_log.append(
        f"Dataset: {primeiro['dataset']} | "
        f"Detector: {primeiro['detector']} | "
        f"window={primeiro['window']} | "
        f"drift_numero={primeiro['drift_numero']} | "
        f"timestamp={primeiro['timestamp']}"
    )

    if "drift_index_detector" in df_problemas.columns:
        linhas_log.append(
            f"drift_index_detector={primeiro.get('drift_index_detector', np.nan)} | "
            f"drift_index_original={primeiro.get('drift_index_original', np.nan)}"
        )

    linhas_log.append(f"Total de fluxos problemáticos: {len(df_problemas)}")
    linhas_log.append("-" * 90)

    for _, r in df_problemas.iterrows():
        linhas_log.append(
            f"pos_fluxo={r['posicao_fluxo_na_matriz']} | "
            f"fluxo={r['fluxo']} | "
            f"validos_before={r['n_validos_before']} | "
            f"validos_after={r['n_validos_after']} | "
            f"std_before={r['std_before']} | "
            f"std_after={r['std_after']} | "
            f"corr_validas_before={r['n_corr_validas_before']} | "
            f"corr_validas_after={r['n_corr_validas_after']} | "
            f"corr_validas_ref={r['n_corr_validas_referencia']} | "
            f"motivos={r['motivos']}"
        )

    linhas_log.append("")

def nome_seguro(texto):
    texto = str(texto)
    texto = texto.replace("GÉANT", "GEANT")
    texto = texto.replace("É", "E").replace("é", "e")
    texto = texto.replace("Á", "A").replace("á", "a")
    texto = texto.replace(" ", "_")
    texto = texto.replace("/", "_")
    texto = texto.replace("\\", "_")
    texto = texto.replace(":", "-")
    return texto


def obter_df_para_analise(dataset_name, modo_serie="original"):
    if modo_serie == "original":
        df = DATASETS_ORIGINAIS[dataset_name].copy()
    else:
        raise ValueError("Neste script, use MODO_SERIE = 'original'.")

    df = df.replace([np.inf, -np.inf], np.nan)
    return df


def aplicar_transformacao_corr(df, transformacao="nenhuma"):
    df = df.copy()

    if transformacao == "abs":
        df = df.abs()
    elif transformacao == "nenhuma":
        pass
    else:
        raise ValueError("TRANSFORMACAO_CORR deve ser 'abs' ou 'nenhuma'.")

    return df


def extrair_janelas_antes_depois_fluxos(
    df_base,
    timestamp_drift,
    window,
    fator_janela=3,
    normalizar_por_fluxo=False,
):
    """
    Extrai duas janelas:
    - before: pontos imediatamente antes do drift
    - after: pontos imediatamente depois do drift

    Não muda o cálculo de correlação.
    Apenas prepara os dados das duas janelas.
    """

    df_num = df_base.select_dtypes(include=[np.number]).copy()
    df_num = df_num.replace([np.inf, -np.inf], np.nan)

    timestamp_drift = pd.to_datetime(timestamp_drift)

    if timestamp_drift not in df_num.index:
        return None, None, None, None, None, None

    pos = df_num.index.get_loc(timestamp_drift)
    tamanho = int(fator_janela * window)

    ini_antes = max(0, pos - tamanho)
    fim_antes = pos

    ini_depois = pos + 1
    fim_depois = min(len(df_num), pos + 1 + tamanho)

    df_antes = df_num.iloc[ini_antes:fim_antes].copy()
    df_depois = df_num.iloc[ini_depois:fim_depois].copy()

    if normalizar_por_fluxo:
        df_total = pd.concat([df_antes, df_depois], axis=0)

        medias = df_total.mean(axis=0, skipna=True)
        desvios = df_total.std(axis=0, skipna=True)
        desvios = desvios.replace(0, np.nan)

        df_antes = (df_antes - medias) / desvios
        df_depois = (df_depois - medias) / desvios

    df_antes = aplicar_transformacao_corr(df_antes, TRANSFORMACAO_CORR)
    df_depois = aplicar_transformacao_corr(df_depois, TRANSFORMACAO_CORR)

    return df_antes, df_depois, pos, tamanho, df_antes.shape, df_depois.shape


def manter_todos_fluxos_comuns(df_antes, df_depois):
    """
    Mantém todos os fluxos presentes nas duas janelas.
    Não faz seleção por top-k.
    """

    colunas_comuns = df_antes.columns.intersection(df_depois.columns)

    df_antes = df_antes[colunas_comuns].copy()
    df_depois = df_depois[colunas_comuns].copy()

    return df_antes, df_depois, list(colunas_comuns)


def calcular_matriz_correlacao(df_janela):
    """
    Calcula a correlação entre fluxos.
    Este é o cálculo principal da análise.
    """

    return df_janela.corr()


def criar_matriz_referencia_corr(corr_antes, corr_depois):
    """
    Cria uma matriz de referência apenas para ordenar os fluxos.

    Importante:
    - essa matriz NÃO substitui corr_antes nem corr_depois;
    - ela só serve para definir uma ordem visual única;
    - a figura continua mostrando as correlações reais before/after.
    """

    fluxos_comuns = corr_antes.index.intersection(corr_depois.index)

    corr_antes = corr_antes.loc[fluxos_comuns, fluxos_comuns]
    corr_depois = corr_depois.loc[fluxos_comuns, fluxos_comuns]

    arr_antes = corr_antes.to_numpy(dtype=float)
    arr_depois = corr_depois.to_numpy(dtype=float)

    with np.errstate(all="ignore"):
        arr_ref = np.nanmean(
            np.stack([arr_antes, arr_depois], axis=0),
            axis=0
        )

    corr_ref = pd.DataFrame(
        arr_ref,
        index=fluxos_comuns,
        columns=fluxos_comuns
    )

    return corr_ref


def media_fora_diagonal_por_fluxo(corr):
    """
    Calcula, para cada fluxo, a média de correlação com os demais fluxos.

    A diagonal é ignorada porque representa a correlação do fluxo com ele mesmo.
    """

    arr = corr.to_numpy(dtype=float).copy()

    if arr.shape[0] != arr.shape[1]:
        raise ValueError("A matriz de correlação precisa ser quadrada.")

    np.fill_diagonal(arr, np.nan)

    with np.errstate(all="ignore"):
        medias = np.nanmean(arr, axis=1)

    return pd.Series(medias, index=corr.index, name="media_corr_ref")


def categorizar_media_corr(valor, limiar=0.20):
    if pd.isna(valor):
        return "indefinida"

    if valor > limiar:
        return "positiva"

    if valor < -limiar:
        return "negativa"

    return "baixa"


def ordenar_fluxos_por_media_corr(
    corr_antes,
    corr_depois,
    limiar=0.20,
    ordem_blocos=None,
):
    """
    Define a ordem visual dos fluxos usando apenas a média de correlação.

    Passos:
    1. Cria uma matriz de referência = média entre corr_antes e corr_depois.
    2. Calcula a média de correlação de cada fluxo com os demais.
    3. Classifica cada fluxo como positiva, baixa, negativa ou indefinida.
    4. Ordena os fluxos por bloco.

    Nada aqui altera os valores das matrizes de correlação.
    """

    if ordem_blocos is None:
        ordem_blocos = ["positiva", "baixa", "negativa", "indefinida"]

    corr_ref = criar_matriz_referencia_corr(corr_antes, corr_depois)
    media_corr = media_fora_diagonal_por_fluxo(corr_ref)

    df_ordem = pd.DataFrame({
        "fluxo": media_corr.index,
        "media_corr_ref": media_corr.values,
    })

    df_ordem["categoria_corr"] = df_ordem["media_corr_ref"].apply(
        lambda x: categorizar_media_corr(x, limiar=limiar)
    )

    mapa_bloco = {nome: i for i, nome in enumerate(ordem_blocos)}
    df_ordem["ordem_bloco"] = df_ordem["categoria_corr"].map(mapa_bloco)
    df_ordem["ordem_bloco"] = df_ordem["ordem_bloco"].fillna(len(ordem_blocos))

    # Chaves internas de ordenação:
    # - positiva: maior média primeiro
    # - baixa: mais próximo de zero primeiro
    # - negativa: mais negativa primeiro
    def chave_interna(row):
        cat = row["categoria_corr"]
        val = row["media_corr_ref"]

        if pd.isna(val):
            return np.inf

        if cat == "positiva":
            return -val

        if cat == "baixa":
            return abs(val)

        if cat == "negativa":
            return val

        return np.inf

    df_ordem["ordem_interna"] = df_ordem.apply(chave_interna, axis=1)

    df_ordem = df_ordem.sort_values(
        ["ordem_bloco", "ordem_interna", "fluxo"]
    ).reset_index(drop=True)

    df_ordem["posicao_plot"] = np.arange(len(df_ordem))

    ordem_fluxos = df_ordem["fluxo"].tolist()

    return ordem_fluxos, df_ordem


def reordenar_matriz_corr(corr, ordem_fluxos):
    fluxos_validos = [f for f in ordem_fluxos if f in corr.index and f in corr.columns]
    return corr.loc[fluxos_validos, fluxos_validos].copy()


def aplicar_mascara_triangulo(matriz, mascarar_diagonal=True):
    """
    Retorna uma matriz mascarada para exibir apenas o triângulo superior.

    Se mascarar_diagonal=True:
        esconde triângulo inferior + diagonal.

    Se mascarar_diagonal=False:
        esconde apenas triângulo inferior.
    """

    matriz = np.array(matriz, dtype=float)

    if mascarar_diagonal:
        idx = np.tril_indices_from(matriz, k=0)
    else:
        idx = np.tril_indices_from(matriz, k=-1)

    matriz[idx] = np.nan

    return matriz


def obter_limites_blocos(df_ordem):
    """
    Retorna posições onde os blocos positiva/baixa/negativa mudam.
    Usado para desenhar linhas divisórias na figura.
    """

    if df_ordem.empty:
        return []

    categorias = df_ordem["categoria_corr"].tolist()
    limites = []

    for i in range(1, len(categorias)):
        if categorias[i] != categorias[i - 1]:
            limites.append(i)

    return limites


def resumo_blocos(df_ordem):
    if df_ordem.empty:
        return "sem fluxos"

    cont = df_ordem["categoria_corr"].value_counts().to_dict()

    partes = []
    for cat in ORDEM_BLOCOS_CORR:
        if cat in cont:
            partes.append(f"{cat}={cont[cat]}")

    return " | ".join(partes)


def salvar_figura_correlacao_before_after_ordenada(
    corr_antes,
    corr_depois,
    dataset,
    detector,
    window,
    timestamp_drift,
    drift_numero,
    out_path,
    limiar_corr_baixa=0.20,
    ordem_blocos=None,
    plotar_triangulo_superior=True,
    mascarar_diagonal=True,
    desenhar_separadores=True,
):
    """
    Salva uma única figura com duas janelas:
    - Before
    - After

    A correlação não é recalculada nem alterada.
    Apenas reordenamos linhas/colunas para melhorar a visualização.
    """

    if corr_antes.empty or corr_depois.empty:
        return False, pd.DataFrame()

    fluxos_comuns = corr_antes.index.intersection(corr_depois.index)

    if len(fluxos_comuns) == 0:
        return False, pd.DataFrame()

    corr_antes = corr_antes.loc[fluxos_comuns, fluxos_comuns]
    corr_depois = corr_depois.loc[fluxos_comuns, fluxos_comuns]

    ordem_fluxos, df_ordem = ordenar_fluxos_por_media_corr(
        corr_antes=corr_antes,
        corr_depois=corr_depois,
        limiar=limiar_corr_baixa,
        ordem_blocos=ordem_blocos,
    )

    corr_antes_ord = reordenar_matriz_corr(corr_antes, ordem_fluxos)
    corr_depois_ord = reordenar_matriz_corr(corr_depois, ordem_fluxos)

    matriz_antes = corr_antes_ord.to_numpy(dtype=float)
    matriz_depois = corr_depois_ord.to_numpy(dtype=float)

    if plotar_triangulo_superior:
        matriz_antes = aplicar_mascara_triangulo(
            matriz_antes,
            mascarar_diagonal=mascarar_diagonal
        )
        matriz_depois = aplicar_mascara_triangulo(
            matriz_depois,
            mascarar_diagonal=mascarar_diagonal
        )

    n = len(ordem_fluxos)

    largura = max(12, min(26, n * 0.16 + 10))
    altura = max(6, min(13, n * 0.08 + 5))

    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad(color="white")

    fig, axes = plt.subplots(1, 2, figsize=(largura, altura))

    im1 = axes[0].imshow(
        matriz_antes,
        cmap=cmap,
        vmin=-1,
        vmax=1,
        aspect="equal",
        interpolation="nearest"
    )

    im2 = axes[1].imshow(
        matriz_depois,
        cmap=cmap,
        vmin=-1,
        vmax=1,
        aspect="equal",
        interpolation="nearest"
    )

    limites_blocos = obter_limites_blocos(df_ordem)

    for ax, titulo in zip(axes, ["Before", "After"]):
        ax.set_title(titulo, fontsize=14, pad=10)
        ax.set_xticks([])
        ax.set_yticks([])

        if desenhar_separadores:
            for limite in limites_blocos:
                pos_linha = limite - 0.5
                ax.axhline(pos_linha, color="black", linewidth=0.6, alpha=0.35)
                ax.axvline(pos_linha, color="black", linewidth=0.6, alpha=0.35)

    blocos_txt = resumo_blocos(df_ordem)

    fig.suptitle(
        f"Flow Correlation Matrix | {dataset} | "
        f"Timestamp: {timestamp_drift} \n",
        fontsize=18,
        y=0.90
    )

    fig.subplots_adjust(
        left=0.04,
        right=0.88,
        bottom=0.06,
        top=0.84,
        wspace=0.08
    )

    cbar_ax = fig.add_axes([0.90, 0.18, 0.018, 0.62])
    cbar = fig.colorbar(im2, cax=cbar_ax)
    cbar.set_label("Correlation", rotation=90, fontsize=11)

    fig.savefig(out_path, dpi=DPI_FIGURA, bbox_inches="tight")
    plt.close(fig)

    return True, df_ordem


def resumo_estatistico_correlacao(corr_antes, corr_depois):
    """
    Resumo estatístico das correlações before/after.
    Usa apenas elementos fora da diagonal.
    """

    fluxos_comuns = corr_antes.index.intersection(corr_depois.index)

    if len(fluxos_comuns) == 0:
        return {
            "n_correlacoes_antes": 0,
            "n_correlacoes_depois": 0,
            "media_corr_antes": np.nan,
            "media_corr_depois": np.nan,
            "delta_media_corr": np.nan,
            "media_abs_corr_antes": np.nan,
            "media_abs_corr_depois": np.nan,
            "delta_media_abs_corr": np.nan,
        }

    corr_antes = corr_antes.loc[fluxos_comuns, fluxos_comuns]
    corr_depois = corr_depois.loc[fluxos_comuns, fluxos_comuns]

    n = corr_antes.shape[0]
    mask_fora_diag = ~np.eye(n, dtype=bool)

    vals_antes = corr_antes.to_numpy(dtype=float)[mask_fora_diag]
    vals_depois = corr_depois.to_numpy(dtype=float)[mask_fora_diag]

    vals_antes = vals_antes[np.isfinite(vals_antes)]
    vals_depois = vals_depois[np.isfinite(vals_depois)]

    media_antes = np.mean(vals_antes) if len(vals_antes) else np.nan
    media_depois = np.mean(vals_depois) if len(vals_depois) else np.nan

    media_abs_antes = np.mean(np.abs(vals_antes)) if len(vals_antes) else np.nan
    media_abs_depois = np.mean(np.abs(vals_depois)) if len(vals_depois) else np.nan

    return {
        "n_correlacoes_antes": int(len(vals_antes)),
        "n_correlacoes_depois": int(len(vals_depois)),
        "media_corr_antes": float(media_antes) if np.isfinite(media_antes) else np.nan,
        "media_corr_depois": float(media_depois) if np.isfinite(media_depois) else np.nan,
        "delta_media_corr": (
            float(media_depois - media_antes)
            if np.isfinite(media_antes) and np.isfinite(media_depois)
            else np.nan
        ),
        "media_abs_corr_antes": (
            float(media_abs_antes)
            if np.isfinite(media_abs_antes)
            else np.nan
        ),
        "media_abs_corr_depois": (
            float(media_abs_depois)
            if np.isfinite(media_abs_depois)
            else np.nan
        ),
        "delta_media_abs_corr": (
            float(media_abs_depois - media_abs_antes)
            if np.isfinite(media_abs_antes) and np.isfinite(media_abs_depois)
            else np.nan
        ),
    }


# ============================================================
# EXECUÇÃO
# ============================================================

df_base = df_drifts_detalhado.copy()

if DATASETS_FILTRAR is not None:
    df_base = df_base[df_base["dataset"].isin(DATASETS_FILTRAR)]

if DETECTORES_FILTRAR is not None:
    df_base = df_base[df_base["detector"].isin(DETECTORES_FILTRAR)]

df_base["timestamp"] = pd.to_datetime(df_base["timestamp"])

linhas_resumo = []

total_salvos = 0
total_pulados = 0

for dataset_name, df_dataset in df_base.groupby("dataset"):

    df_analise = obter_df_para_analise(
        dataset_name=dataset_name,
        modo_serie=MODO_SERIE
    )

    for (detector, window), df_config in df_dataset.groupby(["detector", "window"]):

        df_config = df_config.sort_values("timestamp").reset_index(drop=True)

        if MAX_DRIFTS_POR_CONFIG is not None:
            df_config = df_config.head(MAX_DRIFTS_POR_CONFIG)

        pasta_config = (
            OUT_DIR
            / nome_seguro(dataset_name)
            / nome_seguro(detector)
            / f"window_{int(window)}"
        )
        pasta_config.mkdir(parents=True, exist_ok=True)

        pasta_ordens = pasta_config / "ordem_fluxos"
        if SALVAR_ORDEM_FLUXOS:
            pasta_ordens.mkdir(parents=True, exist_ok=True)

        for i, row in df_config.iterrows():

            drift_numero = i + 1
            timestamp_drift = pd.to_datetime(row["timestamp"])

            (
                df_antes,
                df_depois,
                pos,
                tamanho,
                shape_antes,
                shape_depois
            ) = extrair_janelas_antes_depois_fluxos(
                df_base=df_analise,
                timestamp_drift=timestamp_drift,
                window=int(window),
                fator_janela=FATOR_JANELA,
                normalizar_por_fluxo=NORMALIZAR_POR_FLUXO
            )

            if (
                df_antes is None or
                df_depois is None or
                df_antes.empty or
                df_depois.empty
            ):
                total_pulados += 1

                linhas_resumo.append({
                    "dataset": dataset_name,
                    "detector": detector,
                    "window": window,
                    "drift_numero": drift_numero,
                    "timestamp": timestamp_drift,
                    "status": "pulado_sem_janela_suficiente",
                    "arquivo_corr_before_after": "",
                    "arquivo_ordem_fluxos": "",
                })
                continue

            df_antes_plot, df_depois_plot, fluxos_usados = manter_todos_fluxos_comuns(
                df_antes=df_antes,
                df_depois=df_depois
            )

            corr_antes = calcular_matriz_correlacao(df_antes_plot)
            corr_depois = calcular_matriz_correlacao(df_depois_plot)

            timestamp_nome = nome_seguro(timestamp_drift)

            df_problemas_corr = diagnosticar_fluxos_problematicos(
                df_antes=df_antes_plot,
                df_depois=df_depois_plot,
                corr_antes=corr_antes,
                corr_depois=corr_depois,
                dataset=dataset_name,
                detector=detector,
                window=int(window),
                drift_numero=drift_numero,
                timestamp_drift=timestamp_drift,
                row_drift=row,
            )

            adicionar_problemas_ao_log(
                df_problemas=df_problemas_corr,
                linhas_log=linhas_log_problemas
            )


            arquivo_corr = (
                pasta_config
                / f"drift_{drift_numero:04d}_{timestamp_nome}_correlacao_before_after_ordenada.png"
            )

            arquivo_ordem = (
                pasta_ordens
                / f"drift_{drift_numero:04d}_{timestamp_nome}_ordem_fluxos.csv"
            )

            corr_ok, df_ordem_fluxos = salvar_figura_correlacao_before_after_ordenada(
                corr_antes=corr_antes,
                corr_depois=corr_depois,
                dataset=dataset_name,
                detector=detector,
                window=int(window),
                timestamp_drift=timestamp_drift,
                drift_numero=drift_numero,
                out_path=arquivo_corr,
                limiar_corr_baixa=LIMIAR_CORR_BAIXA,
                ordem_blocos=ORDEM_BLOCOS_CORR,
                plotar_triangulo_superior=PLOTAR_APENAS_TRIANGULO_SUPERIOR,
                mascarar_diagonal=MASCARAR_DIAGONAL,
                desenhar_separadores=DESENHAR_SEPARADORES_BLOCOS,
            )

            if corr_ok:
                total_salvos += 1

            if SALVAR_ORDEM_FLUXOS and corr_ok and not df_ordem_fluxos.empty:
                df_ordem_fluxos.to_csv(arquivo_ordem, index=False)
                arquivo_ordem_txt = str(arquivo_ordem)
            else:
                arquivo_ordem_txt = ""

            stats = resumo_estatistico_correlacao(corr_antes, corr_depois)

            # Contagem dos blocos usados na ordenação visual
            if not df_ordem_fluxos.empty:
                cont_blocos = df_ordem_fluxos["categoria_corr"].value_counts().to_dict()
            else:
                cont_blocos = {}

            linha = {
                "dataset": dataset_name,
                "detector": detector,
                "window": window,
                "drift_numero": drift_numero,
                "timestamp": timestamp_drift,
                "modo_serie": MODO_SERIE,
                "fator_janela": FATOR_JANELA,
                "normalizar_por_fluxo": NORMALIZAR_POR_FLUXO,
                "transformacao_corr": TRANSFORMACAO_CORR,
                "limiar_corr_baixa": LIMIAR_CORR_BAIXA,
                "ordem_blocos_corr": " -> ".join(ORDEM_BLOCOS_CORR),
                "plotar_apenas_triangulo_superior": PLOTAR_APENAS_TRIANGULO_SUPERIOR,
                "mascarar_diagonal": MASCARAR_DIAGONAL,
                "tamanho_janela_lado_em_timestamps": tamanho,
                "n_fluxos_antes": shape_antes[1],
                "n_fluxos_depois": shape_depois[1],
                "n_fluxos_plotados": len(fluxos_usados),
                "n_timestamps_antes": shape_antes[0],
                "n_timestamps_depois": shape_depois[0],
                "n_fluxos_corr_positiva": int(cont_blocos.get("positiva", 0)),
                "n_fluxos_corr_baixa": int(cont_blocos.get("baixa", 0)),
                "n_fluxos_corr_negativa": int(cont_blocos.get("negativa", 0)),
                "n_fluxos_corr_indefinida": int(cont_blocos.get("indefinida", 0)),
                "status": "ok" if corr_ok else "correlacao_nao_salva",
                "arquivo_corr_before_after": str(arquivo_corr) if corr_ok else "",
                "arquivo_ordem_fluxos": arquivo_ordem_txt,
            }

            linha.update(stats)
            linhas_resumo.append(linha)

        print(
            f"{dataset_name} | {detector} | window={window} "
            f"-> processados {len(df_config)} drifts"
        )


df_resumo_corr = pd.DataFrame(linhas_resumo)

path_resumo = OUT_DIR / "resumo_figuras_correlacao_before_after_ordenadas.csv"
df_resumo_corr.to_csv(path_resumo, index=False)

if linhas_log_problemas:
    with open(LOG_PROBLEMAS_CORR, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas_log_problemas))

    print(f"Log de problemas salvo em: {LOG_PROBLEMAS_CORR}")
else:
    print("Nenhum problema de correlação encontrado.")

print("\nFinalizado.")
print(f"Figuras before/after salvas: {total_salvos}")
print(f"Drifts pulados: {total_pulados}")
print(f"Pasta principal: {OUT_DIR}")
print(f"Resumo salvo em: {path_resumo}")