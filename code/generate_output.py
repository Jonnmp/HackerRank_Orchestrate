import pandas as pd
import os
from datetime import timedelta
from main import load_data, normalize_currencies, fill_missing_amounts
from simulator import filter_valid_events, simulate_90_days, build_installment_plan

def process_all_requests():
    print("=== INICIANDO PROCESAMIENTO GENERAL PARA OUTPUT.CSV ===")
    
    reqs, profs, evts, rts, msgs, imgs, opts = load_data()
    
    evts_filled = fill_missing_amounts(evts, imgs)
    evts_normalized = normalize_currencies(evts_filled, profs, rts)
    valid_events = filter_valid_events(evts_normalized)
    
    output_rows = []
    
    print(f"\nProcesando {len(reqs)} solicitudes...")
    
    for index, request in reqs.iterrows():
        req_id = request['request_id']
        user_id = request['user_id']
        req_date = request['request_date']
        requested_amount = request['requested_amount']
        completion_date = request['desired_completion_date']
        allows_partial = request['allows_partial_payment']
        
        user_profile = profs[profs['user_id'] == user_id]
        user_events = valid_events[valid_events['user_id'] == user_id]
        
        if user_profile.empty:
            continue
            
        allowed_methods_str = user_profile['payment_methods_user_will_consider'].iloc[0]
        user_considered_methods = [m.strip() for m in allowed_methods_str.split('|')]
        
        
        full_plan = [(req_date, requested_amount)]
        is_safe_full, _ = simulate_90_days(user_id, req_date, user_profile, user_events, full_plan)
        
        earliest_full_date = ""
        for i in range(91):
            check_date = req_date + timedelta(days=i)
            test_plan = [(check_date, requested_amount)]
            is_safe_check, _ = simulate_90_days(user_id, req_date, user_profile, user_events, test_plan)
            if is_safe_check:
                earliest_full_date = check_date.strftime('%Y-%m-%d')
                break
        
        current_bal = user_profile['current_available_balance'].iloc[0]
        min_bal = user_profile['minimum_balance_to_keep'].iloc[0]
        
        max_possible_today = max(0.0, current_bal - min_bal)
        amount_safe_to_pay = min(requested_amount, max_possible_today)
        
        if is_safe_full:
            amount_safe_to_pay = requested_amount
            

        affordability_status = "not_affordable"
        recommended_method = "not_recommended"
        payment_plan_str = "none"
        spending_changes = "none"
        explanation = "Evaluado por el motor financiero automatizado."
        
        if is_safe_full and 'full_payment' in user_considered_methods:
            affordability_status = "affordable_now"
            recommended_method = "full_payment"
            payment_plan_str = f"{req_date.strftime('%Y-%m-%d')}:{requested_amount}"
            earliest_full_date = req_date.strftime('%Y-%m-%d')
            explanation = "El usuario cuenta con saldo suficiente para cubrir el monto total de manera segura hoy."
            
        else:
            best_option = None
            if 'installments' in user_considered_methods:
                req_options = opts[opts['request_id'] == req_id]
                for _, opt in req_options.iterrows():
                    if opt['payment_method'] == 'installments':
                        plan = build_installment_plan(opt)
                        is_safe_opt, _ = simulate_90_days(user_id, req_date, user_profile, user_events, plan)
                        if is_safe_opt:
                            best_option = opt
                            break
            
            if best_option is not None:
                affordability_status = "affordable_with_plan"
                recommended_method = "installments"
                # Formato de plan: YYYY-MM-DD:monto|YYYY-MM-DD:monto
                plan_tuples = build_installment_plan(best_option)
                payment_plan_str = "|".join([f"{d.strftime('%Y-%m-%d')}:{amt}" for d, amt in plan_tuples])
                explanation = f"Asequible mediante el plan de cuotas {best_option['payment_option_id']} cumpliendo los límites de seguridad."
            
            elif earliest_full_date != "" and pd.to_datetime(earliest_full_date) <= completion_date:
                affordability_status = "affordable_later"
                recommended_method = "wait"
                explanation = f"El gasto no es seguro hoy, pero se proyecta que será completamente seguro a partir de {earliest_full_date}."
            
            else:
                affordability_status = "not_affordable"
                recommended_method = "not_recommended"
                explanation = "El gasto excede la capacidad financiera segura del usuario dentro del horizonte de pronóstico."
                earliest_full_date = "" # Vacío si no es seguro en el periodo

        output_rows.append({
            'request_id': req_id,
            'amount_safe_to_pay': round(amount_safe_to_pay, 2),
            'affordability_status': affordability_status,
            'recommended_payment_method': recommended_method,
            'payment_plan': payment_plan_str,
            'earliest_date_for_full_payment': earliest_full_date,
            'spending_changes_needed': spending_changes,
            'decision_explanation': explanation
        })
        
    df_output = pd.DataFrame(output_rows)
    
    columns_order = [
        'request_id',
        'amount_safe_to_pay',
        'affordability_status',
        'recommended_payment_method',
        'payment_plan',
        'earliest_date_for_full_payment',
        'spending_changes_needed',
        'decision_explanation'
    ]
    
    df_output = df_output[columns_order]
    
    output_path = os.path.join(BASE_DIR, "..", "output.csv")
    df_output.to_csv(output_path, index=False)
    print(f"\n¡Proceso completado con éxito! Archivo generado en: {output_path}")

if __name__ == "__main__":
    process_all_requests()