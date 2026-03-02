# =========================
# CLA+ 2024/2025 vs LO's
# Exporta resultados a Excel
# =========================

import io
import numpy as np
import pandas as pd

from google.colab import files

from scipy.stats import pearsonr, spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LassoCV
from sklearn.model_selection import KFold

# -------------------------
# Helpers
# -------------------------
def normalize_id(s):
    return (
        s.astype(str)
         .str.strip()
         .str.upper()
    )

def pick_score_column(df, preferred_keywords=("cla_total", "total", "score")):
    """
    Intenta detectar la columna de puntaje total CLA+.
    Prioriza coincidencias por keywords en el nombre.
    """
    cols = [c for c in df.columns]
    lower = {c: c.lower() for c in cols}

    # candidatos numéricos
    num_cols = []
    for c in cols:
        if c.lower() in ("matricula", "id", "student_id"):
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            num_cols.append(c)

    # preferidos por keyword
    for kw in preferred_keywords:
        hits = [c for c in num_cols if kw in lower[c]]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            # si hay varios, elige el de menor % nulos
            hits = sorted(hits, key=lambda x: df[x].isna().mean())
            return hits[0]

    # fallback: el numérico con menos nulos
    if num_cols:
        num_cols = sorted(num_cols, key=lambda x: df[x].isna().mean())
        return num_cols[0]

    raise ValueError("No se pudo detectar una columna numérica de score en el archivo CLA+.")

def fdr_bh(pvals):
    """
    Benjamini-Hochberg FDR correction.
    Devuelve q-values en el mismo orden.
    """
    pvals = np.array(pvals, dtype=float)
    n = len(pvals)
    order = np.argsort(pvals)
    ranked = pvals[order]
    q = np.empty(n, dtype=float)
    prev = 1.0
    for i in range(n-1, -1, -1):
        rank = i + 1
        val = ranked[i] * n / rank
        prev = min(prev, val)
        q[i] = prev
    out = np.empty(n, dtype=float)
    out[order] = q
    return out

def corr_table(df, y_col, lo_cols):
    rows = []
    for lo in lo_cols:
        sub = df[[y_col, lo]].dropna()
        if len(sub) < 10:
            continue
        r_p, p_p = pearsonr(sub[y_col], sub[lo])
        r_s, p_s = spearmanr(sub[y_col], sub[lo])
        rows.append({
            "LO": lo,
            "n": len(sub),
            "pearson_r": r_p,
            "pearson_p": p_p,
            "spearman_r": r_s,
            "spearman_p": p_s
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["pearson_q_fdr"] = fdr_bh(out["pearson_p"].values)
    out["spearman_q_fdr"] = fdr_bh(out["spearman_p"].values)
    out["abs_pearson_r"] = out["pearson_r"].abs()
    out = out.sort_values("abs_pearson_r", ascending=False).drop(columns=["abs_pearson_r"])
    return out

# -------------------------
# 1) Cargar archivos
# -------------------------
print("Sube 3 archivos: cla_2024.csv, cla_2025.csv, los.csv")
uploaded = files.upload()

def read_csv_from_upload(name_hint):
    # busca por substring
    matches = [k for k in uploaded.keys() if name_hint in k.lower()]
    if not matches:
        raise FileNotFoundError(f"No encontré archivo con '{name_hint}' en el nombre. Archivos: {list(uploaded.keys())}")
    fname = matches[0]
    return fname, pd.read_csv(io.BytesIO(uploaded[fname]))

cla24_name, cla24 = read_csv_from_upload("2024")
cla25_name, cla25 = read_csv_from_upload("2025")
los_name, los = read_csv_from_upload("lo")

print("Cargados:", cla24_name, cla25_name, los_name)

# -------------------------
# 2) Normalizar llaves
# -------------------------
# Ajusta aquí si tu llave no se llama 'matricula'
id_col = "matricula"
for d in (cla24, cla25, los):
    if id_col not in d.columns:
        # intenta detectar alternativas
        candidates = [c for c in d.columns if c.lower() in ("matricula","id","student_id","studentid")]
        if candidates:
            d.rename(columns={candidates[0]: id_col}, inplace=True)
        else:
            raise ValueError(f"No encontré columna de ID en uno de los archivos. Columnas: {d.columns.tolist()}")

cla24[id_col] = normalize_id(cla24[id_col])
cla25[id_col] = normalize_id(cla25[id_col])
los[id_col]   = normalize_id(los[id_col])

# -------------------------
# 3) Detectar score total CLA+ por año
# -------------------------
y24 = pick_score_column(cla24)
y25 = pick_score_column(cla25)
cla24 = cla24[[id_col, y24]].rename(columns={y24: "cla_total_2024"})
cla25 = cla25[[id_col, y25]].rename(columns={y25: "cla_total_2025"})

# -------------------------
# 4) Preparar LO's (formato wide)
# -------------------------
# Si tu LO viene en formato largo (matricula, lo, valor), aquí habría que pivotear.
# Por ahora asumimos wide: columnas numéricas son LO's.
exclude = {id_col, "ciclo", "curso", "trimestre", "year", "anio"}
lo_cols = [c for c in los.columns
           if c not in exclude and pd.api.types.is_numeric_dtype(los[c])]

if len(lo_cols) == 0:
    raise ValueError("No detecté columnas numéricas de LO en los.csv. Revisa el formato.")

los_w = los[[id_col] + lo_cols].copy()

# -------------------------
# 5) Merge y deltas
# -------------------------
df = (cla24.merge(cla25, on=id_col, how="outer")
           .merge(los_w, on=id_col, how="left"))

df["cla_delta_24_25"] = df["cla_total_2025"] - df["cla_total_2024"]

# -------------------------
# 6) Correlaciones
# -------------------------
corr24 = corr_table(df, "cla_total_2024", lo_cols)
corr25 = corr_table(df, "cla_total_2025", lo_cols)
corrD  = corr_table(df, "cla_delta_24_25", lo_cols)

# -------------------------
# 7) LASSO: seleccionar LO's que predicen CLA+ (2025 y delta)
# -------------------------
def lasso_select(target_col):
    sub = df[[target_col] + lo_cols].dropna()
    if len(sub) < 30:
        return pd.DataFrame(), "Muestra insuficiente para LASSO (se recomienda n>=30 con datos completos)."

    X = sub[lo_cols].values
    y = sub[target_col].values

    # estandarización
    Xs = StandardScaler().fit_transform(X)

    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    model = LassoCV(cv=cv, random_state=42, n_alphas=100).fit(Xs, y)

    coefs = pd.Series(model.coef_, index=lo_cols)
    nonzero = coefs[coefs != 0].sort_values(key=lambda s: s.abs(), ascending=False)

    out = nonzero.reset_index()
    out.columns = ["LO", "coef"]
    meta = f"alpha={model.alpha_:.6f} | n={len(sub)} | selected={len(nonzero)}"
    return out, meta

lasso25, meta25 = lasso_select("cla_total_2025")
lassoD,  metaD  = lasso_select("cla_delta_24_25")

# -------------------------
# 8) Resumen ejecutivo (top LO's)
# -------------------------
def top_los(corr_df, k=10):
    if corr_df.empty:
        return []
    return corr_df.head(k)[["LO","pearson_r","pearson_p","pearson_q_fdr","n"]].to_dict("records")

summary = {
    "N_total_ids": int(df[id_col].nunique()),
    "N_with_CLA_2024": int(df["cla_total_2024"].notna().sum()),
    "N_with_CLA_2025": int(df["cla_total_2025"].notna().sum()),
    "N_with_LO": int(df[lo_cols].notna().any(axis=1).sum()),
    "Top_LOs_CLA_2024": top_los(corr24, 10),
    "Top_LOs_CLA_2025": top_los(corr25, 10),
    "Top_LOs_Delta": top_los(corrD, 10),
    "LASSO_meta_2025": meta25,
    "LASSO_meta_delta": metaD
}
summary_df = pd.DataFrame([summary])

# -------------------------
# 9) Exportar a Excel
# -------------------------
out_name = "Resultados_CLA_2024_2025_vs_LOs.xlsx"
with pd.ExcelWriter(out_name, engine="openpyxl") as writer:
    summary_df.to_excel(writer, index=False, sheet_name="summary")
    corr24.to_excel(writer, index=False, sheet_name="corr_CLA2024")
    corr25.to_excel(writer, index=False, sheet_name="corr_CLA2025")
    corrD.to_excel(writer, index=False, sheet_name="corr_Delta")
    lasso25.to_excel(writer, index=False, sheet_name="lasso_CLA2025")
    lassoD.to_excel(writer, index=False, sheet_name="lasso_Delta")

print("Archivo generado:", out_name)
files.download(out_name)
