from datetime import datetime

current_year = datetime.now().year
bank_name = "Maybank Malaysia"

SECTION_ORDER = [
    "Executive Summary",
    "Background, Management, and Ownership",
    "Financial Analysis",
    "Collateral and Security",
    "Risk Assessment",
    "Loan Structure and Terms",
    "Recommendation and Conclusion",
]

CREDIT_MEMO_SECTIONS = {
    "Background, Management, and Ownership": [
        {
            "user_query":
                f"""/no_think Write about the-
        - Board of directors/names of directors or management team
        Only use relevant information from the context to generate the report as some part of the context could be irrelevant.
        Do not include anything that is not present in the context.
        """,

            "semantic_queries": [
                {"query": "Describe the company's board of directors including their names and positions", "k": 3},
            ],
            "full_page": True,
            "fin_data_needed": False
        },
        {
            "user_query":
                f"""/no_think Write about the-
        - Relationship with {bank_name} (e.g., prior loans, payment history).
        Only use relevant information from the context to generate the report as some part of the context could be irrelevant.
        Do not include anything that is not present in the context.""",

            "semantic_queries": [
                {"query": "Company's relationship history with the bank", "k": 3, "filter": "loan"},
            ],
            "full_page": True,
            "include_for_recommendation": True,
            "fin_data_needed": False
        },
        {
            "user_query":
                f"""/no_think Write regarding-
        - About the company
        - What the company does
        - Overview of the industry
        Be elaborate. Include as many facts as you can from the provided context.
        Do not include anything that is not present in the context.""",
            "semantic_queries": [
                {"query": "About us, what we do, our history", "k": 3},
            ],
            "full_page": True, "include_for_summary": True, "fin_data_needed": False
        },
        {
            "user_query":
                """/no_think Write about the-
                - Percentage shares of the directors
                - any information about shareholders
                Only use relevant contexts to generate the report as some of the context could be irrelevant.
                Do not include anything that is not present in the context.
                Use an appropriate title for this section.""",
            "semantic_queries": [
                {"query": "Who are the shareholders of the company, and how are shares distributed among them?",
                 "k": 2},
            ],
            "full_page": True, "fin_data_needed": False
        }
    ],
    "Financial Analysis": [
        {
            "user_query": """
        /no_think Analyze the company's financial statements from the annual reports provided.

        Extract and discuss:
        - Revenue trends: What are the actual revenue numbers? How much has it grown/declined year-over-year? What does this growth rate tell us about business momentum and market position?
        - Profitability (margins, EBITDA): What are the actual margin percentages? Are they improving or declining? What does this say about pricing power, cost control, and operational efficiency?
        - Assets, liabilities, equity: What are the actual balance sheet numbers? How is leverage changing? What does the asset composition tell us about the business?

        For EVERY number you extract, explain:
        1. What the number actually is (state it clearly)
        2. WHY this number is significant for credit assessment
        3. What it reveals about the company's financial health and ability to repay debt

        Note: Only take up values from the given context and do not calculate or assume values.

        Write in detailed paragraphs. Make every number meaningful by explaining its significance.

            """,
            "semantic_queries": [
                {"query": "annual report financial statements income statement revenue EBITDA net income profit",
                 "k": 2},
                {"query": "balance sheet assets liabilities equity shareholders equity total debt", "k": 2},
                {"query": "year over year financial performance, total revenue growth margins profitability trends",
                 "k": 1}
            ],
            "full_page": True,
            "include_for_recommendation": True, "fin_data_needed": False
        },
        {
            "user_query": """
        /no_think You are a credit analyst. Using the extracted information from the company’s financial documents, produce a **detailed, plain-language analysis of key financial ratios**. Focus only on ratios, including but not limited to:

        -Gearing Ratio
        -Cash Ratio
        -Current Ratio
        -Quick Ratio
        -Debt-to-Equity Ratio
        -Debt Ratio
        -Net Profit Margin
        -Operating Margin
        -Return on Assets (ROA)
        -Return on Equity (ROE)
        -Asset Turnover Ratio
        -Inventory Turnover
        -Operating Cash Flow Ratio
        -Free Cash Flow
        -Debt to Asset Ratio

        Instructions:

        1. For each ratio, clearly explain:
        - What the ratio value actually means in simple terms
        - How it compares to typical thresholds, regulatory limits, or industry standards
        - What it implies about the company’s **repayment ability, liquidity, leverage, and creditworthiness**
        - Any cushion or buffer (e.g., cash flow cushion for DSCR, equity buffer for LTV)
        - How sensitive the ratio is to adverse changes (e.g., how much cash flow could drop before DSCR breaches 1.25x)

        2. Do **not** discuss unrelated items like loans, derivatives, fair value, or swaps unless directly tied to a ratio.

        3. Present each ratio as a separate section with:
        - The ratio name and actual value
        - Plain-language explanation
        - Significance and risk assessment
        - Optional comparison to prior periods if available

        Note: Only take up values from the given context and do not calculate or assume values.
        Note: If you are not able to find values from the Financial Data, see it from context,
        Note: If values are not present do not output anything for that ratio.
        Write detailed paragraphs for each ratio. Don't just state numbers - explain what they MEAN and why they MATTER.
            """,
            "semantic_queries": [
                {"query": "capital management, gearing ratio, net debt", "k": 2, "filter": "table"},
                {"query": "current ratio, quick ratio, total assets liabilities", "k": 2, "filter": "table"},
            ],
            "full_page": True,
            "include_for_summary": True,
            "include_for_recommendation": True, "fin_data_needed": True
        },
        {
            "user_query": """
        /no_think Analyze the company’s cash flow statements from the annual reports to assess business quality and repayment capacity. Focus on:

        **Operating Cash Flow (OCF):**
        - Report actual OCF values for each year.
        - Describe the trend (growing, stable, or declining) and magnitude of change.
        - Explain what this pattern indicates about the company’s cash generation strength and stability.
        - Assess whether OCF comfortably covers debt servicing needs.

        **Investing Cash Flow (ICF):**
        - Summarize spending on capital expenditures and investments.
        - Interpret what this investment level reveals about growth priorities and long-term sustainability.

        **Financing Cash Flow (FCF):**
        - Explain whether the company is raising or repaying debt, and note any dividend or distribution payments.
        - Discuss how these flows affect leverage and liquidity.

        **Cash Flow Outlook (if mentioned):**
        - Summarize projected cash flows and comment on their realism compared to historical performance.
        - Evaluate whether projected flows support timely loan repayment.

        For every cash flow metric, explain:
        - The actual figure,
        - What it implies about operational performance,
        - Whether it ensures adequate debt coverage,
        - And what risks or vulnerabilities exist to ongoing cash generation.

        **Note: Do not calculate anything on your own use values only from context

        Write detailed analytical paragraphs integrating these insights into an overall assessment of repayment confidence.
            """,
            "semantic_queries": [
                {"query": "consolidated cash flow from operations operating cash flow OCF annual report", "k": 2},
                # {"query": "free cash flow FCF cash available debt service", "k": 1},
                # {"query": "cash flow projections forecast future cash flow", "k": 1},
                {
                    "query": "statement of cash flows, net cash used, cash used in investing activities, operating activities, financing activites",
                    "k": 4, "filter": "table"},
            ],
            "full_page": False,
            "include_for_recommendation": True, "fin_data_needed": False
        }
    ],
    "Collateral and Security": [
        {
            "user_query": """
        /no_think You are a credit analyst. Using the retrieved information about the company’s pledged assets and appraisals, provide a detailed **collateral adequacy analysis** in the context of the proposed loan structure.

        ### Instructions:

        1. **Description of Pledged Assets**
        - Identify each asset pledged (e.g., plant & machinery, land, accounts receivable, inventory).
        - Include appraised values and any notes on valuation methodology or recent appraisal dates.

        2. **Loan-to-Value (LTV) Assessment**
        - Compare the total appraised value of pledged assets to the proposed loan amount.
        - Calculate or confirm the LTV ratio.
        - Discuss whether the LTV indicates adequate collateral coverage relative to industry norms or bank thresholds.

        3. **Collateral Quality & Perfection**
        - Assess the type and quality of assets (liquid vs. illiquid, fixed vs. current, marketable vs. specialized).
        - Mention if liens or security interests are perfected or legally enforceable.

        4. **Adequacy vs. Proposed Loan**
        - Discuss whether the pledged collateral adequately supports the proposed loan of RM 7,500,000.
        - Consider sources and uses of funds (e.g., new plant, acquisition, working capital) and whether the collateral provides sufficient protection.

        5. **Overall Implications**
        - Explain how collateral quality and LTV affect the lender’s risk.
        - Highlight any gaps, risks, or recommendations regarding additional security or monitoring.


        Write **detailed paragraphs**, not bullet points, integrating numeric insights (appraised values, LTV) and interpreting what the collateral picture means for **loan security and risk**.
            """,
            "semantic_queries": [
                {"query": "total assets, liabilities, real estate, equipment, inventory)", "k": 2, "filter": "loan"},
            ],
            "full_page": True,
            "include_for_recommendation": True, "fin_data_needed": False
        }
    ],
    "Risk Assessment": [
        {
            "user_query": """/no_think as an information extraction system and analyze the provided context to identify and report ONLY the company's external or internal credit rating and risk rating.
### INSTRUCTIONS:
1. **Content Expectations:**
- If multiple ratings are present, list all of them.
- Only use relevant information from the context to generate the report as some part of the context could be irrelevant.
- Do not include anything that is not present in the context.
- This output will directly be a part of a bigger report with remaining sections. So refrain from using conversational language.
- Do not include any personal opinions or interpretations and always be professional without adding any emojis.

2. **FORMATTING**
- Include the details about credit and risk ratings under the section titled "Credit Ratings" or "Risk Ratings" respectively.
- If no credit rating information is found in the context, respond with 'Details about credit ratings were not found in the provided document.' under the credit rating section.
- If no risk rating information is found in the context, respond with 'Details about risk ratings were not found in the provided document.' under the risk rating section.
- Use bullet points or numbered lists or tabular format for clarity if multiple ratings are mentioned in each section.

### OUTPUT EXAMPLE:
**Credit Ratings**
Details about the credit ratings found in the provided document (if any).

**Risk Ratings**
Details about the risk ratings found in the provided document (if any).

""",
            "semantic_queries": [
                {
                    "query": "CARE A2+,CARE A-, AAA, Aaa, AA+, AA, AA-, Aa1, Aa2, Aa3, A+, A, A-, A1, A2, A3, BBB+, BBB, BBB-, Baa1, Baa2, Baa3",
                    "k": 5},
                {"query": "Details of credit rating, ratings, rating actions", "k": 2},
                {"query": "Details of risk rating", "k": 2},
                {"query": "Details of external credit assessment and internal risk evaluation", "k": 3}
            ],
            "full_page": False,
            "include_for_summary": True, "fin_data_needed": False
            # "include_for_recommendation": True
        },
        {
            "user_query": """/no_think You are a senior credit analyst. Using only the  above provided context, prepare a **professional narrative section** on the company’s **Key Strengths** relevant to a credit assessment.
### INSTRUCTIONS:
1. **Style & Tone:**
- Write in a formal, analytical, and concise report style used in credit memos.
- Avoid repetitive or templated bullet structures (e.g., “CLAIM / EVIDENCE / IMPACT”).
- Integrate evidence naturally into analytical sentences.
**Example:**
“Strong liquidity position with significant cash and bank balances. The company reported total cash and bank balances of x and y, indicating healthy liquidity and strong cash flow coverage [Annual Report, p.54].”

Note: The above example is for illustrative purposes only. Do not copy it verbatim.

2. **Content Expectations:**
- Identify and elaborate on **3–6 major strengths**.
- Focus on aspects most relevant to creditworthiness, such as:
- Financial health and capital structure
- Market position, diversification, and recurring income
- Profitability and efficiency metrics
- Strategic or operational excellence
- If numbers (such as revenue, market share, or margins) related to any strengths are mentioned, include them with context.
- Always include source references in brackets (e.g., [Sustainability Report]) if mentioned. This can be the section name/title from the provided context.

3. **Formatting:**
- Use a numbered list or concise paragraphs.
- Begin each point with a short **bold title** (the main strength).

4. **Factual Integrity:**
- Use only facts from the input context.
- Always include source references in brackets (e.g., [Sustainability Report]) if mentioned. This can be the section name/title from the provided context.
- Do not infer or fabricate data.

5. **Closing Summary:**
- End with a brief analytical paragraph summarizing how these strengths enhance the company’s credit profile.

6. **Analyst Rationale (3–5 bullets):**
- Conclude with an “Analyst Rationale” summarizing why the strengths positively influence credit standing.

### OUTPUT EXAMPLE:
**Strengths**

1. **Strength title**
Reasoned analysis of the strength with supporting data, numbers and context [References].

2. **Strength title**
Reasoned analysis of the strength with supporting data, numbers and context [References].

**Analyst Rationale**
Opinions as an analyst on how these strengths impact credit quality.

Note:If no strengths are identified, state: “The provided context does not detail specific strengths or competitive advantages.”""",

            "semantic_queries": [
                {"query": "Strong financial foundation, liquidity ratios, assets, profitability, or solvency metrics",
                 "k": 5},
                {
                    "query": "Company's competitive advantages, financial strengths, assets, liquidity position, and stability for lenders",
                    "k": 5},
                {"query": "Market position, diversification, recurring income, or growth prospects", "k": 5},
                {"query": "Technological innovation, operational excellence, or brand leadership", "k": 5}
            ],
            "full_page": False,
            "include_for_summary": True,
            "include_for_recommendation": True, "fin_data_needed": False
        },
        {
            "user_query": """/no_think You are a senior credit analyst. Using only the above provided context, prepare a **professional narrative section** on the company’s **Key Weaknesses** relevant to a credit assessment.
### INSTRUCTIONS:
1. **Style & Tone:**
- Write in a concise, analytical tone consistent with credit memos.
- Avoid templates like “ISSUE / IMPACT / MITIGANT”; instead, integrate the analysis fluidly.
**Example:**
“Elevated leverage remains a key concern, with total borrowings increasing to x from y. Despite stable cash flows, interest coverage has weakened, constraining near-term financial flexibility [Reference].”

Note: The above example is for illustrative purposes only. Do not copy it verbatim.

2. **Content Expectations:**
- Identify **3–6 major weaknesses** relevant to credit risk.
- Focus on issues such as:
- Declining profitability or margins
- High leverage and weak coverage ratios
- Revenue concentration
- Operational or governance constraints
- If numbers (such as revenue, market share, or margins) related to any weakness are mentioned, include them with context.
- Always include source references in brackets (e.g., [Sustainability Report]) if mentioned. This can be the section name/title from the provided context.

3. **Formatting:**
- Each weakness should begin with a **bold heading** followed by an analytical paragraph.

4. **Factual Integrity:**
- Use only verified data from the input context.
- Always include source references in brackets (e.g., [Sustainability Report]) if mentioned. This can be the section name/title from the provided context.
- Do not infer or fabricate information.

5. **Closing Summary:**
- Summarize how these weaknesses may impact creditworthiness or risk stability.

6. **Analyst Rationale (3–5 bullets):**
- End with bullet points summarizing the impact of these weaknesses on credit quality.

### OUTPUT EXAMPLE:
**Weaknesses**

1. **Weakness title**
Reasoned analysis of the weakness with supporting data, numbers and context [References].

2. **Weakness title**
Reasoned analysis of the weakness with supporting data, numbers and context [References].

**Analyst Rationale**
Opinions as an analyst on how these weaknesses impact credit quality.

Note: If no weaknesses are identified, state: “The provided context does not detail specific weaknesses or vulnerabilities.”""",
            "semantic_queries": [
                {"query": "high debt leverage borrowings interest expense", "k": 5},
                {"query": "declining revenue profit losses negative trends", "k": 4},
                {"query": "liquidity constraints cash flow problems working capital", "k": 4},
                {"query": "competition pressure market challenges industry headwinds", "k": 3},
            ],
            "full_page": False,
            "include_for_summary": True,
            "include_for_recommendation": True, "fin_data_needed": False
        },
        {
            "user_query": """/no_think You are a senior credit analyst. Using only the above provided context, prepare a **professional narrative section** on the company’s **Key Opportunities** that could strengthen its credit profile.
### INSTRUCTIONS:
1. **Style & Tone:**
- Maintain a formal and analytical tone consistent with credit memoranda.
- Avoid speculative statements; rely strictly on provided context.
**Example:**
“The company’s expansion into renewable energy projects worth x presents a significant growth avenue, enhancing revenue diversification and improving long-term cash flow stability [Management Discussion, p.33].”

Note: The above example is for illustrative purposes only. Do not copy it verbatim.

2. **Content Expectations:**
- Identify **3–5 opportunities** likely to enhance credit strength.
- Focus on initiatives such as:
- Market or revenue diversification
- Strategic investments or partnerships
- Technological or operational improvements
- Capital optimization and deleveraging initiatives
- If numbers related to any opportunity are mentioned, include them with context.
- Always include source references in brackets (e.g., [Sustainability Report]) if mentioned. This can be the section name/title from the provided context.

3. **Formatting:**
- Each opportunity should start with a **bold heading** followed by an analytical paragraph.

4. **Factual Integrity:**
- Use only verified data from the input context.
- Always include source references in brackets (e.g., [Sustainability Report]) if mentioned. This can be the section name/title from the provided context.
- Do not infer or fabricate information.

5. **Closing Summary:**
- Summarize how these opportunities can enhance the borrower’s credit resilience.

6. **Analyst Rationale (3–5 bullets):**
- Conclude with an analytical rationale highlighting how opportunities may improve future credit quality.

### OUTPUT EXAMPLE:
**Opportunities**

1. **Opportunity Title**
Reasoned analysis of the opportunity with supporting data and context [References].

2. **Opportunity Title**
Reasoned analysis of the opportunity with supporting data and context [References].

**Analyst Rationale**
Opinions as an analyst on how these opportunities impact credit quality.

Note: If no opportunities are identified, state: “The provided context does not detail specific growth opportunities or strategic initiatives.” Do not invent opportunities beyond what is explicitly described in the context.""",
            "semantic_queries": [
                {"query": "future projects pipeline order book contracts", "k": 4},
                {"query": "diversification new products services segments", "k": 3},
                {"query": "strategic investments partnerships collaborations", "k": 3},
                {"query": "targets, vision, goals", "k": 2},
            ],
            "full_page": False,
            "include_for_recommendation": True, "fin_data_needed": False
        },
        {
            "user_query": """/no_think You are a senior credit analyst. Using only the above provided context, prepare a **professional narrative section** summarizing the company’s **Key Risks and Mitigation Strategies** relevant to its credit profile.
### INSTRUCTIONS:
1. **Style & Tone:**
- Write in a formal, analytical, and concise tone consistent with professional credit memos.
- Avoid vague or generic statements—each risk should be specific and directly supported by contextual evidence.
- Do not invent risks or mitigants beyond what is explicitly described in the context.

2. **Content Expectations:**
- Identify **3–6 major risks** disclosed or evident from the provided information.
- If more than six risks are found, prioritize those most relevant to credit assessment and at the end mention "Other risks mentioned but not detailed here include [list any additional risks briefly]."
- For each major risk, provide:
- A clear **Risk Title** summarizing the risk.
- A brief analytical **description** explaining its relevance and potential impact on creditworthiness.
- A **Mitigation** section detailing the strategies or actions taken by company to address the risk.
- If multiple strategies or actions exist, list them as bullet points for clarity.
- Focus on risks most relevant to credit assessment, such as: Financial risks (liquidity, leverage, foreign exchange exposure), Operational risks (supply chain, project execution, cost overruns), Strategic risks (market competition, regulatory change, governance), Environmental, social, or climate-related risks (ESG compliance, carbon exposure).

3. **Formatting:**
- Present each risk in the following structured format:
**Risk Title**
A concise paragraph describing the risk, its nature, cause, or implications of the risk.
*Mitigant(s):*
List of mitigation strategies or actions taken by the company.

4. **Factual Integrity:**
- Use only facts, figures, or quotes available in the input context.
- Always include source references in brackets (e.g., [Sustainability Report, p.42]) if mentioned.
- If a risk is mentioned without an explicit mitigation, state: “No specific mitigation disclosed.”

5. **Closing Summary:**
- End with a short analytical paragraph summarizing the overall effectiveness of the company’s risk management framework, highlighting whether mitigations appear adequate and proactive.

6. **Analyst Rationale (3–5 bullets):**
- After the main section, include a concise “Analyst Rationale” summarizing the overall strength or weakness of the company’s risk management approach.

### OUTPUT EXAMPLE:
**Risks and Mitigation Strategies**

1. **Risk Title**
Explanation and reasoning of the risk and its implications.
*Mitigant(s):*
List of mitigation strategies or actions taken by the company.

2. **Risk Title**
Explanation and reasoning of the risk and its implications.
*Mitigant(s):*
List of mitigation strategies or actions taken by the company.

**Analyst Rationale**
Opinions as an analyst on how these risks and mitigants impact credit quality.

Note: If no clear risks are mentioned, state: "The provided context does not detail specific identified risks." Do not fabricate risks or mitigants.""",
            "semantic_queries": [
                {"query": "managing risks principal risks risk factors risk drivers mitigants", "k": 5},
                {"query": "operational risks supply chain project execution cost overruns", "k": 3},
                {"query": "strategic risks market competition regulatory change governance", "k": 3},
                {"query": "environmental social climate risks", "k": 3},
                {"query": "risk management framework policies procedures oversight", "k": 4}
            ],
            "full_page": False,
            "include_for_recommendation": True, "fin_data_needed": False
        },
        {
            "user_query": """Based on all the information analyzed in this Risk Assessment section and above context, provide a comprehensive **Credit Implications** analysis.
### STRUCTURE:
**Credit Implications**
1. **Overall Risk Profile Summary (1 paragraph)**
Provide a synthesis of findings from risk ratings, SWOT, and risks & mitigants.

2. **Key Credit Considerations (4–6 bullet points)**
• Major strengths supporting credit quality.
• Key weaknesses and risks.
• Mitigating factors and credit stabilizers.

3. **Credit Outlook Assessment (1 paragraph)**
Offer a forward-looking perspective: improving, stable, or deteriorating outlook.

4. **Analyst Recommendations (3–5 bullets)**
• Suggested credit classification.
• Metrics or covenants to monitor.
• Review frequency and key watchpoints.

**Tone:** Balanced, professional, analytical. 
**Do not introduce new facts.** Base all analysis strictly on the provided context.""",
            "semantic_queries": [
                {"query": "management outlook future prospects guidance", "k": 4},
                {"query": "strategy priorities objectives targets", "k": 4},
                {"query": "analyst commentary market expectations", "k": 3},
                {"query": "credit metrics covenant compliance financial health", "k": 3}
            ],
            "full_page": False,
            "fin_data_needed": False
            # "include_for_recommendation": True
        }
    ],
    "Loan Structure and Terms": [
        {
            "user_query": """/no_think You are a senior credit analyst. Using only the above provided context, prepare a **professional narrative section** summarizing the company’s **Loan Structure and Terms** relevant to the credit proposal.
### INSTRUCTIONS:
1. **Style & Tone:**
- Write in a formal, analytical, and concise tone consistent with professional credit memos.
- Use clear subheadings and maintain consistent formatting with other memo sections.
- Do not fabricate or infer details beyond what is explicitly available in the context.

2. **Content Expectations:**
- Present a structured summary that covers all key components of the proposed financing arrangement:
- **Loan Amount**
- **Interest Rate**
- **Tenure / Maturity**
- **Repayment Terms**
- **Covenants**
- **Fees / Charges** (if disclosed)
- **Purpose of Funds** (briefly explain intended use)
- **Sources and Uses of Funds Table:**
Present in a structured, readable format different sources of funds and their amounts if available
- **Uses of Funds**
Present in a structured, readable format different uses of funds and their amounts if available

3. **Formatting:**
- Use bold section headers such as **Loan Amount**, **Interest Rate**, **Repayment Terms**, etc.
- Use bullet points or short structured lines for clarity where applicable.
- Use tabular structure where appropriate.

4. **Factual Integrity:**  
- Cite all figures and data exactly as they appear.
- Do not add assumptions or rephrase quantitative details.
- If certain details (e.g., covenants or fees) are missing, explicitly state: “No information on [covenants/fees/etc.] is disclosed in the provided context.”

5. **Closing Summary:**
- End with a concise analytical paragraph summarizing:
- How well the loan structure aligns with the borrower’s funding needs and repayment capacity.
- Whether the structure is consistent with the bank’s policy and prudent credit practice.

### OUTPUT EXAMPLE:
**Loan Amount:**
**Interest Rate:**
**Tenure:**
**Repayment Terms:**
**Covenants:**
**Fees:**
**Purpose of Funds:**
**Sources of Funds**
What are the sources of funds for the loan?

**Uses of Funds**
What are the uses of funds for the loan?

**Summary:**
Summarize

Note: If no loan terms are disclosed, state: ”The provided context does not contain details regarding loan amount, structure, or repayment terms.”""",
            "semantic_queries": [
                {"query": "Proposed loan amount, structure, and purpose of funds", "k": 2, "filter": "loan"},
                {"query": "Loan amount, interest rate, tenure, and repayment schedule", "k": 2, "filter": "loan"},
                {"query": "Financial covenants and loan conditions such as debt to EBITDA, DSCR, etc.", "k": 2,
                 "filter": "loan"},
                {"query": "Sources and uses of funds breakdown", "k": 2, "filter": "loan"},
                {"query": "Any applicable fees, charges, or facility costs", "k": 2, "filter": "loan"}
            ],
            "full_page": False,
            "include_for_summary": True, 
            "fin_data_needed": False
        }
    ],

    "Recommendation and Conclusion": [
        {
            "user_query": """/no_think You are an expert in providing recommendations based on credit information. Your task is to analyze the provided context and deliver a professional recommendation.
            Guidelines:
            1. The recommendation must be analytical and based only on the information in the provided context. Do not invent or assume data that is not explicitly stated.
            2. Support your recommendation with clear evidence or reasoning drawn directly from the context.
            3. If the context does not provide sufficient information to justify a recommendation, clearly state: “There is no sufficient evidence to support recommendation.”
            4. Maintain a professional tone consistent with that of an experienced financial analyst with long-term expertise in the credit domain.
            Output:
            Provide a concise, evidence-based recommendation and a brief analytical conclusion summarizing the credit data mentioned in the context. 
            """,
            "include_for_summary": True,
            "fin_data_needed": False
        }
    ],
    "Executive Summary": [
        {
            "user_query": """
        Generate a 1 page long Executive Summary section of the credit memo.
        You don't have to analyse anything, you just have to extract the following information from the context.

        Content to include (if available in context, Skip if not present):
        1. About the company
        2. Loan amount and purpose (Don't include this section if details about loan amount and purpose are not present in the context. Skip this section in that case) 
        3. Key financial metrics 
        4. Repayment information
        5. Key risks and strengths  
        6. Proposed risk rating  
        7. Final recommendation (approve or decline)
        """
            ,
            "fin_data_needed": False
        }
    ],

}