import pandas as pd
import os

# Configuración de rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "dataset")

def load_data():
    print("Cargando datasets...")
    requests = pd.read_csv(os.path.join(DATA_DIR, "requests.csv"))
    profiles = pd.read_csv(os.path.join(DATA_DIR, "financial_profiles.csv"))
    events = pd.read_csv(os.path.join(DATA_DIR, "financial_events.csv"))
    rates = pd.read_csv(os.path.join(DATA_DIR, "exchange_rates.csv"))
    messages = pd.read_csv(os.path.join(DATA_DIR, "messages.csv"))
    images = pd.read_csv(os.path.join(DATA_DIR, "images.csv"))
    options = pd.read_csv(os.path.join(DATA_DIR, "request_payment_options.csv"))
    
    # Parsear fechas cruciales
    requests['request_date'] = pd.to_datetime(requests['request_date'])
    requests['desired_completion_date'] = pd.to_datetime(requests['desired_completion_date'])
    events['event_date'] = pd.to_datetime(events['event_date'])
    rates['rate_date'] = pd.to_datetime(rates['rate_date'])
    
    return requests, profiles, events, rates, messages, images, options

def normalize_currencies(events, profiles, rates):
    print("Normalizando divisas...")
    # 1. Agregar la moneda local (home_currency) al evento según el usuario
    events_merged = events.merge(profiles[['user_id', 'home_currency']], on='user_id', how='left')
    
    # 2. Cruzar con las tasas de cambio (currency -> from_currency, home_currency -> to_currency)
    events_with_rates = events_merged.merge(
        rates, 
        left_on=['event_date', 'currency', 'home_currency'],
        right_on=['rate_date', 'from_currency', 'to_currency'],
        how='left'
    )
    
    # 3. Si la moneda original es igual a la local (ej. USD a USD), la tasa (rate) será NaN tras el merge. La llenamos con 1.0
    events_with_rates['rate'] = events_with_rates['rate'].fillna(1.0)
    
    # 4. Calcular monto estandarizado
    events_with_rates['normalized_amount'] = events_with_rates['amount'] * events_with_rates['rate']
    
    # 5. Limpiar columnas auxiliares para no ensuciar el DataFrame
    events_with_rates = events_with_rates.drop(columns=['rate_date', 'from_currency', 'to_currency'])
    
    return events_with_rates

if __name__ == "__main__":
    # Ejecutamos la carga
    reqs, profs, evts, rts, msgs, imgs, opts = load_data()
    
    # Ejecutamos la normalización
    evts_normalized = normalize_currencies(evts, profs, rts)
    
    # Verificamos
    print(f"\nTotal de eventos cargados: {len(evts_normalized)}")
    print("\nMuestra de eventos normalizados (Nota los NaN en 'amount' que tendremos que extraer con IA):")
    print(evts_normalized[['event_id', 'amount', 'currency', 'rate', 'normalized_amount', 'home_currency']].head(10))