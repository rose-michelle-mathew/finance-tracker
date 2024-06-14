import streamlit as st
import yfinance as yf
import pandas as pd
import sqlite3
from datetime import datetime
import calendar
from streamlit_option_menu import option_menu
import plotly.express as px

import plotly.graph_objects as go

import geocoder
import requests


st.set_page_config(layout ="wide")

# Ensure the user is logged in
if "user" not in st.session_state or st.session_state["user"] is None:
    st.warning("Please log in to access this page.")
    st.stop()

# Connect to SQLite database
conn = sqlite3.connect('data.db', check_same_thread=False)
cur = conn.cursor()

# Check if the finance_data table already exists and has the correct columns
cur.execute("PRAGMA table_info(finance_data)")
columns = [col[1] for col in cur.fetchall()]

if 'username' not in columns:
    # Rename the finance_data table to new_finance_data
    cur.execute("ALTER TABLE finance_data RENAME TO new_finance_data")
    conn.commit()

    # Create the finance_data table with the correct columns
    cur.execute('''
    CREATE TABLE IF NOT EXISTS finance_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        period TEXT,
        type TEXT,
        category TEXT,
        amount INTEGER,
        remarks TEXT
    )
    ''')
    conn.commit()

    # Transfer data to the new table
    cur.execute('''
    INSERT INTO finance_data (username, period, type, category, amount, remarks)
    SELECT username, period, type, category, amount, remarks FROM new_finance_data
    ''')
    conn.commit()

    # Drop the temporary table
    cur.execute("DROP TABLE new_finance_data")
    conn.commit()

# Function to add data
# Function to add or update data
def addOrUpdateData(username, period, category, amount, remarks, data_type):
    # Check if data already exists for the given period and category
    existing_data = cur.execute("SELECT id FROM finance_data WHERE username = ? AND period = ? AND category = ? AND type = ?", 
                                (username, period, category, data_type)).fetchone()
    if existing_data:
        # Update existing data
        cur.execute('''
            UPDATE finance_data 
            SET amount = ?, remarks = ?
            WHERE id = ?
            ''', (amount, remarks, existing_data[0]))
    else:
        # Add new data
        cur.execute('''
            INSERT INTO finance_data (username, period, type, category, amount, remarks)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, period, data_type, category, amount, remarks))
    conn.commit()


# Get the logged-in user's usernamea
username = st.session_state["username"]

# Create tabs
tab1, tab2, tab3 = st.tabs(["Stock Prices", "Finance Tracker", "My Dashboard"])

with tab1:
    st.title("Stock Prices")

    # List of company names and ticker symbols
    excel_file = r"C:\Users\rosem\OneDrive\Desktop\Michelle\4MCA\Streamlit_Stuff\Ticker_Company.xlsx"
    company_data = pd.read_excel(excel_file)

    # Extract company names and ticker symbols
    company_names = company_data["Company_Name"].tolist()
    ticker_symbols = company_data["Symbol"].tolist()

    # Dropdown menu for selecting a company
    selected_company = st.selectbox("Select a Company", company_names)

    # Find the corresponding ticker symbol
    selected_ticker_symbol = ticker_symbols[company_names.index(selected_company)]

    st.write("Selected Ticker Symbol:", selected_ticker_symbol)

    if selected_ticker_symbol:
        # Retrieve historical data for selected stock
        tickerData = yf.Ticker(selected_ticker_symbol)
        tickerDf = tickerData.history(period='1d', start='2014-6-12', end=datetime.today())
        high_low_data = tickerDf[['High', 'Low']]

        # Check if data is available for the entered symbol
        if not tickerDf.empty:
            # Display line charts for closing prices and volume
            st.write(f"Stock Data for {selected_ticker_symbol}:")
            st.line_chart(tickerDf.Close, color="#03fc88")
            st.caption('Chart for Closing prices.')
            st.divider()
            st.line_chart(tickerDf.Volume, color="#fc0356")
            st.caption('Chart for Stock Volume.')
            st.bar_chart(high_low_data)
            st.caption('Chart for High Vs Low of Stock Prices.')
        else:
            st.warning("No data available for the entered symbol. Please enter a valid stock ticker symbol.")

with tab2:
    st.title("Income and Expense Tracker")
    incomes = ["Salary", "Stocks", "Other Income"]
    expenses = ["Rent", "Utilities", "Groceries", "Car", "Insurance", "Savings", "Miscellaneous"]
    currency = "INR"

    years = [datetime.today().year, datetime.today().year + 1]
    months = list(calendar.month_name[1:])

    selected = option_menu(
        menu_title=None,
        icons=["pencil-fill", "bar-chart-fill"],
        options=["Data Entry", "Data Visualization"], orientation="horizontal",
    )

    if selected == "Data Entry":
        with st.form("entry_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            month = col1.selectbox("Select Month", months, key='month')
            year = col2.selectbox("Select Year", years, key='year')

            with st.expander("Income"):
                for income in incomes:
                    st.number_input(f"{income}:", min_value=0, format="%i", step=100, key=income)
            with st.expander("Expenses"):
                for expense in expenses:
                    st.number_input(f"{expense}:", min_value=0, format="%i", step=100, key=expense)
            with st.expander("Remarks"):
                comment = st.text_area("", placeholder="Enter Remarks")
            

            submitted = st.form_submit_button("Save Data")
        
            if submitted:
                period = f"{year}_{month}"
                for income in incomes:
                    addOrUpdateData(username, period, income, st.session_state[income], comment, 'Income')
                for expense in expenses:
                    addOrUpdateData(username, period, expense, st.session_state[expense], comment, 'Expense')
                st.success("Data Saved")

    elif selected == "Data Visualization":
        st.header("Data Visualization")
        periods = cur.execute("SELECT DISTINCT period FROM finance_data WHERE username = ?", (username,)).fetchall()
        periods = [period[0] for period in periods]

        with st.form("saved_periods"):
            period = st.selectbox("Select Period:", periods)
            submitted = st.form_submit_button("Plot Period")

            if submitted:
                income_data = cur.execute("SELECT category, amount FROM finance_data WHERE period = ? AND type = 'Income' AND username = ?", (period, username)).fetchall()
                expense_data = cur.execute("SELECT category, amount FROM finance_data WHERE period = ? AND type = 'Expense' AND username = ?", (period, username)).fetchall()

                incomes = {data[0]: data[1] for data in income_data}
                expenses = {data[0]: data[1] for data in expense_data}

                total_income = sum(incomes.values())
                total_expense = sum(expenses.values())
                remaining = total_income - total_expense

                col1, col2, col3 = st.columns(3)
                col1.metric("Total Income:", "{:,} {}".format(total_income, currency))
                col2.metric("Total Expense:", "{:,} {}".format(total_expense, currency))
                col3.metric("Total Remaining:", "{:,} {}".format(remaining, currency))


                income_df = pd.DataFrame.from_dict(incomes, orient='index', columns=['Amount'])
                expense_df = pd.DataFrame.from_dict(expenses, orient='index', columns=['Amount'])

                # Define custom color palette
                neon_pink_palette = ['#FF005E', '#F30476', '#E7098E', '#DC0DA6', '#D011BD', '#C416D5', '#B81AED', '#4361ee', '#4895ef', '#4cc9f0']
                neon_green_palette = ['#2b9348', '#3eaf7c', '#57cc99', '#64dfdf', '#72efdd', '#64dfdf', '#72efdd', '#64dfdf', '#50c9c3', '#40b3a2']

                income_df = pd.DataFrame.from_dict(incomes, orient='index', columns=['Amount']).reset_index()
                expense_df = pd.DataFrame.from_dict(expenses, orient='index', columns=['Amount']).reset_index()

                # Add a column to indicate the type (income or expense)
                income_df['Type'] = 'Income'
                expense_df['Type'] = 'Expense'

                # Concatenate dataframes
                combined_df = pd.concat([income_df, expense_df])

                # Plot pie charts for income and expenses
                fig1 = px.pie(income_df, values='Amount', names='index', title="Income Breakdown", color_discrete_sequence=neon_green_palette)
                fig1.update_traces(textposition='inside', textinfo='percent+label')

                fig2 = px.pie(expense_df, values='Amount', names='index', title="Expense Breakdown", color_discrete_sequence=neon_pink_palette)
                fig2.update_traces(textposition='inside', textinfo='percent+label')

                # Display charts
                st.plotly_chart(fig1)
                st.plotly_chart(fig2)

                st.table(income_df)
                st.table(expense_df)


with tab3:
# Function to get user's location based on IP address
    st.title("My Dashboard")

    # Function to get user's location based on IP address
    def get_user_location():
        ip = geocoder.ip('me').ip
        location = geocoder.ip(ip)
        return location

    # Function to fetch weather data from OpenWeatherMap API
    def get_weather(city, api_key):
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url)
        data = response.json()
        return data
    
    def get_icon_url(icon_code):
        return f"http://openweathermap.org/img/wn/{icon_code}.png"

    # Main function
    def main():
         # Get user's location
        location = get_user_location()

        # Display user's location
        if location:
            # Your OpenWeatherMap API key
            api_key = "8bdbd2e318823265106ee07bf92c3007"

            # Fetch weather data for user's location
            weather_data = get_weather(location.city, api_key)

            # Display weather information
            weather_container = st.container(border=True)
            # Display weather information in three columns
            with weather_container:
                if weather_data["cod"] == 200:  # Check if request was successful
                    icon_code = weather_data['weather'][0]['icon']
                    icon_url = get_icon_url(icon_code)

                    # Create three columns
                    col1, col2, col3 = st.columns(3)

                    # Display weather icon in the first column
                    with col1:
                        st.image(icon_url)

                    # Display temperature in the second column
                    with col2:
                        st.write('')
                        st.write(f"🌤️ {weather_data['main']['temp']}°C with {weather_data['weather'][0]['description']}")

                    # Display location in the third column
                    with col3:
                        st.write('')
                        st.write(f"📍 {location.city}")

                else:
                    st.write("Error fetching weather data. Please try again.")

        else:
            st.write("Error fetching location. Please try again.")

        # Retrieve finance data for all periods
        income_data = cur.execute("SELECT period, amount, category FROM finance_data WHERE type = 'Income' AND username = ?", (username,)).fetchall()
        expense_data = cur.execute("SELECT period, amount, category FROM finance_data WHERE type = 'Expense' AND username = ?", (username,)).fetchall()

        total_income = sum(data[1] for data in income_data)
        total_expense = sum(data[1] for data in expense_data)
        remaining = total_income - total_expense

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income:", "{:,} {}".format(total_income, currency))
        col2.metric("Total Expense:", "{:,} {}".format(total_expense, currency))
        col3.metric("Total Remaining:", "{:,} {}".format(remaining, currency))

        # Convert fetched data into pandas DataFrame
        income_df = pd.DataFrame(income_data, columns=["Period", "Income","Category"])
        expense_df = pd.DataFrame(expense_data, columns=["Period", "Expense","Category"])

        # Concatenate income and expense data
        merged_df = pd.concat([income_df, expense_df])

        # Extract month and year from the period
        merged_df["Month"] = merged_df["Period"].str.split("_").str[1]

        # Group by month and sum the amounts
        grouped_df = merged_df.groupby("Month").sum().reset_index()

        # Create a line chart for income and expense
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

        # Convert the "Month" column to categorical data type with the specified order
        merged_df["Month"] = pd.Categorical(merged_df["Month"], categories=month_order, ordered=True)
                
        neon_colors = ['#FF005E', '#F30476', '#E7098E', '#DC0DA6', '#D011BD', '#C416D5', '#B81AED', '#4361ee', '#4895ef', '#4cc9f0']
        neon_green_palette = ['#2b9348', '#3eaf7c', '#57cc99', '#64dfdf', '#72efdd', '#64dfdf', '#72efdd', '#64dfdf', '#50c9c3', '#40b3a2']

        # Create a line chart for income and expense
        fig = px.line(grouped_df, x='Month', y=['Income', 'Expense'], title='Income and Expense over Months')
        fig.update_layout(xaxis_title='Month', yaxis_title='Amount (INR)')

        # Group by category and sum the income for each category
        income_grouped = income_df.groupby("Category").sum().reset_index()

        # Create a bar plot for total income by category
        fig2 = px.bar(income_grouped, x='Category', y='Income', title='Total Income by Category',color='Category', color_discrete_sequence=neon_green_palette)
        fig2.update_layout(xaxis_title='Category', yaxis_title='Total Income (INR)')
 
        # Group by category and sum the income for each category
        expense_grouped = expense_df.groupby("Category").sum().reset_index()

        # Create a bar plot for total income by category
        fig3 = px.bar(expense_grouped, x='Category', y='Expense', title='Total Expenses by Category', color='Category', color_discrete_sequence=neon_colors)
        fig3.update_layout(xaxis_title='Category', yaxis_title='Total Expenses (INR)')
  

        fig4 = px.scatter(merged_df, x='Income', y='Expense', color='Category', 
                 title='Income vs Expense by Category', 
                 labels={'Income': 'Total Income (INR)', 'Expense': 'Total Expense (INR)'})
        fig4.update_layout(xaxis_title='Total Income (INR)', yaxis_title='Total Expense (INR)')

        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(fig)  # Replace fig1 with the chart variable for the first chart

        with col2:
            st.plotly_chart(fig2)  # Replace fig2 with the chart variable for the second chart

        with col1:
            st.plotly_chart(fig3)  # Replace fig3 with the chart variable for the third chart



    if __name__ == "__main__":
        main()