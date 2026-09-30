import os
import json

from dotenv import load_dotenv
from google import genai


# Load .env
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY was not found. "
        "Please check your .env file."
    )


# Gemini client
client = genai.Client(
    api_key=API_KEY
)


def analyze_text(text):

    prompt = f"""
You are an expert STEM educational knowledge-graph generator.

Analyze the textbook content below.

Your job is to create a STRUCTURED CONCEPT MAP,
not a simple summary.

Identify important concepts and explain how they
are connected.

Return ONLY valid JSON.

Use exactly this structure:

{{
    "concepts": [
        {{
            "name": "Concept name",
            "description": "Simple student-friendly explanation",
            "type": "Core Concept"
        }}
    ],

    "relationships": [
        {{
            "source": "Exact Concept A",
            "target": "Exact Concept B",
            "relationship": "short relationship phrase"
        }}
    ]
}}

RULES:

1. Extract 6 to 15 important concepts.

2. Concept names must be short and clear.

3. Every relationship source MUST exactly match
   a concept name.

4. Every relationship target MUST exactly match
   a concept name.

5. Relationship phrases must explain WHY
   the concepts are connected.

GOOD relationship examples:

"uses"
"transforms"
"depends on"
"produces"
"contains"
"calculates"
"updates"
"leads to"
"part of"

BAD relationship examples:

"related"
"connected"
"associated"

6. Prefer directional relationships.

7. Avoid duplicate relationships.

8. Avoid unnecessary concepts.

9. Organize concepts from foundational ideas
   toward advanced ideas.

10. The final graph should help an undergraduate
    understand HOW concepts connect.

TEXTBOOK CONTENT:

{text}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt
    )

    result = response.text.strip()

    # Remove markdown fences if Gemini adds them
    if result.startswith("```json"):
        result = result[7:]

    if result.startswith("```"):
        result = result[3:]

    if result.endswith("```"):
        result = result[:-3]

    result = result.strip()

    return json.loads(result)