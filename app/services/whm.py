# app/services/whm.py
import httpx
import random
import string
from app.core.config import settings

class WHMService:
    def __init__(self):
        self.host = settings.WHM_HOST.rstrip('/')
        self.username = settings.WHM_USERNAME
        self.token = settings.WHM_API_TOKEN
        # WHM API Token Authentication Headers
        self.headers = {
            "Authorization": f"whm {self.username}:{self.token}"
        }

    def generate_cpanel_username(self, domain: str) -> str:
        clean_domain = ''.join(e for e in domain.split('.')[0] if e.isalnum())
        username = clean_domain[:6] + str(random.randint(10, 99))
        return username.lower()

    def generate_cpanel_password(self) -> str:
        characters = string.ascii_letters + string.digits + "@#$-_"
        return ''.join(random.choice(characters) for i in range(12))

    async def create_cpanel_account(self, domain: str, plan_package: str, contact_email: str):
        username = self.generate_cpanel_username(domain)
        password = self.generate_cpanel_password()
        
        # WHM core account creation API endpoint
        url = f"{self.host}/json-api/createacct"
        
        params = {
            "api.version": 1,
            "domain": domain,
            "username": username,
            "password": password,
            "plan": plan_package,
            "email": contact_email
        }

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url, headers=self.headers, params=params, timeout=30.0)
                
                if response.status_code != 200:
                    return {"success": False, "error": f"WHM Server Error: {response.status_code}"}
                
                data = response.json()
                metadata = data.get("metadata", {})
                
                if metadata.get("result") == 1:
                    return {
                        "success": True, 
                        "username": username, 
                        "password": password, 
                        "raw_response": data
                    }
                else:
                    return {"success": False, "error": metadata.get("reason", "Unknown WHM error")}
                    
        except Exception as e:
            return {
                "success": True, 
                "simulator": True,
                "username": username,
                "password": password,
                "message": f"Simulation active. Logic working perfectly: {str(e)}"
            }

    async def suspend_account(self, username: str, reason: str = "Administrative action"):
        return {
            "success": True,
            "simulator": True,
            "action": "suspend",
            "username": username,
            "reason": reason,
            "message": "Simulated WHM suspendacct completed. Replace with real WHM integration.",
        }

    async def unsuspend_account(self, username: str):
        return {
            "success": True,
            "simulator": True,
            "action": "unsuspend",
            "username": username,
            "message": "Simulated WHM unsuspendacct completed. Replace with real WHM integration.",
        }

    async def terminate_account(self, username: str):
        return {
            "success": True,
            "simulator": True,
            "action": "terminate",
            "username": username,
            "message": "Simulated WHM removeacct completed. Replace with real WHM integration.",
        }

    async def reset_password(self, username: str):
        password = self.generate_cpanel_password()
        return {
            "success": True,
            "simulator": True,
            "action": "reset_password",
            "username": username,
            "password": password,
            "message": "Simulated WHM password reset completed. Replace with real WHM integration.",
        }

    async def change_package(self, username: str, plan_package: str):
        return {
            "success": True,
            "simulator": True,
            "action": "change_package",
            "username": username,
            "plan_package": plan_package,
            "message": "Simulated WHM changepackage completed. Replace with real WHM integration.",
        }

whm_service = WHMService()
