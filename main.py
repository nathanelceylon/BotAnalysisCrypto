import requests
import yfinance as yf
import pandas as pd
import ta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time

def get_top_20_cryptos():
    # Récupérer une large liste de cryptomonnaies par capitalisation boursière
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 100,
        'page': 1
    }
    response = requests.get(url, params=params)
    data = response.json()
    large_ticker_list = [coin['symbol'].upper() for coin in data]

    # Télécharger les données horaires pour ces cryptomonnaies
    evolutions = {}
    for t in large_ticker_list:
        symbol = f"{t}-USD"
        try:
            data = yf.download(tickers=symbol, interval='1h')
            if not data.empty and len(data) > 1:
                # Calculer l'évolution horaire
                last_close = data['Close'].iloc[-1]
                prev_close = data['Close'].iloc[-2]
                hourly_change = (last_close - prev_close) / prev_close
                evolutions[symbol] = hourly_change
        except Exception :
            pass

    # Trier les cryptomonnaies par leur évolution horaire et sélectionner les 20 meilleures évolutions positives
    sorted_evolutions = sorted(evolutions.items(), key=lambda x: x[1], reverse=True)
    top_20_positive_evolutions = [symbol for symbol, change in sorted_evolutions if change > 0][:10]

    return top_20_positive_evolutions

# Utiliser la fonction pour obtenir la liste mise à jour
ticker_list = get_top_20_cryptos()
print(f"Les 20 cryptomonnaies avec les meilleures évolutions positives de la dernière heure : {ticker_list}")



# Fonction pour calculer les indicateurs techniques
def calculate_technical_indicators(df):
    # SMA
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()

    # EMA
    df['EMA_10'] = df['Close'].ewm(span=10, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()

    # RSI
    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()

    # Bollinger Bands
    bollinger = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_Upper'] = bollinger.bollinger_hband()
    df['BB_Middle'] = bollinger.bollinger_mavg()
    df['BB_Lower'] = bollinger.bollinger_lband()

    # MACD
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()

    # ATR
    df['ATR'] = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close']).average_true_range()

    # ADX
    adx = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=14)
    df['ADX'] = adx.adx()
    df['+DI'] = adx.adx_pos()  # Positive Directional Indicator
    df['-DI'] = adx.adx_neg()  # Negative Directional Indicator

    return df

# Obtenir les 20 plus grandes cryptos
ticker_list = get_top_20_cryptos()

# Télécharger les données pour chaque ticker
Dataset_hour = {}
valid_tickers = []

for t in ticker_list:
    symbol = f"{t}-USD"
    try:
        data = yf.download(tickers=t, start='2024-04-01', end=None, interval='1d')
        if not data.empty:
            Dataset_hour[t] = data
            valid_tickers.append(t)
    except Exception:
        pass

# Calculer les indicateurs pour chaque ticker et obtenir les dernières valeurs
last_values = {}
for t in valid_tickers:
    Dataset_hour[t] = calculate_technical_indicators(Dataset_hour[t])
    last_row = Dataset_hour[t].iloc[-1]
    last_values[t] = {
        'BB_Middle': last_row['BB_Middle'],
        'RSI': last_row['RSI'],
        'ADX': last_row['ADX'],
        '+DI': last_row['+DI'],
        '-DI': last_row['-DI'],
        'Close': last_row['Close'],
        'Close_BB_Middle_Diff': last_row['Close'] - last_row['BB_Middle'],
        'Evolution': -(last_row['Close'] - last_row['BB_Middle']) / last_row['Close'] * 100,
        'MACD': last_row['MACD'],
        'MACD_Signal': last_row['MACD_Signal'],
        'SMA_50' : last_row['SMA_50'],
        'SMA_10' : last_row['SMA_10'],
        'EMA_50' : last_row['EMA_50'],
        'EMA_10' : last_row['EMA_10']
    }

buy_tickers = []

# Afficher les dernières valeurs des indicateurs et la différence
for t in ticker_list:
    print(f"{t} - Last BB_Middle: {last_values[t]['BB_Middle']}, Last RSI: {last_values[t]['RSI']}, Last ADX: {last_values[t]['ADX']}, Last +DI: {last_values[t]['+DI']}, Last -DI: {last_values[t]['-DI']}, Close: {last_values[t]['Close']}, MACD: {last_values[t]['MACD']}, MACD Signal: {last_values[t]['MACD_Signal']}, SMA_50 : {last_values[t]['SMA_50']}, EMA_50 : {last_values[t]['EMA_50']}, Close - BB_Middle: {last_values[t]['Close_BB_Middle_Diff']}")
    #print(f"{t} - Evolution probable: {last_values[t]['Evolution']}%")
    if (last_values[t]['RSI'] < 80 and last_values[t]['+DI']- 5 > last_values[t]['-DI'] and last_values[t]['MACD'] > last_values[t]['MACD_Signal']) :
      print(f"{t} - BUY")
      buy_tickers.append(t)
      
print(buy_tickers)

def send_email(subject, body, recipient_email):
    sender_email = "nathanelceylon@gmail.com"
    sender_password = "wnqy dyrm pqjd sxyh"
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f"Email envoyé à {recipient_email}")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email: {e}")

# Fonction pour vérifier les alertes et envoyer des emails
def check_and_alert(tickers, last_values):
    cryptos_to_sell = []
    cryptos_to_buy = []
    
    for ticker in tickers:
        if (last_values[ticker]['RSI'] > 85 or last_values[ticker]['+DI'] + 5 < last_values[ticker]['-DI']):
            cryptos_to_sell.append(ticker)
        if (last_values[ticker]['RSI'] < 80 and last_values[ticker]['+DI'] - 5 > last_values[ticker]['-DI'] and last_values[ticker]['MACD'] > last_values[ticker]['MACD_Signal']):
            cryptos_to_buy.append(ticker)

    if cryptos_to_sell:
        subject = "Crypto SELL ALERT"
        body = f"Crypto(s) à vendre rapidement:\n\n" + "\n".join(cryptos_to_sell)
        send_email(subject, body, "nathanelceylon@gmail.com")

    if cryptos_to_buy:
        subject = "Crypto BUY ALERT"
        body = f"Crypto(s) à acheter rapidement:\n\n" + "\n".join(cryptos_to_buy)
        send_email(subject, body, "nathanelceylon@gmail.com")

    if not cryptos_to_sell and not cryptos_to_buy:
        subject = "Crypto Update"
        body = "Don't move! Aucune action recommandée pour le moment."
        send_email(subject, body, "nathanelceylon@gmail.com")

# Fonction principale pour exécuter l'algorithme
def execute_algorithm():
    print("Execution du script...")
    ticker_list = get_top_20_cryptos()
    datasets = {ticker: yf.download(tickers=ticker, start='2024-04-01', interval='1d') for ticker in ticker_list}

    
    last_values = {}
    for ticker, df in datasets.items():
        df = calculate_technical_indicators(df)
        last_row = df.iloc[-1]

        last_values[ticker] = {
            'BB_Middle': last_row['BB_Middle'],
            'ADX': last_row['ADX'],
            '+DI': last_row['+DI'],
            '-DI': last_row['-DI'],
            'Close': last_row['Close'],
            'RSI': last_row['RSI'],
            'MACD': last_row['MACD'],
            'MACD_Signal': last_row['MACD_Signal']
        }
    print("Exécution terminée.")
    check_and_alert(ticker_list, last_values)
    print("Mail envoyé.")

execute_algorithm()

#schedule.every(12).hours.do(lambda: execute_algorithm)
#schedule.every(5).minutes.do(lambda: execute_algorithm)

#schedule.every().day.at("08:00").do(execute_algorithm)

#while True:
    #schedule.run_pending()
#    execute_algorithm()
#    print("Attente de 2 minutes avant la prochaine vérification...")
#    time.sleep(120)

