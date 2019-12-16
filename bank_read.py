#next step is creating a plot widget/rewriting matplotlib syntax to pyqt5_graph

#STEP BY STEP
#1. turn buttons into dropdown menu, create groupbox to handle them
#2. create logic that will generate average monthly income/expenditures (SQL Query), display those values along with selected user id, put in groupbox
#---> you are here (don't forget to break up all balances function into two)
#3. add a plot widget, rewrite each plot code with PyQt5_graph syntax and that, when function is called, stores that plot into the class variable that is being displayed
#4. Calculate average monthly savings and project savings into the future, don't forget to include in database storage/queries, slider to adjust for time?
#4b. extra credit for doing a linear regression on monthly income/expenditures and using a changing monthly savings for projections
#5. clean up style, organize code

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from PyQt5.Qt import PYQT_VERSION_STR
print("PyQt version: ", PYQT_VERSION_STR)

import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates
import re
import operator
import sqlite3

from pandas.plotting import register_matplotlib_converters #date2num needs to be registered
register_matplotlib_converters()

class Example(QMainWindow):

    def __init__(self):
        super().__init__()
        self.key = '' #defined by user input, from prompt after selecting the .csv file, used as primary key for all relevant data in db
        self.buttonLocation = (135, 110) #initial button location, allows for easier movement of all buttons to accomodate UI changes
        self.threshold = '' #used to remove credits/debits LARGER than this amount
        self.df = '' #holds dataframe of all bank transactions
        self.month_hash = {} #each month is a "sub-hash", containing key/value pairs for total expenditures, income, and balance
        self.all_balances = [] #all_balances will be a list of tuples that store date and account balance for every transaction
        self.months = [] #months as strings (used primarily for x-axis labels for graphing)
        self.incomes = [] #float amounts for income by month
        self.expenditures = [] #same for expenditures
        self.balances = [] #same but for last balance of month
        self.savings = [] #same but for savings
        self.all_balances = [] #list of tuples containing integer representing date (date2num) and balance after every transaction
        self.x_axis_monthly = [] #list of integers in range(0, len(self.months))
        self.income_source_hash = {} #each key is a year with value of a "sub-hash" where each key is an income source and value is amount of income for that year
        self.yearly_gross = [] #list of gross income by year
        self.year_x_ticks = [] #labels for gross income by year (just year as string)
        self.balance_dates = []
        self.initUI()

    def initUI(self):
        #menu with file opener
        openFile = QAction(QIcon('open.png'), 'Open', self)
        openFile.setShortcut('Ctrl+O')
        openFile.setStatusTip('Open new File')
        openFile.triggered.connect(self.getFilePath)
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&Import')
        fileMenu.addAction(openFile)

        #combobox to select prior imported data:

        #get ids associated with previous collections of data (each id is unique - used to track data in database)
        connection = sqlite3.connect('bank_statement_data.db')
        cursor = connection.cursor()
        temp = cursor.execute('select * from users')
        already_imported = temp.fetchall()
        connection.close()

        #previous data dropdown

        self.userDropdown = QComboBox(self)
        self.userDropdown.addItem('--Select--')
        #if len(already_imported) > 0:
        for user in already_imported:
            self.userDropdown.addItems(user)
        #else:
            #self.userDropdown.addItems(('(none)',))
        self.userDropdown.activated[str].connect(self.onPreviousData)
        self.userDropdown.move(15, 65)
        self.userDropdownLabel = QLabel(self.userDropdown)
        self.userDropdownLabel.setText('Previously imported data:')
        #self.userDropdownLabel.move(15,35)
        #self.userDropdownLabel.resize(len(qlabel.text()) * 6, 15)
        self.userBox = QGroupBox()
        userLayout = QVBoxLayout()
        userLayout.addWidget(self.userDropdownLabel)
        userLayout.addWidget(self.userDropdown)
        self.userBox.setLayout(userLayout)

        #Plot options dropdown
        self.plotOptions = QComboBox()
        self.plotOptions.addItem('All Balances')
        self.plotOptions.addItem('Monthly Balances')
        self.plotOptions.addItem('Monthly Incomes vs. Expenditures')
        self.plotOptions.addItem('Monthly Savings')
        self.plotOptions.addItem('Monthly Income/Expenditures/Savings')
        self.plotOptions.addItem('Income Sources by Year')
        self.plotOptions.addItem('Yearly Gross')
        self.plotOptions.activated[str].connect(self.handlePlotOptions)
        self.plotOptionsLabel = QLabel(self.plotOptions)
        self.plotOptionsLabel.setText('Graph Options:')
        self.plotOptionsBox = QGroupBox()
        plotOptionsLayout = QVBoxLayout()
        plotOptionsLayout.addWidget(self.plotOptionsLabel)
        plotOptionsLayout.addWidget(self.plotOptions)
        self.plotOptionsBox.setLayout(plotOptionsLayout)

        #BUTTONS
        #showMonthlyBalances = QPushButton('Show Monthly Balances', self)
        #showMonthlyBalances.move(self.buttonLocation[0],self.buttonLocation[1])
        #showMonthlyBalances.resize(200,50)
        #showMonthlyBalances.clicked.connect(self.displayBalancePlots)

        #showIncomesExpenditures = QPushButton('Incomes vs. Expenditures by Month', self)
        #showIncomesExpenditures.move(self.buttonLocation[0],self.buttonLocation[1] + 55)
        #showIncomesExpenditures.resize(200,50)
        #showIncomesExpenditures.clicked.connect(self.compareIncomesExpenditures)

        #showSavings = QPushButton('Savings by Month', self)
        #showSavings.move(self.buttonLocation[0], self.buttonLocation[1] + 110)
        #showSavings.resize(200,50)
        #showSavings.clicked.connect(self.displaySavings)

        #showBarMulti = QPushButton('Income/Expenditures/Savings by Month', self)
        #showBarMulti.move(self.buttonLocation[0], self.buttonLocation[1] + 165)
        #showBarMulti.resize(200,50)
        #showBarMulti.clicked.connect(self.displayBarMultiVar)

        #showIncomeSources = QPushButton('Income Sorted by Source by Year', self)
        #showIncomeSources.move(self.buttonLocation[0], self.buttonLocation[1] + 220)
        #showIncomeSources.resize(200,50)
        #showIncomeSources.clicked.connect(self.displayIncomeSources)

        #showYearlyGross = QPushButton('Yearly Gross Income', self)
        #showYearlyGross.move(self.buttonLocation[0], self.buttonLocation[1] + 275)
        #showYearlyGross.resize(200,50)
        #showYearlyGross.clicked.connect(self.displayYearlyGross)

        #setting overall layout
        self.dropdownRow = QGroupBox()
        dropdownLayout = QHBoxLayout()
        dropdownLayout.addWidget(self.plotOptionsBox)
        dropdownLayout.addWidget(self.userBox)
        self.dropdownRow.setLayout(dropdownLayout)

        self.container = QGroupBox()
        containerLayout = QVBoxLayout()
        containerLayout.addWidget(self.dropdownRow)
        #containerLayout.addWidget(self.currentPlot) #add when you've refactored graph with pyqt5
        self.container.setLayout(containerLayout)

        #self.setGeometry(150, 150, len(qlabel.text()) * 5 + 50, self.buttonLocation[1] + 350)
        self.setWindowTitle('Graph Your Bank Statement')
        self.setCentralWidget(self.container)
        self.show()

    def getFilePath(self):
        filename = QFileDialog.getOpenFileName(self, 'Open File', '/home', "CSV files (*.csv)")

        if filename != ('', ''):
            #filename[0] is path for bank statement csv
            self.df = pd.read_csv(filename[0], header=3, sep=',', error_bad_lines=False)
            self.df['Date'] = pd.to_datetime(self.df.Date)
            self.df = self.df.fillna(0)
            self.df['year_month'] = self.df['Date'].dt.strftime("%Y" + "-" + "%m")
            self.df.sort_values(by=['Date'])
            #ask for id and threshold input
            self.getPrompts()

    def onPreviousData(self, text):
        #following code uses user-selected id to import all data necessary for graphing from database, then creates the necssary data for graphing from SQL queries
        if text == '--Select--':
            return

        connection = sqlite3.connect('bank_statement_data.db')
        cursor = connection.cursor()
        temp_key = cursor.execute('''select id from users where id = ?''', (text,))
        self.key = temp_key.fetchone()
        self.setWindowTitle('Graph Your Bank Statement - %s' % self.key)
        self.all_balances = cursor.execute('''SELECT date, balance FROM %s_all_balances ORDER BY date DESC''' % self.key).fetchall()
        self.months = cursor.execute('''SELECT month FROM %s_monthly ORDER BY date(month)''' % self.key).fetchall()
        self.x_axis_monthly = range(0, len(self.months))
        self.balances = cursor.execute('''SELECT end_balance from %s_monthly ORDER BY date(month)''' % self.key).fetchall()
        self.incomes = cursor.execute('''SELECT income from %s_monthly ORDER BY date(month)''' % self.key).fetchall()
        self.expenditures = cursor.execute('''SELECT expenditures from %s_monthly ORDER BY date(month)''' % self.key).fetchall()

        #extract value from returned tuple of sql queries
        for i in range(0, len(self.months)):
            #remove the artificially added day to each year-month (a contrivance necessary for sql sorting when in db)
            self.months[i] = self.months[i][0][:-3]
            self.incomes[i] = self.incomes[i][0]
            self.expenditures[i] = self.expenditures[i][0]

        self.savings = list(map(lambda income, expense: income - expense, self.incomes, self.expenditures))

        years = cursor.execute('''SELECT DISTINCT year FROM %s_income_sources ORDER BY date(year)''' % self.key).fetchall()
        income_sources = cursor.execute('''SELECT * from %s_income_sources''' % self.key).fetchall()

        #create income_source_hash
        for year in years:
            self.year_x_ticks.append(year[0])
            self.income_source_hash[year[0]] = {}
            for source in income_sources:
                if source[0] == year[0]:
                    self.income_source_hash[year[0]][source[1]] = source[2]

        self.yearly_gross = cursor.execute('''SELECT SUM(amount) FROM %s_income_sources GROUP BY year''' % self.key).fetchall()
        #extra value from each in tuple from SQL query
        for i in range(0, len(self.yearly_gross)):
            self.yearly_gross[i] = self.yearly_gross[i][0]

        connection.close()

    def getPrompts(self):
        #users set id which is used as a unique value to group/track data in db
        tempTextHold, okPressed = QInputDialog.getText(self, "Text Input Dialog", "Please provide a name with which you would like to track this statement's data:")
        if okPressed:
            self.key = tempTextHold
            self.setWindowTitle('Graph Your Bank Statement - %s' % self.key)
            connection = sqlite3.connect('bank_statement_data.db')
            cursor = connection.cursor()
            cursor.execute('''insert into users values(?)''', (self.key,))
            connection.commit()
            connection.close()
        #users sets threshold (all transactions with a value equal to or greater threshold will be removed from processing)
        self.threshold, okPressed = QInputDialog.getInt(self, "Get integer","Would you like to remove all transactions above a certain dollar threshold? (enter -1 for none):", -1, -1, 1000000, 1)
        if okPressed:
            if self.threshold != -1:
                rows_to_delete = []
                for item in self.df.iterrows():
                    if abs(item[1].get('Amount Debit')) >= self.threshold or abs(item[1].get('Amount Credit')) >= self.threshold:
                        #item[0] is the index of the row to be dropped
                        rows_to_delete.append(item[0])
                self.df = self.df.drop([*rows_to_delete], axis=0)
            self.crunchAndSend()

    def crunchAndSend(self):
        #crunches data, creates id-specific tables in db, and sends data to said tables

        source_matcher = re.compile("(?<=Deposit ).*$") #matches all text from "Deposit " to end of line (name of entity depositing)
        atm_catcher = re.compile('^at ATM #[0-9]*$') #different atms have different number ids, this allows us to lump them all together as one source

        for item in self.df.iterrows():
            #a list of tuples with transaction timestamp (float) and account balance
            self.all_balances.append((matplotlib.dates.date2num(item[1].get('Date')), item[1].get('Balance')))
            #the following code creates a hash where the year-month (string) is the key, and the value is a hash of incomes/expenditures/last balance
            date = item[1].get('year_month')
            if date not in self.month_hash:
                self.month_hash[date] = {'income': item[1].get('Amount Credit'), 'expenditures': (item[1].get('Amount Debit') * -1), 'balance': item[1].get('Balance')}
            else:
                self.month_hash[date]['income'] += item[1].get('Amount Credit')
                self.month_hash[date]['expenditures'] -= item[1].get('Amount Debit')

            #the following code sorts income by source by year
            if item[1].get('Amount Credit'):
                amount = item[1].get('Amount Credit')
                year = item[1].get('year_month')[:4]
                match_object = source_matcher.search(str(item[1].get('Description')))
                if match_object and atm_catcher.match(match_object.group(0)):
                    description = 'ATM DPST'
                elif match_object:
                    description = match_object.group(0)[:9] #9 limit character count
                else:
                    description = 'Cash DPST'
                if year in self.income_source_hash:
                    if description[:12] in self.income_source_hash[year]:
                        self.income_source_hash[year][description] += amount
                    else:
                        self.income_source_hash[year][description] = amount
                else:
                    self.income_source_hash[year] = {description: amount}

        #following code extracts data from month_hash into separate lists for each attribute (income, expenditures, etc.)
        #although it doesn't generate new data, this allows for more concise code later
        self.months = list(self.month_hash.keys())

        for month in self.months:
            self.incomes.append(self.month_hash[month]['income'])
            self.expenditures.append(self.month_hash[month]['expenditures'])
            self.balances.append(self.month_hash[month]['balance'])

        for year in self.income_source_hash:
            count = 0
            self.year_x_ticks.append(year)
            for name in self.income_source_hash[year]:
                count += self.income_source_hash[year][name]
            self.yearly_gross.append(count)
        self.yearly_gross.reverse()
        self.year_x_ticks.reverse()

        #reversing each list so graphs start with oldest month first
        self.months.reverse()
        self.incomes.reverse()
        self.expenditures.reverse()
        self.savings = list(map(lambda income, expense: income - expense, self.incomes, self.expenditures))
        self.balances.reverse()
        self.all_balances.reverse()
        self.x_axis_monthly = range(0, len(self.months)) #used for creating plots of proper length

        #create tables and send data to them:

        createMonthTable = ('''CREATE TABLE IF NOT EXISTS "%s_monthly" (
	"month"	TEXT UNIQUE,
	"income"	REAL,
	"expenditures"	REAL,
	"savings"	REAL,
	"end_balance"	REAL,
	PRIMARY KEY("month")
);''' % self.key)
        month_insertion = "INSERT INTO " + self.key + "_monthly VALUES(?,?,?,?,?)"

        createIncomeSourceTable = ('''CREATE TABLE "%s_income_sources" (
	"year"	TEXT,
	"source"	TEXT,
	"amount"	REAL
);''' % self.key)
        income_source_insertion = "INSERT INTO " + self.key + "_income_sources VALUES(?,?,?)"

        createGrossSalaryTable = ('''CREATE TABLE IF NOT EXISTS "%s_gross_salary" (
	"year"	TEXT,
	"gross_income"	REAL
);''' % self.key)
        gross_salary_insertion = "INSERT INTO " + self.key + "_gross_salary VALUES(?,?)"

        createAllBalancesTable = ('''CREATE TABLE IF NOT EXISTS "%s_all_balances" (
	"date"	REAL,
	"balance"	REAL
);''' % self.key)
        all_balances_insertion = "INSERT INTO " + self.key + "_all_balances VALUES(?,?)"

        connection = sqlite3.connect('bank_statement_data.db')
        cursor = connection.cursor()
        #create tables
        cursor.execute(createMonthTable)
        cursor.execute(createIncomeSourceTable)
        cursor.execute(createGrossSalaryTable)
        cursor.execute(createAllBalancesTable)

        #insert all month based data
        for month in self.month_hash:
            #NOTE: it's necessary to concat a '-01' to year_month for sorting capability, as sqlite can only sort date in YYYY-MM-DD format
            cursor.execute(month_insertion, (month + '-01', self.month_hash[month]['income'], self.month_hash[month]['expenditures'], self.month_hash[month]['income'] - self.month_hash[month]['expenditures'], self.month_hash[month]['balance']))

        #insert income source table data
        count = 1
        for year in self.income_source_hash:
            for source in self.income_source_hash[year]:
                cursor.execute(income_source_insertion, (year, source, self.income_source_hash[year][source]))
            #insert gross salary table data
            cursor.execute(gross_salary_insertion, (year, self.yearly_gross[count]))
            count -= 1

        #insert all balances table data
        for transaction in self.all_balances:
            cursor.execute(all_balances_insertion, (transaction[0], transaction[1]))

        connection.commit()
        connection.close()

    def handlePlotOptions(self, choice):
        if choice == 'All Balances':
            self.displayBalancePlots()
        elif choice == 'Monthly Balances':
            self.displayBalancePlots()
        elif choice == 'Monthly Incomes vs. Expenditures':
            self.compareIncomesExpenditures()
        elif choice == 'Monthly Savings':
            self.displaySavings()
        elif choice == 'Monthly Income/Expenditures/Savings':
            self.displayBarMultiVar()
        elif choice == 'Income Sources by Year':
            self.displayIncomeSources()
        elif choice == 'Yearly Gross':
            self.displayYearlyGross()

    def displayBalancePlots(self):
        plt.figure(figsize = (len(self.months)/1.2, 3))
        plt.grid(True)
        plt.ylabel('Amount in Dollars')
        plt.title("All Account Balance Changes Grouped by Month")
        plt.plot_date([i[0] for i in self.all_balances], [i[1] for i in self.all_balances], 'o');
        plt.show()

        plt.figure(figsize = (len(self.months)/1.2, 3))
        plt.plot(self.x_axis_monthly, self.balances, '--bo')
        plt.grid(True)
        plt.ylabel('Amount in Dollars')
        plt.xticks(self.x_axis_monthly, self.months)
        plt.title("Monthly Account Balances (using end of month total)")
        plt.show()

    def compareIncomesExpenditures(self):
        plt.figure(figsize=(len(self.months)/1.2,3))
        plt.plot(self.x_axis_monthly, self.incomes, '--go', label='Incomes')
        plt.plot(self.x_axis_monthly, self.expenditures, '--ro', label='Expenditures')
        plt.legend()
        plt.grid(True)
        plt.xticks(self.x_axis_monthly, self.months)
        plt.show()

    def displaySavings(self):
        plt.figure(figsize=(len(self.months)/1.2,3))
        plt.plot(self.x_axis_monthly, self.savings, '--bo', label='savings')
        plt.legend()
        plt.grid(True)
        plt.xticks(self.x_axis_monthly, self.months)
        plt.show()

    def displayBarMultiVar(self):
        x_left = list(map(lambda x: x -.25, self.x_axis_monthly))
        x_right = list(map(lambda x: x +.25, self.x_axis_monthly))

        plt.figure(figsize=(len(self.months)/1.2, 6))
        plt.bar(x_left, self.incomes, width=.25, align='center', alpha=.5, color='g')
        plt.bar(self.x_axis_monthly, self.expenditures, width=.25, align='center', alpha=.5, color='r')
        plt.bar(x_right, self.savings, width=.25, align='center', alpha=.5, color='b')
        plt.grid(True, axis='y')
        plt.xticks(self.x_axis_monthly, self.months)
        plt.ylabel('Money in Dollars')
        plt.title('Comparison of Monthly Income, Expenditures, and Savings')
        variables = ['Income', 'Expenditures', 'Savings']
        plt.legend(variables, loc=2)
        plt.show()

    def displayIncomeSources(self):
        for year in self.income_source_hash:
            sorted_income_tuples = sorted(self.income_source_hash[year].items(), key=operator.itemgetter(1), reverse=True)
            plt.figure(figsize = (len(self.income_source_hash[year])/.7, 5))
            plt.bar([item[0] for item in sorted_income_tuples], [item[1] for item in sorted_income_tuples], color='g')
            plt.grid(True, axis='y')
            plt.ylabel('Amount in Dollars')
            plt.title('Sources of Income ' + str(year))
            plt.show();

    def displayYearlyGross(self):
        plt.figure(figsize=(len(self.yearly_gross) + 4, 5))
        plt.plot(range(0, len(self.yearly_gross)), self.yearly_gross, '--go', label='Yearly Salary')
        plt.grid(True)
        plt.xticks(range(0, len(self.yearly_gross)), self.year_x_ticks)
        plt.title('Total Year Gross Income')
        plt.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())
