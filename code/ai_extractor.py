import os
from google import genai
from PIL import Image
from dotenv import load_dotenv

# Cargamos las variables de entorno (.env)
load_dotenv()

def extract_amount_from_image(image_path):
    """
    Toma la ruta de una imagen, se la envía al LLM y retorna el monto numérico.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ Error: No se encontró GEMINI_API_KEY en el archivo .env")
        return None

    # Inicializamos el cliente con el nuevo SDK
    client = genai.Client(api_key=api_key)
    
    prompt = """
    You are an expert accountant. Extract the total numerical amount to pay from this invoice/receipt.
    Return ONLY the valid float number (e.g., 150.50). 
    Do not include currency symbols, commas, formatting, or any extra text.
    """
    
    try:
        img = Image.open(image_path)
        # ¡Cambiamos a la versión 3.6 que pide el sistema!
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[prompt, img]
        )
        
        # Limpiar la salida y convertir a float
        amount_str = response.text.strip()
        return float(amount_str)
        
    except Exception as e:
        print(f"Error procesando imagen {image_path}: {e}")
        return None