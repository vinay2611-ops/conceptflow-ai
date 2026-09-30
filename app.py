import streamlit as st

from pdf_processor import extract_text_from_pdf
from ai_engine import analyze_text
from concept_mapper import create_concept_map


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="ConceptFlow AI",
    page_icon="C",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# PROFESSIONAL DARK MULTICOLOR THEME
# ============================================================

st.markdown(
    """
    <style>

    /* ========================================================
       APPLICATION BACKGROUND
       ======================================================== */

    .stApp {
        background:
            radial-gradient(
                circle at 0% 0%,
                rgba(37, 99, 235, 0.12),
                transparent 28%
            ),
            radial-gradient(
                circle at 100% 0%,
                rgba(124, 58, 237, 0.12),
                transparent 30%
            ),
            radial-gradient(
                circle at 50% 100%,
                rgba(6, 182, 212, 0.06),
                transparent 32%
            ),
            #060914;

        color: #f8fafc;
    }


    /* ========================================================
       MAIN CONTENT
       ======================================================== */

    .block-container {
        max-width: 1450px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
    }


    /* ========================================================
       SIDEBAR
       ======================================================== */

    section[data-testid="stSidebar"] {
        background:
            linear-gradient(
                180deg,
                #080c17 0%,
                #0b1020 50%,
                #080c16 100%
            );

        border-right: 1px solid #202a3d;
    }


    section[data-testid="stSidebar"] h1 {
        color: #60a5fa !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }


    section[data-testid="stSidebar"] h2 {
        color: #c4b5fd !important;
    }


    section[data-testid="stSidebar"] h3 {
        color: #93c5fd !important;
    }


    section[data-testid="stSidebar"] p {
        color: #9caac0;
    }


    /* ========================================================
       TYPOGRAPHY
       ======================================================== */

    h1 {
        color: #f8fafc !important;
        font-weight: 850 !important;
        letter-spacing: -1.2px;
    }


    h2 {
        color: #e2e8f0 !important;
        font-weight: 800 !important;
        letter-spacing: -0.4px;
    }


    h3 {
        color: #dbeafe !important;
        font-weight: 750 !important;
    }


    p {
        color: #aeb9ca;
    }


    /* ========================================================
       PRIMARY BUTTON
       ======================================================== */

    .stButton > button {
        min-height: 50px;

        border-radius: 10px;

        border: 1px solid rgba(96, 165, 250, 0.25);

        background:
            linear-gradient(
                90deg,
                #0891b2,
                #2563eb,
                #7c3aed
            );

        color: #ffffff;

        font-weight: 750;

        box-shadow:
            0 8px 25px rgba(37, 99, 235, 0.20);

        transition: all 0.2s ease;
    }


    .stButton > button:hover {
        background:
            linear-gradient(
                90deg,
                #06b6d4,
                #3b82f6,
                #8b5cf6
            );

        border-color: rgba(255,255,255,0.20);

        transform: translateY(-1px);
    }


    /* ========================================================
       FILE UPLOADER
       ======================================================== */

    [data-testid="stFileUploader"] {
        background:
            linear-gradient(
                135deg,
                rgba(37, 99, 235, 0.08),
                rgba(124, 58, 237, 0.08)
            );

        border: 1px dashed #334155;

        border-radius: 12px;

        padding: 12px;
    }


    /* ========================================================
       METRIC CARDS
       ======================================================== */

    [data-testid="stMetric"] {
        background:
            linear-gradient(
                135deg,
                #0b1220,
                #111827
            );

        border: 1px solid #263249;

        border-radius: 14px;

        padding: 18px;

        box-shadow:
            0 8px 25px rgba(0, 0, 0, 0.20);
    }


    [data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-weight: 800;
    }


    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
    }


    /* ========================================================
       EXPANDERS
       ======================================================== */

    [data-testid="stExpander"] {
        background:
            linear-gradient(
                135deg,
                #0b1220,
                #101827
            );

        border: 1px solid #263249;

        border-radius: 12px;
    }


    /* ========================================================
       ALERTS
       ======================================================== */

    [data-testid="stAlert"] {
        border-radius: 12px;
    }


    /* ========================================================
       TEXT AREA
       ======================================================== */

    textarea {
        background-color: #0b1220 !important;

        color: #e2e8f0 !important;

        border: 1px solid #293449 !important;
    }


    /* ========================================================
       DIVIDERS
       ======================================================== */

    hr {
        border-color: #202a3d;
    }


    /* ========================================================
       RELATIONSHIP SECTION
       ======================================================== */

    .relationship-source {
        text-align: center;
        color: #60a5fa;
        font-size: 21px;
        font-weight: 800;
        padding-top: 8px;
        padding-bottom: 6px;
    }


    .relationship-label {
        text-align: center;
        color: #c4b5fd;
        font-size: 14px;
        font-weight: 700;
        padding-top: 3px;
        padding-bottom: 2px;
    }


    .relationship-arrow {
        text-align: center;
        color: #22d3c5;
        font-size: 42px;
        font-weight: 900;
        line-height: 1;
        padding-top: 2px;
        padding-bottom: 3px;
    }


    .relationship-target {
        text-align: center;
        color: #34d399;
        font-size: 21px;
        font-weight: 800;
        padding-top: 5px;
        padding-bottom: 8px;
    }


    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("ConceptFlow AI")

    st.caption(
        "STEM Knowledge Visualization Platform"
    )

    st.divider()

    st.subheader("Chapter Input")

    uploaded_file = st.file_uploader(
        "Upload a STEM textbook chapter",
        type=["pdf"],
        help="Upload a STEM textbook chapter in PDF format."
    )

    st.divider()

    st.subheader("Workflow")

    st.markdown("""
    **01  Upload**

    Add a textbook chapter.

    **02  Extract**

    Extract readable chapter content.

    **03  Analyze**

    Identify important concepts.

    **04  Connect**

    Detect relationships between concepts.

    **05  Visualize**

    Explore the resulting knowledge map.
    """)

    st.divider()

    st.subheader("Concept Classification")

    st.markdown("""
    **Foundation**

    Fundamental knowledge required by later concepts.

    **Core Concept**

    A central idea within the chapter.

    **Process**

    An action, procedure, or sequence.

    **Mathematical**

    A mathematical operation or principle.

    **Outcome**

    A result produced by another concept.
    """)


# ============================================================
# MAIN HEADER
# ============================================================

st.title("ConceptFlow AI")

st.subheader(
    "Visual Knowledge Mapping for STEM Learning"
)

st.write(
    "Transform dense STEM textbook chapters into "
    "structured visual knowledge maps that reveal "
    "how concepts connect."
)


# ============================================================
# FEATURE ROW
# ============================================================

feature1, feature2, feature3, feature4 = st.columns(4)


with feature1:

    st.info(
        "**Textbook Analysis**\n\n"
        "Extract knowledge from chapter content."
    )


with feature2:

    st.success(
        "**Concept Extraction**\n\n"
        "Identify important concepts."
    )


with feature3:

    st.warning(
        "**Relationship Detection**\n\n"
        "Discover how concepts connect."
    )


with feature4:

    st.error(
        "**Knowledge Visualization**\n\n"
        "Explore the conceptual structure."
    )


st.divider()


# ============================================================
# LANDING PAGE
# ============================================================

if uploaded_file is None:

    st.header("Get Started")

    st.write(
        "Upload a STEM textbook chapter to generate "
        "an interactive representation of its "
        "conceptual structure."
    )


    col1, col2, col3 = st.columns(3)


    with col1:

        st.subheader("Extract")

        st.write(
            "Identify important concepts and definitions "
            "from dense textbook material."
        )


    with col2:

        st.subheader("Connect")

        st.write(
            "Determine how concepts depend on, use, "
            "transform, or produce one another."
        )


    with col3:

        st.subheader("Understand")

        st.write(
            "Explore the subject as a connected knowledge "
            "structure rather than isolated text."
        )


    st.info(
        "Upload a textbook chapter from the sidebar "
        "to begin."
    )

    st.stop()


# ============================================================
# FILE READY
# ============================================================

st.header("Chapter Ready")

st.success(
    f"Successfully uploaded: {uploaded_file.name}"
)


# ============================================================
# EXTRACT TEXT
# ============================================================

text = extract_text_from_pdf(
    uploaded_file
)


if not text.strip():

    st.error(
        "No readable text was found in this PDF."
    )

    st.stop()


# ============================================================
# TEXT PREVIEW
# ============================================================

with st.expander("View Extracted Text"):

    st.text_area(
        "Chapter content",
        text,
        height=250
    )


# ============================================================
# GENERATE MAP
# ============================================================

generate_button = st.button(
    "Generate Visual Concept Map",
    type="primary",
    use_container_width=True
)


if generate_button:

    with st.spinner(
        "Analyzing chapter content and detecting relationships..."
    ):

        try:

            result = analyze_text(
                text
            )

            st.session_state[
                "concept_data"
            ] = result

            st.success(
                "Concept map generated successfully."
            )

        except Exception as e:

            st.error(
                f"Processing failed: {e}"
            )


# ============================================================
# RESULTS
# ============================================================

if "concept_data" in st.session_state:

    data = st.session_state[
        "concept_data"
    ]

    concepts = data.get(
        "concepts",
        []
    )

    relationships = data.get(
        "relationships",
        []
    )


    # ========================================================
    # STATISTICS
    # ========================================================

    st.divider()

    st.header("Chapter Intelligence")

    st.caption(
        "Summary of the knowledge extracted from the chapter."
    )


    stat1, stat2, stat3, stat4 = st.columns(4)


    with stat1:

        st.metric(
            "Concepts",
            len(concepts)
        )


    with stat2:

        st.metric(
            "Relationships",
            len(relationships)
        )


    with stat3:

        st.metric(
            "Analysis",
            "Complete"
        )


    with stat4:

        st.metric(
            "Knowledge Map",
            "Ready"
        )


    # ========================================================
    # KNOWLEDGE MAP
    # ========================================================

    st.divider()

    st.header("Interactive Knowledge Map")

    st.caption(
        "Follow the directional connections to understand "
        "how concepts relate to one another."
    )


    network = create_concept_map(
        data
    )


    network.save_graph(
        "concept_map.html"
    )


    with open(
        "concept_map.html",
        "r",
        encoding="utf-8"
    ) as file:

        html = file.read()


    st.components.v1.html(
        html,
        height=750,
        scrolling=True
    )


    # ========================================================
    # CORE CONCEPT EXPLANATION
    # ========================================================

    st.divider()

    st.header(
        "Understanding Concept Classification"
    )


    st.info(
        """
        **Core Concept** refers to an idea that is central
        to understanding the chapter.

        Example:

        Foundation → Vectors

        Foundation → Matrices

        Mathematical → Matrix Multiplication

        Core Concept → Neural Networks

        Process → Backpropagation

        The classification describes the role of a concept
        within the knowledge structure.
        """
    )


    # ========================================================
    # CONCEPT EXPLORER
    # ========================================================

    st.header("Concept Explorer")

    st.caption(
        "Select a concept to view its explanation."
    )


    for concept in concepts:

        name = concept.get(
            "name",
            "Unknown Concept"
        )

        description = concept.get(
            "description",
            "No description available."
        )

        concept_type = concept.get(
            "type",
            "Concept"
        )


        with st.expander(
            name
        ):

            st.write(
                description
            )

            st.caption(
                f"Classification: {concept_type}"
            )


    # ========================================================
    # DETECTED RELATIONSHIPS
    # ========================================================

    st.divider()

    st.header(
        "Detected Relationships"
    )

    st.caption(
        "Directional relationships identified from "
        "the textbook content."
    )


    for relation in relationships:

        source = relation.get(
            "source",
            "Unknown"
        )

        target = relation.get(
            "target",
            "Unknown"
        )

        relationship = relation.get(
            "relationship",
            "related to"
        )


        # ====================================================
        # CENTERED RELATIONSHIP
        # ====================================================

        left_space, center_space, right_space = st.columns(
            [1, 2, 1]
        )


        with center_space:

            # SOURCE CONCEPT

            st.markdown(
                f"""
                <div class="relationship-source">
                    ● {source}
                </div>
                """,
                unsafe_allow_html=True
            )


            # RELATIONSHIP LABEL

            st.markdown(
                f"""
                <div class="relationship-label">
                    {relationship}
                </div>
                """,
                unsafe_allow_html=True
            )


            # LARGE CENTERED ARROW

            st.markdown(
                """
                <div class="relationship-arrow">
                    ↓
                </div>
                """,
                unsafe_allow_html=True
            )


            # TARGET CONCEPT

            st.markdown(
                f"""
                <div class="relationship-target">
                    ● {target}
                </div>
                """,
                unsafe_allow_html=True
            )


        st.divider()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "ConceptFlow AI | Visual Knowledge Mapping for STEM Education"
)