"""
G-Mini Agent - Payment Registry (STUB)
Registro de cuentas de pago/configuración de pagos.
Para producción: integrar Stripe/PayPal/etc.
"""

from typing import Any, Dict, List


class PaymentRegistry:
    """Registro de cuentas de pago disponibles."""
    
    def __init__(self):
        self._accounts: Dict[str, Dict[str, Any]] = {}
    
    def list_accounts(self) -> Dict[str, Any]:
        """Lista todas las cuentas de pago registradas."""
        return {
            "accounts": list(self._accounts.values())
        }
    
    def get_account(self, account_id: str) -> Dict[str, Any] | None:
        """Obtiene cuenta por ID."""
        return self._accounts.get(account_id)


# Singleton global  
_registry_instance = PaymentRegistry()
def get_payment_registry() -> PaymentRegistry:
    return _registry_instance
