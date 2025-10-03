
from datetime import datetime
current_year = datetime.now().year

CREDIT_MEMO_SECTIONS = {
    "Borrower, Management, and Ownership": [

            {
            "user_query": 
            """Generate the 'Borrower, Management' section of the credit memo. 
            It should include the 
            - Company background
            - The names of directors 
            - Overview of the industry
            - Relationship with the bank (e.g., prior loans, payment history).
            Be elaborate. Include as many facts as you can from the provided context.
            Do not include anything that is not present in the context""",

            "semantic_queries": [
                {"query": "Provide a summary of the company, including its history, core business operations, and what products or services it offers.", "k": 3},
                {"query": "Describe the company's management team and board of directors, including the organizational structure.", "k": 3},
                {"query": "Company's relationship history with the bank","k":3,"filter":"loan"}
            ]
            },
            {
            "user_query": 
            """Generate the 'Ownership' section of the credit memo. 
            It should include the 
            - the no. of shares or percentwise shares of the directors if available
            - any information about shareholders
            - any other important information
            Especialy include any CORRECT numerical information about shares if present).
            Be elaborate. Include as many facts as you can from the provided context.
            Do not include anything that is not present in the context""",
                "semantic_queries": [
                    {"query": "Who are the shareholders of the company, and how are shares distributed among them?", "k": 3},
                ]
            }
        ],
    "Financial Analysis": [
        {
            "user_query": f"""Generate the financial analysis section based on the provided context.
            It should include the 
            - Market trends and comparison to industry benchmarks
            - Cash flow projections and analysis
            - Company's key financial highlights in {current_year-2} and {current_year-1}
            - Any other important information if present.
            Be elaborate. Include as many facts as you can from the provided context.
            Do not include anything that is not present in the context""",
            "semantic_queries": [
                {"query": f"What were the company's key financial highlights in {current_year-2} and {current_year-1}?", "k": 3},
                {"query": "Cash flow projections and analysis", "k": 3},
                {"query": "Market trends and comparison to industry benchmarks", "k": 3},
            ]
        }
    ],

    "Risk Assessment": [
        {
            "user_query": "Generate the risk assesment section by identifying the risks faced by the company.",
            "semantic_queries": [
                {"query": "Risks faced by the business", "k": 5}
            ]
        }
    ]

}



# ignore
        # "semantic_queries": [
        #     {"query": "Provide a summary of the company, including its history, core business operations, and what products or services it offers.", "k": 3},
        #     {"query": "Who are the shareholders of the company, and how are shares distributed among them?", "k": 3},
        #     {"query": "Describe the company's management team and board of directors, including the organizational structure.", "k": 3},
        # ],
        # "user_queries":[
        #     """Generate the 'Borrower, Management' section of the credit memo. 
        #     It should include the 
        #     - Company history
        #     - the names of directors 
        #     - overview of the industry
        #     Be elaborate. Include as many facts as you can from the provided context.
        #     Do not include anything that is not present in the context""",

        #     """Generate the 'Ownership' section of the credit memo. 
        #     It should include the 
        #     - the no. of shares/ percentwise shares of directors if available
        #     - any information about shareholders
        #     - and any other important information if present.
        #     Especialy include any CORRECT numerical information about shares if present).
        #     Be elaborate. Include as many facts as you can from the provided context.
        #     Do not include anything that is not present in the context""",
        #     ]
        # "user_queries": [