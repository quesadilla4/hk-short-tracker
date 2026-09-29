Summary: A weekly tracker of short positioning in Hong Kong stocks. It pulls the SFC's aggregated short position releases into a database, works out which names are seeing the biggest changes, and emails you a one-page note every Friday.



**Scripts Folder:**



1. scripts/load\_sfc\_short.py is the main loader:



Fetch: downloads any weekly SFC CSVs you don't already have into data/raw/. Files already there are skipped, so weekly runs only fetch one new file.

Parse: reads every raw CSV, checks its header, and cleans the values.

Combine: writes all weeks into one file, data/sfc\_short\_positions.csv, sorted by date then stock code.





2. scripts/fetch\_sfc\_short.py downloads the most recent weekly PDF of aggregated short positions from the SFC into data/. It finds the newest link on the SFC listing page, or falls back to guessing the URL for recent Fridays.





Format Info:



Raw files → combined file (sfc\_short\_positions.csv)



Each raw file is one week, named Short\_Position\_Reporting\_Aggregated\_Data\_YYYYMMDD.csv, with about 100 to 1,200 rows. The combined file stacks all 733 weeks (514,599 rows), with each column converted like this:



|Raw SFC Column|Example Raw Value|Combined Column|Example Output|Conversion|
|-|-|-|-|-|
|Date|18/09/2026|date|2026-09-18|DD/MM/YYYY -> YYYY-MM-DD, so dates sort correctly|
|Stock Code|1|stock\_code|00001|Padded to 5 digits, kept as text|
|Stock Name|CKH HOLDINGS|stock\_name|CKH HOLDINGS|Unchanged|
|Aggregated Reportable Short Positions (Shares)|49126109|short\_shares|49126109|Whole number, with any commas removed|
|Aggregated Reportable Short Positions (HK$)|3335662801|short\_value\_hkd|3335662801|Whole number, with commas and $ removed|



Two values in the SFC files needed special handling:



n.a. in the HK$ column (9 rows) is left blank, not 0.

Scientific notation such as 1.18734E+11 (4 PING AN rows) is converted to a whole number. The SFC file only keeps 6 significant figures there, so those values are approximate.

