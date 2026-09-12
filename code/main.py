import pandas as pd
import os
from ai_extractor import extract_amount_from_image

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
    
    requests['request_date'] = pd.to_datetime(requests['request_date'])
    requests['desired_completion_date'] = pd.to_datetime(requests['desired_completion_date'])
    events['event_date'] = pd.to_datetime(events['event_date'])
    rates['rate_date'] = pd.to_datetime(rates['rate_date'])
    
    return requests, profiles, events, rates, messages, images, options

def fill_missing_amounts(events, images):
    print("\nBuscando eventos con montos faltantes...")
    
    missing_mask = events['amount'].isna()
    missing_events = events[missing_mask].copy()
    
    print(f"Se encontraron {len(missing_events)} eventos sin monto. Cruzando con imágenes...")
    
    missing_with_images = missing_events.merge(
        images[['image_id', 'related_event_id']], 
        left_on='event_id', 
        right_on='related_event_id', 
        how='inner'
    )
    
    print("Iniciando extracción con IA (esto tomará unos segundos por imagen)...")
    for index, row in missing_with_images.iterrows():
        image_id = row['image_id']
        event_id = row['event_id']
        
        image_path = os.path.join(DATA_DIR, "media", "images", f"{image_id}.png")
        
        print(f"Procesando {image_id}.png para el evento {event_id}...")
        extracted_amount = extract_amount_from_image(image_path)
        
        if extracted_amount is not None:
            events.loc[events['event_id'] == event_id, 'amount'] = extracted_amount
            print(f"  -> Monto extraído: {extracted_amount}")
            
    return events

def normalize_currencies(events, profiles, rates):
    print("\nNormalizando divisas...")
    events_merged = events.merge(profiles[['user_id', 'home_currency']], on='user_id', how='left')
    
    events_with_rates = events_merged.merge(
        rates, 
        left_on=['event_date', 'currency', 'home_currency'],
        right_on=['rate_date', 'from_currency', 'to_currency'],
        how='left'
    )
    
    events_with_rates['rate'] = events_with_rates['rate'].fillna(1.0)
    events_with_rates['normalized_amount'] = events_with_rates['amount'] * events_with_rates['rate']
    events_with_rates = events_with_rates.drop(columns=['rate_date', 'from_currency', 'to_currency'])
    
    return events_with_rates

if __name__ == "__main__":
    reqs, profs, evts, rts, msgs, imgs, opts = load_data()
    
    evts_filled = fill_missing_amounts(evts, imgs)
    
    evts_normalized = normalize_currencies(evts_filled, profs, rts)
    
    print("\n=== MUESTRA FINAL DE EVENTOS CORREGIDOS Y NORMALIZADOS ===")
    eventos_corregidos = ['event_253', 'event_1442', 'event_1545']
    mask = evts_normalized['event_id'].isin(eventos_corregidos)
    print(evts_normalized[mask][['event_id', 'amount', 'currency', 'rate', 'normalized_amount', 'home_currency']])