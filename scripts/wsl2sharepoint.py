import msal
from office365.sharepoint.client_context import ClientContext

site_url = "https://americasmining.sharepoint.com/sites/ControldeProcesosToquepala"
# ID público estándar de Microsoft para aplicaciones de consola
client_id = "04b07795-8ddb-461a-bbee-02f9e1bf7b46" 
authority = "https://login.microsoftonline.com/common"

app = msal.PublicClientApplication(client_id, authority=authority)

# Iniciar flujo de código de dispositivo
flow = app.initiate_device_flow(scopes=["https://americasmining.sharepoint.com/.default"])
print(flow["message"]) # Te dirá: "Go to https://microsoft.com/devicelogin and enter code XXX"

result = app.acquire_token_by_device_flow(flow)

if "access_token" in result:
    ctx = ClientContext(site_url).with_access_token(result["access_token"])
    target_list = ctx.web.lists.get_by_title("adf_user")
    
    # Intenta escribir
    item_props = {'Title': 'Test_MFA', 'nombre': 'Adolfo'}
    target_list.add_item(item_props).execute_query()
    print("¡Logrado! Escritura exitosa con token MFA.")
else:
    print(f"Error: {result.get('error_description')}")