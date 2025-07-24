#!/usr/bin/env python3
"""
Script to clean and format JMoney trading alerts from Discord CSV export.
Extracts Date Time, Price, Size (A/B/C), and Stop values into a clean CSV format.
"""

import pandas as pd
import re
from datetime import datetime

def determine_trade_result(alert_time, entry_price, target1, target2, stop_price, price_data):
    """
    Determine if a trade hit Target 1, Target 2, or stopped out.
    
    Args:
        alert_time (datetime): Time of the trading alert
        entry_price (float): Entry price of the trade
        target1 (float): First target price
        target2 (float): Second target price
        stop_price (float): Stop loss price
        price_data (DataFrame): OHLC price data
    
    Returns:
        tuple: (result, price_at_alert)
    """
    # Find price data at or after the alert time
    alert_time = pd.to_datetime(alert_time)
    price_data['time'] = pd.to_datetime(price_data['time'])
    
    # Find the closest price data point at or after the alert
    future_data = price_data[price_data['time'] >= alert_time].copy()
    
    if future_data.empty:
        return "No Data", None
    
    # Get price at time of alert (or closest after)
    price_at_alert = future_data.iloc[0]['close']
    
    # Check each subsequent candle to see what was hit first
    for _, candle in future_data.iterrows():
        high = candle['high']
        low = candle['low']
        
        # For long trades, check if stop was hit first (price went below stop)
        if low <= stop_price:
            return "Stop Out", price_at_alert
        
        # Check if Target 2 was hit (higher priority since it's further)
        if high >= target2:
            return "Target 1 + 2 Hit", price_at_alert
        
        # Check if Target 1 was hit
        if high >= target1:
            return "Target 1 Hit", price_at_alert
    
    # If we've gone through all available data without hitting targets or stop
    return "Open/No Data", price_at_alert

def clean_trading_data(input_file='jmoney_alerts.csv', output_file='cleaned_trading_alerts.csv', price_data_file='CME_MINI_ES1!, 5_2025_CST.csv'):
    """
    Clean and format trading alert data from Discord CSV export.
    
    Args:
        input_file (str): Path to input CSV file
        output_file (str): Path to output cleaned CSV file
    """
    
    # Read the CSV files
    print(f"Reading alert data from {input_file}...")
    df = pd.read_csv(input_file)
    
    print(f"Reading price data from {price_data_file}...")
    price_data = pd.read_csv(price_data_file)
    
    # Get the date range of available price data
    price_data['time'] = pd.to_datetime(price_data['time'])
    price_start = price_data['time'].min()
    price_end = price_data['time'].max()
    print(f"Price data available from {price_start} to {price_end}")
    
    # Filter for rows that contain trading alerts (have the 🚨 emoji and ES long)
    trading_alerts = df[df['content'].str.contains('🚨 ES long', na=False)]
    
    # Filter alerts to only include those within the price data range
    trading_alerts['timestamp_dt'] = pd.to_datetime(trading_alerts['timestamp'])
    trading_alerts_filtered = trading_alerts[
        (trading_alerts['timestamp_dt'] >= price_start) & 
        (trading_alerts['timestamp_dt'] <= price_end)
    ].copy()
    
    print(f"Found {len(trading_alerts)} total trading alert messages")
    print(f"Processing {len(trading_alerts_filtered)} alerts within price data range")
    
    # Initialize lists to store extracted data
    cleaned_data = []
    
    for index, row in trading_alerts_filtered.iterrows():
        try:
            content = row['content']
            timestamp = row['timestamp']
            
            # Parse the content to extract price, size, and stop
            # Pattern: 🚨 ES long 6326: A\nStop: 6316
            lines = content.split('\n')
            
            # Extract price and size from first line
            # Pattern: 🚨 ES long [price]: [size] [optional GAMMA]
            first_line = lines[0]
            price_size_match = re.search(r'ES long (\d+): ([ABC])(?:\s+GAMMA)?', first_line)
            
            if not price_size_match:
                print(f"Warning: Could not parse price/size from: {first_line}")
                continue
                
            price = int(price_size_match.group(1))
            size = price_size_match.group(2)
            
            # Extract stop from second line
            # Pattern: Stop: [stop_price]
            stop = None
            for line in lines[1:]:
                if line.startswith('Stop:'):
                    stop_match = re.search(r'Stop:\s*(\d+)', line)
                    if stop_match:
                        stop = int(stop_match.group(1))
                        break
            
            if stop is None:
                print(f"Warning: Could not find stop price in: {content}")
                continue
            
            # Parse timestamp
            # Convert from ISO format to datetime
            dt = pd.to_datetime(timestamp)
            
            # Calculate targets
            target1 = price + 7
            target2 = price + 12
            
            # Determine trade result
            result, price_at_alert = determine_trade_result(
                dt, price, target1, target2, stop, price_data
            )
            
            # Add to cleaned data
            cleaned_data.append({
                'Date Time': dt.strftime('%Y-%m-%d %H:%M:%S'),
                'Price': price,
                'Size': size,
                'Stop': stop,
                'Target 1': target1,
                'Target 2': target2,
                'Price at Alert': price_at_alert,
                'Result': result
            })
            
        except Exception as e:
            print(f"Error processing row {index}: {e}")
            continue
    
    # Create DataFrame from cleaned data
    cleaned_df = pd.DataFrame(cleaned_data)
    
    # Sort by Date Time (most recent first)
    cleaned_df = cleaned_df.sort_values('Date Time', ascending=False)
    
    # Save to CSV
    cleaned_df.to_csv(output_file, index=False)
    
    print(f"\nCleaned data saved to {output_file}")
    print(f"Total records processed: {len(cleaned_df)}")
    
    # Display summary statistics
    print("\n=== SUMMARY ===")
    print(f"Date range: {cleaned_df['Date Time'].min()} to {cleaned_df['Date Time'].max()}")
    print(f"Price range: ${cleaned_df['Price'].min()} - ${cleaned_df['Price'].max()}")
    print(f"Size distribution:")
    print(cleaned_df['Size'].value_counts().sort_index())
    print(f"\nTrade Results:")
    print(cleaned_df['Result'].value_counts())
    
    # Display first few rows
    print(f"\nFirst 5 records:")
    print(cleaned_df.head())
    
    return cleaned_df

if __name__ == "__main__":
    # Run the cleaning process
    cleaned_data = clean_trading_data()
