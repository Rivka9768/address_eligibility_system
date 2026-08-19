# Address Eligibility System

A Streamlit-based system that evaluates whether an address is eligible for the geographic-profile benefit used by the Rav Kav (the public transit card / bus card in Israel) by combining:

- Natural-language address parsing using OpenAI
- ArcGIS geocoding to locate the address spatially
- CBS socio-economic and periphery rankings to determine eligibility for the Rav Kav geographic profile
- A transparent reasoning output with metadata for each check

Live site:
https://addresseligibilitysystem-ag5v9woh6cmauzjzzxf2vg.streamlit.app/

## Overview

This project was built to answer a practical question: given free-text address input in any language, can the system determine whether the address qualifies under Israel's geographic profiling rules for the Rav Kav (the public transit card / bus card in Israel)?

The workflow is:

1. Parse the raw address string into structured fields such as city, street, house number, and ambiguity flags.
2. Geocode the address with ArcGIS to get the precise locality code and statistical area.
3. Cross-reference the result against CBS (Israel Central Bureau of Statistics) socio-economic and periphery datasets.
4. Return an eligibility decision with explanatory reasons and raw metadata.

The app is designed to be usable from a browser and also has a command-line runner for scripted/local inspection.

## Features

- Free-text address input in any language
- AI-based parsing via OpenAI structured output
- Spatial validation using ArcGIS geocoding
- Eligibility logic built on CBS ranking data
- Support for both social-economic and periphery-based eligibility rules
- Transparent metadata display for debugging and auditing
- Responsive Streamlit UI with support for RTL Hebrew presentation
- CLI fallback for batch/local testing

## Tech Stack

- Python 3.10+
- Streamlit
- OpenAI API (GPT-4o-mini)
- ArcGIS REST services
- pandas
- openpyxl
- httpx
- pydantic
- python-dotenv

## Project Structure

```text
address_eligibility_system/
├── app.py                     # Streamlit web application
├── main.py                    # CLI pipeline runner
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (not committed in some setups)
├── agents/
│   ├── eligibility_agent.py   # CBS eligibility logic
│   ├── geocoder_agent.py      # ArcGIS geocoding and statistical area lookup
│   └── parser_agent.py        # LLM address parsing
├── data/                      # Cached Excel files downloaded from CBS
   ├── test_*.py                  # Validation checks for parsing, flow, geocoding, etc.
├── tests/                     # Project test scripts (if present in local setup)
├── generate_benchmark.py      # Benchmark/data generation utility
├── benchmark_results.xlsx     # Benchmark output example
└── README.md                  # Project documentation
```

## Eligibility Logic

The system evaluates two main paths:

- Social-economic eligibility: checks if the locality/statistical area falls in ranks 1-5
- Periphery eligibility: checks if the location is in a peripheral area with rank 1-5

Additional business rule:

- If a location qualifies as peripheral but has a high socio-economic rank (9 or 10), it may be excluded based on the defined logic.

The final result returns:

- `is_eligible`: boolean
- `reasons`: human-readable explanations
- `metadata`: locality code, statistical area, ranks, and source table

## Environment Setup

1. Create and activate a Python virtual environment:

```bash
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your OpenAI API key:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

Note: The parser agent depends on a valid OpenAI API key. The app also uses external network access to ArcGIS and CBS data sources.

## Running the App

Start the Streamlit app:

```bash
streamlit run app.py
```

Then open the local URL printed in the terminal, usually:

```text
http://localhost:8501
```

## Running the CLI Version

The project includes a command-line runner that executes the full pipeline step by step:

```bash
python main.py
```

Example input:

```text
הפלמ"ח 14 ירוחם
```

The CLI prints:

- parsed address components
- geocoded result
- locality code and statistical area
- final eligibility outcome and reasons

## Data Sources

The eligibility engine relies on public CBS Excel files, including:

- socio-economic indicators by locality / statistical area
- periphery ranking tables

These files are downloaded locally into the `data/` folder if they are not already available.

## Testing

The repository includes validation scripts for core flows, including:

- parser validation
- geocoder checks
- flow checks
- periphery lookup
- socio-economic lookup
- edge cases

You can run targeted checks using Python, for example:

```bash
python test_flow.py
python test_parser.py
python test_geocoder.py
```

## Usage Example

In the web app:

1. Enter a full address in any language supported by the parser.
2. Click "בדיקת זכאות".
3. Review the result:
   - eligible or not eligible
   - matched address
   - locality code and statistical area
   - explanation
   - technical metadata

## Notes

- The app supports free-text address input in any language, with Hebrew/RTL UI support included.
- Network access is required for OpenAI, ArcGIS, and CBS lookups.
- If parsing fails or the address is ambiguous, the app will return a validation error rather than guessing.
- The project is suitable for demonstration, internal tools, and further extension into a broader eligibility service.

## License

This project does not include a formal license file. If you are using it in a production environment, confirm the licensing terms for any upstream data sources and API usage before deployment.

## Contact / Extension Ideas

Potential enhancements include:

- more robust address normalization and validation
- fallback logic for missing geocoding candidates
- API layer for integration with external services
- additional benefit categories beyond geographic profiling
- caching and performance optimizations for production workloads
