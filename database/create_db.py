import psycopg2


def create_db():
    # Connect to PostgreSQL

    conn = psycopg2.connect(
        host="localhost",
        database="financial_db",
        user="financial_user",
        password="financial-agent")

    cursor = conn.cursor()

    # Create customers table having cols: id, name, email, country, account_type (savings/investment/checking)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100) NOT NULL UNIQUE,
        country VARCHAR(50),
        account_type VARCHAR(20) CHECK (account_type IN ('savings', 'investment', 'checking'))
    );
    """)

    # Create accounts table having cols: id, customer_id, balance, currency, created_date, status (active/frozen)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id SERIAL PRIMARY KEY,
        customer_id INTEGER REFERENCES customers(id),
        balance DECIMAL(15, 2) NOT NULL,
        currency VARCHAR(10) NOT NULL,
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(20) CHECK (status IN ('active', 'frozen')) DEFAULT 'active'
    );
    """)

    # Create transactions table having cols: id, account_id, type (deposit/withdrawal/transfer), amount, date, status

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id SERIAL PRIMARY KEY,
        account_id INTEGER REFERENCES accounts(id),
        type VARCHAR(20) CHECK (type IN ('deposit', 'withdrawal', 'transfer')) NOT NULL,
        amount DECIMAL(15, 2) NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(20) CHECK (status IN ('pending', 'completed', 'failed'))
    );
    """)

    # Create loans table having cols: id, customer_id, amount, interest_rate, start_date, due_date, status (active/paid/overdue)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS loans (
        id SERIAL PRIMARY KEY,
        customer_id INTEGER REFERENCES customers(id),
        amount DECIMAL(15, 2) NOT NULL,
        interest_rate DECIMAL(5, 2) NOT NULL,
        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        due_date TIMESTAMP NOT NULL,
        status VARCHAR(20) CHECK (status IN ('active', 'paid', 'overdue'))
    );
    """)

    # Create investments table having cols: id, customer_id, asset_name, amount_invested, current_value, purchase_date

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS investments (
        id SERIAL PRIMARY KEY,
        customer_id INTEGER REFERENCES customers(id),
        asset_name VARCHAR(100) NOT NULL,
        amount_invested DECIMAL(15, 2) NOT NULL,
        current_value DECIMAL(15, 2) NOT NULL,
        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
    );
    """)

    # Insert sample data into customers table
    cursor.execute("""
    INSERT INTO customers (name, email, country, account_type) VALUES
    ('Alice Smith', 'alice@gmail.com', 'USA', 'savings'),
    ('Bob Johnson', 'bob@gmail.com', 'UK', 'investment'),
    ('Charlie Brown', 'charlie@gmail.com', 'Canada', 'checking'),
    ('Diana Prince', 'diana@gmail.com', 'UAE', 'savings'),
    ('Ethan Hunt', 'ethan@gmail.com', 'Australia', 'investment'),
    ('Fiona Gallagher', 'fiona@gmail.com', 'Ireland', 'checking'),
    ('George Martin', 'george@gmail.com', 'Germany', 'savings'),
    ('Hannah Lee', 'hannah@gmail.com', 'South Korea', 'investment')    

    """)

    # Insert sample data into accounts table
    cursor.execute("""
    INSERT INTO accounts (customer_id, balance, currency, status) VALUES
    (1, 5000.00, 'USD', 'active'),
    (2, 15000.00, 'GBP', 'active'),
    (3, 2000.00, 'CAD', 'frozen'),
    (4, 8000.00, 'AED', 'active'),
    (5, 12000.00, 'AUD', 'active'),
    (6, 3000.00, 'EUR', 'frozen'),
    (7, 7000.00, 'USD', 'active'),
    (8, 10000.00, 'KRW', 'active');


    """)

    # Insert sample data into transactions table
    cursor.execute("""
    INSERT INTO transactions (account_id, type, amount, date, status) VALUES
    (1, 'deposit', 2000.00, '2025-10-15', 'completed'),
    (2, 'withdrawal', 500.00, '2025-11-20', 'completed'),
    (3, 'transfer', 1000.00, '2025-11-25', 'pending'),
    (4, 'deposit', 3000.00, '2025-12-10', 'completed'),
    (5, 'withdrawal', 2000.00, '2025-12-20', 'failed'),
    (6, 'transfer', 1500.00, '2026-01-15', 'completed'),
    (7, 'deposit', 4000.00, '2026-02-10', 'completed'),
    (8, 'withdrawal', 2500.00, '2026-03-05', 'pending');
    """)

    # Insert sample data into loans table
    cursor.execute("""
    INSERT INTO loans (customer_id, amount, interest_rate, due_date, status) VALUES
    (1, 10000.00, 5.00, '2024-12-31', 'active'),
    (2, 20000.00, 4.50, '2025-06-30', 'paid'),
    (3, 15000.00, 6.00, '2024-11-30', 'overdue'),
    (4, 25000.00, 3.75, '2025-01-31', 'active'),
    (5, 30000.00, 4.25, '2025-03-31', 'paid'),
    (6, 12000.00, 5.50, '2024-10-31', 'overdue'),
    (7, 18000.00, 4.75, '2025-02-28', 'active'),
    (8, 22000.00, 3.90, '2025-04-30', 'paid');    


    """)

    # Insert sample data into investments table
    cursor.execute("""
    INSERT INTO investments (customer_id, asset_name, amount_invested, current_value) VALUES
    (1, 'Apple Inc. (AAPL)', 5000.00, 5500.00),
    (2, 'Amazon.com Inc. (AMZN)', 10000.00, 12000.00),
    (3, 'Tesla Inc. (TSLA)', 3000.00, 2500.00),
    (4, 'Microsoft Corp. (MSFT)', 7000.00, 7500.00),
    (5, 'Alphabet Inc. (GOOGL)', 8000.00, 8500.00),
    (6, 'Facebook Inc. (META)', 2000.00, 1800.00),
    (7, 'NVIDIA Corp. (NVDA)', 6000.00, 6500.00),
    (8, 'Netflix Inc. (NFLX)', 4000.00, 4200.00);
    """)

    # Commit changes and close connection
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_db()
    print("Database and tables created successfully!")
