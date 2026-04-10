import streamlit as st
import json
from assessment_1.orchestrator import run_war_room
from assessment_2.orchestrator import run_investigation

st.set_page_config(page_title="Multi-Agent Assessment", layout="wide", initial_sidebar_state="expanded")

st.title("🤖 Multi-Agent Engine")

assessment = st.sidebar.selectbox("Select Assessment", ["Assessment 1: War Room", "Assessment 2: Bug Investigation"])

if assessment == "Assessment 1: War Room":
    st.header("🚀 Assessment 1: War Room Launch Decision System")
    st.markdown("This runs the multi-agent system to decide whether to launch, pause, or roll back a feature based on dynamic data.")
    
    if st.button("Run War Room Agents", type="primary", use_container_width=True):
        with st.spinner("Agents are analyzing the data..."):
            try:
                final_state = run_war_room()
                st.success("Analysis complete!")
                
                col1, col2 = st.columns(2)
                decision = final_state["decision"]
                col1.metric("Final Decision", decision)
                col2.metric("Confidence Score", f"{final_state.get('confidence_score', 0):.0%}")
                
                st.subheader("💡 Rationale")
                st.info(final_state["rationale"])
                
                st.subheader("📅 Action Plan (24-48 Hours)")
                if final_state.get("action_plan"):
                    st.dataframe(
                        final_state.get("action_plan", []), 
                        use_container_width=True,
                        column_order=["priority", "action", "owner", "deadline"]
                    )
                
                with st.expander("⚠️ Risk Register"):
                    st.dataframe(final_state.get("risk_register", []), use_container_width=True)
                    
                with st.expander("📢 Communication Plan"):
                    st.markdown(final_state.get("communication_plan", ""))

                st.subheader("Agent Output Reports")
                r_col1, r_col2, r_col3, r_col4 = st.tabs(["Data Analyst", "Product Manager", "Marketing", "Risk Critic"])
                with r_col1:
                    st.markdown(final_state["analyst_report"])
                with r_col2:
                    st.markdown(final_state["pm_report"])
                with r_col3:
                    st.markdown(final_state["marketing_report"])
                with r_col4:
                    st.markdown(final_state["critic_report"])
                    
            except Exception as e:
                st.error(f"Error during execution: {e}")

else:
    st.header("🐞 Assessment 2: Automated Bug Investigation System")
    st.markdown("This system ingests a bug report, reproduces the issue via execution tools, and formulates a patch plan.")
    
    if st.button("Run Investigation Agents", type="primary", use_container_width=True):
        with st.spinner("Agents are triaging, replicating, and planning fix..."):
            try:
                final_state = run_investigation()
                st.success("Investigation complete!")
                
                st.subheader("🎯 Hypothesized Root Cause")
                st.error(final_state.get("root_cause", "No root cause identified."))
                
                col1, col2 = st.columns(2)
                col1.metric("Confidence", f"{final_state.get('root_cause_confidence', 0):.0%}")
                repro_status = "Reproduced" if final_state.get("repro_succeeded") else "Failed to Reproduce"
                col2.metric("Repro Status", repro_status)
                
                st.subheader("🛠 Patch Plan")
                if final_state.get("patch_plan"):
                    st.dataframe(final_state.get("patch_plan", []), use_container_width=True)
                
                with st.expander("📝 Reproduction Details"):
                    st.markdown(f"**Repro Script Path:** `{final_state.get('repro_script_path', '')}`")
                    st.text(final_state.get("repro_run_output", ""))
                
                with st.expander("🔎 Log Evidence"):
                    st.json(final_state.get("log_evidence", []))
                    
                with st.expander("🕵️ Critic Feedback"):
                    approved = final_state.get("critic_approved")
                    if approved:
                        st.success("Approved by Critic")
                    else:
                        st.warning("Needs Review")
                    try:
                        fb = json.loads(final_state.get("critic_feedback", "{}"))
                        st.json(fb)
                    except:
                        st.write(final_state.get("critic_feedback", ""))
                
            except Exception as e:
                st.error(f"Error during execution: {e}")
