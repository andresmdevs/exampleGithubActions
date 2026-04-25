import flet as ft
import httpx
import asyncio
import time
import hmac
import hashlib
from urllib.parse import urlencode

# --- Configuración de API (¡Verifica estas claves de nuevo!) ---
API_KEY = "xxxx"
SECRET_KEY = "xxxxxx"
BASE_URL = "https://testnet.binancefuture.com"

# --- Lógica de API (función asíncrona con depuración) ---
async def get_open_orders(symbol: str):
    endpoint = "/fapi/v1"
    timestamp = int(time.time() * 1000)
    params = {'symbol': symbol, 'timestamp': timestamp}
    
    query_string = urlencode(params)
    signature = hmac.new(SECRET_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    
    # La firma se añade al final de los parámetros
    full_query_string = f"{query_string}&signature={signature}"
    
    headers = {'X-MBX-APIKEY': API_KEY}
    
    # --- INICIO: LÍNEAS DE DEPURACIÓN ---
    # Imprime la URL completa que se va a solicitar. Puedes copiarla y pegarla en tu navegador
    # (aunque puede que no funcione por el timestamp, es útil para ver si está bien formada).
    print("======================================================")
    print(f"URL de la solicitud: {BASE_URL}{endpoint}?{full_query_string}")
    print(f"Cabeceras (Headers): {headers}")
    print("======================================================")
    # --- FIN: LÍNEAS DE DEPURACIÓN ---

    try:
        # Nota: En lugar de pasar 'params', construimos la URL manualmente para asegurar el formato.
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}{endpoint}?{full_query_string}", headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        # Si el error persiste, el contenido de e.response.text será el HTML que ves en la app
        return {"error": f"Error de API: {e.response.status_code}", "message": e.response.text}
    except Exception as e:
        return {"error": "Error de conexión", "message": str(e)}

# --- Control de UI Personalizado (Sin cambios aquí) ---
class OrdersView(ft.Column):
    def __init__(self, symbol):
        super().__init__()
        self.symbol = symbol
        self.expand = True
        self.alignment = ft.MainAxisAlignment.CENTER
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        
        self.orders_datatable = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Símbolo")), ft.DataColumn(ft.Text("Lado")),
                ft.DataColumn(ft.Text("Tipo")), ft.DataColumn(ft.Text("Cantidad"), numeric=True),
                ft.DataColumn(ft.Text("Precio"), numeric=True), ft.DataColumn(ft.Text("Estado")),
            ],
            rows=[], expand=True
        )
        self.progress_ring = ft.ProgressRing(visible=False)
        self.error_text = ft.Text(color=ft.Colors.RED, visible=False, width=500, max_lines=5, overflow=ft.TextOverflow.ELLIPSIS)

        self.controls = [
            ft.Row([ft.Text(f"Órdenes Abiertas para {self.symbol}", style=ft.TextThemeStyle.HEADLINE_MEDIUM)]),
            ft.Stack([self.progress_ring, self.error_text]),
            ft.Column([self.orders_datatable], scroll=ft.ScrollMode.ADAPTIVE, expand=True),
        ]

    def did_mount(self):
        self.page.run_task(self.update_orders_periodically)

    async def update_orders_periodically(self):
        while True:
            await self.update_orders()
            await asyncio.sleep(30)

    async def update_orders(self):
        self.progress_ring.visible = True
        self.error_text.visible = False
        self.update()

        orders_data = await get_open_orders(self.symbol)
        
        self.progress_ring.visible = False
        
        if isinstance(orders_data, dict) and "error" in orders_data:
            # Mostramos un mensaje más limpio en la UI
            error_message = orders_data['message']
            if "Request blocked" in error_message:
                self.error_text.value = "Error 403: Solicitud bloqueada por el servidor. Revisa la sincronización del reloj y las claves API."
            else:
                 self.error_text.value = f"Error: {orders_data.get('message', orders_data['error'])}"
            self.error_text.visible = True
        else:
            self.orders_datatable.rows.clear()
            if not orders_data:
                self.orders_datatable.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text("No hay órdenes abiertas", colspan=6, text_align="center"))]))
            else:
                for order in orders_data:
                    self.orders_datatable.rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(order['symbol'])),
                        ft.DataCell(ft.Text(order['side'], color=ft.colors.GREEN if order['side'] == 'BUY' else ft.colors.RED)),
                        ft.DataCell(ft.Text(order['type'])), ft.DataCell(ft.Text(order['origQty'])),
                        ft.DataCell(ft.Text(order['price'])), ft.DataCell(ft.Text(order['status'])),
                    ]))
        self.update()

# --- Función Principal Asíncrona de la App (Sin cambios aquí) ---
async def main(page: ft.Page):
    page.title = "Visor de Órdenes - Binance Futures"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    orders_view_btc = OrdersView("0GUSDT")
    page.add(orders_view_btc)

# --- Punto de Entrada ---
if __name__ == "__main__":
    ft.app(target=main)
