# ---

**🏗️ Architecture Design Review (ADR)**

**Feature Name:** \[Enter Name and Jira link\]

**Lead Developer:** \[Name\] | **Date:** \[Date\] | **Priority:** \[Low/Med/High\]

### ---

**1\. Executive Summary**

*A high-level view for stakeholders and the Architect.*

| Section | Developer Input |
| :---- | :---- |
| **Problem Statement** | *Describe the pain point this feature addresses.* |
| **High-Level Solution** | *Summarize the technical approach in 2-3 sentences.* |
| **Success Metrics** | *How do we measure success? (e.g., Latency \< 500ms, 95% AI accuracy).* |

### ---

**2\. The "Where": Code & Data Changes**

*Identifying the blast radius before coding starts.*

| Area | Targeted Repositories / Files / Modules |
| :---- | :---- |
| **Frontend** |  |
| **Backend/APIs** |  |
| **Database** | *List new tables, columns, or vector indices.* |
| **Config/Infra** | *New environment variables or third-party keys.* |

### ---

**3\. Architecture & AI Strategy**

*The "logic" of the solution.*

| Component | Design Details |
| :---- | :---- |
| **System Diagram** | *\[Insert/Paste Diagram Link or Image here\]* |
| **LLM / Model** | *Which model? (e.g., Gemini 1.5 Pro, GPT-4o). Why this one?* |
| **Context Strategy** | *How is the prompt built? (e.g., RAG, few-shot, system instructions).* |
| **Output Validation** | *How do we catch hallucinations or bad formatting?* |

### ---

**4\. Risk & Reliability (AI-Era Checklist)**

*Addressing the non-deterministic nature of AI.*

| Risk | Mitigation Plan |
| :---- | :---- |
| **LLM Failure** | *What is the fallback if the provider is down or rate-limited?* |
| **Data Privacy** | *How are we ensuring PII/sensitive data is not leaked to the model?* |
| **Cost Control** | *What is the estimated token usage per user/session?* |
| **Performance** | *How will we handle long inference times? (e.g., Streaming, Async).* |

### ---

### 

### **5\. Reviewer’s feedback** 

| Status | Feedback / Required Changes |
| :---- | :---- |
| **\[ \] Approved** |  |
| **\[ \] Revise** |  |

### 