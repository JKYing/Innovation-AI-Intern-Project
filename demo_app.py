#!/usr/bin/env python3
import json
from pathlib import Path
import streamlit as st

DATA = Path("data")
st.set_page_config(page_title="Innovation AI — Inbox ➜ Plan Demo", layout="wide")
st.title("📬 ➜ 🗓️ Innovation AI — Inbox → Tasks → Plan")

col1, col2, col3 = st.columns([1.2,1.2,1])

with col1:
    st.header("Gmail / Calendar Preview")
    gpath = DATA/"gmail_sample.json"; cpath = DATA/"calendar_sample.json"
    if gpath.exists():
        st.subheader("Gmail Sample")
        for g in json.loads(gpath.read_text(encoding="utf-8"))[:20]:
            st.markdown(f"**{g.get('subject','(no subject)')}**  \n_{g.get('from','')} • {g.get('date','')}_  \n{g.get('snippet','')[:160]}...")
            st.divider()
    else: st.info("Place Week-1 file: data/gmail_sample.json")
    if cpath.exists():
        st.subheader("Calendar Sample")
        for e in json.loads(cpath.read_text(encoding='utf-8'))[:20]:
            start=(e.get('start') or {}).get('dateTime') or (e.get('start') or {}).get('date')
            st.write(f"• {e.get('summary','(event)')} — {start}")
    else: st.info("Place Week-1 file: data/calendar_sample.json")

with col2:
    st.header("Task Extraction")
    hp = DATA/"tasks_pred.jsonl"; lp = DATA/"tasks_pred_llm.jsonl"
    if hp.exists() or lp.exists():
        tab_h, tab_l = st.tabs(["Heuristic", "LLM"])
        with tab_h:
            if hp.exists():
                for l in hp.read_text(encoding='utf-8').splitlines()[:15]:
                    st.json(json.loads(l), expanded=False)
            else: st.info("Run baseline: python task_parser.py")
        with tab_l:
            if lp.exists():
                for l in lp.read_text(encoding='utf-8').splitlines()[:15]:
                    st.json(json.loads(l), expanded=False)
            else: st.info("Save LLM results to data/tasks_pred_llm.jsonl")
    else: st.info("Add extraction outputs to /data")

with col3:
    st.header("Daily Plan & Metrics")
    pp = DATA / "daily_plan_pred.jsonl"

    if pp.exists():
        import plotly.express as px
        import pandas as pd

        lines = [json.loads(x) for x in pp.read_text(encoding='utf-8').splitlines()]
        if lines:
            sel = st.selectbox("Select Day", [l["date"] for l in lines])
            rec = next(x for x in lines if x["date"] == sel)
            plan_df = pd.DataFrame(rec["plan"])

            # Show summary metrics
            st.markdown(f"**Total tasks:** {len(plan_df[plan_df['type']=='task'])} | **Events:** {len(plan_df[plan_df['type']=='event'])}")

            # Gantt chart visualization
            df_plot = plan_df.copy()
            df_plot["Start"] = pd.to_datetime(df_plot["start"])
            df_plot["Finish"] = pd.to_datetime(df_plot["end"])
            df_plot.rename(columns={"item":"Task","type":"Type"}, inplace=True)

            # Limit sample size (e.g., show up to 15 blocks)
            df_plot = df_plot.head(15)

            fig = px.timeline(df_plot, x_start="Start", x_end="Finish", y="Task", color="Type",
                              title=f"AI Daily Plan for {sel}",
                              labels={"Task":"Task/Event"}, hover_name="Task")
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(height=600, margin=dict(l=40, r=40, t=60, b=60))
            st.plotly_chart(fig, use_container_width=True)

            # Optional raw JSON details
            with st.expander("Show Raw Plan JSON"):
                st.json(rec["plan"], expanded=False)

        else:
            st.info("No plans found. Run generate_daily_plan.py first.")
    else:
        st.info("Run: python generate_daily_plan.py")

st.sidebar.header("Runbook")
st.sidebar.markdown("""
**Week 3**
1) `python generate_daily_plan.py` → writes `data/daily_plan_pred.jsonl`  
2) `python evaluate_daily_plan.py`  

**Week 4**
1) `python evaluate_final.py`  
2) `streamlit run demo_app.py`
""")