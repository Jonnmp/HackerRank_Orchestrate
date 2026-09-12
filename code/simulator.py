import pandas as pd
from datetime import timedelta

def filter_valid_events(events):
    """
    Limpia los eventos financieros siguiendo las reglas del problema.
    """
    invalid_statuses = ['failed', 'cancelled', 'pending_credit']
    valid_events = events[~events['status'].isin(invalid_statuses)].copy()
    
    valid_events = valid_events[valid_events['event_type'] != 'investment_value']
    
    valid_events['effective_date'] = pd.to_datetime(valid_events['settlement_date']).fillna(valid_events['event_date'])
    
    return valid_events

def simulate_90_days(user_id, request_date, profile, user_events, proposed_plan=None):
    """
    Simula el flujo de caja diario durante 90 días.
    Retorna (is_safe, min_projected_balance)
    
    proposed_plan: lista de tuplas (fecha, monto_a_pagar) para probar una opción de pago.
    """
    current_balance = profile['current_available_balance'].iloc[0]
    min_balance_to_keep = profile['minimum_balance_to_keep'].iloc[0]
    
    end_date = request_date + timedelta(days=90)
    
    future_events = user_events[
        (user_events['effective_date'] >= request_date) & 
        (user_events['effective_date'] <= end_date)
    ].copy()
    
    daily_cashflow = {}
    
    for _, event in future_events.iterrows():
        day = event['effective_date'].date()
        amount = event['normalized_amount'] # Ya convertido a la moneda local
        
        if event['direction'] == 'inbound':
            daily_cashflow[day] = daily_cashflow.get(day, 0) + amount
        elif event['direction'] == 'outbound':
            daily_cashflow[day] = daily_cashflow.get(day, 0) - amount
            
    if proposed_plan:
        for pay_date, pay_amount in proposed_plan:
            day = pd.to_datetime(pay_date).date()
            if day <= end_date.date():
                daily_cashflow[day] = daily_cashflow.get(day, 0) - pay_amount

    running_balance = current_balance
    lowest_balance_seen = running_balance
    
    for i in range(91):
        current_day = (request_date + timedelta(days=i)).date()
        
        if current_day in daily_cashflow:
            running_balance += daily_cashflow[current_day]
            
        if running_balance < lowest_balance_seen:
            lowest_balance_seen = running_balance
            
        if running_balance < min_balance_to_keep:
            return False, lowest_balance_seen
            
    return True, lowest_balance_seen

def build_installment_plan(payment_option):
    """
    Construye una lista de tuplas (fecha, monto) basada en las reglas de una opción de pago.
    """
    plan = []
    first_date = pd.to_datetime(payment_option['first_payment_date'])
    amount = payment_option['payment_amount']
    num_payments = int(payment_option['number_of_payments'])
    freq_days = int(payment_option['payment_frequency_days'])
    
    for i in range(num_payments):
        pay_date = first_date + timedelta(days=i * freq_days)
        plan.append((pay_date, amount))
        
    return plan