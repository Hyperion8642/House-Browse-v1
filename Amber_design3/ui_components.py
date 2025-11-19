# ui_components.py
"""
Reusable UX-style control panel components for Design 3.
"""

import streamlit as st


def income_control_panel():
    """
    Sidebar: persona + smooth income slider + manual input box.

    Returns
    -------
    final_income : float
    persona      : str
    """

    st.sidebar.markdown("### Who are you?")

    persona = st.sidebar.radio(
        "Choose a profile",
        options=["Student", "Young professional", "Family"],
        index=1,
        help="We use this to suggest a starting income level.",
    )

    # persona default incomes
    persona_defaults = {
        "Student": 30000,
        "Young professional": 60000,
        "Family": 90000,
    }
    default_income = persona_defaults[persona]

    st.sidebar.markdown("### Budget settings")

    # ---- Step 1: slider ----
    income_slider = st.sidebar.slider(
        "Annual income (rough adjustment)",
        min_value=20000,
        max_value=200000,
        value=default_income,
        step=1000,
    )

    # ---- Step 2: inputbox ----
    manual_income = st.sidebar.number_input(
        "Exact annual income ($)",
        min_value=20000,
        max_value=200000,
        value=income_slider,
        step=500,
        format="%d",
        help="Use this box to fine-tune the exact value.",
    )

    final_income = manual_income

    st.sidebar.caption(
        "Tip: use the slider for rough adjustment and the box for precise input."
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
**30% rule**

We assume housing is affordable if  

> monthly rent ≤ 30% of your monthly income.
"""
    )

    return final_income, persona
