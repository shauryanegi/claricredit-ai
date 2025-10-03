import re
import json
import os

def split_md_by_page(md_file):
    """
    Splits a markdown file by separators like:
    \n\n{71}------------------------------------------------\n\n
    (48 dashes exactly)
    Saves a dict {page_number: page_content} to output_file.
    """
    # Exactly 48 dashes
    pattern = r"\n\n\{(?:\d+)\}-{48}\n\n"
    # Get root filename only
    root_name = os.path.splitext(os.path.basename(md_file))[0]
    output_file = os.path.join("outputs", f"{root_name}_pages.json")
    # output_file=f"{root_name}_pages.json"

    with open(md_file, "r", encoding="utf-8") as f:
        md_content = f.read()


    pages = re.split(pattern, md_content)

    # page_dict = {}
    # for i in range(1, len(splits), 2):
    #     page_number = int(splits[i])
    #     page_content = splits[i + 1]
    #     page_dict[page_number] = page_content
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)
    print(output_file)
    return output_file
    # Save to file


#     # return page_dict
# with open("/home/chhavi/Downloads/FSA-43482714(1) 1.md", "r", encoding="utf-8") as f:
#     md_content = f.read()

# # split_md_to_page_dict(md_content, "pages.json")

# print(f"Saved pages to pages.json")
