# AI Usage Disclosure

In accordance with the Journal of Open Source Software (JOSS) AI usage policy, this document outlines the extent to which generative AI tools were utilized in the development of this package and its accompanying documentation.

## 1. Tools and Models Used

During the lifecycle of this project, the following generative AI models were used:

- Gemini 3.1 Pro & Gemini 3.6 Thinking.
- Claude 5.5 Sonnet.
- GPT 5.4.

## 2. Nature and Scope of Assistance

AI assistance was strictly used as an accelerator for implementation, boilerplate generation, and troubleshooting, bounded by the following scopes:

- **Core Code & Architecture:** The framework and architecture were originally designed based on previous workflows at the Servicio Geológico Colombiano (SGC). AI was used to translate logical outlines into Python syntax and refactor specific algorithmic components (e.g., implementing the sorted slicing window approach for duplicate detection).
- **Testing and CI/CD:** AI generated `pytest` boilerplate and test scaffolding. The human author defined the edge cases, while the AI assisted in implementing the specific mock structures, monkeypatching, and example configuration files. AI was also used to enhance a pre-existing GitHub Actions workflow to create a more robust automated testing pipeline.
- **Frontend and CLI:** For the Streamlit application and CLI tools, AI was utilized exclusively to troubleshoot specific UI and terminal rendering issues.
- **Documentation:** AI drafted Python docstrings by reading the source files and assisted in structuring general documentation. However, the core technical tutorials were written entirely by the human author to guarantee functional accuracy.

## 3. Confirmation of Review

The author confirms that human authors reviewed, edited, and validated all AI-assisted outputs. All core design decisions, architectural logic, scientific claims, and evaluative determinations remain solely the original work and responsibility of the human author. The author remains fully responsible for the accuracy, originality, licensing, and ethical compliance of all submitted materials in this repository.

