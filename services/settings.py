import os
from dotenv import load_dotenv

load_dotenv()


def env(key: str, default: str = "") -> str:
    """Read from Streamlit secrets first (Cloud), then environment variables."""
    try:
        import streamlit as st
        val = st.secrets.get(key)
    except Exception:
        val = None
    return str(val) if val else os.getenv(key, default)


DEMO = env("DEMO_MODE").lower() == "true" or not (env("SUPABASE_URL") and env("SUPABASE_ANON_KEY"))
