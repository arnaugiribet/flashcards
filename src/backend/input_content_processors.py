import logging
logger = logging.getLogger("src/backend/input_content_processors.py")
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def get_docx(content):
    from docx import Document
    doc = Document(content)
    full_text = []
    
    for block in doc._element.body:
        if block.tag.endswith('p'):  # Paragraph
            # Get text directly from the paragraph element
            paragraph_text = block.text
            if paragraph_text.strip():  # Only add non-empty paragraphs
                full_text.append(paragraph_text)
        elif block.tag.endswith('tbl'):  # Table
            table = []
            # Navigate the XML to get table cells
            for row in block.tr_lst:
                cells = [cell.text for cell in row.tc_lst]
                table.append(' | '.join(cells))
            full_text.append('\r'.join(table))

    full_text = "  ".join(full_text)
    return full_text

def get_pdf(content):
    """
    Extract text and tables from a PDF using pdfplumber.
    Args:
        content: File content (bytes) or file path (str)
    Returns:
        str: Extracted text with preserved structure
    """
    import pdfplumber
    import io

    try:
        logger.debug("Reading content from file...")
        pdf = pdfplumber.open(content)

        document_content = []
        
        # Process each page
        for page in pdf.pages:
            page_content = []
            
            # Extract text from the page
            text = page.extract_text()
            if text:
                page_content.append(text)

            # Extract tables from the page
            tables = page.extract_tables()
            
            if tables:
                # Process each table
                for table in tables:
                    # Clean the table (remove None and empty strings)
                    cleaned_table = [
                        [str(cell).strip() if cell is not None else '' for cell in row]
                        for row in table
                    ]
                    # Convert table to string format
                    table_str = '\n'.join(
                        ' | '.join(cell for cell in row if cell)
                        for row in cleaned_table
                        if any(cell for cell in row)  # Skip empty rows
                    )
                    if table_str:
                        page_content.append(f"[TABLE]\n{table_str}\n[/TABLE]")
            
            # Add non-empty page content
            if page_content:
                document_content.append('\n\n'.join(page_content))
        
        pdf.close()
        return '\n\n'.join(document_content)
    
    except Exception as e:
        raise Exception(f"Error extracting PDF content: {str(e)}")