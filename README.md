# bank_statement_processing

Coded in Python 3.7
Pandas 0.25 and PyQt5 5.13.2 dependencies

This program was designed to work with the formatting Mazuma Credit Union bank statements, exported as .csv files. It plots bank account balance changes, monthly income, expenditures, and savings, as well as plotted sorted income by source by year as a bar graph.

The program has a basic GUI that will, when taking in new data, prompt the user for both an id with which to track bank statement data (needs to be alphanumeric). The id serves as a unique key with which users are tracked in the database. This program uses sqlite3 to send data to the bank_statement_data.db file and is capable of loading data from previously imported and processed bank statements.
