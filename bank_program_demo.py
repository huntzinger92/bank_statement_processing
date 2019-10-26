#!/usr/bin/env python
# coding: utf-8

# In[70]:


import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates
import re
import operator

#this is to avoid running into deprecation with a datetime converter in the balance graphing section (date2num)
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()


# In[71]:


#importing and then cleaning the data

df = pd.read_csv(r'C:\Users\Trevor\Documents\bank_crunch\Export.csv', header=3, sep=',', error_bad_lines=False)
df['Date'] = pd.to_datetime(df.Date)
df = df.fillna(0)
df['year_month'] = df['Date'].dt.to_period('M')
df.sort_values(by=['Date'])


# In[72]:


#threshold = 1160

###if user wants to exclude debits or credits larger than a certain amount due to unusual circumstances,
###uncommenting this code, entering in the maxiumum value relevant transactions for "threshold", and running it allows them to do so

#rows_to_delete = []
#for item in df.iterrows():
    #if abs(item[1].get('Amount Debit')) >= threshold or abs(item[1].get('Amount Credit')) >= threshold:
        #rows_to_delete.append(item[0])
        ###item[0] is the index of the row to be dropped
#df = df.drop([*rows_to_delete], axis=0)


# In[73]:


#all data will initially be collected in "month_hash", where each month is a "sub-hash", containing key/value pairs for total
#expenditures, income, and balance
#all_balances will be a list of tuples that store date and account balance for every transaction

month_hash = {}
all_balances = []

for item in df.iterrows():
    date = str(item[1].get('year_month').month) + ' ' + str(item[1].get('year_month').year)
    if date not in month_hash:
        month_hash[date] = {'income': item[1].get('Amount Credit'), 'expenditures': (item[1].get('Amount Debit') * -1), 'balance': item[1].get('Balance')}
        all_balances.append((item[1].get('Date'), item[1].get('Balance')))
    else: 
        month_hash[date]['income'] += item[1].get('Amount Credit')
        month_hash[date]['expenditures'] -= item[1].get('Amount Debit')
        
months = list(month_hash.keys()) #this code simply extracts data from month_hash into separate lists for each attribute
incomes = []                     #allows for more concise code later, even though it doesn't add any new information
expenditures = [] 
balances = []

for month in months:
    incomes.append(month_hash[month]['income'])
    expenditures.append(month_hash[month]['expenditures'])
    balances.append(month_hash[month]['balance'])

months.reverse()  #reversing each list so graphs start with oldest month first
incomes.reverse()
expenditures.reverse()
balances.reverse()
all_balances.reverse()


# 

# In[81]:


x_axis_monthly = range(0, len(months))

plt.figure(figsize = (len(months), 3))
plt.plot(x_axis_monthly, balances, '--bo')
plt.grid(True)
plt.ylabel('Amount in Dollars')
plt.xticks(x_axis_monthly, months)
plt.title("Monthly Account Balance")
plt.show()

balance_dates = matplotlib.dates.date2num([i[0] for i in all_balances])
plt.figure(figsize = (len(months), 3))
plt.grid(True)
plt.ylabel('Amount in Dollars')
plt.title("All Account Balance Changes")
plt.plot_date(balance_dates, [i[1] for i in all_balances], '-b');


# In[75]:


plt.figure(figsize=(len(months),3))
plt.plot(x_axis_monthly, incomes, '--go', label='Incomes')
plt.plot(x_axis_monthly, expenditures, '--ro', label='Expenditures')
plt.legend()
plt.grid(True)
plt.xticks(x_axis_monthly, months)
plt.show()


# In[76]:


savings = list(map(lambda income, expense: income - expense, incomes, expenditures))

plt.figure(figsize=(len(months),3))
plt.plot(x_axis_monthly, savings, '--bo', label='savings')
plt.legend()
plt.grid(True)
plt.xticks(x_axis_monthly, months)
plt.show()


# In[77]:


#Note: to have each variable shared by a month, we need to create offset x values so bar graphs can be displayed side by side

x_left = list(map(lambda x: x -.25, x_axis_monthly))
x_right = list(map(lambda x: x +.25, x_axis_monthly))

plt.figure(figsize=(len(months), 6))
plt.bar(x_left, incomes, width=.25, align='center', alpha=.5, color='g')
plt.bar(x_axis_monthly, expenditures, width=.25, align='center', alpha=.5, color='r')
plt.bar(x_right, savings, width=.25, align='center', alpha=.5, color='b')
plt.grid(True, axis='y')
plt.xticks(x_axis_monthly, months)
plt.ylabel('Money in Dollars')
plt.title('Comparison of Monthly Income, Expenditures, and Savings')
variables = ['Income', 'Expenditures', 'Savings']
plt.legend(variables, loc=2)
plt.show();


# In[ ]:





# In[78]:


#this code sorts all income by source, by year

income_source_hash = {}
source_matcher = re.compile("(?<=Deposit ).*$") #matches all text from "Deposit " to end of line (name of entity depositing)
atm_catcher = re.compile('^at ATM #[0-9]*$') #different atms have different number ids, this allows us to lump them all together

for item in df.iterrows():
    if item[1].get('Amount Credit'):
        amount = item[1].get('Amount Credit')
        year = item[1].get('year_month').year
        match_object = source_matcher.search(str(item[1].get('Description')))
        if match_object and atm_catcher.match(match_object.group(0)):
            description = 'ATM Deposit'
        elif match_object:
            description = match_object.group(0)
        else:
            description = 'Cash Deposit'
        #small correction for my own personal data
        if description == '1004166091752':
            description = 'PAYPAL'
        if year in income_source_hash:
            if description in income_source_hash[year]:
                income_source_hash[year][description] += amount
            else:
                income_source_hash[year][description] = amount
        else:
            income_source_hash[year] = {description: amount}


# In[79]:


for year in income_source_hash:
    sorted_income_tuples = sorted(income_source_hash[year].items(), key=operator.itemgetter(1), reverse=True)
    plt.figure(figsize = (len(income_source_hash[year]) * 2, 8))
    plt.bar([item[0] for item in sorted_income_tuples], [item[1] for item in sorted_income_tuples], color='g')
    plt.grid(True, axis='y')
    plt.ylabel('Amount in Dollars')
    plt.title('Sources of Income ' + str(year))
    plt.show();


# In[99]:


yearly_gross = []
year_x_ticks = []

for year in income_source_hash:
    count = 0
    year_x_ticks.append(year)
    for name in income_source_hash[year]:
        count += income_source_hash[year][name]
    yearly_gross.append(count)
yearly_gross.reverse()
year_x_ticks.reverse()

plt.figure(figsize=(len(yearly_gross), 5))
plt.plot(range(0, len(yearly_gross)), yearly_gross, '--go', label='Yearly Salary')
plt.grid(True)
plt.xticks(range(0, len(yearly_gross)), year_x_ticks)
plt.title('Total Year Gross Income')
plt.show()


# In[ ]:





# In[ ]:




