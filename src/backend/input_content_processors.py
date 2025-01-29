def get_docx_text(content):
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