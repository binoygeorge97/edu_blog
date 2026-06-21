import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from app.pipeline import run_pipeline

st.set_page_config(page_title="Sourcerer", page_icon="🔍", layout="centered")

st.title("Sourcerer")
st.caption("An AI tutor that verifies its own answers.")

question = st.text_input(
    "Ask anything:",
    placeholder="What is the speed of light and how was it measured?",
)

if st.button("Ask", disabled=not question.strip()):
    with st.spinner("Thinking..."):
        answer = asyncio.run(run_pipeline(question.strip()))
    st.markdown("### Answer")
    st.write(answer)
