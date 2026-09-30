# ConceptFlow AI

## Visual Concept Mapper for STEM Textbooks

ConceptFlow AI is a GenAI-powered visual concept mapping system that transforms dense STEM textbook chapters into interactive visual knowledge maps.

Instead of only summarizing textbook content, ConceptFlow AI identifies important concepts, generates student-friendly explanations, and discovers relationships between concepts.

The system also supports cross-disciplinary analysis, where two chapters from different STEM subjects can be analyzed together to discover conceptual connections between the two domains.

---

## Problem Statement

STEM textbooks contain large amounts of interconnected information, but concepts are often presented sequentially within individual chapters.

Students may understand individual topics but struggle to answer questions such as:

- How are two concepts connected?
- What concept depends on another concept?
- How does knowledge from one STEM subject connect to another?
- What are the hidden relationships between concepts across different chapters?

Traditional summarization reduces content into shorter text but does not clearly reveal the underlying conceptual structure.

### Our Goal

Build an intelligent system that converts textbook content into a visual representation of concepts and their relationships.

---

# Solution

ConceptFlow AI uses Generative AI to extract concepts and relationships from STEM textbook chapters and convert them into an interactive knowledge graph.

The system supports two analysis modes:

### Single Chapter Analysis

A user uploads one STEM textbook chapter in PDF format.

The system:

1. Extracts text from the PDF.
2. Identifies important concepts.
3. Generates student-friendly explanations.
4. Identifies relationships between concepts.
5. Creates an interactive concept map.

### Cross-Disciplinary Analysis

The user uploads two textbook chapters from different STEM subjects.

The system:

1. Extracts text from both chapters.
2. Analyzes each chapter.
3. Identifies important concepts from both sources.
4. Compares the extracted concept information.
5. Identifies meaningful cross-disciplinary relationships.
6. Generates a combined visual concept map.

This allows the system to reveal conceptual bridges between different STEM domains.

---

# Cross-Disciplinary Challenge

A key requirement of the challenge is to determine whether concept extraction can generalize beyond a single textbook chapter.

ConceptFlow AI addresses this by accepting two independently uploaded textbook chapters and identifying relationships between concepts across the two sources.

```text
Chapter A                    Chapter B
    │                            │
    ↓                            ↓
Concept Extraction         Concept Extraction
    │                            │
    └──────────────┬─────────────┘
                   ↓
       Cross-Disciplinary
       Relationship Analysis
                   ↓
          Combined Concept Map
