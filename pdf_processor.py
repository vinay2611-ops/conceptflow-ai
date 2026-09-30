import fitz


def extract_text_from_pdf(uploaded_file):
    """
    Extract text from an uploaded PDF file.
    """

    pdf_document = fitz.open(
        stream=uploaded_file.read(),
        filetype="pdf"
    )

    text = ""

    for page in pdf_document:
        text += page.get_text()

    pdf_document.close()

    return text