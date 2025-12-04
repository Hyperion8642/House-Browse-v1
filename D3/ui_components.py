# ui_components.py
# Fixing warning message above Exact annual income ($) and cleaning misc captions 

import streamlit as st

# New default income values
PERSONA_DEFAULTS = {
    "Student": 34000,
    "Young professional": 43000,
    "Family": 84000,
}

# --- CALLBACKS remain the same ---

def sync_slider_to_manual():
    """Updates the slider value (key) whenever the manual input changes."""
    st.session_state.income_slider_key = st.session_state.income_manual_key

def sync_manual_to_slider():
    """Updates the manual input value (key) whenever the slider changes."""
    st.session_state.income_manual_key = st.session_state.income_slider_key

# -----------------------------------------------------------

def get_income_and_persona_logic():
    
    if "current_persona" not in st.session_state:
        st.session_state.current_persona = "Young professional"
    
    initial_default = PERSONA_DEFAULTS[st.session_state.current_persona]

    if "income_manual_key" not in st.session_state:
        st.session_state.income_manual_key = initial_default
    if "income_slider_key" not in st.session_state:
        st.session_state.income_slider_key = initial_default
    
    persona = st.session_state.get("profile_radio_key", st.session_state.current_persona)
    
    if persona != st.session_state.current_persona:
        new_default = PERSONA_DEFAULTS.get(persona)
        
        st.session_state.income_manual_key = new_default
        st.session_state.income_slider_key = new_default
        st.session_state.current_persona = persona
    
    final_income = st.session_state.income_manual_key

    return final_income, persona


def render_affordability_summary_card(final_income, persona, max_affordable_price):
    """
    Renders just the Affordability Summary Card.
    (Can be used anywhere to display the summary)
    """
    st.markdown("#### Affordability Summary")

    st.markdown(
        f"""
        <div style="
            padding: 1rem 1rem;
            background-color: #ffffff10;
            border-radius: 8px;
            border: 1px solid #444;
            ">
            <p style="margin:0.1rem 0;"><strong>Profile:</strong> {persona}</p>
            <p style="margin:0.1rem 0;"><strong>Annual income:</strong> ${int(final_income):,}</p>
            <p style="margin:0.1rem 0;"><strong>Max Affordable Price (from PTI thresholds):</strong> ≈ ${max_affordable_price:,.0f}</p> 
        </div>
        """,
        unsafe_allow_html=True,
    )


def persona_income_slider(final_income, persona):
    """
    NEW FUNCTION: Renders the Persona selector and the Rough Adjustment Slider.
    (Used in the Map Column)
    """
    
    st.markdown("##### Who are you?")
    st.markdown("""Input income data using the slider below.
    The Affordability Summary will tell you the maximum price of a house that would be considered affordable based on the PTI thresholds.
    The zip code map below color-codes unaffordable zip codes as red, and affordable zip codes as green. """)
    persona_options = list(PERSONA_DEFAULTS.keys())
    
    st.radio(
        "Choose a profile",
        options=persona_options,
        index=persona_options.index(persona),
        key="profile_radio_key",
        help="We use this to suggest a starting income level. Defaults: Student ($34k), YP ($43k), Family ($84k).",
        horizontal=True
    )
    
    st.markdown("##### Income settings")
    
    # RENDER SLIDER (Takes full width of the column it's in)
    st.slider(
        "Annual income (rough adjustment)",
        min_value=20000,
        max_value=200000,
        value=st.session_state.income_slider_key,
        step=1000,
        key="income_slider_key",
        on_change=sync_manual_to_slider,
    )
    # st.markdown("---") # Separator


# def render_manual_input_and_summary(final_income, persona, max_affordable_price):
#     """
#     Renders the Manual Input, Tip, and Affordability Summary Card.
#     (Used in the Top Right Profile Column)
#     """
    
#     # --- 1. RENDER MANUAL INPUT (Vertical Stack) ---
#     st.number_input(
#         "Exact annual income ($)",
#         min_value=20000,
#         max_value=200000,
#         value=st.session_state.income_manual_key,
#         step=500,
#         format="%d",
#         key="income_manual_key",
#         help="This income is used to filter available cities/ZIPs by Per Capita Income.",
#         on_change=sync_slider_to_manual,
#     )
#     # # TIP PLACEMENT
#     # st.caption(
#     #     "Tip: use the slider for rough adjustment and the box for precise input."
#     # )
#     # --- 2. RENDER AFFORDABILITY SUMMARY ---
#     st.markdown("---")
#     st.markdown("##### Affordability Summary")

#     st.markdown(
#         f"""
#         <div style="
#             padding: 1rem 1rem;
#             background-color: #ffffff10;
#             border-radius: 8px;
#             border: 1px solid #444;
#             ">
#             <p style="margin:0.1rem 0;"><strong>Profile:</strong> {persona}</p>
#             <p style="margin:0.1rem 0;"><strong>Annual income:</strong> ${int(final_income):,}</p>
#             <p style="margin:0.1rem 0;"><strong>Max affordable price using Ratio-to-Income formula:</strong> ≈ ${max_affordable_price:,.0f}</p> 
#         </div>
#         """,
#         unsafe_allow_html=True,
#     )
    
    
income_control_panel = get_income_and_persona_logic



# Putting income slider right above map

# --- File: ui_components.py (Final Code with Segmented Rendering) ---
# import streamlit as st

# # New default income values
# PERSONA_DEFAULTS = {
#     "Student": 34000,
#     "Young professional": 43000,
#     "Family": 84000,
# }

# # --- CALLBACKS remain the same ---

# def sync_slider_to_manual():
#     """Updates the slider value (key) whenever the manual input changes."""
#     st.session_state.income_slider_key = st.session_state.income_manual_key

# def sync_manual_to_slider():
#     """Updates the manual input value (key) whenever the slider changes."""
#     st.session_state.income_manual_key = st.session_state.income_slider_key

# # -----------------------------------------------------------

# def get_income_and_persona_logic():
#     """
#     Initializes session state and handles the core persona/income logic.
#     """
    
#     if "current_persona" not in st.session_state:
#         st.session_state.current_persona = "Young professional"
    
#     initial_default = PERSONA_DEFAULTS[st.session_state.current_persona]

#     if "income_manual_key" not in st.session_state:
#         st.session_state.income_manual_key = initial_default
#     if "income_slider_key" not in st.session_state:
#         st.session_state.income_slider_key = initial_default
    
#     persona = st.session_state.get("profile_radio_key", st.session_state.current_persona)
    
#     if persona != st.session_state.current_persona:
#         new_default = PERSONA_DEFAULTS.get(persona)
        
#         st.session_state.income_manual_key = new_default
#         st.session_state.income_slider_key = new_default
#         st.session_state.current_persona = persona
    
#     final_income = st.session_state.income_manual_key

#     return final_income, persona


# def persona_income_slider(final_income, persona):
#     """
#     NEW FUNCTION: Renders the Persona selector and the Rough Adjustment Slider.
#     (Used in the Map Column)
#     """
    
#     st.markdown("##### Who are you?")
#     persona_options = list(PERSONA_DEFAULTS.keys())
    
#     st.radio(
#         "Choose a profile",
#         options=persona_options,
#         index=persona_options.index(persona),
#         key="profile_radio_key",
#         help="We use this to suggest a starting income level. Defaults: Student ($34k), YP ($43k), Family ($84k).",
#         horizontal=True
#     )
    
#     st.markdown("##### Budget settings")
    
#     # RENDER SLIDER (Takes full width of the column it's in)
#     st.slider(
#         "Annual income (rough adjustment)",
#         min_value=20000,
#         max_value=200000,
#         value=st.session_state.income_slider_key,
#         step=1000,
#         key="income_slider_key",
#         on_change=sync_manual_to_slider,
#     )
#     # st.markdown("---") # Separator


# def render_manual_input_and_summary(final_income, persona, max_affordable_price):
#     """
#     Renders the Manual Input, Tip, and Affordability Summary Card.
#     (Used in the Top Right Profile Column)
#     """
    
#     # --- 1. RENDER MANUAL INPUT (Takes full width of the column it's in) ---
#     st.number_input(
#         "Exact annual income ($)",
#         min_value=20000,
#         max_value=200000,
#         value=st.session_state.income_manual_key,
#         step=500,
#         format="%d",
#         key="income_manual_key",
#         help="This income is used to filter available cities/ZIPs by Per Capita Income.",
#         on_change=sync_slider_to_manual,
#     )
#     # TIP PLACEMENT
#     st.caption(
#         "Tip: use the slider for rough adjustment and the box for precise input."
#     )

#     # --- 2. RENDER AFFORDABILITY SUMMARY ---
#     st.markdown("---")
#     st.markdown("##### Affordability Summary")

#     st.markdown(
#         f"""
#         <div style="
#             padding: 1rem 1rem;
#             background-color: #ffffff10;
#             border-radius: 8px;
#             border: 1px solid #444;
#             ">
#             <p style="margin:0.1rem 0;"><strong>Profile:</strong> {persona}</p>
#             <p style="margin:0.1rem 0;"><strong>Annual income:</strong> ${int(final_income):,}</p>
#             <p style="margin:0.1rem 0;"><strong>Max affordable price (Ratio-to-Income):</strong> ≈ ${max_affordable_price:,.0f}</p> 
#             <p style="margin:0.1rem 0;font-size:0.9rem;color:#ccc;">
#                 City affordability uses <em>Median Sale Price / Per Capita Income</em>
#                 (lower is better).
#             </p>
#         </div>
#         """,
#         unsafe_allow_html=True,
#     )
    
#     # st.markdown("---")
#     # st.markdown(
#     #     """
#     #     **Price-to-Income rule**
#     #     We evaluate housing affordability using:
#     #     > **Median Sale Price / Per Capita Income**
#     #     Lower ratios indicate better affordability.
#     #     In this dashboard, cities with a ratio **≤ 5.0** are treated as relatively more affordable.
#     #     """
#     # )
    
# # Export the logic function to be called by app_v2.py
# income_control_panel = get_income_and_persona_logic

