import re
import json
import os

def split_md_by_page(md_file):
    """
    Splits a markdown file by page markers like:
    {1}----
    {2}----
    etc.

    Produces a JSON file as a list:
    [
      "Page 1 content...",
      "Page 2 content...",
      ...
    ]
    """
    # Regex: {number} followed by one or more dashes
    page_pattern = r"\{(\d+)\}-+"

    # Get root filename
    root_name = os.path.splitext(os.path.basename(md_file))[0]
    output_file = os.path.join("outputs", f"{root_name}_pages.json")

    # Read markdown content
    with open(md_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Split content keeping page numbers
    pages = re.split(page_pattern, md_content, flags=re.MULTILINE)

    # Extract only the page contents (ignore intro and page numbers)
    page_contents = []
    for i in range(1, len(pages), 2):
        content = pages[i + 1].strip()
        page_contents.append(content)

    # Ensure outputs directory exists
    os.makedirs("outputs", exist_ok=True)

    # Save list to JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(page_contents, f, ensure_ascii=False, indent=2)

    print(f"Saved: {output_file}")
    return output_file

    # Save to file


#     # return page_dict
# with open("/home/chhavi/Downloads/FSA-43482714(1) 1.md", "r", encoding="utf-8") as f:
#     md_content = f.read()

# # split_md_to_page_dict(md_content, "pages.json")

# print(f"Saved pages to pages.json")
