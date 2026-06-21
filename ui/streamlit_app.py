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
        result = asyncio.run(run_pipeline(question.strip()))

    # ── Answer ────────────────────────────────────────────────────────────────
    confidence_emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(
        result.confidence_level, "⚪"
    )
    st.markdown(
        f"### Answer  {confidence_emoji} {result.confidence_level.capitalize()} confidence "
        f"({result.confidence:.0%})"
    )
    st.markdown(result.answer)

    # ── Agent comments ────────────────────────────────────────────────────────
    if result.comments:
        with st.expander(f"Agent contributions ({len(result.comments)} comments)", expanded=False):
            for c in result.comments:
                verdict_badge = ""
                if c.verdict:
                    colours = {"supports": "🟢", "refutes": "🔴", "unclear": "🟡"}
                    verdict_badge = f" {colours.get(c.verdict, '')} {c.verdict}"
                st.markdown(f"**{c.role}**{verdict_badge}")
                if c.claim:
                    st.caption(f"Claim: {c.claim}")
                st.markdown(c.content)
                if c.url:
                    st.markdown(f"[Source]({c.url})")
                st.divider()
