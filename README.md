# bank_statement_processing

Coded in Python 3.7
Dependent on Pandas 0.25 and matplotlib 1.31

This program was designed to work with Mazuma Credit Union bank statements, exported as .csv files.

This repository includes both .py and .ipynb (Juypter notebook) files. The program is more accessible with Juypter for the following reasons:
  - one section of the code removes outliers from processing, requires user input to determine that threshhold (default is set to one million dollars). The .py file does not include the code for taking user input, needs to be modified directly to take that. In Juypter, is easier for the user to see
  - since the code is dependent on Pandas and matplotlib, running it from Juypter notebook means not having to have those two modules installed locally. Without that, the .py file will not run
  - the user can control the "flow" of graphs in Juypter, the .py file renders each one individually, only opening the following one after closing the current graph. Not ideal, perhaps possible to make contigent on user input in the future, but likely never as clean as the Juypter experience
  
Still looking for other Mazuma bank statements to test this on, have only processed my own.
