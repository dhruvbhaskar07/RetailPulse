"""
RetailPulse — Custom Dataset Import Page
Supports: CSV, Excel (.xlsx/.xls), JSON, Parquet
Features:
  - Auto-detect column types + schema
  - Smart column mapping (auto-detect standard columns)
  - Data preview + quality report
  - Stores in session_state["data_cache"] as "custom_*"
  - All existing pages will show custom data if mapped correctly
"""
import io
import json
import time
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.dashboard.components.ui import (
    section_header, alert_card, metric_card, kpi_hero,
    chart_container, empty_state, methodology_card,
)

from src.dashboard.config import (
    SCHEMA_TEMPLATES,
    COLUMN_ALIASES,
    IMPORT_ALLOWED_ROLES,
    MAX_IMPORT_ROWS,
    MISSING_DATA_WARN_PCT,
    MISSING_DATA_HIGH_PCT,
    PALETTE,
)

PAGE_ICON = "⬆️"

SUPPORTED_TYPES = {
    "csv":     "text/csv",
    "xlsx":    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls":     "application/vnd.ms-excel",
    "json":    "application/json",
    "parquet": "application/octet-stream",
}


def _detect_col_mapping(df_cols: list[str], required: list[str], optional: list[str]) -> dict:
    """Auto-detect which uploaded columns match schema columns using config COLUMN_ALIASES."""
    mapping = {}
    all_schema = required + optional
    df_cols_lower = {c: c.lower().replace(" ", "_").replace("-", "_") for c in df_cols}

    for schema_col in all_schema:
        # Exact match
        if schema_col in df_cols:
            mapping[schema_col] = schema_col
            continue

        # Check aliases from config
        aliases = COLUMN_ALIASES.get(schema_col, [schema_col])
        found = False
        for alias in aliases:
            norm_alias = alias.lower().replace(" ", "_").replace("-", "_")
            for orig_col, norm_col in df_cols_lower.items():
                if norm_col == norm_alias:
                    mapping[schema_col] = orig_col
                    found = True
                    break
            if found:
                break

        if not found:
            # Partial keyword match as fallback
            for orig_col, norm_col in df_cols_lower.items():
                if any(keyword in norm_col for keyword in schema_col.split("_")):
                    mapping[schema_col] = orig_col
                    break
    return mapping


def _quality_report(df: pd.DataFrame) -> dict:
    """Generate data quality metrics."""
    total_cells = df.shape[0] * df.shape[1]
    missing = df.isnull().sum().sum()
    duplicates = df.duplicated().sum()
    return {
        "rows":       len(df),
        "cols":       len(df.columns),
        "missing":    missing,
        "missing_pct": (missing / total_cells * 100) if total_cells > 0 else 0,
        "duplicates": duplicates,
        "dup_pct":    (duplicates / len(df) * 100) if len(df) > 0 else 0,
        "dtypes":     df.dtypes.value_counts().to_dict(),
    }


def _read_file(uploaded_file) -> tuple[pd.DataFrame | None, str]:
    """Read uploaded file into a DataFrame. Returns (df, error_msg)."""
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
    try:
        if ext == "csv":
            # Try multiple encodings
            for enc in ["utf-8", "latin-1", "cp1252"]:
                try:
                    df = pd.read_csv(uploaded_file, encoding=enc, low_memory=False)
                    uploaded_file.seek(0)
                    return df, ""
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    continue
            return None, "Could not decode CSV — try saving as UTF-8."
        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(uploaded_file)
            return df, ""
        elif ext == "json":
            content = uploaded_file.read()
            data = json.loads(content)
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data]) if not any(isinstance(v, list) for v in data.values()) \
                     else pd.DataFrame(data)
            else:
                return None, "JSON must be a list of objects or a dict of arrays."
            return df, ""
        elif ext == "parquet":
            df = pd.read_parquet(io.BytesIO(uploaded_file.read()))
            return df, ""
        else:
            return None, f"Unsupported format: .{ext}"
    except Exception as e:
        return None, str(e)


def _apply_mapping_and_transform(df: pd.DataFrame, mapping: dict, schema_key: str) -> pd.DataFrame:
    """Rename columns according to mapping and do type coercion."""
    reverse_map = {v: k for k, v in mapping.items() if v}
    df = df.rename(columns=reverse_map)

    # Parse date columns
    for date_col in ["date", "invoice_date", "order_date", "purchase_date"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            if date_col != "date":
                df = df.rename(columns={date_col: "date"})
            break

    # Coerce numeric columns
    numeric_cols = ["revenue", "quantity", "total_quantity", "churn_risk_score",
                    "recency", "frequency", "monetary", "stock_level",
                    "urgency_score", "days_of_supply", "recommended_order_qty"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Add churn_risk_level if missing but score exists
    if schema_key == "churn_scores" and "churn_risk_score" in df.columns and "churn_risk_level" not in df.columns:
        from src.dashboard.utils import score_to_risk_level
        df["churn_risk_level"] = df["churn_risk_score"].apply(score_to_risk_level)

    # Add urgency flags for inventory
    if schema_key == "inventory_recommendations":
        from src.dashboard.config import STOCKOUT_DAYS_CRITICAL, URGENCY_SCORE_MAX
        if "is_stockout_risk" not in df.columns and "days_of_supply" in df.columns:
            df["is_stockout_risk"] = df["days_of_supply"] < STOCKOUT_DAYS_CRITICAL
        if "is_below_reorder" not in df.columns and "stock_level" in df.columns and "reorder_point_calculated" in df.columns:
            df["is_below_reorder"] = df["stock_level"] < df["reorder_point_calculated"]
        if "urgency_score" not in df.columns and "days_of_supply" in df.columns:
            from src.dashboard.utils import compute_urgency
            df["urgency_score"] = compute_urgency(df["days_of_supply"])

    return df


def render():
    from src.dashboard.utils import can_import

    # ── Role Guard ────────────────────────────────────────────────
    if not can_import():
        alert_card(
            "Access Restricted",
            "Only authorized roles can import custom datasets. "
            "Contact your administrator to request access.",
            variant="danger", icon="🔒",
        )
        return

    methodology_card(
        "Custom Dataset Import",
        "Upload your own CSV, Excel, JSON, or Parquet file. RetailPulse will auto-detect column types, "
        "suggest a schema mapping, validate data quality, and store the dataset so all dashboard pages "
        "use it automatically. Supported targets: Sales, Forecast, Segments, Churn, Inventory.",
        icon="📤",
    )

    # ── Dataset Type Selector ─────────────────────────────────────
    section_header("Step 1 — Choose Dataset Type", icon="🎯")
    template_names = list(SCHEMA_TEMPLATES.keys())
    template_icons = [SCHEMA_TEMPLATES[t]["icon"] for t in template_names]

    sel_template = st.selectbox(
        "Dataset Type",
        template_names,
        format_func=lambda t: f"{SCHEMA_TEMPLATES[t]['icon']}  {t}",
        help="Choose which page this dataset should power",
    )
    tmpl = SCHEMA_TEMPLATES[sel_template]

    st.markdown(
        f'<div class="info-card">'
        f'<h4>{tmpl["icon"]} {sel_template}</h4>'
        f'<p>{tmpl["description"]}'
        + (f'<br><br><strong>Required columns:</strong> <code>{", ".join(tmpl["required"])}</code>' if tmpl["required"] else "")
        + (f'<br><strong>Optional columns:</strong> <code>{", ".join(tmpl["optional"])}</code>' if tmpl["optional"] else "")
        + f'</p></div>',
        unsafe_allow_html=True,
    )

    # ── File Upload ───────────────────────────────────────────────
    section_header("Step 2 — Upload File", icon="📂")
    uploaded = st.file_uploader(
        "Drop your file here or click to browse",
        type=["csv", "xlsx", "xls", "json", "parquet"],
        help="Max 200 MB. CSV files must have a header row.",
        label_visibility="collapsed",
    )

    if uploaded is None:
        # Upload hints
        st.markdown(
            '''<div class="empty-state" style="margin-top:0.5rem;padding:2rem;">
              <div class="empty-state-icon">📂</div>
              <h3>No file uploaded yet</h3>
              <p>Supported formats: <strong>CSV · Excel (.xlsx/.xls) · JSON · Parquet</strong><br>
              Max size: 200 MB &nbsp;·&nbsp; Header row required for CSV/Excel</p>
            </div>''',
            unsafe_allow_html=True,
        )
        return

    # ── Reading File ──────────────────────────────────────────────
    with st.spinner(f"⏳ Reading **{uploaded.name}** …"):
        time.sleep(0.3)  # micro-delay for visual effect
        df_raw, err = _read_file(uploaded)

    if err or df_raw is None:
        alert_card("File Read Error", err or "Unknown error reading file.", variant="danger", icon="❌")
        return

    if df_raw.empty:
        alert_card("Empty File", "The uploaded file has no rows.", variant="warn", icon="⚠️")
        return

    # ── Data Quality Report ───────────────────────────────────────
    section_header("Step 3 — Data Quality Overview", icon="🔍")
    qr = _quality_report(df_raw)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_hero(f"{qr['rows']:,}", "Rows", delta=f"{qr['cols']} columns", delta_dir="flat", cls="teal")
    with c2:
        warn_pct = qr["missing_pct"]
        kpi_hero(f"{warn_pct:.1f}%", "Missing Data",
                 delta=f"{qr['missing']:,} cells",
                 delta_dir="down" if warn_pct > MISSING_DATA_WARN_PCT else "flat",
                 cls="danger" if warn_pct > MISSING_DATA_HIGH_PCT else ("warm" if warn_pct > MISSING_DATA_WARN_PCT else ""))
    with c3:
        kpi_hero(f"{qr['duplicates']:,}", "Duplicate Rows",
                 delta=f"{qr['dup_pct']:.1f}% of total",
                 delta_dir="down" if qr['duplicates'] > 0 else "flat",
                 cls="warm" if qr['duplicates'] > 0 else "teal")
    with c4:
        numeric_count = sum(1 for dt in df_raw.dtypes if pd.api.types.is_numeric_dtype(dt))
        kpi_hero(f"{numeric_count}", "Numeric Cols",
                 delta=f"{qr['cols'] - numeric_count} non-numeric",
                 delta_dir="flat", cls="violet")

    # Quality warnings
    if qr["missing_pct"] > MISSING_DATA_HIGH_PCT:
        alert_card("High Missing Data Rate",
                   f"{qr['missing_pct']:.1f}% of cells are empty. Consider cleaning before import.",
                   variant="warn", icon="⚠️")
    if qr["duplicates"] > 0:
        alert_card(f"{qr['duplicates']:,} Duplicate Rows Detected",
                   "Duplicates will be kept unless you choose to remove them below.",
                   variant="warn", icon="⚠️")

    # ── Column Type Preview ───────────────────────────────────────
    with st.expander("📋 Column Summary", expanded=False):
        col_info = pd.DataFrame({
            "Column": df_raw.columns,
            "Type": [str(t) for t in df_raw.dtypes],
            "Non-Null": df_raw.notna().sum().values,
            "Null %": (df_raw.isnull().mean() * 100).round(1).values,
            "Sample Value": [str(df_raw[c].dropna().iloc[0]) if not df_raw[c].dropna().empty else "—"
                             for c in df_raw.columns],
        })
        st.dataframe(col_info, use_container_width=True)

    # ── Column Mapping ────────────────────────────────────────────
    section_header("Step 4 — Column Mapping", icon="🔗")
    st.markdown(
        '<p style="color:#94a3b8;font-size:0.8rem;margin-bottom:0.8rem;">'
        'RetailPulse auto-detected the best column matches. '
        'Adjust any mapping below if needed, then click Import.</p>',
        unsafe_allow_html=True,
    )

    df_cols    = list(df_raw.columns)
    all_schema = tmpl["required"] + tmpl["optional"]
    auto_map   = _detect_col_mapping(df_cols, tmpl["required"], tmpl["optional"])
    NONE_OPT   = "— (not mapped)"

    mapping = {}
    if all_schema:
        req_set = set(tmpl["required"])
        col_count = min(3, len(all_schema))
        rows = [all_schema[i:i+col_count] for i in range(0, len(all_schema), col_count)]
        for row_cols in rows:
            cols_ui = st.columns(col_count)
            for schema_col, col_ui in zip(row_cols, cols_ui):
                is_required = schema_col in req_set
                auto_detected = auto_map.get(schema_col)
                options = df_cols if is_required else [NONE_OPT] + df_cols
                default_idx = 0
                if auto_detected:
                    try:
                        default_idx = options.index(auto_detected)
                    except ValueError:
                        pass
                label_badge = " 🔴" if is_required else " ⚪"
                sel = col_ui.selectbox(
                    f"`{schema_col}`{label_badge}",
                    options,
                    index=default_idx,
                    key=f"map_{schema_col}",
                    help=f"{'Required' if is_required else 'Optional'} field",
                )
                mapping[schema_col] = None if sel == NONE_OPT else sel
    else:
        # Custom Raw — no mapping needed
        st.info("ℹ️ Custom Raw mode: all columns will be kept as-is.")
        for col in df_cols:
            mapping[col] = col

    # Validation: required columns must be mapped
    missing_required = [c for c in tmpl["required"] if not mapping.get(c)]
    if missing_required:
        st.markdown(
            f'<div class="alert-card danger"><div class="alert-card-icon">❌</div>'
            f'<div><h3>Missing Required Columns</h3>'
            f'<p>Please map these required fields: <strong>{", ".join(missing_required)}</strong></p>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # ── Pre-processing Options ────────────────────────────────────
    section_header("Step 5 — Processing Options", icon="⚙️")
    c1, c2, c3 = st.columns(3)
    with c1:
        drop_dupes  = st.checkbox("Drop duplicate rows", value=qr["duplicates"] > 0)
    with c2:
        drop_nulls  = st.checkbox("Drop rows with any null in required cols", value=False)
    with c3:
        sample_cap  = st.number_input("Row limit (0 = all rows)", min_value=0, max_value=MAX_IMPORT_ROWS,
                                       value=0, step=10000,
                                       help="Cap import to first N rows. 0 means no limit.")

    # ── Data Preview ──────────────────────────────────────────────
    section_header("Step 6 — Data Preview", icon="👁️")
    with st.expander("Show raw preview (first 50 rows)", expanded=False):
        st.dataframe(df_raw.head(50), use_container_width=True)

    # ── Import Button ─────────────────────────────────────────────
    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
    can_import = not missing_required
    col_btn1, col_btn2, _ = st.columns([1, 1, 3])

    with col_btn1:
        do_import = st.button(
            "⬆️  Import Dataset",
            type="primary",
            use_container_width=True,
            disabled=not can_import,
            key="do_import_btn",
        )

    with col_btn2:
        # Clear custom data
        if st.button("🗑️ Clear Custom Data", use_container_width=True, key="clear_custom_btn"):
            cache = st.session_state.get("data_cache", {})
            removed = [k for k in list(cache.keys()) if k.startswith("custom_") or k in SCHEMA_TEMPLATES.values()]
            for k in removed:
                cache.pop(k, None)
            st.success(f"Cleared {len(removed)} custom dataset(s) from memory.")
            st.rerun()

    if do_import:
        progress_bar = st.progress(0)
        status_text  = st.empty()

        try:
            # Step 1 — Copy
            status_text.markdown(
                '<div style="color:#94a3b8;font-size:0.8rem">📋 Copying dataset…</div>',
                unsafe_allow_html=True,
            )
            df = df_raw.copy()
            progress_bar.progress(15)
            time.sleep(0.2)

            # Step 2 — Row cap
            if sample_cap and sample_cap > 0:
                df = df.head(sample_cap)
            status_text.markdown(
                f'<div style="color:#94a3b8;font-size:0.8rem">📐 Applying row limit ({len(df):,} rows)…</div>',
                unsafe_allow_html=True,
            )
            progress_bar.progress(25)
            time.sleep(0.15)

            # Step 3 — Drop dupes
            if drop_dupes:
                before = len(df)
                df = df.drop_duplicates()
                status_text.markdown(
                    f'<div style="color:#94a3b8;font-size:0.8rem">🔄 Removed {before - len(df):,} duplicates…</div>',
                    unsafe_allow_html=True,
                )
            progress_bar.progress(35)
            time.sleep(0.15)

            # Step 4 — Apply mapping + type coercion
            status_text.markdown(
                '<div style="color:#94a3b8;font-size:0.8rem">🔗 Mapping columns and coercing types…</div>',
                unsafe_allow_html=True,
            )
            df = _apply_mapping_and_transform(df, mapping, tmpl["cache_key"])
            progress_bar.progress(55)
            time.sleep(0.2)

            # Step 5 — Drop nulls in required cols
            if drop_nulls and tmpl["required"]:
                mapped_required = [mapping.get(c, c) for c in tmpl["required"] if mapping.get(c)]
                actual_req = [c for c in mapped_required if c in df.columns]
                before = len(df)
                df = df.dropna(subset=actual_req)
                status_text.markdown(
                    f'<div style="color:#94a3b8;font-size:0.8rem">🧹 Dropped {before - len(df):,} rows with nulls…</div>',
                    unsafe_allow_html=True,
                )
            progress_bar.progress(70)
            time.sleep(0.15)

            # Step 6 — Store in cache
            status_text.markdown(
                '<div style="color:#94a3b8;font-size:0.8rem">💾 Storing in session cache…</div>',
                unsafe_allow_html=True,
            )
            cache = st.session_state.setdefault("data_cache", {})
            cache_key = tmpl["cache_key"]
            cache[cache_key] = df
            # Also store a labeled copy so user can see what's imported
            cache[f"custom_{cache_key}"] = df
            # Track import history
            imports = st.session_state.setdefault("import_history", [])
            imports.append({
                "filename":  uploaded.name,
                "type":      sel_template,
                "cache_key": cache_key,
                "rows":      len(df),
                "cols":      len(df.columns),
                "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            })
            progress_bar.progress(100)
            time.sleep(0.3)

            status_text.empty()
            progress_bar.empty()

            # ── Success ────────────────────────────────────────────
            st.balloons()
            alert_card(
                f"✅ Dataset Imported Successfully — {len(df):,} rows · {len(df.columns)} columns",
                f'"{uploaded.name}" is now powering the **{sel_template}** data on all relevant pages. '
                f'Navigate to the appropriate page to see your data.',
                variant="ok", icon="🎉",
            )

            # ── Post-import Analytics ─────────────────────────────
            st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
            section_header("Import Summary & Quick Stats", icon="📊")

            c1, c2 = st.columns(2)
            with c1:
                # Column types donut
                dtype_counts = df.dtypes.astype(str).value_counts()
                fig = px.pie(
                    values=dtype_counts.values,
                    names=dtype_counts.index,
                    title="Column Type Distribution",
                    color_discrete_sequence=["#6366f1","#10b981","#f472b6","#f59e0b"],
                    hole=0.4,
                )
                fig.update_traces(textinfo="percent+label")
                chart_container(fig, height=260)

            with c2:
                # Missing data bar
                missing_by_col = (df.isnull().sum() / len(df) * 100).round(2)
                missing_by_col = missing_by_col[missing_by_col > 0].sort_values(ascending=False).head(10)
                if not missing_by_col.empty:
                    fig2 = go.Figure(go.Bar(
                        x=missing_by_col.values,
                        y=missing_by_col.index,
                        orientation="h",
                        marker=dict(color="#f59e0b", opacity=0.8),
                        hovertemplate="<b>%{y}</b><br>Missing: %{x:.1f}%<extra></extra>",
                    ))
                    fig2.update_layout(xaxis_title="% Missing", title="Missing Data by Column")
                    chart_container(fig2, height=260)
                else:
                    alert_card("Zero Missing Data!", "Your dataset is complete.", variant="ok", icon="🎉")

            # Numeric column distributions
            num_cols = df.select_dtypes(include="number").columns.tolist()
            if num_cols:
                section_header("Numeric Column Distribution", icon="📈")
                sel_col = st.selectbox("Select column to plot", num_cols, key="dist_col")
                fig3 = go.Figure(go.Histogram(
                    x=df[sel_col].dropna(),
                    nbinsx=40,
                    marker=dict(color="#6366f1", opacity=0.8),
                    hovertemplate=f"{sel_col}: %{{x}}<br>Count: %{{y}}<extra></extra>",
                ))
                chart_container(fig3, height=280)

            # Preview imported data
            with st.expander("📄 Preview Imported Dataset", expanded=False):
                st.dataframe(df.head(100), use_container_width=True)

        except Exception as exc:
            progress_bar.empty()
            status_text.empty()
            alert_card("Import Failed", str(exc), variant="danger", icon="❌")

    # ── Import History ────────────────────────────────────────────
    history = st.session_state.get("import_history", [])
    if history:
        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
        section_header("Import History (This Session)", icon="📜")
        hdf = pd.DataFrame(history[::-1])  # newest first
        st.dataframe(
            hdf,
            use_container_width=True,
            column_config={
                "rows": st.column_config.NumberColumn("Rows", format="%d"),
                "cols": st.column_config.NumberColumn("Cols", format="%d"),
                "timestamp": st.column_config.TextColumn("Imported At"),
            },
        )

    # ── Active Custom Datasets ────────────────────────────────────
    cache = st.session_state.get("data_cache", {})
    custom_keys = {k: v for k, v in cache.items() if k.startswith("custom_") and isinstance(v, pd.DataFrame)}
    if custom_keys:
        section_header("Active Custom Datasets in Memory", icon="💾")
        for key, df_c in custom_keys.items():
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:6px 10px;'
                f'background:rgba(99,102,241,0.05);border:1px solid rgba(99,102,241,0.15);'
                f'border-radius:6px;margin-bottom:4px;">'
                f'<span style="font-size:0.8rem;color:#818cf8;font-weight:600">📦 {key}</span>'
                f'<span style="font-size:0.75rem;color:#94a3b8">{len(df_c):,} rows · {len(df_c.columns)} cols</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
