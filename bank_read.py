from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import Qt
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
pg.setConfigOption('background', 'w') #make graphs white and black
pg.setConfigOption('foreground', 'k')
from PyQt5.Qt import PYQT_VERSION_STR
print("PyQt version: ", PYQT_VERSION_STR)

import sys
import pandas as pd
import re
import operator
import sqlite3
import datetime
from statistics import mean

class App(QMainWindow):

    def __init__(self):
        super().__init__()
        #list of class variables to be used
        self.key = '' #defined by user input, from prompt after selecting the .csv file, used as primary key for all relevant data in db
        self.choice = 'All Balances' #used to reload current graph on threshold changes (changed by handlePlotOptions) and initialize app after data import with a display of all balances graph
        self.threshold = '' #used to remove credits/debits LARGER than this amount
        self.df = '' #holds dataframe of all bank transactions, user can mutate
        self.originalDf = '' #holds a permanent, immutable dataframe of all bank transactions
        self.month_hash = {} #each month is a "sub-hash", containing key/value pairs for total expenditures, income, and balance
        self.all_balances = [] #list of tuples containing integer representing date (unix epoch sec) and balance after every transaction
        self.months = [] #months as strings (used primarily for x-axis labels for graphing)
        self.incomes = [] #float amounts for income by month
        self.expenditures = [] #same for expenditures
        self.balances = [] #same but for last balance of month
        self.savings = [] #same but for savings
        self.avgSavings = 0 #a single number indicating average monthly savings over all months
        self.avgIncome = 0 #same but with average monthly income
        self.avgExpenditure = 0 #same but with expenditure
        self.years_projected = 5 #used for the projected savings view, altered by self.changeYears
        self.x_axis_monthly = [] #list of integers in range(0, len(self.months))
        self.income_source_hash = {} #each key is a year with value of a "sub-hash" where each key is an income source and value is amount of income for that year
        self.year_plot_hash = {} #each key is a year where its value is the relevant plotwidget, displaying a bar graph of sorted sources of income
        self.yearly_gross = [] #list of gross income by year
        self.balance_dates = [] #integer representations of date from every transaction (unix epoch)
        self.month_x_ticks = [] #tuple of integer and respective month-year, used for labeling monthly x ticks
        self.year_x_ticks = [] #tuples of integer and respective gross income by year (just year as string)
        self.greenPen = pg.mkPen(color=(50, 130, 20), width=2) #used when graph is actually plotted
        self.redPen = pg.mkPen(color=(243, 59, 59), width=2)
        self.bluePen = pg.mkPen(color=(57, 64, 255), width=2)
        self.layout_is_normal = False #used to check and see when normal layout needs to be restored
        self.has_savings_layout = False #used to check if savings layout is needed
        self.sent_to_db = False #used to indicate whether or not data has been sent to database, if not, then self.send() is called by self.crunch()
        self.initUI()

    def initUI(self):
        #menu with file opener
        openFile = QAction(QIcon('open.png'), 'Open', self)
        openFile.setShortcut('Ctrl+O')
        openFile.setStatusTip('Open new File')
        openFile.triggered.connect(self.getFilePath)
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&Import New Statement')
        fileMenu.addAction(openFile)

        #get ids associated with previous collections of data (each id is unique - used to track data in database)
        connection = sqlite3.connect('bank_statement_data.db')
        cursor = connection.cursor()
        temp = cursor.execute('select * from users')
        already_imported = temp.fetchall()
        connection.close()

        #previous data import dropdown
        self.userDropdown = QComboBox(self)
        self.userDropdown.addItem('--Select--')
        for user in already_imported:
            self.userDropdown.addItems(user)
        self.userDropdown.activated[str].connect(self.onPreviousData)
        self.userDropdown.move(15, 65)
        self.userDropdownLabel = QLabel(self.userDropdown)
        self.userDropdownLabel.setText('Previously imported data:')
        self.userBox = QGroupBox()
        userLayout = QVBoxLayout()
        userLayout.addWidget(self.userDropdownLabel)
        userLayout.addWidget(self.userDropdown)
        self.userBox.setLayout(userLayout)

        #Plot options dropdown (hidden before data import, so user can't try to make plots with no data present)
        self.plotOptions = QComboBox()
        self.plotOptions.addItem('All Balances')
        self.plotOptions.addItem('Monthly Balances')
        self.plotOptions.addItem('Monthly Incomes vs. Expenditures')
        self.plotOptions.addItem('Monthly Savings')
        self.plotOptions.addItem('Monthly Income/Expenditures/Savings')
        self.plotOptions.addItem('Income Sources by Year')
        self.plotOptions.addItem('Yearly Gross')
        self.plotOptions.addItem('Projected Savings')
        self.plotOptions.activated[str].connect(self.handlePlotOptions)
        self.plotOptionsLabel = QLabel(self.plotOptions)
        self.plotOptionsLabel.setText('Graph Options:')
        self.plotOptionsBox = QGroupBox()
        plotOptionsLayout = QVBoxLayout()
        plotOptionsLayout.addWidget(self.plotOptionsLabel)
        plotOptionsLayout.addWidget(self.plotOptions)
        self.plotOptionsBox.setLayout(plotOptionsLayout)
        self.plotOptionsBox.hide()

        #income threshold slider (hidden before data import)
        self.thresholdSlider = QSlider(Qt.Horizontal)
        self.thresholdSlider.setSingleStep(500)
        self.thresholdSlider.setMinimum(0)
        self.thresholdSlider.setMaximum(20000)
        self.thresholdSlider.valueChanged[int].connect(self.thresholdTracker)
        self.thresholdSlider.sliderReleased.connect(self.thresholdDropper)
        self.thresholdLabel = QLabel(self.thresholdSlider)
        self.thresholdLabel.setText('Remove any transactions above this amount (set to $0 for none)')
        self.thresholdLabel.setStyleSheet('font-size: 12px;')
        self.thresholdSlider.hide()

        #currentPlot widget, each plotOptions choice rewrites self.currentPlot with relevant data
        self.currentPlot = pg.PlotWidget()
        self.currentPlot.showGrid(x=True, y=True)
        self.xAxis = self.currentPlot.getAxis('bottom')
        self.yAxis = self.currentPlot.getAxis('top')
        self.currentPlot.setLabel("left", "Amount ($)")

        #setting overall layout
        self.setNormalLayout()
        self.setWindowTitle('Graph Your Bank Statement')
        self.showMaximized()

    def setNormalLayout(self):
        if not self.layout_is_normal:
            self.dropdownRow = QGroupBox()
            dropdownLayout = QHBoxLayout()
            dropdownLayout.addWidget(self.userBox)
            dropdownLayout.addWidget(self.plotOptionsBox)
            self.dropdownRow.setLayout(dropdownLayout)
            self.sliderRow = QGroupBox()
            sliderLayout = QVBoxLayout()
            sliderLayout.addWidget(self.thresholdLabel)
            sliderLayout.addWidget(self.thresholdSlider)
            self.sliderRow.setLayout(sliderLayout)
            self.container = QGroupBox()
            containerLayout = QVBoxLayout()
            containerLayout.addWidget(self.dropdownRow)
            containerLayout.addWidget(self.sliderRow)
            containerLayout.addWidget(self.currentPlot)
            self.container.setLayout(containerLayout)
            self.setCentralWidget(self.container)
            self.layout_is_normal = True
            self.has_savings_layout = False

    def onPreviousData(self, text):
        #following code uses user-selected id to import all data necessary for graphing from database, then creates the necssary data for graphing from SQL queries
        #still need to add import of entire bank statement history to store as originalDf
        self.plotOptionsBox.show()
        self.thresholdSlider.show()
        self.sent_to_db = True

        if text == '--Select--':
            return

        connection = sqlite3.connect('bank_statement_data.db')
        cursor = connection.cursor()
        temp_key = cursor.execute('''select id from users where id = ?''', (text,))
        #create necessary variables for graphing
        self.key = temp_key.fetchone()
        self.setWindowTitle('Graph Your Bank Statement - %s' % self.key)
        entire_statement = pd.read_sql_query('''select * from %s''' % self.key, connection)
        self.originalDf = pd.DataFrame(entire_statement)
        self.originalDf['Date'] = pd.to_datetime(self.originalDf.Date)
        self.all_balances = cursor.execute('''SELECT date, balance FROM %s_all_balances ORDER BY date DESC''' % self.key).fetchall()
        self.months = cursor.execute('''SELECT month FROM %s_monthly ORDER BY date(month)''' % self.key).fetchall()
        self.x_axis_monthly = range(0, len(self.months))
        self.balances = cursor.execute('''SELECT end_balance from %s_monthly ORDER BY date(month)''' % self.key).fetchall()
        self.incomes = cursor.execute('''SELECT income from %s_monthly ORDER BY date(month)''' % self.key).fetchall()
        self.expenditures = cursor.execute('''SELECT expenditures from %s_monthly ORDER BY date(month)''' % self.key).fetchall()

        #set thresholdSlider maximum now that we have originalDf:
        self.thresholdSliderMax()

        #extract value from returned tuple of sql queries (just need list of values, not list of tuples)
        for i in range(0, len(self.months)):
            #remove the artificially added day to each year-month (a contrivance necessary for sql sorting when in db)
            self.months[i] = self.months[i][0][:-3]
            self.incomes[i] = self.incomes[i][0]
            self.expenditures[i] = self.expenditures[i][0]
            self.balances[i] = self.balances[i][0]

        self.savings = list(map(lambda income, expense: income - expense, self.incomes, self.expenditures))
        self.avgSavings = int(mean(self.savings) * 100)/100
        self.avgIncome = int(mean(self.incomes) * 100)/100
        self.avgExpenditure = int(mean(self.expenditures) * 100)/100
        self.month_x_ticks = [(self.x_axis_monthly[i], self.months[i]) for i in range(0, len(self.months))] #formatted to create monthly x ticks on graphs

        years = cursor.execute('''SELECT DISTINCT year FROM %s_income_sources ORDER BY date(year)''' % self.key).fetchall()
        income_sources = cursor.execute('''SELECT * from %s_income_sources''' % self.key).fetchall()

        #create self.income_source_hash
        for year in years:
            self.year_x_ticks.append((len(self.year_x_ticks), year[0]))
            self.income_source_hash[year[0]] = {}
            for source in income_sources:
                if source[0] == year[0]:
                    self.income_source_hash[year[0]][source[1]] = source[2]

        self.yearly_gross = cursor.execute('''SELECT SUM(amount) FROM %s_income_sources GROUP BY year''' % self.key).fetchall()
        #extra value from each in tuple from SQL query
        for i in range(0, len(self.yearly_gross)):
            self.yearly_gross[i] = self.yearly_gross[i][0]
        connection.close()
        #call first graph
        self.handlePlotOptions(self.choice)

    def getFilePath(self):
        #runs when user selects "Import New Statement" from menubar
        filename = QFileDialog.getOpenFileName(self, 'Open File', '/home', "CSV files (*.csv)")
        if filename != ('', ''):
            #filename[0] is path for bank statement csv
            self.originalDf = pd.read_csv(filename[0], header=3, sep=',', error_bad_lines=False)
            self.originalDf['Date'] = pd.to_datetime(self.originalDf.Date)
            self.originalDf = self.originalDf.fillna(0)
            self.originalDf['year_month'] = self.originalDf['Date'].dt.strftime("%Y" + "-" + "%m")
            self.originalDf.sort_values(by=['Date'])
            self.df = self.originalDf
            #ask for id and threshold input
            self.getPrompts()

    def getPrompts(self):
        #user chooses an id, which is used as a unique value to store and track data in db
        tempTextHold, okPressed = QInputDialog.getText(self, "Text Input Dialog", "Please provide a name with which you would like to track this statement's data:")
        if okPressed:
            self.key = tempTextHold
            self.setWindowTitle('Graph Your Bank Statement - %s' % self.key)
            connection = sqlite3.connect('bank_statement_data.db')
            cursor = connection.cursor()
            cursor.execute('''insert into users values(?)''', (self.key,))
            connection.commit()
            connection.close()
            self.plotOptionsBox.show()
            self.thresholdSlider.show()
            self.thresholdSliderMax()
            self.crunch()

    def crunch(self):
        #crunches data, generates variables for graphing
        source_matcher = re.compile("(?<=Deposit ).*$") #matches all text from "Deposit " to end of line (name of entity depositing)
        atm_catcher = re.compile('^at ATM #[0-9]*$') #different atms have different number ids, this allows us to lump them all together as one source

        for item in self.df.iterrows():
            #generate a list of tuples with transaction timestamp (unix epoch sec) and remaining account balance for every transaction
            self.all_balances.append((pd.to_timedelta(item[1].get('Date') - pd.to_datetime('1/1/1970')).total_seconds(), item[1].get('Balance')))

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
        #although it doesn't generate new data, this allows for more concise and legible code later
        self.months = list(self.month_hash.keys())

        for month in self.months:
            self.incomes.append(self.month_hash[month]['income'])
            self.expenditures.append(self.month_hash[month]['expenditures'])
            self.balances.append(self.month_hash[month]['balance'])

        for year in self.income_source_hash:
            count = 0
            for name in self.income_source_hash[year]:
                count += self.income_source_hash[year][name]
            self.yearly_gross.append(count)
        self.yearly_gross.reverse()

        self.year_x_ticks = []
        sorted_years = sorted(list(self.income_source_hash.keys()))
        for index, year in enumerate(sorted_years):
            self.year_x_ticks.append((index, year))

        #reversing each list so graphs start with oldest month first
        self.months.reverse()
        self.incomes.reverse()
        self.expenditures.reverse()
        self.savings = list(map(lambda income, expense: income - expense, self.incomes, self.expenditures))
        self.avgSavings = int(mean(self.savings) * 100)/100 #note: these three avgs are not entered into database, they are simply crunched on query if re-importing older data
        self.avgIncome = int(mean(self.incomes) * 100)/100
        self.avgExpenditure = int(mean(self.expenditures) * 100)/100
        self.balances.reverse()
        self.all_balances.reverse()
        self.x_axis_monthly = range(0, len(self.months)) #used for creating plots of proper length
        self.month_x_ticks = [(self.x_axis_monthly[i], self.months[i]) for i in range(0, len(self.months))] #formatting for monthly x ticks on graph

        if not self.sent_to_db: #condition that matches on intial import
            self.send()
            self.sent_to_db = True
        self.handlePlotOptions(self.choice)

    def send(self):
        #this function creates id-specific tables in sqlite, and sends data to respective tables

        #create tables:

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

        #send entire dataframe:
        self.originalDf.to_sql(self.key, connection)

        #create tables in db
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
            cursor.execute(gross_salary_insertion, (year, self.yearly_gross[len(self.yearly_gross) - count]))
            #if len(self.yearly_gross) == 1:
                #cursor.execute(gross_salary_insertion, (year, self.yearly_gross[0]))
            #else:
                #cursor.execute(gross_salary_insertion, (year, self.yearly_gross[count]))
            count += 1

        #insert all balances table data
        for transaction in self.all_balances:
            cursor.execute(all_balances_insertion, (transaction[0], transaction[1]))

        connection.commit()
        connection.close()

    def thresholdSliderMax(self):
        max_credit = self.originalDf['Amount Credit'].max()
        max_debit = self.originalDf['Amount Debit'].max()
        max_transaction = max(max_credit, max_debit)
        self.thresholdSlider.setMaximum(max_transaction + 1)
        #self.thresholdSlider.setSingleStep((max_transaction + 1)//50)

    def thresholdTracker(self, threshold):
        self.threshold = threshold
        #redo slider label
        self.thresholdLabel.setText('Removed transactions above $%s (set to 0 to keep all)' % self.threshold)

    def thresholdDropper(self):
        #this function drops any rows with transactions above threshold, set by user
        #set has_savings_layout to False so that variables update when df changes:
        self.has_savings_layout = False
        #reset all variables:
        self.df = self.originalDf
        self.month_hash = {} #each month is a "sub-hash", containing key/value pairs for total expenditures, income, and balance
        self.all_balances = [] #list of tuples containing integer representing date (unix epoch sec) and balance after every transaction
        self.months = [] #months as strings (used primarily for x-axis labels for graphing)
        self.incomes = [] #float amounts for income by month
        self.expenditures = [] #same for expenditures
        self.balances = [] #same but for last balance of month
        self.savings = [] #same but for savings
        self.years_projected = 5 #used for the projected savings view, altered by self.changeYears
        self.x_axis_monthly = [] #list of integers in range(0, len(self.months))
        self.income_source_hash = {} #each key is a year with value of a "sub-hash" where each key is an income source and value is amount of income for that year
        self.year_plot_hash = {} #each key is a year where its value is the relevant plotwidget, displaying a bar graph of sorted sources of income
        self.yearly_gross = [] #list of gross income by year
        self.balance_dates = [] #integer representations of date from every transaction (unix epoch)
        self.month_x_ticks = [] #tuple of integer and respective month-year, used for labeling monthly x ticks
        self.year_x_ticks = [] #tuples of integer and respective gross income by year (just year as string)

        #drop rows with transactions above user set threshold, if threshold is not 0
        if self.threshold != 0:
            rows_to_delete = []
            for item in self.df.iterrows():
                if abs(item[1].get('Amount Debit')) >= self.threshold or abs(item[1].get('Amount Credit')) >= self.threshold:
                    #item[0] is the index of the row to be dropped
                    rows_to_delete.append(item[0])
            self.df = self.df.drop(rows_to_delete, axis=0)
        self.crunch()


    def handlePlotOptions(self, choice):
        #make choice a class variable so that it can be passed to thresholdDropper and graph can be reloaded on treshold changes
        self.choice = choice
        if choice == 'All Balances':
            self.displayAllBalances()
        elif choice == 'Monthly Balances':
            self.displayMonthlyBalances()
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
        elif choice == 'Projected Savings':
            self.displaySavingsProjections()

    def clearPlot(self):
        #called every time a new graph is chosen
        self.currentPlot.clear()
        try: #removes the legend, which .clear() will not do
            self.legend.scene().removeItem(self.legend)
        except Exception as e:
            return ''

    def list_breakup(self, list_):
        #this code breaks up list_ with an interval that won't allow more than 12 x ticks, then formats the tick labels at that interval (month-year)
        #note that this code assumes a list of unix epoch seconds and will not necessarily set ticks at n amount of months, but instead n amount of changes to balance
        formatted_x_ticks = [(list_[0], datetime.datetime.utcfromtimestamp(list_[0]).strftime('%m-%Y'))]
        length = len(list_)
        interval = length//8
        for index in range(interval, length, interval):
            formatted_x_ticks.append((list_[index], datetime.datetime.utcfromtimestamp(list_[index]).strftime('%m-%Y')))
        return formatted_x_ticks

    def displayAllBalances(self):
        all_balances_x_ticks = self.list_breakup([i[0] for i in self.all_balances])
        self.setNormalLayout()
        self.clearPlot()
        self.currentPlot.plot([i[0] for i in self.all_balances], [i[1] for i in self.all_balances], pen=self.bluePen, symbol='o', symbolSize='1', symbolBrush=(57, 64, 255))
        self.currentPlot.setTitle('Balance Remaining After Every Transaction')
        self.xAxis.setTicks([all_balances_x_ticks])

    def displayMonthlyBalances(self):
        self.setNormalLayout()
        self.clearPlot()
        self.currentPlot.plot(self.x_axis_monthly, self.balances, pen=self.bluePen, symbol='o', symbolBrush=(57, 64, 255))
        self.currentPlot.setTitle('All Account Balance Changes Grouped by Month')
        self.xAxis.setTicks([self.month_x_ticks])

    def compareIncomesExpenditures(self):
        self.setNormalLayout()
        self.clearPlot()
        self.legend = self.currentPlot.addLegend()
        self.currentPlot.plot(self.x_axis_monthly, self.incomes, name='Income', pen=self.greenPen, symbol='o', symbolBrush=(50, 130, 20))
        self.currentPlot.plot(self.x_axis_monthly, self.expenditures, name='Expenditures', pen=self.redPen, symbol='o', symbolBrush=(243, 59, 59))
        self.xAxis.setTicks([self.month_x_ticks])
        self.currentPlot.setTitle('Monthly Income vs. Expenditures')

    def displaySavings(self):
        self.setNormalLayout()
        self.clearPlot()
        self.currentPlot.plot(self.x_axis_monthly, self.savings, pen=self.bluePen, symbol='o', symbolBrush=(57, 64, 255))
        self.currentPlot.setTitle('Monthly Savings')
        self.xAxis.setTicks([self.month_x_ticks])

    def displayBarMultiVar(self):
        self.setNormalLayout()
        self.clearPlot()

        x_left = list(map(lambda x: x -.25, self.x_axis_monthly))
        x_right = list(map(lambda x: x +.25, self.x_axis_monthly))

        self.legend = self.currentPlot.addLegend()
        incomes_bar = pg.BarGraphItem(x=x_left, height=self.incomes, width=0.25, brush='g', name='Incomes')
        expenditures_bar = pg.BarGraphItem(x=self.x_axis_monthly, height=self.expenditures, width=0.25, brush='r', name='Expenditures')
        savings_bar = pg.BarGraphItem(x=x_right, height=self.savings, width=0.25, brush='b', name='Savings')
        self.currentPlot.addItem(incomes_bar)
        self.currentPlot.addItem(expenditures_bar)
        self.currentPlot.addItem(savings_bar)
        #color of BarGraphItem currently not displaying with legend. Note that addItem is also NOT using the name keyword defined within incomes_bar, etc.
        self.legend.addItem(incomes_bar, name="Green: Incomes")
        self.legend.addItem(expenditures_bar, name="Red: Expenditures")
        self.legend.addItem(savings_bar, name="Blue: Savings")
        self.currentPlot.setTitle("Comparison of Monthly Income, Expenditures, and Savings")
        self.xAxis.setTicks([self.month_x_ticks])

    def addYearDropdown(self):
        #called when self.displayIncomeSources, as there is a distinct graph for each year in statement history
        self.yearOptions = QComboBox()
        for year in self.income_source_hash:
            self.yearOptions.addItem(str(year))
        self.yearOptions.activated[str].connect(self.handleDisplayYear)
        self.yearOptionsLabel = QLabel(self.yearOptions)
        self.yearOptionsLabel.setText('Displayed year:')
        self.yearOptionsBox = QGroupBox()
        yearOptionsLayout = QVBoxLayout()
        yearOptionsLayout.addWidget(self.yearOptionsLabel)
        yearOptionsLayout.addWidget(self.yearOptions)
        self.yearOptionsBox.setLayout(yearOptionsLayout)

        #alter layout to include year dropdown
        self.newContainer = QGroupBox()
        newContainerLayout = QVBoxLayout()
        newContainerLayout.addWidget(self.dropdownRow)
        newContainerLayout.addWidget(self.sliderRow)
        newContainerLayout.addWidget(self.yearOptionsBox)
        newContainerLayout.addWidget(self.currentPlot)
        self.newContainer.setLayout(newContainerLayout)
        self.setCentralWidget(self.newContainer)
        self.showMaximized()

        self.layout_is_normal = False
        self.has_savings_layout = False

    def handleDisplayYear(self, chosen_year):
        self.clearPlot()
        self.currentPlot.addItem(self.year_plot_hash[chosen_year][0])
        self.xAxis.setTicks([self.year_plot_hash[chosen_year][1]])
        self.currentPlot.setTitle('Unique Income Sources from %s' % chosen_year)

    def displayIncomeSources(self):
        #this creates a hash of plots where the keys are each year and their values are the relevant plot. User chooses which year to display
        self.addYearDropdown()

        #init_year used to create an initial graph before user choice, intuitive behavior from UI (as user already chose income source category before choosing a year)
        init_year = ''

        for year in self.income_source_hash:
            if not init_year:
                init_year = year
            sorted_income_tuples = sorted(self.income_source_hash[year].items(), key=operator.itemgetter(1), reverse=True)
            #each key in year_plot_hash is a year as string, value is a tuple where first entry is a BarGraphItem, 2nd entry is a sub-tuple that contains formatted x-tick labels: [(integer1, description1), (integer2, description2)...]
            self.year_plot_hash[str(year)] = (pg.BarGraphItem(x=[i for i in range(0, len(sorted_income_tuples))], height=[item[1] for item in sorted_income_tuples], width=.25, brush='g'), [(i, sorted_income_tuples[i][0]) for i in range(0, len(sorted_income_tuples))])

        #initialize graph with first year in statement
        self.handleDisplayYear(init_year)

    def displayYearlyGross(self):
        self.setNormalLayout()
        self.clearPlot()
        self.currentPlot.plot(range(0, len(self.yearly_gross)), self.yearly_gross, pen=self.greenPen, symbol='o', symbolBrush=(50, 130, 20))
        self.xAxis.setTicks([self.year_x_ticks])
        self.currentPlot.setTitle('Yearly Gross Income')

    def handleSavingsLayout(self):
        #builds new layout for savings projection view
        styleSheet = ("border: 1px solid grey; font-size: 13px; font-weight: 450;")

        average_display = QGroupBox()
        average_layout = QVBoxLayout()
        avg_income_display = QLabel(self)
        avg_income_display.setText('Average Monthly Income: %s' % self.avgIncome)
        avg_income_display.setStyleSheet(styleSheet)
        avg_expenditure_display = QLabel(self)
        avg_expenditure_display.setText('Average Monthly Expenditure: %s' % self.avgExpenditure)
        avg_expenditure_display.setStyleSheet(styleSheet)
        avg_savings_display = QLabel(self)
        avg_savings_display.setText('Average Monthly Savings: %s' % self.avgSavings)
        avg_savings_display.setStyleSheet(styleSheet)
        average_layout.addWidget(avg_income_display)
        average_layout.addWidget(avg_expenditure_display)
        average_layout.addWidget(avg_savings_display)
        average_display.setLayout(average_layout)
        years_slider = QSlider(Qt.Horizontal, self)
        years_slider.setMaximum(75)
        years_slider.setMinimum(5)
        years_slider.setSingleStep(1)
        years_slider.valueChanged[int].connect(self.changeYears)
        self.years_label = QLabel(years_slider)
        self.years_label.setText('Years Projected: 5')
        self.years_label.setStyleSheet('font-size: 12px;')
        savings_container = QGroupBox()
        savings_layout = QHBoxLayout()
        savings_layout.addWidget(average_display)
        savings_layout.addWidget(self.years_label)
        savings_layout.addWidget(years_slider)
        savings_container.setLayout(savings_layout)

        newest_container = QGroupBox()
        layout = QVBoxLayout()
        layout.addWidget(self.dropdownRow)
        layout.addWidget(self.sliderRow)
        layout.addWidget(savings_container)
        layout.addWidget(self.currentPlot)
        newest_container.setLayout(layout)
        self.setCentralWidget(newest_container)
        self.layout_is_normal = False
        self.has_savings_layout = True

    def changeYears(self, year):
        #called when slider from savings view is adjusted
        self.years_label.setText('Years Projected: %s' % year)
        self.years_projected = year
        self.displaySavingsProjections()

    def displaySavingsProjections(self):
        if self.all_balances:
            #create new layout
            if not self.has_savings_layout:
                self.handleSavingsLayout()

            init_amount = self.all_balances[1][-1] #last known amount in account
            avg_yearly_savings = self.avgSavings * 12

            #following code generates x ticks, starting on current year, increments of either one or two, depending on how many years are projected
            latest_year = max(map(lambda year: int(year), self.income_source_hash.keys()))
            projection_x_ticks = [] #a list of tuples where (x coordinate, x description), where x description is the year projected
            projection_savings = [] #the y value, projected saving amount
            year_interval = 1
            if self.years_projected > 45:
                year_interval = 2
            for i in range(0, self.years_projected, year_interval):
                projection_x_ticks.append((i, str(latest_year + i)))
                projection_savings.append(init_amount + (avg_yearly_savings * i))

            self.clearPlot()
            self.currentPlot.plot([item[0] for item in projection_x_ticks], projection_savings, pen=self.bluePen, symbol='o', symbolBrush=(57, 64, 255))
            self.currentPlot.setTitle('Projected Savings for %s Years' % self.years_projected)
            self.xAxis.setTicks([projection_x_ticks])

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
