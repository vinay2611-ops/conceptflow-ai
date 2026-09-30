import os
import re
import json
import html
from pathlib import Path
from collections import Counter

import streamlit as st
from dotenv import load_dotenv
from google import genai

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
# CONFIGURATION
# ============================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    try:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    except Exception:
        GEMINI_API_KEY = None

CACHE_DIR = Path(".conceptflow_cache")
CACHE_DIR.mkdir(exist_ok=True)


# ============================================================
# GEMINI HELPERS
# ============================================================

def get_gemini_client():
    if not GEMINI_API_KEY:
        return None

    return genai.Client(api_key=GEMINI_API_KEY)


def clean_json_response(result):
    result = result.strip()

    if result.startswith("```json"):
        result = result[7:]
    elif result.startswith("```"):
        result = result[3:]

    if result.endswith("```"):
        result = result[:-3]

    return result.strip()


def is_quota_or_api_error(error):
    message = str(error).lower()

    return any(
        phrase in message
        for phrase in [
            "429",
            "resource_exhausted",
            "quota",
            "rate limit",
            "503",
            "unavailable",
            "high demand",
            "deadline exceeded",
            "500",
            "internal"
        ]
    )


# ============================================================
# CACHE
# ============================================================

def get_file_signature(uploaded_file):
    data = uploaded_file.getvalue()

    import hashlib

    return hashlib.sha256(data).hexdigest()


def get_cross_cache_path(signature_a, signature_b):
    import hashlib

    combined = f"{signature_a}:{signature_b}".encode("utf-8")
    cache_key = hashlib.sha256(combined).hexdigest()

    return CACHE_DIR / f"cross_{cache_key}.json"


def load_cross_cache(signature_a, signature_b):
    path = get_cross_cache_path(
        signature_a,
        signature_b
    )

    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return None


def save_cross_cache(signature_a, signature_b, result):
    path = get_cross_cache_path(
        signature_a,
        signature_b
    )

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# LOCAL FALLBACK ENGINE
# ============================================================

STOPWORDS = {
    "about", "after", "again", "against", "also", "among",
    "because", "before", "between", "both", "can", "could",
    "each", "from", "have", "having", "into", "more",
    "most", "other", "over", "same", "such", "than",
    "that", "their", "these", "they", "this", "those",
    "through", "using", "very", "when", "where", "which",
    "while", "with", "within", "would", "will", "used",
    "use", "uses", "using", "the", "and", "for", "are",
    "was", "were", "been", "being", "has", "had", "its",
    "our", "you", "your", "from", "then", "there", "here",
    "what", "how", "why", "who", "whose", "not", "but",
    "all", "any", "one", "two", "three", "may", "must",
    "should", "shall", "does", "did", "do", "of", "in",
    "on", "to", "as", "at", "by", "or", "an", "a", "is",
    "it", "be", "if", "we", "they", "he", "she"
}


def normalize_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text):
    return [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", text)
        if len(s.strip()) > 30
    ]


def clean_term(term):
    term = re.sub(r"\s+", " ", term).strip(" .,;:()[]{}")

    words = term.split()

    while words and words[0].lower() in STOPWORDS:
        words.pop(0)

    while words and words[-1].lower() in STOPWORDS:
        words.pop()

    term = " ".join(words)

    if len(term) < 3 or len(term) > 80:
        return ""

    return term


def local_subject_from_text(text, filename):
    """
    Give the fallback a useful subject label without requiring AI.
    """

    first_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ][:15]

    title_candidates = []

    for line in first_lines:
        if 3 <= len(line) <= 100:
            if len(line.split()) <= 12:
                title_candidates.append(line)

    if title_candidates:
        candidate = title_candidates[0]

        bad_titles = {
            "chapter",
            "contents",
            "introduction",
            "references",
            "abstract"
        }

        if candidate.lower() not in bad_titles:
            return candidate

    filename_clean = Path(filename).stem
    filename_clean = re.sub(
        r"[_\-]+",
        " ",
        filename_clean
    )

    return filename_clean.title()


def local_extract_concepts(text, filename):
    """
    Generic offline STEM concept extraction.

    This does not use hard-coded subjects. It derives candidate
    concepts from the actual uploaded chapter.
    """

    text = normalize_text(text)
    sentences = split_sentences(text)

    if not sentences:
        sentences = [text[:5000]]

    candidates = Counter()

    # Technical multi-word phrases.
    for sentence in sentences:
        words = re.findall(
            r"[A-Za-z][A-Za-z0-9\-]{2,}",
            sentence
        )

        for n in (2, 3):
            for i in range(len(words) - n + 1):
                phrase_words = words[i:i+n]

                if any(
                    word.lower() in STOPWORDS
                    for word in phrase_words
                ):
                    continue

                phrase = " ".join(phrase_words)

                # Prefer phrases containing technical-looking terms.
                technical_score = sum(
                    1
                    for word in phrase_words
                    if (
                        len(word) >= 7
                        or any(ch.isdigit() for ch in word)
                    )
                )

                if technical_score:
                    candidates[phrase] += 1

    # Single technical words.
    word_counts = Counter(
        word.lower()
        for word in re.findall(
            r"[A-Za-z][A-Za-z0-9\-]{3,}",
            text
        )
        if word.lower() not in STOPWORDS
    )

    for word, count in word_counts.items():
        if count >= 2 and (
            len(word) >= 7
            or word.lower() in {
                "matrix",
                "vector",
                "gradient",
                "network",
                "algorithm",
                "database",
                "storage",
                "processor",
                "energy",
                "current",
                "voltage",
                "signal",
                "function",
                "model",
                "feature",
                "parameter",
                "optimization"
            }
        ):
            candidates[word] += count

    ranked = [
        term
        for term, _ in candidates.most_common(30)
    ]

    concepts = []

    used_words = set()

    for term in ranked:

        term = clean_term(term)

        if not term:
            continue

        normalized = term.lower()

        # Avoid near-duplicate phrases.
        if normalized in used_words:
            continue

        if any(
            normalized in existing.lower()
            or existing.lower() in normalized
            for existing in used_words
        ):
            continue

        related_sentence = ""

        for sentence in sentences:
            if all(
                word.lower() in sentence.lower()
                for word in term.split()
            ):
                related_sentence = sentence
                break

        if not related_sentence:
            related_sentence = (
                f"{term} is a concept identified from the uploaded chapter."
            )

        concepts.append(
            {
                "name": term.title(),
                "description": related_sentence[:280],
                "type": "Detected Concept"
            }
        )

        used_words.add(normalized)

        if len(concepts) >= 10:
            break

    return concepts


def concept_tokens(text):
    """Create simple normalized tokens without external ML libraries."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", text.lower())
    return {
        word
        for word in words
        if word not in STOPWORDS and len(word) >= 4
    }


def local_cross_links(
    subject_a,
    concepts_a,
    subject_b,
    concepts_b
):
    """
    Offline cross-disciplinary relationship detection.

    This intentionally uses only Python's standard library so the
    application does not depend on native ML DLLs such as those used
    by scikit-learn. It compares concept names and descriptions using
    token overlap and a small amount of phrase matching.
    """

    if not concepts_a or not concepts_b:
        return []

    def concept_text(concept):
        return f"{concept.get('name', '')} {concept.get('description', '')}"

    token_sets_a = [concept_tokens(concept_text(c)) for c in concepts_a]
    token_sets_b = [concept_tokens(concept_text(c)) for c in concepts_b]

    candidates = []

    for i, concept_a in enumerate(concepts_a):
        for j, concept_b in enumerate(concepts_b):
            tokens_a = token_sets_a[i]
            tokens_b = token_sets_b[j]

            if not tokens_a or not tokens_b:
                continue

            shared = tokens_a.intersection(tokens_b)

            # Jaccard-style overlap. This is deliberately simple and
            # explainable for a hackathon fallback.
            union = tokens_a.union(tokens_b)
            score = len(shared) / len(union) if union else 0.0

            # Give an additional signal when a meaningful concept name
            # token appears in the other concept's text.
            name_a = concept_tokens(concept_a.get('name', ''))
            name_b = concept_tokens(concept_b.get('name', ''))

            name_overlap = name_a.intersection(name_b)
            description_overlap = shared - name_overlap

            if name_overlap:
                score += 0.20
            elif description_overlap:
                score += min(0.15, 0.05 * len(description_overlap))

            if score >= 0.08:
                candidates.append({
                    "score": min(score, 1.0),
                    "source": concept_a["name"],
                    "target": concept_b["name"]
                })

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    relationships = []
    used_pairs = set()

    relationship_phrases = [
        "shares concepts with",
        "uses a related idea from",
        "provides a conceptual foundation for",
        "can be applied to",
        "has overlapping principles with"
    ]

    # Keep the strongest connection for each source concept first.
    source_counts = Counter()

    for index, candidate in enumerate(candidates):
        pair = (
            candidate["source"],
            candidate["target"]
        )

        if pair in used_pairs:
            continue

        if source_counts[candidate["source"]] >= 2:
            continue

        used_pairs.add(pair)
        source_counts[candidate["source"]] += 1

        if candidate["score"] >= 0.25:
            confidence = "High"
        elif candidate["score"] >= 0.14:
            confidence = "Medium"
        else:
            confidence = "Low"

        relationships.append({
            "source": candidate["source"],
            "source_subject": subject_a,
            "target": candidate["target"],
            "target_subject": subject_b,
            "relationship": relationship_phrases[
                index % len(relationship_phrases)
            ],
            "confidence": confidence
        })

        if len(relationships) >= 6:
            break

    return relationships


def local_cross_analysis(
    text_a,
    text_b,
    filename_a,
    filename_b
):
    subject_a = local_subject_from_text(
        text_a,
        filename_a
    )

    subject_b = local_subject_from_text(
        text_b,
        filename_b
    )

    concepts_a = local_extract_concepts(
        text_a,
        filename_a
    )

    concepts_b = local_extract_concepts(
        text_b,
        filename_b
    )

    relationships = local_cross_links(
        subject_a,
        concepts_a,
        subject_b,
        concepts_b
    )

    return {
        "subject_a": subject_a,
        "subject_b": subject_b,
        "concepts_a": concepts_a,
        "concepts_b": concepts_b,
        "cross_relationships": relationships,
        "analysis_mode": "Local fallback"
    }


# ============================================================
# GEMINI CROSS-DISCIPLINARY ANALYSIS
# ============================================================

def gemini_cross_analysis(text_a, text_b):
    """
    ONE Gemini request for both chapters.

    This replaces the previous 3-request pipeline.
    """

    client = get_gemini_client()

    if client is None:
        raise RuntimeError("Gemini API key is not configured.")

    prompt = f"""
You are an expert interdisciplinary STEM knowledge-graph generator.

Two textbook chapters have been supplied.

CHAPTER A:
{text_a}

CHAPTER B:
{text_b}

Analyze BOTH chapters in one reasoning process.

TASK 1:
Identify the subject of Chapter A.

TASK 2:
Identify the subject of Chapter B.

TASK 3:
Extract 6 to 12 important concepts from each chapter.

TASK 4:
Find 3 to 8 meaningful cross-disciplinary relationships
between the concepts.

The relationships must be technically meaningful.
Do not simply match similar-looking words.

Return ONLY valid JSON in exactly this format:

{{
    "subject_a": "detected subject",
    "subject_b": "detected subject",

    "concepts_a": [
        {{
            "name": "concept",
            "description": "simple explanation",
            "type": "Foundation"
        }}
    ],

    "concepts_b": [
        {{
            "name": "concept",
            "description": "simple explanation",
            "type": "Foundation"
        }}
    ],

    "cross_relationships": [
        {{
            "source": "exact concept from Chapter A",
            "source_subject": "subject A",
            "target": "exact concept from Chapter B",
            "target_subject": "subject B",
            "relationship": "why these concepts connect",
            "confidence": "High"
        }}
    ]
}}

RULES:

- Every relationship source must exactly match a concept in concepts_a.
- Every relationship target must exactly match a concept in concepts_b.
- Do not invent concepts.
- Do not use "related to", "connected to", or "associated with".
- Prefer directional technical relationships.
- Keep descriptions student-friendly.
- Return ONLY JSON.
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    result = json.loads(
        clean_json_response(response.text)
    )

    result["analysis_mode"] = "Gemini AI"

    return result


def run_cross_analysis(
    text_a,
    text_b,
    filename_a,
    filename_b,
    signature_a,
    signature_b
):
    """
    Order:
    1. Existing cached result
    2. Gemini, using ONE request
    3. Local generic fallback

    Therefore the presentation never depends on Gemini being
    available.
    """

    cached = load_cross_cache(
        signature_a,
        signature_b
    )

    if cached:
        cached["analysis_mode"] = "Cached result"
        return cached

    # Try Gemini first.
    try:

        result = gemini_cross_analysis(
            text_a,
            text_b
        )

        save_cross_cache(
            signature_a,
            signature_b,
            result
        )

        return result

    except Exception:

        # Never stop the demo because of an API problem.
        result = local_cross_analysis(
            text_a,
            text_b,
            filename_a,
            filename_b
        )

        return result


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

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

    .block-container {
        max-width: 1450px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
    }

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

    h1 {
        color: #f8fafc !important;
        font-weight: 850 !important;
        letter-spacing: -1.2px;
    }

    h2 {
        color: #e2e8f0 !important;
        font-weight: 800 !important;
    }

    h3 {
        color: #dbeafe !important;
        font-weight: 750 !important;
    }

    p {
        color: #aeb9ca;
    }

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
    }

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
    }

    [data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-weight: 800;
    }

    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
    }

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

    textarea {
        background-color: #0b1220 !important;
        color: #e2e8f0 !important;
        border: 1px solid #293449 !important;
    }

    hr {
        border-color: #202a3d;
    }

    .relationship-source {
        text-align: center;
        color: #60a5fa;
        font-size: 21px;
        font-weight: 800;
    }

    .relationship-label {
        text-align: center;
        color: #c4b5fd;
        font-size: 14px;
        font-weight: 700;
    }

    .relationship-arrow {
        text-align: center;
        color: #22d3c5;
        font-size: 42px;
        font-weight: 900;
        line-height: 1;
    }

    .relationship-target {
        text-align: center;
        color: #34d399;
        font-size: 21px;
        font-weight: 800;
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

    st.subheader("Analysis Mode")

    analysis_mode = st.radio(
        "Choose analysis",
        [
            "Single Chapter",
            "Cross-Disciplinary"
        ],
        index=0
    )

    st.divider()

    if analysis_mode == "Single Chapter":

        st.subheader("Chapter Input")

        uploaded_file = st.file_uploader(
            "Upload a STEM textbook chapter",
            type=["pdf"],
            key="single_pdf"
        )

        st.divider()

        st.subheader("Workflow")

        st.markdown(
            """
            **01  Upload**

            Add a textbook chapter.

            **02  Extract**

            Extract readable chapter content.

            **03  Analyze**

            Identify important concepts.

            **04  Connect**

            Detect relationships.

            **05  Visualize**

            Explore the knowledge map.
            """
        )

    else:

        st.subheader("Cross-Disciplinary Input")

        st.caption(
            "Upload any two STEM textbook chapters."
        )

        st.divider()

        st.markdown("**Chapter A**")

        uploaded_file_a = st.file_uploader(
            "Upload Chapter A",
            type=["pdf"],
            key="cross_pdf_a"
        )

        st.divider()

        st.markdown("**Chapter B**")

        uploaded_file_b = st.file_uploader(
            "Upload Chapter B",
            type=["pdf"],
            key="cross_pdf_b"
        )

        st.divider()

        st.subheader("Workflow")

        st.markdown(
            """
            **01  Upload**

            Add two chapters.

            **02  Extract**

            Read both chapters.

            **03  Analyze**

            Detect concepts independently.

            **04  Connect**

            Find cross-disciplinary links.

            **05  Visualize**

            Explore the combined structure.
            """
        )

    st.divider()

    st.subheader("Concept Classification")

    st.markdown(
        """
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
        """
    )


# ============================================================
# MAIN HEADER
# ============================================================

st.title("ConceptFlow AI")

if analysis_mode == "Single Chapter":

    st.subheader(
        "Visual Knowledge Mapping for STEM Learning"
    )

    st.write(
        "Transform dense STEM textbook chapters into "
        "structured visual knowledge maps that reveal "
        "how concepts connect."
    )

else:

    st.subheader(
        "Cross-Disciplinary Knowledge Mapping"
    )

    st.write(
        "Upload any two STEM chapters and discover "
        "meaningful relationships across their concepts."
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
    if analysis_mode == "Single Chapter":
        st.warning(
            "**Relationship Detection**\n\n"
            "Discover how concepts connect."
        )
    else:
        st.warning(
            "**Cross-Link Detection**\n\n"
            "Discover links between subjects."
        )

with feature4:
    st.error(
        "**Knowledge Visualization**\n\n"
        "Explore the conceptual structure."
    )

st.divider()


# ============================================================
# SINGLE CHAPTER MODE
# ============================================================

if analysis_mode == "Single Chapter":

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
            "Upload a textbook chapter from the sidebar to begin."
        )

        st.stop()

    st.header("Chapter Ready")

    st.success(
        f"Successfully uploaded: {uploaded_file.name}"
    )

    text = extract_text_from_pdf(uploaded_file)

    if not text.strip():
        st.error("No readable text was found in this PDF.")
        st.stop()

    with st.expander("View Extracted Text"):
        st.text_area(
            "Chapter content",
            text,
            height=250
        )

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

                result = analyze_text(text)

                st.session_state["concept_data"] = result

                st.success(
                    "Concept map generated successfully."
                )

            except Exception as e:
                st.error(f"Processing failed: {e}")

    if "concept_data" in st.session_state:

        data = st.session_state["concept_data"]

        concepts = data.get("concepts", [])
        relationships = data.get("relationships", [])

        st.divider()

        st.header("Chapter Intelligence")

        stat1, stat2, stat3, stat4 = st.columns(4)

        with stat1:
            st.metric("Concepts", len(concepts))

        with stat2:
            st.metric("Relationships", len(relationships))

        with stat3:
            st.metric("Analysis", "Complete")

        with stat4:
            st.metric("Knowledge Map", "Ready")

        st.divider()

        st.header("Interactive Knowledge Map")

        network = create_concept_map(data)

        network.save_graph("concept_map.html")

        with open(
            "concept_map.html",
            "r",
            encoding="utf-8"
        ) as file:
            graph_html = file.read()

        st.components.v1.html(
            graph_html,
            height=750,
            scrolling=True
        )

        st.divider()

        st.header("Concept Explorer")

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

            with st.expander(name):

                st.write(description)

                st.caption(
                    f"Classification: {concept_type}"
                )

        st.divider()

        st.header("Detected Relationships")

        for relation in relationships:

            source = relation.get("source", "Unknown")
            target = relation.get("target", "Unknown")
            relationship = relation.get(
                "relationship",
                "related to"
            )

            _, center_space, _ = st.columns([1, 2, 1])

            with center_space:

                st.markdown(
                    f"""
                    <div class="relationship-source">
                        ● {html.escape(source)}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    <div class="relationship-label">
                        {html.escape(relationship)}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    """
                    <div class="relationship-arrow">
                        ↓
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    <div class="relationship-target">
                        ● {html.escape(target)}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.divider()


# ============================================================
# CROSS-DISCIPLINARY MODE
# ============================================================

else:

    st.header("Cross-Disciplinary Challenge")

    st.info(
        "Upload any two STEM chapters. ConceptFlow AI will "
        "analyze both chapters and discover cross-disciplinary "
        "relationships."
    )

    if uploaded_file_a is None or uploaded_file_b is None:

        st.warning(
            "Upload BOTH Chapter A and Chapter B from the sidebar."
        )

        st.stop()

    st.header("Chapters Ready")

    col_a, col_b = st.columns(2)

    with col_a:
        st.success(
            f"Chapter A: {uploaded_file_a.name}"
        )

    with col_b:
        st.success(
            f"Chapter B: {uploaded_file_b.name}"
        )

    with st.spinner("Extracting text from both chapters..."):

        text_a = extract_text_from_pdf(uploaded_file_a)
        text_b = extract_text_from_pdf(uploaded_file_b)

    if not text_a.strip():
        st.error("No readable text was found in Chapter A.")
        st.stop()

    if not text_b.strip():
        st.error("No readable text was found in Chapter B.")
        st.stop()

    with st.expander("Preview Uploaded Chapters"):

        preview_a, preview_b = st.columns(2)

        with preview_a:
            st.text_area(
                "Chapter A",
                text_a,
                height=220,
                key="preview_a"
            )

        with preview_b:
            st.text_area(
                "Chapter B",
                text_b,
                height=220,
                key="preview_b"
            )

    cross_button = st.button(
        "Generate Cross-Disciplinary Knowledge Map",
        type="primary",
        use_container_width=True
    )

    if cross_button:

        signature_a = get_file_signature(
            uploaded_file_a
        )

        signature_b = get_file_signature(
            uploaded_file_b
        )

        with st.spinner(
            "Analyzing both chapters and discovering "
            "cross-disciplinary relationships..."
        ):

            try:

                result = run_cross_analysis(
                    text_a,
                    text_b,
                    uploaded_file_a.name,
                    uploaded_file_b.name,
                    signature_a,
                    signature_b
                )

                st.session_state["cross_data"] = result

                mode = result.get(
                    "analysis_mode",
                    "Analysis"
                )

                if mode == "Gemini AI":
                    st.success(
                        "Cross-disciplinary analysis completed using Gemini AI."
                    )

                elif mode == "Cached result":
                    st.success(
                        "Loaded the saved analysis. No new Gemini request was needed."
                    )

                else:
                    st.warning(
                        "Gemini was unavailable, so ConceptFlow AI "
                        "automatically used its local analysis engine. "
                        "The presentation can continue."
                    )

            except Exception as e:

                st.error(
                    "The analysis could not be completed. "
                    f"Details: {e}"
                )

    if "cross_data" in st.session_state:

        cross_data = st.session_state["cross_data"]

        subject_a = cross_data.get(
            "subject_a",
            "Chapter A"
        )

        subject_b = cross_data.get(
            "subject_b",
            "Chapter B"
        )

        concepts_a = cross_data.get(
            "concepts_a",
            []
        )

        concepts_b = cross_data.get(
            "concepts_b",
            []
        )

        relationships = cross_data.get(
            "cross_relationships",
            []
        )

        analysis_source = cross_data.get(
            "analysis_mode",
            "Analysis"
        )

        st.divider()

        st.header("Cross-Disciplinary Intelligence")

        stat1, stat2, stat3, stat4 = st.columns(4)

        with stat1:
            st.metric(
                f"{subject_a} Concepts",
                len(concepts_a)
            )

        with stat2:
            st.metric(
                f"{subject_b} Concepts",
                len(concepts_b)
            )

        with stat3:
            st.metric(
                "Cross-Disciplinary Links",
                len(relationships)
            )

        with stat4:
            st.metric(
                "Analysis Source",
                analysis_source
            )

        st.divider()

        st.header("Concepts Extracted Independently")

        left, right = st.columns(2)

        with left:

            st.subheader(subject_a)

            for concept in concepts_a:

                name = concept.get("name", "Unknown")
                description = concept.get(
                    "description",
                    ""
                )
                concept_type = concept.get(
                    "type",
                    "Concept"
                )

                with st.container(border=True):

                    st.markdown(
                        f"**{name}**"
                    )

                    st.write(
                        description
                    )

                    st.caption(
                        concept_type
                    )

        with right:

            st.subheader(subject_b)

            for concept in concepts_b:

                name = concept.get("name", "Unknown")
                description = concept.get(
                    "description",
                    ""
                )
                concept_type = concept.get(
                    "type",
                    "Concept"
                )

                with st.container(border=True):

                    st.markdown(
                        f"**{name}**"
                    )

                    st.write(
                        description
                    )

                    st.caption(
                        concept_type
                    )

        st.divider()

        st.header("Cross-Disciplinary Knowledge Map")

        st.caption(
            "Connections discovered between concepts from "
            "the two uploaded chapters."
        )

        if not relationships:

            st.warning(
                "No strong cross-disciplinary connections were detected."
            )

        else:

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
                    "connects"
                )

                confidence = relation.get(
                    "confidence",
                    "Medium"
                )

                left_space, center_space, right_space = st.columns(
                    [1, 2, 1]
                )

                with center_space:

                    st.markdown(
                        f"""
                        <div class="relationship-source">
                            ● {html.escape(source)}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"""
                        <div class="relationship-label">
                            {html.escape(relationship)}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        """
                        <div class="relationship-arrow">
                            ↓
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"""
                        <div class="relationship-target">
                            ● {html.escape(target)}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.caption(
                        f"{subject_a} → {subject_b} | "
                        f"Confidence: {confidence}"
                    )

                st.divider()

        st.header("How ConceptFlow AI Solves the Challenge")

        st.info(
            "Two independent knowledge structures → "
            "concept comparison → cross-disciplinary reasoning → "
            "combined knowledge map"
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "ConceptFlow AI | Visual Knowledge Mapping for STEM Education"
)
