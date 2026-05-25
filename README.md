# ScholarScope: OpenAlex Russell Group vs UEA Publication Comparator
Author: Taimur Shahzad Gill

This project is an effort to analyse OpenAlex journal article metadata for the 24 Russell Group universities and the University of East Anglia (UEA). UEA is not a Russell Group member. It is included as an external benchmark so its research output can be read against a known peer group of research-intensive universities. The analysis covers journal articles published from 2015 to 2024.

## Libraries required:

The project was developed with Python 3.11. These libraries are needed:

  pandas        data loading and analysis
  numpy         numerical helpers used in the notebook
  plotly        all charts, in the notebook and the dashboard
  streamlit     the dashboard only
  jupyter       to open and run the notebook

Install everything in one go:

```python
  pip install pandas numpy plotly streamlit jupyter
```

## How to run the notebook?

  1. Open a terminal in the project folder.
  2. Start Jupyter:

         jupyter notebook

  3. Open 100532874_Task2_jupyter.ipynb.
  4. Run every cell from top to bottom. Use the menu option Kernel > Restart & Run All so the outputs are fresh.

The notebook expects the data file in the same folder. If you move the data, update the file path near the top of the notebook.

## How to run the dashboard?

The dashboard reads the pre-aggregated CSV files in the data/ folder, which keeps it fast.

  1. Open a terminal in the project folder.
  2. Run:

         python -m streamlit run app.py

  3. The dashboard opens in your browser, usually at http://localhost:8501

The data/ folder must sit next to app.py and contain these files:
  - yearly_summary.csv
  - field_year_summary.csv
  - field_counts.csv
  - institution_summary.csv
  - institution_year_summary.csv
  - uea_metric_comparison.csv
  - uea_field_specialisation.csv
  - uea_rg_collaboration.csv
  - record_table_top100k.csv

If record_table_top100k.csv is missing, the dashboard still runs. Only the Records tab shows a short notice instead of the table.

## How to use the dashboard?

  Sidebar filters
  - Institution group: Both, Russell Group only, or UEA only.
  - Publication years.
  - Research fields.
  - Minimum records per institution.

  Four tabs:
  - **Overview:** headline metrics and open access over time.
  - **UEA benchmark:** performance index, field concentration, citation trend, and the co-publication network.
  - **Institution explorer:** a comparator scatter where you can change the y-axis metric and spotlight any institutions.
  - **Records:** a searchable table with a CSV export button.

---

**Notes:**
  - The FWCI ratio used in this project is an FWCI-style figure. It uses the same field-and-year normalisation idea as the commercial Field-Weighted Citation Impact, but it is computed from this extract, so it will not match a Scopus or InCites value exactly.
  - Data source: OpenAlex (https://openalex.org), used under CC0.
  - 2025 is excluded because that publication year was still incomplete in OpenAlex when the data was extracted.
